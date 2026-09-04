"""
Django management command: offload_and_vacuum

Usage
-----
    python manage.py offload_and_vacuum [--dry-run] [--vacuum] [--batch-size N]

What it does
------------
1. Finds all AudioRecording rows where analysis_result is NOT NULL (legacy
   monolithic JSON blobs that bloat the SQLite file).
2. For each row it extracts the heavy matrix fields from the JSON and writes
   them to a compressed .npz file on disk under MEDIA_ROOT/analysis_matrices/.
3. Moves the scalar-only portion to analysis_metadata and sets matrices_file.
4. Nulls analysis_result to free the space in SQLite.
5. Optionally runs VACUUM on the SQLite connection to reclaim freed pages.

Idempotent — rows that already have matrices_file set are skipped unless
--force is passed.
"""

import json
import numpy as np
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from api.models import AudioRecording


# Fields in the old analysis_result that contain dense matrix data.
# Everything else is treated as a scalar and kept in analysis_metadata.
_MATRIX_FIELDS = {
    'spectrogram_data',
    'mfcc_data',
    'chroma_data',
    'pcp_data',
    'f0_track',
}

# Scalar fields that must be renamed to match the new metadata layout.
_RENAMES = {
    'pcp_data':          None,   # offloaded → matrices_file
    'f0_track':          None,   # offloaded
    'spectrogram_data':  None,   # offloaded
    'mfcc_data':         None,   # offloaded
    'chroma_data':       None,   # offloaded
}

MATRICES_SUBDIR = 'analysis_matrices'
_MAX_PCP_COLS = 500


class Command(BaseCommand):
    help = 'Offload legacy analysis_result matrix blobs to .npz files, then VACUUM SQLite.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be done without writing anything.',
        )
        parser.add_argument(
            '--vacuum', action='store_true', default=True,
            help='Run VACUUM on the SQLite database after offloading (default: True).',
        )
        parser.add_argument(
            '--no-vacuum', action='store_false', dest='vacuum',
            help='Skip the VACUUM step.',
        )
        parser.add_argument(
            '--batch-size', type=int, default=50,
            help='Rows to process per DB query batch (default: 50).',
        )
        parser.add_argument(
            '--force', action='store_true',
            help='Re-offload rows that already have matrices_file set.',
        )

    def handle(self, *args, **options):
        dry_run    = options['dry_run']
        do_vacuum  = options['vacuum']
        batch_size = options['batch_size']
        force      = options['force']

        matrices_root = Path(settings.MEDIA_ROOT) / MATRICES_SUBDIR
        if not dry_run:
            matrices_root.mkdir(parents=True, exist_ok=True)

        qs = AudioRecording.objects.filter(analysis_result__isnull=False)
        if not force:
            qs = qs.filter(matrices_file__isnull=True)

        total = qs.count()
        self.stdout.write(
            f'Found {total} record(s) with legacy analysis_result to offload.'
        )
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to offload.'))
            if do_vacuum and not dry_run:
                self._run_vacuum()
            return

        processed = skipped = errors = 0

        # Process in batches to avoid loading all rows into memory at once.
        offset = 0
        while offset < total:
            batch = list(qs.order_by('id')[offset:offset + batch_size])
            offset += batch_size

            for recording in batch:
                try:
                    result = self._offload_record(
                        recording, matrices_root, dry_run, force
                    )
                    if result == 'processed':
                        processed += 1
                    elif result == 'skipped':
                        skipped += 1
                except Exception as exc:
                    errors += 1
                    self.stderr.write(
                        f'  ERROR pk={recording.pk}: {exc}'
                    )

        self.stdout.write(
            f'\nOffload complete: {processed} processed, {skipped} skipped, '
            f'{errors} errors.'
        )

        if do_vacuum and not dry_run:
            self._run_vacuum()

    # ------------------------------------------------------------------
    def _offload_record(
        self, recording: AudioRecording, matrices_root: Path,
        dry_run: bool, force: bool,
    ) -> str:
        pk = recording.pk
        blob = recording.analysis_result

        if not blob:
            self.stdout.write(f'  pk={pk}: analysis_result is empty — skip.')
            return 'skipped'

        if recording.matrices_file and not force:
            self.stdout.write(f'  pk={pk}: already offloaded — skip.')
            return 'skipped'

        self.stdout.write(f'  pk={pk}: offloading…', ending=' ')

        # ── Separate matrices from scalars ────────────────────────────────────
        npz_kwargs: dict[str, np.ndarray] = {}
        metadata: dict = {}

        for key, val in blob.items():
            if key in _MATRIX_FIELDS and val is not None:
                try:
                    arr = np.array(val, dtype=np.float32)
                    npz_key = key.replace('_data', '')  # pcp_data→pcp etc.
                    # Special-case f0_track (may contain None → NaN)
                    if key == 'f0_track':
                        arr = np.array(
                            [float('nan') if v is None else v for v in val],
                            dtype=np.float64,
                        )
                        npz_kwargs['f0_track'] = arr
                    elif key == 'pcp_data':
                        # Store as pcp_ds; also derive pcp_full (same data here)
                        npz_kwargs['pcp_ds'] = arr.astype(np.float32)
                        npz_kwargs['pcp_full'] = arr.astype(np.float32)
                    else:
                        npz_kwargs[npz_key] = arr
                except Exception:
                    # Can't convert — keep as scalar metadata
                    metadata[key] = val
            else:
                metadata[key] = val

        rel_path = f'{MATRICES_SUBDIR}/{pk}_matrices.npz'
        full_path = matrices_root / f'{pk}_matrices.npz'

        if dry_run:
            size_est = sum(a.nbytes for a in npz_kwargs.values())
            self.stdout.write(
                f'[DRY RUN] would write {full_path} '
                f'(~{size_est // 1024} KB uncompressed, '
                f'{len(npz_kwargs)} arrays)'
            )
            return 'processed'

        if npz_kwargs:
            np.savez_compressed(str(full_path), **npz_kwargs)
            self.stdout.write(
                f'saved {full_path.name} '
                f'({full_path.stat().st_size // 1024} KB compressed)',
                ending=' '
            )
        else:
            self.stdout.write('no matrix arrays found — storing metadata only', ending=' ')

        # ── Persist changes ───────────────────────────────────────────────────
        recording.analysis_metadata = metadata
        recording.matrices_file = rel_path if npz_kwargs else None
        recording.analysis_result = None   # free the blob
        recording.save(update_fields=['analysis_metadata', 'matrices_file', 'analysis_result'])

        self.stdout.write(self.style.SUCCESS('✓'))
        return 'processed'

    # ------------------------------------------------------------------
    def _run_vacuum(self):
        self.stdout.write('\nRunning VACUUM on SQLite database…')
        db_path = settings.DATABASES['default']['NAME']
        before = Path(db_path).stat().st_size if Path(db_path).exists() else 0

        with connection.cursor() as cursor:
            cursor.execute('VACUUM;')

        after = Path(db_path).stat().st_size if Path(db_path).exists() else 0
        freed = (before - after) / (1024 ** 3)
        self.stdout.write(
            self.style.SUCCESS(
                f'VACUUM complete. '
                f'DB size: {before / 1024**2:.1f} MB → {after / 1024**2:.1f} MB '
                f'(freed {freed:.2f} GB)'
            )
        )

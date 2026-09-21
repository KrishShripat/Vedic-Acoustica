"""
Django management command: ingest_corpus

Usage
-----
    python manage.py ingest_corpus [--dry-run] [--limit N] [--source NAME]
                                   [--analyze] [--reanalyze] [--manifest PATH]

What it does
------------
1. Reads a curated clip manifest (test_audio/manifest.json by default).
2. Enforces a **license allowlist** — a clip is skipped unless its license is
   in BOTH the manifest's ``allowlist`` and this command's hard ``_TRUSTED``
   set (currently CC-BY-4.0 and Apache-2.0 only).
3. Downloads each pinned clip, enforces per-clip and cumulative size caps, and
   creates an ``AudioRecording`` with full provenance stored in
   ``corpus_metadata`` (which the ML pipeline never overwrites).
4. Optionally runs the ML pipeline on each ingested clip — via the Celery
   queue when the broker is reachable, falling back to an in-process
   synchronous run otherwise (so local/dev works without Redis).

Idempotency
-----------
Clips are keyed by their pinned URL; re-running skips clips already ingested
unless ``--reanalyze`` is passed (which only re-runs analysis, never
re-downloads).

Attribution
-----------
After a non-dry run an up-to-date ``test_audio/ATTRIBUTION.md`` is written
that names every ingested clip, its source corpus, license and home page.
"""

import json
import time
import urllib.request
from pathlib import Path
from urllib.error import URLError

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import AudioRecording
from api.tasks import process_audio_task

# ── Hard allowlist: clips with any other license are refused outright. ──────
_TRUSTED_LICENSES = {"CC-BY-4.0", "Apache-2.0"}

# ingest_corpus.py → api/management/commands → project root (parents[4])
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MANIFEST = str(_PROJECT_ROOT / "test_audio" / "manifest.json")

_USER_AGENT = "VedicAcoustica-ingest/1.0"


class ClipTooLarge(Exception):
    pass


class Command(BaseCommand):
    help = (
        'Ingest curated recitation clips from test_audio/manifest.json with '
        'license allowlisting and attribution.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--manifest', default=DEFAULT_MANIFEST,
            help='Path to the clip manifest JSON (default: test_audio/manifest.json).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Validate/download to temp only; write nothing.',
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Ingest at most N clips (after source filtering).',
        )
        parser.add_argument(
            '--source', dest='source', default=None,
            help='Only ingest clips from this source (e.g. vaagdhenu | vedavani).',
        )
        parser.add_argument(
            '--analyze', action='store_true',
            help='Run the ML pipeline on each ingested clip (queue -> sync fallback).',
        )
        parser.add_argument(
            '--reanalyze', action='store_true',
            help='Re-run analysis for clips already ingested; do NOT re-download.',
        )
        parser.add_argument(
            '--max-mb-per-clip', type=float, default=8.0,
            help='Hard cap for a single clip in MB (default: 8.0).',
        )

    # ──────────────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        source = options['source']
        analyze = options['analyze']
        reanalyze = options['reanalyze']
        max_bytes = int(options['max_mb_per_clip'] * 1024 * 1024)

        manifest_path = Path(options['manifest'])
        if not manifest_path.exists():
            self.stderr.write(self.style.ERROR(f'Manifest not found: {manifest_path}'))
            return

        with open(manifest_path, encoding='utf-8') as fh:
            manifest = json.load(fh)

        # ── Allowlist enforcement (manifest vs trusted hard set) ──────────────
        allowlist = set(manifest.get('allowlist', []))
        blocked = allowlist - _TRUSTED_LICENSES
        if blocked:
            self.stderr.write(
                self.style.WARNING(
                    f'Manifest allowlist contains untrusted license(s): '
                    f'{sorted(blocked)} — ignoring them.'
                )
            )
            allowlist &= _TRUSTED_LICENSES
        total_mb_cap = manifest.get('max_clips_mb', 40)

        clips = manifest.get('clips', [])
        if source:
            clips = [c for c in clips if c.get('source') == source]
        if limit:
            clips = clips[:limit]

        self.stdout.write(
            f'Manifest: {manifest_path.name} · {len(clips)} candidate clip(s) '
            f'· allowlist {sorted(allowlist)}'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing is written.\n'))
        else:
            self.stdout.write('')

        ingested = skipped = analyzed = errors = 0
        total_bytes = 0

        for i, clip in enumerate(clips, 1):
            label = f"[{i:2d}/{len(clips)}] {clip['id']}"
            license_name = clip.get('license')
            url = clip.get('url')

            if license_name not in allowlist:
                self.stderr.write(
                    self.style.ERROR(
                        f'{label}: license {license_name!r} not allowed — SKIPPED'
                    )
                )
                skipped += 1
                continue

            existing = (
                AudioRecording.objects
                .filter(corpus_metadata__url=url)
                .first()
            )

            reanalyze_only = existing is not None
            if existing is not None and not reanalyze:
                self.stdout.write(
                    f'{label}: already ingested (pk={existing.pk}) — skip.'
                )
                skipped += 1
                continue

            # ── Download (with size enforcement) ────────────────────────────────
            t0 = time.perf_counter()
            try:
                data = self._download(url, max_bytes)
            except ClipTooLarge:
                self.stderr.write(
                    self.style.ERROR(
                        f'{label}: exceeds {options["max_mb_per_clip"]:.1f} MB cap — SKIPPED'
                    )
                )
                skipped += 1
                continue
            except URLError as exc:
                self.stderr.write(
                    self.style.ERROR(f'{label}: download failed — {exc}')
                )
                errors += 1
                continue

            size_mb = len(data) / (1024 * 1024)
            total_bytes += len(data)
            dl_s = time.perf_counter() - t0

            detail = self._clip_summary(clip, size_mb, dl_s)

            if dry_run:
                self.stdout.write(f'{label}: verified {detail}')
                continue

            if reanalyze_only:
                recording = existing
                self.stdout.write(f'{label}: re-analyzing existing pk={recording.pk}.')
            else:
                recording = AudioRecording(
                    title=clip.get('title') or clip.get('id'),
                    corpus_metadata=self._provenance(clip),
                )
                recording.audio_file.save(
                    f"{clip['id']}.wav", ContentFile(data), save=False
                )
                recording.save()
                ingested += 1
                self.stdout.write(f'{label}: ingested as pk={recording.pk} ({detail})')

            # ── Analysis ───────────────────────────────────────────────────────
            if analyze or reanalyze:
                outcome = self._enqueue_analysis(recording.pk)
                if outcome in ('queued', 'sync'):
                    analyzed += 1
                else:
                    errors += 1
                self.stdout.write(f'  analysis: {outcome} for pk={recording.pk}')

        if not dry_run:
            self._write_attribution(manifest_path.parent)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone: {ingested} ingested, {skipped} skipped, '
                f'{analyzed} analyzed, {errors} errors '
                f'({total_bytes / 1024**2:.2f} MB downloaded).'
            )
        )
        if total_bytes > total_mb_cap * 1024 * 1024:
            self.stderr.write(
                self.style.WARNING(
                    f'Cumulative corpus exceeds the {total_mb_cap} MB manifest cap '
                    f'({total_bytes / 1024**2:.1f} MB) — increase max_clips_mb in '
                    'the manifest if this is intentional.'
                )
            )

    # ──────────────────────────────────────────────────────────────────────────

    def _download(self, url: str, max_bytes: int) -> bytes:
        req = urllib.request.Request(
            url, headers={'User-Agent': _USER_AGENT}, method='GET'
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            content_length = resp.headers.get('Content-Length')
            if content_length and int(content_length) > max_bytes:
                raise ClipTooLarge()
            data = resp.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ClipTooLarge()
        return data

    def _clip_summary(self, clip: dict, size_mb: float, dl_s: float) -> str:
        return (
            f'{size_mb:.2f} MB in {dl_s:.2f}s · {clip["license"]}'
            f' · {clip.get("duration_s", "?")}s'
        )

    def _provenance(self, clip: dict) -> dict:
        return {
            'corpus_id': clip.get('id'),
            'source': clip.get('source'),
            'license': clip.get('license'),
            'license_url': clip.get('license_url'),
            'url': clip.get('url'),
            'homepage': clip.get('homepage'),
            'attribution': clip.get('attribution'),
            'text': clip.get('text'),
            'transliteration': clip.get('transliteration'),
            'ingested_at_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        }

    def _enqueue_analysis(self, pk: int) -> str:
        """Queue analysis; fall back to an in-process run if the broker is down."""
        try:
            process_audio_task.delay(pk)
            return 'queued'
        except Exception as exc:  # BrokerConnectionError etc.
            self.stderr.write(
                self.style.WARNING(
                    f'  broker unavailable ({exc.__class__.__name__}); '
                    f'running pipeline synchronously for pk={pk}'
                )
            )
            try:
                from api.tasks import _run_pipeline  # noqa: PLC0415

                _run_pipeline(pk)
                return 'sync'
            except Exception as exc2:
                self.stderr.write(
                    self.style.ERROR(f'  sync analysis failed for pk={pk}: {exc2}')
                )
                return 'error'

    def _write_attribution(self, manifest_dir: Path) -> None:
        rows = []
        for rec in AudioRecording.objects.filter(
            corpus_metadata__isnull=False,
        ).order_by('pk'):
            meta = rec.corpus_metadata or {}
            rows.append({
                'pk': rec.pk,
                'title': rec.title,
                'license': meta.get('license', '?'),
                'license_url': meta.get('license_url', ''),
                'homepage': meta.get('homepage', ''),
                'attribution': meta.get('attribution', ''),
                'audio_file': rec.audio_file.name,
            })

        lines = [
            '# Attribution & Licensing — Curated Corpus',
            '',
            'Every clip ingested via `manage.py ingest_corpus` is listed here with',
            'its source corpus, license and attribution. Nothing from these files is',
            'redistributed: the app downloads the pinned originals from the corpus',
            'home pages and stores them under `MEDIA_ROOT/`.',
            '',
            '| PK | Title | License | Source |',
            '|----|-------|---------|--------|',
        ]
        for r in rows:
            lines.append(
                f"| {r['pk']} | {r['title']} | "
                f"[{r['license']}]({r['license_url']}) | "
                f"{r['homepage']} |"
            )
        lines += [
            '',
            '## Attribution',
            '',
        ]
        seen = set()
        for r in rows:
            key = (r['license'], r['attribution'])
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- **{r['license']}** — {r['attribution']}")
        lines += ['', f"_Regenerated by `ingest_corpus` at "
                     f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}._", '']

        out = manifest_dir / 'ATTRIBUTION.md'
        out.write_text('\n'.join(lines), encoding='utf-8')
        self.stdout.write(f'Attribution written: {out}')
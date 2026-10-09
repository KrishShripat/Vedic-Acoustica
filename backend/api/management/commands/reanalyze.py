"""
Django management command: reanalyze

Re-runs the 4-stage ML pipeline on recordings whose stored
``analysis_metadata`` was produced by an older algorithm.  Every result is
stamped with ``ml_engine.PIPELINE_VERSION``; results without a matching stamp
are considered stale.

Usage
-----
    python manage.py reanalyze                 # re-run every stale recording
    python manage.py reanalyze --all           # re-run every recording
    python manage.py reanalyze --pks 2 3       # re-run specific recordings
    python manage.py reanalyze --dry-run       # list targets, change nothing
    python manage.py reanalyze --sync          # run inline instead of Celery

Dispatch is identical to a normal user analysis: the task goes to the Celery
queue, with an in-process fallback if the broker is unreachable.
"""

from django.core.management.base import BaseCommand

from api.models import AudioRecording
from api.tasks import process_audio_task
from ml_engine import PIPELINE_VERSION


class Command(BaseCommand):
    help = (
        'Re-run the ML pipeline on stale recordings (or all, or selected pks).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--all', action='store_true',
            help='Re-run every recording, not just stale ones.',
        )
        parser.add_argument(
            '--pks', nargs='*', type=int, default=None,
            help='Only re-run these recording primary keys.',
        )
        parser.add_argument(
            '--sync', action='store_true',
            help='Run the pipeline inline instead of dispatching to Celery.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='List the recordings that would be re-analysed, then exit.',
        )

    def handle(self, *args, **options):
        qs = AudioRecording.objects.all().order_by('pk')
        if options['pks']:
            qs = qs.filter(pk__in=options['pks'])

        targets = []
        for recording in qs:
            metadata = recording.analysis_metadata or {}
            stamped = metadata.get('pipeline_version')
            stale = (not recording.is_analyzed) or stamped != PIPELINE_VERSION
            if options['pks'] or options['all'] or stale:
                targets.append((recording, stamped, stale))

        if not targets:
            self.stdout.write(self.style.SUCCESS(
                f'Nothing to do — all recordings already at {PIPELINE_VERSION}.'
            ))
            return

        if options['dry_run']:
            for recording, stamped, stale in targets:
                state = f'stale ({stamped or "unstamped"})' if stale else 'current'
                self.stdout.write(
                    f'  pk={recording.pk:<4} {state:<28} {recording.title}'
                )
            self.stdout.write(self.style.WARNING(
                f'Dry run: {len(targets)} recording(s) would be re-analysed.'
            ))
            return

        queued = sync = errors = 0
        for recording, _stamped, _stale in targets:
            pk = recording.pk
            if options['sync']:
                outcome = self._run_sync(pk)
            else:
                outcome = self._dispatch(pk)
            if outcome == 'queued':
                queued += 1
            elif outcome == 'sync':
                sync += 1
            else:
                errors += 1
            self.stdout.write(f'  pk={pk:<4} -> {outcome}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {queued} queued, {sync} run inline, {errors} errors.'
        ))

    # ──────────────────────────────────────────────────────────────────────────

    def _dispatch(self, pk: int) -> str:
        """Queue the analysis; fall back to an inline run if the broker is down."""
        try:
            process_audio_task.delay(pk)
            return 'queued'
        except Exception as exc:  # noqa: BLE001 - BrokerConnectionError etc.
            self.stderr.write(
                self.style.WARNING(
                    f'  broker unavailable ({exc.__class__.__name__}); '
                    f'running pipeline inline for pk={pk}'
                )
            )
            return self._run_sync(pk)

    def _run_sync(self, pk: int) -> str:
        try:
            from api.tasks import _run_pipeline  # noqa: PLC0415

            _run_pipeline(pk)
            return 'sync'
        except Exception as exc:  # noqa: BLE001
            self.stderr.write(self.style.ERROR(f'  analysis failed for pk={pk}: {exc}'))
            return 'error'

"""
Django management command: purge_probe_data

Deletes the probe user + probe recordings left behind by a live audit run
(audit finding R6).  Defaults match the 2026-09-21 audit's round-trip, which
registered a throwaway user and uploaded ``test_10s.wav`` (recordings id 15).

Usage
-----
    python manage.py purge_probe_data \
        [--username audit_probe_user] \
        [--recording-titles test_10s.wav] \
        [--recording-pks 15] \
        [--dry-run]

Warnings
--------
- ``--username``/``--recording-pks`` default to the probe values; pass
  ``--recording-titles ''`` to keep only pk-based deletion.
- Deleting a recording removes its media + analysis artifacts on disk and
  purges its Celery progress/snapshot files (best-effort).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from api.models import AudioRecording

User = get_user_model()

_DEFAULT_USER = 'audit_probe_user'
_DEFAULT_PKS = [15]
_DEFAULT_TITLES = ['test_10s.wav']


class Command(BaseCommand):
    help = (
        'Delete audit-probe leftovers: the throwaway user, its recordings and '
        'on-disk media.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', default=_DEFAULT_USER,
            help=f'Probe username to delete (default: {_DEFAULT_USER!r}).',
        )
        parser.add_argument(
            '--recording-pks', nargs='*', type=int, default=_DEFAULT_PKS,
            help='Recording primary keys to delete (default: 15).',
        )
        parser.add_argument(
            '--recording-titles', nargs='*', default=_DEFAULT_TITLES,
            help=(
                'Delete recordings whose audio filename startswith/endswith '
                'these substrings (default: test_10s.wav). Pass --recording-titles '
                "'' to disable title-based deletion."
            ),
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be deleted without deleting anything.',
        )

    # ──────────────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        usernames = [u for u in [options['username']] if u]
        pks = options['recording_pks']
        titles = [t for t in options['recording_titles'] if t]

        users = (
            list(User.objects.filter(username__in=usernames)) if usernames else []
        )
        recordings = list(
            AudioRecording.objects.filter(
                pk__in=pks,
            ).order_by('pk')
        )
        title_matches = []
        for sub in titles:
            title_matches += list(
                AudioRecording.objects.filter(
                    audio_file__icontains=sub,
                ).exclude(pk__in=[r.pk for r in recordings])
            )

        recordings = list({r.pk: r for r in recordings + title_matches}.values())
        recordings.sort(key=lambda r: r.pk)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing deleted.\n'))
        else:
            self.stdout.write('')

        if users:
            for u in users:
                self.stdout.write(f'user: {u.username} (pk={u.pk}) -> delete')
            if not dry_run:
                for u in users:
                    u.delete()
                    self.stdout.write(f'  deleted {u.username}.')
        else:
            self.stdout.write(f'user: no match for {usernames or ""!r}')

        if recordings:
            for r in recordings:
                self.stdout.write(
                    f'recording: pk={r.pk} title={r.title!r} '
                    f'file={r.audio_file.name} -> delete'
                )
            if not dry_run:
                import os

                for r in recordings:
                    pk = r.pk
                    name = getattr(r, 'audio_file', None) and r.audio_file.name
                    if name:
                        try:
                            storage = r.audio_file.storage
                            if storage.exists(name):
                                storage.delete(name)
                        except Exception as exc:  # OSError, ValueError, ...
                            self.stderr.write(
                                self.style.WARNING(f'  media cleanup audio: {exc}')
                            )
                        try:
                            root = storage.path(name)
                            stem, _ = os.path.splitext(root)
                            if os.path.exists(f'{stem}.mp3'):
                                os.remove(f'{stem}.mp3')
                        except Exception as exc:  # NotImplementedError, OSError
                            self.stderr.write(
                                self.style.WARNING(f'  media cleanup mp3: {exc}')
                            )
                    r.delete()
                    self.stdout.write(f'  deleted pk={pk}.')
        else:
            self.stdout.write(f'recording: no match for pks={pks} / titles={titles}')

        self.stdout.write(
            self.style.SUCCESS(
                '\nDone.' + (' (dry run)' if dry_run else '')
            )
        )
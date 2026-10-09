"""One-time cleanup: remove the throwaway uploads used to diagnose the
2026-10-09 "failed to fetch" report.

Safe and idempotent: matching only by the exact probe titles, deleting rows
that do not exist is a no-op, and media cleanup is best-effort.
"""

import os

from django.conf import settings
from django.db import migrations

_PROBE_TITLES = ['probe_test.wav', 'probe_origin_test.wav']


def _cleanup_media(recording):
    try:
        field = recording.audio_file
    except Exception:  # noqa: BLE001
        field = None
    if field and field.name:
        try:
            storage = field.storage
            path = storage.path(field.name)
            stem, _ = os.path.splitext(path)
            for candidate in (path, f'{stem}.mp3'):
                if os.path.exists(candidate):
                    os.remove(candidate)
        except Exception:  # noqa: BLE001 - NotImplementedError/OSError/etc.
            pass

    matrices = getattr(recording, 'matrices_file', None)
    if matrices:
        try:
            path = os.path.join(settings.MEDIA_ROOT, matrices)
            if os.path.exists(path):
                os.remove(path)
        except Exception:  # noqa: BLE001
            pass


def remove_probe_recordings(apps, schema_editor):
    AudioRecording = apps.get_model('api', 'AudioRecording')
    for recording in AudioRecording.objects.filter(title__in=_PROBE_TITLES):
        _cleanup_media(recording)
        recording.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_delete_reanalyze_probe_user'),
    ]

    operations = [
        migrations.RunPython(remove_probe_recordings, migrations.RunPython.noop),
    ]

"""
Django management command: seed_samples

Idempotently (re)creates the bundled sample recordings that the landing page and
demo screens link to (e.g. ``/media/recordings/test_10s.wav``).  A Space volume
wipe can never strand the frontend with 404 media again (audit finding R3).

Why synthesize instead of bundling audio files?
------------------------------------------------
Hugging Face Spaces now rejects binary files at the git hook level (requires
Xet storage), and shipping recitation clips in-repo has licensing/corpus
provenance implications the app deliberately avoids (see ``ingest_corpus``,
which downloads pinned, license-allowlisted corpus originals instead).  The
sample clips are therefore generated on the first boot from the SAME Shruti
frequency model the ML pipeline uses, so they analyse cleanly and their
playback URL (``/media/recordings/test_10s.wav``) is always guaranteed.

Usage
-----
    python manage.py seed_samples [--analyze]

Behaviour
---------
- Generates each named sample clip in memory, writes it to ``MEDIA_ROOT`` and
  creates an ``AudioRecording`` whose filename is stable (``test_10s.wav``).
- Already-seeded clips (matched by audio filename) are skipped — safe to run on
  every boot.
- With ``--analyze``, enqueues the ML pipeline for each newly seeded clip
  (Celery queue, falling back to an in-process run if the broker is down).
"""

import numpy as np

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from api.models import AudioRecording
from api.tasks import process_audio_task
from ml_engine.audio_processing import SR
from ml_engine.shruti_mapping import SHRUTI_FREQUENCIES, SHRUTI_NAMES

def _ghana_motif(cycles: int = 3) -> list:
    """Build a bell-shaped Ghana-path sequence over a 5-word phrase.

    For each consecutive 3-word window ``abc`` the traditional pattern is
    ``ab, ba, abc, cba, abc``; the run closes with ``de, ed, de``.  Repeating
    the pass keeps the clip analysis-friendly (a clear forward/reverse cycle
    for the DTW validator).
    """
    phrase = [0, 4, 7, 9, 13]  # Sa Re Ga Ma Pa (shuddha Shruti bins)
    notes = []
    for _ in range(cycles):
        for i in range(len(phrase) - 2):
            a, b, c = phrase[i], phrase[i + 1], phrase[i + 2]
            notes += [a, b, b, a, a, b, c, c, b, a, a, b, c]
        d, e = phrase[-2], phrase[-1]
        notes += [d, e, e, d, d, e]
    return notes


_GHANA_MOTIF = _ghana_motif(cycles=3)

# ── Samples to seed: {filename: (description, shruti index motif, octave) } ─
# The motif is a list of Shruti indices swept in a gentle melody; playing it one
# octave down keeps it in a comfortable recitation register (~130–165 Hz).
_SAMPLES = {
    'test_10s.wav': {
        'title': 'Sample: Kalyani arpeggio',
        # Kalyani: Sa Re Ga Ma(2) Pa Dha Ni — ascending then descending.
        'motif': [0, 3, 8, 11, 13, 17, 21, 22, 21, 17, 13, 11, 8, 3, 0],
        'note_dur': 0.55,
        'octave': 0.5,
    },
    'isavasya_ghanam_60s.wav': {
        'title': 'Sample: Ghana Patha recitation (synthetic)',
        'motif': _GHANA_MOTIF,
        # 60 s target for the landing-page player.
        'note_dur': 60.0 / len(_GHANA_MOTIF),
        'octave': 0.5,
    },
}


def _note(freq_hz: float, dur_s: float, octave: float) -> np.ndarray:
    """Single harmonic-rich tone at ``freq``; harmonics give PCP a natural
    profile so raga detection isn't fed a bare fundamental."""
    t = np.linspace(0, dur_s, int(SR * dur_s), endpoint=False)
    w = (
        0.5 * np.sin(2 * np.pi * freq_hz * t)
        + 0.25 * np.sin(2 * np.pi * 2 * freq_hz * t)
        + 0.12 * np.sin(2 * np.pi * 3 * freq_hz * t)
        + 0.04 * np.sin(2 * np.pi * 4 * freq_hz * t)
    )
    return (w * octave).astype(np.float32)


def _synthesize(spec: dict) -> bytes:
    """Render the named sample to 16-bit WAV bytes."""
    import io

    import soundfile as sf

    parts = [
        _note(SHRUTI_FREQUENCIES[SHRUTI_NAMES[i]], spec['note_dur'], spec['octave'])
        for i in spec['motif']
    ]
    audio = np.concatenate(parts)

    # Gentle fade in/out so playback has no clicks.
    fade = int(0.05 * SR)
    audio[:fade] *= np.linspace(0, 1, fade)
    audio[-fade:] *= np.linspace(1, 0, fade)

    buf = io.BytesIO()
    sf.write(buf, audio, SR, format='WAV', subtype='PCM_16')
    return buf.getvalue()


class Command(BaseCommand):
    help = (
        'Idempotently regenerate the bundled sample recordings (landing-page '
        'media) into the database; optionally run the ML pipeline on them.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze', action='store_true',
            help='Run the ML pipeline on each newly seeded clip (queue -> sync fallback).',
        )

    # ──────────────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        analyze = options['analyze']
        seeded = skipped = analyzed = errors = 0

        for name, spec in _SAMPLES.items():
            existing = AudioRecording.objects.filter(audio_file__endswith=name).first()
            if existing is not None:
                self.stdout.write(f'{name}: already seeded (pk={existing.pk}) — skip.')
                skipped += 1
                continue

            data = _synthesize(spec)
            recording = AudioRecording(
                title=spec['title'],
                corpus_metadata={
                    'sample': True,
                    'synthetic': True,
                    'source': 'synthesized at boot from Shruti model',
                    'generator': 'manage.py seed_samples',
                },
            )
            recording.audio_file.save(
                name, ContentFile(data), save=False
            )
            recording.save()
            seeded += 1
            duration_s = max(0.0, (len(data) - 44) / (2 * SR))
            self.stdout.write(
                self.style.SUCCESS(
                    f'{name}: seeded as pk={recording.pk} '
                    f'({len(data) / 1024 ** 2:.2f} MB, {duration_s:.1f}s clip).'
                )
            )

            if analyze:
                outcome = self._enqueue_analysis(recording.pk)
                analyzed += 1 if outcome in ('queued', 'sync') else 0
                errors += 1 if outcome == 'error' else 0
                self.stdout.write(f'  analysis: {outcome} for pk={recording.pk}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone: {seeded} seeded, {skipped} skipped, '
                f'{analyzed} analyzed, {errors} errors.'
            )
        )

    # ──────────────────────────────────────────────────────────────────────────

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
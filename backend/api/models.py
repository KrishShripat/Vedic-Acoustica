import os

from django.conf import settings
from django.db import models


class AudioRecording(models.Model):
    title = models.CharField(max_length=255, blank=True)
    audio_file = models.FileField(upload_to='recordings/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def playback_file(self):
        if not self.audio_file:
            return None
        mp3_rel = os.path.splitext(self.audio_file.name)[0] + '.mp3'
        if os.path.exists(os.path.join(settings.MEDIA_ROOT, mp3_rel)):
            return f"{settings.MEDIA_URL}{mp3_rel}"
        return None

    # ── New slim storage ──────────────────────────────────────────────────────
    # Scalar metrics, scores, and detection metadata only — no matrices here.
    analysis_metadata = models.JSONField(null=True, blank=True)
    # Path (relative to MEDIA_ROOT) to the compressed .npz file holding heavy
    # arrays: spectrogram, mfcc, chroma, pcp, f0_track.
    matrices_file = models.CharField(max_length=512, null=True, blank=True)

    # ── Legacy field (kept nullable so existing rows survive) ─────────────────
    # Will be nulled out by the offload_and_vacuum management command.
    analysis_result = models.JSONField(null=True, blank=True)

    is_analyzed = models.BooleanField(default=False)

    def __str__(self):
        return self.title or f"Recording {self.pk}"

from django.db import models


class AudioRecording(models.Model):
    title = models.CharField(max_length=255, blank=True)
    audio_file = models.FileField(upload_to='recordings/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    analysis_result = models.JSONField(null=True, blank=True)
    is_analyzed = models.BooleanField(default=False)

    def __str__(self):
        return self.title or f"Recording {self.pk}"

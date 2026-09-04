from rest_framework import serializers
from .models import AudioRecording


class AudioRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioRecording
        # NOTE: analysis_result (legacy large blob) is intentionally excluded.
        # Heavy matrix data is loaded from .npz on disk by the view layer.
        # analysis_metadata holds scalar metrics only; matrices_file is the
        # path to the compressed .npz file for the current record.
        fields = [
            'id', 'title', 'audio_file', 'uploaded_at',
            'analysis_metadata', 'matrices_file', 'is_analyzed',
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'analysis_metadata', 'matrices_file', 'is_analyzed',
        ]

    _ALLOWED_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac')
    _MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

    def validate_audio_file(self, value):
        if value.size > self._MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(
                f"File size cannot exceed 50 MB "
                f"(received {value.size / 1024 / 1024:.1f} MB)."
            )
        if not value.name.lower().endswith(self._ALLOWED_EXTENSIONS):
            raise serializers.ValidationError(
                f"Unsupported file type. "
                f"Allowed extensions: {', '.join(self._ALLOWED_EXTENSIONS)}."
            )
        return value

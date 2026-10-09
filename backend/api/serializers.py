from rest_framework import serializers
from .models import AudioRecording


class AudioRecordingSerializer(serializers.ModelSerializer):
    playback_file = serializers.SerializerMethodField()

    class Meta:
        model = AudioRecording
        # NOTE: analysis_result (legacy large blob) is intentionally excluded.
        # Heavy matrix data is loaded from .npz on disk by the view layer.
        # analysis_metadata holds scalar metrics only; matrices_file is the
        # path to the compressed .npz file for the current record.
        fields = [
            'id', 'title', 'audio_file', 'playback_file', 'uploaded_at',
            'uploaded_by', 'analysis_metadata', 'matrices_file', 'is_analyzed',
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'uploaded_by', 'analysis_metadata', 'matrices_file', 'is_analyzed',
        ]

    def get_playback_file(self, obj):
        return obj.playback_file

    _ALLOWED_EXTENSIONS = ('.wav', '.mp3', '.ogg', '.flac')
    _MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

    def validate_audio_file(self, value):
        import os
        import re
        # Sanitize to an ASCII-safe basename: strip directory components,
        # replace any character that isn't alphanumeric, dot, hyphen, or
        # underscore with '_', strip leading dashes/dots to prevent CLI flag
        # confusion in downstream subprocesses, and cap at 200 characters.
        raw_base = os.path.basename(value.name)
        safe_name = re.sub(r'[^\w.\-]', '_', raw_base).lstrip('.-')
        if not safe_name:
            safe_name = 'audio_recording'
        if len(safe_name) > 200:
            safe_name = safe_name[:200]
        value.name = safe_name

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

        # Verify magic bytes to reject non-audio files masquerading with audio extensions
        pos = value.tell() if hasattr(value, 'tell') else 0
        try:
            head = value.read(32)
        finally:
            if hasattr(value, 'seek'):
                value.seek(pos)

        is_wav = (head[:4] in (b'RIFF', b'RIFX') and len(head) >= 12 and head[8:12] == b'WAVE')
        is_mp3 = head[:3] == b'ID3' or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0)
        is_ogg = head[:4] == b'OggS'
        is_flac = head[:4] == b'fLaC'

        if not (is_wav or is_mp3 or is_ogg or is_flac):
            raise serializers.ValidationError(
                "Uploaded file header does not match a valid audio format (WAV, MP3, OGG, or FLAC)."
            )

        return value


class AudioRecordingListSerializer(AudioRecordingSerializer):
    """Lightweight list view — heavy per-frame metadata belongs to the detail
    endpoint only, otherwise GET /recordings/ bloats with every row."""

    class Meta(AudioRecordingSerializer.Meta):
        fields = [
            'id', 'title', 'audio_file', 'playback_file', 'uploaded_at',
            'uploaded_by', 'is_analyzed',
        ]

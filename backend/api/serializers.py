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

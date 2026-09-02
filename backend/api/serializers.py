from rest_framework import serializers
from .models import AudioRecording


class AudioRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioRecording
        fields = ['id', 'title', 'audio_file', 'uploaded_at', 'analysis_result', 'is_analyzed']
        read_only_fields = ['id', 'uploaded_at', 'analysis_result', 'is_analyzed']

from rest_framework import serializers
from .models import AudioRecording


class AudioRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioRecording
        fields = ['id', 'title', 'audio_file', 'uploaded_at', 'analysis_result', 'is_analyzed']
        read_only_fields = ['id', 'uploaded_at', 'analysis_result', 'is_analyzed']


class AnalysisResultSerializer(serializers.Serializer):
    shruti_clusters = serializers.DictField()
    dominant_frequencies = serializers.ListField(child=serializers.FloatField())
    spectral_centroid_timeline = serializers.ListField(child=serializers.FloatField())
    ghana_patha_valid = serializers.BooleanField()
    ghana_patha_confidence = serializers.FloatField()
    spectrogram_data = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    mfcc_data = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))

import os
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import AudioRecording
from .serializers import AudioRecordingSerializer
from ml_engine.audio_processing import extract_features
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga


@api_view(['POST'])
def upload_audio(request):
    serializer = AudioRecordingSerializer(data=request.data)
    if serializer.is_valid():
        recording = serializer.save()
        return Response(
            AudioRecordingSerializer(recording).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def list_recordings(request):
    recordings = AudioRecording.objects.all().order_by('-uploaded_at')
    serializer = AudioRecordingSerializer(recordings, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def recording_detail(request, pk):
    try:
        recording = AudioRecording.objects.get(pk=pk)
    except AudioRecording.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    serializer = AudioRecordingSerializer(recording)
    return Response(serializer.data)


@api_view(['POST'])
def analyze_audio(request, pk):
    try:
        recording = AudioRecording.objects.get(pk=pk)
    except AudioRecording.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    audio_path = recording.audio_file.path

    if not os.path.exists(audio_path):
        return Response(
            {'error': 'Audio file not found on disk'},
            status=status.HTTP_404_NOT_FOUND,
        )

    features = extract_features(audio_path)
    clustering_results = run_clustering(features)
    ghana_result = validate_ghana_patha(features)
    raga_result = detect_raga(clustering_results, features=features)

    analysis = {
        'shruti_clusters': clustering_results['shruti_clusters'],
        # PCP + pYIN derived per-frame Shruti assignments
        'freq_assignments': clustering_results['freq_assignments'],
        # 22-element mean PCP vector [0, 1] — overall tonal fingerprint
        'mean_pcp': clustering_results['mean_pcp'],
        # pYIN F0 pitch track — null for unvoiced / silent frames
        'f0_track': features['f0_track'],
        # Fraction of frames detected as voiced [0, 1]
        'voiced_ratio': features['voiced_ratio'],
        'spectral_centroid_timeline': features['spectral_centroid'].tolist(),
        # Ghana Patha — DTW-based validation results
        'ghana_patha_valid': ghana_result['is_valid'],
        'ghana_patha_confidence': ghana_result['confidence'],
        'ghana_patha_repetition_score': ghana_result.get('repetition_score', 0.0),
        'ghana_patha_n_segments': ghana_result.get('n_segments', 0),
        'ghana_patha_segments': ghana_result.get('segments', []),
        'ghana_patha_detected_pattern': ghana_result.get('detected_pattern', []),
        # DTW-specific diagnostics (None when legacy path used)
        'ghana_patha_dtw_details': ghana_result.get('dtw_details'),
        'raga_detection': raga_result,
        'spectrogram_data': features['spectrogram'].tolist(),
        'mfcc_data': features['mfcc'].tolist(),
        'chroma_data': features['chroma'].tolist(),
        'tempo': features['tempo'],
        'duration': features['duration'],
    }

    recording.analysis_result = analysis
    recording.is_analyzed = True
    recording.save()

    return Response(analysis)

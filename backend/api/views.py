import os
import json
import time
import threading
from django.http import StreamingHttpResponse
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


# ---------------------------------------------------------------------------
# File-based atomic progress store
#
# Why not in-memory?
#   Gunicorn runs multiple worker processes.  The POST /analyze/<pk>/ request
#   and the GET /analyze/<pk>/status/ SSE stream are likely handled by
#   *different* workers, so an in-memory dict is invisible across the process
#   boundary.  A file-based store is visible to all workers with zero extra
#   infrastructure.
#
# Design:
#   • Each recording gets its own tiny JSON file: /tmp/vedic_progress_{pk}.json
#   • Writes use NamedTemporaryFile + os.replace() for atomic cross-process
#     visibility (the rename is atomic on POSIX filesystems).
#   • A per-PK threading.Lock prevents torn writes *within* a single worker
#     (rare, since the ML pipeline is single-threaded per request).
#
# Progress dict schema:
#   { 'stage': str, 'percent': int, 'status': 'running'|'done'|'error',
#     'error': str|None }
# ---------------------------------------------------------------------------
import tempfile

_WRITE_LOCKS: dict[int, threading.Lock] = {}
_LOCKS_MUTEX = threading.Lock()

_PROGRESS_DIR = os.environ.get('VEDIC_PROGRESS_DIR', tempfile.gettempdir())


def _progress_path(pk: int) -> str:
    return os.path.join(_PROGRESS_DIR, f'vedic_progress_{pk}.json')


def _get_lock(pk: int) -> threading.Lock:
    with _LOCKS_MUTEX:
        if pk not in _WRITE_LOCKS:
            _WRITE_LOCKS[pk] = threading.Lock()
        return _WRITE_LOCKS[pk]


def _set_progress(pk: int, stage: str, percent: int,
                  status_val: str = 'running', error: str | None = None) -> None:
    """Atomically write a progress snapshot visible to all Gunicorn workers."""
    payload = json.dumps({
        'stage':   stage,
        'percent': percent,
        'status':  status_val,
        'error':   error,
    })
    dest = _progress_path(pk)
    with _get_lock(pk):
        # Write to a temp file in the same directory, then rename atomically.
        fd, tmp = tempfile.mkstemp(dir=_PROGRESS_DIR, suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w') as fh:
                fh.write(payload)
            os.replace(tmp, dest)   # POSIX atomic rename
        except Exception:           # noqa: BLE001
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def _get_progress(pk: int) -> dict | None:
    """Read the latest progress snapshot written by any worker."""
    path = _progress_path(pk)
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _delete_progress(pk: int) -> None:
    """Remove the progress file after the SSE stream has closed."""
    try:
        os.unlink(_progress_path(pk))
    except FileNotFoundError:
        pass
    with _LOCKS_MUTEX:
        _WRITE_LOCKS.pop(pk, None)


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse_message(data: dict) -> str:
    """Format a dict as an SSE data frame."""
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------

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
    """Run the ML pipeline, writing per-stage progress to a shared file so
    any Gunicorn worker can read it via the SSE status endpoint."""
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

    try:
        # ── Stage 1: Feature Extraction ────────────────────────────────────
        _set_progress(pk, 'Feature Extraction', 5)
        features = extract_features(audio_path)
        _set_progress(pk, 'Feature Extraction', 30)

        # ── Stage 2: Clustering (K=22 Shrutis) ────────────────────────────
        _set_progress(pk, 'Shruti Clustering', 35)
        clustering_results = run_clustering(features)
        _set_progress(pk, 'Shruti Clustering', 60)

        # ── Stage 3: Ghana Patha Validation ───────────────────────────────
        _set_progress(pk, 'Ghana Patha Validation', 65)
        ghana_result = validate_ghana_patha(features)
        _set_progress(pk, 'Ghana Patha Validation', 80)

        # ── Stage 4: Raga Detection ────────────────────────────────────────
        _set_progress(pk, 'Raga Detection', 85)
        raga_result = detect_raga(clustering_results, features=features)
        _set_progress(pk, 'Raga Detection', 98)

    except Exception as exc:  # noqa: BLE001
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── PCP heatmap: downsample time axis to ≤ 500 columns ──────────────────
    # pcp shape: (22, n_frames).  We keep all 22 Shruti rows and thin the
    # time axis so the JSON payload stays < ~200 KB even for 10-minute files.
    _pcp_raw = features['pcp']            # (22, n_frames)
    _MAX_COLS = 500
    if _pcp_raw.shape[1] > _MAX_COLS:
        _step = _pcp_raw.shape[1] // _MAX_COLS
        _pcp_ds = _pcp_raw[:, ::_step][:, :_MAX_COLS]
    else:
        _pcp_ds = _pcp_raw
    _n_cols = _pcp_ds.shape[1]
    # Build a seconds axis matching downsampled columns
    _hop_sec = 512 / 22050          # hop_length / SR
    _orig_step = max(_pcp_raw.shape[1] // _MAX_COLS, 1)
    _time_axis = [round(i * _hop_sec * _orig_step, 3) for i in range(_n_cols)]

    analysis = {
        'shruti_clusters': clustering_results['shruti_clusters'],
        # PCP + pYIN derived per-frame Shruti assignments
        'freq_assignments': clustering_results['freq_assignments'],
        # 22-element mean PCP vector [0, 1] — overall tonal fingerprint
        'mean_pcp': clustering_results['mean_pcp'],
        # Full per-frame PCP matrix for the heatmap — shape (22, n_cols_ds)
        # Each inner list is one Shruti row; columns are downsampled time frames.
        'pcp_data': _pcp_ds.tolist(),
        # Seconds timestamps aligned with pcp_data columns
        'pcp_time_axis': _time_axis,
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

    # Mark complete
    _set_progress(pk, 'Complete', 100, status_val='done')

    return Response(analysis)


def analysis_status(request, pk):
    """
    GET /api/analyze/<pk>/status/

    Returns a Server-Sent Events stream that emits progress JSON objects until
    the analysis completes or errors out.

    Each SSE frame looks like:
        data: {"stage": "Shruti Clustering", "percent": 35, "status": "running"}

    The stream ends with a 'done' or 'error' event and closes.
    """
    def _event_stream():
        max_wait_seconds = 300  # safety ceiling
        elapsed = 0
        poll_interval = 0.8  # seconds between polls

        # Emit an initial heartbeat so the browser knows the connection is live
        yield _sse_message({'stage': 'Queued', 'percent': 0, 'status': 'running'})

        while elapsed < max_wait_seconds:
            prog = _get_progress(pk)

            if prog is None:
                # Analysis hasn't started yet — keep waiting
                yield _sse_message({'stage': 'Queued', 'percent': 0, 'status': 'running'})
            else:
                yield _sse_message(prog)

                if prog['status'] in ('done', 'error'):
                    break

            time.sleep(poll_interval)
            elapsed += poll_interval

        # Stream closed — delete the progress file after a short delay so
        # late subscribers can still read the final state.
        def _cleanup():
            time.sleep(10)
            _delete_progress(pk)

        threading.Thread(target=_cleanup, daemon=True).start()

    response = StreamingHttpResponse(
        _event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # disable Nginx buffering
    return response

import os
import json
import time
import threading
import tempfile
from pathlib import Path

import numpy as np
from django.conf import settings
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
# Matrix offload helpers
# ---------------------------------------------------------------------------

MATRICES_SUBDIR = 'analysis_matrices'
_MAX_PCP_COLS = 500      # max time-columns kept in the PCP heatmap slice


def _matrices_root() -> Path:
    """Return (and create) the directory where .npz files are stored."""
    root = Path(settings.MEDIA_ROOT) / MATRICES_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _npz_rel_path(recording_id: int) -> str:
    """Relative path (to MEDIA_ROOT) for a recording's .npz file."""
    return f'{MATRICES_SUBDIR}/{recording_id}_matrices.npz'


def _save_matrices(recording_id: int, features: dict) -> str:
    """
    Compress heavy arrays to disk with numpy's savez_compressed.

    Arrays saved
    ------------
    spectrogram   : (n_fft_bins, n_frames) float32 — dB spectrogram
    mfcc          : (13, n_frames)          float32
    chroma        : (22, n_frames)          float32
    pcp_full      : (22, n_frames)          float32 — full resolution PCP
    pcp_ds        : (22, n_cols_ds)         float32 — downsampled PCP slice
    f0_track      : (n_frames,)             float64 — NaN for unvoiced

    Returns the relative path string stored on the model.
    """
    pcp_raw: np.ndarray = features['pcp']                 # (22, n_frames)
    n_frames = pcp_raw.shape[1]

    if n_frames > _MAX_PCP_COLS:
        step = n_frames // _MAX_PCP_COLS
        pcp_ds = pcp_raw[:, ::step][:, :_MAX_PCP_COLS]
    else:
        pcp_ds = pcp_raw

    # f0 NaN-safe: keep as float64 array (NaN serialises back cleanly)
    f0_arr = np.array(features['f0'], dtype=np.float64)   # (n_frames,)

    rel = _npz_rel_path(recording_id)
    full_path = Path(settings.MEDIA_ROOT) / rel
    full_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        str(full_path),
        spectrogram=features['spectrogram'].astype(np.float32),
        mfcc=features['mfcc'].astype(np.float32),
        chroma=features['chroma'].astype(np.float32),
        pcp_full=pcp_raw.astype(np.float32),
        pcp_ds=pcp_ds.astype(np.float32),
        f0_track=f0_arr,
    )
    return rel


def _load_matrices(rel_path: str) -> dict | None:
    """
    Load the .npz file and return a dict of arrays.
    Returns None if the file is missing (graceful degradation).
    """
    full_path = Path(settings.MEDIA_ROOT) / rel_path
    if not full_path.exists():
        return None
    data = np.load(str(full_path), allow_pickle=False)
    return {k: data[k] for k in data.files}


def _build_pcp_time_axis(pcp_ds: np.ndarray, pcp_full_ncols: int) -> list[float]:
    hop_sec = 512 / 22050
    step = max(pcp_full_ncols // _MAX_PCP_COLS, 1)
    n_cols = pcp_ds.shape[1]
    return [round(i * hop_sec * step, 3) for i in range(n_cols)]


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
        fd, tmp = tempfile.mkstemp(dir=_PROGRESS_DIR, suffix='.json.tmp')
        try:
            with os.fdopen(fd, 'w') as fh:
                fh.write(payload)
            os.replace(tmp, dest)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def _get_progress(pk: int) -> dict | None:
    path = _progress_path(pk)
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _delete_progress(pk: int) -> None:
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
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Response builder — shared by analyze_audio and recording_detail
# ---------------------------------------------------------------------------

def _build_analysis_response(recording: 'AudioRecording') -> dict | None:
    """
    Reconstruct the full analysis JSON that the React/Plotly frontend expects.

    Loads lightweight scalar metadata from the DB and heavy arrays from the
    .npz file on disk.  Returns None when the recording is not yet analysed.
    """
    if not recording.is_analyzed:
        return None

    metadata = recording.analysis_metadata or {}

    # ── Try new slim storage first ────────────────────────────────────────────
    if recording.matrices_file:
        arrays = _load_matrices(recording.matrices_file)
    else:
        arrays = None

    # ── Fall back to legacy monolithic JSON when arrays are still inlined ─────
    if arrays is None and recording.analysis_result:
        # Old format: everything is already in analysis_result
        return recording.analysis_result

    if arrays is None:
        # Analysis exists but .npz is missing — return metadata-only gracefully
        return metadata

    # ── Reconstruct expected response structure ───────────────────────────────
    # Guard against legacy .npz files that were offloaded before the new
    # _save_matrices schema added pcp_ds / pcp_full / f0_track.

    response: dict = {**metadata}

    # Spectrogram / MFCC / Chroma — present in all .npz versions
    if 'spectrogram' in arrays:
        response['spectrogram_data'] = arrays['spectrogram'].tolist()
    if 'mfcc' in arrays:
        response['mfcc_data'] = arrays['mfcc'].tolist()
    if 'chroma' in arrays:
        response['chroma_data'] = arrays['chroma'].tolist()

    # PCP heatmap — new-format files have pcp_ds + pcp_full
    if 'pcp_ds' in arrays and 'pcp_full' in arrays:
        pcp_ds: np.ndarray = arrays['pcp_ds']
        pcp_full_ncols: int = int(arrays['pcp_full'].shape[1])
        response['pcp_data'] = pcp_ds.tolist()
        response['pcp_time_axis'] = _build_pcp_time_axis(pcp_ds, pcp_full_ncols)
    elif 'pcp_ds' in arrays:
        pcp_ds = arrays['pcp_ds']
        response['pcp_data'] = pcp_ds.tolist()
        response['pcp_time_axis'] = _build_pcp_time_axis(pcp_ds, pcp_ds.shape[1])
    elif 'chroma' in arrays and arrays['chroma'].shape[0] == 22:
        # Legacy offload: the 22-bin PCP was stored as 'chroma' in older runs.
        # Downsample to at most _MAX_PCP_COLS columns for frontend performance.
        pcp_raw: np.ndarray = arrays['chroma']   # (22, n_frames)
        n_frames = pcp_raw.shape[1]
        if n_frames > _MAX_PCP_COLS:
            step = n_frames // _MAX_PCP_COLS
            pcp_ds_legacy = pcp_raw[:, ::step][:, :_MAX_PCP_COLS]
        else:
            pcp_ds_legacy = pcp_raw
        response['pcp_data'] = pcp_ds_legacy.tolist()
        response['pcp_time_axis'] = _build_pcp_time_axis(pcp_ds_legacy, n_frames)
    else:
        # Final fallback: synthesise a single-column PCP from mean_pcp scalar in metadata
        mean_pcp = metadata.get('mean_pcp')
        if mean_pcp is not None:
            response['pcp_data'] = [[v] for v in mean_pcp]
            response['pcp_time_axis'] = [0.0]

    # F0 track — absent in legacy offloaded files
    if 'f0_track' in arrays:
        f0_arr: np.ndarray = arrays['f0_track']
        response['f0_track'] = [
            None if np.isnan(v) else round(float(v), 3) for v in f0_arr
        ]
    else:
        response['f0_track'] = []

    return response


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

    base = AudioRecordingSerializer(recording).data

    # Attach full analysis payload (matrices loaded from disk) if available
    if recording.is_analyzed:
        base['analysis_result'] = _build_analysis_response(recording)

    return Response(base)


@api_view(['POST'])
def analyze_audio(request, pk):
    """Run the ML pipeline, offloading heavy matrices to disk."""
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

    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── Save heavy arrays to compressed .npz on disk ──────────────────────────
    rel_path = _save_matrices(pk, features)

    # ── Build slim metadata dict (scalars only — no matrices) ─────────────────
    metadata = {
        # Shruti clustering scalars
        'shruti_clusters':                  clustering_results['shruti_clusters'],
        'freq_assignments':                 clustering_results['freq_assignments'],
        'mean_pcp':                         clustering_results['mean_pcp'],
        # pYIN scalars
        'voiced_ratio':                     features['voiced_ratio'],
        'spectral_centroid_timeline':       features['spectral_centroid'].tolist(),
        # Ghana Patha scalars
        'ghana_patha_valid':                ghana_result['is_valid'],
        'ghana_patha_confidence':           ghana_result['confidence'],
        'ghana_patha_repetition_score':     ghana_result.get('repetition_score', 0.0),
        'ghana_patha_n_segments':           ghana_result.get('n_segments', 0),
        'ghana_patha_segments':             ghana_result.get('segments', []),
        'ghana_patha_detected_pattern':     ghana_result.get('detected_pattern', []),
        'ghana_patha_dtw_details':          ghana_result.get('dtw_details'),
        # Raga detection (structured dict — already compact)
        'raga_detection':                   raga_result,
        # Audio-level scalars
        'tempo':                            features['tempo'],
        'duration':                         features['duration'],
    }

    # ── Persist to DB (no matrices — just path + scalars) ─────────────────────
    recording.analysis_metadata = metadata
    recording.matrices_file = rel_path
    recording.analysis_result = None   # clear any legacy blob to free DB space
    recording.is_analyzed = True
    recording.save()

    _set_progress(pk, 'Complete', 100, status_val='done')

    # ── Return the full response (matrices loaded back for this request) ───────
    # On subsequent GET requests _build_analysis_response() does the same.
    pcp_raw: np.ndarray = features['pcp']
    n_frames = pcp_raw.shape[1]
    if n_frames > _MAX_PCP_COLS:
        step = n_frames // _MAX_PCP_COLS
        pcp_ds = pcp_raw[:, ::step][:, :_MAX_PCP_COLS]
    else:
        pcp_ds = pcp_raw

    hop_sec = 512 / 22050
    orig_step = max(n_frames // _MAX_PCP_COLS, 1)
    time_axis = [round(i * hop_sec * orig_step, 3) for i in range(pcp_ds.shape[1])]

    f0_track = [
        None if np.isnan(v) else round(float(v), 3)
        for v in features['f0']
    ]

    analysis = {
        **metadata,
        'pcp_data':          pcp_ds.tolist(),
        'pcp_time_axis':     time_axis,
        'f0_track':          f0_track,
        'spectrogram_data':  features['spectrogram'].tolist(),
        'mfcc_data':         features['mfcc'].tolist(),
        'chroma_data':       features['chroma'].tolist(),
    }

    return Response(analysis)


def analysis_status(request, pk):
    """
    GET /api/analyze/<pk>/status/

    Returns a Server-Sent Events stream that emits progress JSON objects until
    the analysis completes or errors out.
    """
    def _event_stream():
        max_wait_seconds = 300
        elapsed = 0
        poll_interval = 0.8

        yield _sse_message({'stage': 'Queued', 'percent': 0, 'status': 'running'})

        while elapsed < max_wait_seconds:
            prog = _get_progress(pk)

            if prog is None:
                yield _sse_message({'stage': 'Queued', 'percent': 0, 'status': 'running'})
            else:
                yield _sse_message(prog)

                if prog['status'] in ('done', 'error'):
                    break

            time.sleep(poll_interval)
            elapsed += poll_interval

        def _cleanup():
            time.sleep(10)
            _delete_progress(pk)

        threading.Thread(target=_cleanup, daemon=True).start()

    response = StreamingHttpResponse(
        _event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

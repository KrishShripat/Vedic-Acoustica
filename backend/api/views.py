import os
import json
import time
import threading
import tempfile
from pathlib import Path

import numpy as np
from django.conf import settings
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import AnonRateThrottle

from .models import AudioRecording
from .serializers import AudioRecordingSerializer


# ---------------------------------------------------------------------------
# Per-endpoint throttle classes
#
# Two custom subclasses override `scope` so DRF looks up their individual
# rate limits from REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] in settings.py:
#
#   UploadAnonThrottle  → 'upload_anon'  → 10 req/hour
#   AnalyzeAnonThrottle → 'analyze_anon' → 10 req/hour
#
# The default AnonRateThrottle (scope='anon', 60/min) is applied globally
# via DEFAULT_THROTTLE_CLASSES and covers all other endpoints.
# ---------------------------------------------------------------------------

class UploadAnonThrottle(AnonRateThrottle):
    """Strict per-IP rate limit on audio file uploads (disk + bandwidth cost)."""
    scope = 'upload_anon'


class AnalyzeAnonThrottle(AnonRateThrottle):
    """Strict per-IP rate limit on ML analysis triggers (CPU + memory cost)."""
    scope = 'analyze_anon'


class StatusAnonThrottle(AnonRateThrottle):
    """Anon throttle for the SSE status view (safe with raw HttpRequest)."""
    scope = 'anon'

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


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
    Returns None if the path is invalid, escapes analysis_matrices,
    or if the file is missing (graceful degradation).
    """
    if not rel_path:
        return None

    matrices_root = _matrices_root().resolve()
    try:
        full_path = (Path(settings.MEDIA_ROOT) / rel_path).resolve()
    except (ValueError, RuntimeError):
        return None

    # Enforce strict path confinement within analysis_matrices directory
    if not full_path.is_relative_to(matrices_root) or full_path == matrices_root:
        return None

    if not full_path.is_file():
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

# Single global lock — progress writes are infrequent and non-contended
# in practice (one ML pipeline per recording at a time).  An unbounded
# per-PK dict would grow indefinitely with thousands of analyses.
_PROGRESS_LOCK = threading.Lock()

_PROGRESS_DIR = os.environ.get(
    'VEDIC_PROGRESS_DIR',
    os.path.join(settings.MEDIA_ROOT, 'progress'),
)
os.makedirs(_PROGRESS_DIR, exist_ok=True)


def _progress_path(pk: int) -> str:
    return os.path.join(_PROGRESS_DIR, f'vedic_progress_{pk}.json')




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
    with _PROGRESS_LOCK:
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
@throttle_classes([UploadAnonThrottle])
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
    """
    GET /api/recordings/

    Returns a paginated list of all recordings, ordered newest first.

    Query parameters
    ----------------
    page      : int  — page number (default: 1)
    page_size : int  — items per page (default: 20, max: 100)

    Response envelope
    -----------------
    {
        "count":    <total items>,
        "next":     <url | null>,
        "previous": <url | null>,
        "results":  [ ... ]
    }
    """
    from rest_framework.pagination import PageNumberPagination  # noqa: PLC0415

    paginator = PageNumberPagination()
    paginator.page_size = 20
    paginator.page_size_query_param = 'page_size'
    paginator.max_page_size = 100

    qs = AudioRecording.objects.all().order_by('-uploaded_at')
    page = paginator.paginate_queryset(qs, request)
    serializer = AudioRecordingSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)



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
@throttle_classes([AnalyzeAnonThrottle])
def analyze_audio(request, pk):
    """
    POST /api/analyze/<pk>/

    Enqueues the ML analysis pipeline as a Celery background task and
    returns HTTP 202 Accepted immediately so the request thread is never
    blocked.  The React frontend should then subscribe to:

        GET /api/analyze/<pk>/status/   (SSE stream)

    and fetch the full analysis result via:

        GET /api/recordings/<pk>/       (once status == 'done')
    """
    # Import here (not at module top) to avoid loading Celery when Django
    # starts in contexts where Celery is not configured (e.g. manage.py check).
    from .tasks import process_audio_task  # noqa: PLC0415

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

    # Write an initial progress record so the SSE stream has something to
    # read immediately, even before the Celery worker picks up the task.
    _set_progress(pk, 'Queued', 0, status_val='running')

    # Dispatch to the background worker — this call returns almost instantly.
    process_audio_task.delay(recording.id)

    return Response(
        {
            'status':       'queued',
            'recording_id': recording.id,
            'message':      'Analysis queued. Subscribe to the /status/ SSE stream for progress.',
        },
        status=status.HTTP_202_ACCEPTED,
    )



@csrf_exempt
@require_GET
def analysis_status(request, pk):
    """
    SSE view — intentionally bypasses DRF for StreamingHttpResponse.
    Throttle is enforced manually: we instantiate the global AnonRateThrottle
    and call allow_request() before entering the streaming generator.
    A 429 response is returned immediately if the per-IP limit is exceeded.
    """
    throttle = StatusAnonThrottle()
    if not throttle.allow_request(request, None):
        from django.http import HttpResponse  # noqa: PLC0415
        retry_after = throttle.wait()
        resp = HttpResponse(
            'Too Many Requests',
            status=429,
            content_type='text/plain',
        )
        if retry_after is not None:
            resp['Retry-After'] = str(int(retry_after))
        return resp

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

        # Progress file cleanup is deferred: the next POST /analyze/<pk>/
        # overwrites the file, and a periodic management command can purge
        # stale ones.  A daemon thread sleeping here risks deleting the file
        # from under a reconnecting client or being silently killed on
        # Gunicorn worker shutdown, leaving orphan files either way.

    response = StreamingHttpResponse(
        _event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

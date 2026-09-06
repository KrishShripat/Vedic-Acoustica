"""
api/tasks.py — Celery background tasks for Vedic Acoustica.

The ``process_audio_task`` function contains the full 4-stage ML pipeline
that was previously executed synchronously inside the ``analyze_audio`` view.
Moving it here frees the Django request thread immediately; the React
frontend tracks progress via the existing SSE endpoint (``/api/analyze/<pk>/status/``).

SSE progress bridge
-------------------
Tasks write atomic progress snapshots to the file-based store defined in
``api/views.py`` (``_set_progress`` / ``_get_progress``).  The SSE stream
view polls that same store, so no additional infrastructure is needed — the
progress flow is identical to the old synchronous path.
"""

import os
import time

import redis as redislib
from celery import shared_task
from django.conf import settings

# Re-use the progress helpers and matrix helpers from views.py so there
# is a single source of truth for file paths and progress semantics.
from api.views import (
    _set_progress,
    _save_matrices,
    _build_playback_file,
)
from api.models import AudioRecording
from ml_engine.audio_processing import extract_features
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga


@shared_task(bind=True, max_retries=2, name='api.tasks.build_playback_file_task')
def build_playback_file_task(self, recording_id: int) -> bool:
    """
    Transcode the uploaded audio to an MP3 playback file in the background.

    The ffmpeg transcode used to run synchronously inside the upload request,
    racing gunicorn's ``--timeout 120`` — a slow transcode killed the worker
    mid-request and the client got a 502 even though the upload itself had
    succeeded.  Running it here frees the request thread entirely.

    ``max_retries=2`` gives ffmpeg two retries before the task is marked
    FAILURE (worst case the playback file is simply missing and the frontend
    falls back to the raw audio — ``_build_playback_file`` already swallows
    ffmpeg errors).
    """
    recording = AudioRecording.objects.get(pk=recording_id)
    _build_playback_file(recording)
    return True


def _record_ml_metrics(conn: redislib.Redis, status: str, seconds: float | None = None) -> None:
    """
    Record an analysis outcome for the /metrics bridge (see api/metrics.py).

    The Celery worker is a separate process from gunicorn, so it cannot append
    directly to the /metrics output.  These keys are read by
    ``metrics._bridge_worker_metrics()`` on every scrape.  Best-effort only.
    """
    try:
        if status == 'ok' and seconds is not None:
            conn.set('vedic:metrics:ml_last_seconds', seconds, ex=3600)
        conn.incr(f'vedic:metrics:ml_analyses_{status}')
    except redislib.RedisError:
        pass


def _run_pipeline(pk: int) -> dict:
    """
    Run the full ML analysis pipeline for *pk* in the background.

    Stages
    ------
    1. Feature Extraction  (pYIN F0, spectrogram, MFCC, PCP)
    2. Shruti Clustering   (K=22 clustering against canonical Shruti freqs)
    3. Ghana Patha Validation (DTW-based recitation pattern validation)
    4. Raga Detection      (directional scoring against raga database)

    On success
        • Heavy arrays are saved to ``MEDIA_ROOT/analysis_matrices/<pk>_matrices.npz``
        • Scalar metadata is written to ``AudioRecording.analysis_metadata``
        • ``AudioRecording.is_analyzed`` is set to ``True``
        • Progress file is marked ``done``

    On failure
        • Progress file is marked ``error`` with the exception message
        • ``AudioRecording.is_analyzed`` remains ``False``
        • The exception is re-raised so Celery marks the task as FAILURE

    Returns a minimal dict summary (available via ``AsyncResult.result``).
    """
    # ── Fetch recording ────────────────────────────────────────────────────────
    try:
        recording = AudioRecording.objects.get(pk=pk)
    except AudioRecording.DoesNotExist:
        _set_progress(pk, 'Error', 0, status_val='error',
                      error=f'Recording {pk} does not exist.')
        raise

    audio_path = recording.audio_file.path

    if not os.path.exists(audio_path):
        msg = f'Audio file not found on disk: {audio_path}'
        _set_progress(pk, 'Error', 0, status_val='error', error=msg)
        raise FileNotFoundError(msg)

    # ── Stage 1: Feature Extraction ────────────────────────────────────────────
    try:
        _set_progress(pk, 'Feature Extraction', 5)
        features = extract_features(
            audio_path,
            progress_cb=lambda pct, detail: _set_progress(
                pk, 'Feature Extraction', pct, detail=detail,
            ),
        )
        _set_progress(pk, 'Feature Extraction', 30)
    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        raise

    # ── Stage 2: Shruti Clustering ─────────────────────────────────────────────
    try:
        _set_progress(pk, 'Shruti Clustering', 35)
        clustering_results = run_clustering(features)
        _set_progress(pk, 'Shruti Clustering', 60)
    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        raise

    # ── Stage 3: Ghana Patha Validation ───────────────────────────────────────
    try:
        _set_progress(pk, 'Ghana Patha Validation', 65)
        ghana_result = validate_ghana_patha(features)
        _set_progress(pk, 'Ghana Patha Validation', 80)
    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        raise

    # ── Stage 4: Raga Detection ────────────────────────────────────────────────
    try:
        _set_progress(pk, 'Raga Detection', 85)
        raga_result = detect_raga(clustering_results, features=features)
        _set_progress(pk, 'Raga Detection', 98)
    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        raise

    # ── Save heavy arrays to compressed .npz on disk + persist to DB ──────────
    # Any failure here (disk full, DB error) must still surface as a terminal
    # 'error' progress state so the SSE stream doesn't hang at 'running'.
    try:
        rel_path = _save_matrices(pk, features)

        # ── Build slim metadata dict (scalars only — no matrices) ─────────────
        metadata = {
            # Shruti clustering scalars
            'shruti_clusters':              clustering_results['shruti_clusters'],
            # freq_assignments intentionally omitted — per-frame strings, consumed by nothing
            'mean_pcp':                     clustering_results['mean_pcp'],
            # pYIN scalars
            'voiced_ratio':                 features['voiced_ratio'],
            # spectral_centroid_timeline intentionally omitted — per-frame floats, unused
            # Ghana Patha scalars
            'ghana_patha_valid':            ghana_result['is_valid'],
            'ghana_patha_confidence':       ghana_result['confidence'],
            'ghana_patha_repetition_score': ghana_result.get('repetition_score', 0.0),
            'ghana_patha_n_segments':       ghana_result.get('n_segments', 0),
            'ghana_patha_segments':         ghana_result.get('segments', []),
            'ghana_patha_detected_pattern': ghana_result.get('detected_pattern', []),
            # Word-level expected sequence (flattened GHANA_PATTERNS['simple'])
            'ghana_patha_expected_sequence': [
                w for turn in ghana_result.get('expected_pattern_legacy',
                                                [[1,2],[2,1],[1,2,3],[3,2,1],[1,2,3]])
                for w in turn
            ],
            # Phrase-level direction cycle (forward/reverse per phase)
            'ghana_patha_expected_cycle':    ghana_result.get('expected_pattern', []),
            'ghana_patha_dtw_details':      ghana_result.get('dtw_details'),
            # Raga detection (structured dict — already compact)
            'raga_detection':               raga_result,
            # Audio-level scalars
            'tempo':                        features['tempo'],
            'duration':                     features['duration'],
        }

        # ── Persist to DB (no matrices — just path + scalars) ─────────────────
        recording.analysis_metadata = metadata
        recording.matrices_file = rel_path
        recording.analysis_result = None   # clear any legacy blob to free DB space
        recording.is_analyzed = True
        recording.save(update_fields=[
            'analysis_metadata', 'matrices_file', 'analysis_result', 'is_analyzed',
        ])
    except Exception as exc:
        _set_progress(pk, 'Error', 0, status_val='error', error=str(exc))
        raise

    # ── Signal the SSE stream that processing is complete ─────────────────────
    _set_progress(pk, 'Complete', 100, status_val='done')

    # Terminal state reached — purge the progress file (the next analyze call
    # re-creates it before dispatch, and the SSE reader is done).
    try:
        from api.views import _delete_progress  # noqa: PLC0415
        _delete_progress(pk)
    except Exception:  # pragma: no cover — cleanup is best-effort
        pass

    return {'recording_id': pk, 'matrices_file': rel_path}


@shared_task(bind=True, max_retries=0, name='api.tasks.process_audio_task')
def process_audio_task(self, recording_id: int) -> dict:
    """
    Single-flight wrapper around ``_run_pipeline``.

    ACKS_LATE re-delivers a task if a worker crashes mid-run, but ``max_retries``
    does NOT prevent a duplicate broker redelivery, and a double-click on
    "Analyze" dispatches two independent tasks for the same recording.  Both
    would otherwise write the same progress file and call ``recording.save()``
    (SQLite is the single writer — last-writer-wins, progress can regress).
    A Redis ``SETNX`` lock (Redis is already the broker → zero new infra)
    guarantees only one analysis of a recording ever runs concurrently.
    """
    pk = recording_id

    # ── Single-flight fence: never run two analyses of the same recording ──
    lock_key = f'vedic:analyze:lock:{pk}'
    redis_conn = redislib.Redis.from_url(settings.CELERY_BROKER_URL)
    if not redis_conn.set(lock_key, '1', nx=True, ex=3600):
        _set_progress(pk, 'Queued', 0, status_val='error',
                      error='An analysis for this recording is already running.')
        return {'recording_id': pk, 'skipped': True}
    try:
        start = time.perf_counter()
        try:
            result = _run_pipeline(pk)
            _record_ml_metrics(redis_conn, 'ok', time.perf_counter() - start)
            return result
        except Exception:
            _record_ml_metrics(redis_conn, 'error')
            raise
    finally:
        try:
            redis_conn.delete(lock_key)
        except redislib.RedisError:
            pass

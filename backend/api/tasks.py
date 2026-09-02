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

import numpy as np
from celery import shared_task
from django.conf import settings
from pathlib import Path

# Re-use the progress helpers and matrix helpers from views.py so there
# is a single source of truth for file paths and progress semantics.
from api.views import (
    _set_progress,
    _save_matrices,
    MATRICES_SUBDIR,
    _MAX_PCP_COLS,
)
from api.models import AudioRecording
from ml_engine.audio_processing import extract_features
from ml_engine.ml_engine import run_clustering
from ml_engine.ghana_patha import validate_ghana_patha
from ml_engine.raga_mapping import detect_raga


@shared_task(bind=True, max_retries=0, name='api.tasks.process_audio_task')
def process_audio_task(self, recording_id: int) -> dict:
    """
    Run the full ML analysis pipeline for *recording_id* in the background.

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
    pk = recording_id

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
        features = extract_features(audio_path)
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

    # ── Save heavy arrays to compressed .npz on disk ──────────────────────────
    rel_path = _save_matrices(pk, features)

    # ── Build slim metadata dict (scalars only — no matrices) ─────────────────
    metadata = {
        # Shruti clustering scalars
        'shruti_clusters':              clustering_results['shruti_clusters'],
        'freq_assignments':             clustering_results['freq_assignments'],
        'mean_pcp':                     clustering_results['mean_pcp'],
        # pYIN scalars
        'voiced_ratio':                 features['voiced_ratio'],
        'spectral_centroid_timeline':   features['spectral_centroid'].tolist(),
        # Ghana Patha scalars
        'ghana_patha_valid':            ghana_result['is_valid'],
        'ghana_patha_confidence':       ghana_result['confidence'],
        'ghana_patha_repetition_score': ghana_result.get('repetition_score', 0.0),
        'ghana_patha_n_segments':       ghana_result.get('n_segments', 0),
        'ghana_patha_segments':         ghana_result.get('segments', []),
        'ghana_patha_detected_pattern': ghana_result.get('detected_pattern', []),
        'ghana_patha_dtw_details':      ghana_result.get('dtw_details'),
        # Raga detection (structured dict — already compact)
        'raga_detection':               raga_result,
        # Audio-level scalars
        'tempo':                        features['tempo'],
        'duration':                     features['duration'],
    }

    # ── Persist to DB (no matrices — just path + scalars) ─────────────────────
    recording.analysis_metadata = metadata
    recording.matrices_file = rel_path
    recording.analysis_result = None   # clear any legacy blob to free DB space
    recording.is_analyzed = True
    recording.save(update_fields=[
        'analysis_metadata', 'matrices_file', 'analysis_result', 'is_analyzed',
    ])

    # ── Signal the SSE stream that processing is complete ─────────────────────
    _set_progress(pk, 'Complete', 100, status_val='done')

    return {'recording_id': pk, 'matrices_file': rel_path}

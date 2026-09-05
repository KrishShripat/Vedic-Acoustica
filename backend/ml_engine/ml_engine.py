import numpy as np
from sklearn.cluster import KMeans
from .shruti_mapping import SHRUTI_FREQUENCIES, SHRUTI_NAMES, assign_shruti
from .audio_processing import _SHRUTI_FREQS_ARR, _THRESHOLD_CENTS

N_CLUSTERS = 22


def _nearest_shruti_from_f0(f0_hz):
    """
    Return the index (0-based) of the closest Shruti to a given Hz value,
    using log-frequency (cents) distance instead of absolute Hz distance.
    Returns None when f0_hz is NaN, zero, or outside the threshold.
    """
    if f0_hz is None or np.isnan(f0_hz) or f0_hz <= 0:
        return None
    with np.errstate(divide='ignore', invalid='ignore'):
        cents = np.abs(1200.0 * np.log2(f0_hz / _SHRUTI_FREQS_ARR))
    best = int(np.argmin(cents))
    return best if cents[best] < _THRESHOLD_CENTS else None


def run_clustering(features):
    mfcc = features['mfcc']
    chroma = features['chroma']

    mfcc_flat = mfcc.T
    chroma_flat = chroma.T

    combined = np.hstack([mfcc_flat, chroma_flat])

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    labels = kmeans.fit_predict(combined)

    shruti_clusters = {}
    for cluster_id in range(N_CLUSTERS):
        frame_indices = np.where(labels == cluster_id)[0]
        shruti_clusters[f'shruti_{cluster_id + 1}'] = {
            'frame_count': int(len(frame_indices)),
            'centroid': kmeans.cluster_centers_[cluster_id].tolist(),
            'assigned_shruti': assign_shruti(
                kmeans.cluster_centers_[cluster_id], features,
                cluster_frames=frame_indices,
            ),
        }

    # ── Per-frame Shruti assignment (pYIN F0 preferred, PCP fallback) ────────
    pcp = features['pcp']                         # (22, n_frames)
    mean_pcp = features['mean_pcp']               # (22,)
    f0 = features.get('f0')                       # (n_f0,) or None
    voiced_flag = features.get('voiced_flag')     # (n_f0,) bool or None

    n_frames = pcp.shape[1]
    freq_assignments = []

    # PCP argmax as base assignment for every frame
    pcp_argmax = np.argmax(pcp, axis=0)           # (n_frames,)

    for frame_idx in range(n_frames):
        assigned = None

        # Prefer pYIN F0 for voiced frames — no harmonic ambiguity
        if (f0 is not None and voiced_flag is not None
                and frame_idx < len(f0)
                and bool(voiced_flag[frame_idx])):
            shruti_idx = _nearest_shruti_from_f0(f0[frame_idx])
            if shruti_idx is not None:
                assigned = SHRUTI_NAMES[shruti_idx]

        # Fall back to PCP argmax for unvoiced / out-of-range frames
        if assigned is None:
            assigned = SHRUTI_NAMES[int(pcp_argmax[frame_idx])]

        freq_assignments.append(assigned)

    return {
        'shruti_clusters': shruti_clusters,
        'labels': labels.tolist(),
        'freq_assignments': freq_assignments,
        'mean_pcp': mean_pcp.tolist(),            # 22 floats in [0, 1]
    }

import numpy as np
from sklearn.cluster import KMeans
from .shruti_mapping import SHRUTI_FREQUENCIES, assign_shruti

N_CLUSTERS = 22


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
                kmeans.cluster_centers_[cluster_id], features
            ),
        }

    dominant_freqs = features['dominant_frequencies']
    freq_assignments = [assign_shruti_freq(f) for f in dominant_freqs]

    return {
        'shruti_clusters': shruti_clusters,
        'dominant_frequencies': dominant_freqs,
        'labels': labels.tolist(),
        'freq_assignments': freq_assignments,
    }


def assign_shruti_freq(frequency):
    if frequency <= 0:
        return None
    min_diff = float('inf')
    closest = None
    for shruti_name, shruti_freq in SHRUTI_FREQUENCIES.items():
        diff = abs(frequency - shruti_freq)
        if diff < min_diff:
            min_diff = diff
            closest = shruti_name
    return closest

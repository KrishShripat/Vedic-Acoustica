import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity


GHANA_PATTERNS = {
    'simple': [[1, 2], [2, 1], [1, 2, 3], [3, 2, 1], [1, 2, 3]],
}


def validate_ghana_patha(features):
    chroma = features['chroma']
    mfcc = features['mfcc']
    sr = features['sr']
    hop_length = 512
    total_duration = features['duration']

    if total_duration < 2.0:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': 'Audio too short for Ghana Patha analysis',
            'segments': [],
            'repetition_score': 0.0,
            'self_similarity': 0.0,
        }

    repetition_score, similarity_matrix, n_segments = compute_repetition_score(
        mfcc, chroma, sr, hop_length
    )

    pattern_labels = detect_phrase_pattern(mfcc, chroma, n_segments)

    ghana_match = check_ghana_pattern(pattern_labels)

    self_similarity = float(np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]))

    is_valid = repetition_score > 0.4 and ghana_match['confidence'] > 0.3

    combined_confidence = round(
        0.5 * repetition_score + 0.5 * ghana_match['confidence'], 4
    )

    segments = []
    for i, label in enumerate(pattern_labels):
        segments.append({
            'index': i,
            'cluster_label': int(label),
        })

    return {
        'is_valid': is_valid,
        'confidence': combined_confidence,
        'detected_pattern': pattern_labels,
        'expected_pattern': GHANA_PATTERNS['simple'],
        'segments': segments,
        'repetition_score': round(repetition_score, 4),
        'self_similarity': round(self_similarity, 4),
        'n_segments': n_segments,
    }


def compute_repetition_score(mfcc, chroma, sr, hop_length):
    combined = np.vstack([mfcc, chroma]).T

    n_frames = combined.shape[0]
    segment_frames = max(sr // hop_length, 1)
    n_segments = max(n_frames // segment_frames, 1)

    segment_features = []
    for i in range(n_segments):
        start = i * segment_frames
        end = min(start + segment_frames, n_frames)
        seg = combined[start:end]
        segment_features.append(np.mean(seg, axis=0))

    segment_features = np.array(segment_features)

    sim_matrix = cosine_similarity(segment_features)

    n = len(segment_features)
    if n < 2:
        return 0.0, sim_matrix, n

    off_diagonal = []
    for i in range(n):
        for j in range(i + 2, n):
            off_diagonal.append(sim_matrix[i, j])

    if not off_diagonal:
        return 0.0, sim_matrix, n

    off_diagonal = np.array(off_diagonal)
    high_sim_count = np.sum(off_diagonal > 0.7)
    total_pairs = len(off_diagonal)

    repetition_score = high_sim_count / total_pairs if total_pairs > 0 else 0.0

    return repetition_score, sim_matrix, n


def detect_phrase_pattern(mfcc, chroma, n_segments):
    combined = np.vstack([mfcc, chroma]).T
    n_frames = combined.shape[0]
    segment_frames = max(n_frames // n_segments, 1)

    segment_features = []
    for i in range(n_segments):
        start = i * segment_frames
        end = min(start + segment_frames, n_frames)
        seg = combined[start:end]
        segment_features.append(np.mean(seg, axis=0))

    if len(segment_features) < 3:
        return []

    n_clusters = min(3, len(segment_features))
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(
        np.array(segment_features)
    )

    return labels.tolist()


def check_ghana_pattern(detected_pattern):
    if not detected_pattern or len(detected_pattern) < 3:
        return {'is_valid': False, 'confidence': 0.0, 'segments': []}

    scores = []

    for pattern_name, expected in GHANA_PATTERNS.items():
        flat_expected = [item for sublist in expected for item in sublist]

        score = compute_pattern_similarity(detected_pattern, flat_expected)

        alt_score = compute_repetition_based_score(detected_pattern)

        combined = 0.5 * score + 0.5 * alt_score
        scores.append((pattern_name, combined))

    best_match = max(scores, key=lambda x: x[1])
    pattern_name, score = best_match

    return {
        'is_valid': score > 0.3,
        'confidence': round(score, 4),
        'matched_pattern': pattern_name,
    }


def compute_pattern_similarity(detected, expected):
    min_len = min(len(detected), len(expected))
    if min_len == 0:
        return 0.0

    detected_trimmed = detected[:min_len]
    expected_trimmed = expected[:min_len]

    matches = sum(1 for d, e in zip(detected_trimmed, expected_trimmed) if d == e)
    return matches / min_len


def compute_repetition_based_score(pattern):
    if len(pattern) < 4:
        return 0.0

    unique_labels = set(pattern)
    n_unique = len(unique_labels)

    if n_unique < 2:
        return 0.1

    repeat_count = 0
    total_transitions = len(pattern) - 1

    for i in range(1, len(pattern)):
        if pattern[i] == pattern[i - 1]:
            repeat_count += 1

    back_count = 0
    for i in range(2, len(pattern)):
        if pattern[i] == pattern[i - 2]:
            back_count += 1

    repeat_ratio = repeat_count / total_transitions if total_transitions > 0 else 0
    back_ratio = back_count / (total_transitions - 1) if total_transitions > 1 else 0

    return 0.5 * repeat_ratio + 0.5 * back_ratio

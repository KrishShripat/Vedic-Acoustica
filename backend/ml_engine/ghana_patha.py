"""
ghana_patha.py — Ghana Patha validation with DTW-based pattern matching.

Ghana Patha is a complex recitation mode (Patha) where syllables are chanted
in a specific forward-backward-forward pattern.  The key challenge for
automated validation is that the same pattern can be chanted at very different
tempos — a naive frame-aligned or label-sequence comparison fails completely
when one recording is 1.5× faster than another.

Dynamic Time Warping (DTW) resolves this by finding the minimum-cost monotonic
warping path between two feature sequences, effectively stretching/compressing
the time axis of either sequence to find the best alignment.

Design
------
Feature representation
    Each phrase segment is described by its Pitch-Class Profile (PCP) sequence —
    a (22, n_frames) array of per-frame Shruti energies, already computed in
    audio_processing.py.  The PCP is used instead of raw MFCC because:
    - It is octave-invariant (useful when chanting shifts register)
    - It directly encodes Vedic Shruti relationships
    - It is already normalised to [0, 1] per frame

DTW cost metric
    Local cost = 1 − cosine_similarity(pcp_frame_a, pcp_frame_b) ∈ [0, 1].
    Total cost is normalised by the length of the warping path so that
    long-segment and short-segment comparisons are on the same scale.

Ghana pattern encoding
    GHANA_TEMPLATES maps each pattern variant to a list of reference PCP
    sequences.  We ship two templates:
    - 'forward'  — the ascending phrase (1→2→3)
    - 'reverse'  — the descending phrase (3→2→1)
    A full Ghana cycle is encoded as [fwd, rev, fwd, rev, fwd].
    Reference PCP frames are stored as idealised 22-dim unit vectors where
    energy is concentrated on the Shruti bins characterising that phrase class.

    In production these templates would be learned from annotated examples; the
    shipped templates are hand-coded approximations that capture the structural
    contrast between ascending and descending phrases well enough for scoring.
"""

import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Ghana pattern templates
# ─────────────────────────────────────────────────────────────────────────────
# Each template is a (T, 22) array of idealised PCP frames.
# T=3 frames is a symbolic minimum; the DTW path scales to any real segment.
#
# Shruti indices (0-based, matching SHRUTI_NAMES / PCP bin order):
#   0=Sa  1=Re1  2=Re2  3=Ga1  4=Ga2  5=Ga3
#   6=Ma1 7=Ma2  8=Ma3  9=TivraMa 10=Pa 11=Dha1
#   12=Dha2 13=Ni1 14=Ni2 15=Ni3 16=Re_ ...
#
# 'forward'  = ascending contour: Sa → Ga → Pa
# 'reverse'  = descending contour: Pa → Ga → Sa

def _make_template(shruti_indices_per_frame):
    """Build a (T, 22) float32 template with unit-norm PCP rows."""
    T = len(shruti_indices_per_frame)
    tpl = np.zeros((T, 22), dtype=np.float32)
    for t, indices in enumerate(shruti_indices_per_frame):
        for idx in indices:
            tpl[t, idx] = 1.0
        norm = np.linalg.norm(tpl[t])
        if norm > 0:
            tpl[t] /= norm
    return tpl

# Forward phrase: Sa – Re – Ga – Ma – Pa  (ascending, 5 keyframes)
_TPL_FORWARD = _make_template([
    [0],           # Sa
    [2, 4],        # Re / Ga region
    [4, 6],        # Ga / Ma region
    [6, 10],       # Ma / Pa region
    [10],          # Pa
])

# Reverse phrase: Pa – Ma – Ga – Re – Sa  (descending, 5 keyframes)
_TPL_REVERSE = _make_template([
    [10],          # Pa
    [6, 10],       # Ma / Pa region
    [4, 6],        # Ga / Ma region
    [2, 4],        # Re / Ga region
    [0],           # Sa
])

# Ghana cycle: fwd – rev – fwd – rev – fwd
GHANA_CYCLE = ['forward', 'reverse', 'forward', 'reverse', 'forward']
GHANA_TEMPLATES = {
    'forward': _TPL_FORWARD,
    'reverse': _TPL_REVERSE,
}

# Legacy label-list format kept for API backward-compatibility
GHANA_PATTERNS = {
    'simple': [[1, 2], [2, 1], [1, 2, 3], [3, 2, 1], [1, 2, 3]],
}

# ─────────────────────────────────────────────────────────────────────────────
# DTW core
# ─────────────────────────────────────────────────────────────────────────────

def dtw_distance(seq_a, seq_b):
    """
    Compute the normalised DTW distance between two PCP sequences.

    Parameters
    ----------
    seq_a : ndarray, shape (T_a, 22)
        Query PCP sequence.
    seq_b : ndarray, shape (T_b, 22)
        Reference PCP sequence (template).

    Returns
    -------
    norm_dist : float in [0, 1]
        DTW cost normalised by warping-path length.
        0 = identical, 1 = maximally dissimilar.
    path_length : int
        Length of the optimal warping path.
    """
    T_a, T_b = len(seq_a), len(seq_b)
    if T_a == 0 or T_b == 0:
        return 1.0, 0

    # Local cost matrix: 1 − cosine_similarity ∈ [0, 1]
    # cosine_similarity returns (T_a, T_b); clip for numerical safety
    cos_sim = cosine_similarity(seq_a, seq_b)          # (T_a, T_b)
    cost = np.clip(1.0 - cos_sim, 0.0, 1.0).astype(np.float64)

    # Accumulated cost matrix with standard DTW recurrence
    D = np.full((T_a, T_b), np.inf, dtype=np.float64)
    D[0, 0] = cost[0, 0]

    for i in range(1, T_a):
        D[i, 0] = D[i - 1, 0] + cost[i, 0]
    for j in range(1, T_b):
        D[0, j] = D[0, j - 1] + cost[0, j]

    for i in range(1, T_a):
        for j in range(1, T_b):
            D[i, j] = cost[i, j] + min(D[i - 1, j],      # insertion
                                        D[i, j - 1],      # deletion
                                        D[i - 1, j - 1])  # match

    total_cost = D[T_a - 1, T_b - 1]

    # Traceback to find path length for normalisation
    path_length = _traceback_length(D)

    norm_dist = total_cost / max(path_length, 1)
    return float(np.clip(norm_dist, 0.0, 1.0)), path_length


def _traceback_length(D):
    """Count steps along the optimal warping path (greedy traceback)."""
    i, j = D.shape[0] - 1, D.shape[1] - 1
    length = 1
    while i > 0 or j > 0:
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            step = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
            if step == 0:
                i -= 1; j -= 1
            elif step == 1:
                i -= 1
            else:
                j -= 1
        length += 1
    return length


# ─────────────────────────────────────────────────────────────────────────────
# Segment extraction
# ─────────────────────────────────────────────────────────────────────────────

def segment_pcp_sequences(pcp, sr, hop_length, n_segments):
    """
    Divide the (22, n_frames) PCP matrix into ``n_segments`` equal slices.

    Returns a list of (n_frames_seg, 22) arrays — transposed so rows are
    frames, columns are Shruti bins (the format expected by DTW).
    """
    n_frames = pcp.shape[1]
    seg_len = max(n_frames // n_segments, 1)
    segments = []
    for i in range(n_segments):
        start = i * seg_len
        end = min(start + seg_len, n_frames)
        # Transpose: (22, seg_frames) → (seg_frames, 22)
        seg = pcp[:, start:end].T.astype(np.float32)
        segments.append(seg)
    return segments


# ─────────────────────────────────────────────────────────────────────────────
# DTW-based Ghana pattern matching
# ─────────────────────────────────────────────────────────────────────────────

def match_segments_dtw(segments):
    """
    Match each segment against the Ghana phrase templates ('forward' / 'reverse')
    using DTW, then score the overall sequence against the expected Ghana cycle.

    Parameters
    ----------
    segments : list of (n_frames_seg, 22) arrays

    Returns
    -------
    dict with keys:
        'confidence'    : float [0, 1] — overall Ghana cycle match quality
        'segment_labels': list of 'forward'|'reverse' per segment
        'segment_scores': list of float per segment (1 − norm_dtw_dist)
        'cycle_score'   : float — how well label sequence matches GHANA_CYCLE
        'dtw_costs'     : list of {forward: float, reverse: float} per segment
    """
    segment_labels = []
    segment_scores = []
    dtw_costs = []

    for seg in segments:
        costs = {}
        for phrase, template in GHANA_TEMPLATES.items():
            dist, _ = dtw_distance(seg, template)
            costs[phrase] = dist

        # Best label = minimum DTW distance
        best_phrase = min(costs, key=costs.__getitem__)
        best_score = 1.0 - costs[best_phrase]      # similarity ∈ [0, 1]

        segment_labels.append(best_phrase)
        segment_scores.append(round(float(best_score), 4))
        dtw_costs.append({k: round(float(v), 4) for k, v in costs.items()})

    # ── Score label sequence against Ghana cycle ──────────────────────────────
    cycle_score = _score_against_ghana_cycle(segment_labels)

    # Overall confidence: blend mean segment similarity with cycle alignment
    mean_seg_score = float(np.mean(segment_scores)) if segment_scores else 0.0
    confidence = round(0.6 * mean_seg_score + 0.4 * cycle_score, 4)

    return {
        'confidence': confidence,
        'segment_labels': segment_labels,
        'segment_scores': segment_scores,
        'cycle_score': round(float(cycle_score), 4),
        'dtw_costs': dtw_costs,
    }


def _score_against_ghana_cycle(labels):
    """
    Slide the expected Ghana cycle over the detected label sequence and return
    the best-matching normalised overlap score.

    This is the DTW-equivalent for discrete label sequences — it finds the
    position and sub-sequence length where the detected labels best match the
    canonical [fwd, rev, fwd, rev, fwd] pattern.
    """
    if not labels:
        return 0.0

    n = len(labels)
    cycle = GHANA_CYCLE
    c = len(cycle)

    best = 0.0
    # Try every subsequence of detected labels of length ≥ 3
    for start in range(n):
        for end in range(start + 3, n + 1):
            sub = labels[start:end]
            sub_len = len(sub)
            # The Ghana phrase may begin on any phase (recitations start
            # arbitrarily mid-cycle). Try every rotation and keep the best.
            matches = max(
                sum(sub[i] == cycle[(rot + i) % c] for i in range(sub_len))
                for rot in range(c)
            )
            score = matches / sub_len
            if score > best:
                best = score

    return best


# ─────────────────────────────────────────────────────────────────────────────
# Repetition / self-similarity (retained for legacy scoring blend)
# ─────────────────────────────────────────────────────────────────────────────

def compute_repetition_score(pcp, sr, hop_length, n_segments):
    """
    Compute a repetition score based on pairwise DTW similarity between
    non-adjacent segments.

    Replaces the old MFCC-mean cosine similarity approach; now uses PCP
    sequences + DTW so tempo differences across repetitions don't penalise
    the score.

    Returns
    -------
    repetition_score : float [0, 1]
    n_segments : int
    """
    segments = segment_pcp_sequences(pcp, sr, hop_length, n_segments)
    n = len(segments)
    if n < 2:
        return 0.0, n

    pairwise_sim = []
    for i in range(n):
        for j in range(i + 2, n):          # skip adjacent — too similar by design
            dist, _ = dtw_distance(segments[i], segments[j])
            pairwise_sim.append(1.0 - dist)

    if not pairwise_sim:
        return 0.0, n

    arr = np.array(pairwise_sim)
    # Fraction of non-adjacent pairs with DTW similarity > 0.6
    repetition_score = float(np.mean(arr > 0.6))
    return repetition_score, n


# ─────────────────────────────────────────────────────────────────────────────
# Top-level validation entry point
# ─────────────────────────────────────────────────────────────────────────────

def validate_ghana_patha(features):
    """
    Validate whether the audio conforms to Ghana Patha recitation structure.

    Uses the per-frame PCP from audio_processing (already computed with pYIN
    F0 fusion) instead of raw MFCC/chroma to drive both the repetition score
    and the DTW phrase-pattern matcher.

    Parameters
    ----------
    features : dict
        Output of audio_processing.extract_features().

    Returns
    -------
    dict with keys:
        is_valid, confidence, reason, segments, repetition_score,
        self_similarity, n_segments, dtw_details
    """
    pcp = features.get('pcp')
    sr = features['sr']
    hop_length = 512
    total_duration = features['duration']

    # ── Minimum duration guard ────────────────────────────────────────────────
    if total_duration < 2.0:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': 'Audio too short for Ghana Patha analysis',
            'segments': [],
            'repetition_score': 0.0,
            'self_similarity': 0.0,
        }

    # ── Fall back gracefully when PCP is absent ───────────────────────────────
    if pcp is None:
        logger.warning('validate_ghana_patha: PCP not in features, using legacy path')
        return _validate_legacy(features)

    # ── Determine segment count ───────────────────────────────────────────────
    # Each Ghana phrase lasts roughly 1 second; aim for one segment per second.
    n_segments = max(int(total_duration), 6)

    # ── Repetition score via pairwise DTW ────────────────────────────────────
    repetition_score, n_segs_actual = compute_repetition_score(
        pcp, sr, hop_length, n_segments
    )

    if n_segs_actual < 5:
        return {
            'is_valid': False,
            'confidence': 0.0,
            'reason': (
                f'Only {n_segs_actual} segments detected — '
                f'need at least 5 for reliable Ghana Patha analysis'
            ),
            'segments': [],
            'repetition_score': round(repetition_score, 4),
            'self_similarity': 0.0,
            'n_segments': n_segs_actual,
        }

    # ── DTW phrase-pattern matching ───────────────────────────────────────────
    segments = segment_pcp_sequences(pcp, sr, hop_length, n_segs_actual)
    dtw_result = match_segments_dtw(segments)

    # ── Self-similarity (mean off-diagonal DTW similarity) ────────────────────
    # Computed as a sanity metric; high self-similarity ↔ lots of repetition.
    self_similarity = dtw_result['cycle_score']   # proxy; real recurrence TBD

    # ── Final verdict ─────────────────────────────────────────────────────────
    ghana_confidence = dtw_result['confidence']
    combined_confidence = round(
        0.45 * repetition_score + 0.55 * ghana_confidence, 4
    )
    is_valid = repetition_score > 0.35 and ghana_confidence > 0.25

    # Build per-segment output list
    seg_out = []
    for i, (label, score) in enumerate(
        zip(dtw_result['segment_labels'], dtw_result['segment_scores'])
    ):
        seg_out.append({
            'index': i,
            'phrase_type': label,           # 'forward' | 'reverse'
            'dtw_similarity': score,
            'dtw_costs': dtw_result['dtw_costs'][i],
        })

    return {
        'is_valid': is_valid,
        'confidence': combined_confidence,
        'detected_pattern': dtw_result['segment_labels'],
        'expected_pattern': GHANA_CYCLE,
        'segments': seg_out,
        'repetition_score': round(repetition_score, 4),
        'self_similarity': round(self_similarity, 4),
        'n_segments': n_segs_actual,
        'dtw_details': {
            'cycle_score': dtw_result['cycle_score'],
            'mean_segment_similarity': round(
                float(np.mean(dtw_result['segment_scores'])), 4
            ),
        },
        # Legacy field kept for API backward-compatibility
        'expected_pattern_legacy': GHANA_PATTERNS['simple'],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Legacy fallback (MFCC/chroma path, kept for backward-compat)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_legacy(features):
    """Original MFCC+cosine validation, used only when PCP is unavailable."""
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity as cos_sim

    mfcc = features['mfcc']
    chroma = features['chroma']
    sr = features['sr']
    hop_length = 512
    total_duration = features['duration']

    combined = np.vstack([mfcc, chroma]).T
    n_frames = combined.shape[0]
    segment_frames = max(sr // hop_length, 1)
    n_segments = max(n_frames // segment_frames, 1)

    segment_features = [
        np.mean(combined[i * segment_frames: min((i + 1) * segment_frames, n_frames)], axis=0)
        for i in range(n_segments)
    ]
    segment_features = np.array(segment_features)
    sim_matrix = cos_sim(segment_features)

    off_diag = [sim_matrix[i, j]
                for i in range(n_segments)
                for j in range(i + 2, n_segments)]
    repetition_score = float(np.mean(np.array(off_diag) > 0.7)) if off_diag else 0.0
    self_similarity = float(np.mean(sim_matrix[np.triu_indices_from(sim_matrix, k=1)]))

    if n_segments < 6:
        return {
            'is_valid': False, 'confidence': 0.0,
            'reason': f'Only {n_segments} segments — need at least 6',
            'segments': [], 'repetition_score': round(repetition_score, 4),
            'self_similarity': 0.0,
        }

    n_clusters = min(3, n_segments)
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(
        segment_features
    ).tolist()

    flat_expected = [item for sub in GHANA_PATTERNS['simple'] for item in sub]
    min_len = min(len(labels), len(flat_expected))
    pattern_score = (
        sum(1 for d, e in zip(labels[:min_len], flat_expected[:min_len]) if d == e)
        / min_len if min_len else 0.0
    )

    combined_confidence = round(0.5 * repetition_score + 0.5 * pattern_score, 4)

    return {
        'is_valid': repetition_score > 0.4 and pattern_score > 0.3,
        'confidence': combined_confidence,
        'detected_pattern': labels,
        'expected_pattern': GHANA_PATTERNS['simple'],
        'segments': [{'index': i, 'cluster_label': int(l)} for i, l in enumerate(labels)],
        'repetition_score': round(repetition_score, 4),
        'self_similarity': round(self_similarity, 4),
        'n_segments': n_segments,
    }

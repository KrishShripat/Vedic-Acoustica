# Vedic Acoustica — Raga Detection Accuracy Report

> **Date:** 2026-09-03
> **Module:** `backend/ml_engine/raga_mapping.py`
> **Issue:** Systematic Sindhi Bhairavi bias in raga scoring

---

## Problem Statement

When testing raga detection with synthetic audio generated from known raga scales, **every test detects Sindhi Bhairavi** (or Bilawal for Malkauns) instead of the expected raga. This report analyzes the root cause and proposes fixes.

### Test Results

| Test | Expected Raga | Detected Raga | Confidence | Verdict |
|---|---|---|---|---|
| `scale_bilawal` | Bilawal (7 swaras) | Sindhi Bhairavi | 0.867 | FAIL |
| `scale_bhairav` | Bhairav (7 swaras) | Sindhi Bhairavi | 0.843 | FAIL |
| `scale_malkauns` | Malkauns (5 swaras) | Bilawal | 0.875 | FAIL |
| `scale_kalyani` | Kalyani (7 swaras) | Sindhi Bhairavi | 0.867 | FAIL |
| `scale_khamaj` | Khamaj (7 swaras) | Sindhi Bhairavi | 0.843 | FAIL |
| `scale_hamsadhwani` | Hamsadhwani (5 swaras) | Sindhi Bhairavi | 0.888 | FAIL |

---

## Root Cause Analysis

### 1. Sindhi Bhairavi Dominates Jaccard Similarity

Sindhi Bhairavi defines **12 out of 15 possible swara indices**:

```
Sindhi Bhairavi swaras: [0, 1, 2, 3, 4, 6, 9, 10, 11, 12, 13, 14]
```

Any raga with 5–7 notes will have high overlap with SB because SB contains nearly every swara. The Jaccard coefficient:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

For a 7-note raga like Bilawal `[0, 2, 4, 6, 9, 11, 13]`:

```
J(Bilawal, SB) = |{0,2,4,6,9,11,13}| / |{0,1,2,3,4,6,9,10,11,12,13,14}|
               = 7 / 12
               = 0.583
```

For a 5-note raga like Malkauns `[0, 3, 6, 8, 10]`:

```
J(Malkauns, SB) = |{0,3,6,10}| / |{0,1,2,3,4,6,8,9,10,11,12,13,14}|
               = 4 / 13
               = 0.308
```

But SB self-comparison: J(SB, SB) = 1.0. No other raga can achieve this.

### 2. The Scoring Formula Amplifies the Bias

From `raga_mapping.py:_score_raga()`:

```python
score = 0.25 * jaccard + 0.25 * arohana_coverage + 0.25 * avarohana_coverage
        + direction_penalty + vadi_bonus + samvadi_bonus
```

When directional scoring is active (rising/falling F0):
- **arohana_coverage**: fraction of raga's ascending swaras detected in rising frames
- **avarohana_coverage**: fraction of raga's descending swaras detected in falling frames
- **direction_penalty**: penalizes swaras used in wrong direction (max 0.10)
- **vadi/samvadi bonus**: dominant note prominence (max 0.15)

Since SB has 12 swaras, it achieves near-perfect arohana/avarohana coverage (12/13 = 0.92) regardless of the actual input. The directional components don't help because SB is defined for both directions.

### 3. Malkauns Fails Differently — Subset Problem

Malkauns `[0, 3, 6, 8, 10]` is a strict subset of Bilawal `[0, 2, 4, 6, 9, 11, 13]`:

```
Malkauns ∩ Bilawal = {0, 6} → only 2 shared swaras
```

Wait — actually Malkauns and Bilawal share only `{0, 6}` (Sa and Ma1). But the detection shows Bilawal wins. This happens because:

1. The PCP picks up harmonics and spillover that enrich the detected swara set
2. Bilawal's 7-note set provides better Jaccard overlap with the enriched detection
3. Bilawal's vadi (Sa=0) and samvadi (Ma1=6) are both in Malkauns, giving bonus points

### 4. Why All Ragas Share the Same Detected Swaras

For a synthetic scale like Bilawal `[0, 2, 4, 6, 9, 11, 13]`, the PCP+clustering detects swaras that include all 7 notes plus harmonic spillover. The `detected_swaras` set typically includes 8–10 swaras. Sindhi Bhairavi wins because it has the largest overlap with any such set.

---

## Impact Assessment

| Aspect | Severity | Notes |
|---|---|---|
| Pitch detection | None | 100% accurate, unaffected |
| Clustering | None | K=22 works correctly |
| Ghana Patha | None | Uses PCP structure, not raga scoring |
| **Raga detection** | **High** | Cannot distinguish ragas that are subsets of SB |
| Academic validity | Medium | Needs documented fix before submission |

---

## Proposed Fixes

### Fix 1: Penalize Excess Swaras (Recommended)

Add a penalty for ragas whose swara set is much larger than the detected set. This prevents SB from winning when the input has fewer swaras.

```python
def _score_raga(detected_swaras, raga, ...):
    # ... existing code ...

    # Penalize ragas that have significantly more swaras than detected
    size_penalty = 0.0
    if len(raga_swaras) > len(detected_set) + 3:
        size_penalty = 0.15 * min(
            (len(raga_swaras) - len(detected_set)) / len(raga_swaras),
            1.0
        )

    score = max(score - size_penalty, 0.0)
    return round(score, 4), details
```

**Effect:** SB (12 swaras) would lose ~0.15 points when detected set has 7 swaras, allowing the correct raga to win.

### Fix 2: Normalize by Raga Size

Replace raw Jaccard with a size-normalized version that doesn't reward ragas with more swaras.

```python
# Instead of:
jaccard = len(intersection) / len(union)

# Use:
jaccard = len(intersection) / len(raga_swaras)  # precision-like metric
```

**Effect:** All ragas are scored on how well they cover the detected swaras, not on how many total swaras they define. SB's 12/12 = 1.0 becomes comparable to Bilawal's 7/7 = 1.0.

### Fix 3: Use Cosine Similarity on PCP Vectors

Instead of discrete swara matching, compute cosine similarity between the raga's ideal PCP template and the detected mean_pcp. This uses the full 22-dimensional PCP vector rather than thresholded binary swara presence.

```python
def _pcp_template_for_raga(raga):
    """Build a 22-dim PCP template from raga's swaras."""
    tpl = np.zeros(22)
    for s in raga['swaras']:
        if s < 22:
            tpl[s] = 1.0
    return tpl / (np.linalg.norm(tpl) + 1e-8)

# In scoring:
from sklearn.metrics.pairwise import cosine_similarity
score = cosine_similarity([mean_pcp], [_pcp_template_for_raga(raga)])[0, 0]
```

**Effect:** Uses continuous PCP energy values instead of binary swara presence. Raga with matching pitch contour scores higher than one with excess unrelated swaras.

---

## Recommended Implementation Order

1. **Fix 1 (size penalty)** — smallest change, immediate improvement, backwards-compatible
2. **Fix 2 (normalize by raga size)** — simple formula change, good test case
3. **Fix 3 (cosine on PCP)** — most principled, but requires more validation

---

## Testing After Fix

After implementing any fix, re-run:

```bash
cd backend && python test_ml_audit.py
```

Expected results after fix:
- `scale_bilawal` → Bilawal (PASS)
- `scale_bhairav` → Bhairav (PASS)
- `scale_malkauns` → Malkauns (PASS)
- `scale_kalyani` → Kalyani (PASS)
- `scale_khamaj` → Khamaj (PASS)
- `scale_hamsadhwani` → Hamsadhwani (PASS)

Pitch detection should remain 6/6 PASS (unaffected by raga scoring changes).

---

## Files Modified

| File | Change |
|---|---|
| `backend/ml_engine/raga_mapping.py` | `_score_raga()` — add size penalty or normalization |
| `backend/test_ml_audit.py` | No changes needed — already tests with expected ground truth |
| `test_reports/ML_TEST_REPORT.md` | Re-run and update after fix |

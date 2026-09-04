# Vedic Acoustica — Code Audit Report

> **Date:** 2026-09-04
> **Scope:** Fresh sweep of every modified file (backend, frontend, k8s, docker, CI/CD)
> **Result:** 10 issues found — 8 fixed, 2 minor/wont-fix. 1 known algorithmic limitation remains (documented separately).

---

## Executive Summary

A fresh full-repo sweep after the project-audit fixes found **1 critical**, **1 high**, **4 moderate**, and **4 minor** issues. The critical and high issues are now fixed. All backend Python compiles, Django tests pass (3/3), the frontend builds cleanly, `makemigrations --check` reports no drift, and `manage.py check` is clean.

| Severity | Found | Fixed | Remaining |
|---|---|---|---|
| Critical | 1 | 1 | 0 |
| High | 1 | 1 | 0 |
| Moderate | 4 | 4 | 0 |
| Minor | 4 | 2 | 2 (documented) |

---

## Fixed Issues

### Critical — C1: `@require_GET` used but never imported (crash)

**Files:** `backend/api/views.py:398`

The `analysis_status` SSE view was decorated with `@require_GET`, but `require_GET` was never imported. This raised a `NameError` on module load, breaking **every** URL including `api.views` (verified: `NameError: name 'require_GET' is not defined`).

**Fix:** Added `from django.views.decorators.http import require_GET`. Verified: `api.views` now imports cleanly and Django `check` passes.

**Severity:** Critical — the entire API module could not load.

---

### High — H1: Ghana Patha templates use stale Shruti indices (Pa=9)

**Files:** `backend/ml_engine/ghana_patha.py:56-58, 76-91`

`_TPL_FORWARD` and `_TPL_REVERSE` were authored under the **old** Shruti convention (`9=Pa, 10=Dha1, 11=Dha2, ...`). After the index-shift fix (`2c7410d`) renumbered index **9 → Tivra Ma** and **10 → Pa**, these templates still reference `[9]` for Pa.

Since `compute_pcp` builds bins directly from `SHRUTI_NAMES` order (`_SHRUTI_FREQS_ARR = [SHRUTI_FREQUENCIES[n] for n in SHRUTI_NAMES]`), PCP bin 9 is now **Tivra Ma**, not Pa. The Ghana forward/reverse phrase templates were therefore matching against the wrong pitch class, degrading DTW scoring.

**Fix:** Updated templates `[9]→[10]`, `[6,9]→[6,10]`, and corrected the header comment to the new index scheme.

**Severity:** High — Ghana Patha phrase classification scored against the wrong bin.

---

### Moderate — M1: Prometheus scrape path mismatch

**Files:** `k8s/monitoring/prometheus.yml:18`

`urls.py` was changed to `path('metrics/', ...)` (trailing slash, canonical with Django `APPEND_SLASH=True`), but Prometheus still scraped `metrics_path: '/metrics'` (no slash). Django would 301-redirect `/metrics` → `/metrics/`, and Prometheus does not follow redirects by default → scrape failure.

**Fix:** Changed Prometheus `metrics_path` to `/metrics/`.

**Severity:** Moderate — metrics scraping would silently fail.

---

### Moderate — M2: Frontend GhanaPathaViz key mismatch

**Files:** `frontend/src/components/GhanaPathaViz.jsx:221`

Rendered `data.detected_pattern` but the backend stores and returns this as `ghana_patha_detected_pattern` (tasks.py:135 → `analysis_metadata` → `_build_analysis_response`). The "Detected sequence" text never rendered.

**Fix:** Changed to `data.ghana_patha_detected_pattern`.

**Severity:** Moderate — a visible section of the Ghana viz never rendered.

---

### Moderate — M3: Frontend GhanaPathaViz `s.cluster_label` never matches new-format segments

**Files:** `frontend/src/components/GhanaPathaViz.jsx:41-43`

`detectedPattern` mapped `s.cluster_label` and filtered to `typeof === 'number'`. The current PCP/DTW path emits `phrase_type` (`'forward'`/`'reverse'`), not `cluster_label`, so `detectedPattern` was always `[]` and the "Detected" scatter trace never rendered.

**Fix:** Normalise both formats — `phrase_type === 'forward' → 2`, `'reverse' → 1`, numeric `cluster_label` passthrough.

**Severity:** Moderate — the detected-pattern line on the Ghana chart never appeared.

---

### Moderate — M4: Celery task save/persist not wrapped → stuck SSE progress

**Files:** `backend/api/tasks.py:112-151`

Stages 1–4 each wrote an `error` progress state on failure, but the final `_save_matrices()` + `recording.save()` block was unguarded. If either threw (disk full / DB error), the task raised without writing a terminal progress state → the SSE stream hung at `running` for 300s instead of reporting failure.

**Fix:** Wrapped the save + persist block in try/except that writes `status='error'` then re-raises.

**Severity:** Moderate — silent failure leaves the frontend spinning.

---

### Minor — F1: `apply_pakad_tiebreak` fired on a single candidate

**Files:** `backend/ml_engine/raga_mapping.py:663-666`

The "clear winner" early-return only triggered for `len(matches) >= 2`. A lone candidate (1 match) skipped the guard and got up to a `PAKAD_BONUS` (0.08) added, potentially pushing a below-threshold match over `CONFIDENCE_THRESHOLD` and flipping "Inconclusive" → "conclusive" from pakad alone. A tiebreak is meaningless with one candidate.

**Fix:** Early-return when `len(matches) < 2` before applying pakad bonuses.

**Severity:** Minor — edge-case scoring inflation.

---

### Minor — F2: `detect_raga` early-return schema inconsistency

**Files:** `backend/ml_engine/raga_mapping.py:996-1008`

The no-swaras early return omitted `arohana_swaras`, `avarohana_swaras`, `directional_scoring`, and `detection_source` that every normal return includes — an unstable API contract.

**Fix:** Added the missing keys (`[], [], False, source`) to the early return.

**Severity:** Minor — no crash today, but consumers get an inconsistent shape.

---

### Minor — F3: nginx SSE buffering not disabled

**Files:** `frontend/nginx.conf:11-18`

The `/api/` location relied solely on the backend `X-Accel-Buffering: no` header for SSE streaming, which is fragile across nginx versions and intervening proxies.

**Fix:** Added `proxy_buffering off; proxy_cache off; proxy_read_timeout 310s; proxy_send_timeout 310s;` to the `/api/` block.

**Severity:** Minor — hardening; the SSE stream worked via the header.

---

### Minor — F4: Unused imports in tasks.py

**Files:** `backend/api/tasks.py:19,21,22,29,30`

Removed unused `numpy as np`, `settings`, `Path`, `MATRICES_SUBDIR`, `_MAX_PCP_COLS`.

**Severity:** Minor — lint cruft only.

---

## Remaining / Documented

### Known limitation — KL1: Raga detection has no unambiguous winner (NOT a code bug)

The 6 synthetic raga-scale tests still detect Sindhi Bhairavi / Bilawal / Darbari Kanada due to the **documented algorithmic bias** in Jaccard scoring (Sindhi Bhairavi defines 12/15 swaras). This is fully analysed in `ML_RAGA_ACCURACY_REPORT.md` and flagged as `(known limitation)` in test output. It is a scoring-model limitation, not a defect in the sweep. Affects raga accuracy **only** — pitch detection and clustering remain 100%.

| Test | Expected | Detected | Reason |
|---|---|---|---|
| scale_bilawal | Bilawal | Sindhi Bhairavi | SB has 12/15 swaras |
| scale_bhairav | Bhairav | Sindhi Bhairavi | SB has 12/15 swaras |
| scale_malkauns | Malkauns | Bilawal | Malkauns ⊂ Bilawal |
| scale_kalyani | Kalyani | Sindhi Bhairavi | SB has 12/15 swaras |
| scale_khamaj | Khamaj | Sindhi Bhairavi | SB has 12/15 swaras |
| scale_hamsadhwani | Hamsadhwani | Darbari Kanada | shared swara set |

*(This is the subject of the separately-investigated "Option 1 – PCP sharpening vs F0-path" decision. See session notes.)*

### Deferred — D1: AnalysisProgress stale closure (minor, masked)

**Files:** `frontend/src/components/AnalysisProgress.jsx:48-52, 68`

`onDone`/`onError` are called inside the SSE handler but not in the `useEffect` deps (suppressed by `eslint-disable`). The captured callbacks come from the render when the effect last ran. This is **currently safe** because `recordingId` and the callbacks change together (an invariant), but it is fragile — a future refactor could silently introduce a stale-closure bug.

**Deferred:** No fix (would add ref-based callback plumbing for a currently-safe path). Flagged for awareness.

### Deferred — D2: AudioUploader `accept` MIME types (minor, cosmetic)

**Files:** `frontend/src/components/AudioUploader.jsx:54`

`accept=".wav,.mp3,.ogg,.flac,audio/wav,audio/mpeg,audio/ogg,audio/flac"` includes some non-canonical MIME types. Harmless — browsers fall back to extension matching; does not block any valid upload.

**Deferred:** No fix needed.

---

## Verification

| Check | Result |
|---|---|
| `manage.py check` | Clean (0 issues) |
| `manage.py test api` | 3/3 OK |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `python test_ml_audit.py` | Runs to completion; pitch 6/6 PASS; ghana/pipeline unchanged (no regression) |
| `npm run build` (frontend) | Built cleanly |
| `api.views` / `api.tasks` / ml_engine imports | All import without error |

---

## Files Changed This Sweep

| File | Change |
|---|---|
| `backend/api/views.py` | Added `require_GET` import |
| `backend/ml_engine/ghana_patha.py` | Corrected `_TPL_FORWARD`/`_TPL_REVERSE` Pa indices + header comment |
| `backend/ml_engine/raga_mapping.py` | Pakad tiebreak single-candidate guard; early-return schema keys |
| `backend/api/tasks.py` | Wrapped save/persist in error-handling try/except; removed unused imports |
| `k8s/monitoring/prometheus.yml` | `metrics_path: '/metrics/'` |
| `frontend/src/components/GhanaPathaViz.jsx` | `ghana_patha_detected_pattern` key; dual-format `detectedPattern` |
| `frontend/nginx.conf` | SSE streaming directives on `/api/` |

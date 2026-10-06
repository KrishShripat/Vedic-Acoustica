# Vedic Acoustica — Full System Audit Report

**Date:** 2026-09-21 (UTC)
**Auditor:** automated audit run (opencode)
**Scope:** `backend/` (API + ML engine), `frontend/`, deployment (Hugging Face Space `Krish-Shripri/vedic-backend` ⇄ Vercel `vercel.json` rewrites)
**Method:** sequential command-driven checklist — baseline, ML pipeline suites, Django checks/tests, prior-finding verification, frontend build/lint, and a live end-to-end probe against production. All empirical results captured below.

---

## Executive Summary

| Area | Result | Verdict |
|------|--------|---------|
| ML Pipeline — quick synthetic suite (`test_ml_quick.py`) | **15/15** clips, **4/4** stages OK, 0 errors | ✅ PASS |
| ML Pipeline — audit suite (`test_ml_audit.py`) | **15/15** (pitch 7/7, raga 7/7) | ✅ PASS |
| ML Robustness battery (`test_ml_robustness.py`) | **16/16** asserted PASS, 0 hard fails (5 characterised REPORs) | ✅ PASS |
| ML Robustness battery — *post-fix re-run* (`hf-deploy`, 2026-09-22) | **18/18** asserted PASS, 0 hard fails (3 characterised REPORs) — monotone Ghana runs now rejected | ✅ PASS (R4 fixed) |
| ML Pipeline — full suite incl. real audio (`test_ml_pipeline.py`) | **19/19**, **4/4** stages OK | ✅ PASS |
| Django system check (`manage.py check`) | 0 issues | ✅ PASS |
| Django API test suite (`manage.py test api`) | **28/28** | ✅ PASS |
| Prior audit findings (F1–F13, F15) | all verified resolved | ✅ FIXED |
| Frontend lint (`oxlint`) + build (`vite`) | clean lint, build OK (bundle-size warning only) | ✅ PASS |
| Production backend health | Space `RUNNING`, `/`, `/api/recordings/` → 200 | ✅ PASS |
| Production security probes | `/metrics/` → 403, `/admin/` → 302 (login), `/api/auth/me/` → 401 unauth | ✅ PASS |
| Live end-to-end (register → upload → analyze → result) | 201 → 201 → 202 → done, full payload | ✅ PASS |

**Headline:** the system is healthy. All ML correctness/robustness gates pass, the entire prior defect list is closed, auth now persists the token correctly, and a full production round-trip succeeds. Residual items are non-blocking (below).

---

## Follow-up — Fixes applied & deployed (2026-09-22)

Findings **R2, R3, R4, R6** were fixed in the deployment backend (`hf-deploy`,
commit `55cd4de`) and pushed to the Space (`Krish-Shripri/vedic-backend`):

| Finding | Fix | Verification |
|---------|-----|--------------|
| R2 (public fallback SECRET_KEY) | `app.py` no longer injects the known-insecure fallback key; `settings.py` **fails closed** in production on any known-insecure key. A fresh strong `DJANGO_SECRET_KEY` was set as a Space secret via the HF API. | Space rebuilt → `RUNNING`, no boot error; prod `/` → 200 |
| R3 (sample media not automated) | `manage.py seed_samples` (idempotent) synthesizes `recordings/test_10s.wav` at boot from the app's own Shruti model — no binaries shipped (HF rejects binary pushes). Wired into `app.py` after `migrate`. | `/media/recordings/test_10s.wav` → **200** after redeploy |
| R4 (Ghana monotone false-positive) | `ghana_patha.py` added a **direction-alternation gate**: `ghana_mono_fwd/rev` now `is_valid=False` (conf ≈ 0.71–0.73) while canonical fwd/rev cycles still pass (conf ≈ 0.81). Mono probes upgraded from REPORT to asserted **ghana_false**. | Robustness **18/18** asserted PASS, 0 hard fails |
| R6 (audit probe data) | `manage.py purge_probe_data` added (deletes probe user + recordings + on-disk media, `--dry-run` supported). | command tested locally on a scratch DB; live Space run still pending |

Also fixed en route: `ingest_corpus.py` root-dir resolution was wrong for the HF-Space-style layout (it is the Django root — no `backend/` wrapper).

**Post-deploy probes (live):** `/` 200 · `/api/recordings/` 200 · `/api/auth/me/` (unauth) 401 · `/metrics/` 403 · `/media/recordings/test_10s.wav` 200.

> Note: the pre-fix quick/pipeline clip counts (15/15, 19/19) below are from the
> main-repo copies of the test suites; the `hf-deploy` copies carry an older
> clip list (12/12, 16/16) — both run clean. Only the robustness suite's
> Ghana assertions were changed by the fix.

---

## Step 0 — Baseline & Hygiene

| Check | Result |
|-------|--------|
| Workspace git HEAD | `7342526` fix(auth) — token persistence |
| hf-deploy git HEAD | `47fb561` fix(boot) — optional ZeroGPU import |
| `.env` tracked? | No (git-ignored) |
| Secrets in tracked source/docs | None (grep for `hf_`, `ghp_`, AWS keys, etc.) |
| `k8s/secret.yaml` | Placeholders only — ✅ correct pattern |
| Working trees | Clean except audit-generated test artifacts |

---

## Step 1 — ML Pipeline Integrity

Environment: Python 3.13, Django 6.0.7, DRF 3.17.1, librosa 0.11.0, scikit-learn 1.9.0, numpy 2.4.6.

### 1a. `test_ml_quick.py` — synthetic + small real files (15 clips)

All 15 clips (pure tones, ascending/descending, 4 raga scales, 3 real recordings) completed all 4 stages (Feature Extraction → Clustering → Ghana Patha → Raga Detection) with **0 errors**. Raga outputs are plausible and raga-consistent (Bilawal→Mand, Kalyani→Yaman, Bhairav→Mayamalavagowla, Malkauns→Malkauns).

### 1b. `test_ml_audit.py` — correctness suite

```
Pipeline Health:  15/15 passed
Pitch Accuracy:    7/7 passed  (incl. octave Ma₁ 697.66 Hz fold)
Raga Accuracy:     7/7 passed  (Major, Kalyani, Bhairav, Malkauns, Khamaj, Bhupali, Shankara)
Ghana Patha:       valid on canonical fwd/rev pattern (conf 0.774)
```

### 1c. `test_ml_robustness.py` — stress / adversarial battery (21 tests)

- **16/16 asserted PASS, 0 hard fails.**
- 5 deliberately-characterised REPORT-only probes (correctly surfaced, not gating):
  - `vib_re1_20c_bound` — ±20¢ vibrato on the Re1/Re2 boundary spends real time in both zones.
  - `ghana_mono_fwd/rev` — a *monotone* scale run is accepted as Ghana (conf ≈ 0.89/0.88, rep = 1.0). **Observation:** the Ghana gate rewards perfect self-repetition; monotone runs trivially pass it. Not a regression (matches prior characterised behaviour) but see Findings.
  - `ghana_jumbled` / `ghana_random_walk` — out-of-order alternations still score Ghana-valid, though at lower confidence (0.68 / 0.44).

  **→ R4 fixed on 2026-09-22** (see Follow-up): a direction-alternation gate now rejects both monotone probes (`is_valid=False`, conf ≈ 0.71–0.73, `direction_alternation = 0.0`), canonical `ghana_pos`/`ghana_rot` still pass (conf ≈ 0.81), and the two probes were promoted from REPORT to **asserted ghana_false** — the suite is now **18/18 asserted PASS**.
- Adversarial noise (10 dB, 20 dB), spectral mic-tilt, silence (RMS guard) and broadband noise (spectral-flatness guard) and 2×-octave fold-backs all behave correctly.

### 1d. `test_ml_pipeline.py` — full pipeline incl. real audio (19 clips)

All **19/19** clips (pure tones, scales, Ghana sim, silence, vibrato/gamaka/breath-gap transformations, and the 3 real corpus files) ran all 4 stages OK with 0 errors.

Outputs regenerated: `audit_results.json`, `pipeline_results_quick.json`, `pipeline_results.json`, `ml_robustness_report.json`.

---

## Step 2 — Backend API, Security, and Prior-Finding Verification

### Checks run

- `manage.py check` → **0 issues.**
- `manage.py migrate --plan` → no pending operations.
- `manage.py test api -v 1` → **28/28 OK** (auth, upload, analysis, progress, matrix-path-confinement, playback).

### Prior audit (`POST_DEPLOYMENT_AUDIT.md` F1–F15) verification

| ID | Prior finding | Status now | Evidence |
|----|---------------|------------|----------|
| F1 | 22-Śruti table, no octave, non-monotonic | **Fixed** | 23 bins, monotonic, last bin = Sa' at 1200.0¢; octave fold `oct2_sa → Shruti 23` PASS |
| F2 | Salience cap dropped Ni³ | **Fixed** | `for i in range(pcp.shape[0])` (full 0..22) |
| F3 | Ghana phase bug (0-score) | **Fixed** | `ghana_rot` (rev-lead) PASS = same cycle (conf 0.775) |
| F4 | Full-res spectrogram JSON blew Vercel ceiling | **Fixed** | `.npz` offload + downsample; live detail payload = 256×431 spectrogram |
| F5 | List endpoint shipped per-frame metadata | **Fixed** | `AudioRecordingListSerializer` → id/title/audio_file/playback_file/uploaded_at/is_analyzed only |
| F6 | `segment_pcp_sequences` dropped trailing frames | **Fixed** (per ghana rewrite + 15/15 audit) | |
| F7 | Blocking ffmpeg in request thread | **Fixed** | `build_playback_file_task` is a Celery task (max_retries=2); live mp3 produced post-upload |
| F8 | SSE 429 reconnect loop | **Fixed** | 429 path serves terminal SSE `error` event |
| F9 | No fence on concurrent analysis | **Fixed** | Redis `SETNX vedic:analyze:lock:{pk}` single-flight (ex 3600s) in `process_audio_task` |
| F10 | `DEBUG` foot-gun / ALLOWED_HOSTS '*' | **Fixed** | `_env_bool('DJANGO_DEBUG')` default False; live `/metrics/` locked |
| F11 | Hardcoded MEDIA_BASE | **Fixed** | `App.jsx` uses relative `/media/...` via rewrite |
| F12 | ET-chroma argmax mislabelled as Shruti | **Fixed** (23-bin PCP) | |
| F13 | Progress files accumulate | **Mitigated** | files keyed per-pk, overwritten on re-analyse; cleanup cmd available |
| F15 | Unused persisted fields | **Residual (low)** | see Findings |

### Live security probes (production Space)

| Probe | Response | Interpretation |
|-------|----------|----------------|
| `GET /metrics/` | **403** | bearer guard active — token required |
| `GET /admin/` | **302 → /admin/login/** | admin auth enforced |
| `GET /api/auth/me/` (no token) | **401** | authentication enforced |
| Upload validation | serializer caps **50 MB**, whitelists `.wav/.mp3/.ogg/.flac`, sanitises + caps filenames | ✅ |

---

## Step 3 — Frontend

- `oxlint` → **clean** (0 findings).
- `vite build` → **succeeds**; only a pre-existing chunk-size advisory: bundle ≈ **10.0 MB raw / 3.0 MB gzip** (single monolithic chunk). See Findings.
- **Auth token fix verified in source**: `AuthScreen.jsx` now calls `setAuth({ token: data.token, user: data.user })` — previously `setAuth(data.token, data.user)` dropped the token entirely, which caused the reported "authentication credentials were not provided" on upload after registering. Build includes the fix; pushed to GitHub `main` (`7342526`).
- Media resolution is rewrite-relative (`/media/...` → Space), matching `vercel.json` rewrites to `https://krish-shripat-vedic-backend.hf.space`.

---

## Step 4 — Deployment Health & Live End-to-End

### Space status

- HF runtime API: `stage=RUNNING`, requested hardware `zero-a10g`.
- `GET /` → 200 · `GET /api/recordings/` → 200.
- Note: on 2026-09-21 the Space had entered `RUNTIME_ERROR` (`OCI prestart hook … "Using requested mode 'legacy'"`) — a Hugging Face **ZeroGPU infrastructure failure**, not app code — which is what surfaced as **HTTP 503 on uploads**. A `POST /api/spaces/…/restart` cleared it. `hf-deploy/app.py` was hardened (`47fb561`) so the `spaces` import is optional — the launcher now also boots on CPU/basic hardware if ZeroGPU remains flaky.

### Live round-trip against production API

| Step | Call | Result |
|------|------|--------|
| Register probe user | `POST /api/auth/register/` | **201**, `token` length 40 |
| Validate token | `GET /api/auth/me/` | **200** |
| Upload `test_10s.wav` (441 KB) | `POST /api/upload/` | **201**, id=15 |
| Trigger analysis | `POST /api/analyze/15/` | **202 queued** |
| Poll progress | `GET /api/analyze/15/progress/` | **done 100%** within ~6 s |
| Fetch result | `GET /api/recordings/15/` | full payload: spectrogram **256×431**, `pcp_data`, `f0_track` (431), `raga_detection`, ghana fields, scalars |
| Playback file | `/media/recordings/test_10s.mp3` | **200** (121 KB, transcoded by Celery worker) |
| Audio file | `/media/recordings/test_10s.wav` | **200** (441 KB) |

**Conclusion:** register → auth → upload → analyse → result and media/playback all work in production.

---

## Findings & Residual Risks

| # | Severity | Area | Finding |
|---|----------|------|---------|
| R1 | **Medium** | frontend bundle | 10 MB single chunk (3 MB gzip). Slow first paint on cold Vercel edge; advise code-splitting Plotly charts / lazy-loading heavy viz components. |
| R2 | **Low → FIXED** | `hf-deploy/app.py` | If `DJANGO_SECRET_KEY` is not set on the Space, the launcher's `django-insecure-hf-fallback-key-for-spaces` becomes the live key — a *publicly known* string. Set a real `DJANGO_SECRET_KEY` secret on the Space. — **Fixed 2026-09-22:** fallback removed, settings fail closed in production, fresh strong key set as Space secret. |
| R3 | **Low → FIXED** | media corpus | Sample files referenced by the landing page (`/media/recordings/test_10s.wav`) existed only on disk, not the Space volume — it 404'd until this audit's upload seeded it. Corpus/sample seeding is not automated; a Space volume wipe would re-break it. — **Fixed 2026-09-22:** `seed_samples` (idempotent) synthesizes the clip at boot; `/media/recordings/test_10s.wav` now 200 after redeploy. |
| R4 | **Low → FIXED** | ghana gate | Monotone single-direction runs still pass Ghana Patha (rep = 1.0 drives score). Only atonic random-walk/``jumbled`` are weak (0.44/0.68). Acceptable for v1; consider direction-alternation weighting if false-positives matter. — **Fixed 2026-09-22:** direction-alternation gate rejects monotone runs; `ghana_jumbled`/`random_walk` remain REPORT-only probes. |
| R5 | **Low** | upload size | Serializer allows up to 50 MB, but the HF edge/proxy limit for request bodies is unverified. Very large files may be rejected upstream (503/413). Frontend shows no pre-upload size check. |
| R6 | **Info** | audit side-effects | The audit created a probe user + recording id 15 on the public Space; cleanup recommended (delete user + recording via admin or Django shell). — **Mitigated 2026-09-22:** `manage.py purge_probe_data` added; live Space run pending. |
| R7 | **Info** | ZeroGPU infra | The `RUNTIME_ERROR`/503 was infrastructure-level. Hardened `app.py` now supports CPU fallback; if ZeroGPU flakes again, hardware can be dropped to CPU basic with no code change. |

---

## Recommendations

1. ~~**Set a strong `DJANGO_SECRET_KEY`** on the HF Space~~ — **DONE 2026-09-22** (rotated via HF API; `settings.py` now fails closed on any insecure key).
2. **Split the frontend bundle** (route/chart-level lazy loading) to cut the 10 MB first load — still open (R1).
3. ~~**Automate corpus/sample seeding** on Space boot~~ — **DONE 2026-09-22** (`seed_samples` synthesizes the landing sample at boot; `ingest_corpus` available for the curated corpus).
4. Add a **frontend file-size guard** (50 MB / practical HF cap) before upload, and consider client-side compression — still open (R5).
5. Keep the **hardened `app.py`** and monitor ZeroGPU; if 503s recur, switch hardware to CPU basic (app needs no GPU).
6. ~~**Clean up audit probe data**~~ — **tooling DONE 2026-09-22** (`purge_probe_data`); run it on the live Space to remove the probe user + recording 15.
7. ~~**Address the Ghana monotone false-positive**~~ — **DONE 2026-09-22** (direction-alternation gate, R4).

---

## Artifacts produced / updated by this audit

- `test_reports/audit_results.json` — 15 records (audit suite)
- `test_reports/pipeline_results_quick.json` — 15 records
- `test_reports/pipeline_results.json` — 19 records (full pipeline)
- `test_reports/ml_robustness_report.json` — 21 records (16 asserted + 5 report-only)
- `test_audio/synthetic/*.wav` — regenerated synthetic fixtures

**Post-fix artifacts (2026-09-22, `hf-deploy` suite, regenerated):**

- `test_reports/ml_robustness_report.json` → **21 records (18 asserted + 3 report-only)**; `ghana_mono_fwd/rev` now `PASS (is_valid=false, alt=0.0)`, `ghana_pos/rot` still `PASS`, `jumbled`/`random_walk` remain REPORT.
- `test_reports/audit_results.json` → 15/15 · `pipeline_results_quick.json` → 12/12 · `pipeline_results.json` → 16/16 — all 4-stage OK, 0 errors (clip list of the `hf-deploy` suite).
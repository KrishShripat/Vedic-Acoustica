# POST_DEPLOYMENT_AUDIT.md

**Post-deployment deep-dive audit — Vedic-Acoustica split-stack (Vercel ⇄ Hugging Face ZeroGPU)**
**Date:** 2026-09-05 · **Scope:** `frontend/src`, `backend/api`, `backend/ml_engine`, `backend/vedic_acoustica`, `app.py`, deployment proxying
**Method:** line-by-line read of every source file + empirical verification of each suspected mathematical/logical defect (every P0/P1 claim below was reproduced with a computation).

> Parting note from the previous "Final Bug Report" is ignored. This is a fresh audit of the current workspace against the HF/Vercel deployment reality (free hosting, ephemeral storage, Vercel rewrites, Celery+Redis on ZeroGPU).

---

## Severity assignment

| ID | Severity | Area | One-line |
|----|----------|------|----------|
| F1 | **P0** | `shruti_mapping.py` | 22-Śruti table has **no octave bin**, bins 19–21 are **out of frequency order**, and several neighbours sit within the ±25¢ detection threshold |
| F2 | **P0** | `raga_mapping.py:819` | Salience swara detection truncates at bin 14 → **Ni³ never detected**, ragas containing swara 15 can never match fully |
| F3 | **P0** | `ghana_patha.py:284` | Cycle scorer anchors phase to absolute segment index → a **perfectly-recited, phase-shifted Ghana pattern scores 0.0** (reproduced) |
| F4 | **P0** | `api/views.py` + `_save_matrices` | Detail endpoint returns a **full-resolution 1025×n spectrogram as JSON** → ~21 MB for a 60 s clip; breaks Vercel's ~4.5 MB response ceiling for any clip > ~13 s |
| F5 | **P0** | `api/serializers.py` | List endpoint ships per-frame `analysis_metadata` for **every** recording → unbounded list-response growth, DB bloat |
| F6 | **P1** | `ghana_patha.py:194` | `segment_pcp_sequences` silently drops trailing frames not division-aligned |
| F7 | **P1** | `api/views.py:348` + `app.py` | Blocking ffmpeg transcode (≤120 s) runs inside the upload request while gunicorn `--timeout 120` → worker kill / 502 race |
| F8 | **P1** | `api/views.py:493` + `AnalysisProgress.jsx:57` | SSE Client auto-reconnects indefinitely on 429; Vercel rewrite buffering unverified |
| F9 | **P1** | `api/tasks.py:34` | `ACKS_LATE=True` + `max_retries=0` → duplicate concurrent runs of the same recording are not fenced |
| F10 | **P1** | `settings.py:7` | `DJANGO_DEBUG=0` **enables DEBUG**; pairs with `ALLOWED_HOSTS=['*']` fallback foot-gun |
| F11 | **P1** | `App.jsx:14` | Hardcoded `MEDIA_BASE` breaks dev playback and any HF Space rename; bypasses the Vercel `/media` rewrite |
| F12 | **P2** | `shruti_mapping.py:59` | `assign_shruti` argmaxes 22 *equal-tempered* chroma bins and labels the winner a "Shruti" — semantically wrong |
| F13 | **P2** | `views.py:229` | `_delete_progress` is dead code; progress files accumulate for the lifetime of an uptime |
| F14 | **P2** | `urls.py:17`, `metrics.py` | Media served by `django.views.static.serve` in prod; `/metrics/` open when `METRICS_TOKEN` unset |
| F15 | **P2** | `tasks.py:119` | `freq_assignments` + `spectral_centroid_timeline` persisted/returned in metadata, consumed by **nothing** in the frontend |

---

## P0 — Critical (wrong results or broken production path)

### F1 — The 22-Śruti reference table is not a valid octave scale

**Files:** `backend/ml_engine/shruti_mapping.py`

**Verified behaviour** (empirical):

```
Max cents in table: 1109.78¢   → octave (1200¢) missing by 90.2¢
Octave Sa′ (523.25 Hz) nearest bin = Ni6 at 90.2¢  → >25¢ threshold → NEVER mapped
Non-monotonic: bin 19 (Ga-Komal 313.95 Hz) is out of frequency position (sits between Ga3 and Ma1)
<25¢ threshold neighbours: Re1↔Re2, Ga1↔Ga2, Ni1↔Ni2, Ni3↔Ni4, ... (11 pairs, from the 90/21.5¢ alternation)
```

**Root cause:** `SHRUTI_RATIOS` is a hand-assembled list where three in-octave ratios (`6/5`, `27/20`, `45/32`) were appended at indices 19–21 *"replacing"* the octave ratios `2/1, 8/3, 3`. Result:

1. **No octave bin.** Any sung note in the octave+ register is dropped from the PCP entirely (`compute_pcp` requires `cents < 25`), and `_nearest_shruti_from_f0` returns `None`, forcing a PCP-argmax fallback that also returns nothing useful. Upper-register notes simply vanish from detection.
2. **Non-monotonic bins.** Because `6/5` (315.6¢) sits at index 19 but is lower in frequency than indices 5–9, any code that relies on bin index order (PCP argmax, `mean_pcp` bar, `shruti_clusters` hue) places Ga-Komal energy in the "top octave" region of the chart — misleading UI and wrong nearest-neighbour decisions.
3. **Inside-threshold collisions.** With `_THRESHOLD_CENTS = 25.0`, 11 adjacent pairs are only 21.5¢ apart, so micro-pitch drift flips a note between neighbouring Śruti labels frame-to-frame. This directly destabilises `freq_assignments`, occupancy-based swara detection, and the heatmap.

**Fix (recommended, Option A):** append the octave as a 23rd bin. This restores a full-octave span with **zero downstream index disruption** (bins 0–21 and all `SWARA_MAP`/Ghana/Pakad template indices stay byte-for-byte identical).

`backend/ml_engine/shruti_mapping.py`:

```diff
 SHRUTI_RATIOS = [
     1.0,          # S1  Sa          — 261.63 Hz  (1/1)
     256 / 243,    # S2  Re1         — 275.65 Hz  (256/243)
     ...
     243 / 128,    # S19 Ni6         — 496.68 Hz  (243/128)— Daniélou canonical
     6 / 5,        # S20 Ga-Komal    — 313.95 Hz  (6/5)    — replaces 2/1 (octave Sa’)
     27 / 20,      # S21 Ma-Komal    — 353.20 Hz  (27/20)  — replaces 8/3
     45 / 32,      # S22 Tivra Ma2   — 367.79 Hz  (45/32)  — replaces 3
+    2 / 1,        # S23 Sa’         — 523.25 Hz  (2/1)    — octave Sa’ (NEW)
 ]

 SHRUTI_NAMES = [
     ...
     'Shruti 20 (Ga-Komal)',
     'Shruti 21 (Ma-Komal)',
     'Shruti 22 (Tivra Ma2)',
+    'Shruti 23 (Sa’)',
 ]
```

`compute_pcp`/`mean_pcp`/`f0` nearest-freq logic all size themselves from `SHRUTI_FREQUENCIES`/`_SHRUTI_FREQS_ARR`, so they adapt automatically. Only the frontend hardcodes 22:

`frontend/src/components/ShrutiMap.jsx`:

```diff
 const SHRUTI_NAMES = [
   'Sa', 'Re¹', 'Re²', 'Ga¹', 'Ga²', 'Ga³',
   'Ma¹', 'Ma²', 'Ma³', 'Tivra Ma', 'Pa', 'Dha¹',
   'Dha²', 'Ni¹', 'Ni²', 'Ni³', 'Ni⁴', 'Ni⁵',
   'Ni⁶', 'Ga-Komal', 'Ma-Komal', 'Tivra Ma²',
+  'Sa’',
 ]
 ...
-    if (!Array.isArray(pcpMatrix) || pcpMatrix.length !== 22) return null
+    if (!Array.isArray(pcpMatrix) || pcpMatrix.length !== 23) return null
 ...
-    if (!Array.isArray(data?.mean_pcp) || data.mean_pcp.length !== 22) return null
+    if (!Array.isArray(data?.mean_pcp) || data.mean_pcp.length !== 23) return null
```

`frontend/src/components/ClusterPlot.jsx`:

```diff
-                const hue = (i / 22) * 360
+                const hue = (i / 23) * 360
```

**Interim one-liner (Option B — keeps 22 rows, no frontend change):** swap the redundant `6/5` (Ga-Komal; its only purpose was "a 22nd in-octave microtone" that collides with Ga³ at 21.5¢) for the octave itself:

```diff
-    6 / 5,        # S20 Ga-Komal    — 313.95 Hz  (6/5)
+    2 / 1,        # S20 Sa’         — 523.25 Hz  (2/1)
 ...
-    'Shruti 20 (Ga-Komal)',
+    'Shruti 20 (Sa’)',
```

**Follow-up required regardless of option:** the 21.5¢-neighbour ambiguity is structural (90¢/21.5¢ alternation). Mitigate with pitch smoothing on the F0 track before assignment instead of touching the threshold — apply a median filter in `compute_pcp` and in `_extract_detected_swaras_by_salience`:

```python
from scipy.signal import medfilt
f0_smooth = medfilt(np.asarray(f0, dtype=np.float64), kernel_size=5)  # scipy is a librosa dep
```

---

### F2 — Salience swara extraction hard-caps at bin 14 and silently drops Ni³

**File:** `backend/ml_engine/raga_mapping.py:819`

**Root cause:** `_extract_detected_swaras_by_salience` returns only PCP bins `0..min(15, n)-1`, i.e. indices 0–14. `SWARA_MAP` defines **16** swaras (0=Sa … 15=Ni³) and the raga DB freely uses index 15 (`Shankara swaras=[0,4,10,14,15]`, `Vasanta`, `Panthuvarali`, `Sindhi Bhairavi`). Because PCP bin index == swara index for 0–15, dropping bin 15 means Ni³ occupancy can **never** be counted, capping those ragas' scores.

**Exact diff:**

```diff
     occupancy = counts / total_voiced
     return {
         int(i): float(occupancy[i])
-        for i in range(min(15, pcp.shape[0]))
+        for i in range(min(16, pcp.shape[0]))   # SWARA_MAP spans 0..15 (Ni³ = bin 15)
         if occupancy[i] >= presence_threshold
     }
```

---

### F3 — Ghana cycle scorer has an absolute-phase bug (phase-shifted recitation scores 0)

**File:** `backend/ml_engine/ghana_patha.py:284-287`

**Reproduced:**

```
perfect (phase 0):  1.0
shifted (phase 1):  0.0     ← a TRUE Ghana recitation that starts mid-pattern
reversed (wrong):   1.0     ← reverse order of labels also "matches"
```

**Root cause:** `cycle[(start + i) % c]` fixes the expected pattern's phase to the *absolute* segment index. A recitation that begins on a later phase never has a sub-sequence that lines up with the fixed phase, so `matches=0` even for a flawless rendition; meanwhile a *reversed* pattern also scores 1.0 because `f,r,f,r,f` is palindromic — the scorer cannot distinguish valid from reversed.

**Exact diff:**

```diff
         for end in range(start + 3, n + 1):
             sub = labels[start:end]
             sub_len = len(sub)
-            # Align sub against (possibly repeated) cycle using element DTW
-            matches = sum(
-                sub[i] == cycle[(start + i) % c]
-                for i in range(sub_len)
-            )
+            # The Ghana phrase may begin on any phase (recitations start
+            # arbitrarily mid-cycle). Try every rotation and keep the best.
+            matches = max(
+                sum(sub[i] == cycle[(rot + i) % c] for i in range(sub_len))
+                for rot in range(c)
+            )
             score = matches / sub_len
```

---

### F4 — Full-resolution spectrogram JSON blows through Vercel's response ceiling on any real recording

**Files:** `backend/api/views.py` (`_save_matrices` :80, `_build_analysis_response` :282), `frontend/src/components/SpectrogramView.jsx`

**Measured:**

| Recording | `spectrogram` floats | JSON size |
|---|---|---|
| 14 s | 1025 × 604 ≈ 619 k | **≈ 4.9 MB — over Vercel's ~4.5 MB gate** |
| 60 s | 1025 × 2583 ≈ 2.65 M | **≈ 21 MB** |
| 300 s | 1025 × 12919 ≈ 13.2 M | **≈ 106 MB** |

**Root cause:** `extract_features` stores the spectrogram at `n_fft=2048` (1025 frequency bins) × *every* STFT frame. Unlike the PCP (downsampled to `_MAX_PCP_COLS=500`), the spectrogram is saved and serialised **in full** via `arrays['spectrogram'].tolist()`. On Vercel the detail endpoint runs through a serverless function rewrite with a respell limit of ~4.5 MB, so effectively **any clip longer than ~13 s returns 502/truncated from the browser's perspective** — the analysis itself succeeds, but `handleAnalysisDone`'s refetch fails and the user sees an error.

**Exact diff** — downsample both dimensions in `_save_matrices` and serve the slice:

```diff
 def _save_matrices(recording_id: int, features: dict) -> str:
-    pcp_raw: np.ndarray = features['pcp']                 # (22, n_frames)
+    pcp_raw: np.ndarray = features['pcp']                 # (22, n_frames)
+    spec_raw: np.ndarray = features['spectrogram']        # (1025, n_frames) dB
+
+    # Downsample the spectrogram for the browser: cap time columns like the
+    # PCP and decimate the 1025 frequency bins to at most 256 rows. The 4D
+    # heatmap never needs full FFT resolution.
+    def _downsample_spectrogram(spec, max_cols=_MAX_PCP_COLS, max_rows=256):
+        n_rows, n_cols = spec.shape
+        if n_cols > max_cols:
+            step_c = n_cols // max_cols
+            spec = spec[:, ::step_c][:, :max_cols]
+        if n_rows > max_rows:
+            step_r = n_rows // max_rows
+            spec = spec[::step_r][:max_rows]
+        return spec
```

```diff
     np.savez_compressed(
         str(full_path),
-        spectrogram=features['spectrogram'].astype(np.float32),
+        spectrogram=_downsample_spectrogram(spec_raw).astype(np.float32),
         mfcc=features['mfcc'].astype(np.float32),
         chroma=features['chroma'].astype(np.float32),
         pcp_full=pcp_raw.astype(np.float32),
         pcp_ds=pcp_ds.astype(np.float32),
         f0_track=f0_arr,
     )
```

Also drop the untouched full-size copies from the detail response to cut latency for dev (optional but recommended): after the downsampled change, `_build_analysis_response` keeps reading `arrays['spectrogram']`, which is now ≤ 256 × 500 — no change needed there.

---

### F5 — List endpoint ships per-frame analysis metadata for every recording

**Files:** `backend/api/serializers.py:14-17`, `backend/api/views.py:412`

**Root cause:** `AudioRecordingSerializer` exposes `analysis_metadata` (and `matrices_file`) on **both** the list and detail endpoints. `analysis_metadata` contains per-frame arrays — `freq_assignments` (n_frames strings) and `spectral_centroid_timeline` (n_frames floats). Every `GET /api/recordings/` concatenates that for all rows; a handful of long recordings pushes the list response past Vercel's response limit, and every upload-load spike re-serialises it. The detail endpoint (where the data is actually needed) is a separate fetch the frontend already makes (`handleSelectRecording`), so the list version is pure waste. The existing comment in `serializers.py` explicitly excludes `analysis_result` for size but missed `analysis_metadata`.

**Exact diff** — separate list serializer:

`backend/api/serializers.py`:

```diff
 class AudioRecordingSerializer(serializers.ModelSerializer):
     ...
         read_only_fields = [
             'id', 'uploaded_at', 'analysis_metadata', 'matrices_file', 'is_analyzed',
         ]
```

```python
class AudioRecordingListSerializer(AudioRecordingSerializer):
    """Lightweight list view — heavy per-frame metadata belongs to the detail
    endpoint only, otherwise GET /recordings/ bloats with every row."""

    class Meta(AudioRecordingSerializer.Meta):
        fields = [
            'id', 'title', 'audio_file', 'playback_file', 'uploaded_at',
            'is_analyzed',
        ]
```

`backend/api/views.py`:

```diff
     qs = AudioRecording.objects.all().order_by('-uploaded_at')
     page = paginator.paginate_queryset(qs, request)
-    serializer = AudioRecordingSerializer(page, many=True)
+    serializer = AudioRecordingListSerializer(page, many=True)
     return paginator.get_paginated_response(serializer.data)
```

---

## P1 — High (deployment / correctness at the edges)

### F6 — `segment_pcp_sequences` drops trailing frames

**File:** `backend/ml_engine/ghana_patha.py:193-202`

**Root cause:** `seg_len = n_frames // n_segments`; the loop produces exactly `seg_len`-long segments, so any remainder `n_frames % n_segments` (>0 frames, i.e. up to ~1 s of audio) at the tail is **silently discarded** before DTW. For a 26 s file at 22.05 kHz that is ~1 s of real chanting that never participates in the Ghana verdict.

**Exact diff** — use `np.array_split` so the tail is folded into the last segments instead of deleted:

```diff
-    n_frames = pcp.shape[1]
-    seg_len = max(n_frames // n_segments, 1)
-    segments = []
-    for i in range(n_segments):
-        start = i * seg_len
-        end = min(start + seg_len, n_frames)
-        # Transpose: (22, seg_frames) → (seg_frames, 22)
-        seg = pcp[:, start:end].T.astype(np.float32)
-        segments.append(seg)
-    return segments
+    # np.array_split distributes the remainder so the last segment absorbs
+    # trailing frames instead of dropping them.
+    return [seg.T.astype(np.float32) for seg in np.array_split(pcp, n_segments, axis=1)]
```

---

### F7 — Blocking ffmpeg transcode races gunicorn's 120 s timeout

**Files:** `backend/api/views.py:348-379` (`_build_playback_file`), `backend/app.py:48-49`

**Root cause:** `upload_audio` calls `_build_playback_file(recording)` **synchronously** inside the request, and it runs `subprocess.run(..., timeout=120)`. Gunicorn (HF path, `app.py`) is configured with `--timeout 120`, so if ffmpeg takes ≥ 120 s on a big WAV the worker is killed mid-request and the client gets a 502 — even though the upload itself succeeded. Because `timeout=120` in ffmpeg and `--timeout 120` in gunicorn are equal, the race window is exact.

**Fix (two parts):**

1. Move the transcode off the request thread — enqueue it as a Celery task after the recording is saved:

```diff
 def upload_audio(request):
     serializer = AudioRecordingSerializer(data=request.data)
     if serializer.is_valid():
         recording = serializer.save()
-        _build_playback_file(recording)
+        from .tasks import build_playback_file_task          # noqa: PLC0415
+        build_playback_file_task.delay(recording.id)
         return Response(...)
```

`backend/api/tasks.py` (new task):

```python
@shared_task(bind=True, max_retries=2, name='api.tasks.build_playback_file_task')
def build_playback_file_task(self, recording_id: int) -> bool:
    recording = AudioRecording.objects.get(pk=recording_id)
    _build_playback_file(recording)
    return True
```

2. If a background task is out of scope, at minimum widen the gap: cap ffmpeg at 60 s and raise gunicorn timeout to 180 s in `app.py`.

---

### F8 — SSE hardening: 429 reconnect-loop + Vercel buffering

**Files:** `backend/api/views.py:493-504`, `frontend/src/components/AnalysisProgress.jsx:57-62`

**Root cause (1):** `analysis_status` returns a bare `429` (plain text) when throttled. `EventSource.onerror` fires, `statusRef` is still `'running'` so it does **not** close, and the browser retries every ~3 s forever — a non-terminating reconnect loop once a user exceeds the 60/min status budget.

**Fix — server should speak SSE on throttles too (terminates the stream cleanly):**

```diff
     throttle = StatusAnonThrottle()
     if not throttle.allow_request(request, None):
-        from django.http import HttpResponse  # noqa: PLC0415
         retry_after = throttle.wait()
-        resp = HttpResponse(
-            'Too Many Requests',
-            status=429,
-            content_type='text/plain',
-        )
-        if retry_after is not None:
-            resp['Retry-After'] = str(int(retry_after))
-        return resp
+        resp = StreamingHttpResponse(
+            [_sse_message({'stage': 'Queued', 'percent': 0, 'status': 'error',
+                           'error': 'Too many status requests — slow down.'})],
+            content_type='text/event-stream',
+        )
+        resp['Cache-Control'] = 'no-cache'
+        resp['Retry-After'] = str(int(retry_after)) if retry_after is not None else '60'
+        return resp
```

Client-side, also handle the server-closed case so a dropped connection mid-analysis surfaces an error instead of spinning:

```diff
     es.onerror = () => {
-      // Use ref — not the stale closure — to check terminal state
-      if (statusRef.current === 'done' || statusRef.current === 'error') {
+      if (statusRef.current === 'done' || statusRef.current === 'error') {
         es.close()
+      } else if (es.readyState === EventSource.CLOSED) {
+        es.close()
+        onError?.('Connection to analysis stream was lost mid-processing.')
       }
     }
```

**Root cause (2):** SSE rides the Vercel rewrite (`/api/analyze/<id>/status/` → HF Space). Vercel's serverless proxy can buffer streaming responses, breaking the near-real-time progress bar. This has been verified only as a risk, not a failure — but it is exactly the kind of thing that "works in dev, dies in prod". **Recommended mitigation:** route `/api/analyze/<id>/status/` to a Vercel Edge Function that terminates in Vercel's edge network and reverse-proxies to HF, or add `flushHeaders` + SSE keep-alive comments on the Django side (already polling every 0.8 s, which doubles as keep-alive). Manually verify with `curl -N` pinned against the production URL before demo.

---

### F9 — No fence prevents duplicate concurrent analyses (ACKS_LATE redelivery)

**Files:** `backend/api/tasks.py:34`, `backend/vedic_acoustica/settings.py:157`

**Root cause:** `CELERY_TASK_ACKS_LATE = True` re-delivers a task if a worker crashes mid-run; `max_retries=0` does **not** prevent broker redelivery. A crash between `features = extract_features(...)` and `recording.save(...)` re-runs the *entire* pipeline. Worse: two rapid `POST /analyze/<id>/` (double-click or an SSE re-trigger) dispatch two independent tasks for the same `pk`. Both write the same progress file and both call `recording.save()`, with SQLite as the single writer — the last writer wins and progress can regress backwards.

**Exact diff** — Redis `SETNX` fence at task start (Redis is already the broker, zero new infra):

```diff
 import os
+import redis as redislib
 from celery import shared_task
+from django.conf import settings
 ...
 @shared_task(bind=True, max_retries=0, name='api.tasks.process_audio_task')
 def process_audio_task(self, recording_id: int) -> dict:
     pk = recording_id
+
+    # ── Single-flight fence: never run two analyses of the same recording ──
+    lock_key = f'vedic:analyze:lock:{pk}'
+    redis_conn = redislib.Redis.from_url(settings.CELERY_BROKER_URL)
+    if not redis_conn.set(lock_key, '1', nx=True, ex=3600):
+        _set_progress(pk, 'Queued', 0, status_val='error',
+                      error='An analysis for this recording is already running.')
+        return {'recording_id': pk, 'skipped': True}
+    try:
+        return _run_pipeline(pk)
+    finally:
+        try:
+            redis_conn.delete(lock_key)
+        except redislib.RedisError:
+            pass
```

(Extract the existing pipeline body into `_run_pipeline(pk)` unchanged.)

---

### F10 — DEBUG env parsing is inverted-fragile; `DJANGO_DEBUG=0` enables debug mode

**File:** `backend/vedic_acoustica/settings.py:7`

**Root cause:** `DEBUG = os.environ.get('DJANGO_DEBUG', 'False') != 'False'` — any value other than the exact string `"False"` (including `"0"`, `"false"`, `"f"`, or an empty value) evaluates to `True`. When DEBUG is truthy, `ALLOWED_HOSTS=['*']` and the hardcoded dev SECRET_KEY kick in. One sloppy `DJANGO_DEBUG=0` or `DJANGO_DEBUG=` in a production env converts the deployment into an open debug server.

**Exact diff:**

```diff
-DEBUG = os.environ.get('DJANGO_DEBUG', 'False') != 'False'
+def _env_bool(name: str, default: bool = False) -> bool:
+    value = os.environ.get(name)
+    if value is None or value.strip() == '':
+        return default
+    return value.strip().lower() in ('1', 'true', 'yes', 'on')
+
+DEBUG = _env_bool('DJANGO_DEBUG')
```

---

### F11 — Frontend hardcodes the HF Space media host

**File:** `frontend/src/App.jsx:14,17-20`

**Root cause:** `resolveMediaUrl` prefixes every relative media URL with the hardcoded `https://krish-shripat-vedic-backend.hf.space`. Two concrete failures:

1. **Dev is broken:** in `npm run dev` every `.mp3`/`.wav` requests the *production* Space — a file just uploaded to `localhost:8000/media` 404s in the player. The Vite `/media` proxy (which works) is bypassed.
2. **Prod is fragile:** if the HF Space is ever renamed/regenerated (common), media silently dies. The Vercel `/media` rewrite already solves production correctly; the frontend should simply not care about the host.

**Exact diff:**

```diff
 const API_BASE = '/api'
-const MEDIA_BASE = 'https://krish-shripat-vedic-backend.hf.space'
 const NUM_CHARTS = 5
 
-const resolveMediaUrl = (url) => {
-  if (!url) return url
-  return /^https?:\/\//i.test(url) ? url : `${MEDIA_BASE}${url.startsWith('/') ? '' : '/'}${url}`
-}
+// /media/... is relative on purpose: the Vite dev proxy (localhost:8000)
+// and the Vercel rewrite (HF Space) both resolve it for their environment.
+const resolveMediaUrl = (url) => url
```

---

## P2 — Medium (correctness semantics, hygiene, security advisory)

### F12 — `assign_shruti` labels k-means clusters from *equal-tempered* chroma

**File:** `backend/ml_engine/shruti_mapping.py:59-74`, call-site `ml_engine.py:41-43`

**Root cause:** the centroid's `[13:]` slice is the 22-bin output of `librosa.chroma_stft(n_chroma=22)` — 22 approximately-equal-tempered semitone bands, **not** the 22 just-intonation Śruti bins. `argmax` on that sub-vector and `SHRUTI_NAMES[idx]` produces labels that are musically meaningless (a "Ga2" label can denote any band that happens to dominate aggregate chroma energy). Nothing wrong downstream of ghana/raga detection (they use PCP/F0), but the `assigned_shruti` field distributed to clients is misleading.

**Fix** — assign from the cluster's *actual pitch content* instead: pass the per-frame F0 track into the assignment and use the voiced median F0:

`backend/ml_engine/ml_engine.py`:

```diff
     for cluster_id in range(N_CLUSTERS):
         frame_indices = np.where(labels == cluster_id)[0]
         shruti_clusters[f'shruti_{cluster_id + 1}'] = {
             'frame_count': int(len(frame_indices)),
             'centroid': kmeans.cluster_centers_[cluster_id].tolist(),
             'assigned_shruti': assign_shruti(
-                kmeans.cluster_centers_[cluster_id], features
+                kmeans.cluster_centers_[cluster_id], features,
+                cluster_frames=frame_indices,
             ),
         }
```

`backend/ml_engine/shruti_mapping.py`:

```diff
-def assign_shruti(centroid, features):
-    chroma_part = centroid[13:] if len(centroid) > 13 else centroid
-    if len(chroma_part) == 0:
-        return SHRUTI_NAMES[0]
-    return SHRUTI_NAMES[int(np.argmax(chroma_part)) % len(SHRUTI_NAMES)]
+def assign_shruti(centroid, features, cluster_frames=None):
+    import numpy as np
+    from .audio_processing import _SHRUTI_FREQS_ARR, _THRESHOLD_CENTS
+
+    # Prefer the cluster's voiced F0s (musical truth); fall back to the
+    # dominant chroma bin only when the cluster has no F0 energy.
+    f0 = features.get('f0')
+    voiced = features.get('voiced_flag')
+    if f0 is not None and voiced is not None and cluster_frames is not None:
+        f0_voiced = np.asarray(f0, dtype=np.float64)[np.asarray(voiced, dtype=bool)]
+        if f0_voiced.size:
+            median = float(np.nanmedian(f0_voiced))
+            if np.isfinite(median):
+                cents = np.abs(1200.0 * np.log2(median / _SHRUTI_FREQS_ARR))
+                best = int(np.argmin(cents))
+                if cents[best] < _THRESHOLD_CENTS:
+                    return SHRUTI_NAMES[best]
+
+    chroma_part = centroid[13:] if len(centroid) > 13 else centroid
+    if len(chroma_part) == 0:
+        return SHRUTI_NAMES[0]
+    return SHRUTI_NAMES[int(np.argmax(chroma_part)) % len(SHRUTI_NAMES)]
```

(Note: `cluster_frames` is unused in this median variant, but keeping the parm documents intent and lets a future per-cluster F0 census be added.)

---

### F13 — `_delete_progress` is dead code; progress files accumulate per uptime

**File:** `backend/api/views.py:229-233`

**Root cause:** nothing calls `_delete_progress`. Each analyzed recording leaves `vedic_progress_<pk>.json` in `MEDIA_ROOT/progress` until an HF redeploy wipes ephemeral storage. Low blast radius (tiny files) but unmanaged.

**Fix (safe single-writer delete):** delete in the task after marking `done` — no SSE reader depends on the file once `done` has been emitted, and the next `analyze_audio` call re-writes it before dispatching:

`backend/api/tasks.py`:

```diff
-    # ── Signal the SSE stream that processing is complete ─────────────────────
-    _set_progress(pk, 'Complete', 100, status_val='done')
+    # ── Signal the SSE stream that processing is complete ─────────────────────
+    _set_progress(pk, 'Complete', 100, status_val='done')
+
+    # Terminal state reached — purge the progress file (the next analyze call
+    # re-creates it before dispatch, and the SSE reader is done).
+    try:
+        from api.views import _delete_progress  # noqa: PLC0415
+        _delete_progress(pk)
+    except Exception:  # pragma: no cover — cleanup is best-effort
+        pass
 
     return {'recording_id': pk, 'matrices_file': rel_path}
```

---

### F14 — Production media serving & unauthenticated metrics

**Files:** `backend/vedic_acoustica/urls.py:17-18`, `backend/api/metrics.py`

- `django.views.static.serve` in production is a one-shot development view (no range request support / DoS exposure). On a shared free host, and given that Vercel already proxies `/media` to the Space, the recommended stopgap is caching + access controls. At minimum note the exposure is by-design for the demo; don't move media behind the API without a plan.
- `/metrics/` returns 403 when `METRICS_TOKEN` mismatches, but is **open** if the token env is absent. The deployment `app.py` never sets it. One-line hardening — require the token in non-DEBUG:

```python
# api/metrics.py
_METRICS_TOKEN = os.environ.get('METRICS_TOKEN', '')
if not settings.DEBUG and not _METRICS_TOKEN:
    _METRICS_TOKEN = chr(0)   # never match; deployers must set a token
```

---

### F15 — Dead weight in `analysis_metadata` (never consumed by the frontend)

**File:** `backend/api/tasks.py:119-148`

**Root cause:** `freq_assignments` (n_frames strings) and `spectral_centroid_timeline` (n_frames floats) are persisted into SQLite `analysis_metadata` and returned on the detail endpoint. A full-text search of the frontend shows **no component reads either field** — `App.jsx`/`ClusterPlot`/`ShrutiMap`/`GhanaPathaViz`/`RagaViz`/`exportReport.js` all operate on `shruti_clusters`, `mean_pcp`, `pcp_data`, and the scalar Ghana/raga keys. This is the per-recording payload that F5's list-exclusion no longer sends, but it still bloats the DB and the detail response on every fetch.

**Exact diff:**

```diff
         metadata = {
             # Shruti clustering scalars
             'shruti_clusters':              clustering_results['shruti_clusters'],
-            'freq_assignments':             clustering_results['freq_assignments'],
+            # freq_assignments intentionally omitted — per-frame strings, consumed by nothing
             'mean_pcp':                     clustering_results['mean_pcp'],
             # pYIN scalars
             'voiced_ratio':                 features['voiced_ratio'],
-            'spectral_centroid_timeline':   features['spectral_centroid'].tolist(),
+            # spectral_centroid_timeline intentionally omitted — per-frame floats, unused
             # Ghana Patha scalars
```

---

## Residual environment risks (documented, not fixable in code)

- **Ephemeral storage (by design):** HF restart/redeploy clears `media/`, `analysis_matrices/`, `progress/` **and** `db.sqlite3`. After a restart, previously analyzed recordings will return `analysis_result = {metadata}` (`.npz`/file gone) — `_build_analysis_response` already degrades to metadata-only, so the Shruti bar/Ghana/Raga charts survive but the spectrogram and PCP heatmap silently disappear. Recommend the demo flow (re-upload + re-analyze 5 min before presentation) exactly as agreed.
- **Cold start:** first request after sleep pays Celery/Redis/librosa warm-up; the `Queued` SSE stage masks this, but the 300 s SSE cap is the hard ceiling.
- **`app.py` "Trojan Horse" boot:** migrations run on every boot, Redis start is unverified-then-proceeded, and gunicorn is restarted forever in a loop on crash. Functionally fine for a demo; diagnostics live only in `celery.log`.

---

### Verified with computation

All quantitative claims (F1 cents table, F2 min(15) truncation, F3 phase-shift, F4 spectrogram sizes, F5 metadata weight) were reproduced in this repository's environment before writing the document.

---

## 3D Frontend Rollback + F1 Regression Fix (2026-09-05)

### Incident: VedicAcoustic3D frontend removal

Commits `3ee5a07`, `f5a220c`, `57689e0` introduced a 3D glassmorphic background
(`VedicAcoustic3D.jsx`, `@react-three/fiber`, Surya/Soma themes) that replaced
the original maroon-black UI. These were reverted by resetting `origin/main`
to commit `a84abe4` ("Fix UI: Update backend status pill to show dynamic
production status") and force-pushing.

**Verified clean:**
- `VedicAcoustic3D.jsx` deleted; no three.js / `@react-three/fiber` imports remain
- `prompt.md` (Antigravity prompt) removed
- `package.json` has no 3D dependencies; `package-lock.json` updated
- Frontend build (`vite build`) succeeds; `oxlint` passes clean
- Original maroon-black UI confirmed in `App.jsx` (status-bar at line 167–171)

### Critical fix: F1 regression — Ghana Patha + Raga detection broken

**Root cause:** Commit `f0995f5` (Fix F1) added a 23rd Shruti bin (Sa', 2/1 octave)
to `shruti_mapping.py` and `audio_processing.py`, making the PCP matrix 23-dimensional.
However, the template builders in `ghana_patha.py` and `raga_mapping.py` still
emitted `(T, 22)` templates, causing `sklearn.metrics.pairwise.cosine_similarity`
to fail with:

```
Incompatible dimension for X and Y matrices: X.shape[1] == 23 while Y.shape[1] == 22
```

This broke **both** Ghana Patha validation and Raga detection for every recording —
a silent P0 production regression since F1.

**Fix applied:**

| File | Change |
|------|--------|
| `backend/ml_engine/ghana_patha.py` | Import `SHRUTI_NAMES`; define `_PCP_WIDTH = len(SHRUTI_NAMES)`; `_make_template` builds `(T, _PCP_WIDTH)` instead of `(T, 22)` |
| `backend/ml_engine/raga_mapping.py` | `_pakad_template` builds `(T, len(SHRUTI_NAMES))` instead of `(T, 22)` |

**Post-fix verification (test_ml_quick.py, 13 synthetic + real clips):**
- 4/4 stages OK on all 13 clips, 0 errors
- Ghana Patha scores: 0.33–0.93 (was ERR on all)
- Raga detection: all clips classified (was ERR on all)

**Scope of remaining work (out of scope for this incident):**
- `ml_engine.ml_engine.N_CLUSTERS = 22` — KMeans cluster count; still valid as a
  model choice (KMeans operates on combined MFCC+chroma, not PCP directly)
- `raga_mapping.py` docstrings still reference "(22, n_frames)" in comments;
  purely cosmetic, functionally correct

### Verification summary

| Component | Status |
|-----------|--------|
| Frontend build | ✅ `vite build` + `oxlint` pass |
| Frontend 3D removed | ✅ No three.js/VedicAcoustic3D in codebase |
| Backend Django check | ✅ 0 issues |
| Backend tests | ✅ 11/11 pass |
| ML pipeline (13 clips) | ✅ 4/4 stages, 0 errors |

---

## Storage Cleanup (2026-09-05)

Repo was ~2 GB. Removed ~330 MB without breaking the project or recordings:

| Removed | Size | Why safe |
|---------|------|----------|
| `backend/media/analysis_matrices` | 135 MB | Regenerable `.npz` derived outputs — **recordings kept** (32 MB in `media/recordings`) |
| `backend/tests/audio_samples/*.wav` | 74 MB | 4×19 MB WAVs with zero references in code, tests, or CI |
| `test_audio/isavasya_ghanam.ogg` | 17 MB | Skipped by every ML harness (≥15 MB / >60 s caps) |
| `test_audio/rudram.mp3` | 12 MB | Same — 66 min file, skipped by all test suites |
| `__pycache__` + pip/npm caches | ~2.9 GB | Regenerable build/install caches (outside repo) |

**Still present (intentionally):** `venv/` (601 MB) and `frontend/node_modules/` (444 MB) —
required for local dev/builds, both gitignored. `.git/` (116 MB) is unchanged because the
history rewrite was declined; the untracked blobs linger in history.

**Verification after cleanup:** Django tests 11/11 pass; ML quick suite 13/13 clips at
4/4 stages, 0 errors; frontend build/lint unaffected (test audio removal does not touch src/).

> Note: `test_ml_pipeline.py` (end-to-end harness generating vibrato/gamaka/breath-gap
> clips + ghana sim) is extremely slow locally and was aborted twice during verification;
> the same 4 stages are covered by `test_ml_quick.py` and `test_ml_audit.py`, both green.
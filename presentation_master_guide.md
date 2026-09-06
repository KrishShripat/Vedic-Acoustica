# 🎯 Vedic Acoustica — Presentation Master Guide

> **For:** The 3-person presenting team | **Project:** Vedic Acoustica (5th-semester IT project, A. P. Shah Institute of Technology)
> **Audience:** Academic judges — some technical, some not. Assume they know nothing about Indian classical music or ML.
>
> **Starting point for beginners:** read `PRESENTATION_README.md` first — it explains the *entire* project from zero (where the frequencies come from, how the accuracy works, every graph, the tech stack). Come back here to learn *how to present it*.

**This guide teaches you:**
1. How to explain the project in simple words (60-second pitch)
2. What each piece of code does and how to *show* it
3. Where to go on the live site and what to click to demo it
4. How the backend runs on Hugging Face (and what that even means)
5. How to answer judge questions with confidence
6. How to counter questions you don't know
7. **How to split the whole presentation across 3 people** (§19) and **how to coach them** (§20)

---

## Table of Contents

1. [Before You Start — 4 Things to Memorise](#1-before-you-start)
2. [The Elevator Pitch — Simple Words](#2-the-elevator-pitch)
3. [The Whole Project in 10 Minutes — Your Story](#3-the-story)
4. [System Architecture — 3 Levels](#4-system-architecture)
5. [Live Demo Script — Where to Go & What to Click](#5-live-demo-script)
6. [Tech Stack — The Full Honest List](#6-tech-stack)
7. [The ML Pipeline Explained Like You're 12](#7-the-ml-pipeline)
8. [The 5 Charts — What Judges See on Screen](#8-the-5-charts)
9. [Key Code — Show & Explain](#9-key-code)
10. [The Hugging Face Deployment — The "Trojan Horse" Trick](#10-hugging-face-deployment)
11. [Engineering Challenges — Your "Flex" Moments](#11-engineering-challenges)
12. [Critical Numbers to Memorise](#12-critical-numbers)
13. [Q&A Defense — Model Answers](#13-qa-defense)
14. [Counter-Question Playbook](#14-counter-question-playbook)
15. [Pull-quote One-Liners](#15-pull-quote-one-liners)
16. [Presentation Run Plan (Timeline)](#16-run-plan)
17. [What NOT to Say](#17-what-not-to-say)
18. [24-Hour Pre-Presentation Checklist](#18-checklist)
19. [Splitting This Across 3 People](#19-splitting-across-3-people)
20. [Coach's Kit — Teaching Your Teammates](#20-coachs-kit)

---

## 1. Before You Start — 4 Things to Memorise

If you remember nothing else, remember these four lines:

1. **What it is:** *"Vedic Acoustica converts an ancient oral-only tradition (Vedic chanting) into **objective, measurable data** using machine learning."*
2. **The 3 things it detects:** ① microtonal notes (**Shrutis**) ② whether the recitation pattern is correct (**Ghana Patha**) ③ which **raga** the melody follows.
3. **The clever part:** The 22-Shruti system is *older and more precise* than Western music's 12 notes — so we had to **build our own math** because no Western music library supports it.
4. **Where it runs:** Frontend on **Vercel**, backend ML engine on **Hugging Face** (a free GPU cloud), sync'd via one URL.

> If a judge asks "what did YOU build?" — your answer is: *"I built a full-stack product: a React dashboard, a Django API, and an ML engine that detects ancient Indian microtones. It's deployed live on two cloud platforms and passes objective tests."*

---

## 2. The Elevator Pitch

### The 30-second version (open with this)

> *"Imagine a student learning Vedic chanting — an oral tradition that is 3,500 years old. For thousands of years, the only way to know if you're chanting correctly is to find a guru and hope for **subjective** feedback. Vedic Acoustica replaces that with **objective, mathematical acoustic analysis**. You upload a recording, and our ML pipeline tells you: **which microtonal notes** you're hitting, **whether your recitation follows the correct pattern**, and **which raga** your melody matches — all backed by signal processing and ML, not opinion."*

### The 10-second version (for when they interrupt)

> *"We built a website that analyses Vedic chanting — it tells you the exact microtonal pitch, checks if the chanting pattern is correct, and identifies the raga. It runs on cloud servers for free."*

### Key phrases to use vs avoid

| Say This | Instead Of |
|---|---|
| "Objective, reproducible analysis" | "We check if it sounds right" |
| "22 microtonal intervals (Shrutis)" | "Musical notes" |
| "Research-grade acoustic tool" | "Music app" |
| "Cultural preservation through technology" | "Digitising music" |
| "ML pipeline" | "AI magic" |

### Who is this for? (answer this if they ask "who uses it?")

- **Vedic scholars & gurukuls** — validate students without needing the guru physically present
- **Musicology researchers** — quantitative data for papers about Indian microtonal systems
- **Students of traditional arts** — a self-practice tool with instant feedback
- **Cultural preservation bodies** — digitising endangered oral traditions before they vanish

### The problem → solution table

| The Problem (old way) | Our Solution |
|---|---|
| A guru says "your Ga is flat" — subjective, can't be repeated or verified | We detect the **exact Shruti** using pYIN pitch tracking at ±25 cents precision |
| No way to measure "how correct" a chant is | **DTW pattern matching** produces a 0–100% structural conformity score |
| Identifying a raga takes years of trained listening | **Directional swara scoring** against a 44-raga database with phrase matching |
| Analysis needs expensive studio equipment & expert supervision | Upload a phone recording → full analysis in under 2 minutes |

---

## 3. The Story

> *This is your "narrative spine". Memorise it as a story, not bullet points. Judge questions almost always come back to this story.*

**Act 1 — The Problem (1 minute):**
> "Western music has 12 notes per octave. But ancient Indian music recognised **22 notes** — called Shrutis. Some of these are so close together the gap is smaller than a human hair in pitch terms. For 3,500 years this music survived by **oral tradition alone** — passed from guru to student. There was no written form, and no way to *measure* correctness. If the guru passed away, the exact pitch knowledge could die with him. We wanted to **preserve and verify this knowledge with computers**."

**Act 2 — The Challenge (1 minute):**
> "Here's the engineering problem: every existing music analysis library — Spotify's basic-pitch, music21, etc. — is built for the **12-note Western system**. None of them can see these 22 microtones. So we had to build our **own pitch-analysis math** from scratch — a custom 22-bin Pitch Class Profile, custom clustering, and custom pattern-matching algorithms."

**Act 3 — The Solution (2 minutes):**
> "We built a 4-stage ML pipeline. Stage 1 extracts the acoustic 'fingerprint' of the audio — pitch, spectrum, tempo. Stage 2 clusters all the frames of sound into 22 microtonal buckets to find which Shrutis you sang. Stage 3 checks whether your recitation follows the correct **Ghana Patha** pattern (a 3,500-year-old error-correction technique). Stage 4 identifies which **raga** your melody belongs to. All of this is served through a modern web app — React frontend, Django backend, async workers — and it's **deployed live on the internet**."

**Act 4 — The Proof (1 minute):**
> "We don't just claim it works — we have **objective tests**: synthetic audio files with known pitches that the pipeline identifies correctly, test clips for vibrato, breath gaps, and more. The app renders 5 interactive scientific visualisations for every analysis."

---

## 4. System Architecture

> *Have ONE architecture diagram on your slide. Explain it at three depths depending on who asks.*

### Level 1 — The "restaurant" analogy (for non-technical judges)

| Component | Restaurant Analogy | Real role |
|---|---|---|
| React Frontend (Vercel) | The **dining room & menus** | Where the user sees charts and uploads audio |
| Django Backend | The **maître d' / system controller** | Takes orders (API requests), manages data, serves results |
| Celery Worker | The **kitchen** | Does the heavy ML cooking (30–120 seconds per analysis) |
| Redis | The **ticket rail** between waiter and kitchen | Message queue: "analyse this audio" tickets; also stores results |
| Hugging Face Cloud | The **office building** the restaurant is in | Free cloud hosting that provides the computers |
| Hugging Face ZeroGPU | The **chef's power tool** | A GPU accelerator — we "hook it up" so Hugging Face lets our Space run |

**Your punchline:** *"Without the kitchen (Celery), a 2-minute analysis would freeze the entire website. The waiter can't stand in the kitchen for 2 minutes — he needs to hand the ticket to the kitchen and keep serving others."*

### Level 2 — The components (for moderately technical judges)

```
┌───────────────────────────────┐      ┌──────────────────────────────────┐
│  FRONTEND  (Vercel)           │      │  BACKEND  (Hugging Face Space)   │
│                               │      │                                  │
│  React 19 + Vite + Tailwind   │      │  Django 6 + DRF  (the API)       │
│  Plotly.js charts (5)         │      │    │                             │
│  WaveSurfer audio player      │      │    ├── Redis  (broker) ──┐       │
│  jsPDF report export          │      │    ▼                       ▼       │
│                               │      │  Celery Worker ──▶ ML Engine     │
│  ── /api/... ──────────────── │────▶ │    4-stage pipeline              │
│  ── /media/... ─────────────  │      │    (pYIN, PCP, KMeans, DTW)      │
└───────────────────────────────┘      │                                  │
                                       │  SQLite DB (0-setup file DB)     │
                                       │  Media + .npz matrices on disk   │
                                       │  Gradio wrapper (HF requirement)  │
                                       └──────────────────────────────────┘
```

### Level 3 — The deployment map (for "how is this deployed?" judges)

| Layer | Hosting | What lives there |
|---|---|---|
| **Frontend** | **Vercel** — a serverless static-site CDN | Built React bundle (HTML/CSS/JS). `vercel.json` rewrites `/api/*` & `/media/*` → the HF backend URL. |
| **Backend API** | **Hugging Face Space** (free tier) | Django + DRF app, all `/api/...` endpoints, SQLite DB, uploaded media files. |
| **ML Workers** | Same HF Space, background process | Celery workers + Redis running alongside Django inside the container. |
| **GPU** | HF ZeroGPU (attached "decoy") | Satisfies HF's requirement that Spaces declare a GPU function. |
| **Local demo** | Docker Compose (7 services) | Full stack on one machine: React, Django, Celery, Redis, Prometheus, Grafana, node-exporter. |

---

## 5. Live Demo Script

> *Practice this 5 times. Every click should be second nature. If the live site is down, use the printed screenshots + pre-saved result JSON (see checklist).*

### Where things are

| Thing | Location / URL |
|---|---|
| Live frontend (the site you SHOW) | Vercel URL (the `vercel.app` link) — project `frontend/` |
| Live backend API | `https://krish-shripat-vedic-backend.hf.space` (Hugging Face Space) |
| Backend source (HF) | `/home/Arc/hf-deploy` on your machine |
| Main project source | `/home/Arc/Vedic-Acoustica` |
| Test audio files | `test_audio/synthetic/` (breath_gap_scale.wav, dha1_pure_413hz.wav, gamaka_scale.wav, vibrato_scale.wav) |

> [!IMPORTANT]
> The frontend talks to the backend through a **rewrite**: when you load any Vercel URL ending in `/api/xxx`, Vercel transparently forwards it to the HF Space. That's why the site "just works" from anywhere. If you're offline, run the whole stack locally with Docker Compose.

### Script (aim for the frontend → backend connection to be visible)

1. **Open the live site.** Say: *"This is the public dashboard — the frontend on Vercel, talking to our backend ML engine that runs free on Hugging Face."*
2. **Log in or click "Continue as Guest".** Say: *"We added an authentication layer — real users can register/login; guests can demo without an account. It's token-based, like a key card."*
3. **Upload a file** (use `test_audio/synthetic/dha1_pure_413hz.wav` — it's a clean pure tone at 413 Hz, great for a fast demo). If `dha1_pure_413hz.wav` is too "easy" and judges want something musical, use `gamaka_scale.wav` or `vibrato_scale.wav`.
4. **Click Analyse.** Call out: *"Behind this button, Django hands the audio to a Celery worker via Redis. The progress bar polls the backend every second. This is why the page doesn't freeze."*
5. **While it analyses (30–120s), explain the 4 stages briefly** (from §7). This is your free teaching time.
6. **When done, walk the 5 charts** (§8) top to bottom, left to right. Click a Ghana Patha segment to **jump the audio player** to that part — that's an interactive wow-moment.
7. **Click "Download PDF Report".** Say: *"With one click, all 5 charts and a summary become a shareable scientific report — a teacher could print this for a classroom."*
8. **Done.** Say the closing line: *"That's every feature — objective, measurable, reproducible analysis of a 3,500-year-old oral tradition."*

### What the layout shows (memorise the dashboard order)

| Area | Component | What it proves |
|---|---|---|
| Auth screen (before login) | `AuthScreen.jsx` | Real auth, not a toy |
| Upload zone | `AudioUploader.jsx` | Drag-and-drop, 50 MB limit, wav/mp3/ogg/flac |
| Recording list | In `App.jsx` | History, re-analysis |
| Audio player | `AudioPlayer.jsx` (WaveSurfer) | Waveform, play/pause, clicking charts jumps audio |
| Chart 1 | `SpectrogramView.jsx` | Frequency energy over time — "the fingerprint" |
| Chart 2 | `ClusterPlot.jsx` | K-Means: frames per Shruti bucket |
| Chart 3 | `ShrutiMap.jsx` | 23-row heatmap of microtonal presence over time |
| Chart 4 | `GhanaPathaViz.jsx` | Expected vs detected recitation pattern + verdict |
| Chart 5 | `RagaViz.jsx` | Best raga match + confidence + scale display |
| Report bar | `exportReport.js` | One-click PDF export |

---

## 6. Tech Stack

> *This is the honest, current list. Verify versions before presenting by checking `package.json`, `requirements.txt`, and `docker-compose.yml`.*

### Frontend (Vercel)
| Tool | Version | Why |
|---|---|---|
| React | 19.2.7 | UI framework |
| Vite | 8.1.1 | Fast build tool (Rust-based Oxc compiler via @vitejs/plugin-react) |
| Tailwind CSS | 4.3.3 | Styling (used in auth screen etc.) |
| Plotly.js | 3.7.0 | Scientific interactive charts (raw lib for spectrogram) |
| react-plotly.js | 4.0.0 | React wrapper for the other 4 charts |
| WaveSurfer.js | 7.12.11 | Audio waveform player |
| jsPDF | 4.2.1 | PDF report generation |
| oxlint | 1.71.0 | Linting |

### Backend (Hugging Face)
| Tool | Version | Why |
|---|---|---|
| Python | 3.13 local / 3.12 on HF Space | language |
| Django | 6.0.7 | Web framework + ORM + admin |
| Django REST Framework | 3.17.1 | API endpoints + serializers + auth |
| Celery | 5.4.0 | Async task queue (the "kitchen") |
| Redis | 5.2.1 (client) | Message broker + result backend |
| Gunicorn | 23.0.0 | WSGI server (2 workers, 120s timeout) |
| django-cors-headers | 4.9.0 | Cross-origin API access |

### ML / Signal Processing
| Tool | Version | Used for |
|---|---|---|
| librosa | 0.11.0 | pYIN pitch tracking, STFT, MFCC, chroma |
| scikit-learn | 1.9.0 | K-Means clustering, cosine similarity |
| NumPy | 2.4.6 | All matrix math |
| SciPy | 1.18.0 | Signal processing support |

### Infrastructure
| Tool | Purpose |
|---|---|
| Docker Compose | Local full-stack dev (7 services) |
| Kubernetes (Minikube) | Production-style deployment demo (2 frontend + 1 backend + 2 celery + 1 redis) |
| GitHub Actions | 3-job CI (backend tests, frontend lint+build, Docker smoke) |
| Prometheus + Grafana | Live metrics & dashboards (monitoring stack) |
| Vercel + HF Space | Public hosting, zero cost |

---

## 7. The ML Pipeline

> *Use the "Four Inspectors" analogy. Each stage is a specialist who examines one aspect of the same building.*

**Opening line:** *"Think of the analysis like a building inspection. Four specialized inspectors examine the same building — each looks at a different thing."*

| Stage | Inspector | What it actually does | Progress bar % |
|---|---|---|---|
| 1. Feature Extraction | The **surveyor** who measures everything | Loads audio; extracts pitch curve (pYIN F0 @ 22,050 Hz), spectrum (STFT), 13 MFCCs, tempo, and a custom 22-bin Pitch Class Profile | 5→30 |
| 2. Shruti Clustering | The **materials inspector** who sorts bricks by type | K-Means (K=22) groups every audio frame into 22 buckets; each bucket is mapped to the nearest of the 23 Shrutis by log-frequency (cents) distance | 35→60 |
| 3. Ghana Patha Validation | The **structural engineer** who checks against the blueprint | Cuts the pitch map into segments and compares each to the correct Ghana Patha forward/reverse patterns using Dynamic Time Warping (DTW) | 65→80 |
| 4. Raga Detection | The **architect** who identifies the style | Splits detected notes into ascending/descending halves, scores against 44 ragas; if unsure, matches melodic phrases (Pakad) via DTW | 85→98 |

### One-sentence explanations of the scary words (use these!)

- **pYIN** = a proven algorithm (from librosa) that estimates the sung pitch per tiny time-window (every ~23 ms), and also says "this is silence / no pitch" when unsure. *(Pronounce it: "pie-in")*
- **F0** = fundamental frequency = the actual pitch of your voice in Hz.
- **STFT** = Short-Time Fourier Transform = "which frequencies are loud at each moment" — the spectrogram math.
- **MFCC** = a compact, standard 13-number summary of the *timbre* (voice quality) per frame.
- **Pitch Class Profile (PCP)** = how much energy falls near each of the 22 Shruti slots. Our core custom feature.
- **Cents** = a musical unit of pitch. 100 cents = 1 Western semitone. Our threshold is **±25 cents**.
- **K-Means** = an algorithm that finds 22 natural groups in the data (unsupervised clustering).
- **DTW** = Dynamic Time Warping = "match two patterns even if one is stretched in time" — like matching a song hummed fast vs slow. Perfect for chant validation.
- **Arohana/Avarohana** = the ascending / descending run of notes in a raga.
- **Vadi / Samvadi** = the dominant and second-dominant notes of a raga.
- **Pakad** = the signature melodic phrase that identifies a raga (like a musical fingerprint motif).

### Why the 22-Shruti system is special (the "aha" for judges)

> *"Ancient Indian music didn't use 12 evenly-spaced notes. It used 22 subtle pitch positions based on natural just-intonation ratios — like 256/243, a ratio barely wider than a quarter-tone. Two Shrutis can be only ~22 cents apart, while Western 12-tone music rarely goes below 100-cent steps. That's why even advanced Western music AI can't do this — the resolution is too coarse. Our 23-bin PCP was built specifically to resolve these micro-intervals. And we now include the octave Sa' as Shruti 23 so the full octave span is covered."*

---

## 8. The 5 Charts

> *Judges will stare at the screen during the demo. Teach these so you can narrate without looking.*

### 1. Spectrogram (`SpectrogramView.jsx`)
- **What it is:** a heatmap where X = time, Y = frequency, color = loudness. Dark = quiet, bright = loud.
- **The cursor trick:** as audio plays, a red glowing line moves across — synced to the player via `Plotly.relayout` at ~50ms (bypasses React for speed).
- **Say:** *"This is the raw acoustic fingerprint — every frequency band over time. Notice the voice energy concentrates in low harmonics."*

### 2. Cluster Plot (`ClusterPlot.jsx`)
- **What it is:** a bar chart of how many audio frames fell into each of the 22 K-Means clusters.
- **Say:** *"K-Means grouped every frame into 22 buckets by voice characteristics. Each bar is one Shruti bucket with a distinct color."*

### 3. Shruti Map (`ShrutiMap.jsx`)
- **What it is:** a 23-row heatmap (X = time, Y = the 23 Shrutis bottom-to-top), plus a bar/heatmap toggle.
- **The Sa/Pa dotted lines:** horizontal dotted guides at Sa and Pa — the two anchor notes.
- **Say:** *"This is the heart of the project. It shows exactly which of the 23 microtonal notes are active at every moment. A Western system would show 12 rows; we show 23."*

### 4. Ghana Patha Viz (`GhanaPathaViz.jsx`)
- **What it is:** expected pattern (green dashed) vs detected pattern (red solid) across the recitation segments, plus a ✅ Valid / ❌ Invalid verdict and a 0–1 confidence.
- **The interactive wow:** each segment is a button — click it and the audio **jumps to that segment** (calls `playerRef.seekTo()`).
- **Say:** *"Ghana Patha is the most complex oral preservation pattern in Vedic tradition: 1-2, 2-1, 1-2-3, 3-2-1, 1-2-3 — forward, reverse, forward, reverse, forward. DTW compares each segment to the correct template and we score the whole cycle."*

### 5. Raga Viz (`RagaViz.jsx`)
- **What it is:** the best raga match card (name, tradition, confidence %, time-of-day, mood, vadi/samvadi, arohana/avarohana), top-5 confidence bars with a 40% dashed threshold line, and an amber "Inconclusive" card when confidence is too low.
- **Say:** *"Directional scoring splits the melody into ascending and descending halves and matches each against the raga's scale; the confidence bars show honesty — if nothing passes 40%, we say 'Inconclusive' instead of guessing."*

---

## 9. Key Code

> *Judges love when you can OPEN a file and point. Pick 3–4 of these. For each: 30 seconds of "what it does" in simple words + point at the exact lines.*

### Pick #1 — The 22 Shruti ratios (`backend/ml_engine/shruti_mapping.py`)

**Where:** `SHRUTI_RATIOS` — 23 ratios from `1/1` (Sa) to `2/1` (octave Sa').
**Open the file, point at the ratio `256/243`:**
> *"These are the ancient just-intonation ratios — each Shruti is defined as a pure mathematical ratio of the base note. Shruti 2, Re1, is 256/243 — that's about a 90-cent interval, half a Western semitone. This table IS the ancient music theory, converted to numbers a computer can use."*

### Pick #2 — pYIN pitch extraction + unvoiced handling (`backend/ml_engine/audio_processing.py`)

**Where:** `extract_f0()` uses `librosa.pyin`; the F0 boost constant `_F0_BOOST = 8.0`.
**Point at `_F0_BOOST = 8.0`:**
> *"pYIN gives us a pitch value only when it's confident; silence/breaths come back as NaN. So for voiced moments we boost the matching Shruti bin by 8× to drown out harmonic ghost notes; for silence we fall back to the next-best signal rather than fabricate a note."*

### Pick #3 — K-Means clustering (`backend/ml_engine/ml_engine.py`)

**Where:** `KMeans(n_clusters=22, random_state=42, n_init=10)`.
> *"We throw every audio frame into K-Means with K=22 — one cluster per Shruti. `random_state=42` means the result is reproducible every time. Then each cluster gets assigned to a Shruti by nearest-frequency."*

### Pick #4 — DTW pattern matching (`backend/ml_engine/ghana_patha.py`)

**Where:** the `dtw_distance()` function + `GHANA_CYCLE = ['forward','reverse','forward','reverse','forward']`.
> *"DTW stretches one pattern in time to match another, then measures how far apart they are. Here we compare each chant segment to forward and reverse Ghana templates. The verdict formula is `is_valid = repetition > 0.35 AND ghana_confidence > 0.25` — both conditions must pass."*

### Pick #5 — Raga scoring (`backend/ml_engine/raga_mapping.py`)

**Where:** `_score_raga()` weights and `CONFIDENCE_THRESHOLD = 0.40`.
> *"Each raga scores on a weighted formula: 25% matching notes, 25% ascending-scale coverage, 25% descending-scale coverage, plus bonuses for the vadi/samvadi and penalties for stray notes. Below 40% we report 'Inconclusive' — we'd rather be honest than wrong."*

### Pick #6 — The async task queue (`backend/api/tasks.py`)

**Where:** `process_audio_task` + `_run_pipeline(pk)`.
> *"Clicking 'Analyse' doesn't run code right away — Django puts a message into Redis, and a Celery worker picks it up. That's why the site stays responsive during a 2-minute analysis. There's even a Redis lock making sure the same recording is never analysed twice at once."*

### Pick #7 — The single-flight lock (idempotency flex)

**Where:** `process_audio_task` uses Redis `SETNX` on key `vedic:analyze:lock:{pk}`.
> *"Two things could trigger the same analysis at once — a user double-click, or Celery redelivering a message after a crash. A Redis SETNX lock ensures exactly one analysis runs per recording. That's production-grade thinking, not a student hack."*

### Pick #8 — The progress polling (`backend/api/views.py`) + frontend poller (`AnalysisProgress.jsx`)

**Where:** `analysis_progress()` endpooint + JS `setInterval(…, 1000)`.
> *"Progress is a JSON endpoint polled once per second. We deliberately switched from Server-Sent Events to JSON polling because Vercel's proxy was buffering the SSE stream and freezing the progress bar. Choosing robust-over-cool is exactly what shipping software looks like."*

### Pick #9 — Matrix offload (DB performance flex)

**Where:** `_save_matrices` / `_npz_rel_path` + `offload_and_vacuum` management command.
> *"A raw spectrogram is megabytes of numbers. We didn't stuff those into SQLite — that made the DB balloon to 1.3 GB. We write heavy matrices to compressed `.npz` files on disk and keep only lightweight metadata in the database. DB writes dropped ~95%."*

### Pick #10 — The HF "trojan horse" (`/home/Arc/hf-deploy/app.py`)

**Where:** the Gradio `@spaces.GPU` decoy + Starlette `Mount`.
> *"Hugging Face requires a GPU-declaring app to run on ZeroGPU and a Gradio interface to serve the page. So `app.py` builds a dummy Gradio UI (that nobody uses), the decoy GPU function makes the platform happy, and then we mount the real Django app inside Gradio's server on the same port 7860. Zero GPU minutes consumed, full ML backend running free. This is real deployment engineering."* (Explain customimately in §10.)

### How to "show code" without rambling

1. Say what the file *is* in one plain sentence.
2. Point at one constant/function by name (read it aloud).
3. Give ONE thing it proves (reproducibility, robustness, honesty, performance).
4. Close the laptop. Judges want understanding, not a code read-out.

---

## 10. Hugging Face Deployment

> *This is unique — most student projects are not live on the cloud. Own it.*

### The setup, in simple words

1. **Hugging Face Spaces** is like a free mini-`server` for demos. Each Space runs one container. The free "ZeroGPU" tier gives you a GPU but with a strict rule: your app must declare a GPU function using the `@spaces.GPU` decorator, or the Space won't start.

2. **Our problem:** our ML is CPU-based (librosa + scikit-learn) — we don't need a GPU, but Hugging Face still demanded a GPU-declaring app to allow us on ZeroGPU.

3. **Our trick ("trojan horse"):** In `/home/Arc/hf-deploy/app.py`:
   - Start `redis-server` in the background.
   - Run Django migrations.
   - Start a Celery worker (`--concurrency=2`).
   - Build a throwaway **Gradio** UI containing a `@spaces.GPU` function that is *registered* (satisfies the scan) but **never called** → zero GPU minutes billed.
   - Mount the entire Django app (paths `/api`, `/admin`, `/media`, `/metrics`) INTO Gradio's underlying FastAPI server via Starlette `Mount`s, so Django answers on the same port 7860 that Hugging Face exposes.
   - `threading.Event().wait()` — keep the process alive forever.

4. **Why Gradio?** Because it's the interface HF ships by default and the ZeroGPU scanner walks Gradio handlers looking for `@spaces.GPU`.

### The fix that made it work (go-to engineering story)

> *"The first attempt worked for `/admin` but `/api` routes returned 404s. The reason was subtle: Gradio served Django under a path prefix and rewrote the request root, so Django saw `/analyze/5/` instead of `/api/analyze/5/`. We fixed it with a mount that **re-prepends the prefix and resets `root_path=""`**, so Django resolves the full `/api/...` as it expects. Then we instrumented the paths to verify every route. That's the difference between 'it runs on my laptop' and 'it runs in production'."*

### The URL chain (memorise it)

```
You open Vercel URL  →  browser sends GET /api/recordings/
        →  Vercel rewrite (vercel.json)        →  https://krish-shripat-vedic-backend.hf.space/api/recordings/
        →  HF Space container (port 7860)
        →  Gradio's FastAPI server mounts → Django → path_info "/api/recordings/"
        →  Django returns JSON → travels back the same chain → rendered by React
```

> Say it once like this: *"One URL for the user, but inside, Vercel is a courier that forwards every `/api` and `/media` request to our Hugging Face backend. The user never sees any of the plumbing."*

### Gotcha to be ready for

- The codebase (main repo) and the HF Space are **two separate folders** on disk: the main repo is the full project at `/home/Arc/Vedic-Acoustica`; the HF Space is a stripped-down, single-container version at `/home/Arc/hf-deploy`. Good to say: *"HF Spaces run one container, so the HF version is the backend consolidated into a single Docker service with the auth/metrics extras scoped appropriately. The full stack with Kubernetes lives in the main repo."*

---

## 11. Engineering Challenges

> *Use these only when judges are technical or visibly impressed. Say the hook-line, then the one-liner explanation.*

### 🔧 Flex #1: Concurrency blew up SQLite
**Problem:** 2 Gunicorn workers + 2 Celery workers all writing one SQLite DB → `database is locked` crashes.
**Fix:** 20-second write-lock timeout + offloading heavy matrices to `.npz` files → ~95% fewer DB writes.
**Line:** *"We turned a database crash into a graceful queue."*

### 🔧 Flex #2: Silence freaks out the pitch tracker
**Problem:** breaths/silence → pYIN returns NaN → garbage Shruti assignments.
**Fix:** dual-path: voiced frames use F0→nearest Shruti; unvoiced frames fall back to PCP energy; low-voicing analyses self-report low confidence.
**Line:** *"We don't guess when there's silence — we degrade gracefully to the next-best signal."*

### 🔧 Flex #3: Harmonic ghost notes
**Problem:** a pure Sa (261.6 Hz) also lights up Pa (392 Hz — its 3rd harmonic) → false notes.
**Fix:** fuse pYIN F0 into PCP, boosting the true Shruti bin by **8×** the average magnitude.
**Line:** *"Two independent pitch-estimation methods fused, killing the ghost notes."*

### 🔧 Flex #4: Docker layer caching in CI
**Problem:** every CI run rebuilt heavy image deps (libsndfile, librosa) from scratch → 3+ min.
**Fix:** Dockerfile copies `requirements.txt` first, installs deps, then copies source → layer cache skips deps → ~60% faster CI.
**Line:** *"We made our CI finish in minutes instead of waiting through every `pip install`."*

### 🔧 Flex #5: Cross-process progress tracking
**Problem:** Gunicorn's processes don't share memory — the SSE stream and the ML task couldn't see each other's progress.
**Fix:** file-based atomic progress store (`tempfile.mkstemp()` + `os.replace()`, POSIX-atomic rename). No extra infrastructure.
**Line:** *"We needed cross-process state and chose a zero-dependency, crash-safe file approach — no Redis pub/sub needed."*

### 🔧 Flex #6: Yaman raga disambiguation
**Problem:** ragas sharing the same note set (Yaman vs Bilawal) looked identical to a naive matcher.
**Fix:** directional (ascending/descending) scoring + vadi/samvadi bonus + a Pakad (signature phrase) DTW tiebreaker. Yaman's Ni-Re-Ga opening beats Bilawal's Sa-first approach.
**Line:** *"Data alone wasn't enough — we encoded years of musicology into the scoring rules."*

### 🔧 Flex #7: Vercel killed our real-time updates
**Problem:** SSE events froze behind Vercel's buffering proxy; progress bar stuck.
**Fix:** switched to JSON polling every 1 second.
**Line:** *"We chose the architecture that ships, not the one that's coolest in a tutorial."*

### 🔧 Flex #8: HF's ZeroGPU rules (see §10)
**Line:** *"We reverse-engineered a cloud platform's startup validation to run a CPU service for free — and documented the exact mount fix that made it work."*

---

## 12. Critical Numbers

> *These are verified against the current code. Citing exact numbers makes you sound authoritative — but only say the ones you can point to.*

| Metric | Value | Source file |
|---|---|---|
| Shruti resolution | **23 bins** (22 classical + octave Sa') | `shruti_mapping.py` `SHRUTI_RATIOS` |
| Reference pitch (Sa) | **261.626 Hz** (C4 / middle C) | `shruti_mapping.py` `REFERENCE_FREQ` |
| Pitch-matching tolerance | **±25 cents** | `audio_processing.py` `_THRESHOLD_CENTS = 25.0` |
| F0 boost factor | **8×** average magnitude | `audio_processing.py` `_F0_BOOST = 8.0` |
| PCP harmonics | **5** with 1/h decay | `audio_processing.py` `_N_HARMONICS = 5` |
| Sample rate | **22,050 Hz** | `audio_processing.py` `SR = 22050` |
| STFT size (PCP) | **n_fft = 4096**, hop 512 | `audio_processing.py` |
| MFCC coefficients | **13** | `audio_processing.py` `N_MFCC = 13` |
| Chroma / PCP bins | **22** | `audio_processing.py` `N_CHROMA = 22` |
| K-Means | **K = 22**, `random_state=42`, `n_init=10` | `ml_engine.py` `N_CLUSTERS = 22` |
| Raga database | **44 ragas** (Hindustani + Carnatic) | `raga_mapping.py` `RAGA_DATABASE` |
| Pakad phrase templates | **10** | `raga_mapping.py` `PAKAD_DATABASE` |
| Raga confidence threshold | **40%** (= 0.40) | `raga_mapping.py` `CONFIDENCE_THRESHOLD` |
| Swara presence threshold | **1.2%** of voiced frames | `raga_mapping.py` `SWARA_PRESENCE_THRESHOLD` |
| Near-silence gate (rms) | **rms < 0.01** → inconclusive | `raga_mapping.py` / `ghana_patha.py` |
| Ghana validity rule | repetition > 0.35 **AND** ghana confidence > 0.25 | `ghana_patha.py` |
| Ghana score blend | 45% repetition + 55% ghana | `ghana_patha.py` |
| Minimum analysis duration | **2.0 s**, ≥5 segments | `ghana_patha.py` |
| SQLite write timeout | **20 s** | `settings.py` `OPTIONS: {'timeout': 20}` |
| Upload limits | **50 MB**, `.wav/.mp3/.ogg/.flac` | `api/serializers.py` |
| Throttles | 60/min anon · 10/hr uploads · 10/hr analyses | `settings.py` `REST_FRAMEWORK` |
| Celery | **concurrency 2**, max-memory-per-child 1.5 GB, ACKS_LATE | `settings.py` + `docker-compose.yml` |
| Single-flight lock | Redis `SETNX vedic:analyze:lock:<pk>` (1 hr TTL) | `api/tasks.py` |
| Frontend components | **10** | `frontend/src/components/` |
| Frontend charts | **5** interactive Plotly charts | `frontend/src/components/` |
| CI/CD | **3 jobs**: backend tests · frontend lint+build · Docker smoke | `.github/workflows/` |
| Docker Compose | **7 services** | `docker-compose.yml` |
| K8s replicas | 2 frontend + 1 backend + 2 celery + 1 redis (backend stays single-writer for SQLite) | `k8s/` |

---

## 13. Q&A Defense

> *The highest-probability judge questions with model answers. Adapt, don't memorise word-for-word.*

### Q1: "Why didn't you use a ready-made library like Spotify's basic-pitch or music21?"
> "Those are built for **Western 12-tone equal temperament**. Vedic chanting uses a **microtonal system** where two notes can be just ~22 cents apart — below the resolution of any Western library. We had to build a custom **22-bin Pitch Class Profile** mapped to just-intonation ratios (256/243, 9/8, 16/15 …) and even an octave Sa' as the 23rd bin. No existing tool does this."

### Q2: "Isn't this just a pitch detector app?"
> "A pitch detector gives you one number: *'you're at 392 Hz'*. We give: ① which of 22–23 Shrutis that maps to, ② voiced/unvoiced classification per frame, ③ ascending/descending direction analysis, ④ **structural validation** of the recitation against Ghana Patha templates using DTW, ⑤ **raga identification** from 44 ragas with phrase-level disambiguation. It's the difference between a thermometer and a full diagnostic panel."

### Q3: "How accurate is it? Do you have ground truth?"
> "Honest answer: no public labelled dataset of Vedic chanting exists — we checked. So we validate three ways: ① a **synthetic test suite** with mathematically known pitches that our Shruti assignment must get right; ② a musicologically verified raga database (including the classic vadi/samvadi and pakad definitions); ③ a **confidence threshold** — below 40% we return 'Inconclusive' rather than guess. We prefer honest uncertainty over false precision."

### Q4: "How do you tell apart ragas that share notes?" (Yaman vs Bilawal)
> "Three techniques: ① **directional scoring** — we split notes into ascending (arohana) and descending (avarohana) runs and score each separately; ② **vadi/samvadi weighting** — the most important notes carry bonus weight; ③ a **Pakad tiebreaker** — when the top candidates are within 5%, we run DTW against hand-coded signature phrases. Yaman opens with Ni-Re-Ga; Bilawal doesn't. That's how the algorithm tells them apart."

### Q5: "DTW is O(n²). Real chants are minutes long — doesn't it explode?"
> "We segment the pitch map into ~1-second chunks first, so each DTW call is tiny. For the phrase tiebreaker we use a **strided sliding window** (half-template step) to cut the number of calls in half. A 2-minute chant validates in about 3 seconds."

### Q6: "Why SQLite, not PostgreSQL/MySQL?"
> "Design choice for zero-setup deployment. The whole DB is a file; no server to install on the HF Space. We hardened it: a **20-second write-lock timeout**, WAL-friendly usage, and — most importantly — we **offloaded megabytes of matrices to compressed `.npz` files on disk**, leaving SQLite with only small metadata. At our scale (2 web + 2 Celery workers) it's the right tool, and there's no deployment cost."

### Q7: "Is K8s overkill for a semester project?"
> "For a single laptop demo — yes, and we say so. But the design target is **institutions and gurukuls with many concurrent users**. K8s gives auto-healing (a worker that OOMs gets restarted), independent scaling of workers vs API, and shared persistent storage so any pod can serve files any other pod wrote. We actually debugged liveness probes, resource limits and volume mounts — it's running code, not just config files."

### Q8: "What about background noise in a field recording?"
> "pYIN outputs a confidence per frame. Low-confidence frames are treated as **unvoiced** and routed away from F0 → the PCP energy path; we also report a `voiced_ratio`, and if it drops below ~30% the analysis flags itself low-confidence. We don't hallucinate pitch over noise."

### Q9: "Why Celery? Why not threading or just doing it synchronously?"
> "The ML pipeline takes 30–120 seconds. If Django ran it inline, one upload would block **every other user's request** for 2 minutes. Celery + Redis lets Django say *'ticket in, analyse later'* and return instantly; the consumer keeps serving. Threading in-process wouldn't survive Gunicorn's multi-process model reliably, and we also wanted **retry + single-flight** semantics for free."

### Q10: "What's actually running on Hugging Face vs Vercel?"
> "Vercel hosts the static React build and **rewrites `/api` and `/media` requests** to our HF Space. The HF Space runs one container with: Django (the API), a Redis broker, and 2 Celery ML workers, all wrapped in a Gradio shell that complies with HF's ZeroGPU rules. So the heavy ML happens in the cloud, and the user just sees a fast website."

### Q11: "What did YOU actually build vs what's boilerplate?"
> "The 23-bin PCP and Shruti math (§9 Pick 1), the pYIN-F0 fusion and 8× boost (Pick 2), the K-Means assignment (Pick 3), the DTW Ghana validator (Pick 4), the directional raga scorer with Pakad tiebreak (Pick 5), the Redis single-flight lock (Pick 7), the matrix-offload storage design (Pick 9), and the HF deployment strategy (Pick 10). Frontend-wise: all 10 components from scratch — the synced spectrogram cursor, the clickable Ghana segments that seek the audio, the PDF exporter, and the polling progress system."

### Q12: "What's your next step / future work?"
> 1. **A labelled dataset** — record real chanters with ground truth to publish a benchmark.
> 2. **Real-time analysis** — streaming, not upload-then-wait.
> 3. **More ragas** (target: the principal 100) and more Shruti data for ornaments (gamaka/vibrato).
> 4. **A mobile app** — gurukuls are offline-friendly environments.
> 5. **Persistence on HF** — currently the Space's DB resets on redeploy; we'd wire persistent storage so user accounts survive.

### Q13: "Someone type 392 into a calculator and they get Pa. Why is that impressive?"
> "Because 392 Hz is only the *answer*; the hard part was: ① hearing the pitch correctly from a noisy, living recording (pYIN), ② resolving it against **22 microtonal slots**, not 12, ③ telling you *which* Pa (there are two Dha's, three Ni's, etc.), ④ verifying the *pattern* of notes matches ancient liturgy, and ⑤ identifying the raga those notes imply. One number is trivia; the whole pipeline is a research tool."

---

## 14. Counter-Question Playbook

> *When you don't know the answer. Three beats, that's all.*

**Beat 1 — Acknowledge (buys 2 seconds):** *"That's a fair point."* / *"Good question."*

**Beat 2 — Bridge to what you DO know:** *"We haven't tested that specific case yet — but here's what we can say from the architecture…"* (then explain an adjacent thing you're confident about, e.g., the confidence threshold, the .npz offload, the lock).

**Beat 3 — Redirect:** *"That's explicitly on our future-work list; we'd approach it by…"* — name a real approach so you sound like a builder, e.g.:
- "wavelet denoising / spectral gating" for noise
- "WebSockets" for real-time
- "PostgreSQL + connection pooling" if he pushes scale

**Never say:**
- ❌ *"I don't know."* (unmodified)
- ❌ *"We didn't think of that."*
- ❌ A wild guess.

---

## 15. Pull-Quote One-Liners

> *End any sentence with these when you need to sound experienced.*

- "We scoped that as future work — specifically we'd go with <approach>."
- "Our priority is honest uncertainty over false precision."
- "We chose the architecture that ships, not the one in the tutorial."
- "Every number we're showing is reproducible — `random_state=42`."
- "This is a preservation problem as much as a machine-learning problem."
- "It isn't a music app — it's a research instrument for an endangered oral tradition."

---

## 16. Run Plan

> *Assumes a 15-minute slot (10 min talk + 5 min demo/Q&A). If only 7 minutes, cut the ML deep-dive (§7 stages 3–4) and one flex.*

| Minute | What you do | Which guide section |
|---|---|---|
| 0:00–0:30 | Title slide + intro line | §2 |
| 0:30–1:30 | The problem (Act 1) + solution table | §3 |
| 1:30–3:00 | Architecture at 2 levels (restaurant + diagram) | §4 |
| 3:00–5:00 | The 4-stage ML pipeline | §7 |
| 5:00–7:00 | Key code picks (2–3 opens) | §9 |
| 7:00–9:30 | Live demo walkthrough | §5 + §8 |
| 9:30–10:30 | Hugging Face trick + Vercel chain | §10 |
| 10:30–11:00 | One flex (pick your best) + future work | §11, §13 Q12 |
| 11:00–11:30 | Closing line + open Q&A | §15 |
| 11:30–15:00 | Q&A | §13, §14 |

---

## 17. What NOT to Say

- ❌ "It's just a music app." → It's a research-grade acoustic instrument.
- ❌ "The ML is 100% accurate." → You don't have ground truth; say "validated on synthetic tests + confidence-thresholded".
- ❌ "It works on anything." → Constraints: clean-ish audio, 2s–few-minute files, 50 MB, 4 formats.
- ❌ "Google/ChatGPT told me…" → Say "we chose".
- ❌ "We never had bugs." → Bugs exist; Flex section is where you *admire* the good ones.
- ❌ Swearing, filler words, apologizing twice if the demo breaks.

---

## 18. Checklist

### 24 hours before
- [ ] Re-read this guide; drill §2, §7, §13.
- [ ] Test the live site once from college network.
- [ ] Save **2 screenshots** + **1 saved result JSON** as offline backup.
- [ ] Record a **1-minute screen capture** of an analysis run.
- [ ] Verify `test_audio/synthetic/` files exist & play.

### 30 minutes before
- [ ] Open the live site in a clean browser (no stored login).
- [ ] Log in / guest-mode ready.
- [ ] Keep `dha1_pure_413hz.wav` in an accessible folder.
- [ ] Laptop charged, adapter handy; phone hotspot as backup network.
- [ ] Close Slack/notifications.

### During the demo — if something breaks
- [ ] Don't apologise more than once.
- [ ] Say: *"While the server warms up, here's the identical result from our saved test suite…"* and move on.
- [ ] If it's just slow: *"That's the Celery worker running pYIN + DTW — let me show you what it's doing right now…"* and teach §7.

---

## 19. Splitting This Across 3 People

> *Three people, one coherent story. Each presenter owns ONE storyline so they can learn it deeply instead of memorising everything. Judges ask the whole team questions — so everyone memorises the 4 lines in §1 and the person who *owns* the topic answers the rest.*

### The three roles

| | **Presenter 1 — The Visionary**<br>(opens & closes) | **Presenter 2 — The Scientist**<br>(ML & accuracy) | **Presenter 3 — The Engineer**<br>(stack & deployment) |
|---|---|---|---|
| **Their story** | *Why this exists* | *How the science works* | *What it runs on* |
| **Sections they own** | §1–§3, §7 (why 22 Shrutis), §12 shruti numbers, §13 Q12 (future work) | §7 pipeline, §9 Picks #1–5, §12 ML numbers, charts 1–3, accuracy answers | §6, §4, §9 Picks #6–10, §10, §11 flexes, §12 infra numbers, charts 4–5 + PDF |
| **Slides they drive** | 1–3 (title, problem, solution) | 5–6 (ML pipeline diagrams) + the 3 audio charts | 4 (architecture), 7 (dev ops), demo tail |
| **Q&A they own** | culture, music theory, frequency *origin*, who uses it, future work | microtone frequency *accuracy*, pitch math, noise, raga disambiguation, DTW, "isn't this a pitch detector" | Celery/Redis, SQLite, K8s overkill, HF trick, Vercel chain, API/auth, "what really runs where" |
| **Demo duty** | clicks **Analyse**, reads the final verdict, PDF export | narrates the **progress stages** while waiting, walks charts 1–3 | walks charts 4–5, explains the architecture behind the wait |

> **Recommended assignment (none of them know the project):**
> - **You (who know the project) = Presenter 3 — The Engineer.** It needs the most improvisation (deployment gotchas + unexpected questions).
> - **Teammate A = Presenter 1 — The Visionary.** The most scripted role; easiest for a beginner to learn word-for-word.
> - **Teammate B = Presenter 2 — The Scientist.** Teach them via `PRESENTATION_README.md` (§"How the calc is done" + §"How do you know it's accurate").

### The 15-minute run order (with handover lines)

| Time | Presenter | What happens | Say (handover) |
|---|---|---|---|
| 0:00–1:30 | P1 | Elevator pitch (§2) + problem (§3 Act 1) | — opens |
| 1:30–2:30 | P1 | The 22-Shruti theory & where the frequencies come from | — |
| 2:30–3:00 | P1 | **Start demo**: login/guest → upload `dha1_pure_413hz.wav` → click Analyse | *"Let's run it on a known note and see what happens…"* |
| 3:00–5:00 | P2 | The 4-stage pipeline (narrates the moving progress bar) | P1→P2: *"And while it computes, the Scientist will walk you through exactly what's happening inside."* |
| 5:00–7:00 | P2 | Accuracy & validation (§13 Q3, synthetic tests, thresholds) | *"Now you know the maths. The question everyone asks is — how do we know it's right?"* |
| 7:00–8:30 | P3 | Architecture + tech stack (Restaurant analogy) | P2→P3: *"That's the science. Now the Engineer will show you the machine it runs on."* |
| 8:30–9:30 | P3 | Deployment: Vercel chain + HF trojan horse (§10) | *"The interesting part isn't the code — it's getting it live for free."* |
| 9:30–10:15 | P2 | Charts 1–3 (spectrogram, clusters, shruti map) — results are in | P3→P2: *"And here's what the pipeline just found — the Scientist reads the fingerprints."* |
| 10:15–10:45 | P3 | Charts 4–5 (Ghana verdict, raga card) + click a segment, export PDF | P2→P3: *"Now the pattern check and the raga verdict — and our one-click scientific report."* |
| 10:45–11:00 | P1 | Future work (§13 Q12) + closing line | P3→P1: *"So where does this go next? Back to the Visionary."* |
| 11:00–15:00 | All | Q&A — the owner of the topic answers; others add one line only | pre-agree: **slight nod = "I've got this one"** |

> [!TIP]
> The demo timing is elastic. If the analysis finishes early, P2 just starts charts early. If it's slow, P3 makes §8 extra juicy. Whoever is speaking when the progress hits 100% gets to say: *"…and the results are in."* Don't cram it into a fixed minute.

### Per-presenter mini-scripts (what each one must own)

**Presenter 1 (Visionary) — memorise these 3 paragraphs:**
> *"For 3,500 years, Vedic chanting survived only by ear. A guru passed the exact pitches to a student by singing them — subjective, and impossible to verify or scale. Western music uses 12 notes per octave; ancient Indian music recognised 22 finer positions called Shrutis. They come from pure string-division ratios — a string divided 2:1 gives the octave, 3:2 gives Pa, 4:3 gives Ma. We turned that ancient arithmetic into a numbering system a computer can verify."*
> *"So we built a tool that listens to a chant and answers three questions objectively: which microtones you're hitting, whether the recitation pattern is correct, and which raga the melody follows."*
> *"We validated it with mathematically exact test notes, and it's live on the internet today — free cloud hosting, full ML backend."*

**Presenter 2 (Scientist) — memorise the 4 inspectors + the accuracy story:**
> *"Four inspectors examine one building. Stage 1, the surveyor, measures everything — pitch per frame via the pYIN algorithm, spectrum, MFCC, tempo. Stage 2, the materials inspector, sorts every frame into 22 buckets with K-Means and maps each bucket to a Shruti. Stage 3, the structural engineer, checks the recitation pattern against the Ghana Patha template using DTW. Stage 4, the architect, identifies the raga by directional scoring against 44 ragas, with a phrase tiebreaker when unsure."*
> *"Accuracy? The Shruti ratios are exact fractions from music theory — 3/2 is 701.96 cents, period. Every number a judge sees is reproducible — we use a fixed random seed. When a test tone is a pure 413 Hz, the system must return Dha1. And when it can't be confident — below 40% — it says 'Inconclusive' instead of guessing. That honesty is our accuracy."*

**Presenter 3 (Engineer) — memorise the Restaurant + the HF trick:**
> *"The website is a restaurant. React is the dining room, Django is the maître d', and Celery + Redis are the kitchen — the waiter hands the ticket to the kitchen so it can keep serving other customers instead of blocking for 2 minutes. Without the kitchen, one analysis would freeze the whole site."*
> *"The frontend lives on Vercel and forwards every /api request to our backend deployed free on Hugging Face. HF requires a GPU-declaring app, so the app declares a dummy GPU function that's never called, then mounts the real Django server inside the wrapper — zero GPU minutes used, full ML backend running free. Vercel is the courier; Hugging Face is the warehouse; the user never notices either."*

### What each presenter should NOT answer (pass it)

- P1 doesn't answer pipeline math — pass to P2: *"The Scientist can show you the exact formula there."*
- P2 doesn't answer deployment — pass to P3: *"The Engineer got that working — over to you."*
- P3 doesn't answer music theory origin — pass to P1: *"The Visionary can walk you through the history of those ratios."*
- Passing is NOT weakness — it looks like a well-drilled team.

### Q&A passing signal (agree on this)

- Owner of the topic **nods slightly** → only they speak.
- If two of you start at once, the more junior teaches the other to yield: *the one who ISN'T the topic owner says "nice point — [Owner] can go deeper", and stops.*

---

## 20. Coach's Kit

*This is how the person who knows the project (Presenter 3) trains the other two in <4 hours of work spread over 3 days.*

### The 3-day plan

| Day | What you do together | Output |
|---|---|---|
| **Day 1 (60–90 min)** | ① Give them `PRESENTATION_README.md` — they read it fully. ② You demo the live site once, talking as you click (§5). ③ They each read **only** their own sections of this guide (§19 table). | They can *explain* the project to you, not just read it. |
| **Day 2 (60–90 min)** | ① You ask them the 10 self-test questions in `PRESENTATION_README.md` §9. ② They run the live demo themselves, using the §19 scripts. ③ One dry-run of the full 15-minute order with you as "judge". | They can *run* the demo and answer their topic's questions. |
| **Day 3 (60 min)** | Full rehearsal with a stopwatch + mock Q&A. You fire the §13 questions at whoever owns them. Switch presenters at the handover lines exactly. | The timed run feels boring-easy. |

### The 8-line starter lecture (give teammates this first)

1. The project analyses Vedic chanting audio and tells you three things: the microtone (Shruti), whether the recitation pattern is correct (Ghana Patha), and the raga.
2. Indian music uses 22 Shruti microtones; Western music uses 12 — that's why we built custom math.
3. The 22 frequencies are exact mathematical ratios (e.g., Pa = 3/2 × the base note) — not guesses.
4. The ML pipeline has 4 stages: feature extraction → clustering → pattern validation → raga detection.
5. Accuracy = exact ratios + fixed random seed + synthetic test tones + "Inconclusive below 40%".
6. The site = React frontend (Vercel) + Django/ML backend (Hugging Face), connected by one URL.
7. Behind the scenes, Celery + Redis run the 30–120s analysis in the background so the site never freezes.
8. If they ask you something you don't know: acknowledge it, bridge to what you DO know, say it's on the roadmap.

### Self-test for Presenter 1 (Visionary)

1. Why is the 22-Shruti system harder than Western 12-tone?
2. Where do the frequency ratios come from (history)?
3. What does 3/2 mean and which note is it?
4. Who is this project for? What problem does it remove?
5. What three "verdicts" does the analysis give a user?
6. Why use "objective, reproducible" and not "accurate"?
7. What is Ghana Patha in 2 sentences?
8. What's the future work list (name 3)?
9. What does the site show on screen (name the 5 charts vaguely)?
10. Deliver the 30-second pitch from memory.

### Self-test for Presenter 2 (Scientist)

1. What does pYIN do, and how does it handle silence?
2. What is the cents formula and the ±25 cent threshold for?
3. Why is the gap between Re1 and Re2 ~21.5 cents a design constraint?
4. What is the F0 boost (8×) solving?
5. What does K=22 in K-Means mean and why is the seed fixed?
6. What is DTW and why is it right for chant validation?
7. What is the Ghana Patha validity rule (both conditions)?
8. What are directional swaras, vadi/samvadi, and the Pakad tiebreak?
9. Which test files prove accuracy (name 3) and what do they prove?
10. What makes the system honest when it's unsure?

### Self-test for Presenter 3 (Engineer)

1. Name the 7 components in the Restaurant analogy.
2. What happens when you click Analyse (the full Redis/Celery trip)?
3. Why SQLite with a 20s timeout and .npz offload for big matrices?
4. What is the single-flight Redis lock protecting against?
5. How does the Vercel→HF URL chain work?
6. What is the HF ZeroGPU "trojan horse" and why is it needed?
7. Name the 10 frontend components and the 5 charts.
8. Why JSON polling instead of SSE across Vercel?
9. Name the 7 Docker Compose services.
10. Give one flex story (§11) from memory.

### Mock-Q&A drill (10 minutes)

- The coach (you) plays judge and fires §13 questions **out of order**.
- Whoever owns the topic answers in ≤45 seconds. Others say nothing unless passed to.
- 3 rounds. Round 3 = surprise questions (use §14 four times).

### Cheat cards to print (one per presenter, A6)

**P1:** pitch + 3 verdicts + 3/2=Pa + who it's for + future work → `PRESENTATION_README.md` §"Where the frequencies come from"
**P2:** 4 inspectors + cents formula + 25¢ threshold + 40% inconclusive + dha1_pure_413hz.wav → §7 + §13 Q3/Q4/Q7
**P3:** restaurant + Vercel→HF chain + Single-flight lock + .npz offload + trojan horse → §4 + §10 + §11

> [!IMPORTANT]
> **On the day, the Visionary speaks first and last, the Scientist owns every "how/accuracy" question, the Engineer owns every "how does it run" question. Everyone says "we", never "I". Three one-wall stories always beat three people who each tried to learn everything.**

---

> [!TIP]
> **Final advice:** The judges aren't grading your code — they're grading your **understanding** of your code. If you can say *why* 23 bins and not 12, *why* Celery and not threads, *why* "Inconclusive" is a feature, and *where in the cloud each piece runs — you've already won.

**Go crush it. 🚀**
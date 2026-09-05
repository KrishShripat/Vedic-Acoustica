# Vedic Acoustica

**Microtonal Voice Analysis, Ghana Patha Validation & Raga Detection using Machine Learning**

![Python](https://img.shields.io/badge/Python-3.13-3776AB) ![Django](https://img.shields.io/badge/Django-6-blue) ![React](https://img.shields.io/badge/React-19-61DAFB)

Vedic Acoustica is a full-stack web application that analyzes audio recordings of Vedic chants, Indian classical singing, and traditional folk music. Unlike standard speech-to-text systems, it does not recognize *what* is being spoken. Instead, it analyzes the **mathematical structure, precise frequencies, and temporal patterns** of the audio using AI/ML.

## Live Demo

| Layer | Where it runs |
|-------|---------------|
| Frontend (React UI) | [Vercel](https://vercel.com) |
| Backend API (Django + ML) | [Hugging Face Space](https://huggingface.co) — `krish-shripat-vedic-backend.hf.space` |
| Kubernetes | Local Minikube (demo) |

> The monitoring stack (see [Monitoring](#monitoring)) pulls live metrics from both the
> local Compose stack and the hosted HF backend side by side.

---

The system combines modern machine learning with Indian Knowledge Systems (IKS) to automate three core tasks:

1. **22 Shruti Detection** — Maps audio frequencies onto the 22 ancient Indian microtonal scale (Shrutis) rather than the standard Western 12-semitone scale, using pYIN F0 tracking + PCP analysis + K-Means clustering.
2. **Ghana Patha Validation** — Detects whether a chant follows the rigid recursive recitation pattern (1-2, 2-1, 1-2-3, 3-2-1, 1-2-3) used by ancient Vedic scholars as an oral error-correction mechanism, using Dynamic Time Warping (DTW).
3. **Raga Detection** — Identifies the raga of a musical performance by analyzing swara sets, Arohana (ascending) and Avarohana (descending) directional patterns, and Vadi/Samvadi weighting across a database of 33 ragas (20 Hindustani + 13 Carnatic).

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Indian Knowledge Systems Integration](#indian-knowledge-systems-integration)
- [Machine Learning Pipeline](#machine-learning-pipeline)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Dashboard Output Guide](#dashboard-output-guide)
- [Test Results](#test-results)
- [Docker & DevOps](#docker--devops)
- [Kubernetes Deployment](#kubernetes-deployment)
- [CI/CD](#cicd)
- [Monitoring](#monitoring)
- [Development](#development)

---

## Problem Statement

Western music divides an octave into 12 distinct semitones. However, traditional Indian classical music and Vedic acoustics recognize **22 Shrutis** — hyper-specific, subtle variations in pitch that cannot be detected by standard Western-tuned systems.

Before written texts existed, ancient scholars preserved massive volumes of Vedic literature using oral repetition sequences called **Vikriti Pathas**. The most complex is **Ghana Patha**, where words are mathematically woven back and forth:

```
1-2, 2-1, 1-2-3, 3-2-1, 1-2-3
```

This acts as a built-in data redundancy and error-correction mechanism — similar to a modern checksum or hash. If a single syllable is missed or distorted, the mathematical rhythm collapses.

In Indian classical music, **Raga identification** goes beyond just the notes used — it considers the ascending (Arohana) and descending (Avarohana) scale patterns, which can be asymmetric. A raga like Bhairav uses different swaras going up versus going down.

**Vedic Acoustica automates the detection of all three of these acoustic properties** using machine learning, eliminating the need for human experts to manually verify each recording.

---

## Indian Knowledge Systems Integration

### 22 Shrutis (Microtonal Mapping)

The system encodes the 22 Shruti frequency ratios based on classical Indian music theory:

| Shruti | Name | Ratio | Frequency (Hz) |
|--------|------|-------|----------------|
| 1 | Sa | 1.000 | 261.63 |
| 2 | Re1 | 1.053 | 275.65 |
| 3 | Re2 | 1.111 | 290.69 |
| 4 | Ga1 | 1.125 | 294.33 |
| 5 | Ga2 | 1.200 | 313.95 |
| 6 | Ga3 | 1.266 | 331.13 |
| 7 | Ma1 | 1.250 | 327.03 |
| 8 | Ma2 | 1.406 | 367.86 |
| 9 | Ma3 | 1.333 | 348.83 |
| 10 | Pa | 1.424 | 372.42 |
| 11 | Dha1 | 1.500 | 392.44 |
| 12 | Dha2 | 1.580 | 413.39 |
| 13 | Ni1 | 1.600 | 418.60 |
| 14 | Ni2 | 1.667 | 436.04 |
| 15 | Ni3 | 1.688 | 441.47 |
| 16 | Sa' | 2.000 | 523.25 |
| 17 | Re' | 2.106 | 551.31 |
| 18 | Ga' | 2.222 | 581.39 |
| 19 | Ma' | 2.250 | 588.66 |
| 20 | Pa' | 2.400 | 627.91 |
| 21 | Dha' | 2.667 | 697.66 |
| 22 | Ni' | 3.000 | 784.88 |

### Ghana Patha (Pattern Validation)

Ghana Patha is the most complex of the Vikriti Pathas (modified recitation styles). It treats oral chanting like a **human hash function**:

```
Given words: A, B, C

Ghana Patha sequence: A-B, B-A, A-B-C, C-B-A, A-B-C
                      ↑     ↑     ↑       ↑       ↑
                   1-2   2-1  1-2-3    3-2-1    1-2-3
```

The algorithm validates this using Dynamic Time Warping (DTW):
1. Dividing audio into 1-second segments
2. Computing PCP (Pitch-Class Profile) features for each segment
3. Matching segments against forward/reverse phrase templates via DTW
4. Scoring the expected [fwd, rev, fwd, rev, fwd] Ghana cycle
5. Measuring repetition score via pairwise DTW similarity between non-adjacent segments

### Raga Detection (Directional Scoring)

The system contains a database of **33 ragas**:

**Hindustani (20):** Yaman, Bilawal, Bhupali, Bhairav, Malkauns, Darbari Kanada, Khamaj, Kafi, Asavari, Poorvi, Todi, Puriya, Marwa, Bhairavi, Kedar, Megh, Jhinjhoti, Rageshree, Bihag, Sindhi Bhairavi

**Carnatic (13):** Shankarabharanam, Kharaharapriya, Mayamalavagowla, Sri Raga, Kalyani, Todi, Bhairavi, Kambhoji, Abhogi, Hamsadhwani, Chakravakam, Kapi, Latangi, Mechakalyani

Each raga is defined by:
- **Swaras** — The set of notes (Sa, Re, Ga, Ma, Pa, Dha, Ni) with specific variants
- **Arohana** — The ascending scale pattern
- **Avarohana** — The descending scale pattern
- **Vadi** — The most prominent note (king note)
- **Samvadi** — The second most prominent note (minister note)

The detection uses **5-component scoring**:
| Component | Weight | Description |
|-----------|--------|-------------|
| Total swara overlap (Jaccard) | 0.25 | How many of the detected swaras match this raga's set |
| Arohana coverage | 0.25 | How many ascending-direction swaras match this raga's ascending scale |
| Avarohana coverage | 0.25 | How many descending-direction swaras match this raga's descending scale |
| Direction penalty | 0.10 | Penalty for swaras appearing in wrong direction |
| Vadi/Samvadi bonus | 0.15 | Bonus if the most prominent notes match |

---

## Machine Learning Pipeline

The ML pipeline flows through five stages:

```
Audio Input
    │
    ▼
┌─────────────────────────────────┐
│  Stage 1: Feature Extraction     │
│  (audio_processing.py)           │
│                                  │
│  • pYIN F0 tracking              │──→ F0 pitch contour + voiced/unvoiced
│  • PCP computation               │──→ 22-bin Pitch-Class Profile
│  • MFCC extraction               │──→ Timbre features
│  • Spectral centroid             │──→ Spectral shape
│  • STFT spectrogram             │──→ Time-frequency matrix
└──────────────┬──────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Stage 2│ │ Stage 3│ │ Stage 4│
│ Shruti │ │ Ghana  │ │ Raga   │
│ Assign │ │ Patha  │ │ Detect │
│        │ │ (DTW)  │ │ (Dir.) │
└───┬────┘ └───┬────┘ └───┬────┘
    │          │          │
    └──────────┼──────────┘
               │
               ▼
    ┌─────────────────┐
    │   API Response   │
    │  (JSON export)   │
    └─────────────────┘
```

### Stage 1: Audio Feature Extraction (`ml_engine/audio_processing.py`)

Raw audio is loaded via **librosa** and processed through multiple feature extractors:

| Feature | Function | Purpose |
|---------|----------|---------|
| **F0 Pitch Contour** | `extract_f0()` — `librosa.pyin()` | Monophonic pitch tracking with voiced/unvoiced decision per frame. Uses `librosa.pyin()` with fmin=65Hz, fmax=2093Hz for 22 Shruti range |
| **PCP (Pitch-Class Profile)** | `compute_pcp()` | 22-bin energy profile computed from STFT with harmonic accumulation. pYIN F0 is fused into PCP for voiced frames (F0 bin gets direct energy), providing accurate microtonal pitch information |
| **MFCCs** | `librosa.feature.mfcc()` | 13 Mel-Frequency Cepstral Coefficients capturing timbre, vocal tract shape, and resonance |
| **Chroma (22-bin)** | `librosa.feature.chroma_stft(n_chroma=22)` | Projects audio energy onto 22 pitch classes for clustering input |
| **Spectral Centroid** | `librosa.feature.spectral_centroid()` | Measures the "center of mass" of the sound spectrum |

Additional outputs:
- **STFT Spectrogram** — Time-frequency matrix for visualization
- **Tempo** — Beat detection via `librosa.beat.beat_track()`

**F0 + PCP Fusion Logic:**
```
For each frame:
  if frame is voiced (from pYIN):
      PCP[F0_bin] += F0_confidence    # Direct pitch energy injection
  else:
      PCP from STFT harmonics only     # Fallback for unvoiced/silent frames
```

This hybrid approach ensures accurate pitch detection for voiced speech while maintaining graceful degradation for unvoiced frames.

### Stage 2: Shruti Clustering & Assignment (`ml_engine/ml_engine.py`)

**K-Means Clustering:**

The combined MFCC + Chroma feature vectors are passed to **scikit-learn's KMeans** with `n_clusters=22`:

```python
KMeans(n_clusters=22, random_state=42, n_init=10)
```

**Per-Frame Shruti Assignment:**

For each audio frame, the system assigns a Shruti using a priority-based approach:
1. **Voiced frames (F0 available):** Map F0 frequency to the nearest Shruti bin
2. **Unvoiced/silent frames (no F0):** Use PCP argmax (highest energy bin) as fallback

Output:
- Cluster labels for every audio frame
- Cluster centroids (the "average" frequency profile of each Shruti)
- Per-frame Shruti assignments
- Mean PCP vector (22-element energy profile)

### Stage 3: Ghana Patha Validation (`ml_engine/ghana_patha.py`)

Uses **Dynamic Time Warping (DTW)** for tempo-invariant pattern matching:

1. **PCP Segmentation** — Audio is divided into 1-second segments, each with a 22-element PCP vector
2. **Phrase Templates** — Idealized PCP unit vectors represent forward (ascending) and reverse (descending) Ghana phrases
3. **DTW Matching** — Each segment is compared against forward/reverse templates using normalized DTW with cosine similarity cost
4. **Cycle Scoring** — The expected Ghana cycle `[fwd, rev, fwd, rev, fwd]` is slid over detected segment labels
5. **Repetition Score** — Pairwise DTW similarity between non-adjacent segments measures repetition strength

**Combined Confidence** = 0.45 * Repetition Score + 0.55 * Pattern Match Score

**Key advantage over cosine similarity:** DTW handles tempo variations, so a Ghana Patha chant that is faster or slower than the template will still match correctly.

### Stage 4: Raga Detection (`ml_engine/raga_mapping.py`)

**Directional Swara Extraction:**

1. Compute F0 gradient (pitch slope) from pYIN F0 track
2. Split audio frames into ascending (F0 rising) and descending (F0 falling) segments
3. Extract swara energy maps separately for ascending and descending directions

**5-Component Raga Scoring:**

| Component | Weight | How it works |
|-----------|--------|--------------|
| Total swara overlap | 0.25 | Jaccard similarity between detected swara set and raga's swara set |
| Arohana coverage | 0.25 | Fraction of raga's ascending scale present in ascending frames |
| Avarohana coverage | 0.25 | Fraction of raga's descending scale present in descending frames |
| Direction penalty | 0.10 | Penalizes swaras that appear in the wrong direction |
| Vadi/Samvadi bonus | 0.15 | Bonus when the most prominent detected notes match the raga's key notes |

Returns **top 5 raga matches** with confidence scores, along with arohana/avarohana scale strips showing which swaras were detected.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     USER BROWSER                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │        React Frontend (Port 80 via Nginx)         │  │
│  │                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │ Audio    │ │ Spectro- │ │ Cluster  │          │  │
│  │  │ Uploader │ │ gram     │ │ Plot     │          │  │
│  │  └──────────┘ └──────────┘ └──────────┘          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │ Shruti   │ │ Ghana    │ │ Raga     │          │  │
│  │  │ Map      │ │ Patha    │ │ Detection│          │  │
│  │  └──────────┘ └──────────┘ └──────────┘          │  │
│  │                                                   │  │
│  │  ┌──────────┐ ┌──────────────────────┐            │  │
│  │  │ Audio    │ │ PDF Export           │            │  │
│  │  │ Player   │ │                      │            │  │
│  │  └──────────┘ └──────────────────────┘            │  │
│  └──────────────────────┬────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────┘
                          │ /api/ requests
                          ▼
┌─────────────────────────────────────────────────────────┐
│           Nginx Reverse Proxy (Port 80)                 │
│         Proxies /api/ → Backend Container               │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│     Django Backend (Port 8000, Gunicorn + 2 workers)    │
│  ┌─────────────┐  ┌──────────────────────────────────┐ │
│  │ DRF API     │  │         ML Engine                  │ │
│  │ /api/upload │  │  ┌──────────────┐                 │ │
│  │ /api/list   │→│  │ Feature Ext. │ pYIN + PCP      │ │
│  │ /api/analyze│  │  └──────┬───────┘                 │ │
│  │             │  │         ▼                          │ │
│  │ SQLite DB   │  │  ┌──────────────┐                 │ │
│  │             │  │  │ K-Means      │ K=22 Clusters   │ │
│  │             │  │  └──────┬───────┘                 │ │
│  │             │  │         ▼                          │ │
│  │             │  │  ┌──────────────┐                 │ │
│  │             │  │  │ Ghana Patha  │ DTW Matching    │ │
│  │             │  │  └──────┬───────┘                 │ │
│  │             │  │         ▼                          │ │
│  │             │  │  ┌──────────────┐                 │ │
│  │             │  │  │ Raga Detect  │ Directional     │ │
│  │             │  │  └──────────────┘                 │ │
│  └─────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend UI** | React 19 + Vite 8 | User interface, drag-drop upload, interactive charts |
| **Charts** | Plotly.js (react-plotly.js) | Spectrogram heatmap, cluster bar chart, PCP energy map, raga confidence bars |
| **Audio Player** | WaveSurfer.js 7 | Waveform visualization with play/pause controls |
| **PDF Export** | jsPDF | Landscape A4 reports with embedded chart screenshots |
| **HTTP Client** | Axios / Fetch | API communication between React and Django |
| **Reverse Proxy** | Nginx | Serves React build, proxies /api/ and /media/ to backend |
| **Backend API** | Django 6 + Django REST Framework 3.17 | REST endpoints for upload, list, analyze |
| **ML Engine** | librosa 0.11, scikit-learn 1.9 | Audio feature extraction, pYIN F0, PCP, K-Means clustering, DTW |
| **Scientific Computing** | numpy 2.4, scipy 1.18 | Numerical operations, STFT computation, DTW cost matrices |
| **Database** | SQLite (development) | Stores recordings and analysis results |
| **Linting** | Oxlint | Frontend linting with React rules |
| **Containerization** | Docker + Docker Compose | Isolated environments for all services |
| **Orchestration** | Kubernetes (Minikube) | Container orchestration with monitoring |
| **CI/CD** | GitHub Actions | Automated build, test, and Docker image push |
| **Monitoring** | Prometheus + Grafana | Server metrics, CPU usage, request latency, API rate |

---

## Project Structure

```
Vedic-Acoustica/
├── backend/                            # Django + ML Engine
│   ├── vedic_acoustica/                # Django project settings
│   │   ├── settings.py                 # Configuration (apps, DB, CORS, media)
│   │   ├── urls.py                     # Root URL routing
│   │   ├── wsgi.py                     # WSGI entry point
│   │   └── asgi.py                     # ASGI entry point
│   ├── api/                            # Django app — REST API
│   │   ├── models.py                   # AudioRecording model
│   │   ├── serializers.py              # DRF serializers
│   │   ├── views.py                    # Upload, list, analyze endpoints
│   │   ├── urls.py                     # API URL routes
│   │   ├── tests.py                    # API tests (3 tests)
│   │   └── metrics.py                  # Prometheus metrics middleware
│   ├── ml_engine/                      # Django app — ML Pipeline
│   │   ├── audio_processing.py         # pYIN F0 + PCP + MFCC extraction
│   │   ├── ml_engine.py                # K-Means clustering + Shruti assignment
│   │   ├── shruti_mapping.py           # 22 Shruti frequency table
│   │   ├── ghana_patha.py              # DTW-based Ghana Patha validation
│   │   └── raga_mapping.py             # Directional Raga detection (33 ragas)
│   ├── datasets/                       # Processed audio samples
│   ├── requirements.txt                # Python dependencies
│   ├── Dockerfile                      # Backend container (python:3.13-slim)
│   └── .dockerignore
│
├── frontend/                           # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioUploader.jsx       # Drag-drop file upload (50MB max)
│   │   │   ├── AudioPlayer.jsx         # WaveSurfer.js waveform player
│   │   │   ├── SpectrogramView.jsx     # Plotly time-frequency heatmap
│   │   │   ├── ClusterPlot.jsx         # K-Means cluster bar chart
│   │   │   ├── ShrutiMap.jsx           # 22 Shruti PCP energy bars
│   │   │   ├── GhanaPathaViz.jsx       # Ghana Patha validation + DTW scores
│   │   │   └── RagaViz.jsx             # Raga detection + scale strips
│   │   ├── utils/
│   │   │   └── exportReport.js         # PDF report generator (jsPDF)
│   │   ├── App.jsx                     # Main app — state management, API calls
│   │   ├── App.css                     # Component styles
│   │   ├── index.css                   # Global dark theme
│   │   └── main.jsx                    # React entry point
│   ├── index.html                      # HTML template
│   ├── vite.config.js                  # Vite config with API proxy
│   ├── package.json                    # Node.js dependencies
│   ├── nginx.conf                      # Nginx config for production
│   ├── Dockerfile                      # Multi-stage: node build + nginx serve
│   └── .dockerignore
│
├── k8s/                                # Kubernetes manifests (kustomize)
│   ├── kustomization.yaml              # `kubectl apply -k k8s/` deploys all
│   ├── secret.yaml                     # Secret (django-secret-key, metrics-token)
│   ├── ingress.yaml                    # Ingress (path-based routing)
│   ├── storage.yaml                    # PVCs (RWX shared data + redis)
│   ├── backend/
│   │   ├── deployment.yaml             # Backend Deployment + initContainer
│   │   └── service.yaml                # ClusterIP Service
│   ├── frontend/
│   │   ├── deployment.yaml             # Frontend Deployment
│   │   └── service.yaml                # ClusterIP Service
│   ├── celery/
│   │   └── deployment.yaml             # Celery worker Deployment
│   ├── redis/
│   │   ├── deployment.yaml             # Redis broker Deployment
│   │   └── service.yaml                # ClusterIP Service
│   └── monitoring/
│       ├── kustomization.yaml
│       ├── node-exporter.yaml          # DaemonSet + Service
│       ├── prometheus.yaml             # ConfigMap + Deployment + Service
│       ├── grafana.yaml                # Deployment + Service + ConfigMaps
│       └── grafana-dashboard.yaml      # Dashboard JSON as ConfigMap
│
├── monitoring/                         # Docker Compose monitoring configs
│   ├── prometheus.yml                  # Scrape config (local + prod HF Space)
│   ├── grafana-datasource.yml          # Prometheus datasource
│   ├── grafana-provisioning.yml        # Dashboard provider
│   └── grafana-dashboard.json          # Grafana dashboard (10 panels)
│
├── test_audio/                         # Sample recordings
│   ├── isavasya_ghanam_60s.wav         # Ghana Patha recording (60s)
│   ├── isavasya_ghanam.ogg             # Same chant, OGG format
│   ├── rudram_60s.wav                  # Samhita Patha recording (60s)
│   ├── rudram.mp3                      # Same chant, MP3 format
│   └── test_10s.wav                    # Quick test clip (10s)
│
├── docker-compose.yml                  # Full stack orchestration (5 services)
├── .github/workflows/
│   ├── ci.yml                          # CI: backend test + frontend lint/build
│   └── cd.yml                          # CD: Docker build + push to GHCR
└── README.md                           # This file
```

---

## Installation

### Option 1: Docker (Recommended)

**Install Docker:**

Ubuntu:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker
```

Windows/Mac: Download [Docker Desktop](https://www.docker.com/products/docker-desktop)

**Run:**
```bash
git clone <repo-url>
cd Vedic-Acoustica
docker compose up -d backend frontend
```

Open **http://localhost** in your browser.

**Stop:**
```bash
docker compose down
```

### Option 2: Development Mode

**Prerequisites:** Python 3.11+, Node.js 18+

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
API runs at http://localhost:8000

**Frontend (new terminal):**
```bash
cd frontend
npm install
npm run dev
```
Dashboard runs at http://localhost:5173

---

## Usage

1. Open the dashboard in your browser
2. **Upload** — Drag-drop an audio file or click the upload zone
3. **Select** — Click on the recording in the list
4. **Analyze** — Click the "Run Analysis" button
5. **View Results** — Six interactive visualizations appear:
   - Spectrogram (time-frequency heatmap)
   - Shruti Clusters (K=22 bar chart)
   - 22 Shruti PCP Energy Map
   - Ghana Patha Validation (DTW-based)
   - Raga Detection (directional scoring)
   - Audio Player with waveform
6. **Export** — Generate a PDF report with all chart screenshots

### Supported Audio Formats

WAV, MP3, FLAC, OGG (anything librosa can load)

### Recommended File Size

- **Quick test:** Under 1 MB (`test_10s.wav`)
- **Demo:** Under 10 MB (60-second clips)
- **Full analysis:** Up to 50 MB (may take 30-60 seconds)

---

## API Reference

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/api/upload/` | `audio_file` (file), `title` (string) | Recording object with ID |
| `GET` | `/api/recordings/` | — | Array of all recordings |
| `GET` | `/api/recordings/<id>/` | — | Single recording with analysis |
| `POST` | `/api/analyze/<id>/` | — | Full ML analysis JSON |
| `GET` | `/metrics` | — | Prometheus metrics (text format) |

**Example: Upload**
```bash
curl -X POST http://localhost:8000/api/upload/ \
  -F "audio_file=@test_audio/test_10s.wav" \
  -F "title=My Test Recording"
```

**Example: Analyze**
```bash
curl -X POST http://localhost:8000/api/analyze/1/
```

**Analysis Response Schema:**
```json
{
  "shruti_clusters": {
    "shruti_1": { "frame_count": 25, "centroid": [...], "assigned_shruti": "Sa" },
    "...": "..."
  },
  "freq_assignments": [
    { "frame": 0, "frequency": 261.5, "shruti": "Sa", "method": "f0" },
    { "frame": 1, "frequency": 294.3, "shruti": "Ga1", "method": "pcp" }
  ],
  "mean_pcp": [0.12, 0.08, "..."],
  "f0_track": [261.5, 263.1, "null", "..."],
  "voiced_ratio": 0.72,
  "spectral_centroid_timeline": [1523.4, 1601.2, "..."],
  "ghana_patha_valid": true,
  "ghana_patha_confidence": 0.73,
  "ghana_patha_repetition_score": 0.81,
  "ghana_patha_n_segments": 15,
  "ghana_patha_segments": [
    { "segment": 0, "dtw_forward": 0.85, "dtw_reverse": 0.32, "label": "forward" }
  ],
  "ghana_patha_detected_pattern": ["forward", "reverse", "forward", "reverse", "forward"],
  "ghana_patha_dtw_details": { "...": "..." },
  "raga_detection": {
    "best_match": { "name": "Yaman", "tradition": "Hindustani", "confidence": 0.72 },
    "all_scores": [ { "name": "...", "confidence": 0.65 } ],
    "arohana_detected": ["Sa", "Re", "Ga", "Ma"],
    "avarohana_detected": ["Pa", "Dha", "Ni", "Sa"]
  },
  "spectrogram_data": [[...], "..."],
  "mfcc_data": [[...], "..."],
  "chroma_data": [[...], "..."],
  "tempo": 120.5,
  "duration": 60.0
}
```

---

## Dashboard Output Guide

### 1. Spectrogram (Top Left)

A time-frequency heatmap showing where audio energy is concentrated over time.

- **X-axis:** Time in seconds
- **Y-axis:** Frequency bin index (0 = low bass, higher = higher pitch)
- **Color:** Dark = silence/low energy, Bright (orange/white) = loud/high energy
- **What to look for:**
  - Horizontal bright lines = sustained vocal notes
  - Vertical gaps = pauses between phrases
  - Dense bright regions = energetic chanting sections

### 2. Shruti Clusters — K=22 Bar Chart (Top Right)

Shows how many audio frames were assigned to each of the 22 Shruti clusters by K-Means.

- **X-axis:** Cluster labels (shruti_1 through shruti_22)
- **Y-axis:** Number of audio frames in each cluster
- **Color:** Rainbow gradient (each bar = one Shruti)
- **What to look for:**
  - Tall bars = the Shruti microtones the singer used most
  - 3-4 tall bars = narrow pitch range (monotone chanting)
  - Many tall bars = wide microtonal range (melodic singing)
  - The `assigned_shruti` field maps each cluster to its classical name (Sa, Re1, Ga2, etc.)

### 3. 22 Shruti PCP Energy Map (Middle Left)

The Pitch-Class Profile energy distribution across all 22 Shruti bins. This is computed from harmonic STFT analysis fused with pYIN F0 tracking.

- **X-axis:** Shruti names (Sa, Re1, Re2, Ga1, ..., Ni')
- **Y-axis:** Relative energy (0-100%)
- **Color:** Teal = low energy, Amber/Orange = high energy
- **What to look for:**
  - Hot (amber) bars = Shruti microtones with the most energy in the recording
  - Even distribution = melodic content across many notes
  - Concentrated peaks = specific Shruti frequencies dominating

### 4. Ghana Patha Validation (Middle Right)

Displays whether the audio follows the Ghana Patha recursive pattern using DTW-based matching.

- **Green badge** = Pattern Valid (audio has recursive repetition structure)
- **Red badge** = Pattern Invalid (audio is linear/folk/melodic)
- **Confidence %** = Combined score from repetition analysis + DTW pattern matching
- **Segment Timeline** = Scatter plot showing forward vs reverse labels per segment
- **DTW Details** = Per-segment DTW distances for forward and reverse templates

### 5. Raga Detection (Bottom Left)

Identifies the raga using directional arohana/avarohana scoring.

- **Best Match** = Top raga with name, tradition (Hindustani/Carnatic), and confidence
- **Scale Strips** = Visual representation of Arohana (ascending) and Avarohana (descending) scales with detected swaras highlighted
- **Vadi/Samvadi** = The king and minister notes of the detected raga
- **Candidate List** = Other potential ragas ranked by confidence score
- **Bar Chart** = Plotly visualization of top 5 raga confidence scores

### 6. Audio Player (Bottom Right)

WaveSurfer.js-based waveform player for listening to the uploaded audio.

- **Waveform** = Visual representation of the audio amplitude over time
- **Play/Pause** = Toggle playback
- **Time Display** = Current position / total duration

---

## Test Results

### Three-Tier Validation Matrix

| Audio File | Category | Ghana Patha | Raga Detection | Confidence |
|-----------|----------|-------------|----------------|------------|
| Kumaoni Folk Song | Non-Vedic folk | Pattern Invalid | — | 30% |
| `rudram_60s.wav` | Vedic (Samhita Patha) | Pattern Invalid | Detected Bhairav | 65% |
| `isavasya_ghanam_60s.wav` | Vedic (Ghana Patha) | Pattern Valid | — | 68% |

### DTW Tempo Invariance Test

A 3× time-stretched version of a Ghana Patha recording was tested against the original. The DTW algorithm correctly matched the pattern despite the tempo difference, confirming tempo-invariance.

### Raga Directional Scoring Test

Four ragas with similar swara sets but different arohana/avarohana patterns were tested. The directional scoring correctly differentiated them by analyzing pitch gradient direction.

---

## Docker & DevOps

### Dockerfiles

**Backend (`backend/Dockerfile`):**
- Base image: `python:3.13-slim`
- Installs `libsndfile1` (audio library dependency for `soundfile`/`librosa`)
- Installs all Python packages from `requirements.txt`
- Runs `collectstatic` and `migrate` at build time
- Serves via Gunicorn with 2 workers, 120s timeout, preload mode

**Frontend (`frontend/Dockerfile`):**
- Multi-stage build:
  - Stage 1 (`node:20-alpine`): Builds React app with Vite via `npm ci` + `npm run build`
  - Stage 2 (`nginx:alpine`): Copies built files, serves via Nginx
- Nginx proxies `/api/` and `/media/` requests to the backend container

### Docker Compose Services

```yaml
services:
  backend:      # Django + ML engine on port 8000 (2GB mem limit)
  frontend:     # React + Nginx on port 80
  prometheus:   # Metrics collection on port 9090
  node-exporter:# Host metrics on port 9100
  grafana:      # Monitoring dashboard on port 3000 (admin/admin)
```

### Will I Need to Rebuild Docker After Code Changes?

**Short answer: Yes, but only the affected service.**

| Change Type | What to Rebuild | Command |
|-------------|----------------|---------|
| Python code only (`audio_processing.py`, `ml_engine.py`, etc.) | Backend only | `docker compose build backend` |
| New Python package added to `requirements.txt` | Backend only | `docker compose build backend` |
| React component changes (`.jsx`, `.css`) | Frontend only | `docker compose build frontend` |
| New npm package added to `package.json` | Frontend only | `docker compose build frontend` |
| `Dockerfile` changes in either service | That service | `docker compose build backend` or `frontend` |
| `docker-compose.yml` changes | Depends on section | `docker compose up -d` (auto-rebuilds if needed) |
| `k8s/` manifest changes | No rebuild needed | `kubectl apply -k k8s/` |
| Monitoring config changes | No rebuild needed | Restart the monitoring service |

**Docker layer caching:** The Dockerfiles are structured so that:
- `requirements.txt` / `package.json` is copied and installed first (cached if deps don't change)
- Source code is copied last (`COPY . .`), so only the final layer rebuilds on code changes
- This means code-only changes rebuild quickly (seconds, not minutes)

**What you do NOT need to rebuild for:**
- Changes to `views.py`, `ml_engine.py`, `ghana_patha.py`, `raga_mapping.py`, `audio_processing.py` — these are pure code, no new dependencies
- Changes to `.jsx` components, `App.jsx`, `App.css`, `index.css` — frontend code only
- Changes to `k8s/`, `monitoring/`, `nginx.conf` — runtime config, not baked into images
- Database migrations — the `migrate` command runs at build time AND via initContainer in K8s

**What WILL require a rebuild:**
- Adding a new package to `requirements.txt` (e.g., `pip install new_package`)
- Adding a new npm dependency to `package.json`
- Changing the `Dockerfile` itself
- Changing system dependencies (e.g., adding a new `apt-get install` in backend Dockerfile)

---

## Kubernetes Deployment

Kubernetes manifests live in `k8s/` under standard `deployment.yaml` / `service.yaml`
names per component and are wired together with kustomize. Deploy the whole stack
with a single command:

```bash
kubectl apply -k k8s/
```

| File/Dir | Resources |
|----------|-----------|
| `kustomization.yaml` | Deploys everything below (components + monitoring) |
| `secret.yaml` | Secret: `django-secret-key` + `metrics-token` (bearer for `/metrics`, F14) |
| `ingress.yaml` | Ingress (path-based routing: /api, /media → backend; / → frontend) |
| `storage.yaml` | PersistentVolumeClaims: `vedic-data-pvc` (RWX) + `vedic-redis-pvc` |
| `backend/deployment.yaml` | Backend Deployment (1 replica — SQLite single-writer) + initContainer (migrate/collectstatic) |
| `backend/service.yaml` | ClusterIP Service |
| `frontend/deployment.yaml` | Frontend Deployment (2 replicas) |
| `frontend/service.yaml` | ClusterIP Service |
| `celery/deployment.yaml` | Celery worker Deployment (2 replicas) |
| `redis/deployment.yaml` + `service.yaml` | Redis broker (persistent, appendonly) + ClusterIP Service |
| `monitoring/node-exporter.yaml` | DaemonSet + Service |
| `monitoring/prometheus.yaml` | ConfigMap + Deployment + Service (scrapes cluster + prod HF Space) |
| `monitoring/grafana.yaml` | Deployment + Service + datasource/provider ConfigMaps |
| `monitoring/grafana-dashboard.yaml` | Dashboard JSON as ConfigMap |

### Architecture Notes

- **Shared state:** Both backend replicas mount a `PersistentVolumeClaim` (`vedic-data-pvc`) at `/app/data`. The SQLite database and uploaded media live there, so uploads/analyses are visible from either replica.
- **Migrations:** Run via an `initContainer` (once per pod start), not at build time — this initializes the shared volume on first deploy.
- **Configurable backend host:** The frontend nginx config uses `${BACKEND_HOST}` (env-substituted at container start). In K8s it's set to `vedic-backend-service`; in docker-compose it's `backend`.

### Local Testing with Minikube

```bash
# 1. Start Minikube (Docker driver)
minikube start --driver=docker --cpus=4 --memory=4096 --disk-size=20g

# 2. Build images and load into Minikube
docker build -t vedic-acoustica/backend:latest ./backend
docker build -t vedic-acoustica/frontend:latest ./frontend
minikube image load vedic-acoustica/backend:latest
minikube image load vedic-acoustica/frontend:latest

# 3. Deploy
kubectl apply -k k8s/

# 4. Wait for rollout
kubectl rollout status deployment/vedic-backend
kubectl rollout status deployment/vedic-frontend

# 5. Access the app
minikube service vedic-frontend-service --url
```

### Kubernetes Deployment Impact of Code Changes

| Change Type | K8s Action Required |
|-------------|-------------------|
| Python/JS code changes | Rebuild Docker image, load into Minikube, restart deployment |
| `k8s/**` manifest changes | `kubectl apply -k k8s/` (no rebuild needed) |
| Monitoring config changes | `kubectl apply -k k8s/monitoring/` (no rebuild needed) |
| New secrets/environment variables | Update `k8s/secret.yaml` (and matching env in the deployment manifests) |

```bash
# After code changes, deploy to K8s:
docker build -t vedic-acoustica/backend:latest ./backend
minikube image load vedic-acoustica/backend:latest
kubectl rollout restart deployment/vedic-backend
```

---

## CI/CD

GitHub Actions workflows are in `.github/workflows/`:

### CI (`ci.yml`)

Runs on every push/PR to `main`, and is reusable by `cd.yml` (via `workflow_call`):

| Job | What it does |
|-----|--------------|
| **Backend** | `python manage.py check`, `python manage.py test`, verifies ML engine imports (audio_processing, ml_engine, ghana_patha, raga_mapping) |
| **Frontend** | `npm ci`, `npm run lint` (oxlint), `npm run build` (Vite) |
| **Docker Build Check** | Verifies both `Dockerfile`s build successfully (images not pushed) |

### CD (`cd.yml`)

Runs on every push to `main`:

1. **CI Gate** — Reuses `ci.yml` via `workflow_call` so the build only runs when tests pass
2. **Build & Push** — Builds both Docker images and pushes to GitHub Container Registry (GHCR) with `:latest` + `:<sha>` tags

The Kubernetes deploy job was intentionally removed — the K8s demo runs on a local
Minikube cluster, not a cloud cluster, so CI/CD is limited to test + container push.

### Enabling CI/CD

```bash
# 1. Create the GitHub repo and push
git remote add origin https://github.com/<your-username>/Vedic-Acoustica.git
git push -u origin main

# 2. CI runs automatically on the first push — check the Actions tab
# 3. Deploy locally to Minikube with: kubectl apply -k k8s/
```

---

## Monitoring

A full Prometheus + Grafana stack is included. It monitors both the app (Django) and the host (node_exporter).

### Metrics Endpoint

The Django backend exposes Prometheus metrics at `/metrics` (`backend/api/metrics.py`):
- `http_requests_total{method,path}` — request counter
- `http_request_duration_seconds{method,path}` — request duration histogram
- Plus default Python/process metrics

A `MetricsMiddleware` records these on every request automatically.

### Prometheus (`monitoring/prometheus.yml`)

Scrapes three targets:
| Target | What it monitors |
|--------|------------------|
| `localhost:9090` | Prometheus self-monitoring |
| `backend:8000/metrics` | Django application metrics |
| `node-exporter:9100` | Host CPU / memory / disk metrics |

### Grafana (auto-provisioned)

- `monitoring/grafana-datasource.yml` — Prometheus datasource (loaded automatically)
- `monitoring/grafana-provisioning.yml` — dashboard provider config
- `monitoring/grafana-dashboard.json` — dashboard, loaded at startup

Dashboard panels:
- **API Request Rate** — total requests/sec
- **API Request Rate by Endpoint** — per-path/method breakdown
- **Response Latency (p95)** — histogram_quantile of request duration
- **CPU Usage** — node_exporter idle→busy calculation
- **Memory Usage** — MemAvailable / MemTotal
- **Node Uptime** — time since boot
- **Celery Queue Depth** — messages waiting in the broker queue
- **ML Analysis Duration (last)** — most recently completed analysis duration
- **Analyses Completed / Failed** — cumulative worker-side totals (Redis-bridged)

Access Grafana at `http://localhost:3000` (admin/admin). Prometheus at `http://localhost:9090`.

### Run the monitoring stack

```bash
docker compose up -d backend prometheus node-exporter grafana
curl http://localhost:9090/api/v1/targets   # Verify all targets are UP
# Open Grafana → "Vedic Acoustica - System Monitor" dashboard
```

### Monitoring inside Kubernetes

```bash
kubectl apply -k k8s/monitoring/
kubectl port-forward service/prometheus 9090:9090   # Prometheus UI
kubectl port-forward service/grafana 3000:3000      # Grafana (admin/admin)
```

---

## Development

### Adding New Features

**New API endpoint:**
1. Add view in `backend/api/views.py`
2. Add URL in `backend/api/urls.py`
3. Add serializer in `backend/api/serializers.py` if needed

**New ML feature:**
1. Add extraction function in `backend/ml_engine/audio_processing.py`
2. Add processing logic in `backend/ml_engine/ml_engine.py`
3. Return new fields in `backend/api/views.py` analyze endpoint

**New raga:**
1. Add raga entry to `RAGA_DATABASE` in `backend/ml_engine/raga_mapping.py`
2. Include swaras, arohana, avarohana, vadi, samvadi, tradition, time, mood

**New frontend chart:**
1. Create component in `frontend/src/components/`
2. Import in `App.jsx`
3. Use Plotly.js for visualization

### Running Tests

```bash
# Backend
cd backend
python manage.py test

# Frontend
cd frontend
npm run lint
npm run build
```

---

## License

This project was developed as a Semester 5 capstone project integrating AI/ML, Web Technologies, IKS, DevOps, and Software Engineering labs.

---

## Acknowledgments

- Indian Knowledge Systems (IKS) — 22 Shruti theory and Ghana Patha recitation patterns
- [librosa](https://librosa.org/) — Audio feature extraction, pYIN pitch tracking
- [scikit-learn](https://scikit-learn.org/) — K-Means clustering
- [scipy](https://scipy.org/) — DTW cost matrix computation
- [Plotly.js](https://plotly.com/javascript/) — Interactive data visualization
- [WaveSurfer.js](https://wavesurfer.xyz/) — Audio waveform player
- [jsPDF](https://github.com/parallax/jsPDF) — PDF report generation
- [Django](https://www.djangoproject.com/) — Backend web framework
- [React](https://react.dev/) — Frontend UI library
- [Docker](https://www.docker.com/) — Containerization platform
- [Prometheus](https://prometheus.io/) + [Grafana](https://grafana.com/) — Monitoring

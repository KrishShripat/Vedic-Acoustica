# Vedic Acoustica

**Microtonal Voice Analysis & Ghana Patha Validation using Unsupervised Machine Learning**

Vedic Acoustica is a full-stack web application that analyzes audio recordings of Vedic chants, Indian classical singing, and traditional folk music. Unlike standard speech-to-text systems, it does not recognize *what* is being spoken. Instead, it analyzes the **mathematical structure, precise frequencies, and temporal patterns** of the audio using AI/ML.

The system combines modern machine learning with Indian Knowledge Systems (IKS) to automate two tasks:

1. **22 Shruti Detection** — Maps audio frequencies onto the 22 ancient Indian microtonal scale (Shrutis) rather than the standard Western 12-semitone scale, using K-Means clustering.
2. **Ghana Patha Validation** — Detects whether a chant follows the rigid recursive recitation pattern (1-2, 2-1, 1-2-3, 3-2-1, 1-2-3) used by ancient Vedic scholars as an oral error-correction mechanism.

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
- [Docker Containerization](#docker-containerization)
- [Kubernetes Deployment](#kubernetes-deployment)
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

**Vedic Acoustica automates the detection of both of these acoustic properties** using unsupervised machine learning, eliminating the need for human experts to manually verify each recording.

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

The algorithm validates this by:
1. Dividing audio into 1-second segments
2. Computing a self-similarity matrix (cosine similarity between all segment pairs)
3. Measuring the repetition score (fraction of pairs with >0.7 similarity)
4. Clustering segments into phrase types and checking for the Ghana recursion pattern

---

## Machine Learning Pipeline

### Step 1: Audio Feature Extraction (`ml_engine/audio_processing.py`)

Raw audio cannot be fed directly into ML models. The system uses **librosa** to extract three types of features:

| Feature | Function | Purpose |
|---------|----------|---------|
| **MFCCs** | `librosa.feature.mfcc()` | 13 Mel-Frequency Cepstral Coefficients capturing timbre, vocal tract shape, and resonance |
| **Chroma (22-bin)** | `librosa.feature.chroma_stft(n_chroma=22)` | Projects audio energy onto 22 pitch classes (not the standard 12), enabling Shruti-level resolution |
| **Spectral Centroid** | `librosa.feature.spectral_centroid()` | Measures the "center of mass" of the sound spectrum, crucial for echo and resonance analysis |

Additional outputs:
- **STFT Spectrogram** — Time-frequency matrix for visualization
- **Dominant Frequencies** — Per-frame peak frequency via scipy.signal.stft
- **Tempo** — Beat detection via `librosa.beat.beat_track()`

### Step 2: K-Means Clustering (`ml_engine/ml_engine.py`)

The combined MFCC + Chroma feature vectors are passed to **scikit-learn's KMeans** with `n_clusters=22`:

```python
KMeans(n_clusters=22, random_state=42, n_init=10)
```

This groups similar frequency frames into 22 piles, each corresponding to one Shruti. The output includes:
- Cluster labels for every audio frame
- Cluster centroids (the "average" frequency profile of each Shruti)
- Per-frame dominant frequency mapped to the closest Shruti

### Step 3: Ghana Patha Validation (`ml_engine/ghana_patha.py`)

Uses a multi-signal approach:

1. **Self-Similarity Matrix** — Computes cosine similarity between all pairs of 1-second audio segments
2. **Repetition Score** — Fraction of off-diagonal pairs with similarity > 0.7
3. **Phrase Clustering** — K-Means (K=3) groups segments into 3 phrase types
4. **Pattern Matching** — Checks if the phrase sequence matches the Ghana recursion

**Combined Confidence** = 0.5 * Repetition Score + 0.5 * Pattern Match Score

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     USER BROWSER                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │         React Frontend (Port 80 via Nginx)        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │  │
│  │  │ Audio    │ │ Spectro- │ │ Cluster  │          │  │
│  │  │ Uploader │ │ gram     │ │ Plot     │          │  │
│  │  └──────────┘ └──────────┘ └──────────┘          │  │
│  │  ┌──────────┐ ┌──────────────────────┐            │  │
│  │  │ Shruti   │ │ Ghana Patha          │            │  │
│  │  │ Map      │ │ Validation           │            │  │
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
│  │ DRF API     │  │         ML Engine                 │ │
│  │ /api/upload │  │  ┌─────────────┐                 │ │
│  │ /api/list   │→│  │ librosa     │ Feature Extract  │ │
│  │ /api/analyze│  │  └──────┬──────┘                 │ │
│  │             │  │         ▼                         │ │
│  │ SQLite DB   │  │  ┌─────────────┐                 │ │
│  │             │  │  │ scikit-learn│ K-Means K=22     │ │
│  └─────────────┘  │  └──────┬──────┘                 │ │
│                   │         ▼                         │ │
│                   │  ┌─────────────┐                 │ │
│                   │  │ Ghana Patha │ Pattern Valid.   │ │
│                   │  │ Validator   │                  │ │
│                   │  └─────────────┘                 │ │
│                   └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend UI** | React 19 + Vite | User interface, drag-drop upload, interactive charts |
| **Charts** | Plotly.js (react-plotly.js) | Spectrogram heatmap, cluster bar chart, frequency map, pattern timeline |
| **API Client** | Axios | HTTP communication between React and Django |
| **Reverse Proxy** | Nginx | Serves React build, proxies /api/ requests to backend |
| **Backend API** | Django 6 + Django REST Framework | REST endpoints for upload, list, analyze |
| **ML Engine** | librosa 0.11, scikit-learn 1.9 | Audio feature extraction, K-Means clustering |
| **Scientific Computing** | numpy, scipy | Numerical operations, STFT computation |
| **Database** | SQLite (development) | Stores recordings and analysis results |
| **Containerization** | Docker + Docker Compose | Isolated environments for frontend and backend |
| **Orchestration** | Kubernetes (Minikube) | Container orchestration manifests |
| **CI/CD** | GitHub Actions | Automated build, test, and deploy pipeline |
| **Monitoring** | Prometheus + Grafana | Server metrics, CPU usage, request latency |

---

## Project Structure

```
Vedic-Acoustica/
├── backend/                        # Django + ML Engine
│   ├── vedic_acoustica/            # Django project settings
│   │   ├── settings.py             # Configuration (apps, DB, CORS, media)
│   │   ├── urls.py                 # Root URL routing
│   │   ├── wsgi.py                 # WSGI entry point
│   │   └── asgi.py                 # ASGI entry point
│   ├── api/                        # Django app — REST API
│   │   ├── models.py               # AudioRecording model
│   │   ├── serializers.py          # DRF serializers
│   │   ├── views.py                # Upload, list, analyze endpoints
│   │   └── urls.py                 # API URL routes
│   ├── ml_engine/                  # Django app — ML Pipeline
│   │   ├── audio_processing.py     # librosa feature extraction
│   │   ├── ml_engine.py            # K-Means clustering
│   │   ├── shruti_mapping.py       # 22 Shruti frequency table
│   │   └── ghana_patha.py          # Ghana Patha pattern validator
│   ├── migrations/                 # Database migrations
│   ├── manage.py                   # Django CLI
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Backend container image
│   └── .dockerignore               # Excludes venv, __pycache__, etc.
│
├── frontend/                       # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── AudioUploader.jsx   # Drag-drop file upload
│   │   │   ├── SpectrogramView.jsx # Time-frequency heatmap (Plotly)
│   │   │   ├── ClusterPlot.jsx     # K-Means cluster bar chart
│   │   │   ├── ShrutiMap.jsx       # 22 Shruti frequency bars
│   │   │   └── GhanaPathaViz.jsx   # Pattern validation result + timeline
│   │   ├── App.jsx                 # Main app — state management, API calls
│   │   ├── App.css                 # Component styles
│   │   ├── index.css               # Global dark theme
│   │   └── main.jsx                # React entry point
│   ├── index.html                  # HTML template
│   ├── vite.config.js              # Vite config with API proxy
│   ├── package.json                # Node.js dependencies
│   ├── nginx.conf                  # Nginx config for production
│   ├── Dockerfile                  # Multi-stage: build + Nginx
│   └── .dockerignore               # Excludes node_modules, dist
│
├── k8s/                            # Kubernetes manifests
│   ├── backend-deployment.yml      # Backend Deployment + Service
│   ├── frontend-deployment.yml     # Frontend Deployment + Service
│   └── services.yml                # Secret + Ingress
│
├── monitoring/                     # DevOps monitoring
│   ├── prometheus.yml              # Prometheus scrape config
│   └── grafana-dashboard.json      # Grafana dashboard JSON
│
├── test_audio/                     # Sample recordings for testing
│   ├── isavasya_ghanam_60s.wav     # Ghana Patha recording (60s)
│   ├── rudram_60s.wav              # Samhita Patha recording (60s)
│   └── test_10s.wav                # Quick test clip (10s)
│
├── docker-compose.yml              # Full stack: backend + frontend + monitoring
├── .gitignore                      # Git ignore rules
└── README.md                       # This file
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
2. **Upload** — Drag-drop a `.wav` file or click the upload zone
3. **Select** — Click on the recording in the list
4. **Analyze** — Click the "Run Analysis" button
5. **View Results** — Four interactive charts appear:
   - Spectrogram (time-frequency heatmap)
   - Shruti Clusters (K=22 bar chart)
   - 22 Shruti Frequency Map
   - Ghana Patha Validation

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
  "dominant_frequencies": [261.5, 329.8, "..."],
  "spectral_centroid_timeline": [1523.4, 1601.2, "..."],
  "ghana_patha_valid": true,
  "ghana_patha_confidence": 0.68,
  "repetition_score": 1.0,
  "self_similarity": 0.96,
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

### 3. 22 Shruti Frequency Map (Bottom Left)

The theoretical reference scale showing all 22 Shruti frequencies, with detected hits highlighted.

- **X-axis:** Shruti names (Sa, Re1, Re2, Ga1, ..., Ni')
- **Y-axis:** Frequency in Hz (reference: Sa = 261.63 Hz)
- **Color:** Red/pink = detected hits, Gray = undetected
- **What to look for:**
  - Red bars indicate which Shruti frequencies were actually present in the audio
  - This serves as the IKS theoretical reference benchmark

### 4. Ghana Patha Validation (Bottom Right)

Displays whether the audio follows the Ghana Patha recursive pattern.

- **Green checkmark** = Pattern Valid (audio has recursive repetition structure)
- **Red X** = Pattern Invalid (audio is linear/folk/melodic)
- **Confidence %** = Combined score from repetition analysis + pattern matching
- **Detected vs Expected pattern** = If valid, shows the actual vs expected sequence

---

## Test Results

### Three-Tier Validation Matrix

| Audio File | Category | Result | Confidence | What It Proves |
|-----------|----------|--------|------------|----------------|
| Kumaoni Folk Song | Non-Vedic folk | Pattern Invalid | 30% | Correctly rejects non-structured melody |
| `rudram_60s.wav` | Vedic (Samhita Patha) | Pattern Invalid | 65% | Distinguishes linear chanting from Ghana Patha |
| `isavasya_ghanam_60s.wav` | Vedic (Ghana Patha) | Pattern Valid | 68% | Correctly detects recursive 1-2, 2-1 loops |

### Why These Results Matter

The algorithm is **not returning random guesses**. It correctly:
- Rejects folk music (no recursive structure)
- Rejects linear Vedic chanting (Samhita Patha — sequential, not recursive)
- Accepts Ghana Patha (the specific back-and-forth mathematical pattern)

This three-tier comparison demonstrates genuine audio structural analysis, not hardcoded responses.

---

## Docker Containerization

### Dockerfiles

**Backend (`backend/Dockerfile`):**
- Base image: `python:3.13-slim`
- Installs `libsndfile1` (audio library dependency)
- Installs all Python packages from `requirements.txt`
- Runs `collectstatic` and `migrate` at build time
- Serves via Gunicorn with 2 workers, 120s timeout, preload mode

**Frontend (`frontend/Dockerfile`):**
- Multi-stage build:
  - Stage 1 (`node:20-alpine`): Builds React app with Vite
  - Stage 2 (`nginx:alpine`): Copies built files, serves via Nginx
- Nginx proxies `/api/` requests to the backend container

### Docker Compose Services

```yaml
services:
  backend:    # Django + ML engine on port 8000
  frontend:   # React + Nginx on port 80
  prometheus: # Metrics collection on port 9090
  grafana:    # Monitoring dashboard on port 3000
```

### Key Commands

```bash
docker compose up -d backend frontend   # Start app (no monitoring)
docker compose up -d                    # Start everything including monitoring
docker compose down                     # Stop all containers
docker compose ps                       # List running containers
docker compose logs backend             # View backend logs
docker compose logs -f backend          # Follow logs in real-time
docker compose build backend            # Rebuild backend image
docker image ls                         # List all Docker images
docker volume ls                        # List Docker volumes
```

### How Containers Communicate

1. User visits `http://localhost` → Nginx serves the React app
2. React sends API request to `/api/upload/` → same browser URL
3. Nginx sees `/api/` prefix → proxies request to `http://backend:8000`
4. Django processes the request → runs ML pipeline → returns JSON
5. Nginx forwards the response back to the browser

The containers communicate over a private Docker network using container names as hostnames (`backend`, `frontend`).

---

## Kubernetes Deployment

Kubernetes manifests are in `k8s/`:

| File | Resources |
|------|-----------|
| `backend-deployment.yml` | Deployment (2 replicas) + initContainer (migrate/collectstatic) + PersistentVolumeClaim (shared SQLite + media) + ClusterIP Service |
| `frontend-deployment.yml` | Deployment (2 replicas) + LoadBalancer Service |
| `services.yml` | Secret (Django key) + Ingress (routing rules) |

### Architecture Notes

- **Shared state:** Both backend replicas mount a `PersistentVolumeClaim` (`vedic-data-pvc`) at `/app/data`. The SQLite database and uploaded media live there, so uploads/analyses are visible from either replica.
- **Migrations:** Run via an `initContainer` (once per pod start), not at build time — this initializes the shared volume on first deploy.
- **Configurable backend host:** The frontend nginx config uses `${BACKEND_HOST}` (env-substituted at container start). In K8s it's set to `vedic-backend-service`; in docker-compose it's `backend`.

### Local Testing with Minikube

```bash
# 1. Start Minikube (Docker driver — runs natively on Ubuntu, no VirtualBox)
minikube start --driver=docker --cpus=4 --memory=4096 --disk-size=20g

# 2. Build images and load into Minikube
docker build -t vedic-acoustica/backend:latest ./backend
docker build -t vedic-acoustica/frontend:latest ./frontend
minikube image load vedic-acoustica/backend:latest
minikube image load vedic-acoustica/frontend:latest

# 3. Deploy
kubectl apply -f k8s/

# 4. Wait for rollout (backend migrations run in initContainer first)
kubectl rollout status deployment/vedic-backend
kubectl rollout status deployment/vedic-frontend

# 5. Expose the LoadBalancer (enables an External-IP in Minikube)
minikube addons enable metallb
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: config
  namespace: metallb-system
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - 192.168.49.100-192.168.49.110
EOF

# 6. Access the app at the LoadBalancer External-IP
minikube service vedic-frontend-service --url
# → http://192.168.49.100  (frontend + /api proxy through nginx)
```

**End-to-end test through the cluster:**

```bash
# Upload a recording (round-robins across both backend replicas)
curl -X POST -F "title=Test" -F "audio_file=@test_audio/test_10s.wav" \
  http://192.168.49.100/api/upload/

# Run the 22-Shruti K-Means + Ghana Patha analysis
curl -X POST http://192.168.49.100/api/analyze/1/

# Both uploads are visible regardless of which replica served the request
curl http://192.168.49.100/api/recordings/
```

---

## Continuous Integration / Continuous Deployment

GitHub Actions workflows are in `.github/workflows/`:

### CI (`ci.yml`)

Runs on every push/PR to `main`:

| Job | What it does |
|-----|--------------|
| **Backend** | `python manage.py check`, `python manage.py test`, verifies ML engine imports (librosa + scikit-learn) |
| **Frontend** | `npm ci`, `npm run lint` (oxlint), `npm run build` (Vite) |

### CD (`cd.yml`)

Runs on every push to `main`:

1. **Build & Push** — builds both Docker images and pushes to GitHub Container Registry (GHCR) with `:latest` + `:<sha>` tags
2. **Deploy** — (disabled by default, `if: false`) applies `k8s/` manifests to a cluster using a `KUBECONFIG` secret, substituting image refs for the freshly-built GHCR images

### Enabling CI/CD

```bash
# 1. Create the GitHub repo and push
git remote add origin https://github.com/<your-username>/Vedic-Acoustica.git
git push -u origin main

# 2. CI runs automatically on the first push — check Actions tab
# 3. To enable the CD deploy step, remove `if: false` and add a
#    KUBECONFIG secret (base64-encoded kubeconfig) to repo settings.
```

## Monitoring

A full Prometheus + Grafana stack is included in `docker-compose.yml`. It monitors both the app (Django) and the host (node_exporter).

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

Access Grafana at `http://localhost:3000` (admin/admin). Prometheus at `http://localhost:9090`.

### Run the monitoring stack

```bash
docker compose up -d backend prometheus node-exporter grafana
# Verify all Prometheus targets are UP:
curl http://localhost:9090/api/v1/targets
# Open Grafana → "Vedic Acoustica - System Monitor" dashboard
```

### Verified metrics (docker-compose)

| Metric | Value |
|--------|-------|
| API request rate | ~0.9 req/s (under load test) |
| p95 latency | ~5 ms |
| Host CPU | ~10% |
| Host memory | ~56% |

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
- [librosa](https://librosa.org/) — Audio feature extraction
- [scikit-learn](https://scikit-learn.org/) — K-Means clustering
- [Plotly.js](https://plotly.com/javascript/) — Interactive data visualization
- [Django](https://www.djangoproject.com/) — Backend web framework
- [React](https://react.dev/) — Frontend UI library
- [Docker](https://www.docker.com/) — Containerization platform

# Vedic Acoustica — Architecture Report

> A single codebase, four deployment shapes. This document describes how the
> project is structured and why a **dual-deployment strategy** drives the
> public demo, while the identical container images also run locally
> (Docker Compose) and on Kubernetes.

---

## 1. Deployment Map

```
                         ↓  public demo  ↓
┌───────────────────────────────────────────────────────────────┐
│  VERCEL (serverless)                        HF.ZERO GPU     │
│  Static React SPA (frontend/dist)           https://krish-  │
│  + vercel.json edge rewrites                shripat-vedic-  │
│      /api/*    → ../../backend.hf.space/api/*   backend.hf. │
│      /media/*  → ../../backend.hf.space/media/*        space │
│                                                              │
│      one-container backend (backend/app.py):                 │
│      redis-server → migrate → celery → gunicorn :7860        │
└───────────────┬──────────────────────────────────────────────┘
                │
                │  same source of truth (ml_engine, api/*, Dockerfiles)
                ▼
┌─────────────────────────────┐        ┌─────────────────────────────┐
│  DOCKER COMPOSE (local)     │        │  KUBERNETES / Minikube      │
│  backend :8000 · celery     │        │  k8s/** (kustomize)         │
│  redis · frontend :80       │        │  backend · celery · redis   │
│  prometheus :9090           │        │  frontend · monitoring      │
│  grafana :3000              │        └─────────────────────────────┘
└─────────────────────────────┘
```

The **same** `backend/Dockerfile` and `frontend/Dockerfile` produce the images for
all three runtimes:

| Deployment | Serves | Proxy | DB/MSg | ML work |
|-----------|--------|-------|--------|---------|
| **Vercel** | static React SPA (edge CDN) | `vercel.json` rewrites | — | — |
| **HF Space** | Django API (gunicorn :7860) | platform reverse proxy | SQLite + Redis (in-container) | Celery (same container) |
| **Docker Compose** | nginx serving SPA :80 | nginx → `backend:8000` | SQLite + Redis (containers) | Celery worker (container) |
| **Kubernetes** | nginx per pod :80 + Ingress | nginx → ClusterIP | SQLite (RWX PVC) + Redis (Stateful pod) | Celery Deployment (2 replicas) |

---

## 2. Dual-Deployment Strategy (public demo)

The public demo deliberately splits the stack across two managed services with
**zero fixed hosting cost and no VPS**:

1. **Vercel (serverless)** hosts the React build.
   `frontend/vercel.json` rewrites the two dynamic URL namespaces to the HF
   backend, so the browser never talks cross-origin — it calls `/api/*` on the
   same origin and Vercel proxies it:

   ```json
   { "source": "/api/(.*)",   "destination": "https://krish-shripat-vedic-backend.hf.space/api/$1" }
   { "source": "/media/(.*)", "destination": "https://krish-shripat-vedic-backend.hf.space/media/$1" }
   ```

   This replaces the nginx reverse proxy of the container deployments with a
   **routing-layer proxy**: the SPA’s `API_BASE = '/api'` (`src/App.jsx`) is
   unchanged between Vercel and local/K8s.

2. **Hugging Face Space (ZeroGPU)** runs the entire backend in one container via
   `backend/app.py` — the “trojan horse” boot script:

   ```
   app.py order of operations
     1. Set HF platform proxies + allowed hosts      (host = *.hf.space)
     2. Start Redis in-process (redis-server child)  (broker + results + locks)
     3. python manage.py migrate
     4. Launch Celery worker (in-container child)
     5. gunicorn --bind 0.0.0.0:7860 --workers 2 ...  (HuggingFace expects 7860)
   ```

   Because the Space is a single process group, Redis/Celery/https have **no
   cross-service networking** — files go straight to `MEDIA_ROOT` on local disk.
   Platform sensors boot/sleep the Space on idle, so cost scales to zero between
   uses.

This split keeps the SPA trivial to serve (Vercel edge) while the heavy librosa /
pYIN / DTW computation lives where it belongs (HF ZeroGPU). The same reasoning
maps to the “enterprise” variant — nginx/Docker Compose or K8s with a real
reverse proxy and STEAM services.

---

## 3. Local Stack (Docker Compose)

`docker-compose.yml` names six services plus persistent volumes:

| Service | Port | Purpose |
|---------|------|---------|
| `redis` | 6379 | broker/result backend (health-gated) |
| `backend` | 8000 | Django + DRF + gunicorn, `entrypoint.sh` runs migrations |
| `celery` | — | `celery -A vedic_acoustica worker --concurrency=2` |
| `frontend` | 80 | nginx serving the SPA, proxying `/api/`, `/media/` to `backend` |
| `prometheus` | 9090 | scraping `backend:8000`, `node-exporter:9100` and the **prod Space** |
| `node-exporter` | 9100 | host metrics |
| `grafana` | 3000 | auto-provisioned dashboard (admin/admin) |

Key semantics:

- **Shared volumes** `media_data` and `db_data` are mounted into *both* `backend`
  and `celery`, so uploads written by Django are visible to the worker and
  `.npz` matrices written by the worker are served by Django.
- **Memory floors**: 2 Celery workers × ~1.5 GB peak each → `mem_limit: 6g`.
- **`.env` (git-ignored)**: `METRICS_TOKEN=…` is forwarded into Prometheus, which
  injects it into the `vedic-backend-prod` scrape job via `${METRICS_TOKEN}`
  (see §5).

```bash
cp .env.example .env      # optional; sets METRICS_TOKEN for prod scrape
docker compose up -d --build
docker compose ps
```

---

## 4. Kubernetes Deployment (Minikube / on-prem)

`k8s/` is organised as **standard per-component `deployment.yaml` /
`service.yaml`** and wired with kustomize — one command deploys everything:

```
k8s/
├── kustomization.yaml          # kubectl apply -k k8s/
├── secret.yaml                 # django-secret-key + metrics-token (F14)
├── ingress.yaml                # path routing: /api /media → backend; / → frontend
├── storage.yaml                # vedic-data-pvc (RWX) + vedic-redis-pvc
├── backend/{deployment,service}.yaml
├── frontend/{deployment,service}.yaml
├── celery/deployment.yaml
├── redis/{deployment,service}.yaml
└── monitoring/                 # node-exporter, prometheus, grafana + kustomization
```

```bash
minikube start --driver=docker --cpus=4 --memory=4096 --disk-size=20g
docker build -t vedic-acoustica/backend:latest ./backend
docker build -t vedic-acoustica/frontend:latest ./frontend
minikube image load vedic-acoustica/backend:latest
minikube image load vedic-acoustica/frontend:latest
kubectl apply -k k8s/
minikube service vedic-frontend-service --url
```

Notes:

- **Single-writer SQLite**: backend runs 1 replica; the shared `vedic-data-pvc`
  is `ReadWriteMany` so backend init/migrate, API pods and Celery pods mount the
  same `/app/data`.
- **Migrations** run via initContainer on first start, not at build time.
- **Metrics auth**: in-cluster backend runs with `DJANGO_DEBUG=False` and must
  supply `METRICS_TOKEN`; it is read from the `vedic-secrets` Secret, and
  Prometheus mounts the same Secret value as a `bearer_token_file` so cluster
  + prod scrapes authenticate (F14).

---

## 5. Monitoring & Telemetry

### 5.1 `/metrics` endpoint

`backend/api/metrics.py` exposes a Prometheus text-format endpoint via
`prometheus_client`:

| Metric | Kind | Meaning |
|--------|------|---------|
| `http_requests_total{method,path}` | Counter | cardinality-safe (PKs normalized to `{pk}`) |
| `http_request_duration_seconds{method,path}` | Histogram | request latency (p95 in dashboard) |
| `celery_queue_depth{queue}` | Gauge | messages waiting in the broker queue (`LLEN`) |
| `ml_processing_seconds_last` | Gauge | duration of the most recent analysis |
| `ml_analyses_total{status=ok|error}` | Gauge | cumulative analysis outcomes |

**Cross-process bridge.** Gunicorn and the Celery workers are separate
processes, so worker-side samples cannot be appended to the web scrapes. The
worker records outcomes to Redis keys (`vedic:metrics:*`) in
`api/tasks.py::_record_ml_metrics`; `metrics._bridge_worker_metrics()` reads
them (Redis is already the broker) and exposes them as gauges on every scrape,
**plus** uses `LLEN` for queue depth — same code path in every deployment.

**Auth guard (F14).** When `DJANGO_DEBUG=False`, `/metrics` requires
`Authorization: Bearer $METRICS_TOKEN`. With no token configured the view is
unmatchable (`chr(0)`), forcing deployers to set one. On the HF Space, the
Space’s token doubles as `METRICS_TOKEN`.

### 5.2 Prometheus

- `monitoring/prometheus.yml` (Docker Compose) scrapes, alongside local targets,
  the **production Space** job `vedic-backend-prod` at
  `https://krish-shripat-vedic-backend.hf.space/metrics/` with
  `bearer_token: '${METRICS_TOKEN}'` substituted from the container env
  (`docker-compose.yml` forwards the git-ignored `.env` value). Poll the
  verified endpoint:

  ```bash
  curl -H "Authorization: Bearer $METRICS_TOKEN" \
       https://krish-shripat-vedic-backend.hf.space/metrics/
  ```

- `k8s/monitoring/prometheus.yaml` uses a `bearer_token_file` mounted from the
  `vedic-secrets` Secret (k8s ConfigMaps cannot env-substitute at runtime) and
  reuses the identical prod Space job.

### 5.3 Grafana

`monitoring/grafana-dashboard.json` (synced to
`k8s/monitoring/grafana-dashboard.yaml`) auto-provisions a dark-theme dashboard,
“Vedic Acoustica - System Monitor”, with panels for API request rate, per-path
rate, p95 latency, CPU, memory, uptime, **Celery queue depth**, **ML analysis
duration** and **completed/failed analysis** counters. Prometheus and prod are
scraped side-by-side, so the same dashboard shows dev + production.

```bash
docker compose up -d prometheus node-exporter grafana
# Prometheus → http://localhost:9090/targets   (all UP)
# Grafana    → http://localhost:3000           (admin/admin)
```

---

## 6. Security Notes

| Concern | Mitigation |
|---------|-----------|
| `METRICS_TOKEN` | Bearer-guard (F14); never committed — HF token lives in Space env, local value in git-ignored `.env`, k8s value in `vedic-secrets` |
| `DJANGO_SECRET_KEY` | Placeholder in `k8s/secret.yaml`; real key via `kubectl create secret` / HF env |
| Secrets in git | `.env` is git-ignored; secret manifests are placeholders |
| Metrics cardinality | URL PKs bucketed to `{pk}` to bound label space |
| Public exposure | `/metrics/` returns 403 without token; API hardened per F1–F15 audit |

---

## 7. CI/CD

`.github/workflows/cd.yml`: on push to `main`, CI gate → build/push backend +
frontend images to GHCR → pin digest SHAs into `k8s/backend/deployment.yaml`,
`k8s/celery/deployment.yaml`, `k8s/frontend/deployment.yaml` → `kubectl apply -k
k8s/` (only when a `KUBECONFIG` secret is configured).

---

## 8. Deployment Runbooks

**Update the HF backend Space**

```bash
git remote add hf https://huggingface.co/spaces/KrishShripat/vedic-backend   # once
git push hf main
```

**Live-check after deploy**

```bash
curl -s https://krish-shripat-vedic-backend.hf.space/api/recordings/        # → JSON
curl -H "Authorization: Bearer $METRICS_TOKEN" \
     https://krish-shripat-vedic-backend.hf.space/metrics/                  # → Prometheus
```

**Local** → `docker compose up -d --build` · **K8s** → `kubectl apply -k k8s/`
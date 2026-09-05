import os
import re
import time

import redis as redislib
from django.conf import settings
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from django.http import HttpResponse

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path'],
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'path'],
)


# ---------------------------------------------------------------------------
# Cross-process ML + Celery metrics
#
# Gunicorn (serving /metrics) and the Celery workers are *separate processes*,
# so histogram/counter samples recorded in the workers can never appear in the
# web process's scrape.  We bridge that gap with Redis (already the broker):
#   • workers INCR / SET keys when an analysis finishes (see api/tasks.py)
#   • this view reads those keys and exposes them as gauges on every scrape
# ---------------------------------------------------------------------------

CELERY_QUEUE_DEPTH = Gauge(
    'celery_queue_depth',
    'Number of messages currently waiting in the Celery broker queue',
    ['queue'],
)

ML_PROCESSING_LAST_SECONDS = Gauge(
    'ml_processing_seconds_last',
    'Duration in seconds of the most recently completed analysis',
)

ML_ANALYSES_TOTAL = Gauge(
    'ml_analyses_total',
    'Total analyses completed across all Celery workers',
    ['status'],
)

_REDIS_URL = getattr(settings, 'CELERY_BROKER_URL', '') or ''


def _redis_conn() -> redislib.Redis:
    return redislib.from_url(_REDIS_URL)


def _bridge_worker_metrics() -> None:
    """Expose worker-side ML/celery state on this process's /metrics endpoint."""
    if not _REDIS_URL:
        return
    queue = getattr(settings, 'CELERY_QUEUE', 'celery')
    try:
        conn = _redis_conn()
        try:
            last = conn.get('vedic:metrics:ml_last_seconds')
            ok = conn.get('vedic:metrics:ml_analyses_ok')
            err = conn.get('vedic:metrics:ml_analyses_error')
            if last is not None:
                ML_PROCESSING_LAST_SECONDS.set(float(last))
            ML_ANALYSES_TOTAL.labels(status='ok').set(int(ok or 0))
            ML_ANALYSES_TOTAL.labels(status='error').set(int(err or 0))
            CELERY_QUEUE_DEPTH.labels(queue=queue).set(conn.llen(queue))
        finally:
            conn.close()
    except (redislib.RedisError, TypeError, ValueError):
        pass  # metrics must never break a scrape


# Regex patterns that replace numeric primary keys with a fixed placeholder.
# Add new patterns here whenever a URL segment contains a dynamic integer ID.
_PK_PATTERNS: list[tuple[re.Pattern, str]] = [
    # /api/analyze/<pk>/          → /api/analyze/{pk}/
    (re.compile(r'(/api/analyze/)\d+(/?)'), r'\g<1>{pk}\2'),
    # /api/recordings/<pk>/       → /api/recordings/{pk}/
    (re.compile(r'(/api/recordings/)\d+(/?)'), r'\g<1>{pk}\2'),
    # /api/upload/<pk>/           → /api/upload/{pk}/   (future-proof)
    (re.compile(r'(/api/upload/)\d+(/?)'), r'\g<1>{pk}\2'),
]


def _normalize_path(raw_path: str) -> str:
    """Replace integer PK segments with '{pk}' to prevent label cardinality explosion."""
    for pattern, replacement in _PK_PATTERNS:
        raw_path = pattern.sub(replacement, raw_path)
    return raw_path


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        normalized_path = _normalize_path(request.path)
        method = request.method
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(method=method, path=normalized_path).inc()
        REQUEST_DURATION.labels(method=method, path=normalized_path).observe(duration)
        return response


# ---------------------------------------------------------------------------
# Bearer-token auth guard
#
# In production set the METRICS_TOKEN environment variable (any random string,
# e.g. `openssl rand -hex 32`).  Then add the same value to prometheus.yml:
#
#   scrape_configs:
#     - job_name: 'vedic-backend'
#       bearer_token: '<your-token>'
#       ...
#
# If the env var is absent (local dev / Docker Compose without the var set)
# the endpoint is open — nothing breaks during development.
# ---------------------------------------------------------------------------

_METRICS_TOKEN: str | None = os.environ.get('METRICS_TOKEN') or None
if not settings.DEBUG and not _METRICS_TOKEN:
    _METRICS_TOKEN = chr(0)   # never match; deployers must set a token


def metrics_view(request):
    if request.method != 'GET':
        return HttpResponse(status=405)

    if _METRICS_TOKEN is not None:
        auth_header = request.headers.get('Authorization', '')
        if auth_header != f'Bearer {_METRICS_TOKEN}':
            return HttpResponse(status=403)

    _bridge_worker_metrics()
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)

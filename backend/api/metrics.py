import re
import time

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
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


def metrics_view(request):
    if request.method == 'GET':
        return HttpResponse(
            generate_latest(),
            content_type=CONTENT_TYPE_LATEST,
        )
    return HttpResponse(status=405)

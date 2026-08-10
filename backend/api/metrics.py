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


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        method = request.method
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(method=method, path=path).inc()
        REQUEST_DURATION.labels(method=method, path=path).observe(duration)
        return response


def metrics_view(request):
    if request.method == 'GET':
        return HttpResponse(
            generate_latest(),
            content_type=CONTENT_TYPE_LATEST,
        )
    return HttpResponse(status=405)

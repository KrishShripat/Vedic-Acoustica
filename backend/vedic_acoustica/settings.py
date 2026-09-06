from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


DEBUG = _env_bool('DJANGO_DEBUG')

_secret_key = os.environ.get('DJANGO_SECRET_KEY', '')
if not _secret_key:
    if not DEBUG:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set via the DJANGO_SECRET_KEY environment variable in production."
        )
    _secret_key = 'django-insecure-dev-key-replace-in-production'
SECRET_KEY = _secret_key

_allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must be set via the DJANGO_ALLOWED_HOSTS environment variable in production."
    )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'api',
    'ml_engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'api.metrics.MetricsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vedic_acoustica.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'vedic_acoustica.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')),
        # Wait up to 20 s for a write lock to release before raising
        # OperationalError. This reduces concurrent-write failures when
        # multiple Celery workers and Gunicorn processes access the DB
        # simultaneously.
        'OPTIONS': {'timeout': 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    'http://localhost',
    'http://localhost:5173',
    'http://127.0.0.1',
]
# Production: set CORS_EXTRA_ORIGINS to a comma-separated list of allowed
# origins (e.g. "https://vedic.local,https://www.vedic.example.com").
# This avoids hardcoding the production domain and keeps the K8s deployment
# fully configurable via ConfigMap / Secret.
_extra_origins = os.environ.get('CORS_EXTRA_ORIGINS', '')
if _extra_origins:
    CORS_ALLOWED_ORIGINS += [o.strip() for o in _extra_origins.split(',') if o.strip()]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Token auth is what the React frontend uses
        # (Authorization: Token <key>).  SessionAuthentication is intentionally
        # omitted: its CSRF enforcement turns unauthenticated POSTs into 403
        # instead of 401, which muddies the login workflow.  The Django admin
        # (/admin/) authenticates via its own session auth, not DRF.
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Read endpoints stay open by default; upload/analyze opt in to
        # IsAuthenticated at the view level, and /api/admin/* requires staff.
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.JSONParser',
    ],
    # ---------------------------------------------------------------------------
    # Throttling — protects all endpoints from anonymous abuse without
    # introducing an authentication requirement or breaking the frontend.
    #
    # Scope breakdown:
    #   anon          → 60 req/min  — list recordings, recording detail, SSE status
    #   upload_anon   → 10 req/hr   — file upload (disk + bandwidth cost)
    #   analyze_anon  → 10 req/hr   — ML analysis trigger (CPU + memory cost)
    #
    # Views opt in to a specific scope via a custom throttle subclass (see
    # api/views.py).  The default 'anon' scope is the global fallback applied
    # to any view that does not declare its own throttle_classes.
    # ---------------------------------------------------------------------------
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':         '60/minute',   # default for low-cost read endpoints
        'upload_anon':  '10/hour',     # per-IP limit on audio file uploads
        'analyze_anon': '10/hour',     # per-IP limit on ML analysis triggers
    },
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
# Serialise task arguments as JSON (safer than the default pickle)
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
# Acknowledge tasks only after they complete so a worker crash re-queues the job
CELERY_TASK_ACKS_LATE = True
# Restart each worker process after ~1.5 GB RSS to prevent OOM kills.
# librosa analyses can peak at ~1.5 GB and CPython's arena allocator retains
# freed memory; without this setting RSS grows monotonically.
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 1_500_000  # KB ≈ 1.5 GB

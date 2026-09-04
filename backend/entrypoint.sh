#!/bin/sh
# ---------------------------------------------------------------------------
# Docker entrypoint for Vedic Acoustica backend services.
#
# Runs database migrations at container startup (runtime, NOT image build time),
# then executes the requested command or starts Gunicorn by default.
#
# Why here and not in the Dockerfile?
#   - Migrations require runtime database access (e.g. mounted volumes or
#     network services), which are unavailable during image build.
#   - collectstatic remains in the Dockerfile build step.
#
# Celery worker / custom commands:
#   - When invoked with custom arguments (e.g., celery worker), migrations
#     are not run again to avoid concurrent SQLite write locks.
#   - Signals are passed cleanly via `exec "$@"`.
# ---------------------------------------------------------------------------

set -e

# Run migrations only when starting the web server or when no args are passed
if [ "$1" = "gunicorn" ] || [ $# -eq 0 ]; then
    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput
    echo "[entrypoint] Migrations complete."
fi

# If arguments were provided, execute them (e.g. celery worker or custom manage.py command)
if [ $# -gt 0 ]; then
    exec "$@"
else
    echo "[entrypoint] Starting Gunicorn..."
    exec gunicorn vedic_acoustica.wsgi:application \
        --bind 0.0.0.0:8000 \
        --worker-class gthread \
        --workers 2 \
        --threads 4 \
        --timeout 360 \
        --preload
fi

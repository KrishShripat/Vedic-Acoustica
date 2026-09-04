FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN DJANGO_SECRET_KEY=build-placeholder DJANGO_DEBUG=True \
    python manage.py collectstatic --noinput

EXPOSE 8000

# Copy the startup script and make it executable.
# The script runs `migrate --noinput` at container start-up (runtime),
# then exec's Gunicorn so it is PID 1 and receives signals cleanly.
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "vedic_acoustica.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--preload"]

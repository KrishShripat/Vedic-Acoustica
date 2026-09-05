import os
import subprocess
import time

print("Starting Trojan Horse setup...")

# Hugging Face forwards requests with Host: <space>.hf.space. Production
# (DEBUG=False) requires DJANGO_ALLOWED_HOSTS, so cover the HF proxy hosts here.
if not os.environ.get('DJANGO_ALLOWED_HOSTS'):
    os.environ['DJANGO_ALLOWED_HOSTS'] = '.hf.space,localhost,127.0.0.1'

# settings.py reads CORS_EXTRA_ORIGINS, not FRONTEND_URL. Translate the HF
# Space variable so the Vercel frontend can call the API.
if os.environ.get('FRONTEND_URL') and not os.environ.get('CORS_EXTRA_ORIGINS'):
    os.environ['CORS_EXTRA_ORIGINS'] = os.environ['FRONTEND_URL']

# 1. Start Redis in the background
print("Starting Redis...")
subprocess.Popen(["redis-server"])
time.sleep(2)
import redis as redislib
for attempt in range(10):
    try:
        redislib.Redis(host='127.0.0.1', socket_connect_timeout=1).ping()
        print("Redis is up.")
        break
    except Exception as exc:
        print(f"Waiting for Redis ({attempt + 1}/10)... {exc}")
        time.sleep(1)

# 2. Run Database Migrations
print("Running migrations...")
if os.system("python manage.py migrate --noinput") != 0:
    print("WARNING: migrations failed, continuing anyway.")

# 3. Start Celery Worker
print("Starting Celery...")
celery_log = open("celery.log", "a")
subprocess.Popen(
    ["celery", "-A", "vedic_acoustica", "worker", "--loglevel=info", "--concurrency=2"],
    stdout=celery_log,
    stderr=subprocess.STDOUT,
)

# 4. Start Django via Gunicorn on port 7860 (the port Hugging Face watches)
print("Starting Django on port 7860...")
while True:
    ret = os.system("gunicorn vedic_acoustica.wsgi:application "
                    "--bind 0.0.0.0:7860 --workers 2 --timeout 120")
    print(f"Gunicorn exited with code {ret}, restarting in 5s...")
    time.sleep(5)
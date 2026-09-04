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

CMD ["gunicorn", "vedic_acoustica.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--preload"]

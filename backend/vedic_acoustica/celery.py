"""
Celery application for Vedic Acoustica.

This module is imported by vedic_acoustica/__init__.py so that the Celery
app is always available as ``vedic_acoustica.celery.app`` and the Django
@shared_task decorator works from any app without circular imports.
"""

import os

from celery import Celery

# Tell Celery which Django settings module to use.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vedic_acoustica.settings')

app = Celery('vedic_acoustica')

# Read Celery configuration from the CELERY_* namespace in Django settings.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover @shared_task definitions in each installed app's tasks.py.
app.autodiscover_tasks()

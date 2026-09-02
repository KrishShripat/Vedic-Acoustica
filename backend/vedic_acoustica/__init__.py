# Ensure the Celery app is loaded whenever Django starts so that
# @shared_task decorators in api/tasks.py and elsewhere are registered.
from .celery import app as celery_app  # noqa: F401

__all__ = ('celery_app',)

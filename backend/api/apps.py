from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _enable_sqlite_wal(sender, connection, **kwargs):
    """Enable Write-Ahead Logging (WAL) and synchronous=NORMAL on SQLite connections."""
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        connection_created.connect(_enable_sqlite_wal)

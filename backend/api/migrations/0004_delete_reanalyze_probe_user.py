"""One-time cleanup: remove the temporary ``reanalyze_probe`` user.

Created by the 2026-10-09 live re-analysis pass.  Safe and idempotent: deleting
a user that does not exist is a no-op, and the probe user owns no recordings.
"""

from django.db import migrations

_PROBE_USERNAME = 'reanalyze_probe'


def remove_probe_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username=_PROBE_USERNAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_audiorecording_corpus_metadata'),
    ]

    operations = [
        migrations.RunPython(remove_probe_user, migrations.RunPython.noop),
    ]

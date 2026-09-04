from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add slim metadata + matrix-file-path fields.

    analysis_result is left untouched (nullable) so existing rows survive.
    The offload_and_vacuum management command will drain it later.
    """

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='audiorecording',
            name='analysis_metadata',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='audiorecording',
            name='matrices_file',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]

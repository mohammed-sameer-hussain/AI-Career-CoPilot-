from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('jobs', '0006_backgroundtask')]

    operations = [
        migrations.AddField(
            model_name='application',
            name='structured_output',
            field=models.JSONField(default=dict),
        ),
    ]

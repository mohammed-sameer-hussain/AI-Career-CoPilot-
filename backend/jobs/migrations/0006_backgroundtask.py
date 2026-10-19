from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('jobs', '0005_jobmatch_hiring_factors_jobmatch_hiring_probability_and_more')]

    operations = [
        migrations.CreateModel(
            name='BackgroundTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(max_length=255, unique=True)),
                ('kind', models.CharField(max_length=80)),
                ('dedupe_key', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('STARTED', 'Started'), ('RETRY', 'Retrying'), ('SUCCESS', 'Succeeded'), ('FAILURE', 'Failed')], default='PENDING', max_length=20)),
                ('result', models.JSONField(blank=True, null=True)),
                ('error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='background_tasks', to='jobs.candidateprofile')),
            ],
        ),
        migrations.AddConstraint(
            model_name='backgroundtask',
            constraint=models.UniqueConstraint(condition=Q(status__in=['PENDING', 'STARTED', 'RETRY']), fields=('profile', 'kind', 'dedupe_key'), name='unique_active_background_task'),
        ),
    ]

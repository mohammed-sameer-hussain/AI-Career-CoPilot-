from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('jobs','0002_candidateprofile_password')]
    operations=[
        migrations.AddField(model_name='application',name='interview_qa',field=models.JSONField(default=list)),
        migrations.CreateModel(name='AssistantMessage',fields=[
            ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
            ('role',models.CharField(choices=[('user','User'),('assistant','Assistant')],max_length=20)),
            ('content',models.TextField()),
            ('created_at',models.DateTimeField(auto_now_add=True)),
            ('job',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to='jobs.job')),
            ('profile',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='assistant_messages',to='jobs.candidateprofile')),
        ],options={'ordering':['created_at']}),
    ]

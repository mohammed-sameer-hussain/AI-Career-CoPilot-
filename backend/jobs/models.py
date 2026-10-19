from django.db import models
from django.db.models import Q

class CandidateProfile(models.Model):
    name=models.CharField(max_length=200)
    email=models.EmailField(blank=True)
    password=models.CharField(max_length=255,blank=True,default='')
    target_roles=models.JSONField(default=list)
    preferred_locations=models.JSONField(default=list)
    skills=models.JSONField(default=list)
    summary=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

class Resume(models.Model):
    profile=models.ForeignKey(CandidateProfile,on_delete=models.CASCADE,related_name='resumes')
    file=models.FileField(upload_to='resumes/')
    extracted_text=models.TextField(blank=True)
    uploaded_at=models.DateTimeField(auto_now_add=True)

class Job(models.Model):
    external_id=models.CharField(max_length=300,unique=True)
    source=models.CharField(max_length=80)
    company=models.CharField(max_length=200)
    title=models.CharField(max_length=300)
    location=models.CharField(max_length=300,blank=True)
    url=models.URLField(max_length=1000)
    description=models.TextField()
    required_skills=models.JSONField(default=list)
    preferred_skills=models.JSONField(default=list)
    experience=models.CharField(max_length=100,blank=True)
    is_mnc=models.BooleanField(default=False)
    discovered_at=models.DateTimeField(auto_now_add=True)
    posted_at=models.DateTimeField(null=True,blank=True)

class JobMatch(models.Model):
    job=models.ForeignKey(Job,on_delete=models.CASCADE,related_name='matches')
    profile=models.ForeignKey(CandidateProfile,on_delete=models.CASCADE,related_name='job_matches')
    score=models.FloatField()
    hiring_probability=models.FloatField(default=0.0)
    semantic_similarity=models.FloatField(default=0.0)
    skill_match=models.FloatField()
    experience_match=models.FloatField()
    seniority_match=models.FloatField()
    preference_match=models.FloatField()
    matching_skills=models.JSONField(default=list)
    missing_skills=models.JSONField(default=list)
    skill_breakdown=models.JSONField(default=dict)
    hiring_factors=models.JSONField(default=dict)
    explanation=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now=True)
    class Meta:
        unique_together=('job','profile')

class Application(models.Model):
    STATUS=[('saved','Saved'),('interested','Interested'),('applied','Applied'),('assessment','Assessment'),('interview','Interview'),('offer','Offer'),('rejected','Rejected'),('withdrawn','Withdrawn')]
    job=models.ForeignKey(Job,on_delete=models.CASCADE,related_name='applications')
    profile=models.ForeignKey(CandidateProfile,on_delete=models.CASCADE,related_name='applications')
    status=models.CharField(max_length=30,choices=STATUS,default='saved')
    resume_suggestions=models.JSONField(default=list)
    cover_letter=models.TextField(blank=True)
    interview_questions=models.JSONField(default=list)
    interview_qa=models.JSONField(default=list)
    structured_output=models.JSONField(default=dict)
    notes=models.TextField(blank=True)
    applied_at=models.DateTimeField(null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)

class Notification(models.Model):
    profile=models.ForeignKey(CandidateProfile,on_delete=models.CASCADE,related_name='notifications')
    job=models.ForeignKey(Job,on_delete=models.CASCADE)
    title=models.CharField(max_length=300)
    message=models.TextField()
    read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

class AssistantMessage(models.Model):
    ROLE=[('user','User'),('assistant','Assistant')]
    profile=models.ForeignKey(CandidateProfile,on_delete=models.CASCADE,related_name='assistant_messages')
    job=models.ForeignKey(Job,on_delete=models.SET_NULL,null=True,blank=True)
    role=models.CharField(max_length=20,choices=ROLE)
    content=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['created_at']


class BackgroundTask(models.Model):
    """Durable, profile-scoped metadata for a Celery task."""
    STATUS = [('PENDING', 'Pending'), ('STARTED', 'Started'), ('RETRY', 'Retrying'),
              ('SUCCESS', 'Succeeded'), ('FAILURE', 'Failed')]
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='background_tasks')
    task_id = models.CharField(max_length=255, unique=True)
    kind = models.CharField(max_length=80)
    dedupe_key = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'kind', 'dedupe_key'],
                condition=Q(status__in=['PENDING', 'STARTED', 'RETRY']),
                name='unique_active_background_task',
            )
        ]

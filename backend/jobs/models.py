from django.db import models

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
    skill_match=models.FloatField()
    experience_match=models.FloatField()
    seniority_match=models.FloatField()
    preference_match=models.FloatField()
    matching_skills=models.JSONField(default=list)
    missing_skills=models.JSONField(default=list)
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

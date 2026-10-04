from django.contrib import admin
from .models import *
admin.site.register([CandidateProfile,Resume,Job,JobMatch,Application,Notification])

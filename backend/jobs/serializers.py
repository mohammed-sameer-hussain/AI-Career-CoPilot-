from rest_framework import serializers
from .models import CandidateProfile, Resume, Job, JobMatch, Application, Notification, AssistantMessage

class ProfileSerializer(serializers.ModelSerializer):
    class Meta: model=CandidateProfile; exclude=['password']
class ResumeSerializer(serializers.ModelSerializer):
    class Meta: model=Resume; fields='__all__'; read_only_fields=['extracted_text','uploaded_at']
class JobSerializer(serializers.ModelSerializer):
    match_score = serializers.SerializerMethodField()
    class Meta: model=Job; fields='__all__'
    def get_match_score(self, obj):
        matches_map = self.context.get('matches_map')
        if matches_map is not None:
            return matches_map.get(obj.id)
        request = self.context.get('request')
        profile = getattr(getattr(request, 'user', None), 'profile', None) if request else None
        if not profile:
            return None
        m = JobMatch.objects.filter(job=obj, profile=profile).only('score').first()
        return m.score if m else None
class MatchSerializer(serializers.ModelSerializer):
    class Meta: model=JobMatch; fields='__all__'
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta: model=Application; fields='__all__'
class NotificationSerializer(serializers.ModelSerializer):
    class Meta: model=Notification; fields='__all__'
class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta: model=AssistantMessage; fields=['id','role','content','job','created_at']

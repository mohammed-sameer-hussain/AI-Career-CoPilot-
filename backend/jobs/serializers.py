import zipfile
from pathlib import Path
from rest_framework import serializers
from .models import CandidateProfile, Resume, Job, JobMatch, Application, Notification, AssistantMessage

class ProfileSerializer(serializers.ModelSerializer):
    class Meta: model=CandidateProfile; exclude=['password']
class ResumeSerializer(serializers.ModelSerializer):
    class Meta: model=Resume; fields='__all__'; read_only_fields=['profile','extracted_text','uploaded_at']

    def validate_file(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('Resume must be 10 MB or smaller.')
        extension = Path(value.name).suffix.lower()
        if extension not in {'.pdf', '.docx', '.txt'}:
            raise serializers.ValidationError('Only PDF, DOCX, and TXT resumes are supported.')
        header = value.read(8)
        value.seek(0)
        if extension == '.pdf' and not header.startswith(b'%PDF-'):
            raise serializers.ValidationError('The uploaded file is not a valid PDF.')
        if extension == '.docx':
            try:
                with zipfile.ZipFile(value) as archive:
                    if ('[Content_Types].xml' not in archive.namelist()
                            or archive.testzip() is not None
                            or sum(item.file_size for item in archive.infolist()) > 20 * 1024 * 1024):
                        raise serializers.ValidationError('The uploaded DOCX file is invalid or corrupt.')
            except zipfile.BadZipFile:
                raise serializers.ValidationError('The uploaded file is not a valid DOCX.')
            finally:
                value.seek(0)
        return value
class JobSerializer(serializers.ModelSerializer):
    match_score = serializers.SerializerMethodField()
    hiring_probability = serializers.SerializerMethodField()
    class Meta: model=Job; fields='__all__'
    def get_match_score(self, obj):
        matches_map = self.context.get('matches_map')
        if matches_map is not None:
            val = matches_map.get(obj.id)
            return val.get('score') if isinstance(val, dict) else val
        request = self.context.get('request')
        profile = getattr(getattr(request, 'user', None), 'profile', None) if request else None
        if not profile:
            return None
        m = JobMatch.objects.filter(job=obj, profile=profile).only('score').first()
        return m.score if m else None

    def get_hiring_probability(self, obj):
        matches_map = self.context.get('matches_map')
        if matches_map is not None:
            val = matches_map.get(obj.id)
            return val.get('hiring_probability') if isinstance(val, dict) else None
        request = self.context.get('request')
        profile = getattr(getattr(request, 'user', None), 'profile', None) if request else None
        if not profile:
            return None
        m = JobMatch.objects.filter(job=obj, profile=profile).only('hiring_probability').first()
        return m.hiring_probability if m else None
class MatchSerializer(serializers.ModelSerializer):
    class Meta: model=JobMatch; fields='__all__'
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta: model=Application; fields='__all__'; read_only_fields=['profile']
class NotificationSerializer(serializers.ModelSerializer):
    class Meta: model=Notification; fields='__all__'; read_only_fields=['profile']
class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta: model=AssistantMessage; fields=['id','role','content','job','created_at']

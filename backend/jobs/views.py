from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Avg, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from pypdf import PdfReader
from docx import Document
from .auth import REFRESH_SALT, REFRESH_TTL, make_tokens, read_token
from .models import CandidateProfile, Resume, Job, JobMatch, Application, Notification
from .serializers import *
from .services import scan_jobs, match_job, application_for, match_all_jobs, get_skill_gap_plan
from .ai import assistant_reply
from .models import AssistantMessage

def extract_text(path):
    if path.name.lower().endswith('.pdf'):
        return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages)
    if path.name.lower().endswith('.docx'):
        return '\n'.join(p.text for p in Document(path).paragraphs)
    return path.read().decode('utf-8','ignore')

def current_profile(request):
    '''Return the CandidateProfile bound to the request token, or None.'''
    user=getattr(request,'user',None)
    return getattr(user,'profile',None) if user and user.is_authenticated else None

def auth_payload(profile):
    return {**make_tokens(profile),'profile':ProfileSerializer(profile).data}

class ProfileScopedViewSet(viewsets.ModelViewSet):
    '''Only expose rows owned by the authenticated profile.'''
    def get_queryset(self):
        profile=current_profile(self.request)
        qs=super().get_queryset()
        return qs.filter(profile=profile) if profile else qs.none()

class ProfileViewSet(ProfileScopedViewSet):
    queryset=CandidateProfile.objects.all(); serializer_class=ProfileSerializer
    def get_queryset(self):
        profile=current_profile(self.request)
        return CandidateProfile.objects.filter(pk=profile.pk) if profile else CandidateProfile.objects.none()

class ResumeViewSet(ProfileScopedViewSet):
    queryset=Resume.objects.all(); serializer_class=ResumeSerializer; parser_classes=[MultiPartParser,FormParser]
    def create(self,request,*args,**kwargs):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        f=request.FILES.get('file')
        if not f: return Response({'detail':'file is required'},status=400)
        resume=Resume.objects.create(profile=profile,file=f)
        resume.extracted_text=extract_text(resume.file)
        resume.save(update_fields=['extracted_text'])
        return Response(ResumeSerializer(resume).data,status=status.HTTP_201_CREATED)

class JobViewSet(viewsets.ModelViewSet):
    # MNCs are listed first, then the freshest discoveries.
    queryset=Job.objects.all().order_by('-is_mnc','-discovered_at'); serializer_class=JobSerializer
    def get_queryset(self):
        qs=Job.objects.all().order_by('-is_mnc','-discovered_at')
        params=self.request.query_params
        search=params.get('search')
        if search:
            qs=qs.filter(Q(title__icontains=search)|Q(company__icontains=search)|Q(description__icontains=search))
        for field in ('location','experience','source'):
            value=params.get(field)
            if value: qs=qs.filter(**{f'{field}__icontains':value})
        if str(params.get('mnc','')).lower()=='true': qs=qs.filter(is_mnc=True)
        company=params.get('company')
        if company: qs=qs.filter(company__icontains=company)
        level=(params.get('level') or '').lower()
        if level in ('fresher','mid','senior'):
            from .targeting import experience_level
            ids=[j.id for j in qs if experience_level(j.title, j.experience)==level]
            qs=qs.filter(pk__in=ids) if ids else qs.none()
        south=params.get('south')
        if str(south).lower() in ('true','1','yes'):
            from .targeting import is_south_india_location
            ids=[j.id for j in qs if is_south_india_location(j.location)]
            qs=qs.filter(pk__in=ids) if ids else qs.none()
        ordering=params.get('ordering')
        if ordering and ordering.lstrip('-') in ('discovered_at','posted_at'):
            qs=qs.order_by(ordering)
        # BUG FIX: never slice here - DRF pagination breaks on sliced querysets
        # ('Cannot filter a query once a slice has been taken'). Dashboard
        # limit= is handled in list() below as a plain array instead.
        return qs
    def list(self, request, *args, **kwargs):
        # limit= without page= -> plain array (dashboard/smoke pattern),
        # so slicing stays out of get_queryset and pagination never breaks.
        if request.query_params.get('limit') and not request.query_params.get('page'):
            qs=self.filter_queryset(self.get_queryset())
            try: n=max(1,min(100,int(request.query_params.get('limit'))))
            except (TypeError,ValueError): n=20
            return Response(JobSerializer(qs[:n],many=True).data)
        return super().list(request,*args,**kwargs)
    @action(detail=False,methods=['post'])
    def scan(self,request):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        try: jobs=scan_jobs(profile)
        except Exception as e: return Response({'detail':f'Job scan failed: {e}'},status=400)
        return Response({'count':len(jobs)})
    @action(detail=True,methods=['post'])
    def match(self,request,pk=None):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        try: match=match_job(profile,self.get_object())
        except ValueError as e: return Response({'detail':str(e)},status=400)
        return Response(MatchSerializer(match).data)
    @action(detail=True,methods=['post'])
    def application(self,request,pk=None):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        try: application=application_for(profile,self.get_object())
        except ValueError as e: return Response({'detail':str(e)},status=400)
        return Response(ApplicationSerializer(application).data)

    @action(detail=False,methods=['post'],url_path='match-all')
    def match_all(self,request):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        try:
            min_score = int(request.data.get('min_score', 0))
            matches = match_all_jobs(profile, min_score)
        except ValueError as e:
            return Response({'detail':str(e)},status=400)
        return Response({'matches': matches, 'count': len(matches)})

    @action(detail=True,methods=['post'],url_path='skill-gap-plan')
    def skill_gap_plan(self,request,pk=None):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        job=self.get_object()
        try:
            match = JobMatch.objects.get(job=job, profile=profile)
        except JobMatch.DoesNotExist:
            return Response({'detail': 'Run "Analyze Match" first.'}, status=400)
        plan = get_skill_gap_plan(match.missing_skills, match.matching_skills)
        return Response({'plan': plan, 'job_title': job.title, 'company': job.company})

class ApplicationViewSet(ProfileScopedViewSet):
    queryset=Application.objects.all().order_by('-updated_at'); serializer_class=ApplicationSerializer
    def get_queryset(self):
        qs=super().get_queryset()
        status_filter=self.request.query_params.get('status')
        if status_filter: qs=qs.filter(status=status_filter)
        return qs

class NotificationViewSet(ProfileScopedViewSet):
    queryset=Notification.objects.all().order_by('-created_at'); serializer_class=NotificationSerializer
    def get_queryset(self):
        qs=super().get_queryset()
        read=self.request.query_params.get('read')
        if read not in (None,''): qs=qs.filter(read=str(read).lower()=='true')
        return qs
    @action(detail=False,methods=['post'],url_path='mark-all-read')
    def mark_all_read(self,request):
        self.get_queryset().update(read=True)
        return Response({'status':'ok'})

class AssistantMessageViewSet(ProfileScopedViewSet):
    '''Chat with the career assistant. GET lists history, POST sends a message.'''
    queryset=AssistantMessage.objects.all(); serializer_class=AssistantMessageSerializer
    http_method_names=['get','post','delete']
    def get_queryset(self):
        profile=current_profile(self.request)
        qs=super().get_queryset()
        job_id=self.request.query_params.get('job')
        # 'job=abc' or 'job=[..]' must return empty, never 500 (b2err.log).
        if job_id not in (None,''):
            if isinstance(job_id,(list,tuple)): job_id=job_id[0] if job_id else None
            try: qs=qs.filter(job_id=int(str(job_id).strip().strip('[],')))
            except (TypeError,ValueError): qs=qs.none()
        return qs
    @action(detail=False,methods=['delete'],url_path='clear')
    def clear(self,request):
        deleted,_=AssistantMessage.objects.filter(profile=current_profile(self.request)).delete()
        return Response({'deleted':deleted,'status':'ok'})
    def create(self,request,*args,**kwargs):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        message=(request.data.get('message') or '').strip()
        if not message: return Response({'detail':'message is required'},status=400)
        job=None
        job_id=request.data.get('job')
        # Frontend can send job as [id] / 'undefined' / 'abc' (b2err.log 500s) - normalise.
        if isinstance(job_id,(list,tuple)): job_id=job_id[0] if job_id else None
        if isinstance(job_id,str):
            job_id=job_id.strip().strip('[],')
            if job_id.lower() in ('','none','null','undefined'): job_id=None
        if job_id not in (None,''):
            try: job=Job.objects.filter(pk=int(job_id)).first()
            except (TypeError,ValueError): job=None
        resume=profile.resumes.order_by('-uploaded_at').first()
        resume_text=resume.extracted_text if resume else ''
        recent=AssistantMessage.objects.filter(profile=profile).order_by('-created_at')[:10]
        history=list(AssistantMessageSerializer(list(reversed(recent)),many=True).data)
        try:
            reply=assistant_reply(profile,resume_text,job,message,history)
        except Exception as e:
            return Response({'detail':f'Assistant unavailable: {e}'},status=502)
        user_message=AssistantMessage.objects.create(profile=profile,job=job,role='user',content=message)
        assistant_message=AssistantMessage.objects.create(profile=profile,job=job,role='assistant',content=reply)
        return Response({'user_message':AssistantMessageSerializer(user_message).data,
                         'reply':AssistantMessageSerializer(assistant_message).data},status=201)

@api_view(['POST'])
def register(request):
    name=(request.data.get('name') or '').strip()
    email=(request.data.get('email') or '').strip().lower()
    password=request.data.get('password') or ''
    if not name or not email or len(password)<8:
        return Response({'detail':'Name, email and a password of at least 8 characters are required.'},status=400)
    if CandidateProfile.objects.filter(email__iexact=email).exists():
        return Response({'detail':'An account with this email already exists.'},status=400)
    profile=CandidateProfile.objects.create(
        name=name,email=email,password=make_password(password),
        target_roles=request.data.get('target_roles') or [],
        preferred_locations=request.data.get('preferred_locations') or [],
        skills=request.data.get('skills') or [],
        summary=request.data.get('summary') or '')
    return Response(auth_payload(profile),status=status.HTTP_201_CREATED)

@api_view(['POST'])
def login(request):
    email=(request.data.get('email') or '').strip().lower()
    password=request.data.get('password') or ''
    profile=CandidateProfile.objects.filter(email__iexact=email).first()
    if profile is None or not profile.password or not check_password(password,profile.password):
        return Response({'detail':'Invalid email or password.'},status=400)
    return Response(auth_payload(profile))

@api_view(['POST'])
def token_refresh(request):
    profile=read_token(request.data.get('refresh') or '',REFRESH_SALT,REFRESH_TTL)
    if profile is None:
        return Response({'detail':'Refresh token is invalid or expired.'},status=401)
    return Response(make_tokens(profile))

@api_view(['GET'])
def dashboard(request):
    profile=current_profile(request)
    matches=JobMatch.objects.filter(profile=profile) if profile else JobMatch.objects.none()
    applications=Application.objects.filter(profile=profile) if profile else Application.objects.none()
    notifications=Notification.objects.filter(profile=profile) if profile else Notification.objects.none()
    average=matches.aggregate(avg=Avg('score'))['avg']
    return Response({
        'jobs':Job.objects.count(),
        'applications':applications.count(),
        'notifications':notifications.filter(read=False).count(),
        'profiles':CandidateProfile.objects.count(),
        'match_rate':round(average) if average else 0,
    })

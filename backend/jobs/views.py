from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Avg, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from pypdf import PdfReader
from docx import Document
from .auth import AuthRateThrottle, make_tokens, read_token
from .models import CandidateProfile, Resume, Job, JobMatch, Application, Notification
from .serializers import *
from .services import scan_jobs, match_job, application_for, match_all_jobs, get_skill_gap_plan
from .ai import assistant_reply
from .models import AssistantMessage
from .models import BackgroundTask
from .tasks import (assistant_task, application_task, match_all_jobs_task, match_job_task,
                    parse_resume_task, scan_jobs_task, submit_task, task_payload)

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
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(profile=current_profile(self.request))

class ProfileViewSet(ProfileScopedViewSet):
    queryset=CandidateProfile.objects.all(); serializer_class=ProfileSerializer
    http_method_names=['get','patch','put','head','options']
    def get_queryset(self):
        profile=current_profile(self.request)
        return CandidateProfile.objects.filter(pk=profile.pk) if profile else CandidateProfile.objects.none()

class ResumeViewSet(ProfileScopedViewSet):
    queryset=Resume.objects.all().order_by('-uploaded_at', '-pk'); serializer_class=ResumeSerializer; parser_classes=[MultiPartParser,FormParser]
    def create(self,request,*args,**kwargs):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        f=request.FILES.get('file')
        if not f: return Response({'detail':'file is required'},status=400)
        serializer = ResumeSerializer(data={'file': f})
        serializer.is_valid(raise_exception=True)
        resume=Resume.objects.create(profile=profile,file=serializer.validated_data['file'])
        if str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            task, _ = submit_task(profile, 'resume_parse', f'resume:{resume.id}:{resume.uploaded_at.isoformat()}', (resume.id,))
            return Response({**ResumeSerializer(resume).data, 'task_id': task.task_id,
                             'task_status_url': f'/api/tasks/{task.task_id}/'}, status=status.HTTP_202_ACCEPTED)
        try:
            resume.extracted_text=extract_text(resume.file)
        except Exception:
            resume.file.delete(save=False)
            resume.delete()
            return Response({'detail':'The uploaded resume could not be parsed.'}, status=400)
        resume.save(update_fields=['extracted_text'])
        return Response(ResumeSerializer(resume).data,status=status.HTTP_201_CREATED)

class JobViewSet(viewsets.ModelViewSet):
    # MNCs are listed first, then the freshest discoveries.
    queryset=Job.objects.all().order_by('-is_mnc','-discovered_at'); serializer_class=JobSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
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
        profile = current_profile(request)
        matches_map = {}
        if profile:
            matches_qs = JobMatch.objects.filter(profile=profile).values('job_id', 'score', 'hiring_probability')
            matches_map = {m['job_id']: {'score': m['score'], 'hiring_probability': m['hiring_probability']} for m in matches_qs}
        if request.query_params.get('limit') and not request.query_params.get('page'):
            qs=self.filter_queryset(self.get_queryset())
            try: n=max(1,min(100,int(request.query_params.get('limit'))))
            except (TypeError,ValueError): n=20
            return Response(JobSerializer(qs[:n],many=True,context={'matches_map':matches_map,'request':request}).data)
        response = super().list(request,*args,**kwargs)
        if profile and isinstance(response.data, dict) and 'results' in response.data:
            for item in response.data['results']:
                match_info = matches_map.get(item.get('id'))
                if match_info:
                    item['match_score'] = match_info.get('score')
                    item['hiring_probability'] = match_info.get('hiring_probability')
        return response
    @action(detail=False,methods=['post'])
    def scan(self,request):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        if str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            record, created = submit_task(profile, 'job_scan', 'profile-scan', (profile.id,))
            return Response({**task_payload(record), 'deduplicated': not created}, status=status.HTTP_202_ACCEPTED)
        try: jobs=scan_jobs(profile)
        except Exception as e: return Response({'detail':f'Job scan failed: {e}'},status=400)
        return Response({'count':len(jobs)})
    @action(detail=True,methods=['get','post'])
    def match(self,request,pk=None):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        job=self.get_object()
        if request.method.lower() == 'post' and str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            resume = profile.resumes.order_by('-uploaded_at').first()
            if not resume: return Response({'detail': 'Upload a resume first.'}, status=400)
            record, created = submit_task(profile, 'job_match', f'job:{job.id}:resume:{resume.id}:{resume.uploaded_at.isoformat()}', (profile.id, job.id))
            return Response({**task_payload(record), 'deduplicated': not created}, status=status.HTTP_202_ACCEPTED)
        existing=JobMatch.objects.filter(job=job,profile=profile).first()
        if request.method.lower()=='get' and existing:
            return Response(MatchSerializer(existing).data)
        try: match=match_job(profile,job)
        except ValueError as e:
            if request.method.lower()=='get' and not existing:
                return Response({'detail':str(e),'no_resume':True},status=404)
            return Response({'detail':str(e)},status=400)
        return Response(MatchSerializer(match).data)
    @action(detail=True,methods=['post'])
    def application(self,request,pk=None):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        if str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            job = self.get_object()
            if not profile.resumes.exists(): return Response({'detail': 'Upload a resume first.'}, status=400)
            record, created = submit_task(profile, 'application', f'application:job:{job.id}', (profile.id, job.id))
            return Response({**task_payload(record), 'deduplicated': not created}, status=status.HTTP_202_ACCEPTED)
        try: application=application_for(profile,self.get_object())
        except ValueError as e: return Response({'detail':str(e)},status=400)
        return Response(ApplicationSerializer(application).data)

    @action(detail=False,methods=['post'],url_path='match-all')
    def match_all(self,request):
        profile=current_profile(request)
        if profile is None: return Response({'detail':'Authentication is required.'},status=401)
        if str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            minimum = int(request.data.get('min_score', 0))
            resume = profile.resumes.order_by('-uploaded_at').first()
            if not resume: return Response({'detail': 'Upload a resume first.'}, status=400)
            record, created = submit_task(profile, 'match_all', f'all:{minimum}:resume:{resume.id}:{resume.uploaded_at.isoformat()}', (profile.id, minimum))
            return Response({**task_payload(record), 'deduplicated': not created}, status=status.HTTP_202_ACCEPTED)
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
        if str(request.data.get('async', '')).lower() in ('1', 'true', 'yes'):
            job_id = request.data.get('job') or None
            if isinstance(job_id, (list, tuple)): job_id = job_id[0] if job_id else None
            if isinstance(job_id, str):
                job_id = job_id.strip().strip('[],')
                if job_id.lower() in ('', 'none', 'null', 'undefined'): job_id = None
            if job_id is not None:
                try: job_id = int(job_id)
                except (TypeError, ValueError): job_id = None
            record, created = submit_task(profile, 'assistant', f'assistant:{job_id}:{message}', (profile.id, message, job_id))
            return Response({**task_payload(record), 'deduplicated': not created}, status=status.HTTP_202_ACCEPTED)
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
@throttle_classes([AuthRateThrottle])
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
@throttle_classes([AuthRateThrottle])
def login(request):
    email=(request.data.get('email') or '').strip().lower()
    password=request.data.get('password') or ''
    profile=CandidateProfile.objects.filter(email__iexact=email).first()
    if profile is None or not profile.password or not check_password(password,profile.password):
        return Response({'detail':'Invalid email or password.'},status=400)
    return Response(auth_payload(profile))

@api_view(['POST'])
@throttle_classes([AuthRateThrottle])
def token_refresh(request):
    profile=read_token(request.data.get('refresh') or '', 'refresh')
    if profile is None:
        return Response({'detail':'Refresh token is invalid or expired.'},status=401)
    return Response(make_tokens(profile))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_background_task(request):
    """Queue a profile-scoped background operation and return its task ID."""
    profile = current_profile(request)
    kind = request.data.get('kind')
    if profile is None:
        return Response({'detail': 'Authentication is required.'}, status=401)
    try:
        if kind == 'resume_parse':
            resume = profile.resumes.get(pk=request.data.get('resume_id'))
            key, args = f'resume:{resume.id}:{resume.uploaded_at.isoformat()}', (resume.id,)
        elif kind == 'job_scan':
            # One active scan per profile; completed scans can be requested again.
            key, args = 'profile-scan', (profile.id,)
        elif kind == 'job_match':
            job = Job.objects.get(pk=request.data.get('job_id'))
            resume = profile.resumes.order_by('-uploaded_at').first()
            if not resume:
                return Response({'detail': 'Upload a resume first.'}, status=400)
            key, args = f'job:{job.id}:resume:{resume.id}:{resume.uploaded_at.isoformat()}', (profile.id, job.id)
        elif kind == 'match_all':
            minimum = int(request.data.get('min_score', 0))
            resume = profile.resumes.order_by('-uploaded_at').first()
            if not resume:
                return Response({'detail': 'Upload a resume first.'}, status=400)
            key, args = f'all:{minimum}:resume:{resume.id}:{resume.uploaded_at.isoformat()}', (profile.id, minimum)
        elif kind == 'application':
            job = Job.objects.get(pk=request.data.get('job_id'))
            key, args = f'application:job:{job.id}', (profile.id, job.id)
        elif kind == 'assistant':
            message = (request.data.get('message') or '').strip()
            if not message:
                return Response({'detail': 'message is required'}, status=400)
            job_id = request.data.get('job_id') or None
            key, args = f'assistant:{job_id}:{message}', (profile.id, message, job_id)
        else:
            return Response({'detail': 'Unsupported task kind.'}, status=400)
    except (TypeError, ValueError, Resume.DoesNotExist, Job.DoesNotExist):
        return Response({'detail': 'The requested resource or task parameters are invalid.'}, status=400)

    try:
        record, created = submit_task(profile, kind, key, args)
    except Exception as exc:
        return Response({'detail': f'Could not queue task: {exc}'}, status=503)
    payload = task_payload(record)
    payload['deduplicated'] = not created
    return Response(payload, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def background_task_status(request, task_id):
    profile = current_profile(request)
    try:
        record = BackgroundTask.objects.get(task_id=task_id, profile=profile)
    except BackgroundTask.DoesNotExist:
        return Response({'detail': 'Task not found.'}, status=404)
    return Response(task_payload(record))

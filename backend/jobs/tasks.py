import uuid

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import IntegrityError, transaction
from django.utils import timezone
from docx import Document
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pypdf import PdfReader

from .ai import assistant_reply
from .models import (Application, AssistantMessage, BackgroundTask, CandidateProfile,
                     Job, Resume)
from .serializers import ApplicationSerializer, AssistantMessageSerializer
from .services import application_for, match_all_jobs, match_job, scan_jobs


class TemporaryTaskError(Exception):
    """Raised for failures that are safe to retry."""


def _serialize(value):
    if isinstance(value, dict):
        return value
    return {'value': value}


def _mark(task_id, **values):
    BackgroundTask.objects.filter(task_id=task_id).update(**values, updated_at=timezone.now())


def _run(task, kind, callback):
    record = BackgroundTask.objects.get(task_id=task.request.id)
    if record.status == 'SUCCESS':
        return record.result
    _mark(record.task_id, status='STARTED', error='')
    try:
        result = _serialize(callback())
    except (ConnectionError, TimeoutError, TemporaryTaskError,
            APIConnectionError, APITimeoutError, RateLimitError) as exc:
        _mark(record.task_id, status='RETRY', error=str(exc))
        try:
            raise task.retry(exc=exc, countdown=2 ** task.request.retries * 10)
        except MaxRetriesExceededError:
            _mark(record.task_id, status='FAILURE', error=str(exc), completed_at=timezone.now())
            raise
    except Exception as exc:
        _mark(record.task_id, status='FAILURE', error=str(exc), completed_at=timezone.now())
        raise
    _mark(record.task_id, status='SUCCESS', result=result, completed_at=timezone.now())
    return result


def _extract(resume):
    path = resume.file
    if path.name.lower().endswith('.pdf'):
        return '\n'.join((page.extract_text() or '') for page in PdfReader(path).pages)
    if path.name.lower().endswith('.docx'):
        return '\n'.join(paragraph.text for paragraph in Document(path).paragraphs)
    return path.read().decode('utf-8', 'ignore')


@shared_task(bind=True, max_retries=3, acks_late=True)
def parse_resume_task(self, resume_id):
    return _run(self, 'resume_parse', lambda: _parse_resume(resume_id))


def _parse_resume(resume_id):
    resume = Resume.objects.get(pk=resume_id)
    resume.extracted_text = _extract(resume)
    resume.save(update_fields=['extracted_text'])
    return {'resume_id': resume.id, 'extracted_text_length': len(resume.extracted_text)}


@shared_task(bind=True, max_retries=3, acks_late=True)
def scan_jobs_task(self, profile_id):
    return _run(self, 'job_scan', lambda: {'count': len(scan_jobs(CandidateProfile.objects.get(pk=profile_id)))})


@shared_task(bind=True, max_retries=3, acks_late=True)
def match_job_task(self, profile_id, job_id):
    return _run(self, 'job_match', lambda: _match(profile_id, job_id))


def _match(profile_id, job_id):
    return {'match_id': match_job(CandidateProfile.objects.get(pk=profile_id), Job.objects.get(pk=job_id)).id}


@shared_task(bind=True, max_retries=3, acks_late=True)
def match_all_jobs_task(self, profile_id, min_score=0):
    return _run(self, 'match_all', lambda: {'matches': match_all_jobs(CandidateProfile.objects.get(pk=profile_id), min_score)})


@shared_task(bind=True, max_retries=3, acks_late=True)
def application_task(self, profile_id, job_id):
    return _run(self, 'application', lambda: ApplicationSerializer(application_for(CandidateProfile.objects.get(pk=profile_id), Job.objects.get(pk=job_id))).data)


@shared_task(bind=True, max_retries=3, acks_late=True)
def assistant_task(self, profile_id, message, job_id=None):
    return _run(self, 'assistant', lambda: _assistant(profile_id, message, job_id))


def _assistant(profile_id, message, job_id):
    profile = CandidateProfile.objects.get(pk=profile_id)
    job = Job.objects.filter(pk=job_id).first() if job_id else None
    resume = profile.resumes.order_by('-uploaded_at').first()
    recent = AssistantMessage.objects.filter(profile=profile).order_by('-created_at')[:10]
    history = list(reversed(AssistantMessageSerializer(recent, many=True).data))
    reply = assistant_reply(profile, resume.extracted_text if resume else '', job, message, history)
    user_message = AssistantMessage.objects.create(profile=profile, job=job, role='user', content=message)
    assistant_message = AssistantMessage.objects.create(profile=profile, job=job, role='assistant', content=reply)
    return {'user_message': AssistantMessageSerializer(user_message).data, 'reply': AssistantMessageSerializer(assistant_message).data}


TASKS = {
    'resume_parse': parse_resume_task,
    'job_scan': scan_jobs_task,
    'job_match': match_job_task,
    'match_all': match_all_jobs_task,
    'application': application_task,
    'assistant': assistant_task,
}


def submit_task(profile, kind, dedupe_key, task_args):
    """Create one active task per profile/kind/key, then enqueue it after commit."""
    task_id = str(uuid.uuid4())
    try:
        with transaction.atomic():
            existing = BackgroundTask.objects.filter(profile=profile, kind=kind, dedupe_key=dedupe_key,
                                                      status__in=['PENDING', 'STARTED', 'RETRY']).first()
            if existing:
                return existing, False
            record = BackgroundTask.objects.create(profile=profile, task_id=task_id, kind=kind, dedupe_key=dedupe_key)
            transaction.on_commit(lambda: TASKS[kind].apply_async(args=task_args, task_id=record.task_id))
            return record, True
    except IntegrityError:
        return BackgroundTask.objects.get(profile=profile, kind=kind, dedupe_key=dedupe_key,
                                          status__in=['PENDING', 'STARTED', 'RETRY']), False


def task_payload(record):
    return {'task_id': record.task_id, 'kind': record.kind, 'status': record.status,
            'result': record.result, 'error': record.error or None,
            'created_at': record.created_at, 'updated_at': record.updated_at,
            'completed_at': record.completed_at}

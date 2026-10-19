from django.utils import timezone
from .models import Job, JobMatch, Notification, Application
from .sources import configured_sources
from .targeting import passes_target_policy, is_mnc_company
from .ai import analyze, generate_application
from .serializers import JobSerializer

def scan_jobs(profile=None):
    '''Pull every configured source. One failing source must not sink the scan,
    and only targeted rows (IT + India + fresher) are stored, with MNCs flagged.'''
    created=[]; errors=[]
    has_resume=bool(profile and profile.resumes.exists())
    for source in configured_sources():
        try: raw_jobs=source.fetch()
        except Exception as e:
            errors.append(f'{source.name}: {e}'); continue
        for raw in raw_jobs:
            if not passes_target_policy(raw): continue
            raw['is_mnc']=is_mnc_company(raw.get('company',''))
            job,_=Job.objects.update_or_create(external_id=raw['external_id'],defaults=raw)
            created.append(job)
            if has_resume:
                match_job(profile,job)
    if not created and errors:
        raise ValueError(' | '.join(errors))
    return created

from .matching_engine import calculate_intelligent_match

def match_job(profile,job):
    resume=profile.resumes.order_by('-uploaded_at').first()
    if not resume: raise ValueError('Upload a resume first.')
    data=calculate_intelligent_match(resume.extracted_text,job,profile)
    score=data['score']
    match,_=JobMatch.objects.update_or_create(
        job=job,
        profile=profile,
        defaults={
            'score': score,
            'hiring_probability': data.get('hiring_probability', 0.0),
            'semantic_similarity': data.get('semantic_similarity', 0.0),
            'skill_match': data.get('skill_match', 0.0),
            'experience_match': data.get('experience_match', 0.0),
            'seniority_match': data.get('seniority_match', 0.0),
            'preference_match': data.get('preference_match', 0.0),
            'matching_skills': data.get('matching_skills', []),
            'missing_skills': data.get('missing_skills', []),
            'skill_breakdown': data.get('skill_breakdown', {}),
            'hiring_factors': data.get('hiring_factors', {}),
            'explanation': data.get('explanation', ''),
        }
    )
    if score>=70:
        Notification.objects.get_or_create(
            profile=profile,
            job=job,
            defaults={
                'title':f'{job.title} at {job.company}',
                'message':f'Match score: {score}% (Hire Odds: {data.get("hiring_probability", 0)}%). Matching skills: {", ".join(data.get("matching_skills", []))}'
            }
        )
    return match

def application_for(profile,job):
    resume=profile.resumes.order_by('-uploaded_at').first()
    if not resume: raise ValueError('Upload a resume first.')
    data=generate_application(resume.extracted_text,job)
    app,_=Application.objects.update_or_create(job=job,profile=profile,defaults=data)
    return app


def match_all_jobs(profile, min_score=0):
    '''Match resume against all jobs and return sorted matches.'''
    resume=profile.resumes.order_by('-uploaded_at').first()
    if not resume: raise ValueError('Upload a resume first.')
    jobs=Job.objects.all()
    matches=[]
    for job in jobs:
        try:
            m = match_job(profile, job)
            if m.score >= min_score:
                matches.append({
                    'job': JobSerializer(job).data,
                    'score': m.score,
                    'hiring_probability': m.hiring_probability,
                    'semantic_similarity': m.semantic_similarity,
                    'skill_match': m.skill_match,
                    'experience_match': m.experience_match,
                    'seniority_match': m.seniority_match,
                    'preference_match': m.preference_match,
                    'matching_skills': m.matching_skills,
                    'missing_skills': m.missing_skills,
                    'skill_breakdown': m.skill_breakdown,
                    'hiring_factors': m.hiring_factors,
                    'explanation': m.explanation,
                })
        except Exception:
            pass
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches


def get_skill_gap_plan(missing_skills, matching_skills):
    '''Generate a learning plan for missing skills with resources.'''
    plan = []
    for skill in missing_skills:
        plan.append({
            'skill': skill,
            'priority': 'high' if skill in matching_skills else 'medium',
            'suggested_actions': [
                f'Complete a hands-on project using {skill}',
                f'Take an online course on {skill} (Coursera, Udemy, freeCodeCamp)',
                f'Build a portfolio piece demonstrating {skill}',
                f'Contribute to an open-source project using {skill}',
            ],
            'estimated_time': '2-4 weeks',
            'resources': [
                f'https://www.coursera.org/search?query={skill.replace(" ", "%20")}',
                f'https://www.udemy.com/courses/search/?q={skill.replace(" ", "%20")}',
                f'https://www.freecodecamp.org/news/search/?query={skill.replace(" ", "%20")}',
                f'https://github.com/topics/{skill.replace(" ", "-").lower()}',
            ],
        })
    return plan

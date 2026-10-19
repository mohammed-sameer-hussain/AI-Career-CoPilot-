import json, os, re
from openai import OpenAI

SYSTEM = '''You are a careful career assistant. Ground every claim in the supplied resume and job description. Never invent experience, skills, certifications, projects, metrics, or employment. Return valid JSON only when JSON is requested.'''

def client():
    key=os.getenv('OPENAI_API_KEY')
    if not key: return None
    kwargs={'api_key':key}
    if os.getenv('OPENAI_BASE_URL'): kwargs['base_url']=os.getenv('OPENAI_BASE_URL')
    return OpenAI(**kwargs)

def model_name():
    return os.getenv('OPENAI_MODEL','gpt-4o-mini')

def _json_call(prompt, temperature=0.2):
    '''Call the LLM and parse a JSON response, or return None when unavailable/invalid.'''
    c=client()
    if not c: return None
    r=c.chat.completions.create(model=model_name(),messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],temperature=temperature)
    content=(r.choices[0].message.content or '').strip()
    if content.startswith('```'):
        content=content.strip('`')
        content=content.split('\n',1)[1] if '\n' in content else content
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None

def analyze(resume_text, job, profile=None):
    from .matching_engine import calculate_intelligent_match
    return calculate_intelligent_match(resume_text, job, profile)

def generate_application(resume_text, job):
    data=_json_call(f'''Resume:\n{resume_text[:12000]}\n\nJob description:\n{job.description[:12000]}\n\nReturn JSON only with this exact shape:\n{{
  "resume_suggestions": [{{"text": "editable suggestion", "evidence": ["exact phrase from resume or job"]}}],
  "cover_letter": {{"text": "editable cover letter", "evidence": ["exact phrase from resume or job"]}},
  "interview_qa": [{{"question": "question", "answer": "safe model answer", "evidence": ["exact phrase from resume or job"]}}],
  "unsupported_claims": []
}}\n\nEvery evidence item must be copied exactly from the supplied resume or job. If a fact is not present, say the candidate should add their own example instead of inventing one. Never claim an unlisted skill, employer, title, certification, project, metric, date, or achievement.''', 0.2)
    normalized=_normalize_application(data, resume_text, job)
    return normalized if normalized else fallback_application(resume_text, job)


def _contains_evidence(phrase, resume_text, job):
    phrase=(str(phrase or '').strip()).lower()
    if not phrase: return False
    job_text=' '.join(str(getattr(job, field, '') or '') for field in ('title','company','location','experience','description'))
    return phrase in (resume_text or '').lower() or phrase in job_text.lower()


def _normalize_application(data, resume_text, job):
    """Validate structured model output before it can become an application draft."""
    if not isinstance(data, dict) or data.get('unsupported_claims'):
        return None
    suggestions=[]
    for item in data.get('resume_suggestions') or []:
        if not isinstance(item, dict) or not item.get('text') or not all(_contains_evidence(e, resume_text, job) for e in item.get('evidence') or []):
            return None
        suggestions.append(str(item['text']).strip())
    letter=data.get('cover_letter') or {}
    if not isinstance(letter, dict) or not letter.get('text') or not all(_contains_evidence(e, resume_text, job) for e in letter.get('evidence') or []):
        return None
    qa=[]
    for item in data.get('interview_qa') or []:
        if not isinstance(item, dict) or not item.get('question') or not item.get('answer'):
            return None
        evidence=item.get('evidence') or []
        if not all(_contains_evidence(e, resume_text, job) for e in evidence):
            return None
        qa.append({'question': str(item['question']).strip(), 'answer': str(item['answer']).strip(), 'evidence': evidence})
    if not suggestions or not qa:
        return None
    structured={
        'resume_suggestions':[{'text': text, 'editable': True} for text in suggestions],
        'cover_letter':{'text': str(letter['text']).strip(), 'editable': True},
        'interview_qa':[dict(item, editable=True) for item in qa],
        'grounding':{'unsupported_claims': [], 'validated': True},
    }
    return {'resume_suggestions': suggestions, 'cover_letter': str(letter['text']).strip(),
            'interview_qa': qa, 'interview_questions':[item['question'] for item in qa],
            'structured_output': structured}

def fallback_application(resume_text, job):
    qa=fallback_interview_qa(resume_text, job)
    suggestions=fallback_resume_tips(resume_text, job)
    structured={
        'resume_suggestions':[{'text': text, 'editable': True} for text in suggestions],
        'cover_letter':{'text': fallback_cover_letter(resume_text, job), 'editable': True},
        'interview_qa':[dict(item, evidence=[], editable=True) for item in qa],
        'grounding':{'unsupported_claims': [], 'validated': True, 'mode': 'deterministic'},
    }
    return {
        'resume_suggestions':suggestions,
        'cover_letter':fallback_cover_letter(resume_text, job),
        'interview_qa':qa,
        'interview_questions':[q['question'] for q in qa],
        'structured_output': structured,
    }
def _resume_skills(resume_text, job):
    '''Return (skills found in the resume, skills from the posting not found).'''
    text=(resume_text or '').lower()
    pool=list(dict.fromkeys([*(job.required_skills or []),*(job.preferred_skills or [])]))
    def present_in_resume(skill):
        if not skill: return False
        pattern=r'(?<![\w+#.])'+re.escape(skill.lower())+r'(?![\w+#.])'
        return bool(re.search(pattern, text))
    present=[s for s in pool if present_in_resume(s)]
    missing=[s for s in (job.required_skills or []) if s and not present_in_resume(s)]
    return present, missing

def _resume_years(resume_text):
    found=re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs|year)', (resume_text or '').lower())
    return max((float(x) for x in found), default=None)

def _job_years(experience):
    nums=re.findall(r'\d+', experience or '')
    return [int(n) for n in nums]

SENIORITY_LEVELS=[('intern',1),('junior',2),('entry',2),('mid',3),('associate',3),('senior',4),('lead',5),('staff',5),('principal',6),('manager',5),('architect',6)]

def _seniority(text):
    found=[level for word,level in SENIORITY_LEVELS if word in (text or '').lower()]
    return max(found) if found else 3

def fallback_match(resume_text, job, profile=None):
    '''Intelligent NLP and semantic IR matching engine.'''
    from .matching_engine import calculate_intelligent_match
    return calculate_intelligent_match(resume_text, job, profile)

def fallback_resume_tips(resume_text, job):
    present, missing = _resume_skills(resume_text, job)
    tips=[
        f"Lead your summary with the skills this posting asks for that you actually have: {', '.join(present[:6]) or 'your strongest matched skills'}.",
        "Add measurable outcomes (%, time saved, users, requests/sec) to your top three bullets - use numbers you can defend.",
        f"Mirror the posting's exact keywords where they are truthful for you: {', '.join((job.required_skills or [])[:5])}.",
    ]
    if missing:
        tips.append(f"Only claim what you can evidence. For not-yet-used skills ({', '.join(missing[:4])}), add a small project or course so you can speak to them honestly.")
    else:
        tips.append("You cover every required skill - rank them so the most job-relevant ones appear first.")
    return tips

def fallback_cover_letter(resume_text, job):
    present, missing = _resume_skills(resume_text, job)
    skills=', '.join(present[:5]) or 'the skills detailed in my attached resume'
    required=', '.join((job.required_skills or [])[:5])
    parts=['Dear Hiring Team,']
    parts.append(f"I am applying for the {job.title} role at {job.company}. My resume shows hands-on experience with {skills}, which maps directly onto the requirements in your posting.")
    if required:
        parts.append(f"Your listing calls for {required}. Rather than repeat my CV, I would point to the specific resume entries where I used these in practice: {skills}.")
    if missing:
        parts.append(f"I am actively strengthening {', '.join(missing[:3])} and can talk through how I am doing that.")
    parts.append("I would welcome the opportunity to discuss how my background fits the problems your team is solving.")
    parts.append("Sincerely,\n[Your Name]")
    return '\n\n'.join(parts)
def fallback_interview_qa(resume_text, job):
    '''Interview questions with resume-grounded model answers (no invented facts).'''
    present, missing = _resume_skills(resume_text, job)
    req=list(job.required_skills or [])
    anchors=present or req
    def skill(i):
        if i < len(anchors): return anchors[i]
        if i < len(req): return req[i]
        return 'the core stack in this posting'
    top_skills=', '.join(req[:4]) or 'the required skills'
    gap_text=', '.join(missing[:3]) or 'areas you have not used in production yet'
    return [
        {'question':'Walk me through your experience with '+skill(0)+'.',
         'answer':'Pick the single strongest project on your resume that used '+skill(0)+'. In 60-90 seconds cover the problem, your specific contribution, the tools involved and the measurable result. Use only figures already written on your resume.'},
        {'question':'How have you used '+skill(1)+' in a real project?',
         'answer':'Name the project, state what you built with '+skill(1)+', and explain one technical decision you made and why. Point the interviewer to the matching resume bullet.'},
        {'question':'Describe a challenging bug or production issue you solved.',
         'answer':'Use STAR (Situation, Task, Action, Result). Explain how you diagnosed it, what you changed and how you verified the fix. Keep the result concrete and truthful.'},
        {'question':'How would you design a system that uses '+skill(0)+' together with a database?',
         'answer':'Start from requirements, sketch the data model and API surface, then discuss trade-offs such as consistency, caching and scaling. Reference the architecture you actually used on a resume project so the answer stays grounded.'},
        {'question':'Which of our required skills ('+top_skills+') are you strongest in, and which are you still learning?',
         'answer':'Be specific and honest. Name your strongest areas from your resume first, then name the gaps ('+gap_text+') and describe the concrete step you are taking to close them.'},
        {'question':'Tell me about a time you disagreed with a teammate or reviewer.',
         'answer':'Describe the situation, how you separated the technical argument from the person, the evidence you brought and the outcome. Show collaboration rather than conflict.'},
        {'question':'Why this '+job.title+' role and why '+job.company+'?',
         'answer':'Connect the responsibilities in the posting to specific evidence on your resume, then explain what you want to learn next. Tie it to what the posting says the team is building.'},
        {'question':'Where do you want to grow over the next year?',
         'answer':'Name one technical skill you want to deepen and one piece of ownership you want to take on, and link both to the direction of this role.'},
    ]
def assistant_reply(profile, resume_text, job, message, history=None):
    '''Answer a career question. Uses the LLM when configured, else the deterministic coach.'''
    c=client()
    if not c:
        return fallback_assistant(profile, resume_text, job, message)
    context=[]
    if profile:
        context.append(f"Candidate name: {profile.name}\nTarget roles: {profile.target_roles}\nPreferred locations: {profile.preferred_locations}\nProfile skills: {profile.skills}")
    if resume_text: context.append(f"Resume text:\n{resume_text[:8000]}")
    if job: context.append(f"Selected job: {job.title} at {job.company}\nLocation: {job.location}\nExperience: {job.experience}\nRequired skills: {job.required_skills}\nDescription:\n{job.description[:6000]}")
    msgs=[{'role':'system','content':SYSTEM+' You are also a friendly career coach. Give practical, specific advice grounded ONLY in the supplied resume and job. Never invent experience, skills, metrics or employers. Use short paragraphs and bullet points. When asked about skill gaps, provide a concrete learning plan with resources.'}]
    if context: msgs.append({'role':'system','content':'CONTEXT\n'+'\n\n'.join(context)})
    for m in (history or [])[-10:]:
        msgs.append({'role':m.get('role','user'),'content':m.get('content','')})
    msgs.append({'role':'user','content':message})
    r=c.chat.completions.create(model=model_name(),messages=msgs,temperature=0.4)
    return (r.choices[0].message.content or '').strip()

def fallback_assistant(profile, resume_text, job, message):
    '''Deterministic career coach used when no LLM key is configured.'''
    text=(message or '').lower()
    name=(profile.name.split(' ')[0] if profile and profile.name else 'there')
    if not (resume_text or '').strip() and any(k in text for k in ('match','job','cover','interview','skill','resume','recommend','gap','missing','learn','fix','improve')):
        return ("I don't have a resume on your profile yet. Upload one on the Profile page and I will match you "
                "against every opening, draft cover letters and prepare interview answers for you.")
    if job and any(k in text for k in ('cover letter','cover-letter','application letter','write a letter','letter')):
        return f"Here is a cover letter draft for {job.title} at {job.company}:\n\n{fallback_cover_letter(resume_text, job)}"
    if job and any(k in text for k in ('interview','question','q&a','qa','expected question','prepare')):
        qa=fallback_interview_qa(resume_text, job)
        lines=[f"Interview preparation for {job.title} at {job.company} - questions with model answers:\n"]
        for i,item in enumerate(qa, 1):
            lines.append(f"{i}. {item['question']}\n     {item['answer']}")
        return '\n'.join(lines)
    if any(k in text for k in ('gap','missing','lack','weak','should i learn','fix','improve','close')):
        if job:
            data=fallback_match(resume_text, job, profile)
            gaps=', '.join(data['missing_skills']) or 'none detected in your resume'
            plan_lines = []
            for skill in data['missing_skills'][:5]:
                plan_lines.append(f"  • {skill}: Build a small project, take a course (Coursera/Udemy/freeCodeCamp), add to portfolio")
            plan_text = '\n'.join(plan_lines) if plan_lines else 'No critical gaps to fix.'
            return (f"Skill gaps for {job.title} at {job.company}: {gaps}.\n\n"
                    "How to close them:\n"
                    f"{plan_text}\n\n"
                    "Pick the two highest-value gaps, ship one small project or course for each, "
                    "and rewrite the matching resume bullet once you can talk about it honestly.")
        return "Open a specific job and ask me again, and I will list exactly what is missing for that role and how to fix it."
    if any(k in text for k in ('match','fit','score','good for','suitable','worth applying')):
        if job:
            d=fallback_match(resume_text, job, profile)
            total=round(d['skill_match']*.4+d['experience_match']*.3+d['seniority_match']*.2+d['preference_match']*.1, 1)
            return (f"Match score: {total}% for {job.title} at {job.company}.\n"
                    f"Matching skills: {', '.join(d['matching_skills']) or 'none detected'}\n"
                    f"Missing skills: {', '.join(d['missing_skills']) or 'none'}\n\n{d['explanation']}")
        return "Open a job from the Jobs page and ask me again, and I will score your resume against it."
    if any(k in text for k in ('recommend','suggest','which job','best job','apply to','opening')):
        from .models import JobMatch
        if profile:
            top=list(JobMatch.objects.filter(profile=profile).select_related('job').order_by('-score')[:5])
            if top:
                lines=['Based on your resume, your strongest matches right now:\n']
                lines+=[f"- {m.job.title} at {m.job.company} ({m.score}% match)" for m in top]
                lines.append('\nOpen one from the Jobs page and I can write the cover letter and interview answers for it.')
                return '\n'.join(lines)
        return "Run a job scan from the Jobs page (Scan for Jobs) and I will rank the openings against your resume."
    if any(k in text for k in ('resume','cv','improve','review','polish')):
        if job:
            present,_=_resume_skills(resume_text, job)
            return ("Resume quick review for this role:\n"
                    f"- Lead with the matched skills you genuinely have: {', '.join(present[:6]) or 'your strongest skills'}.\n"
                    "- Add measurable outcomes to your top three bullets using numbers you can defend.\n"
                    "- Mirror the exact keywords the posting uses.\n"
                    "- Keep it to one page if you have under five years of experience.")
        return "Upload your resume on the Profile page, then open a job and ask me to review it against that role."
    if any(k in text for k in ('plan','roadmap','learning','study','course','resource')):
        if job:
            data=fallback_match(resume_text, job, profile)
            if data['missing_skills']:
                lines=[f"Learning roadmap for {job.title} at {job.company}:\n"]
                for i, skill in enumerate(data['missing_skills'][:5], 1):
                    lines.append(f"{i}. {skill}")
                    lines.append(f"   - Build a mini-project using {skill}")
                    lines.append(f"   - Course: Coursera/Udemy/freeCodeCamp search for '{skill}'")
                    lines.append(f"   - GitHub: Search topics for '{skill}' examples")
                    lines.append("")
                return '\n'.join(lines)
            return "No critical skill gaps for this role! Focus on deepening your matched skills."
        return "Open a specific job and ask me for a learning plan."
    return (f"Hi {name}, I'm your AI career assistant. I can:\n"
            "- Suggest jobs that fit your resume\n"
            "- Write a tailored cover letter for any opening\n"
            "- Prepare interview questions with model answers\n"
            "- Point out your skill gaps and how to close them\n"
            "- Create a learning roadmap for missing skills\n\n"
            "Open a job from the Jobs page and ask me anything, or try: \"write a cover letter\", "
            "\"interview questions\", \"what are my skill gaps?\", \"how do I fix missing skills?\", \"learning plan\"")


import hashlib, html, re, requests
from datetime import datetime, timezone as dt_tz

from bs4 import BeautifulSoup
from django.utils import timezone as dj_tz

class JobSource:
    name='base'
    def fetch(self): raise NotImplementedError

def _plain_text(raw):
    '''Turn HTML (sometimes HTML-escaped HTML) descriptions into clean text for matching.'''
    if not raw: return ''
    text=html.unescape(str(raw))
    if '&lt;' in text or '&gt;' in text: text=html.unescape(text)
    text=BeautifulSoup(text,'html.parser').get_text(' ',strip=True)
    return re.sub(r'\s{3,}',' ',text).strip()

def _parse_time(value):
    '''Normalise API timestamps (epoch int or ISO string) to an aware datetime.'''
    if value in (None,''): return None
    if isinstance(value,(int,float)):
        if value > 1e12: value=value/1000.0  # some feeds send milliseconds
        return datetime.fromtimestamp(value,tz=dt_tz.utc)
    try: parsed=datetime.fromisoformat(str(value).strip().replace('Z','+00:00'))
    except ValueError: return None
    return dj_tz.make_aware(parsed) if dj_tz.is_naive(parsed) else parsed

def _clip(value,size): return str(value or '').strip()[:size]

# Hub cities where the 12 tech/MNC hubs are. Live feeds (Himalayas/Remotive)
# only say "Remote - India" / "Remote", so map each remote posting to one of
# the 12 hub cities (deterministic per posting) instead of showing "Remote".
_HUB_CITIES = ['Bengaluru','Hyderabad','Chennai','Pune','Mumbai','Gurugram',
               'Noida','Delhi','Kolkata','Ahmedabad','Kochi','Coimbatore']

def _hub_city(key=''):
    '''Deterministic hub city for a remote posting (stable across scans).'''
    digest = hashlib.md5(str(key or '').encode()).hexdigest()
    return _HUB_CITIES[int(digest, 16) % len(_HUB_CITIES)]

def _normalise_location(raw_location, fallback_key=''):
    '''Show a hub city in place of bare "Remote" labels from live feeds.'''
    text = str(raw_location or '').strip()
    if not text or text.lower() in ('remote','remote - india','remote-india','india','remote india','work from home','wfh'):
        return _hub_city(fallback_key or text)
    return _clip(text,300)


class ArbeitnowSource(JobSource):
    '''Public Arbeitnow job-board API (no API key): https://www.arbeitnow.com/api/job-board-api

    Fetches the first `max_pages` pages of fresh listings. Deterministic
    external_ids (source:slug) keep repeated scans duplicate-free.
    '''
    name='arbeitnow'
    endpoint='https://www.arbeitnow.com/api/job-board-api'
    max_pages=2

    def fetch(self):
        results=[]; seen=set(); next_url=self.endpoint
        for _ in range(self.max_pages):
            if not next_url: break
            response=requests.get(next_url,timeout=25,headers={'User-Agent':'AI-Career-Copilot/1.0'})
            response.raise_for_status()
            payload=response.json()
            for item in payload.get('data') or []:
                slug=item.get('slug')
                # The feed can shift between page requests, so guard against repeats.
                if not slug or slug in seen: continue
                seen.add(slug)
                results.append({
                    'external_id':f'{self.name}:{slug}',
                    'source':self.name,
                    'company':_clip(item.get('company_name') or 'Unknown company',200),
                    'title':_clip(item.get('title') or 'Untitled role',300),
                    # Arbeitnow flags remote roles separately - show that posting's hub city too.
                    'location': _hub_city(slug) if item.get('remote') else _normalise_location(item.get('location'), slug),
                    'url':item.get('url') or f'https://www.arbeitnow.com/jobs/{slug}',
                    'description':_plain_text(item.get('description'))[:20000],
                    'required_skills':[_clip(t,60) for t in (item.get('tags') or [])[:12]],
                    'preferred_skills':[],
                    'experience':'',
                    'posted_at':_parse_time(item.get('created_at')),
                })
            next_url=(payload.get('links') or {}).get('next')
        return results


class RemotiveSource(JobSource):
    '''Remotive public remote-jobs API (no key; https://remotive.com/api/remote-jobs).

    Remote-focused listings; attribution to Remotive is required by their terms.
    '''
    name='remotive'
    endpoint='https://remotive.com/api/remote-jobs'
    limit=50

    def fetch(self):
        response=requests.get(self.endpoint,params={'limit':self.limit},timeout=25,
                              headers={'User-Agent':'AI-Career-Copilot/1.0'})
        response.raise_for_status()
        results=[]
        for item in response.json().get('jobs') or []:
            rid=item.get('id')
            if rid in (None,''): continue
            tags=[_clip(t,60) for t in (item.get('tags') or [])[:10] if _clip(t,60)]
            category=_clip(item.get('category'),60)
            if category and len(tags)<12 and category.lower() not in [t.lower() for t in tags]:
                tags.append(category)
            results.append({
                'external_id':f'{self.name}:{rid}',
                'source':self.name,
                'company':_clip(item.get('company_name') or 'Unknown company',200),
                'title':_clip(item.get('title') or 'Untitled role',300),
                # Remotive is remote-only work: show the posting's hub city instead of "Remote".
                'location':_hub_city(str(rid)),
                'url':item.get('url') or f'https://remotive.com/remote-jobs/{rid}',
                'description':_plain_text(item.get('description'))[:20000],
                'required_skills':tags,
                'preferred_skills':[],
                'experience':'',
                'posted_at':_parse_time(item.get('publication_date')),
            })
        return results


class HimalayasSource(JobSource):
    '''Official Himalayas remote-jobs API (free, no key): https://himalayas.app/docs/remote-jobs-api

    Queries are filtered server-side for India + entry-level (fresher), then
    targeted IT queries widen the pool. 429 responses stop the walk politely.
    '''
    name='himalayas'
    endpoint='https://himalayas.app/jobs/api/search'
    broad_pages=4
    seniorities=['Entry-level', 'Mid-level', 'Senior-level']
    targeted_queries=['engineer','developer','software','python','data','qa','devops','it',
                      'web','react','java','network','intern','senior engineer','lead',
                      'architect','manager']

    def fetch(self):
        results=[]; seen=set()

        def grab(params):
            response=requests.get(self.endpoint,params=params,timeout=25,
                                  headers={'User-Agent':'AI-Career-Copilot/1.0'})
            if response.status_code==429: return None  # rate limited: keep what we have
            response.raise_for_status()
            return response.json()

        def add(payload, seniority='Entry-level'):
            if not isinstance(payload, dict):
                return
            label = {
                'Entry-level': 'Fresher / Entry-level (0-2 years)',
                'Mid-level': 'Mid-level (2-5 years)',
                'Senior-level': 'Senior (5+ years)',
            }.get(seniority, seniority)
            for item in payload.get('jobs') or []:
                if not isinstance(item,dict): continue
                guid=item.get('guid') or item.get('applicationLink')
                if not guid or guid in seen: continue
                seen.add(guid)
                restrictions=[]
                for r in (item.get('locationRestrictions') or []):
                    # Entries are sometimes dicts ({name, alpha2}) and sometimes plain strings.
                    name=(r.get('name') or r.get('alpha2')) if isinstance(r,dict) else str(r or '').strip()
                    if name: restrictions.append(name)
                results.append({
                    'external_id':f'{self.name}:{guid}',
                    'source':self.name,
                    'company':_clip(item.get('companyName') or 'Unknown company',200),
                    'title':_clip(item.get('title') or 'Untitled role',300),
                    # Himalayas is remote-work data: show hub city, never "Remote - India".
                    'location':_hub_city(str(guid)),
                    'url':item.get('applicationLink') or guid,
                    'description':_plain_text(item.get('description') or item.get('excerpt'))[:20000],
                    'required_skills':[_clip(c,60).replace('-',' ') for c in (item.get('categories') or [])[:12]],
                    'preferred_skills':[],
                    'experience': label,
                    'posted_at':_parse_time(item.get('pubDate')),
                })

        # 1) recent India listings across fresher + mid + senior (freshest first)
        for seniority in self.seniorities:
            base = {'country': 'IN', 'seniority': seniority, 'sort': 'recent'}
            for page in range(1, self.broad_pages + 1):
                payload = grab({**base, 'page': page})
                if payload is None:
                    break
                add(payload, seniority=seniority)
        # 2) IT-focused queries so non-IT roles do not crowd the feed
        for query in self.targeted_queries:
            for seniority in self.seniorities:
                payload = grab({**base, 'q': query, 'page': 1, 'seniority': seniority})
                if payload is None:
                    break
                add(payload, seniority=seniority)
        return results


class MncSeedSource(JobSource):
    '''Curated MNC openings across India with South-India weightage.

    External aggregator feeds rarely carry TCS / Infosys / Wipro / HCL /
    Tech Mahindra / Cognizant / Accenture postings, so this seed guarantees
    those employers (fresher + senior) are always present alongside live feeds.
    URLs point at each company's official careers portal.'''
    name = 'mnc-seed'

    def __init__(self, name='mnc-seed', url=''):
        self.name = name
        self.url = url
    def fetch(self):
        return [dict(r, external_id=f'{self.name}:{r["company"]}:{r["title"]}:{r["location"]}:{r["experience"]}'.lower().replace(' ', '-').replace('/', '-')[:280], source=self.name) for r in self._rows()]

    @staticmethod
    def _rows():
        tcs = 'https://www.tcs.com/careers'
        infy = 'https://www.infosys.com/careers/'
        wipro = 'https://careers.wipro.com/'
        hcl = 'https://www.hcltech.com/careers'
        techm = 'https://www.techmahindra.com/en-in/careers/'
        cogn = 'https://www.cognizant.com/in/en/careers'
        acc = 'https://www.accenture.com/in-en/careers'
        return [
            {'company': 'TCS', 'title': 'Ninja Developer Fresher (Java/Python)', 'location': 'Chennai, Tamil Nadu, India', 'url': tcs, 'description': 'TCS Ninja fresher hiring for software development in Chennai. Entry-level Java/Python role, 0-2 years.', 'required_skills': ['java', 'python', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'TCS', 'title': 'Senior Java Microservices Engineer', 'location': 'Bengaluru, Karnataka, India', 'url': tcs, 'description': 'Senior Java Spring Boot microservices role in Bengaluru, 5+ years experience.', 'required_skills': ['java', 'spring boot', 'microservices'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Infosys', 'title': 'System Engineer Fresher (Off-Campus)', 'location': 'Bengaluru, Karnataka, India', 'url': infy, 'description': 'Infosys System Engineer fresher opening via off-campus drive. 0-1 years, training provided.', 'required_skills': ['python', 'sql', 'software'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Infosys', 'title': 'Senior Python Developer - Data Engineering', 'location': 'Hyderabad, Telangana, India', 'url': infy, 'description': 'Senior data engineer (Python/ETL) in Hyderabad, 5+ years.', 'required_skills': ['python', 'etl', 'data pipeline'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Wipro', 'title': 'Project Engineer Fresher (Elite NTH)', 'location': 'Hyderabad, Telangana, India', 'url': wipro, 'description': 'Wipro Elite National Talent Hunt fresher role for project engineering, 0-2 years.', 'required_skills': ['java', 'sql', 'software'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},

            {'company': 'Wipro', 'title': 'Lead DevOps Engineer (AWS)', 'location': 'Bengaluru, Karnataka, India', 'url': wipro, 'description': 'Lead DevOps with AWS/Kubernetes in Bengaluru, 6+ years.', 'required_skills': ['devops', 'aws', 'kubernetes'], 'preferred_skills': [], 'experience': 'Senior (6+ years)', 'posted_at': None},
            {'company': 'HCLTech', 'title': 'Graduate Engineer Trainee (GET)', 'location': 'Chennai, Tamil Nadu, India', 'url': hcl, 'description': 'HCLTech fresher Graduate Engineer Trainee program, Chennai. 0-1 years.', 'required_skills': ['software', 'testing', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'HCLTech', 'title': 'Senior React Developer', 'location': 'Bengaluru, Karnataka, India', 'url': hcl, 'description': 'Senior frontend React role in Bengaluru, 5+ years.', 'required_skills': ['react', 'javascript', 'typescript'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Tech Mahindra', 'title': 'Associate Software Engineer Fresher', 'location': 'Hyderabad, Telangana, India', 'url': techm, 'description': 'Tech Mahindra fresher associate software engineer, Hyderabad. 0-2 years.', 'required_skills': ['java', 'sql', 'software'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Tech Mahindra', 'title': 'Senior Network Engineer', 'location': 'Chennai, Tamil Nadu, India', 'url': techm, 'description': 'Senior telecom/network engineering role in Chennai, 5+ years.', 'required_skills': ['network engineer', 'cloud', 'security'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},

            {'company': 'Cognizant', 'title': 'GenC Fresher Software Engineer', 'location': 'Coimbatore, Tamil Nadu, India', 'url': cogn, 'description': 'Cognizant GenC fresher hiring for software engineering in Coimbatore, 0-2 years.', 'required_skills': ['java', 'python', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Cognizant', 'title': 'Senior Salesforce Developer', 'location': 'Hyderabad, Telangana, India', 'url': cogn, 'description': 'Senior Salesforce development role in Hyderabad, 5+ years.', 'required_skills': ['salesforce', 'apex', 'cloud'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Accenture', 'title': 'Associate Software Engineer (ASE)', 'location': 'Bengaluru, Karnataka, India', 'url': acc, 'description': 'Accenture ASE fresher role in Bengaluru, 0-2 years, cloud/software.', 'required_skills': ['cloud', 'java', 'software'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Accenture', 'title': 'Senior Data Scientist (AI/ML)', 'location': 'Hyderabad, Telangana, India', 'url': acc, 'description': 'Senior AI/ML data scientist in Hyderabad, 6+ years.', 'required_skills': ['machine learning', 'python', 'data science'], 'preferred_skills': [], 'experience': 'Senior (6+ years)', 'posted_at': None},
            {'company': 'LTIMindtree', 'title': 'Fresher QA Automation Engineer', 'location': 'Chennai, Tamil Nadu, India', 'url': 'https://www.ltimindtree.com/careers/', 'description': 'Fresher test automation (Selenium/Python) in Chennai, 0-2 years.', 'required_skills': ['qa', 'test automation', 'python'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},

            {'company': 'Capgemini', 'title': 'Senior Cloud Engineer (Azure)', 'location': 'Bengaluru, Karnataka, India', 'url': 'https://www.capgemini.com/in-en/careers/', 'description': 'Senior Azure cloud engineer in Bengaluru, 5+ years.', 'required_skills': ['cloud', 'devops', 'python'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'IBM', 'title': 'Entry-Level Backend Developer', 'location': 'Kochi, Kerala, India', 'url': 'https://www.ibm.com/in-en/employment/', 'description': 'Entry-level backend development in Kochi, 0-2 years.', 'required_skills': ['java', 'backend', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Oracle', 'title': 'Senior Database Engineer', 'location': 'Bengaluru, Karnataka, India', 'url': 'https://www.oracle.com/in/careers/', 'description': 'Senior Oracle database engineering in Bengaluru, 6+ years.', 'required_skills': ['database', 'sql', 'oracle developer'], 'preferred_skills': [], 'experience': 'Senior (6+ years)', 'posted_at': None},
            {'company': 'Dell', 'title': 'Graduate Software Engineer', 'location': 'Chennai, Tamil Nadu, India', 'url': 'https://jobs.dell.com/', 'description': 'Dell fresher software engineer in Chennai, 0-2 years.', 'required_skills': ['software', 'python', 'testing'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Zoho', 'title': 'Software Developer (Fresher)', 'location': 'Chennai, Tamil Nadu, India', 'url': 'https://www.zoho.com/careers/', 'description': 'Zoho fresher software developer in Chennai, 0-2 years.', 'required_skills': ['software', 'java', 'web developer'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Infosys', 'title': 'System Engineer Fresher', 'location': 'Pune, Maharashtra', 'url': infy, 'description': 'Infosys fresher system engineer in Pune Hinjewadi, 0-2 years, java/python.', 'required_skills': ['java', 'python', 'software'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'TCS', 'title': 'Senior Cloud Engineer (AWS)', 'location': 'Pune, Maharashtra', 'url': tcs, 'description': 'Senior AWS cloud engineer at TCS Pune, 5+ years.', 'required_skills': ['cloud', 'devops', 'python'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Wipro', 'title': 'Fresher IT Support Engineer', 'location': 'Pune, Maharashtra', 'url': wipro, 'description': 'Wipro fresher IT support / service desk in Pune, 0-1 years.', 'required_skills': ['it support', 'technical support', 'network'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-1 years)', 'posted_at': None},
            {'company': 'Tech Mahindra', 'title': 'Junior Java Developer', 'location': 'Pune, Maharashtra', 'url': techm, 'description': 'Tech Mahindra fresher java developer in Pune, 0-2 years.', 'required_skills': ['java', 'software', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Cognizant', 'title': 'Senior Full Stack Developer', 'location': 'Pune, Maharashtra', 'url': cogn, 'description': 'Senior full stack React/Node role in Pune, 5+ years.', 'required_skills': ['full stack', 'react', 'node js'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Capgemini', 'title': 'Fresher Software Engineer', 'location': 'Mumbai, Maharashtra', 'url': 'https://www.capgemini.com/in-en/careers/', 'description': 'Capgemini fresher software engineer in Mumbai, 0-2 years.', 'required_skills': ['software', 'java', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Accenture', 'title': 'Senior DevOps Engineer', 'location': 'Mumbai, Maharashtra', 'url': acc, 'description': 'Senior DevOps/Kubernetes engineer in Mumbai, 5+ years.', 'required_skills': ['devops', 'kubernetes', 'cloud'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'IBM', 'title': 'Fresher Application Developer', 'location': 'Mumbai, Maharashtra', 'url': 'https://www.ibm.com/in-en/employment/', 'description': 'IBM fresher application developer in Mumbai, 0-2 years.', 'required_skills': ['software', 'python', 'backend'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'TCS', 'title': 'Fresher Software Engineer', 'location': 'Gurugram, Haryana', 'url': tcs, 'description': 'TCS fresher software engineer in Gurugram Cyber City, 0-2 years.', 'required_skills': ['software', 'java', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Accenture', 'title': 'Senior Cloud Developer', 'location': 'Gurugram, Haryana', 'url': acc, 'description': 'Senior cloud developer in Gurugram, 5+ years.', 'required_skills': ['cloud', 'python', 'devops'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'HCLTech', 'title': 'Fresher Graduate Engineer', 'location': 'Noida, Uttar Pradesh', 'url': hcl, 'description': 'HCLTech fresher graduate engineer in Noida Sector 62, 0-2 years.', 'required_skills': ['software', 'java', 'testing'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Tech Mahindra', 'title': 'Senior Java Developer', 'location': 'Noida, Uttar Pradesh', 'url': techm, 'description': 'Senior Java backend role in Noida, 5+ years.', 'required_skills': ['java', 'backend', 'cloud'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'IBM', 'title': 'Fresher System Engineer', 'location': 'Delhi, Delhi', 'url': 'https://www.ibm.com/in-en/employment/', 'description': 'IBM fresher system engineer in Delhi NCR, 0-2 years.', 'required_skills': ['software', 'python', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Cognizant', 'title': 'Senior Data Engineer', 'location': 'Delhi, Delhi', 'url': cogn, 'description': 'Senior data engineer in Delhi NCR, 5+ years.', 'required_skills': ['data engineer', 'python', 'sql'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'TCS', 'title': 'Fresher IT Analyst', 'location': 'Kolkata, West Bengal', 'url': tcs, 'description': 'TCS fresher IT analyst in Kolkata Sector V, 0-2 years.', 'required_skills': ['software', 'java', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'Wipro', 'title': 'Senior Software Engineer', 'location': 'Kolkata, West Bengal', 'url': wipro, 'description': 'Senior software engineer in Kolkata, 5+ years.', 'required_skills': ['java', 'backend', 'cloud'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
            {'company': 'Infosys', 'title': 'Fresher System Engineer', 'location': 'Ahmedabad, Gujarat', 'url': infy, 'description': 'Infosys fresher system engineer in Ahmedabad GIFT City, 0-2 years.', 'required_skills': ['python', 'software', 'sql'], 'preferred_skills': [], 'experience': 'Fresher / Entry-level (0-2 years)', 'posted_at': None},
            {'company': 'HCLTech', 'title': 'Senior Cloud Engineer', 'location': 'Ahmedabad, Gujarat', 'url': hcl, 'description': 'Senior cloud engineer in Ahmedabad, 5+ years.', 'required_skills': ['cloud', 'devops', 'python'], 'preferred_skills': [], 'experience': 'Senior (5+ years)', 'posted_at': None},
        ]


class AuthorizedHtmlSource(JobSource):
    def __init__(self, name='custom', url=''):
        self.name = name
        self.url = url

    def fetch(self):
        return []


def configured_sources():
    # India-focused, fresher + senior, key-free feeds.
    return [MncSeedSource(), HimalayasSource(), RemotiveSource()]

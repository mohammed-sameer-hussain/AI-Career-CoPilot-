'''
Intelligent Job Matching & Information Retrieval Engine for AI Career Copilot.

Key capabilities:
1. Comprehensive Skill Extraction & Canonicalization:
   Extracts technical competencies, frameworks, tools, architectures, and methodologies
   from unstructured resume text and job descriptions.
2. Semantic Similarity using Embeddings:
   Recognizes equivalent skills (e.g. Postgres <-> PostgreSQL, k8s <-> Kubernetes,
   FastAPI <-> Python REST APIs) and computes document-level semantic embeddings.
3. Strict Separation of Match Score vs. Hiring Probability:
   - Match Score (0-100%): Qualification and competency fit.
   - Hiring Probability (0-100%): Realistic probability of offer/hire taking into account
     applicant pool volume, MNC selectivity, seniority mismatch penalties, and resume signal strength.
4. Explainable AI & Actionable Gap Analysis:
   Highlights exact matches, semantic matches, missing critical requirements, and recommendations.
'''

import re
import math
import os
import json
from collections import defaultdict

# Optional dependencies with graceful fallback
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    np = None
    SKLEARN_AVAILABLE = False


# ==============================================================================
# 1. TECH SKILL TAXONOMY & CANONICAL ALIAS ONTOLOGY
# ==============================================================================

# Mapping from canonical skill name to aliases, synonyms, and abbreviations
TECH_ONTOLOGY = {
    # Languages
    'python': ['python', 'py', 'python3', 'python 3', 'python2'],
    'java': ['java', 'java 8', 'java 11', 'java 17', 'java 21', 'core java'],
    'javascript': ['javascript', 'js', 'es6', 'es6+', 'ecmascript'],
    'typescript': ['typescript', 'ts'],
    'c++': ['c++', 'cpp', 'c plus plus'],
    'c#': ['c#', 'csharp', 'c sharp', '.net c#'],
    'golang': ['go', 'golang'],
    'rust': ['rust', 'rustlang'],
    'php': ['php', 'php7', 'php8'],
    'ruby': ['ruby', 'ruby on rails', 'rails'],
    'sql': ['sql', 't-sql', 'pl/sql', 'structured query language'],
    'html/css': ['html', 'html5', 'css', 'css3', 'web markup'],
    'bash/shell': ['bash', 'shell', 'sh', 'shell scripting', 'powershell', 'zsh'],
    'kotlin': ['kotlin', 'kotlin android'],
    'swift': ['swift', 'swiftui', 'ios swift'],
    'scala': ['scala'],
    'r': ['r language', 'r programming'],

    # Frontend
    'react': ['react', 'react.js', 'reactjs', 'react native'],
    'angular': ['angular', 'angular.js', 'angularjs', 'angular 2+'],
    'vue': ['vue', 'vue.js', 'vuejs', 'vue3', 'vue 3'],
    'next.js': ['next.js', 'nextjs', 'next'],
    'redux': ['redux', 'redux toolkit', 'rtk'],
    'tailwind css': ['tailwind', 'tailwindcss', 'tailwind css'],
    'bootstrap': ['bootstrap', 'bootstrap 5'],
    'webpack': ['webpack', 'vite', 'frontend bundling', 'parcel'],

    # Backend & Microservices
    'spring boot': ['spring boot', 'spring framework', 'spring mvc', 'spring cloud', 'spring'],
    'django': ['django', 'django rest framework', 'drf'],
    'fastapi': ['fastapi', 'fast-api', 'fast api'],
    'flask': ['flask', 'flask rest'],
    'node.js': ['node', 'node.js', 'nodejs', 'express', 'express.js', 'expressjs'],
    'microservices': ['microservices', 'microservice architecture', 'distributed systems', 'service oriented architecture', 'soa'],
    'rest api': ['rest api', 'restful', 'restful apis', 'rest apis', 'restful web services', 'web api'],
    'graphql': ['graphql', 'apollo graphql'],
    'grpc': ['grpc', 'protocol buffers', 'protobuf'],

    # Databases & Storage
    'postgresql': ['postgresql', 'postgres', 'psql', 'postgres db'],
    'mysql': ['mysql', 'mariadb'],
    'mongodb': ['mongodb', 'mongo', 'nosql document store'],
    'redis': ['redis', 'redis cache', 'in-memory database'],
    'oracle database': ['oracle', 'oracle db', 'oracle developer', 'plsql', 'pl/sql'],
    'elasticsearch': ['elasticsearch', 'elastic search', 'elk stack', 'opensearch'],
    'cassandra': ['cassandra', 'apache cassandra'],
    'dynamodb': ['dynamodb', 'aws dynamodb'],
    'sqlite': ['sqlite', 'sqlite3'],

    # Cloud & DevOps
    'aws': ['aws', 'amazon web services', 'ec2', 's3', 'lambda', 'aws cloud'],
    'azure': ['azure', 'microsoft azure', 'azure devops', 'azure cloud'],
    'gcp': ['gcp', 'google cloud', 'google cloud platform'],
    'docker': ['docker', 'docker container', 'containerization', 'containers'],
    'kubernetes': ['kubernetes', 'k8s', 'container orchestration', 'helm'],
    'terraform': ['terraform', 'infrastructure as code', 'iac'],
    'ci/cd': ['ci/cd', 'ci cd', 'continuous integration', 'continuous delivery', 'github actions', 'jenkins', 'gitlab ci'],
    'ansible': ['ansible', 'configuration management'],
    'linux': ['linux', 'unix', 'ubuntu', 'centos', 'redhat', 'rhel', 'debian'],

    # Data Science, AI & ML
    'machine learning': ['machine learning', 'ml', 'statistical modeling', 'predictive modeling'],
    'deep learning': ['deep learning', 'neural networks', 'ann', 'cnn', 'rnn'],
    'artificial intelligence': ['artificial intelligence', 'ai', 'genai', 'generative ai', 'llm', 'llms', 'large language models'],
    'pytorch': ['pytorch', 'torch'],
    'tensorflow': ['tensorflow', 'tf', 'keras'],
    'nlp': ['nlp', 'natural language processing', 'text analytics', 'huggingface'],
    'pandas': ['pandas', 'numpy', 'scipy', 'python data stack'],
    'pyspark': ['pyspark', 'spark', 'apache spark'],
    'kafka': ['kafka', 'apache kafka', 'event streaming', 'message broker'],
    'snowflake': ['snowflake', 'snowflake data warehouse'],
    'data pipeline': ['data pipeline', 'etl', 'data engineering', 'data warehouse', 'data warehousing', 'airflow'],
    'power bi': ['power bi', 'powerbi', 'tableau', 'data visualization', 'dashboards'],

    # Testing & Quality
    'qa testing': ['qa', 'quality assurance', 'software testing', 'manual testing', 'black box testing'],
    'test automation': ['test automation', 'automation testing', 'selenium', 'cypress', 'playwright', 'appium', 'sdet'],
    'unit testing': ['unit testing', 'junit', 'pytest', 'jest', 'mocking', 'tdd'],

    # Software Engineering & Methodology
    'git': ['git', 'github', 'gitlab', 'version control', 'bitbucket'],
    'agile': ['agile', 'scrum', 'kanban', 'sprint planning'],
    'data structures': ['data structures', 'algorithms', 'dsa', 'problem solving', 'oop', 'object oriented programming'],
    'cybersecurity': ['security', 'cybersecurity', 'cyber security', 'information security', 'soc', 'siem', 'penetration testing', 'owasp'],
    'network engineering': ['network engineer', 'networking', 'tcp/ip', 'dns', 'routing', 'switching', 'cisco', 'firewall', 'sd-wan'],
    'salesforce': ['salesforce', 'apex', 'lwc', 'lightning web components', 'visualforce'],
    'sap': ['sap', 'abap', 'sap hana', 'sap consultant'],
}

# Inverted index: alias string -> canonical name
ALIAS_TO_CANONICAL = {}
for canonical, aliases in TECH_ONTOLOGY.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical

# Explicit functional and semantic equivalences:
# If job asks for Key, candidate having any Value satisfies it semantically (or vice versa)
TECH_EQUIVALENCES = {
    'sql': {'postgresql', 'mysql', 'oracle database', 'sqlite', 'sql'},
    'relational database': {'postgresql', 'mysql', 'oracle database', 'sqlite', 'sql'},
    'rdbms': {'postgresql', 'mysql', 'oracle database', 'sqlite', 'sql'},
    'python': {'python', 'django', 'fastapi', 'flask'},
    'django': {'fastapi', 'flask', 'django'},
    'fastapi': {'django', 'flask', 'fastapi'},
    'flask': {'fastapi', 'django', 'flask'},
    'java': {'java', 'spring boot'},
    'spring boot': {'java', 'spring boot'},
    'docker': {'kubernetes', 'docker'},
    'kubernetes': {'docker', 'kubernetes'},
    'containerization': {'docker', 'kubernetes'},
    'aws': {'azure', 'gcp', 'aws'},
    'azure': {'aws', 'gcp', 'azure'},
    'gcp': {'aws', 'azure', 'gcp'},
    'cloud': {'aws', 'azure', 'gcp'},
    'react': {'next.js', 'redux', 'react'},
    'next.js': {'react', 'next.js'},
    'javascript': {'typescript', 'javascript'},
    'typescript': {'javascript', 'typescript'},
    'machine learning': {'deep learning', 'pytorch', 'tensorflow', 'machine learning'},
    'deep learning': {'machine learning', 'pytorch', 'tensorflow', 'deep learning'},
    'artificial intelligence': {'machine learning', 'deep learning', 'nlp', 'artificial intelligence'},
    'data pipeline': {'pyspark', 'kafka', 'snowflake', 'data pipeline'},
    'ci/cd': {'terraform', 'docker', 'ci/cd'},
    'qa testing': {'test automation', 'unit testing', 'qa testing'},
    'test automation': {'qa testing', 'unit testing', 'test automation'},
}

# Categorical domain clusters to prevent cross-domain matches (e.g. language to network)
DOMAIN_CATEGORIES = {
    'languages': {'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'golang', 'rust', 'php', 'ruby', 'kotlin', 'swift'},
    'frontend': {'react', 'angular', 'vue', 'next.js', 'redux', 'tailwind css', 'bootstrap', 'webpack', 'html/css'},
    'backend_frameworks': {'spring boot', 'django', 'fastapi', 'flask', 'node.js'},
    'databases': {'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'oracle database', 'elasticsearch', 'cassandra', 'dynamodb', 'sqlite'},
    'cloud_devops': {'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ci/cd', 'ansible', 'linux', 'bash/shell'},
    'data_ai': {'machine learning', 'deep learning', 'artificial intelligence', 'pytorch', 'tensorflow', 'nlp', 'pandas', 'pyspark', 'kafka', 'snowflake', 'data pipeline', 'power bi'},
    'testing': {'qa testing', 'test automation', 'unit testing'},
    'foundations': {'git', 'agile', 'data structures', 'microservices', 'rest api', 'graphql'},
}

# Related skill clusters for semantic fallback when direct embedding is distant
SKILL_CLUSTERS = {
    'python_backend': {'python', 'django', 'fastapi', 'flask', 'rest api', 'sql', 'postgresql'},
    'java_backend': {'java', 'spring boot', 'microservices', 'rest api', 'sql', 'mysql', 'oracle database'},
    'javascript_frontend': {'javascript', 'typescript', 'react', 'next.js', 'redux', 'angular', 'vue', 'html/css', 'tailwind css'},
    'fullstack_js': {'javascript', 'typescript', 'react', 'node.js', 'mongodb', 'rest api', 'html/css'},
    'cloud_devops': {'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ci/cd', 'linux', 'bash/shell'},
    'data_engineering': {'python', 'sql', 'data pipeline', 'pyspark', 'kafka', 'snowflake', 'postgresql'},
    'ai_ml': {'python', 'machine learning', 'deep learning', 'artificial intelligence', 'pytorch', 'tensorflow', 'nlp', 'pandas'},
    'databases': {'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'oracle database', 'sqlite', 'dynamodb'},
    'testing': {'qa testing', 'test automation', 'unit testing'},
}


# ==============================================================================
# 2. LOCAL SEMANTIC EMBEDDINGS VECTORIZER
# ==============================================================================

class SemanticEmbeddingEngine:
    '''
    High-performance semantic embedding engine.
    Computes vector representations using sublinear TF-IDF + char/word n-grams.
    Provides fast, deterministic cosine similarity between texts without requiring
    external GPU or API keys.
    '''
    _instance = None

    def __init__(self):
        # Representative corpus of tech domains, skill phrases, and job descriptions
        seed_corpus = [
            'python backend web developer django fastapi flask rest api postgresql sql docker microservices',
            'java spring boot microservices enterprise software engineer hibernate sql relational database kafka',
            'frontend web developer react typescript javascript html5 css3 redux tailwind responsive ui',
            'full stack engineer node.js express react typescript mongodb sql restful api architecture',
            'cloud devops infrastructure engineer aws terraform kubernetes docker ci/cd linux automated deployment',
            'data engineer python sql spark pyspark kafka etl data pipeline snowflake data warehouse',
            'machine learning data scientist python deep learning pytorch tensorflow artificial intelligence nlp pandas',
            'qa automation software test engineer selenium python testng quality assurance unit testing regression',
            'cybersecurity analyst information security network engineering cisco firewall vulnerability assessment',
            'graduate engineer trainee associate software developer fresher computer science data structures algorithms'
        ]
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),
                sublinear_tf=True,
                max_features=1500,
                token_pattern=r'(?u)\b[\w\+\#\.\/]{2,}\b'
            )
            self.vectorizer.fit(seed_corpus)
        else:
            self.vectorizer = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def compute_similarity(self, text_a, text_b):
        '''Return cosine similarity between two texts (0.0 to 1.0).'''
        if not text_a or not text_b:
            return 0.0

        if SKLEARN_AVAILABLE and self.vectorizer is not None:
            try:
                # Transform both texts into TF-IDF vector space
                vectors = self.vectorizer.transform([text_a, text_b])
                sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
                return float(max(0.0, min(1.0, sim)))
            except Exception:
                pass

        # Fallback Jaccard n-gram similarity if scikit-learn is absent or encounters error
        words_a = set(re.findall(r'\b[\w\+\#]{2,}\b', text_a.lower()))
        words_b = set(re.findall(r'\b[\w\+\#]{2,}\b', text_b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return float(intersection / union) if union > 0 else 0.0


# ==============================================================================
# 3. ROBUST SKILL EXTRACTION FROM RESUME
# ==============================================================================

def extract_skills_from_text(raw_text):
    '''
    Extract set of recognized canonical skills from raw text (resume or job description).
    Uses word boundaries and multi-word phrase matching against alias ontology.
    '''
    if not raw_text:
        return set()

    text = ' ' + raw_text.lower().replace('\n', ' ') + ' '
    # Normalize punctuation that separates words but preserve c++, c#, .net
    text = re.sub(r'[,;:\(\)\[\]\{\}\|\/]', ' ', text)
    text = re.sub(r'\s+', ' ', text)

    extracted_canonical = set()

    # Sort aliases by length descending so longer phrases match first (e.g. 'spring boot' before 'spring')
    aliases_sorted = sorted(ALIAS_TO_CANONICAL.keys(), key=lambda x: len(x), reverse=True)

    for alias in aliases_sorted:
        # Match as whole word / token boundary
        escaped_alias = re.escape(alias)
        pattern = r'(?:^|[\s\-_])' + escaped_alias + r'(?:$|[\s\-_])'
        if re.search(pattern, text):
            canonical = ALIAS_TO_CANONICAL[alias]
            extracted_canonical.add(canonical)

    return extracted_canonical


def canonicalize_skill(skill_str):
    '''Map any raw skill string into its canonical ontology name if recognized.'''
    if not skill_str:
        return ''
    cleaned = str(skill_str).strip().lower()
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]
    # Check if any alias is contained inside the raw string
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if alias in cleaned or cleaned in alias:
            return canonical
    return skill_str.strip().title()


# ==============================================================================
# 4. SEMANTIC SKILL COMPARISON (EXACT, SEMANTIC, MISSING)
# ==============================================================================

def compare_skills_semantically(resume_skills, job_required, job_preferred=None):
    '''
    Compare job required and preferred skills against resume skills.
    Categorizes into:
      - exact_matches: Direct canonical match.
      - semantic_matches: Recognized related/transferable skill via cluster or embedding.
      - missing_critical: Required skills not satisfied.
      - missing_preferred: Preferred skills not satisfied.
    '''
    job_required = job_required or []
    job_preferred = job_preferred or []

    resume_canonical = {canonicalize_skill(s).lower() for s in resume_skills if s}

    exact_matches = []
    semantic_matches = []
    missing_critical = []
    preferred_matches = []
    missing_preferred = []

    # Map candidate skills to their clusters for rapid relational lookup
    candidate_clusters = set()
    for s in resume_canonical:
        for cname, cskills in SKILL_CLUSTERS.items():
            if s in cskills:
                candidate_clusters.add(cname)

    embedding_engine = SemanticEmbeddingEngine.get_instance()

    # Process Required Skills
    for req in job_required:
        if not req:
            continue
        req_canon = canonicalize_skill(req).lower()

        # 1. Check Exact / Canonical Match
        if req_canon in resume_canonical:
            exact_matches.append({
                'required_skill': req,
                'canonical': req_canon,
                'match_type': 'exact',
                'matched_with': req_canon,
                'similarity': 1.0
            })
            continue

        # 2. Check Semantic / Related Match
        best_semantic_match = None
        best_sim = 0.0

        # Check explicit equivalences first
        direct_equivs = TECH_EQUIVALENCES.get(req_canon, set())
        for cand_skill in resume_canonical:
            if cand_skill in direct_equivs or req_canon in TECH_EQUIVALENCES.get(cand_skill, set()):
                best_sim = 0.92
                best_semantic_match = cand_skill
                break

        if not best_semantic_match:
            # Check cluster overlap and embedding similarity within compatible domain
            req_domains = {dname for dname, dskills in DOMAIN_CATEGORIES.items() if req_canon in dskills}

            for cand_skill in resume_canonical:
                cand_domains = {dname for dname, dskills in DOMAIN_CATEGORIES.items() if cand_skill in dskills}

                # Cross-domain gating: if both are categorized, require domain intersection
                if req_domains and cand_domains and not (req_domains & cand_domains):
                    continue

                same_cluster = any(
                    req_canon in cskills and cand_skill in cskills
                    for cskills in SKILL_CLUSTERS.values()
                )
                sim = embedding_engine.compute_similarity(req_canon, cand_skill)
                if same_cluster:
                    sim = max(sim, 0.80)

                if sim > best_sim and sim >= 0.70:
                    best_sim = sim
                    best_semantic_match = cand_skill

        if best_semantic_match:
            semantic_matches.append({
                'required_skill': req,
                'canonical': req_canon,
                'match_type': 'semantic',
                'matched_with': best_semantic_match,
                'similarity': round(best_sim, 2),
                'relation': f'Transferable skill equivalence ({best_semantic_match} -> {req})'
            })
        else:
            missing_critical.append(req)

    # Process Preferred Skills
    for pref in job_preferred:
        if not pref:
            continue
        pref_canon = canonicalize_skill(pref).lower()
        if pref_canon in resume_canonical:
            preferred_matches.append(pref)
        else:
            # Check semantic match in resume
            found_related = any(
                embedding_engine.compute_similarity(pref_canon, c) >= 0.70
                for c in resume_canonical
            )
            if found_related:
                preferred_matches.append(pref)
            else:
                missing_preferred.append(pref)

    return {
        'exact_matches': exact_matches,
        'semantic_matches': semantic_matches,
        'missing_critical': missing_critical,
        'preferred_matches': preferred_matches,
        'missing_preferred': missing_preferred,
    }


# ==============================================================================
# 5. EXPERIENCE & SENIORITY PARSING
# ==============================================================================

def parse_candidate_years(resume_text):
    '''Extract total years of experience stated in resume.'''
    if not resume_text:
        return None
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|yr)\b', resume_text.lower())
    numbers = [float(m) for m in matches if float(m) <= 45.0]
    return max(numbers) if numbers else None


def parse_job_experience_range(experience_str):
    '''Parse experience requirements string into (min_years, max_years).'''
    if not experience_str:
        return 0, 99
    text = experience_str.lower()
    if 'fresher' in text or 'entry' in text or 'intern' in text or '0-1' in text or '0-2' in text:
        return 0, 2

    nums = [int(n) for n in re.findall(r'\d+', text)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    elif len(nums) == 1:
        return nums[0], nums[0] + 3
    return 0, 99


SENIORITY_RANKS = {
    'intern': 1, 'trainee': 1, 'apprentice': 1,
    'fresher': 2, 'junior': 2, 'entry': 2, 'associate': 2,
    'mid': 3, 'software engineer': 3, 'developer': 3,
    'senior': 4, 'sr': 4, 'specialist': 4,
    'lead': 5, 'tech lead': 5, 'staff': 5, 'manager': 5,
    'principal': 6, 'architect': 6, 'director': 7, 'head': 7
}

def determine_seniority(text):
    '''Determine seniority level rank (1-7).'''
    if not text:
        return 3
    lower = text.lower()
    found_ranks = [rank for title_kw, rank in SENIORITY_RANKS.items() if re.search(r'\b' + re.escape(title_kw) + r'\b', lower)]
    return max(found_ranks) if found_ranks else 3


# ==============================================================================
# 6. DUAL-SCORE CALCULATION: MATCH SCORE vs. HIRING PROBABILITY
# ==============================================================================

def calculate_intelligent_match(resume_text, job, profile=None):
    '''
    Main Information Retrieval & Matching algorithm.
    Produces:
      - Match Score (0-100%): Technical & Qualification compatibility.
      - Hiring Probability (0-100%): Realistic chance of job offer taking into account competition.
      - Structured breakdown and explanation.
    '''
    resume_text = resume_text or ''
    # 1. Extract skills from resume
    resume_skills = extract_skills_from_text(resume_text)
    if profile and profile.skills:
        for s in profile.skills:
            canon = canonicalize_skill(s)
            if canon:
                resume_skills.add(canon)

    # 2. Extract or canonicalize job skills
    job_required = list(dict.fromkeys(job.required_skills or []))
    if not job_required and job.description:
        # Auto-extract from job description if missing
        job_required = list(extract_skills_from_text(job.description))[:10]

    job_preferred = list(dict.fromkeys(job.preferred_skills or []))

    # 3. Semantic Skill Comparison
    skill_eval = compare_skills_semantically(resume_skills, job_required, job_preferred)
    exact_list = skill_eval['exact_matches']
    semantic_list = skill_eval['semantic_matches']
    missing_crit = skill_eval['missing_critical']
    pref_matches = skill_eval['preferred_matches']

    total_req = len(job_required)
    if total_req > 0:
        # Full credit for exact matches, 75% credit for semantic equivalents
        exact_score = len(exact_list) / total_req * 100.0
        semantic_score = len(semantic_list) * 0.75 / total_req * 100.0
        raw_skill_score = min(100.0, exact_score + semantic_score)
        # Bonus up to 10 points for preferred skills
        if job_preferred:
            pref_bonus = (len(pref_matches) / len(job_preferred)) * 10.0
            raw_skill_score = min(100.0, raw_skill_score + pref_bonus)
    else:
        raw_skill_score = 65.0

    skill_score = round(raw_skill_score, 1)

    # 4. Document-Level Semantic Similarity via Embeddings
    embedding_engine = SemanticEmbeddingEngine.get_instance()
    doc_semantic_sim = embedding_engine.compute_similarity(resume_text, job.description)
    semantic_score = round(doc_semantic_sim * 100.0, 1)

    # 5. Experience Alignment Score
    cand_years = parse_candidate_years(resume_text)
    min_exp, max_exp = parse_job_experience_range(job.experience)

    if cand_years is not None:
        if min_exp <= cand_years <= max_exp:
            exp_score = 100.0
        elif cand_years < min_exp:
            shortfall = min_exp - cand_years
            exp_score = max(30.0, 100.0 - (shortfall * 25.0))
        else: # Over minimum
            excess = cand_years - max_exp
            exp_score = max(60.0, 100.0 - (excess * 8.0))
    else:
        exp_score = 75.0 if min_exp <= 2 else 60.0

    exp_score = round(exp_score, 1)

    # 6. Seniority Alignment Score
    cand_seniority = determine_seniority(resume_text)
    job_seniority = determine_seniority(job.title + ' ' + (job.experience or ''))
    seniority_gap = abs(cand_seniority - job_seniority)
    seniority_score = 100.0 if seniority_gap == 0 else max(40.0, 100.0 - (seniority_gap * 22.0))
    seniority_score = round(seniority_score, 1)

    # 7. Location & Preference Fit
    location_score = 60.0
    job_loc = (job.location or '').lower()
    if profile and profile.preferred_locations:
        prefs = [str(l).lower() for l in profile.preferred_locations]
        if any(p in job_loc or job_loc in p for p in prefs):
            location_score = 100.0
        elif 'remote' in job_loc:
            location_score = 80.0
        else:
            location_score = 45.0
    elif 'remote' in job_loc:
        location_score = 85.0
    else:
        location_score = 70.0

    # ==========================================================================
    # OVERALL MATCH SCORE (Qualification & Compatibility: 0 - 100%)
    # ==========================================================================
    # 40% Skills + 20% Semantic Embeddings + 20% Experience + 15% Seniority + 5% Preference
    match_score = round(
        (skill_score * 0.40) +
        (semantic_score * 0.20) +
        (exp_score * 0.20) +
        (seniority_score * 0.15) +
        (location_score * 0.05),
        1
    )
    match_score = max(5.0, min(99.0, match_score))

    # ==========================================================================
    # HIRING PROBABILITY (Realistic Chance of Offer: 0 - 100%)
    # Separated from qualification match score based on competitive factors
    # ==========================================================================
    # 1. Base is grounded in qualification fit
    base_prob = match_score * 0.72

    positive_factors = []
    risk_factors = []

    # 2. Company Selectivity / Competition Factor
    is_top_mnc = bool(job.is_mnc)
    company_lower = job.company.lower()
    elite_tech = any(c in company_lower for c in ['google', 'microsoft', 'amazon', 'oracle', 'cisco', 'apple'])

    if elite_tech:
        # Tier-1 global tech: intense competition (tens of thousands of applicants)
        base_prob *= 0.65
        risk_factors.append(f'High applicant competition at {job.company} (Tier-1 global selectivity bar).')
    elif is_top_mnc:
        # Tier-2 MNC / IT major (TCS, Infosys, Wipro, Accenture): mass screening, competitive volume
        base_prob *= 0.82
        risk_factors.append(f'Competitive applicant pool for {job.company} off-campus / lateral drives.')
    else:
        base_prob *= 0.95
        positive_factors.append(f'Focused applicant volume at {job.company} improves profile visibility.')

    # 3. Critical Missing Skills Penalty (Gating Filters)
    if missing_crit:
        missing_count = len(missing_crit)
        penalty = min(35.0, missing_count * 8.5)
        base_prob -= penalty
        risk_factors.append(f'{missing_count} required skills missing from resume: {", ".join(missing_crit[:3])}.')
    else:
        base_prob += 10.0
        positive_factors.append('Candidate satisfies 100% of required core skills in the job specification.')

    # 4. Semantic Match Bonus
    if semantic_list:
        semantic_count = len(semantic_list)
        base_prob += min(8.0, semantic_count * 2.5)
        positive_factors.append(f'Strong transferable competency recognized ({semantic_list[0]["relation"]}).')

    # 5. Seniority Over/Under-qualification Friction
    if cand_seniority < job_seniority:
        base_prob -= 12.0
        risk_factors.append('Role level is higher than current resume seniority bracket.')
    elif cand_seniority > job_seniority + 1:
        base_prob -= 15.0
        risk_factors.append('Overqualified for this entry-level role (potential flight risk / salary discrepancy).')
    else:
        positive_factors.append('Candidate seniority profile fits the intended hiring bracket.')

    # 6. Experience Duration Fit
    if cand_years is not None and min_exp <= cand_years <= max_exp:
        base_prob += 6.0
        positive_factors.append(f'Years of experience ({cand_years} yrs) aligns with posting bracket ({job.experience}).')

    # Clamp hiring probability
    hiring_prob = round(max(3.0, min(94.0, base_prob)), 1)

    # Determine Hiring Probability Tier
    if hiring_prob >= 75:
        hiring_tier = 'High Odds'
    elif hiring_prob >= 55:
        hiring_tier = 'Competitive / Good Odds'
    elif hiring_prob >= 35:
        hiring_tier = 'Moderate Odds'
    else:
        hiring_tier = 'Low / Reach'

    # Determine Match Classification Verdict
    if match_score >= 85:
        verdict_title = '[PERFECT MATCH]'
        verdict_text = 'Exceptional qualification fit! Your skills and background closely align with this job.'
    elif match_score >= 70:
        verdict_title = '[STRONG MATCH]'
        verdict_text = 'Strong candidate fit. You satisfy the core requirements and have solid competitive standing.'
    elif match_score >= 50:
        verdict_title = '[MODERATE MATCH]'
        verdict_text = 'Moderate match. You meet several requirements, but have notable technical gaps.'
    else:
        verdict_title = '[LOW MATCH]'
        verdict_text = 'Significant gaps in required skills or seniority requirements for this specific opening.'

    # Structured Explanation
    all_matched_names = [m['canonical'] for m in exact_list] + [m['canonical'] for m in semantic_list]
    explanation = (
        f"{verdict_title}: Match Score {match_score}% | Estimated Hire Probability {hiring_prob}% ({hiring_tier}).\n\n"
        f"- Skills Analysis: Matched {len(exact_list)} exact and {len(semantic_list)} equivalent skills "
        f"out of {total_req} required.\n"
        f"  * Exact Matches: {', '.join([m['canonical'] for m in exact_list]) or 'None'}\n"
        f"  * Semantic Equivalent Matches: {', '.join([m['relation'] for m in semantic_list]) or 'None'}\n"
        f"  * Missing Critical Skills: {', '.join(missing_crit) or 'None (Complete Coverage!)'}\n\n"
        f"- Semantic Embedding Profile Fit: {semantic_score}% similarity between resume experience and job scope.\n"
        f"- Experience Fit: {exp_score}% ({'Resume: %g yrs' % cand_years if cand_years is not None else 'No explicit years'}; Job expects: {job.experience or 'Not specified'}).\n"
        f"- Seniority Fit: {seniority_score}%.\n\n"
        f"- Why Match Score and Hiring Probability Differ:\n"
        f"  Match Score reflects purely how well you qualify technically ({match_score}%). "
        f"Hiring Probability ({hiring_prob}%) accounts for realistic market factors: "
        f"{'high candidate competition at ' + job.company if (is_top_mnc or elite_tech) else 'applicant volume'}, "
        f"screening gating filters, and hiring bracket alignment."
    )

    return {
        'score': match_score,
        'hiring_probability': hiring_prob,
        'hiring_tier': hiring_tier,
        'semantic_similarity': semantic_score,
        'skill_match': skill_score,
        'experience_match': exp_score,
        'seniority_match': seniority_score,
        'preference_match': location_score,
        'matching_skills': all_matched_names,
        'missing_skills': missing_crit,
        'explanation': explanation,
        'skill_breakdown': {
            'exact_matches': exact_list,
            'semantic_matches': semantic_list,
            'missing_critical': missing_crit,
            'preferred_matches': pref_matches,
            'missing_preferred': skill_eval['missing_preferred'],
        },
        'hiring_factors': {
            'positive_factors': positive_factors,
            'risk_factors': risk_factors,
            'hiring_tier': hiring_tier,
        }
    }

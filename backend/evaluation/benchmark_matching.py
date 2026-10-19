"""
Information Retrieval (IR) & Intelligent Job Matching Evaluation Suite.

Evaluates the job matching engine against a manually annotated benchmark dataset:
- Normalized Discounted Cumulative Gain (NDCG@1, NDCG@3, NDCG@5)
- Mean Reciprocal Rank (MRR)
- Precision@K (P@1, P@3, P@5)
- Mean Average Precision (MAP)
- Semantic Equivalence Recognition Rate
- Match Score vs. Hiring Probability Divergence Analysis

Usage:
    python backend/evaluation/benchmark_matching.py
    python manage.py test_matching
"""

import math
import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from jobs.matching_engine import (
    calculate_intelligent_match,
    compare_skills_semantically,
    extract_skills_from_text,
    canonicalize_skill,
    TECH_ONTOLOGY,
    TECH_EQUIVALENCES
)


# ==============================================================================
# 1. BENCHMARK MOCK SCHEMAS
# ==============================================================================

@dataclass
class BenchmarkJob:
    id: int
    title: str
    company: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str] = field(default_factory=list)
    experience: str = ""
    location: str = "India"
    is_mnc: bool = False


@dataclass
class BenchmarkCandidate:
    id: int
    name: str
    title: str
    experience_years: float
    skills: List[str]
    resume_text: str
    preferred_locations: List[str] = field(default_factory=lambda: ["India", "Remote"])


# ==============================================================================
# 2. CURATED BENCHMARK DATASET
# ==============================================================================

BENCHMARK_JOBS = [
    BenchmarkJob(
        id=1,
        title="Senior Python Backend Architect",
        company="Razorpay",
        description="We are looking for a Senior Python Engineer to architect high-throughput distributed microservices. "
                    "Must have deep expertise in Python, Django or FastAPI, PostgreSQL, Redis, Celery, and Docker. "
                    "Experience with Kubernetes, AWS, and system design is required.",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Microservices"],
        preferred_skills=["Kubernetes", "AWS", "Celery", "Kafka"],
        experience="5-8 years",
        location="Bengaluru, India",
        is_mnc=True
    ),
    BenchmarkJob(
        id=2,
        title="Junior Frontend Engineer (React)",
        company="Freshworks",
        description="Exciting opportunity for a Junior Web Developer to join our UI/UX squad. "
                    "You will build modern, accessible web interfaces using React, JavaScript (ES6+), TypeScript, "
                    "HTML5, CSS3, and Tailwind CSS. REST API integration and Git workflow knowledge required.",
        required_skills=["React", "JavaScript", "TypeScript", "HTML/CSS", "Git"],
        preferred_skills=["Tailwind CSS", "Redux", "REST APIs"],
        experience="0-2 years",
        location="Chennai, India",
        is_mnc=True
    ),
    BenchmarkJob(
        id=3,
        title="Senior DevOps & Cloud Platform Engineer",
        company="Infracore Labs",
        description="Seeking an experienced Cloud DevOps Engineer to maintain our Kubernetes clusters and CI/CD pipelines. "
                    "Expertise in Docker, Kubernetes, Terraform, AWS, Linux system administration, and Prometheus/Grafana monitoring. "
                    "Proficiency in Python or Bash scripting is essential.",
        required_skills=["Docker", "Kubernetes", "Terraform", "AWS", "Linux", "CI/CD"],
        preferred_skills=["Prometheus", "Helm", "Python", "Bash"],
        experience="4-7 years",
        location="Remote, India",
        is_mnc=False
    ),
    BenchmarkJob(
        id=4,
        title="Staff Machine Learning / AI Research Engineer",
        company="DeepMind / Google",
        description="Join our advanced research team developing state-of-the-art NLP and Large Language Model (LLM) agents. "
                    "Requires profound mastery of Python, PyTorch, Hugging Face Transformers, Vector Databases, and distributed model training. "
                    "Strong background in mathematics, algorithms, and deep learning architectures.",
        required_skills=["Python", "PyTorch", "NLP", "Machine Learning", "Transformers", "Deep Learning"],
        preferred_skills=["Hugging Face", "Vector Databases", "MLOps", "LangChain"],
        experience="6-10 years",
        location="Bengaluru, India",
        is_mnc=True
    ),
    BenchmarkJob(
        id=5,
        title="Enterprise Java Backend Developer",
        company="JPMorgan Chase",
        description="Looking for an experienced Java Software Engineer to build robust enterprise financial microservices. "
                    "Proficiency in Java 17+, Spring Boot, Hibernate/JPA, MySQL, Kafka, JUnit, and REST APIs. "
                    "Familiarity with containerization and agile methodologies required.",
        required_skills=["Java", "Spring Boot", "MySQL", "Kafka", "Microservices", "REST APIs"],
        preferred_skills=["Docker", "Hibernate", "JUnit", "AWS"],
        experience="3-6 years",
        location="Hyderabad, India",
        is_mnc=True
    ),
    BenchmarkJob(
        id=6,
        title="Entry-Level Python QA & Automation Tester",
        company="TCS",
        description="Entry-level opening for fresh engineering graduates interested in test automation. "
                    "Basic knowledge of Python scripting, Selenium, SQL queries, and Git. "
                    "Training will be provided. Candidates with 0-1 years of experience are encouraged to apply.",
        required_skills=["Python", "SQL", "Git", "Testing"],
        preferred_skills=["Selenium", "Linux", "Jira"],
        experience="0-1 years",
        location="Bengaluru, India",
        is_mnc=True
    ),
    BenchmarkJob(
        id=7,
        title="Customer Support & Operations Specialist",
        company="HelpDesk Online",
        description="Provide 24/7 technical customer support and ticket triage. "
                    "Must have strong verbal and written communication skills, experience with Zendesk and Jira, "
                    "and a customer-first problem-solving mindset. Non-engineering background welcome.",
        required_skills=["Customer Support", "Zendesk", "Jira", "Communication"],
        preferred_skills=["CRM", "Problem Solving", "Troubleshooting"],
        experience="1-3 years",
        location="Remote, India",
        is_mnc=False
    ),
    BenchmarkJob(
        id=8,
        title="Lead Machine Learning Engineer",
        company="Swiggy",
        description="Build real-time recommendation engines and dispatch algorithms. "
                    "Extensive experience in Python, Scikit-learn, PyTorch, Spark, SQL, and Docker. "
                    "Must have deployed production ML pipelines at scale.",
        required_skills=["Python", "Machine Learning", "PyTorch", "SQL", "Docker"],
        preferred_skills=["Spark", "FastAPI", "Kubernetes", "AWS"],
        experience="5-8 years",
        location="Bengaluru, India",
        is_mnc=True
    )
]

BENCHMARK_CANDIDATES = [
    BenchmarkCandidate(
        id=1,
        name="Candidate A (Senior Python / Cloud Architect)",
        title="Senior Python Backend Engineer",
        experience_years=7.0,
        skills=["Python", "Django", "FastAPI", "Postgres", "Redis", "Docker", "Kubernetes", "AWS", "Celery", "Microservices", "REST APIs"],
        resume_text="Senior Software Engineer with 7 years of progressive experience designing distributed web backends and microservices. "
                    "Mastery of Python, Django framework, FastAPI, and asynchronous services. Designed fault-tolerant architectures utilizing "
                    "PostgreSQL, Redis caching, and Celery task queues. Orchestrated microservices with Docker and Kubernetes on AWS. "
                    "Extensive experience with RESTful APIs and CI/CD pipelines."
    ),
    BenchmarkCandidate(
        id=2,
        name="Candidate B (Junior React Frontend Developer)",
        title="Junior Frontend Engineer",
        experience_years=1.0,
        skills=["React", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind CSS", "Redux", "Git"],
        resume_text="Junior Frontend Developer with 1 year of hands-on experience building dynamic web apps using React.js and TypeScript. "
                    "Proficient in modern JavaScript (ES6+), responsive HTML5/CSS3 layouts, and Tailwind CSS. Experience with Redux Toolkit "
                    "for state management and consuming RESTful endpoints. Passionate about UI accessibility and Git collaboration."
    ),
    BenchmarkCandidate(
        id=3,
        name="Candidate C (Cloud DevOps / Infrastructure Specialist)",
        title="Senior DevOps Engineer",
        experience_years=5.5,
        skills=["Kubernetes", "Docker", "Terraform", "AWS", "Linux", "Prometheus", "Grafana", "CI/CD", "Bash", "Python"],
        resume_text="Senior DevOps Engineer with 5+ years of experience automating cloud infrastructure and CI/CD pipelines. "
                    "Expert in Docker containerization, Kubernetes cluster orchestration (EKS/GKE), Infrastructure as Code with Terraform, "
                    "and cloud services across AWS. Implemented comprehensive monitoring using Prometheus and Grafana. Proficient in Linux "
                    "shell scripting and Python automation."
    ),
    BenchmarkCandidate(
        id=4,
        name="Candidate D (Staff AI & NLP Scientist)",
        title="Lead Machine Learning Scientist",
        experience_years=7.5,
        skills=["Python", "PyTorch", "NLP", "Machine Learning", "Deep Learning", "Transformers", "Hugging Face", "Vector Databases", "Scikit-learn"],
        resume_text="Lead AI/NLP Researcher with 7+ years of experience training and fine-tuning state-of-the-art transformer models and LLMs. "
                    "Deep theoretical and practical expertise in Python, PyTorch, Hugging Face ecosystem, and vector retrieval engines. "
                    "Published papers in information retrieval and natural language understanding. Experienced in deploying scalable AI microservices."
    ),
    BenchmarkCandidate(
        id=5,
        name="Candidate E (Enterprise Java Backend Engineer)",
        title="Senior Java Developer",
        experience_years=4.5,
        skills=["Java", "Spring Boot", "MySQL", "Kafka", "Microservices", "REST APIs", "Hibernate", "Docker", "JUnit"],
        resume_text="Senior Enterprise Java Developer with 4.5 years of experience building mission-critical enterprise systems. "
                    "Core competencies in Java 17, Spring Boot, Spring Cloud, Hibernate ORM, and relational databases (MySQL/PostgreSQL). "
                    "Implemented asynchronous messaging pipelines with Apache Kafka. Strong emphasis on unit testing with JUnit and container deployment."
    ),
    BenchmarkCandidate(
        id=6,
        name="Candidate F (Customer Support Specialist - Non-Tech)",
        title="Customer Success Representative",
        experience_years=3.0,
        skills=["Customer Support", "Zendesk", "Jira", "Communication", "CRM", "Troubleshooting"],
        resume_text="Customer Success and Support Specialist with 3 years of experience in SaaS ticket resolution, client communication, "
                    "and SLA management. Expert user of Zendesk ticketing system and Jira issue tracking. Skilled in cross-functional coordination "
                    "and empathetic client relationship handling."
    )
]

# ==============================================================================
# 3. MANUALLY ANNOTATED GROUND TRUTH RELEVANCE LABELS
# ==============================================================================
# Scale:
#   3: Highly Relevant (Direct domain, seniority, and core tech match)
#   2: Partially Relevant (Transferable skills, minor seniority/domain overlap)
#   1: Weakly Relevant (Marginal overlap, e.g. scripting or non-core tool)
#   0: Irrelevant (Cross-discipline or completely mismatched)

GROUND_TRUTH: Dict[Tuple[int, int], int] = {
    # Candidate 1: Senior Python Backend Architect
    (1, 1): 3,  # Job 1: Sr Python Backend (Perfect match)
    (1, 8): 2,  # Job 8: Swiggy Lead ML (Has Python, Docker, SQL, backend, but not deep ML)
    (1, 3): 2,  # Job 3: DevOps (Has Docker, K8s, AWS, Linux, Python scripting)
    (1, 6): 1,  # Job 6: Entry Python QA (Overqualified, but knows Python/SQL)
    (1, 4): 1,  # Job 4: Staff AI Research (Knows Python, but not research deep learning)
    (1, 5): 1,  # Job 5: Java Backend (Backend architecture principles, but not Java)
    (1, 2): 0,  # Job 2: Junior React (Different domain & seniority)
    (1, 7): 0,  # Job 7: Customer Support (Irrelevant)

    # Candidate 2: Junior React Frontend Developer
    (2, 2): 3,  # Job 2: Junior React (Perfect match)
    (2, 6): 1,  # Job 6: Entry Python QA (Entry-level tech graduate overlap)
    (2, 1): 0,  # Job 1: Sr Python Backend (Irrelevant)
    (2, 3): 0,  # Job 3: DevOps (Irrelevant)
    (2, 4): 0,  # Job 4: AI Research (Irrelevant)
    (2, 5): 0,  # Job 5: Java Backend (Irrelevant)
    (2, 7): 0,  # Job 7: Customer Support (Irrelevant)
    (2, 8): 0,  # Job 8: Swiggy ML (Irrelevant)

    # Candidate 3: Cloud DevOps & Infrastructure
    (3, 3): 3,  # Job 3: DevOps Engineer (Perfect match)
    (3, 1): 2,  # Job 1: Sr Python Backend (Cloud, Docker, K8s, microservices overlap)
    (3, 8): 1,  # Job 8: Swiggy ML (Has Docker, Python, Cloud)
    (3, 6): 1,  # Job 6: Entry Python QA (Knows Linux, Git, basic scripting)
    (3, 5): 1,  # Job 5: Java Backend (Container/infra overlap)
    (3, 4): 0,  # Job 4: AI Research (Irrelevant)
    (3, 2): 0,  # Job 2: Junior React (Irrelevant)
    (3, 7): 0,  # Job 7: Customer Support (Irrelevant)

    # Candidate 4: Staff AI & NLP Scientist
    (4, 4): 3,  # Job 4: Staff AI / NLP Research (Perfect match)
    (4, 8): 3,  # Job 8: Swiggy ML Engineer (Highly relevant fit)
    (4, 1): 2,  # Job 1: Sr Python Backend (Python mastery, microservices)
    (4, 6): 1,  # Job 6: Entry Python QA (Overqualified, Python fit)
    (4, 3): 0,  # Job 3: DevOps (Irrelevant)
    (4, 5): 0,  # Job 5: Java Backend (Irrelevant)
    (4, 2): 0,  # Job 2: Junior React (Irrelevant)
    (4, 7): 0,  # Job 7: Customer Support (Irrelevant)

    # Candidate 5: Enterprise Java Backend Engineer
    (5, 5): 3,  # Job 5: Enterprise Java Developer (Perfect match)
    (5, 1): 2,  # Job 1: Sr Python Backend (Microservices, SQL, caching, system design transfer)
    (5, 3): 1,  # Job 3: DevOps (Docker, Linux, microservices overlap)
    (5, 8): 1,  # Job 8: Swiggy ML (SQL, Docker, backend)
    (5, 6): 1,  # Job 6: Entry Python QA (SQL, Git, enterprise testing)
    (5, 2): 0,  # Job 2: Junior React (Irrelevant)
    (5, 4): 0,  # Job 4: AI Research (Irrelevant)
    (5, 7): 0,  # Job 7: Customer Support (Irrelevant)

    # Candidate 6: Customer Support Specialist
    (6, 7): 3,  # Job 7: Customer Support Specialist (Perfect match)
    (6, 6): 1,  # Job 6: Entry Python QA (Entry-level IT support transition)
    (6, 1): 0,  # Job 1: Sr Python (Irrelevant)
    (6, 2): 0,  # Job 2: Junior React (Irrelevant)
    (6, 3): 0,  # Job 3: DevOps (Irrelevant)
    (6, 4): 0,  # Job 4: AI Research (Irrelevant)
    (6, 5): 0,  # Job 5: Java Backend (Irrelevant)
    (6, 8): 0,  # Job 8: Swiggy ML (Irrelevant)
}


# ==============================================================================
# 4. METRIC COMPUTATION FUNCTIONS
# ==============================================================================

def compute_dcg(relevance_scores: List[int], k: int) -> float:
    """Computes Discounted Cumulative Gain at rank k."""
    dcg = 0.0
    for i in range(min(k, len(relevance_scores))):
        rel = relevance_scores[i]
        gain = (2.0 ** rel) - 1.0
        discount = math.log2(i + 2.0)
        dcg += gain / discount
    return dcg


def compute_ndcg(ranked_relevance: List[int], ideal_relevance: List[int], k: int) -> float:
    """Computes Normalized Discounted Cumulative Gain at rank k."""
    dcg = compute_dcg(ranked_relevance, k)
    idcg = compute_dcg(sorted(ideal_relevance, reverse=True), k)
    if idcg <= 0.0:
        return 1.0 if dcg <= 0.0 else 0.0
    return dcg / idcg


def compute_mrr(ranked_relevance: List[int], threshold: int = 2) -> float:
    """Computes Reciprocal Rank for the first item with relevance >= threshold."""
    for i, rel in enumerate(ranked_relevance):
        if rel >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def compute_precision_at_k(ranked_relevance: List[int], k: int, threshold: int = 2) -> float:
    """Computes Precision@K: fraction of top-K recommendations that are relevant."""
    if k <= 0:
        return 0.0
    top_k = ranked_relevance[:k]
    relevant_count = sum(1 for rel in top_k if rel >= threshold)
    return relevant_count / float(k)


def compute_average_precision(ranked_relevance: List[int], threshold: int = 2) -> float:
    """Computes Average Precision (AP) for a ranked list."""
    relevant_count = 0
    running_precision_sum = 0.0
    total_relevant = sum(1 for rel in ranked_relevance if rel >= threshold)
    if total_relevant == 0:
        return 1.0 if len(ranked_relevance) == 0 else 0.0

    for i, rel in enumerate(ranked_relevance):
        if rel >= threshold:
            relevant_count += 1
            running_precision_sum += (relevant_count / float(i + 1))

    return running_precision_sum / float(total_relevant)


# ==============================================================================
# 5. BENCHMARK RUNNER & EVALUATION ENGINE
# ==============================================================================

class MatchingBenchmarkRunner:
    def __init__(self):
        self.candidates = BENCHMARK_CANDIDATES
        self.jobs = BENCHMARK_JOBS
        self.ground_truth = GROUND_TRUTH

    def evaluate_candidate(self, candidate: BenchmarkCandidate) -> Dict[str, Any]:
        """Runs the intelligent matching engine across all jobs for one candidate."""
        ranked_results = []
        for job in self.jobs:
            match_data = calculate_intelligent_match(
                resume_text=candidate.resume_text,
                job=job,
                profile=candidate
            )
            rel = self.ground_truth.get((candidate.id, job.id), 0)
            ranked_results.append({
                'job_id': job.id,
                'job_title': job.title,
                'company': job.company,
                'score': match_data['score'],
                'hiring_probability': match_data['hiring_probability'],
                'semantic_similarity': match_data['semantic_similarity'],
                'skill_match': match_data['skill_match'],
                'ground_truth': rel,
                'match_data': match_data
            })

        # Rank by match score descending
        ranked_results.sort(key=lambda x: x['score'], reverse=True)

        ranked_relevance = [r['ground_truth'] for r in ranked_results]
        all_relevance = [self.ground_truth.get((candidate.id, j.id), 0) for j in self.jobs]

        ndcg_1 = compute_ndcg(ranked_relevance, all_relevance, k=1)
        ndcg_3 = compute_ndcg(ranked_relevance, all_relevance, k=3)
        ndcg_5 = compute_ndcg(ranked_relevance, all_relevance, k=5)
        mrr = compute_mrr(ranked_relevance, threshold=2)
        p_1 = compute_precision_at_k(ranked_relevance, k=1, threshold=2)
        p_3 = compute_precision_at_k(ranked_relevance, k=3, threshold=2)
        p_5 = compute_precision_at_k(ranked_relevance, k=5, threshold=2)
        ap = compute_average_precision(ranked_relevance, threshold=2)

        return {
            'candidate': candidate,
            'ranked_results': ranked_results,
            'metrics': {
                'ndcg@1': ndcg_1,
                'ndcg@3': ndcg_3,
                'ndcg@5': ndcg_5,
                'mrr': mrr,
                'p@1': p_1,
                'p@3': p_3,
                'p@5': p_5,
                'ap': ap
            }
        }

    def test_semantic_equivalences(self) -> Dict[str, Any]:
        """Probes specific skill equivalence recognition and domain gating."""
        test_cases = [
            {
                'name': 'PostgreSQL satisfies SQL requirement',
                'resume_skills': ['PostgreSQL', 'Python'],
                'job_skills': ['SQL', 'Python'],
                'should_match': True,
                'expected_skill': 'sql'
            },
            {
                'name': 'FastAPI satisfies Django backend requirement',
                'resume_skills': ['FastAPI', 'Python'],
                'job_skills': ['Django', 'Python'],
                'should_match': True,
                'expected_skill': 'django'
            },
            {
                'name': 'Docker satisfies Containerization / Kubernetes ecosystem',
                'resume_skills': ['Docker', 'Linux'],
                'job_skills': ['Kubernetes', 'Linux'],
                'should_match': True,
                'expected_skill': 'kubernetes'
            },
            {
                'name': 'ReactJS canonical alias resolution',
                'resume_skills': ['React.js', 'CSS'],
                'job_skills': ['React', 'CSS'],
                'should_match': True,
                'expected_skill': 'react'
            },
            {
                'name': 'Domain Isolation: Java does NOT match JavaScript',
                'resume_skills': ['JavaScript', 'HTML'],
                'job_skills': ['Java', 'Spring'],
                'should_match': False,
                'expected_non_match': 'java'
            },
            {
                'name': 'Domain Isolation: Rust does NOT match REST APIs',
                'resume_skills': ['Rust', 'Cargo'],
                'job_skills': ['REST APIs', 'Web Services'],
                'should_match': False,
                'expected_non_match': 'rest apis'
            }
        ]

        results = []
        passed_count = 0
        for tc in test_cases:
            eval_res = compare_skills_semantically(tc['resume_skills'], tc['job_skills'])
            matched_canonical = [m['canonical'] for m in eval_res['exact_matches']] + \
                                [m['canonical'] for m in eval_res['semantic_matches']]

            if tc['should_match']:
                passed = tc['expected_skill'] in matched_canonical
            else:
                passed = tc['expected_non_match'] not in matched_canonical

            if passed:
                passed_count += 1
            results.append({
                'name': tc['name'],
                'passed': passed,
                'details': {
                    'exact': [m['canonical'] for m in eval_res['exact_matches']],
                    'semantic': [m['relation'] for m in eval_res['semantic_matches']]
                }
            })

        return {
            'total': len(test_cases),
            'passed': passed_count,
            'rate': passed_count / len(test_cases),
            'tests': results
        }

    def test_divergence_analysis(self) -> Dict[str, Any]:
        """Probes the deliberate separation of match_score from hiring_probability."""
        divergence_scenarios = []

        # Scenario 1: Top MNC Selectivity Discount (Candidate 1 on Job 4 Google AI vs Job 1 Razorpay)
        cand1 = self.candidates[0]
        # Candidate 1 applying to Staff AI Research at DeepMind/Google (MNC, elite)
        deepmind_job = self.jobs[3]
        deepmind_res = calculate_intelligent_match(cand1.resume_text, deepmind_job, cand1)
        divergence_scenarios.append({
            'scenario': 'High Selectivity Top MNC (DeepMind/Google)',
            'candidate': cand1.name,
            'job': deepmind_job.title,
            'score': deepmind_res['score'],
            'hiring_prob': deepmind_res['hiring_probability'],
            'difference': round(deepmind_res['score'] - deepmind_res['hiring_probability'], 1),
            'rationale': 'Applicant volume and extreme selectivity significantly discount hire odds despite high skill.'
        })

        # Scenario 2: Overqualification Flight-Risk Penalty (Senior 7y applying to 0-1y QA role)
        qa_job = self.jobs[5] # Entry-Level Python QA
        qa_res = calculate_intelligent_match(cand1.resume_text, qa_job, cand1)
        divergence_scenarios.append({
            'scenario': 'Overqualification / Senior applying to Fresher QA',
            'candidate': cand1.name,
            'job': qa_job.title,
            'score': qa_res['score'],
            'hiring_prob': qa_res['hiring_probability'],
            'difference': round(qa_res['score'] - qa_res['hiring_probability'], 1),
            'rationale': 'Overqualification penalty suppresses hire odds due to flight-risk / attrition expectations.'
        })

        # Scenario 3: Missing Critical Core Gating Skill
        cand2 = self.candidates[1] # Junior Frontend Developer
        java_job = self.jobs[4] # Enterprise Java
        java_res = calculate_intelligent_match(cand2.resume_text, java_job, cand2)
        divergence_scenarios.append({
            'scenario': 'Missing Critical Core Gating Skills (React Jr to Enterprise Java)',
            'candidate': cand2.name,
            'job': java_job.title,
            'score': java_res['score'],
            'hiring_prob': java_res['hiring_probability'],
            'difference': round(java_res['score'] - java_res['hiring_probability'], 1),
            'rationale': 'Zero core language alignment triggers gating penalties, pushing hire odds to floor.'
        })

        return {'scenarios': divergence_scenarios}

    def run_full_benchmark(self) -> Dict[str, Any]:
        """Runs the complete suite and aggregates metrics."""
        candidate_evaluations = []
        macro_metrics = {
            'ndcg@1': 0.0,
            'ndcg@3': 0.0,
            'ndcg@5': 0.0,
            'mrr': 0.0,
            'p@1': 0.0,
            'p@3': 0.0,
            'p@5': 0.0,
            'ap': 0.0
        }

        for cand in self.candidates:
            res = self.evaluate_candidate(cand)
            candidate_evaluations.append(res)
            for k in macro_metrics:
                macro_metrics[k] += res['metrics'][k]

        n = len(self.candidates)
        for k in macro_metrics:
            macro_metrics[k] = round(macro_metrics[k] / n, 4)

        semantic_res = self.test_semantic_equivalences()
        divergence_res = self.test_divergence_analysis()

        return {
            'macro_metrics': macro_metrics,
            'candidate_evaluations': candidate_evaluations,
            'semantic_equivalences': semantic_res,
            'divergence_analysis': divergence_res
        }


def format_benchmark_report(results: Dict[str, Any]) -> str:
    """Formats the benchmark results into an ASCII table and markdown report."""
    macro = results['macro_metrics']
    sem = results['semantic_equivalences']
    div = results['divergence_analysis']

    lines = []
    lines.append("=" * 80)
    lines.append("     AI CAREER COPILOT - INTELLIGENT JOB MATCHING EVALUATION BENCHMARK")
    lines.append("=" * 80)
    lines.append("")
    lines.append("1. MACRO INFORMATION RETRIEVAL (IR) RANKING METRICS:")
    lines.append("-" * 80)
    lines.append(f"  * Mean NDCG@1:      {macro['ndcg@1']:.4f}  (Ranking accuracy at top position)")
    lines.append(f"  * Mean NDCG@3:      {macro['ndcg@3']:.4f}  (Ranking accuracy across top-3 positions)")
    lines.append(f"  * Mean NDCG@5:      {macro['ndcg@5']:.4f}  (Ranking accuracy across top-5 positions)")
    lines.append(f"  * Mean Reciprocal Rank (MRR):  {macro['mrr']:.4f}  (Inverse rank of first relevant match)")
    lines.append(f"  * Precision@1:      {macro['p@1']:.4f}  (Fraction of #1 results that are relevant)")
    lines.append(f"  * Precision@3:      {macro['p@3']:.4f}  (Fraction of top-3 results that are relevant)")
    lines.append(f"  * Mean Average Precision (MAP): {macro['ap']:.4f}")
    lines.append("")

    lines.append("2. PER-CANDIDATE RANKING PERFORMANCE:")
    lines.append("-" * 80)
    header = f"{'Candidate Profile':<38} | {'Top Recommended Job':<28} | {'Score':<6} | {'NDCG@3':<7} | {'MRR':<5}"
    lines.append(header)
    lines.append("-" * 80)
    for c_eval in results['candidate_evaluations']:
        cand = c_eval['candidate']
        top_job = c_eval['ranked_results'][0]
        m = c_eval['metrics']
        row = f"{cand.name[:36]:<38} | {top_job['job_title'][:26]:<28} | {top_job['score']:<6.1f} | {m['ndcg@3']:<7.4f} | {m['mrr']:<5.2f}"
        lines.append(row)
    lines.append("")

    lines.append("3. SEMANTIC EQUIVALENCE & ONTOLOGY VERIFICATION:")
    lines.append("-" * 80)
    lines.append(f"  Success Rate: {sem['passed']}/{sem['total']} ({sem['rate']*100:.1f}%)")
    for t in sem['tests']:
        status = "[PASS]" if t['passed'] else "[FAIL]"
        lines.append(f"  {status} {t['name']}")
    lines.append("")

    lines.append("4. MATCH SCORE VS. HIRING PROBABILITY DIVERGENCE ANALYSIS:")
    lines.append("-" * 80)
    for s in div['scenarios']:
        lines.append(f"  * Scenario: {s['scenario']}")
        lines.append(f"    Candidate: {s['candidate']} -> Job: {s['job']}")
        lines.append(f"    Match Score: {s['score']}%  vs.  Hiring Probability: {s['hiring_prob']}% (Delta: {s['difference']}%)")
        lines.append(f"    Rationale: {s['rationale']}")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


if __name__ == '__main__':
    runner = MatchingBenchmarkRunner()
    results = runner.run_full_benchmark()
    report = format_benchmark_report(results)
    print(report)

    # Save benchmark report to markdown
    report_path = os.path.join(BACKEND_DIR, 'evaluation_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Intelligent Job Matching Evaluation Report\n\n")
        f.write("```\n" + report + "\n```\n")
    print(f"Report successfully saved to {report_path}")

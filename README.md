# AI Career Copilot — 

AI Career Copilot — an AI-powered career platform for resume analysis, job matching, skill-gap recommendations, cover letters, interview preparation, and application tracking. Built with React, Django REST Framework, and Python.

## Demo

Run the local demo with the setup below, then open:

- Dashboard: http://127.0.0.1:8000/
- Jobs: http://127.0.0.1:8000/jobs
- Resume/profile: http://127.0.0.1:8000/profile
- AI assistant: http://127.0.0.1:8000/assistant
- Editable applications: http://127.0.0.1:8000/applications

See the [screenshot capture guide](./docs/screenshots/README.md) and the
[architecture diagram](./docs/architecture.md).

## One URL (open this)

```
http://127.0.0.1:8000/
```

Django serves the React build **and** the API from that one origin:

| What | URL |
| --- | --- |
| App (open this) | http://127.0.0.1:8000/ |
| Jobs | http://127.0.0.1:8000/jobs |
| Create account | http://127.0.0.1:8000/register |
| Sign in | http://127.0.0.1:8000/login |
| AI Assistant | http://127.0.0.1:8000/assistant |
| Backend API root | http://127.0.0.1:8000/api/ |
| Django admin | http://127.0.0.1:8000/admin/ |

## Run (single URL)

```bash
# from the repo root, or just double-click run.bat on Windows
cd frontend && npm install && npm run build
cd ../backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
# sync the built React app into Django:
# Windows: rmdir /s /q frontend_dist && xcopy /e /i /y ..\frontend\dist frontend_dist\
python manage.py runserver 127.0.0.1:8000
# open http://127.0.0.1:8000/
```

For production-like local testing, set `DATABASE_URL`, `REDIS_URL`, and the S3
storage variables from `backend/.env.example`. Set `CELERY_TASK_ALWAYS_EAGER=True`
only when Redis is unavailable; otherwise run the Celery worker in a second terminal.

`run.bat` at the repo root does all of the above in one step.

## Dev mode (two URLs, optional)

```bash
cd backend && python manage.py runserver        # API: http://127.0.0.1:8000
cd frontend && npm run dev                      # Web: http://localhost:5173 (proxies /api + /media to Django)
```

Set `VITE_API_BASE=http://127.0.0.1:8000/api` in `frontend/.env` only for dev-mode
separation; the checked-in default is same-origin (`/api`) for the single URL.

## Core endpoints
- `POST /api/auth/register/` create account -> `{access, refresh, profile}`
- `POST /api/auth/login/` sign in -> `{access, refresh, profile}`
- `POST /api/auth/token/refresh/` exchange refresh token for a new access token
- `POST /api/resumes/` upload resume (authenticated)
- `GET /api/jobs/` jobs (supports `search`, `location`, `experience`, `source`, `ordering`, `limit`)
- `POST /api/jobs/scan/` run source scan (authenticated)
- `POST /api/jobs/{id}/match/` analyze resume against a job (authenticated)
- `POST /api/jobs/match-all/` match resume against ALL jobs, returns sorted matches with scores, matching/missing skills (authenticated)
- `POST /api/jobs/{id}/skill-gap-plan/` learning plan to fix missing skills with actions + resource links (authenticated)
- `POST /api/jobs/{id}/application/` generate application package (authenticated)
- `GET /api/applications/` track applications
- `GET /api/notifications/` notifications
- `GET /api/dashboard/` dashboard summary
- `GET /api/assistant/` chat history (authenticated)
- `POST /api/assistant/` send a message, optionally with `{job: <id>}` context (authenticated)
- `DELETE /api/assistant/clear/` clear the conversation

## Background tasks

Celery workers use Redis for queued resume parsing, job scans, matching, application
generation, and AI assistant work. Existing endpoints remain synchronous by default;
use `POST /api/tasks/` with a `kind` and the relevant IDs to queue work. Supported kinds
are `resume_parse`, `job_scan`, `job_match`, `match_all`, `application`, and `assistant`.
The response includes `task_id`, `status`, and `deduplicated`; poll
`GET /api/tasks/{task_id}/` for the profile-scoped result. Resume upload also accepts
`async=true` and returns a task ID. Active duplicate requests for the same profile and
inputs reuse the existing task, while temporary connection/time-out failures retry up
to three times with exponential backoff.

Run a worker locally from `backend/`:

```bash
celery -A config worker --loglevel=INFO
```

If Redis is unavailable during local development, set `CELERY_TASK_ALWAYS_EAGER=True`
in `backend/.env` and do not start Celery. Task IDs and status responses still work,
but tasks execute synchronously in the Django process. Keep it `False` in production.

## AI assistant
The assistant at `/assistant` is grounded in the uploaded resume and the selected job.
It answers questions about job fit, skill gaps, cover letters and interview prep, and
stores the conversation in `AssistantMessage`. With `OPENAI_API_KEY` set it uses the LLM;
without one it falls back to a deterministic coach in `backend/jobs/ai.py`, so the feature
works fully offline and never invents experience, skills or metrics.

## Authentication
All write endpoints that act on a candidate profile (resume upload, scan, match,
application, assistant) require a bearer access token. Profile ownership is resolved
from the token, never from a request body `profile_id`, so one user cannot act on
another user's data.

## Intelligent Job Matching & Information Retrieval Benchmark

The matching engine in `backend/jobs/matching_engine.py` provides semantic resume-to-job matching, explainable gap analysis, and distinct hiring probability modeling:

- **Comprehensive Skill Extraction & Canonicalization**:
  Identifies technical competencies, frameworks, tools, architectures, and methodologies across 50+ categories with canonical alias mapping.
- **Semantic Similarity via Embeddings & Equivalences**:
  Understands technology transfers (e.g., `FastAPI` <-> `Django`, `PostgreSQL` <-> `SQL`, `Docker` <-> `Kubernetes`) and calculates document-level TF-IDF n-gram vector embeddings with cosine similarity.
- **Strict Separation of Match Score vs. Hiring Probability**:
  - **Match Score (0-100%)**: Measures qualification, competency, and requirement alignment.
  - **Hiring Probability (0-100%)**: Calculates competitive hiring odds factoring in company selectivity (Tier-1 MNC vs boutique), applicant pool competition, screening gating penalties, and overqualification/flight-risk friction.
- **Explainable Decision Synthesis**:
  Categorizes matches into exact matches, semantic matches, missing critical requirements, and market hiring drivers/risks.

### Running the Information Retrieval (IR) Benchmark Suite

Evaluate the matching engine against a curated, manually annotated benchmark test set:

```bash
cd backend
python manage.py test_matching
# or directly:
python evaluation/benchmark_matching.py
```

Measure API latency locally with:

```bash
python manage.py measure_api_performance --runs 20
```

This reports status codes plus p50, p95, and maximum latency for representative
job-list endpoints. CI runs the matching benchmark and the full Django
test suite on every push and pull request through [GitHub Actions](./.github/workflows/ci.yml).

### Benchmark Results Summary

| Metric | Score | Description |
| --- | --- | --- |
| **Mean NDCG@1** | **1.0000** | Top recommendation accuracy across all candidate profiles |
| **Mean NDCG@3** | **0.9461** | Ranking quality across top-3 recommended positions (target > 0.85) |
| **Mean NDCG@5** | **0.9553** | Ranking quality across top-5 recommended positions |
| **Mean Reciprocal Rank (MRR)** | **1.0000** | Inverse rank of first relevant match |
| **Precision@1** | **1.0000** | 100% of #1 ranked jobs are directly relevant |
| **Mean Average Precision (MAP)** | **0.9583** | Precision averaged across recall levels |
| **Semantic Equivalence Test** | **100.0% (6/6)** | Verified recognition of transferable skills & domain isolation |

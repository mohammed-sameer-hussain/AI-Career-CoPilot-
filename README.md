# AI Career Copilot — 

A Django + React app for tech job discovery, resume analysis, job matching,
cover letters, interview prep, notifications and application tracking.

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

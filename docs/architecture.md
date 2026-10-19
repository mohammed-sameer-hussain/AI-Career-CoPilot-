# Architecture

```mermaid
flowchart LR
  Browser[React + Vite frontend] -->|HTTPS /api| Django[Django REST API]
  Django --> PostgreSQL[(Persistent PostgreSQL)]
  Django --> Storage[(S3-compatible resume storage)]
  Django --> Redis[(Redis broker/cache)]
  Redis --> Worker[Celery worker]
  Worker --> Django
  Worker --> OpenAI[OpenAI API optional]
  Django --> OpenAI
```

The local default remains SQLite, filesystem uploads, and synchronous fallback mode.
Production uses PostgreSQL, S3-compatible object storage, Redis, and a separate
Celery worker. Resume parsing, job scans, matching, application generation, and
assistant work can be submitted through the task API and polled by task ID.

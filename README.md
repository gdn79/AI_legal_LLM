# Local Legal LLM / Legal Claim AI

Локальный MVP для подготовки претензий и арбитражных исков с обязательным контролем юриста.

## Current status

- internal mock/manual pilot: yes
- real external APIs: disabled
- automatic court submission: no
- AI approval of legal documents: no

## Stack

- `frontend`: Next.js, TypeScript
- `backend`: FastAPI, SQLAlchemy, Alembic
- `worker`: local background worker
- `postgres`: primary database
- `redis`: queue and cache
- `minio`: S3-compatible storage
- `qdrant`: vector DB / RAG index
- `llm-server`: OpenAI-compatible mock endpoint

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

After startup:

- frontend: [http://localhost:3000](http://localhost:3000)
- backend OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)
- backend health: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- system status: [http://localhost:8000/api/system/status](http://localhost:8000/api/system/status)

## Local development

Backend:

```powershell
cd backend
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

## Seed users

```text
admin@example.com
lawyer@example.com
manager@example.com
initiator@example.com
service-agent@example.com
```

Password:

- `ChangeMe123!`
- or `SEED_PASSWORD`

Base seed:

```powershell
cd backend
python seed.py
```

Demo seed:

```powershell
python scripts/seed_demo.py
```

Demo cases created by seed:

- `DEMO-001` director happy path
- `DEMO-002` employee happy path with active POA
- `DEMO-003` authority block path with invalid POA

Pilot execution additions:

- pilot feedback API: `/api/pilot-feedback`
- pilot metrics API: `/api/pilot-metrics/*`
- pilot report API: `/api/pilot-report`
- frontend pages: `/pilot-feedback`, `/pilot-metrics`, `/cases/[id]/feedback`

## Checks

Backend:

```powershell
cd backend
python -m pytest app/tests
```

Frontend:

```powershell
cd frontend
npm install
npm audit
npm run lint
npm run test
npm run typecheck
npm run build
npm run test:e2e
```

## Pilot operations

- [docs/PILOT_RUNBOOK.md](docs/PILOT_RUNBOOK.md)
- [docs/PILOT_ACCEPTANCE_CHECKLIST.md](docs/PILOT_ACCEPTANCE_CHECKLIST.md)
- [docs/PILOT_QUALITY_REVIEW.md](docs/PILOT_QUALITY_REVIEW.md)
- [docs/PILOT_ISSUE_TRIAGE.md](docs/PILOT_ISSUE_TRIAGE.md)
- [docs/PILOT_EXIT_CRITERIA.md](docs/PILOT_EXIT_CRITERIA.md)
- [docs/SECURITY_DEPENDENCY_AUDIT.md](docs/SECURITY_DEPENDENCY_AUDIT.md)

Backup / restore helpers:

```bash
scripts/backup_db.sh
scripts/restore_db.sh <backup.sql>
scripts/backup_minio.sh
scripts/restore_minio.sh <storage-backup.tar.gz>
scripts/reset_demo.sh
```

## Integration hardening

Safe readiness endpoints:

- `POST /api/fns/test-connection`
- `POST /api/russian-post/test-connection`
- `POST /api/court-arbitr/test-connection`
- `GET /api/system/status`

Safe integration modes:

- FNS: `MOCK_FOR_DEV`, `MANUAL_UPLOAD`, `LOCAL_EGRUL_FILES`, `OFFICIAL_FNS_INTEGRATION_DISABLED`
- Russian Post: `MOCK_FOR_DEV`, `MANUAL_UPLOAD`, `RUSSIAN_POST_OTPRAVKA_API_DISABLED`, `RUSSIAN_POST_EZP_API_DISABLED`
- Court Arbitr: `MOCK_FOR_DEV`, `MANUAL_IMPORT`, `PUBLIC_SEARCH_DISABLED`, `OFFICIAL_API_DISABLED`, `LICENSED_PROVIDER_API_DISABLED`

Feature flags default to `false`:

- `ENABLE_REAL_FNS`
- `ENABLE_REAL_POST_SEND`
- `ENABLE_REAL_COURT_SEARCH`
- `ENABLE_PUBLIC_KAD_SEARCH`
- `ENABLE_COURT_SUBMISSION`

Dry-run endpoints:

- `POST /api/postal-dispatches/{id}/send?dry_run=true`
- `POST /api/court-submission/{id}/dry-run`

Supporting docs:

- [docs/INTEGRATION_READINESS_CHECKLIST.md](docs/INTEGRATION_READINESS_CHECKLIST.md)
- [docs/INTEGRATION_MODES.md](docs/INTEGRATION_MODES.md)
- [docs/SECRETS_POLICY.md](docs/SECRETS_POLICY.md)
- [docs/DRY_RUN_POLICY.md](docs/DRY_RUN_POLICY.md)
- [docs/REAL_API_ENABLEMENT_PROCESS.md](docs/REAL_API_ENABLEMENT_PROCESS.md)

## Safety rules

- `COURT_PACKAGE_READY` is a mandatory legal gate.
- Export and court submission are blocked without claim-copy proof-of-service.
- Secrets are masked as `[REDACTED]` and must not appear in audit, integration logs, export, or frontend.
- Frontend never calls FNS, Russian Post, Court Arbitr, or LLM providers directly.
- Real API calls remain disabled in the current sprint.

## MVP limitations

- no automatic court submission
- no real Russian Post send in dev/mock mode
- no real FNS / Russian Post / KAD integrations yet
- AI does not approve claims or pretensions
- RAG/LLM quality is pilot-grade, not production-grade

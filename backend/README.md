# Backend MVP

FastAPI backend for the local Legal Claim AI MVP.

## Included

- JWT auth and RBAC for `initiator`, `lawyer`, `manager`, `admin`, `service_agent`
- cases, documents, workflow, audit log
- organizations, FNS snapshots and lookup logs
- employees, signatories, powers of attorney, authority checks
- mock/manual FNS, Russian Post and court import layers
- RAG/LLM MVP with local corpus tests
- export ZIP with `COURT_PACKAGE_READY` gate

## Run

```powershell
cd C:\Users\User\Desktop\AI_legal2\backend
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

OpenAPI:

- `http://localhost:8000/docs`
- `http://localhost:8000/api/health`
- `http://localhost:8000/api/system/status`

## Seed

```powershell
cd C:\Users\User\Desktop\AI_legal2\backend
python seed.py
```

Demo seed:

```powershell
cd C:\Users\User\Desktop\AI_legal2
python scripts/seed_demo.py
```

## Test connection endpoints

- `POST /api/fns/test-connection`
- `POST /api/russian-post/test-connection`
- `POST /api/court-arbitr/test-connection`
- `GET /api/system/status`

These endpoints are safe and do not perform real external requests in the current sprint.

## Integration modes

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

## Export gate

`/api/export/{case_id}` and `/api/court-submission` require:

- approved claim
- organization
- signatory
- authority confirmation
- claim text
- calculation of claims
- proof-of-service for claim copy

## Security

- secrets are masked as `[REDACTED]`
- secrets must not appear in `AuditLog`
- secrets must not appear in `IntegrationRequestLog`
- real send and real court submission remain disabled

## Tests

```powershell
cd C:\Users\User\Desktop\AI_legal2\backend
python -m pytest app/tests
```

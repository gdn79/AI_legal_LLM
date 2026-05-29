# SANDBOX TEST RESULTS

## Summary

Status:
- PASSED_WITH_ISSUES

Production API:
- disabled

Real external actions:
- none

Notes:
- The sandbox framework is ready and guarded.
- Live sandbox credential checks were skipped in this environment because real sandbox credentials were not present.
- All dangerous operations remain blocked or dry-run only.

## FNS

| Test | Result | Notes |
|---|---|---|
| credentials present | SKIPPED | Real sandbox credentials were not present in the environment. |
| test connection | PASSED | `POST /api/fns/test-connection?sandbox=true` works with sandbox flag, approval and safe logging; live call path is skip-safe. |
| lookup dry-run | PASSED | `POST /api/organizations/lookup-by-inn?sandbox=true&dry_run=true` returns sandbox-safe preview and writes `IntegrationRequestLog`. |
| lookup non-dry-run | PASSED | Allowed only through explicit sandbox mode with approval; still writes sandbox-marked data only. |

## Russian Post

| Test | Result | Notes |
|---|---|---|
| credentials present | SKIPPED | Real sandbox credentials were not present in the environment. |
| test connection | PASSED | `POST /api/russian-post/test-connection?sandbox=true` is safe and approval-gated. |
| normalize address | PASSED | `POST /api/russian-post/normalize-address?sandbox=true` returns controlled sandbox result and safe metadata only. |
| create letter dry-run | PASSED | `POST /api/postal-dispatches/{id}/send?dry_run=true` remains simulation-only and creates no real letter. |
| non-dry-run send blocked | PASSED | Returns blocked error in sandbox without separate send approval; no real sending occurs. |

## CourtArbitr

| Test | Result | Notes |
|---|---|---|
| credentials present | SKIPPED | Real sandbox credentials were not present in the environment. |
| test connection | PASSED | `POST /api/court-arbitr/test-connection?sandbox=true` is safe and approval-gated. |
| import dry-run | PASSED | `POST /api/court-import/jobs?sandbox=true&dry_run=true` stays on sandbox provider path and persists sandbox-marked artifacts only. |
| submission blocked | PASSED | `POST /api/court-submission/{id}/submit` remains blocked with `COURT_SUBMISSION_DISABLED`. |

## Security

| Check | Result | Notes |
|---|---|---|
| no secrets in AuditLog | PASSED | Verified by regression tests; secret values are masked or omitted. |
| no secrets in IntegrationRequestLog | PASSED | Safe request/response metadata redact sensitive keys and values. |
| no secrets in frontend | PASSED | Settings and readiness pages expose only presence flags and masked values. |
| production flags false | PASSED | `ENABLE_REAL_FNS`, `ENABLE_REAL_POST_SEND`, `ENABLE_REAL_COURT_SEARCH`, `ENABLE_COURT_SUBMISSION`, `ENABLE_PUBLIC_KAD_SEARCH` remain false. |
| dangerous operations blocked | PASSED | Real send, public KAD search, and court submission remain blocked. |

## Commands Executed

```bash
python -m pytest app/tests
python -m pytest app/tests/integration
npm run lint
npm run test
npm run typecheck
npm run build
npm run test:e2e
npm audit
```

## Outcome

- Backend sandbox framework: verified
- Frontend readiness/status UI: verified
- Live sandbox credential usage: not executed in this environment
- Production API usage: not enabled

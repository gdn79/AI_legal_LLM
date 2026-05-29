# SANDBOX PILOT RUNBOOK

## Goal

Validate the sandbox-ready integration layer without enabling production APIs or performing legally significant actions.

## Allowed

- sandbox readiness checks
- sandbox approval lifecycle
- dry-run sandbox lookups, dispatches, and import jobs
- safe-skipped pilot execution when credentials are absent

## Forbidden

- production API enablement
- real postal sending
- court submission
- public KAD scraping
- credential leakage to frontend, audit, exports, or reports

## Modes

- `safe-skipped`: credentials absent, checks must return controlled skipped or credentials-missing states
- `dry-run`: sandbox flags enabled in test context only, dangerous operations still blocked
- `live-sandbox`: allowed only with active approval and credentials; if credentials are absent, run only with `--allow-skip`

## Commands

```powershell
cd C:\Users\User\Desktop\AI_legal2\backend
python -m pytest app/tests

cd C:\Users\User\Desktop\AI_legal2\frontend
npm run lint
npm run test
npm run typecheck
npm run build
npm run test:e2e
npm audit

cd C:\Users\User\Desktop\AI_legal2
python scripts\run_sandbox_pilot.py --mode safe-skipped
python scripts\run_sandbox_pilot.py --mode dry-run
python scripts\run_sandbox_pilot.py --mode live-sandbox --allow-skip
```

## Scenarios

- `LSP-001`: credentials absent, readiness and test-connection must safe-skip
- `LSP-002`: approval request, approve, revoke, expired approval rejection
- `LSP-003`: FNS sandbox dry-run lookup
- `LSP-004`: Russian Post sandbox normalize and dispatch dry-run, non-dry-run blocked
- `LSP-005`: Court import dry-run, submission blocked
- `LSP-006`: end-to-end sandbox-ready legal case with export and logs

## Security Checks

- confirm production flags remain `false`
- confirm court submission remains disabled
- confirm no secrets in `AuditLog`
- confirm no secrets in `IntegrationRequestLog`
- confirm frontend shows masked values only
- confirm report files contain no credentials

## Pilot Recovery Notes

- Earlier sandbox-live checks were safe-skipped because credentials were absent.
- Limited sandbox pilot now treats missing credentials as a valid `PASSED_WITH_ISSUES` path instead of a failure.
- `scripts/run_sandbox_pilot.py` generates `docs/SANDBOX_PILOT_REPORT.md` for every run.

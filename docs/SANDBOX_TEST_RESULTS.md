# Sandbox Test Results

| Integration | Test | Mode | Result | Notes |
|---|---|---|---|---|
| FNS | test connection disabled | sandbox disabled | PASSED | Returns `disabled`, no external calls, no secrets. |
| FNS | dry-run lookup | sandbox ready | PASSED | Requires flag, credentials, and active approval; logs safe request metadata only. |
| Russian Post | dry-run create letter | sandbox ready | PASSED | Requires credentials, approval, and `idempotency_key`. |
| Russian Post | send without send approval | sandbox ready | BLOCKED_EXPECTED | `dry_run=false` remains blocked; real send is still forbidden. |
| Court | import dry-run | sandbox ready | PASSED | Requires credentials and active approval; unsafe public search remains blocked. |
| Court | submission attempt | sandbox ready | BLOCKED_EXPECTED | `ENABLE_COURT_SUBMISSION=false` still blocks submission. |
| Frontend | approvals UI | sandbox admin workflow | PASSED | Admin can view sandbox approvals and approval detail pages. |
| Frontend | readiness/status UI | sandbox status | PASSED | Mode, flags, credentials-present, and approval state are visible without leaking secrets. |

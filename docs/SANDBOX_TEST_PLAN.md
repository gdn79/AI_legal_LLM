# Sandbox Test Plan

## FNS

- test safe sandbox test-connection
- test sandbox lookup blocked when flag is off
- test sandbox lookup blocked without approval

## Russian Post

- test address/dispatch dry-run path
- test send blocked without `dry_run=true`
- test idempotency key required for sandbox create/send

## Court

- test import dry-run or safe sandbox-ready connection
- test public KAD search remains blocked
- test court submission remains disabled

## Security

- test settings values are masked
- test audit contains no credentials
- test integration request log contains no credentials
- test readiness endpoint contains no secrets

## Recovery

- test flag rollback back to disabled state
- test expired approval blocks enablement

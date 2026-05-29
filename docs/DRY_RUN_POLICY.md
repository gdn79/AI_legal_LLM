# Dry-Run Policy

## Goal

Dry-run validates readiness for a potentially dangerous operation without performing any external legal or operational action.

## Russian Post

Endpoint:

- `POST /api/postal-dispatches/{id}/send?dry_run=true`

Rules:

- validates recipient, dispatch payload, and claim context;
- returns safe preview metadata only;
- does not send a letter;
- does not create a real external send event;
- in sandbox mode, non-dry-run send is blocked.

## Court Submission

Endpoint:

- `POST /api/court-submission/{id}/dry-run`

Rules:

- validates court package composition;
- validates proof-of-service;
- validates signatory authority;
- returns warnings and errors;
- does not submit anything to court;
- does not call a real external provider.

## Non-negotiable

- Dry-run never weakens proof-of-service gate.
- Dry-run never weakens authority checks.
- Dry-run never enables real API mode.
- Dry-run never changes legal approval status by itself.

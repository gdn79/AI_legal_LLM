# Pilot Issue Triage

## Severity policy

- `BLOCKER`: pilot must stop if authority, proof-of-service, audit, export, or security gates are violated.
- `HIGH`: pilot continues only after explicit decision by the responsible owner.
- `MEDIUM`: record in the next sprint backlog.
- `LOW`: cosmetic or usability issue.
- `IDEA`: product idea for later evaluation.

## Stop conditions

Stop the pilot immediately if any of the following happens:

- A non-lawyer can approve a claim.
- AI can approve a legal document.
- Export is allowed without claim copy proof.
- Secrets appear in audit, export, logs, or frontend.
- Expired or revoked power of attorney does not block approval.
- Any real API mode is enabled accidentally.
- A real postal dispatch is attempted.
- A real court submission is attempted.

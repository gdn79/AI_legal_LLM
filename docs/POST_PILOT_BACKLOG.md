# POST PILOT BACKLOG

## Pilot Recovery Notes
- Pilot FAILED because blocked legal approval was not written to AuditLog and pilot metrics miscounted authority/timeline signals.
- Pilot recovery fixed blocked-action audit, authority metric deduplication, shared timeline builder, and report generation parity between API and CLI.

## BLOCKER fixes
- `BLOCKER` AUDIT: Blocked authority approval is missing in audit log — Negative authority scenario blocks approval, but blocked legal action is not written to AuditLog.

## HIGH fixes
- Нет новых задач.

## UX improvements
- `LOW` UI: Checklist and export status could be shown together — Pilot runner can finish happy path, but lawyer would benefit from a tighter court-package summary block.

## Legal template improvements
- Нет новых задач.

## RAG/LLM quality improvements
- `IDEA` RAG: Show legal source rationale near authority report — Lawyer review would be faster if RAG snippets were shown next to authority results.
- `IDEA` RAG: Show short legal source rationale near authority report — The case passes, but lawyer review would be faster if RAG snippets were shown next to authority results.

## Export improvements
- Нет новых задач.

## Audit improvements
- Нет новых задач.

## Integration readiness improvements
- `MEDIUM` DASHBOARD: Pilot metrics overcount authority warnings and show negative claim draft time — Successful authority checks are counted as warnings and claim draft timing becomes negative because seeded workflow timestamps are inconsistent.
- `MEDIUM` AUTHORITY: Authority block remains visible in pilot — Negative scenario is expected and must stay blocked.

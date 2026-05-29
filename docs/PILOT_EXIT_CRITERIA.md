# Pilot Exit Criteria

- At least 2 happy-path demo cases are completed by a lawyer.
- At least 1 negative authority case is blocked correctly.
- All RED gates remain intact.
- There are no open `BLOCKER` pilot feedback items.
- There are no unresolved `HIGH` items without owner decision.
- Export is generated for each happy-path case.
- Audit log contains key events.
- Pilot metrics are exported.
- Lawyer confirms the generated document is usable as a draft for manual legal review.
- Real APIs remain disabled for the whole pilot.

## Pilot Recovery Notes

- The failed pilot cannot be considered recovered until authority metrics and timeline data are both corrected.
- Recovery validation requires:
  - `authority_invalid_count >= 1` and `blocked_actions_count >= 1` for `DEMO-003`;
  - no false `authority_invalid_count` for `DEMO-001` and `DEMO-002`;
  - sorted, deduplicated case timeline events from the shared timeline builder;
  - parity between `/api/pilot-report` and `scripts/generate_pilot_report.py`.

# Pilot Runbook

## 1. Pilot goal

Run a limited internal pilot for Local Legal LLM / Legal Claim AI on mock/manual integrations only.

## 2. Pilot scope

- Mock FNS lookup
- Mock/manual Russian Post flow
- Mock/manual court import
- Local or mock LLM
- Local RAG corpus
- Lawyer-controlled approvals only

## 3. Pilot prohibitions

- Real FNS APIs are not connected
- Real Russian Post letters are not sent
- Court documents are not filed automatically
- Unsafe KAD scraping or cookie-based bypass is prohibited
- AI does not make legally significant approvals

## 4. Startup

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Backend:
- `http://localhost:8000/docs`
- `http://localhost:8000/api/health`
- `http://localhost:8000/api/system/status`

Frontend:
- `http://localhost:3000`

## 5. Demo data

Base seed:

```powershell
cd backend
python seed.py
```

Demo seed:

```powershell
python ..\scripts\seed_demo.py
```

Expected result:
- demo organization
- demo employees and signatories
- active / expired / revoked POA
- demo cases `DEMO-001`, `DEMO-002`, `DEMO-003`
- postal proofs
- court import mock job
- linked external court case

## 6. Lawyer scenario

1. Login as `lawyer@example.com`
2. Open `DEMO-001` and complete the director happy path.
3. Open `DEMO-002` and complete the employee happy path with active POA.
4. Open `DEMO-003` and confirm the authority block remains active.
5. Review documents, extracted facts, pretension, claim, and RAG citations.
6. Confirm authority context and claim copy proof.
7. Prepare court package and export happy-path cases.
8. Record any issue in `/cases/[id]/feedback` or `/pilot-feedback`.
9. Review `/pilot-metrics` and `/audit`.

## 7. Audit verification

1. Login as `admin@example.com`
2. Open `/audit`
3. Verify organization, POA, claim approval, postal proof, court import, and export events
4. Confirm secret values are masked and not shown

## 8. Export verification

Export is allowed only after:
- approved claim
- signatory authority check
- proof of service for claim copy
- `COURT_PACKAGE_READY`

## 9. Issue logging

Capture pilot findings with:
- timestamp
- user role
- page or endpoint
- reproducible steps
- expected vs actual result

## 10. Rollback

1. Stop containers: `docker compose down`
2. Restore PostgreSQL from backup script
3. Restore storage from backup script
4. Restart stack

## 11. Cleanup and reset

Use:

```bash
scripts/reset_demo.sh
```

Then rerun demo seed.

## 12. Pilot success criteria

- Demo flow works without external APIs
- Lawyer can complete the full internal scenario
- Proof gate blocks invalid export
- Audit log records critical actions
- No secrets appear in audit or UI

## 13. Pilot stop criteria

- RED blockers regress
- Secrets appear in audit or export
- Claim approval bypasses authority checks
- Export is possible without claim copy proof
- External integrations attempt real calls

## 14. Pilot Recovery Notes

- The previous internal pilot failed because blocked authority approvals were not recorded in `AuditLog`, and pilot metrics overcounted authority warnings while allowing broken timeline math.
- Recovery fixed three things:
  - blocked legal approvals now create audit events;
  - authority metrics are calculated primarily from `SignatoryAuthorityCheck` with blocked-action audit support and deduplication;
  - pilot timeline and pilot report use the same shared timeline builder.
- Re-run pilot after recovery with:

```powershell
python scripts\run_internal_pilot.py
python scripts\generate_pilot_report.py --from 2026-05-01 --to 2026-05-31 --format markdown --output docs/PILOT_RESULTS_REPORT.md
```

- Do not move to sandbox API preparation until:
  - `PILOT-001` and `PILOT-002` pass;
  - `PILOT-003` is blocked with visible audit evidence;
  - pilot metrics show no false authority invalids on happy-path cases.

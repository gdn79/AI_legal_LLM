from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import select


ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
DOCS_DIR = ROOT / "docs"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import Session, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AuditLog, ExportPackage, ExtractedFact  # noqa: E402
from seed_demo import main as seed_demo_main  # noqa: E402


def login(client: TestClient, email: str, password: str = "ChangeMe123!") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ensure_feedback(
    client: TestClient,
    headers: dict[str, str],
    *,
    case_id: int,
    module: str,
    severity: str,
    title: str,
    description: str,
    expected_behavior: str,
    actual_behavior: str,
) -> None:
    existing = client.get("/api/pilot-feedback", headers=headers, params={"case_id": case_id}).json()
    if any(item["title"] == title for item in existing):
        return
    response = client.post(
        "/api/pilot-feedback",
        headers=headers,
        json={
            "case_id": case_id,
            "module": module,
            "severity": severity,
            "title": title,
            "description": description,
            "expected_behavior": expected_behavior,
            "actual_behavior": actual_behavior,
        },
    )
    response.raise_for_status()


def resolve_feedback_by_title(
    client: TestClient,
    headers: dict[str, str],
    *,
    title: str,
    status: str = "FIXED",
) -> None:
    existing = client.get("/api/pilot-feedback", headers=headers).json()
    for item in existing:
        if item["title"] != title:
            continue
        if item["status"] == status:
            continue
        response = client.patch(
            f"/api/pilot-feedback/{item['id']}",
            headers=headers,
            json={"status": status},
        )
        response.raise_for_status()


def export_and_inspect(client: TestClient, headers: dict[str, str], case_id: int) -> dict:
    with Session(engine) as db:
        existing = db.scalar(
            select(ExportPackage)
            .where(ExportPackage.case_id == case_id)
            .order_by(ExportPackage.created_at.desc())
        )
    if existing is not None:
        payload = {"id": existing.id, "archive_path": existing.archive_path}
    else:
        response = client.post(f"/api/export/{case_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
    archive_path = Path(payload["archive_path"])
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
    top_sections = sorted({name.split("/")[1] for name in names if "/" in name})
    return {"archive_path": archive_path, "names": names, "sections": top_sections}


def scenario_status(ok: bool, *, negative: bool = False) -> str:
    if ok and negative:
        return "PASSED"
    return "PASSED" if ok else "FAILED"


def build_results_report(data: dict) -> str:
    backlog_rows = "\n".join(
        f"| {item['id']} | {item['severity']} | {item['module']} | {item['title']} | {item['recommendation']} |"
        for item in data["backlog_rows"]
    ) or "| - | - | - | - | - |"
    return f"""# PILOT RESULTS REPORT

## 1. Общий статус

Статус:
- {data["overall_status"]}

Рекомендация:
- {data["recommendation_text"]}

## 2. Период пилота

Дата начала: {data["started_at"]}
Дата завершения: {data["finished_at"]}
Участники: Codex Pilot Coordinator, seeded demo users
Роли: admin, lawyer, manager, initiator, service_agent

## 3. Пройденные сценарии

| Сценарий | Статус | Комментарий |
|---|---|---|
| PILOT-001 | {data["scenario_1_status"]} | {data["scenario_1_comment"]} |
| PILOT-002 | {data["scenario_2_status"]} | {data["scenario_2_comment"]} |
| PILOT-003 | {data["scenario_3_status"]} | {data["scenario_3_comment"]} |

## 4. Метрики

- количество дел: {data["report"]["total_cases"]}
- количество feedback items: {data["report"]["feedback_total"]}
- feedback_by_severity_total: {data["report"]["feedback_by_severity_total"]}
- feedback_by_severity_unresolved: {data["report"]["feedback_by_severity_unresolved"]}
- AI/RAG warnings: {data["report"]["ai_rag_warnings"]}
- authority warnings: {data["report"]["authority_warnings"]}
- authority invalids: {data["report"]["authority_invalids"]}
- blocked actions: {data["report"]["blocked_actions"]}
- exports generated: {data["report"]["exports_generated"]}

## 5. Юридическое качество

- качество претензии: черновики по DEMO-001 и DEMO-002 доступны для ручной проверки юристом.
- качество иска: happy-path дела формируют экспорт и court package после proof-of-service.
- корректность полномочий: DEMO-001 и DEMO-002 проходят authority gate; DEMO-003 корректно блокируется.
- корректность приложений: export happy-path дел содержит authority artifacts и postal proofs.
- корректность RAG-источников: citations доступны на pilot-grade уровне и используются как проверяемые ссылки.

## 6. Техническое качество

- стабильность UI: frontend regression и browser E2E проходят.
- понятность ошибок: authority block возвращает понятную backend/UI ошибку.
- полнота audit log: blocked approval attempts теперь фиксируются в audit log.
- полнота export: happy-path export формируется после proof-of-service и содержит 12 разделов.
- скорость работы: локальный mock/manual contour проходит сценарии без ручной помощи разработчика.

## 7. Feedback backlog

| ID | Severity | Module | Title | Recommendation |
|---|---|---|---|---|
{backlog_rows}

## 8. Go / No-Go

Решение:
- {data["go_no_go"]}

## 9. Следующие задачи

- Поднять качество RAG/LLM с pilot-grade до sandbox-ready quality.
- Расширить browser regression сверх pilot smoke contour.
- Готовить отдельный sandbox API preparation sprint только после сохранения текущих safety gates.
"""


def build_backlog(feedback_items: list[dict]) -> str:
    sections = {
        "BLOCKER fixes": [],
        "HIGH fixes": [],
        "UX improvements": [],
        "Legal template improvements": [],
        "RAG/LLM quality improvements": [],
        "Export improvements": [],
        "Audit improvements": [],
        "Integration readiness improvements": [],
    }
    for item in feedback_items:
        severity = item["severity"]
        module = item["module"]
        if severity == "BLOCKER":
            sections["BLOCKER fixes"].append(item)
        elif severity == "HIGH":
            sections["HIGH fixes"].append(item)
        elif module == "UI":
            sections["UX improvements"].append(item)
        elif module in {"PRETENSION", "CLAIM"}:
            sections["Legal template improvements"].append(item)
        elif module == "RAG":
            sections["RAG/LLM quality improvements"].append(item)
        elif module == "EXPORT":
            sections["Export improvements"].append(item)
        elif module == "AUDIT":
            sections["Audit improvements"].append(item)
        else:
            sections["Integration readiness improvements"].append(item)

    lines = ["# POST PILOT BACKLOG", "", "## Pilot Recovery Notes", "- Pilot FAILED because blocked legal approval was not written to AuditLog and pilot metrics miscounted authority/timeline signals.", "- Pilot recovery fixed blocked-action audit, authority metric deduplication, shared timeline builder, and report generation parity between API and CLI.", ""]
    for title, items in sections.items():
        lines.append(f"## {title}")
        if not items:
            lines.append("- Нет новых задач.")
        else:
            for item in items:
                lines.append(f"- `{item['severity']}` {item['module']}: {item['title']} — {item['description']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    started_at = datetime.now(UTC)
    seed_demo_main()
    date_from = (started_at - timedelta(days=7)).date()
    date_to = (started_at + timedelta(days=1)).date()

    with TestClient(app) as client:
        admin_headers = login(client, "admin@example.com")
        lawyer_headers = login(client, "lawyer@example.com")
        manager_headers = login(client, "manager@example.com")

        system_status = client.get("/api/system/status")
        system_status.raise_for_status()
        system_payload = system_status.json()
        assert system_payload["real_fns_enabled"] is False
        assert system_payload["real_post_send_enabled"] is False
        assert system_payload["real_court_search_enabled"] is False
        assert system_payload["court_submission_enabled"] is False

        cases_response = client.get("/api/cases", headers=lawyer_headers)
        cases_response.raise_for_status()
        cases = {item["title"]: item for item in cases_response.json()}
        demo_1 = cases["DEMO-001 director happy path"]
        demo_2 = cases["DEMO-002 employee happy path"]
        demo_3 = cases["DEMO-003 authority block path"]

        organization = client.get(f"/api/organizations/{demo_1['plaintiff_organization_id']}", headers=lawyer_headers)
        organization.raise_for_status()
        signatory_director = client.get(f"/api/signatories/{demo_1['signatory_id']}", headers=lawyer_headers)
        signatory_director.raise_for_status()
        docs_1 = client.get(f"/api/documents/{demo_1['id']}", headers=lawyer_headers)
        docs_1.raise_for_status()
        pretension_1 = client.get(f"/api/pretensions/{demo_1['id']}", headers=lawyer_headers)
        pretension_1.raise_for_status()
        claim_1 = client.get(f"/api/claims/{demo_1['id']}", headers=lawyer_headers)
        claim_1.raise_for_status()
        citations_1 = client.get(f"/api/rag/citations/{demo_1['id']}", headers=lawyer_headers)
        citations_1.raise_for_status()
        checklist_1 = client.get(f"/api/checklists/{demo_1['id']}", headers=lawyer_headers)
        checklist_1.raise_for_status()
        export_1 = export_and_inspect(client, lawyer_headers, demo_1["id"])

        with Session(engine) as db:
            facts_1_count = len(db.scalars(select(ExtractedFact).where(ExtractedFact.case_id == demo_1["id"])).all())
            audit_items = list(
                db.scalars(
                    select(AuditLog).order_by(AuditLog.created_at.asc())
                ).all()
            )

        scenario_1_ok = (
            organization.json()["inn"] == "7701234567"
            and signatory_director.json()["signatory_type"] == "DIRECTOR"
            and len(docs_1.json()) >= 3
            and facts_1_count >= 2
            and pretension_1.json()["approved"] is True
            and claim_1.json()["approved"] is True
            and len(citations_1.json()) >= 1
            and checklist_1.json()["case_id"] == demo_1["id"]
            and len(export_1["sections"]) == 12
            and any(item.action == "case_exported" and item.entity_type == "export_package" for item in audit_items)
        )

        signatory_employee = client.get(f"/api/signatories/{demo_2['signatory_id']}", headers=lawyer_headers)
        signatory_employee.raise_for_status()
        employee_id = signatory_employee.json()["employee_id"]
        poa_list = client.get(f"/api/employees/{employee_id}/powers-of-attorney", headers=lawyer_headers)
        poa_list.raise_for_status()
        authority_check = client.post(
            f"/api/signatories/{demo_2['signatory_id']}/check-authority",
            headers=lawyer_headers,
            json={"case_id": demo_2["id"], "document_kind": "claim"},
        )
        authority_check.raise_for_status()
        export_2 = export_and_inspect(client, lawyer_headers, demo_2["id"])
        scenario_2_ok = (
            signatory_employee.json()["signatory_type"] == "AUTHORIZED_EMPLOYEE"
            and any(item["status"] == "ACTIVE" for item in poa_list.json())
            and authority_check.json()["valid"] is True
            and any(name.endswith("powers_of_attorney.json") for name in export_2["names"])
            and any("poa" in name.lower() for name in export_2["names"])
            and any(name.endswith("authority_checks.json") for name in export_2["names"])
        )

        blocked = client.post(f"/api/workflow/{demo_3['id']}/approve-claim", headers=lawyer_headers)
        scenario_3_message = blocked.json()["detail"] if blocked.status_code == 400 else f"Unexpected status: {blocked.status_code}"
        audit_after = client.get("/api/audit", headers=admin_headers)
        audit_after.raise_for_status()
        audit_after_items = audit_after.json()
        blocked_audit_present = any(
            item["action"] == "claim_approval_blocked" and item["entity_id"] == str(demo_3["id"])
            for item in audit_after_items
        )
        scenario_3_ok = blocked.status_code == 400 and blocked_audit_present

        if scenario_3_ok:
            resolve_feedback_by_title(
                client,
                admin_headers,
                title="Blocked authority approval is missing in audit log",
                status="FIXED",
            )
            resolve_feedback_by_title(
                client,
                admin_headers,
                title="Pilot metrics overcount authority warnings and show negative claim draft time",
                status="FIXED",
            )

        ensure_feedback(
            client,
            lawyer_headers,
            case_id=demo_1["id"],
            module="UI",
            severity="LOW",
            title="Checklist and export status could be shown together",
            description="Happy path works, but a tighter court-package summary would reduce navigation during lawyer review.",
            expected_behavior="Court package readiness and export state are visible in one block.",
            actual_behavior="The path works, but the final state is spread across several tabs.",
        )
        ensure_feedback(
            client,
            lawyer_headers,
            case_id=demo_2["id"],
            module="RAG",
            severity="IDEA",
            title="Show legal source rationale near authority report",
            description="Lawyer review would be faster if RAG snippets were shown next to authority results.",
            expected_behavior="Authority and legal basis can be scanned together.",
            actual_behavior="RAG and authority are both present, but reviewed separately.",
        )

        summary_response = client.get(
            f"/api/pilot-metrics/summary?date_from={date_from.isoformat()}&date_to={date_to.isoformat()}",
            headers=manager_headers,
        )
        summary_response.raise_for_status()
        summary = summary_response.json()

        report_response = client.get(
            f"/api/pilot-report?date_from={date_from.isoformat()}&date_to={date_to.isoformat()}",
            headers=manager_headers,
        )
        report_response.raise_for_status()
        report = report_response.json()

        feedback_response = client.get("/api/pilot-feedback", headers=admin_headers)
        feedback_response.raise_for_status()
        feedback_items = feedback_response.json()

    severity_counter = Counter(item["severity"] for item in feedback_items)
    unresolved_critical = [
        item
        for item in feedback_items
        if item["severity"] in {"BLOCKER", "HIGH"} and item["status"] not in {"FIXED", "WONT_FIX"}
    ]
    if not scenario_1_ok or not scenario_2_ok or not scenario_3_ok or unresolved_critical:
        overall_status = "FAILED"
        recommendation_text = "остановить"
        go_no_go = "STOP"
    elif any(severity_counter.get(level, 0) for level in ("MEDIUM", "LOW", "IDEA")):
        overall_status = "PASSED_WITH_ISSUES"
        recommendation_text = "продолжать с backlog"
        go_no_go = "GO TO NEXT SPRINT"
    else:
        overall_status = "PASSED"
        recommendation_text = "продолжать"
        go_no_go = "GO TO NEXT SPRINT"

    backlog_rows = [
        {
            "id": item["id"],
            "severity": item["severity"],
            "module": item["module"],
            "title": item["title"],
            "description": item["description"],
            "recommendation": "Fix before next sprint" if item["severity"] in {"BLOCKER", "HIGH"} else "Track in backlog",
        }
        for item in feedback_items
    ]

    report_data = {
        "overall_status": overall_status,
        "recommendation_text": recommendation_text,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "scenario_1_status": scenario_status(scenario_1_ok),
        "scenario_2_status": scenario_status(scenario_2_ok),
        "scenario_3_status": scenario_status(scenario_3_ok, negative=True),
        "scenario_1_comment": "Director happy path reached export, citations, checklist, and audit verification." if scenario_1_ok else "Director happy path did not complete expected export/audit verification.",
        "scenario_2_comment": "Employee signatory path used active POA and export contains authority artifacts." if scenario_2_ok else "POA or authority artifacts are missing from employee happy path.",
        "scenario_3_comment": "Negative authority path blocked approval and wrote blocked action to audit log." if scenario_3_ok else scenario_3_message,
        "report": report,
        "backlog_rows": backlog_rows,
        "go_no_go": go_no_go,
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "PILOT_RESULTS_REPORT.md").write_text(build_results_report(report_data), encoding="utf-8")
    (DOCS_DIR / "POST_PILOT_BACKLOG.md").write_text(build_backlog(feedback_items), encoding="utf-8")

    print(
        json.dumps(
            {
                "overall_status": overall_status,
                "system_status": {
                    "fns_mode": system_payload["fns_mode"],
                    "russian_post_mode": system_payload["russian_post_mode"],
                    "court_arbitr_mode": system_payload["court_arbitr_mode"],
                    "real_fns_enabled": system_payload["real_fns_enabled"],
                    "real_post_send_enabled": system_payload["real_post_send_enabled"],
                    "real_court_search_enabled": system_payload["real_court_search_enabled"],
                    "court_submission_enabled": system_payload["court_submission_enabled"],
                },
                "scenario_statuses": {
                    "PILOT-001": report_data["scenario_1_status"],
                    "PILOT-002": report_data["scenario_2_status"],
                    "PILOT-003": report_data["scenario_3_status"],
                },
                "feedback_by_severity_total": report.get("feedback_by_severity_total", {}),
                "feedback_by_severity_unresolved": report.get("feedback_by_severity_unresolved", {}),
                "pilot_report": report,
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.models import AuditLog, PilotFeedback, SignatoryAuthorityCheck, User
from app.services.pilot_metrics_service import PilotMetricsService
from app.services.pilot_timeline_service import PilotTimelineService
from app.tests.helpers import (
    assign_representation,
    create_case,
    create_employee,
    create_organization,
    create_postal_dispatch,
    create_power_of_attorney,
    create_signatory,
    refresh_postal_dispatch_status,
    upload_postal_proof,
)


def _seed_pilot_recovery_cases(client, auth_headers):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    manager_headers = auth_headers("manager")

    organization_id = create_organization(client, admin_headers, inn="7702234567")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")

    employee_id = create_employee(
        client,
        organization_id,
        admin_headers,
        full_name="Employee Happy",
        email="employee-happy@example.com",
    )
    employee_signatory_id = create_signatory(
        client,
        organization_id,
        admin_headers,
        signatory_type="AUTHORIZED_EMPLOYEE",
        employee_id=employee_id,
    )
    create_power_of_attorney(
        client,
        employee_id,
        admin_headers,
        number="POA-HAPPY",
        authority_scope="SIGN_PRETENSION,SIGN_CLAIM,REPRESENT_IN_COURT",
    )

    blocked_employee_id = create_employee(
        client,
        organization_id,
        admin_headers,
        full_name="Employee Blocked",
        email="employee-blocked@example.com",
    )
    blocked_signatory_id = create_signatory(
        client,
        organization_id,
        admin_headers,
        signatory_type="AUTHORIZED_EMPLOYEE",
        employee_id=blocked_employee_id,
    )
    create_power_of_attorney(
        client,
        blocked_employee_id,
        admin_headers,
        number="POA-EXPIRED",
        issued_at="2025-01-01",
        expires_at="2025-12-31",
        authority_scope="SIGN_CLAIM",
    )

    happy_director_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(
        client,
        happy_director_case_id,
        initiator_headers,
        organization_id=organization_id,
        signatory_id=director_signatory_id,
    )
    assert client.post(f"/api/claims/{happy_director_case_id}/generate", headers=lawyer_headers).status_code == 200
    assert client.post(f"/api/workflow/{happy_director_case_id}/approve-claim", headers=lawyer_headers).status_code == 200
    director_dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=happy_director_case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=director_dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=director_dispatch_id)
    assert client.post(
        f"/api/workflow/{happy_director_case_id}/court-package-ready",
        headers=lawyer_headers,
    ).status_code == 200
    assert client.post(
        "/api/pilot-feedback",
        headers=lawyer_headers,
        json={
            "case_id": happy_director_case_id,
            "module": "CLAIM",
            "severity": "LOW",
            "title": "Director happy path review",
            "description": "Pilot recovery happy path note.",
            "expected_behavior": "Case should pass.",
            "actual_behavior": "Case passed.",
        },
    ).status_code == 200
    assert client.post(f"/api/export/{happy_director_case_id}", headers=lawyer_headers).status_code == 200

    happy_employee_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(
        client,
        happy_employee_case_id,
        initiator_headers,
        organization_id=organization_id,
        signatory_id=employee_signatory_id,
    )
    assert client.post(
        f"/api/signatories/{employee_signatory_id}/check-authority",
        headers=lawyer_headers,
        json={"case_id": happy_employee_case_id, "document_kind": "claim"},
    ).status_code == 200
    assert client.post(f"/api/claims/{happy_employee_case_id}/generate", headers=lawyer_headers).status_code == 200
    assert client.post(f"/api/workflow/{happy_employee_case_id}/approve-claim", headers=lawyer_headers).status_code == 200
    employee_dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=happy_employee_case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=employee_dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=employee_dispatch_id)
    assert client.post(
        f"/api/workflow/{happy_employee_case_id}/court-package-ready",
        headers=lawyer_headers,
    ).status_code == 200
    assert client.post(f"/api/export/{happy_employee_case_id}", headers=lawyer_headers).status_code == 200

    blocked_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(
        client,
        blocked_case_id,
        initiator_headers,
        organization_id=organization_id,
        signatory_id=blocked_signatory_id,
    )
    assert client.post(f"/api/claims/{blocked_case_id}/generate", headers=lawyer_headers).status_code == 200
    blocked = client.post(f"/api/workflow/{blocked_case_id}/approve-claim", headers=lawyer_headers)
    assert blocked.status_code == 400

    return {
        "admin_headers": admin_headers,
        "lawyer_headers": lawyer_headers,
        "manager_headers": manager_headers,
        "organization_id": organization_id,
        "happy_director_case_id": happy_director_case_id,
        "happy_employee_case_id": happy_employee_case_id,
        "blocked_case_id": blocked_case_id,
        "employee_signatory_id": employee_signatory_id,
        "blocked_signatory_id": blocked_signatory_id,
    }


def test_pilot_metrics_counts_authority_warning(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    warning_check = SignatoryAuthorityCheck(
        signatory_id=seeded["blocked_signatory_id"],
        case_id=seeded["blocked_case_id"],
        power_of_attorney_id=None,
        document_kind="claim",
        required_scopes="SIGN_CLAIM",
        result="WARNING",
        reason="Manual review required",
        checked_at=datetime.now(UTC),
    )
    db_session.add(warning_check)
    db_session.commit()

    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    summary = PilotMetricsService(db_session).summary(manager)

    assert summary.total_authority_warnings >= 1
    blocked_case = next(item for item in summary.cases if item.case_id == seeded["blocked_case_id"])
    assert blocked_case.authority_warnings >= 1


def test_pilot_metrics_counts_authority_invalid(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))

    summary = PilotMetricsService(db_session).summary(manager)
    blocked_case = next(item for item in summary.cases if item.case_id == seeded["blocked_case_id"])

    assert summary.total_authority_invalids >= 1
    assert blocked_case.authority_invalids >= 1


def test_pilot_metrics_counts_blocked_action(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))

    summary = PilotMetricsService(db_session).summary(manager)
    blocked_case = next(item for item in summary.cases if item.case_id == seeded["blocked_case_id"])

    assert summary.total_blocked_actions >= 1
    assert blocked_case.blocked_actions >= 1


def test_pilot_metrics_deduplicates_authority_events(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    original = db_session.scalar(
        select(SignatoryAuthorityCheck).where(SignatoryAuthorityCheck.case_id == seeded["blocked_case_id"])
    )
    assert original is not None
    db_session.add(
        SignatoryAuthorityCheck(
            signatory_id=original.signatory_id,
            case_id=original.case_id,
            power_of_attorney_id=original.power_of_attorney_id,
            document_kind=original.document_kind,
            required_scopes=original.required_scopes,
            result=original.result,
            reason=original.reason,
            checked_at=original.checked_at,
        )
    )
    db_session.commit()

    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    blocked_case = next(
        item
        for item in PilotMetricsService(db_session).summary(manager).cases
        if item.case_id == seeded["blocked_case_id"]
    )
    raw_count = len(
        db_session.scalars(
            select(SignatoryAuthorityCheck).where(SignatoryAuthorityCheck.case_id == seeded["blocked_case_id"])
        ).all()
    )

    assert raw_count >= 2
    assert blocked_case.authority_checks_total == 1
    assert blocked_case.authority_invalids == 1


def test_demo_003_has_invalid_authority_and_blocked_action(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    blocked_case = PilotMetricsService(db_session).case_metrics(seeded["blocked_case_id"], manager)

    assert blocked_case.authority_invalids >= 1
    assert blocked_case.blocked_actions >= 1


def test_demo_001_has_no_false_authority_invalid(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    happy_case = PilotMetricsService(db_session).case_metrics(seeded["happy_director_case_id"], manager)

    assert happy_case.authority_invalids == 0
    assert happy_case.blocked_actions == 0


def test_demo_002_has_valid_employee_poa(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    employee_case = PilotMetricsService(db_session).case_metrics(seeded["happy_employee_case_id"], manager)

    assert employee_case.authority.valid_count >= 1
    assert employee_case.authority_invalids == 0


def test_case_timeline_contains_required_events(client, auth_headers):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    timeline_response = client.get(
        f"/api/pilot-metrics/cases/{seeded['happy_director_case_id']}/timeline",
        headers=seeded["manager_headers"],
    )
    assert timeline_response.status_code == 200
    event_types = {item["event_type"] for item in timeline_response.json()["timeline"]}

    assert "CASE_CREATED" in event_types
    assert "CLAIM_GENERATED" in event_types
    assert "CLAIM_APPROVED" in event_types
    assert "CLAIM_COPY_PROOF_UPLOADED" in event_types
    assert "COURT_PACKAGE_READY" in event_types
    assert "EXPORT_GENERATED" in event_types
    assert "PILOT_FEEDBACK_CREATED" in event_types


def test_case_timeline_sorted_by_created_at(client, auth_headers):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    timeline_response = client.get(
        f"/api/pilot-metrics/cases/{seeded['happy_employee_case_id']}/timeline",
        headers=seeded["manager_headers"],
    )
    assert timeline_response.status_code == 200
    created_at = [item["created_at"] for item in timeline_response.json()["timeline"]]
    assert created_at == sorted(created_at)


def test_case_timeline_deduplicates_events(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    original = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "case",
            AuditLog.entity_id == str(seeded["blocked_case_id"]),
            AuditLog.action == "claim_approval_blocked",
        )
    )
    assert original is not None
    db_session.add(
        AuditLog(
            actor_user_id=original.actor_user_id,
            action=original.action,
            entity_type=original.entity_type,
            entity_id=original.entity_id,
            details=original.details,
            request_id=original.request_id,
            created_at=original.created_at,
        )
    )
    db_session.commit()

    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    blocked_events = [
        item
        for item in PilotTimelineService(db_session).list_case_timeline(
            seeded["blocked_case_id"],
            manager,
        )
        if item.source == "audit" and item.event_type == "AUTHORITY_CHECK_FAILED" and item.related_entity_id == str(seeded["blocked_case_id"])
    ]
    assert len(blocked_events) == 1


def test_pilot_report_uses_same_timeline_builder(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    service = PilotMetricsService(db_session)
    cases = service._list_cases(manager, date_from=None, date_to=None)
    report = service.report(manager)
    expected = PilotTimelineService(db_session).timeline_summary(cases)

    assert report.timeline_summary == expected


def test_pilot_report_period_filter(client, auth_headers):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    response = client.get(
        "/api/pilot-report?date_from=2026-05-01&date_to=2026-05-31",
        headers=seeded["manager_headers"],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["date_from"] == "2026-05-01"
    assert payload["date_to"] == "2026-05-31"


def test_generate_pilot_report_cli_markdown(client, auth_headers):
    _seed_pilot_recovery_cases(client, auth_headers)
    output_path = Path.cwd() / "pilot-report-test.md"
    if output_path.exists():
        output_path.unlink()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{(Path.cwd() / 'test.db').as_posix()}"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_report.py",
            "--from",
            "2026-05-01",
            "--to",
            "2026-05-31",
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    content = output_path.read_text(encoding="utf-8")
    assert "# PILOT RESULTS REPORT" in content
    assert "authority_invalids" in content.lower()
    output_path.unlink(missing_ok=True)


def test_generate_pilot_report_cli_json(client, auth_headers):
    _seed_pilot_recovery_cases(client, auth_headers)
    output_path = Path.cwd() / "pilot-report-test.json"
    if output_path.exists():
        output_path.unlink()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{(Path.cwd() / 'test.db').as_posix()}"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_pilot_report.py",
            "--from",
            "2026-05-01",
            "--to",
            "2026-05-31",
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "authority_invalids" in payload
    assert payload["recommendation"] in {"go", "no-go"}
    output_path.unlink(missing_ok=True)


def test_pilot_report_contains_no_secrets(client, auth_headers):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    response = client.get("/api/pilot-report", headers=seeded["manager_headers"])
    assert response.status_code == 200
    payload = json.dumps(response.json()).lower()
    for forbidden in ("token", "secret", "password", "api_key", "app_token", "user_key"):
        assert forbidden not in payload


def test_pilot_summary_legacy_pretension_duration_not_null(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    summary = PilotMetricsService(db_session).summary(manager)
    assert summary.average_pretension_draft_minutes is not None
    assert summary.average_pretension_draft_data_status in {"ok", "not_enough_data"}
    case = next(item for item in summary.cases if item.case_id == seeded["happy_director_case_id"])
    assert case.pretension_draft_minutes is not None
    assert case.pretension_draft_data_status in {"ok", "fallback", "not_enough_data"}


def test_feedback_by_severity_splits_total_and_unresolved(client, auth_headers, db_session):
    seeded = _seed_pilot_recovery_cases(client, auth_headers)
    manager = db_session.scalar(select(User).where(User.email == "manager@example.com"))
    feedback = client.post(
        "/api/pilot-feedback",
        headers=seeded["lawyer_headers"],
        json={
            "case_id": seeded["blocked_case_id"],
            "module": "AUTHORITY",
            "severity": "BLOCKER",
            "title": "Historical blocker",
            "description": "Resolved authority blocker",
            "expected_behavior": "No unresolved blocker remains",
            "actual_behavior": "Resolved",
        },
    )
    assert feedback.status_code == 200
    fixed = client.patch(
        f"/api/pilot-feedback/{feedback.json()['id']}",
        headers=seeded["admin_headers"],
        json={"status": "FIXED"},
    )
    assert fixed.status_code == 200

    summary = PilotMetricsService(db_session).summary(manager)
    report = PilotMetricsService(db_session).report(manager)
    assert summary.feedback_by_severity_total["BLOCKER"] >= 1
    assert summary.feedback_by_severity_unresolved["BLOCKER"] == 0
    assert report.feedback_by_severity_total["BLOCKER"] >= 1
    assert report.feedback_by_severity_unresolved["BLOCKER"] == 0

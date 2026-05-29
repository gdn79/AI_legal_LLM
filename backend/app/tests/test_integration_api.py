import json
from datetime import UTC, datetime, timedelta
from io import BytesIO
from zipfile import ZipFile

from sqlalchemy import select

from app.core.config import get_settings
from app.models import AuditLog, CourtSubmissionPackage, Document, DocumentVersion, ExternalCourtCase, IntegrationApproval, IntegrationApprovalEnvironment, IntegrationApprovalStatus, IntegrationRequestLog, Party, PilotFeedback, PostalDispatch, PostalProofDocument
from app.tests.helpers import (
    assign_representation,
    create_case,
    create_employee,
    create_organization,
    create_power_of_attorney,
    create_postal_dispatch,
    create_signatory,
    refresh_postal_dispatch_status,
    upload_postal_proof,
    upload_document_from_path,
)


def create_sandbox_approval(
    db_session,
    *,
    integration_name: str,
    status: str = IntegrationApprovalStatus.APPROVED.value,
    expires_in_days: int = 7,
):
    approval = IntegrationApproval(
        integration_name=integration_name,
        environment=IntegrationApprovalEnvironment.SANDBOX.value,
        requested_by_id=1,
        approved_by_id=1 if status == IntegrationApprovalStatus.APPROVED.value else None,
        status=status,
        reason="test sandbox approval",
        approved_at=datetime.now(UTC) if status == IntegrationApprovalStatus.APPROVED.value else None,
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days) if expires_in_days is not None else None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(approval)
    db_session.commit()
    return approval


def test_healthcheck(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_system_status(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "ok"
    assert payload["database"] == "ok"
    assert payload["storage"] == "ok"
    assert payload["llm"] in {"mock", "configured"}
    assert payload["fns_provider"] == "mock_fns_adapter"
    assert payload["fns_mode"] == "MOCK_FOR_DEV"
    assert payload["fns_sandbox_enabled"] is False
    assert payload["real_fns_enabled"] is False
    assert payload["russian_post_provider"] == "mock_russian_post_adapter"
    assert payload["russian_post_mode"] == "MOCK_FOR_DEV"
    assert payload["russian_post_sandbox_enabled"] is False
    assert payload["real_post_send_enabled"] is False
    assert payload["court_arbitr_provider"] == "mock_court_arbitr_adapter"
    assert payload["court_arbitr_mode"] == "MOCK_FOR_DEV"
    assert payload["court_sandbox_enabled"] is False
    assert payload["real_court_search_enabled"] is False


def test_auth_current_user_case_and_organization_endpoints(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    me = client.get("/api/users/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["role"] == "admin"

    organization_id = create_organization(client, admin_headers)
    snapshots = client.get(f"/api/organizations/{organization_id}/snapshots", headers=admin_headers)
    assert snapshots.status_code == 200
    assert snapshots.json()

    initiator_headers = auth_headers("initiator")
    case_id = create_case(client, initiator_headers)

    listing = client.get("/api/cases", headers=initiator_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = client.get(f"/api/cases/{case_id}", headers=initiator_headers)
    assert detail.status_code == 200

    parties = db_session.scalars(select(Party).where(Party.case_id == case_id)).all()
    assert len(parties) == 2

    audit_logs = db_session.scalars(
        select(AuditLog).where(AuditLog.entity_type == "case", AuditLog.entity_id == str(case_id))
    ).all()
    assert any(log.action == "case_created" for log in audit_logs)


def test_document_upload_download_versions_and_audit(client, auth_headers, db_session, sample_documents_dir):
    initiator_headers = auth_headers("initiator")
    admin_headers = auth_headers("admin")
    case_id = create_case(client, initiator_headers)

    response = upload_document_from_path(
        client,
        case_id,
        initiator_headers,
        sample_documents_dir / "contract.txt",
        "text/plain",
    )
    assert response.status_code == 200
    document_id = response.json()["id"]

    persisted = db_session.scalar(select(Document).where(Document.id == document_id))
    assert persisted is not None
    assert persisted.filename == "contract.txt"
    assert persisted.sha256
    assert "Договор поставки" in persisted.extracted_text

    updated = client.post(
        f"/api/documents/item/{document_id}/versions",
        headers=initiator_headers,
        files={"file": ("contract.txt", BytesIO("Version two".encode("utf-8")), "text/plain")},
    )
    assert updated.status_code == 200
    assert updated.json()["filename"] == "contract_v2.txt"

    versions = client.get(f"/api/documents/item/{document_id}/versions", headers=initiator_headers)
    assert versions.status_code == 200
    assert [item["version"] for item in versions.json()] == [2, 1]

    version_rows = db_session.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.asc())
    ).all()
    assert [item.version for item in version_rows] == [1, 2]
    assert all(item.sha256 for item in version_rows)

    download = client.get(f"/api/documents/download/{document_id}", headers=initiator_headers)
    assert download.status_code == 200
    assert download.content == b"Version two"

    audit = client.get("/api/audit", headers=admin_headers)
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()]
    assert "document_uploaded" in actions
    assert "document_downloaded" in actions


def test_negative_security_and_authority_cases(client, auth_headers):
    unauthenticated = client.get("/api/cases")
    assert unauthenticated.status_code == 401

    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    manager_headers = auth_headers("manager")
    lawyer_headers = auth_headers("lawyer")
    service_agent_headers = auth_headers("service_agent")
    foreign_case_id = create_case(client, initiator_headers)

    manager_create = client.post(
        "/api/cases",
        headers=manager_headers,
        json={
            "title": "Blocked",
            "description": "Case",
            "claimant_name": "OOO Alpha",
            "respondent_name": "OOO Beta",
            "claim_amount": 10.0,
        },
    )
    assert manager_create.status_code == 403

    foreign_case = client.get(f"/api/cases/{foreign_case_id}", headers=lawyer_headers)
    assert foreign_case.status_code == 403

    blocked_upload = client.post(
        f"/api/documents/{foreign_case_id}",
        headers=manager_headers,
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert blocked_upload.status_code in {400, 403}

    assigned_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)

    denied_claim_approval = client.post(f"/api/workflow/{assigned_case_id}/approve-claim", headers=initiator_headers)
    assert denied_claim_approval.status_code == 403
    service_agent_claim_approval = client.post(f"/api/workflow/{assigned_case_id}/approve-claim", headers=service_agent_headers)
    assert service_agent_claim_approval.status_code == 403
    service_agent_pretension_approval = client.post(f"/api/workflow/{assigned_case_id}/approve-pretension", headers=service_agent_headers)
    assert service_agent_pretension_approval.status_code == 403

    organization_id = create_organization(client, admin_headers, inn="7701234568")
    employee_id = create_employee(client, organization_id, admin_headers)
    signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="AUTHORIZED_EMPLOYEE", employee_id=employee_id)
    assign_representation(
        client,
        assigned_case_id,
        initiator_headers,
        organization_id=organization_id,
        signatory_id=signatory_id,
    )

    authority_block = client.post(f"/api/workflow/{assigned_case_id}/approve-claim", headers=lawyer_headers)
    assert authority_block.status_code == 400
    assert "Valid power of attorney" in authority_block.json()["detail"]

    power_id = create_power_of_attorney(client, employee_id, admin_headers)
    check = client.post(
        f"/api/signatories/{signatory_id}/check-authority",
        headers=admin_headers,
        json={"case_id": assigned_case_id, "document_kind": "claim"},
    )
    assert check.status_code == 200
    assert check.json()["valid"] is True

    revoke = client.post(f"/api/powers-of-attorney/{power_id}/revoke", headers=admin_headers)
    assert revoke.status_code == 200
    authority_block_again = client.post(f"/api/workflow/{assigned_case_id}/approve-claim", headers=lawyer_headers)
    assert authority_block_again.status_code == 400


def test_court_import_deduplicates_cases_and_export_requires_authority(client, auth_headers, db_session, sample_documents_dir):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234569")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")

    first_job = client.post(
        "/api/court-import/jobs",
        headers=admin_headers,
        json={
            "organization_id": organization_id,
            "inn": "7701234569",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "participation_role": "claimant",
            "provider_mode": "MOCK_FOR_DEV",
        },
    )
    assert first_job.status_code == 200
    assert first_job.json()["result_count"] == 2

    first_cases = client.get(f"/api/court-import/jobs/{first_job.json()['id']}/cases", headers=admin_headers)
    assert first_cases.status_code == 200
    assert len(first_cases.json()) == 2

    second_job = client.post(
        "/api/court-import/jobs",
        headers=admin_headers,
        json={
            "organization_id": organization_id,
            "inn": "7701234569",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "participation_role": "claimant",
            "provider_mode": "MOCK_FOR_DEV",
        },
    )
    assert second_job.status_code == 200
    assert second_job.json()["result_count"] == 0
    assert db_session.scalars(select(ExternalCourtCase)).all()

    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    upload = upload_document_from_path(
        client,
        case_id,
        initiator_headers,
        sample_documents_dir / "contract.txt",
        "text/plain",
    )
    document_id = upload.json()["id"]
    document = db_session.get(Document, document_id)
    document.is_approved = True
    db_session.add(document)
    db_session.commit()

    pre_approval = client.post(f"/api/export/{case_id}", headers=lawyer_headers)
    assert pre_approval.status_code == 400

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert approved.status_code == 200

    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)

    exported = client.post(f"/api/export/{case_id}", headers=lawyer_headers)
    assert exported.status_code == 200
    with ZipFile(exported.json()["archive_path"]) as archive:
        names = set(archive.namelist())
    assert any(name.endswith("/contract.txt") and "/01_" in name for name in names)
    assert any("03_Претензия/pretension.txt" in name for name in names)
    assert any("05_Проект_иска/claim.txt" in name for name in names)
    assert any("08_Источники_RAG/rag_report.json" in name for name in names)
    assert any("09_Направление_копии_иска/dispatches.json" in name for name in names)
    assert any("12_Журнал_действий/audit_log.txt" in name for name in names)
    for folder in range(1, 13):
        assert any(name.startswith(f"Дело_{case_id}/{folder:02d}_") for name in names)


def test_postal_dispatch_and_court_submission_require_claim_copy_proof(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234571")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)

    blocked = client.post(
        "/api/court-submission",
        headers=lawyer_headers,
        json={"case_id": case_id, "note": "manual package"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Нельзя сформировать судебный комплект: отсутствует доказательство направления копии иска ответчику."

    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    dispatch = db_session.get(PostalDispatch, dispatch_id)
    assert dispatch is not None
    assert dispatch.tracking_number

    proof_id = upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
    proof = db_session.get(PostalProofDocument, proof_id)
    assert proof is not None

    proof_check = client.get(f"/api/russian-post/cases/{case_id}/claim-copy-proof", headers=lawyer_headers)
    assert proof_check.status_code == 200
    assert proof_check.json()["has_claim_copy_proof"] is True

    prepared = client.post(
        "/api/court-submission",
        headers=lawyer_headers,
        json={"case_id": case_id, "note": "manual package"},
    )
    assert prepared.status_code == 200
    package = db_session.get(CourtSubmissionPackage, prepared.json()["id"])
    assert package is not None
    assert package.status == "READY_FOR_MANUAL_SUBMISSION"

    audit = client.get("/api/audit", headers=admin_headers)
    actions = [item["action"] for item in audit.json()]
    assert "postal_dispatch_created" in actions
    assert "postal_proof_uploaded" in actions
    assert "court_submission_package_prepared" in actions


def test_export_forbidden_without_claim_copy_proof(client, auth_headers):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234573")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert approved.status_code == 200

    exported = client.post(f"/api/export/{case_id}", headers=lawyer_headers)
    assert exported.status_code == 409
    assert exported.json()["detail"] == "Нельзя сформировать судебный комплект: отсутствует доказательство направления копии иска ответчику."


def test_export_allowed_with_valid_claim_copy_proof(client, auth_headers):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234574")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert approved.status_code == 200

    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)

    exported = client.post(f"/api/export/{case_id}", headers=lawyer_headers)
    assert exported.status_code == 200
    assert exported.json()["archive_path"].endswith(".zip")


def test_settings_secret_value_not_written_to_audit_log(client, auth_headers):
    admin_headers = auth_headers("admin")
    payload = {"value": "super-secret-token", "description": "secret setting"}
    updated = client.put("/api/settings/LLM_API_KEY", headers=admin_headers, json=payload)
    assert updated.status_code == 200

    audit = client.get("/api/audit", headers=admin_headers)
    assert audit.status_code == 200
    entries = [item for item in audit.json() if item["entity_type"] == "system_setting" and item["entity_id"] == "LLM_API_KEY"]
    assert entries
    assert all("super-secret-token" not in item["details"] for item in entries)
    assert any("[REDACTED]" in item["details"] for item in entries)


def test_settings_non_secret_change_logged_without_sensitive_value(client, auth_headers):
    admin_headers = auth_headers("admin")
    payload = {"value": "stub", "description": "mode"}
    updated = client.put("/api/settings/llm.mode", headers=admin_headers, json=payload)
    assert updated.status_code == 200

    audit = client.get("/api/audit", headers=admin_headers)
    assert audit.status_code == 200
    entries = [item for item in audit.json() if item["entity_type"] == "system_setting" and item["entity_id"] == "llm.mode"]
    assert entries
    assert any("stub" in item["details"] for item in entries)
    assert all("[REDACTED]" not in item["details"] for item in entries)


def test_court_package_ready_forbidden_without_proof(client, auth_headers):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234575")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert approved.status_code == 200

    ready = client.post(f"/api/workflow/{case_id}/court-package-ready", headers=lawyer_headers)
    assert ready.status_code == 409
    assert ready.json()["detail"] == "Нельзя сформировать судебный комплект: отсутствует доказательство направления копии иска ответчику."


def test_court_package_ready_allowed_with_valid_proof(client, auth_headers):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    organization_id = create_organization(client, admin_headers, inn="7701234576")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)

    generated_claim = client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers)
    assert generated_claim.status_code == 200

    approved = client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers)
    assert approved.status_code == 200

    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)

    ready = client.post(f"/api/workflow/{case_id}/court-package-ready", headers=lawyer_headers)
    assert ready.status_code == 200
    assert ready.json()["status"] == "COURT_PACKAGE_READY"


def test_settings_api_masks_secret_values(client, auth_headers):
    admin_headers = auth_headers("admin")
    client.put(
        "/api/settings/RUSSIAN_POST_APP_TOKEN",
        headers=admin_headers,
        json={"value": "very-secret-token", "description": "token"},
    )
    listing = client.get("/api/settings", headers=admin_headers)
    assert listing.status_code == 200
    item = next(entry for entry in listing.json() if entry["key"] == "RUSSIAN_POST_APP_TOKEN")
    assert item["value"] == "[REDACTED]"


def test_test_connection_endpoints_create_safe_integration_logs(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    for path in ["/api/fns/test-connection", "/api/russian-post/test-connection", "/api/court-arbitr/test-connection"]:
        response = client.post(path, headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "secret" not in str(payload).lower()
    logs = db_session.scalars(select(IntegrationRequestLog)).all()
    assert logs
    assert any(log.operation == "test_connection" for log in logs)
    assert all("secret" not in log.safe_request_metadata_json.lower() for log in logs)
    assert all("token" not in log.safe_response_metadata_json.lower() for log in logs)


def test_postal_send_dry_run_and_real_send_disabled(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    lawyer_headers = auth_headers("lawyer")
    initiator_headers = auth_headers("initiator")
    organization_id = create_organization(client, admin_headers, inn="7701234581")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    dispatch_id = create_postal_dispatch(
        client,
        lawyer_headers,
        case_id=case_id,
        organization_id=organization_id,
        dispatch_kind="claim_copy",
    )
    dry_run = client.post(f"/api/postal-dispatches/{dispatch_id}/send?dry_run=true", headers=lawyer_headers)
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    blocked = client.post(f"/api/postal-dispatches/{dispatch_id}/send", headers=lawyer_headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error_code"] == "POST_SEND_DISABLED"
    dispatch = db_session.get(PostalDispatch, dispatch_id)
    assert dispatch is not None
    assert dispatch.external_dispatch_id


def test_postal_create_idempotency_key_prevents_duplicates(client, auth_headers, db_session):
    lawyer_headers = auth_headers("lawyer")
    initiator_headers = auth_headers("initiator")
    admin_headers = auth_headers("admin")
    organization_id = create_organization(client, admin_headers, inn="7701234582")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    payload = {
        "case_id": case_id,
        "organization_id": organization_id,
        "dispatch_kind": "claim_copy",
        "recipient_name": "OOO Beta",
        "recipient_address": "Moscow",
        "provider_mode": "MOCK_FOR_DEV",
        "idempotency_key": "postal-create-1",
    }
    first = client.post("/api/postal-dispatches", headers=lawyer_headers, json=payload)
    second = client.post("/api/postal-dispatches", headers=lawyer_headers, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    rows = db_session.scalars(select(PostalDispatch).where(PostalDispatch.idempotency_key == "postal-create-1")).all()
    assert len(rows) == 1


def test_court_import_public_search_disabled_and_integration_log_created(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    organization_id = create_organization(client, admin_headers, inn="7701234583")
    settings = get_settings()
    original_mode = settings.court_provider_mode
    original_flag = settings.enable_public_kad_search
    settings.court_provider_mode = "PUBLIC_SEARCH_DISABLED"
    settings.enable_public_kad_search = False
    try:
        blocked = client.post(
            "/api/court-import/jobs",
            headers=admin_headers,
            json={
                "organization_id": organization_id,
                "inn": "7701234583",
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "participation_role": "claimant",
                "provider_mode": "PUBLIC_SEARCH",
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["error_code"] == "COURT_UNSAFE_MODE_BLOCKED"
    finally:
        settings.court_provider_mode = original_mode
        settings.enable_public_kad_search = original_flag

    created = client.post(
        "/api/court-import/jobs",
        headers=admin_headers,
        json={
            "organization_id": organization_id,
            "inn": "7701234583",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "participation_role": "claimant",
            "provider_mode": "MOCK_FOR_DEV",
        },
    )
    assert created.status_code == 200
    logs = db_session.scalars(
        select(IntegrationRequestLog)
        .where(IntegrationRequestLog.operation == "import_cases_by_period")
        .order_by(IntegrationRequestLog.created_at.desc())
    ).all()
    assert logs
    assert any(log.status == "FAILED" for log in logs)
    assert any(log.status == "SUCCESS" for log in logs)
    assert all(log.request_id for log in logs)


def test_court_submission_dry_run_and_submit_disabled(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    organization_id = create_organization(client, admin_headers, inn="7701234584")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)
    assert client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers).status_code == 200
    assert client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers).status_code == 200
    dispatch_id = create_postal_dispatch(client, lawyer_headers, case_id=case_id, organization_id=organization_id, dispatch_kind="claim_copy")
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
    package = client.post("/api/court-submission", headers=lawyer_headers, json={"case_id": case_id, "note": "manual package"})
    assert package.status_code == 200
    dry_run = client.post(f"/api/court-submission/{package.json()['id']}/dry-run", headers=lawyer_headers)
    assert dry_run.status_code == 200
    assert dry_run.json()["dry_run"] is True
    blocked = client.post(f"/api/court-submission/{package.json()['id']}/submit", headers=lawyer_headers)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["error_code"] == "COURT_SUBMISSION_DISABLED"


def test_pilot_feedback_crud_attach_and_audit(client, auth_headers, db_session, sample_documents_dir):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")

    case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    upload = upload_document_from_path(
        client,
        case_id,
        initiator_headers,
        sample_documents_dir / "contract.txt",
        "text/plain",
    )
    assert upload.status_code == 200
    document_id = upload.json()["id"]

    created = client.post(
        "/api/pilot-feedback",
        headers=lawyer_headers,
        json={
            "case_id": case_id,
            "module": "CLAIM",
            "severity": "MEDIUM",
            "title": "Draft needs clearer appendix list",
            "description": "Pilot note",
            "expected_behavior": "Appendix list should be explicit",
            "actual_behavior": "List is too short",
        },
    )
    assert created.status_code == 200
    feedback_id = created.json()["id"]

    listing = client.get(f"/api/pilot-feedback?case_id={case_id}", headers=lawyer_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    attached = client.post(
        f"/api/pilot-feedback/{feedback_id}/attach-screenshot",
        headers=lawyer_headers,
        json={"screenshot_document_id": document_id},
    )
    assert attached.status_code == 200
    assert attached.json()["screenshot_document_id"] == document_id

    updated = client.patch(
        f"/api/pilot-feedback/{feedback_id}",
        headers=admin_headers,
        json={"status": "FIXED"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "FIXED"

    row = db_session.get(PilotFeedback, feedback_id)
    assert row is not None
    assert row.screenshot_document_id == document_id

    audit = client.get("/api/audit", headers=admin_headers)
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()]
    assert "pilot_feedback_created" in actions
    assert "pilot_feedback_updated" in actions
    assert "pilot_feedback_screenshot_attached" in actions


def test_pilot_metrics_and_report_endpoints(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    manager_headers = auth_headers("manager")

    organization_id = create_organization(client, admin_headers, inn="7701234591")
    director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
    happy_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    assign_representation(client, happy_case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)
    assert client.post(f"/api/claims/{happy_case_id}/generate", headers=lawyer_headers).status_code == 200
    assert client.post(f"/api/workflow/{happy_case_id}/approve-claim", headers=lawyer_headers).status_code == 200
    dispatch_id = create_postal_dispatch(client, lawyer_headers, case_id=happy_case_id, organization_id=organization_id, dispatch_kind="claim_copy")
    refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
    upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
    assert client.post(f"/api/workflow/{happy_case_id}/court-package-ready", headers=lawyer_headers).status_code == 200

    blocked_case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
    employee_id = create_employee(client, organization_id, admin_headers)
    signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="AUTHORIZED_EMPLOYEE", employee_id=employee_id)
    create_power_of_attorney(
        client,
        employee_id,
        admin_headers,
        number="POA-EXPIRED-PILOT",
        issued_at="2025-01-01",
        expires_at="2025-12-31",
        authority_scope="SIGN_CLAIM,REPRESENT_IN_COURT",
    )
    assign_representation(client, blocked_case_id, initiator_headers, organization_id=organization_id, signatory_id=signatory_id)
    assert client.post(f"/api/claims/{blocked_case_id}/generate", headers=lawyer_headers).status_code == 200
    blocked = client.post(f"/api/workflow/{blocked_case_id}/approve-claim", headers=lawyer_headers)
    assert blocked.status_code == 400

    feedback = client.post(
        "/api/pilot-feedback",
        headers=lawyer_headers,
        json={
            "case_id": blocked_case_id,
            "module": "AUTHORITY",
            "severity": "HIGH",
            "title": "Authority issue surfaced in pilot",
            "description": "Expected negative path",
            "expected_behavior": "Approval must be blocked",
            "actual_behavior": "Approval blocked",
        },
    )
    assert feedback.status_code == 200

    summary = client.get("/api/pilot-metrics/summary", headers=manager_headers)
    assert summary.status_code == 200
    assert summary.json()["total_cases"] >= 2
    assert summary.json()["blocked_cases"] >= 1
    assert summary.json()["total_feedback_items"] >= 1

    case_metrics = client.get(f"/api/pilot-metrics/cases/{blocked_case_id}", headers=manager_headers)
    assert case_metrics.status_code == 200
    assert case_metrics.json()["blocked_actions"] >= 1
    assert case_metrics.json()["feedback_items"] >= 1

    export_json = client.get("/api/pilot-metrics/export?export_format=json", headers=manager_headers)
    assert export_json.status_code == 200
    assert '"total_cases"' in export_json.text

    export_csv = client.get("/api/pilot-metrics/export?export_format=csv", headers=manager_headers)
    assert export_csv.status_code == 200
    assert "case_id,title,status" in export_csv.text

    report = client.get("/api/pilot-report", headers=manager_headers)
    assert report.status_code == 200
    payload = report.json()
    assert payload["feedback_total"] >= 1
    assert payload["recommendation"] in {"go", "no-go"}


def test_sandbox_flags_default_false(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fns_sandbox_enabled"] is False
    assert payload["russian_post_sandbox_enabled"] is False
    assert payload["court_sandbox_enabled"] is False
    assert payload["real_fns_enabled"] is False
    assert payload["real_post_send_enabled"] is False
    assert payload["court_submission_enabled"] is False


def test_fns_sandbox_disabled_blocks_provider_call(client, auth_headers):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_mode = settings.fns_provider_mode
    original_flag = settings.enable_fns_sandbox
    settings.fns_provider_mode = "FNS_SANDBOX_READY"
    settings.enable_fns_sandbox = False
    try:
        response = client.post("/api/organizations", headers=admin_headers, json={"inn": "7705555555"})
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "FNS_SANDBOX_DISABLED"
    finally:
        settings.fns_provider_mode = original_mode
        settings.enable_fns_sandbox = original_flag


def test_fns_sandbox_test_connection_disabled_status(client, auth_headers):
    admin_headers = auth_headers("admin")
    response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "disabled"
    assert payload["sandbox"] is True
    assert payload["external_calls"] is False


def test_fns_sandbox_credentials_masked(client, auth_headers):
    admin_headers = auth_headers("admin")
    client.put("/api/settings/FNS_SANDBOX_CLIENT_SECRET", headers=admin_headers, json={"value": "sandbox-secret", "description": "sandbox"})
    listing = client.get("/api/settings", headers=admin_headers)
    assert listing.status_code == 200
    item = next(entry for entry in listing.json() if entry["key"] == "FNS_SANDBOX_CLIENT_SECRET")
    assert item["value"] == "[REDACTED]"


def test_russian_post_sandbox_send_requires_dry_run(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    lawyer_headers = auth_headers("lawyer")
    initiator_headers = auth_headers("initiator")
    settings = get_settings()
    original_mode = settings.russian_post_mode
    original_flag = settings.enable_russian_post_sandbox
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_client_secret = settings.russian_post_sandbox_client_secret
    settings.russian_post_mode = "RUSSIAN_POST_SANDBOX_READY"
    settings.enable_russian_post_sandbox = True
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, integration_name="russian_post")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555556")
        case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
        dispatch = client.post(
            "/api/postal-dispatches",
            headers=lawyer_headers,
            json={
                "case_id": case_id,
                "organization_id": organization_id,
                "dispatch_kind": "claim_copy",
                "recipient_name": "OOO Beta",
                "recipient_address": "Moscow",
                "provider_mode": "RUSSIAN_POST_SANDBOX_READY",
                "idempotency_key": "sandbox-send-1",
            },
        )
        assert dispatch.status_code == 200
        blocked = client.post(f"/api/postal-dispatches/{dispatch.json()['id']}/send", headers=lawyer_headers)
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["error_code"] == "POST_SANDBOX_DRY_RUN_REQUIRED"
    finally:
        settings.russian_post_mode = original_mode
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_client_secret


def test_russian_post_sandbox_disabled_blocks_send(client, auth_headers):
    admin_headers = auth_headers("admin")
    lawyer_headers = auth_headers("lawyer")
    initiator_headers = auth_headers("initiator")
    settings = get_settings()
    original_mode = settings.russian_post_mode
    original_flag = settings.enable_russian_post_sandbox
    settings.russian_post_mode = "RUSSIAN_POST_SANDBOX_READY"
    settings.enable_russian_post_sandbox = False
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555557")
        case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
        response = client.post(
            "/api/postal-dispatches",
            headers=lawyer_headers,
            json={
                "case_id": case_id,
                "organization_id": organization_id,
                "dispatch_kind": "claim_copy",
                "recipient_name": "OOO Beta",
                "recipient_address": "Moscow",
                "provider_mode": "RUSSIAN_POST_SANDBOX_READY",
                "idempotency_key": "sandbox-disabled-1",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "POST_SANDBOX_DISABLED"
    finally:
        settings.russian_post_mode = original_mode
        settings.enable_russian_post_sandbox = original_flag


def test_russian_post_sandbox_idempotency_key_required(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    lawyer_headers = auth_headers("lawyer")
    initiator_headers = auth_headers("initiator")
    settings = get_settings()
    original_mode = settings.russian_post_mode
    original_flag = settings.enable_russian_post_sandbox
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_client_secret = settings.russian_post_sandbox_client_secret
    settings.russian_post_mode = "RUSSIAN_POST_SANDBOX_READY"
    settings.enable_russian_post_sandbox = True
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, integration_name="russian_post")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555558")
        case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
        response = client.post(
            "/api/postal-dispatches",
            headers=lawyer_headers,
            json={
                "case_id": case_id,
                "organization_id": organization_id,
                "dispatch_kind": "claim_copy",
                "recipient_name": "OOO Beta",
                "recipient_address": "Moscow",
                "provider_mode": "RUSSIAN_POST_SANDBOX_READY",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "POST_IDEMPOTENCY_KEY_REQUIRED"
    finally:
        settings.russian_post_mode = original_mode
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_client_secret


def test_court_sandbox_disabled_blocks_import(client, auth_headers):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_mode = settings.court_provider_mode
    original_flag = settings.enable_court_sandbox
    settings.court_provider_mode = "COURT_SANDBOX_READY"
    settings.enable_court_sandbox = False
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555559")
        response = client.post(
            "/api/court-import/jobs",
            headers=admin_headers,
            json={
                "organization_id": organization_id,
                "inn": "7705555559",
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "participation_role": "claimant",
                "provider_mode": "COURT_SANDBOX_READY",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error_code"] == "COURT_SANDBOX_DISABLED"
    finally:
        settings.court_provider_mode = original_mode
        settings.enable_court_sandbox = original_flag


def test_court_submission_disabled_even_in_sandbox(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    settings = get_settings()
    original_mode = settings.court_provider_mode
    original_flag = settings.enable_court_sandbox
    settings.court_provider_mode = "COURT_SANDBOX_READY"
    settings.enable_court_sandbox = True
    create_sandbox_approval(db_session, integration_name="court")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555560")
        director_signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
        case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
        assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=director_signatory_id)
        assert client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers).status_code == 200
        assert client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers).status_code == 200
        dispatch_id = create_postal_dispatch(client, lawyer_headers, case_id=case_id, organization_id=organization_id, dispatch_kind="claim_copy")
        refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
        upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
        package = client.post("/api/court-submission", headers=lawyer_headers, json={"case_id": case_id, "note": "manual package"})
        assert package.status_code == 200
        blocked = client.post(f"/api/court-submission/{package.json()['id']}/submit", headers=lawyer_headers)
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["error_code"] == "COURT_SUBMISSION_DISABLED"
    finally:
        settings.court_provider_mode = original_mode
        settings.enable_court_sandbox = original_flag


def test_public_kad_search_disabled(client, auth_headers):
    admin_headers = auth_headers("admin")
    organization_id = create_organization(client, admin_headers, inn="7705555561")
    response = client.post(
        "/api/court-import/jobs",
        headers=admin_headers,
        json={
            "organization_id": organization_id,
            "inn": "7705555561",
            "date_from": "2026-05-01",
            "date_to": "2026-05-31",
            "participation_role": "claimant",
            "provider_mode": "PUBLIC_SEARCH",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error_code"] == "COURT_UNSAFE_MODE_BLOCKED"


def test_sandbox_readiness_endpoint_no_secrets(client, auth_headers):
    admin_headers = auth_headers("admin")
    response = client.get("/api/integration-readiness/sandbox", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["fns"]["sandbox_flag"] is False
    assert payload["russian_post"]["test_connection_status"] == "disabled"
    assert "secret" not in str(payload).lower()
    assert "token" not in str(payload).lower()


def test_sandbox_approval_required(client, auth_headers):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "stub"
    settings.fns_sandbox_client_id = "stub"
    settings.fns_sandbox_client_secret = "stub"
    try:
        response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "approval_required"
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_sandbox_approval_expired_blocks_enablement(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "stub"
    settings.fns_sandbox_client_id = "stub"
    settings.fns_sandbox_client_secret = "stub"
    create_sandbox_approval(db_session, integration_name="fns", expires_in_days=-1)
    try:
        response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "approval_required"
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_integration_request_log_no_sandbox_credentials(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
    assert response.status_code == 200
    logs = db_session.scalars(select(IntegrationRequestLog).where(IntegrationRequestLog.operation == "test_connection")).all()
    assert logs
    serialized = " ".join([log.safe_request_metadata_json + log.safe_response_metadata_json + log.error_message for log in logs]).lower()
    for forbidden in ("sandbox-secret", "token", "client_secret", "password"):
        assert forbidden not in serialized


def test_integration_approval_workflow(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    created = client.post(
        "/api/integration-approvals",
        headers=admin_headers,
        json={
            "integration_name": "FNS",
            "environment": "SANDBOX",
            "reason": "Need sandbox lookup validation",
            "expires_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        },
    )
    assert created.status_code == 200
    approval_id = created.json()["id"]
    assert created.json()["status"] == "REQUESTED"

    listing = client.get("/api/integration-approvals?integration_name=FNS", headers=admin_headers)
    assert listing.status_code == 200
    assert any(item["id"] == approval_id for item in listing.json())

    approved = client.post(
        f"/api/integration-approvals/{approval_id}/approve",
        headers=admin_headers,
        json={"reason": "Approved for safe sandbox testing"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    active = client.get("/api/integration-approvals/active", headers=admin_headers)
    assert active.status_code == 200
    assert any(item["id"] == approval_id for item in active.json())

    revoked = client.post(
        f"/api/integration-approvals/{approval_id}/revoke",
        headers=admin_headers,
        json={"reason": "Sandbox window closed"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"

    audit_actions = [
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "integration_approval",
                AuditLog.entity_id == str(approval_id),
            )
        ).all()
    ]
    assert "integration_approval_requested" in audit_actions
    assert "integration_approval_approved" in audit_actions
    assert "integration_approval_revoked" in audit_actions


def test_production_approval_remains_disabled(client, auth_headers):
    admin_headers = auth_headers("admin")
    created = client.post(
        "/api/integration-approvals",
        headers=admin_headers,
        json={
            "integration_name": "RUSSIAN_POST",
            "environment": "PRODUCTION",
            "reason": "Should stay disabled",
            "expires_at": None,
        },
    )
    assert created.status_code == 200
    assert created.json()["status"] == "REJECTED"


def test_integration_readiness_credentials_endpoint(client, auth_headers):
    admin_headers = auth_headers("admin")
    response = client.get("/api/integration-readiness/credentials", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["fns"]["sandbox_credentials_present"] is False
    assert payload["fns"]["production_credentials_present"] is False
    assert payload["russian_post"]["sandbox_credentials_present"] is False
    assert payload["court_arbitr"]["production_credentials_present"] is False
    serialized = json.dumps(payload).lower()
    for forbidden in ("token", "secret", "password", "client_secret"):
        assert forbidden not in serialized


def test_fns_sandbox_lookup_logs_integration_request(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_mode = settings.fns_provider_mode
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.fns_provider_mode = "FNS_SANDBOX_READY"
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "sandbox-token"
    settings.fns_sandbox_client_id = "sandbox-client"
    settings.fns_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, integration_name="FNS")
    try:
        response = client.post("/api/organizations/lookup-by-inn", headers=admin_headers, json={"inn": "7705555570"})
        assert response.status_code == 200
        row = db_session.scalar(
            select(IntegrationRequestLog)
            .where(
                IntegrationRequestLog.integration_name == "fns",
                IntegrationRequestLog.operation == "lookup_preview",
            )
            .order_by(IntegrationRequestLog.id.desc())
        )
        assert row is not None
        assert row.status == "SUCCESS"
        serialized = " ".join(
            [
                row.safe_request_metadata_json,
                row.safe_response_metadata_json,
                row.error_message,
            ]
        ).lower()
        for forbidden in ("sandbox-token", "sandbox-secret", "sandbox-client", "client_secret", "password"):
            assert forbidden not in serialized
    finally:
        settings.fns_provider_mode = original_mode
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.models import IntegrationApproval, IntegrationApprovalEnvironment, IntegrationApprovalStatus, IntegrationRequestLog
from app.tests.helpers import (
    assign_representation,
    create_case,
    create_organization,
    create_postal_dispatch,
    create_signatory,
    refresh_postal_dispatch_status,
    upload_postal_proof,
)


def create_sandbox_approval(db_session, integration_name: str, expires_in_days: int = 7):
    approval = IntegrationApproval(
        integration_name=integration_name,
        environment=IntegrationApprovalEnvironment.SANDBOX.value,
        requested_by_id=1,
        approved_by_id=1,
        status=IntegrationApprovalStatus.APPROVED.value,
        reason="sandbox credential validation",
        approved_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(approval)
    db_session.commit()
    return approval


def test_fns_sandbox_test_connection_with_credentials(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "sandbox-token"
    settings.fns_sandbox_client_id = "sandbox-client"
    settings.fns_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "FNS")
    try:
        response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["sandbox"] is True
        assert payload["credentials_present"] is True
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_fns_sandbox_lookup_dry_run(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "sandbox-token"
    settings.fns_sandbox_client_id = "sandbox-client"
    settings.fns_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "FNS")
    try:
        response = client.post("/api/organizations/lookup-by-inn?sandbox=true&dry_run=true", headers=admin_headers, json={"inn": "7705555570"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "FNS_SANDBOX_READY"
        assert payload["inn"] == "7705555570"
        row = db_session.scalar(
            select(IntegrationRequestLog)
            .where(IntegrationRequestLog.integration_name == "fns", IntegrationRequestLog.operation == "lookup_preview")
            .order_by(IntegrationRequestLog.id.desc())
        )
        assert row is not None
        assert "\"dry_run\": true" in row.safe_request_metadata_json.lower()
        assert "sandbox-secret" not in row.safe_request_metadata_json.lower()
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_post_sandbox_test_connection_with_credentials(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_russian_post_sandbox
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_secret = settings.russian_post_sandbox_client_secret
    settings.enable_russian_post_sandbox = True
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "RUSSIAN_POST")
    try:
        response = client.post("/api/russian-post/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["credentials_present"] is True
        assert payload["sandbox"] is True
    finally:
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_secret


def test_post_sandbox_normalize_address(client, auth_headers, db_session):
    lawyer_headers = auth_headers("lawyer")
    settings = get_settings()
    original_flag = settings.enable_russian_post_sandbox
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_secret = settings.russian_post_sandbox_client_secret
    settings.enable_russian_post_sandbox = True
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "RUSSIAN_POST")
    try:
        response = client.post(
            "/api/russian-post/normalize-address?sandbox=true",
            headers=lawyer_headers,
            json={"address": " Moscow, Test street, 1 "},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["normalized_address"] == "Moscow, Test street, 1"
    finally:
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_secret


def test_post_sandbox_create_letter_dry_run(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    settings = get_settings()
    original_flag = settings.enable_russian_post_sandbox
    original_mode = settings.russian_post_mode
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_secret = settings.russian_post_sandbox_client_secret
    settings.enable_russian_post_sandbox = True
    settings.russian_post_mode = "RUSSIAN_POST_SANDBOX_READY"
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "RUSSIAN_POST")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555580")
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
                "idempotency_key": "sandbox-dry-run-1",
            },
        )
        assert dispatch.status_code == 200
        dry_run = client.post(
            f"/api/postal-dispatches/{dispatch.json()['id']}/send?dry_run=true",
            headers=lawyer_headers,
        )
        assert dry_run.status_code == 200
        payload = dry_run.json()
        assert payload["dry_run"] is True
        assert payload["safe_preview_json"]["provider_mode"] == "RUSSIAN_POST_SANDBOX_READY"
    finally:
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_mode = original_mode
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_secret


def test_post_sandbox_non_dry_run_send_blocked(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    settings = get_settings()
    original_flag = settings.enable_russian_post_sandbox
    original_mode = settings.russian_post_mode
    original_app_token = settings.russian_post_sandbox_app_token
    original_user_key = settings.russian_post_sandbox_user_key
    original_secret = settings.russian_post_sandbox_client_secret
    settings.enable_russian_post_sandbox = True
    settings.russian_post_mode = "RUSSIAN_POST_SANDBOX_READY"
    settings.russian_post_sandbox_app_token = "sandbox-app-token"
    settings.russian_post_sandbox_user_key = "sandbox-user-key"
    settings.russian_post_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "RUSSIAN_POST")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555581")
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
                "idempotency_key": "sandbox-dry-run-2",
            },
        )
        assert dispatch.status_code == 200
        blocked = client.post(f"/api/postal-dispatches/{dispatch.json()['id']}/send", headers=lawyer_headers)
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["error_code"] == "POST_SANDBOX_DRY_RUN_REQUIRED"
    finally:
        settings.enable_russian_post_sandbox = original_flag
        settings.russian_post_mode = original_mode
        settings.russian_post_sandbox_app_token = original_app_token
        settings.russian_post_sandbox_user_key = original_user_key
        settings.russian_post_sandbox_client_secret = original_secret


def test_court_sandbox_test_connection_with_credentials(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_court_sandbox
    original_token = settings.court_sandbox_token
    original_api_key = settings.court_provider_sandbox_api_key
    original_secret = settings.court_sandbox_client_secret
    settings.enable_court_sandbox = True
    settings.court_sandbox_token = "sandbox-token"
    settings.court_provider_sandbox_api_key = "sandbox-api-key"
    settings.court_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "COURT_ARBITR")
    try:
        response = client.post("/api/court-arbitr/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["credentials_present"] is True
    finally:
        settings.enable_court_sandbox = original_flag
        settings.court_sandbox_token = original_token
        settings.court_provider_sandbox_api_key = original_api_key
        settings.court_sandbox_client_secret = original_secret


def test_court_sandbox_import_dry_run(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_court_sandbox
    original_mode = settings.court_provider_mode
    original_token = settings.court_sandbox_token
    original_api_key = settings.court_provider_sandbox_api_key
    original_secret = settings.court_sandbox_client_secret
    settings.enable_court_sandbox = True
    settings.court_provider_mode = "COURT_SANDBOX_READY"
    settings.court_sandbox_token = "sandbox-token"
    settings.court_provider_sandbox_api_key = "sandbox-api-key"
    settings.court_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "COURT_ARBITR")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555582")
        response = client.post(
            "/api/court-import/jobs?sandbox=true&dry_run=true",
            headers=admin_headers,
            json={
                "organization_id": organization_id,
                "inn": "7705555582",
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
                "participation_role": "claimant",
            },
        )
        assert response.status_code == 200
        assert response.json()["source"] == "COURT_SANDBOX_READY"
    finally:
        settings.enable_court_sandbox = original_flag
        settings.court_provider_mode = original_mode
        settings.court_sandbox_token = original_token
        settings.court_provider_sandbox_api_key = original_api_key
        settings.court_sandbox_client_secret = original_secret


def test_court_submission_non_dry_run_blocked(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    initiator_headers = auth_headers("initiator")
    lawyer_headers = auth_headers("lawyer")
    settings = get_settings()
    original_flag = settings.enable_court_sandbox
    original_mode = settings.court_provider_mode
    original_token = settings.court_sandbox_token
    original_api_key = settings.court_provider_sandbox_api_key
    original_secret = settings.court_sandbox_client_secret
    settings.enable_court_sandbox = True
    settings.court_provider_mode = "COURT_SANDBOX_READY"
    settings.court_sandbox_token = "sandbox-token"
    settings.court_provider_sandbox_api_key = "sandbox-api-key"
    settings.court_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "COURT_ARBITR")
    try:
        organization_id = create_organization(client, admin_headers, inn="7705555583")
        signatory_id = create_signatory(client, organization_id, admin_headers, signatory_type="DIRECTOR")
        case_id = create_case(client, initiator_headers, assigned_lawyer_id=2)
        assign_representation(client, case_id, initiator_headers, organization_id=organization_id, signatory_id=signatory_id)
        assert client.post(f"/api/claims/{case_id}/generate", headers=lawyer_headers).status_code == 200
        assert client.post(f"/api/workflow/{case_id}/approve-claim", headers=lawyer_headers).status_code == 200
        dispatch_id = create_postal_dispatch(client, lawyer_headers, case_id=case_id, organization_id=organization_id, dispatch_kind="claim_copy")
        refresh_postal_dispatch_status(client, lawyer_headers, dispatch_id=dispatch_id)
        upload_postal_proof(client, lawyer_headers, dispatch_id=dispatch_id)
        package = client.post("/api/court-submission", headers=lawyer_headers, json={"case_id": case_id, "note": "sandbox manual package"})
        assert package.status_code == 200
        blocked = client.post(f"/api/court-submission/{package.json()['id']}/submit", headers=lawyer_headers)
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["error_code"] == "COURT_SUBMISSION_DISABLED"
    finally:
        settings.enable_court_sandbox = original_flag
        settings.court_provider_mode = original_mode
        settings.court_sandbox_token = original_token
        settings.court_provider_sandbox_api_key = original_api_key
        settings.court_sandbox_client_secret = original_secret


def test_sandbox_readiness_updates_after_test_connection(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "sandbox-token"
    settings.fns_sandbox_client_id = "sandbox-client"
    settings.fns_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "FNS")
    try:
        client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        readiness = client.get("/api/integration-readiness/sandbox", headers=admin_headers)
        assert readiness.status_code == 200
        payload = readiness.json()["fns"]
        assert payload["last_test_connection_status"] == "ok"
        assert payload["last_test_connection_at"] is not None
        assert payload["last_error_code"] in {None, ""}
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_sandbox_test_results_no_secrets(client, auth_headers, db_session):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_flag = settings.enable_fns_sandbox
    original_token = settings.fns_sandbox_token
    original_client_id = settings.fns_sandbox_client_id
    original_client_secret = settings.fns_sandbox_client_secret
    settings.enable_fns_sandbox = True
    settings.fns_sandbox_token = "sandbox-token"
    settings.fns_sandbox_client_id = "sandbox-client"
    settings.fns_sandbox_client_secret = "sandbox-secret"
    create_sandbox_approval(db_session, "FNS")
    try:
        client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        readiness = client.get("/api/integration-readiness/sandbox", headers=admin_headers)
        assert readiness.status_code == 200
        serialized = json.dumps(readiness.json()).lower()
        for forbidden in ("sandbox-token", "sandbox-client", "sandbox-secret", "client_secret", "password"):
            assert forbidden not in serialized
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret

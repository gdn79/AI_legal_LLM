import json
import sys
from pathlib import Path

from app.core.config import get_settings

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_sandbox_pilot import build_console_summary, build_markdown_report, enforce_live_mode_requirements  # noqa: E402


def test_sandbox_pilot_metrics_no_secrets(client, auth_headers):
    admin_headers = auth_headers("admin")
    response = client.get("/api/sandbox-pilot/metrics", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload).lower()
    assert "secrets_leakage_findings" in serialized
    for forbidden in ("real-sandbox-token", "real-sandbox-secret", "real-sandbox-password"):
        assert forbidden not in serialized


def test_sandbox_pilot_report_contains_no_secrets(client, auth_headers):
    admin_headers = auth_headers("admin")
    settings = get_settings()
    original_values = {
        "fns_sandbox_token": settings.fns_sandbox_token,
        "fns_sandbox_client_id": settings.fns_sandbox_client_id,
        "fns_sandbox_client_secret": settings.fns_sandbox_client_secret,
    }
    settings.fns_sandbox_token = "real-sandbox-token"
    settings.fns_sandbox_client_id = "real-sandbox-client"
    settings.fns_sandbox_client_secret = "real-sandbox-secret"
    try:
        response = client.get("/api/sandbox-pilot/report", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        serialized = json.dumps(payload).lower()
        for forbidden in (
            "real-sandbox-token",
            "real-sandbox-client",
            "real-sandbox-secret",
            "password",
            "client_secret",
        ):
            assert forbidden not in serialized
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)


def test_sandbox_run_script_does_not_print_secrets():
    payload = {
        "mode": "safe-skipped",
        "report": {
            "status": "PASSED_WITH_ISSUES",
            "production_api": "disabled",
            "real_sandbox_credentials": "absent",
            "live_sandbox_calls": "safe-skipped",
            "court_submission": "disabled",
            "fns": {
                "approval_active": False,
                "approval_status": "REQUESTED",
                "last_test_connection_status": "credentials_missing",
                "test_connection_status": "credentials_missing",
            },
            "russian_post": {
                "approval_active": False,
                "approval_status": "REQUESTED",
                "last_test_connection_status": "credentials_missing",
                "test_connection_status": "credentials_missing",
            },
            "court_arbitr": {
                "approval_active": False,
                "approval_status": "REQUESTED",
                "last_test_connection_status": "disabled",
                "test_connection_status": "disabled",
            },
            "export_generated": False,
            "audit_ok": True,
            "integration_logs_ok": True,
            "secrets_leakage": "none",
            "issues": [],
            "recommendation": "repeat with real sandbox credentials",
        },
        "metrics": {
            "sandbox_test_connections_total": 3,
            "sandbox_test_connections_skipped": 3,
            "sandbox_test_connections_failed": 0,
            "sandbox_dry_runs_total": 0,
            "sandbox_dangerous_operations_blocked": 2,
            "credentials_missing_count": 3,
            "approval_required_count": 0,
            "approval_expired_count": 0,
            "secrets_leakage_findings": 0,
        },
        "scenarios": {
            "LSP-001": {"status": "PASSED", "notes": "No credentials available."},
            "LSP-002": {"status": "PASSED", "notes": "Approval lifecycle validated."},
        },
    }
    markdown = build_markdown_report(payload)
    summary = build_console_summary(payload)
    for forbidden in ("real-sandbox-token", "real-sandbox-secret", "real-sandbox-password"):
        assert forbidden not in markdown.lower()
        assert forbidden not in summary.lower()


def test_sandbox_live_mode_requires_credentials():
    state, message = enforce_live_mode_requirements(
        credentials_state="absent",
        require_credentials=True,
        allow_skip=False,
    )
    assert state == "blocked"
    assert "required" in message.lower()


def test_sandbox_live_mode_requires_approval(client, auth_headers, db_session):
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
    try:
        response = client.post("/api/fns/test-connection?sandbox=true", headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "approval_required"
    finally:
        settings.enable_fns_sandbox = original_flag
        settings.fns_sandbox_token = original_token
        settings.fns_sandbox_client_id = original_client_id
        settings.fns_sandbox_client_secret = original_client_secret


def test_sandbox_live_mode_safe_skips_without_credentials():
    state, message = enforce_live_mode_requirements(
        credentials_state="absent",
        require_credentials=False,
        allow_skip=True,
    )
    assert state == "skipped"
    assert "skipped safely" in message.lower()

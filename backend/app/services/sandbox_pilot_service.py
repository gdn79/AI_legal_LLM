from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AuditLog, ExportPackage, IntegrationRequestLog
from app.schemas.sandbox_pilot import (
    SandboxPilotIntegrationCheckRead,
    SandboxPilotMetricsRead,
    SandboxPilotReportRead,
)
from app.services.sandbox_service import SandboxService


class SandboxPilotService:
    SENSITIVE_SETTING_NAMES = (
        "fns_sandbox_token",
        "fns_sandbox_client_id",
        "fns_sandbox_client_secret",
        "russian_post_sandbox_app_token",
        "russian_post_sandbox_user_key",
        "russian_post_sandbox_client_secret",
        "court_sandbox_token",
        "court_provider_sandbox_api_key",
        "court_sandbox_client_secret",
    )
    SANDBOX_ERROR_CODES = {"CREDENTIALS_MISSING", "APPROVAL_REQUIRED", "APPROVAL_EXPIRED", "SANDBOX_DISABLED"}
    BLOCKED_ERROR_CODES = {
        "POST_SANDBOX_DRY_RUN_REQUIRED",
        "POST_SEND_DISABLED",
        "COURT_SUBMISSION_DISABLED",
        "COURT_UNSAFE_MODE_BLOCKED",
        "POST_IDEMPOTENCY_KEY_REQUIRED",
    }
    SKIPPED_STATUSES = {"disabled", "credentials_missing", "approval_required"}

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.sandbox = SandboxService(db)

    def _integration_logs(self) -> list[IntegrationRequestLog]:
        return list(self.db.scalars(select(IntegrationRequestLog).order_by(IntegrationRequestLog.created_at.desc())).all())

    def _audit_logs(self) -> list[AuditLog]:
        return list(self.db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc())).all())

    def _secret_values(self) -> list[str]:
        values: list[str] = []
        for name in self.SENSITIVE_SETTING_NAMES:
            value = getattr(self.settings, name, "")
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
        return values

    def _secret_leakage_findings(self) -> int:
        secret_values = self._secret_values()
        if not secret_values:
            return 0
        haystacks = []
        for item in self._integration_logs():
            haystacks.append(item.safe_request_metadata_json or "")
            haystacks.append(item.safe_response_metadata_json or "")
            haystacks.append(item.error_message or "")
        for item in self._audit_logs():
            haystacks.append(item.details or "")
        joined = "\n".join(haystacks)
        return sum(1 for value in secret_values if value in joined)

    def _production_flags_enabled_count(self) -> int:
        return sum(
            1
            for enabled in (
                self.settings.enable_real_fns,
                self.settings.enable_real_post_send,
                self.settings.enable_real_court_search,
                self.settings.enable_court_submission,
                self.settings.enable_public_kad_search,
            )
            if enabled
        )

    def _readiness_item(self, integration_name: str) -> SandboxPilotIntegrationCheckRead:
        item = self.sandbox.readiness_item(integration_name)
        return SandboxPilotIntegrationCheckRead(
            credentials_present=item.credentials_present,
            approval_active=item.active_approval,
            approval_status=item.approval_status,
            approval_expires_at=item.approval_expires_at,
            test_connection_status=item.test_connection_status,
            last_test_connection_status=item.last_test_connection_status,
            last_test_connection_at=item.last_test_connection_at,
            last_error_code=item.last_error_code,
            ready_for_sandbox=item.ready_for_sandbox,
            blocking_reasons=item.blocking_reasons,
        )

    def _credentials_state(self) -> str:
        states = [
            self.sandbox.credentials_present("fns"),
            self.sandbox.credentials_present("russian_post"),
            self.sandbox.credentials_present("court"),
        ]
        if all(states):
            return "present"
        if any(states):
            return "partial"
        return "absent"

    def _live_sandbox_state(self) -> str:
        logs = [
            item
            for item in self._integration_logs()
            if item.operation == "test_connection" and "SANDBOX" in item.mode
        ]
        if any(item.status == "SUCCESS" for item in logs):
            return "executed"
        return "safe-skipped"

    def metrics(self) -> SandboxPilotMetricsRead:
        logs = self._integration_logs()
        sandbox_test_logs = [item for item in logs if item.operation == "test_connection" and "SANDBOX" in item.mode]
        sandbox_dry_runs = [
            item
            for item in logs
            if (
                item.operation.endswith("dry_run")
                or ("SANDBOX" in item.mode and "\"dry_run\": true" in (item.safe_request_metadata_json or "").lower())
            )
        ]
        skipped = 0
        failed = 0
        credentials_missing_count = 0
        approval_required_count = 0
        approval_expired_count = 0
        blocked_count = 0
        for item in logs:
            response_status = ""
            if item.safe_response_metadata_json:
                try:
                    response_status = str(json.loads(item.safe_response_metadata_json).get("status", "")).lower()
                except json.JSONDecodeError:
                    response_status = ""
            if item in sandbox_test_logs and response_status in self.SKIPPED_STATUSES:
                skipped += 1
            elif item in sandbox_test_logs and item.status == "FAILED":
                failed += 1
            if "CREDENTIALS_MISSING" in (item.error_code or "") or response_status == "credentials_missing":
                credentials_missing_count += 1
            if "APPROVAL_REQUIRED" in (item.error_code or "") or response_status == "approval_required":
                approval_required_count += 1
            if "APPROVAL_EXPIRED" in (item.error_code or ""):
                approval_expired_count += 1
            if item.error_code in self.BLOCKED_ERROR_CODES:
                blocked_count += 1
        readiness = self.sandbox.readiness()
        if readiness.fns.approval_status == "EXPIRED":
            approval_expired_count += 1
        if readiness.russian_post.approval_status == "EXPIRED":
            approval_expired_count += 1
        if readiness.court.approval_status == "EXPIRED":
            approval_expired_count += 1
        return SandboxPilotMetricsRead(
            generated_at=datetime.now(UTC),
            sandbox_test_connections_total=len(sandbox_test_logs),
            sandbox_test_connections_skipped=skipped,
            sandbox_test_connections_failed=failed,
            sandbox_dry_runs_total=len(sandbox_dry_runs),
            sandbox_dangerous_operations_blocked=blocked_count,
            credentials_missing_count=credentials_missing_count,
            approval_required_count=approval_required_count,
            approval_expired_count=approval_expired_count,
            secrets_leakage_findings=self._secret_leakage_findings(),
            production_flags_enabled_count=self._production_flags_enabled_count(),
            real_sandbox_credentials=self._credentials_state(),
            live_sandbox_calls=self._live_sandbox_state(),
        )

    def _latest_export_ok(self) -> bool:
        export = self.db.scalar(select(ExportPackage).order_by(ExportPackage.created_at.desc()))
        if export is None:
            return False
        archive_path = Path(export.archive_path)
        if not archive_path.exists():
            return False
        try:
            with ZipFile(archive_path) as archive:
                names = archive.namelist()
            sections = {name.split("/")[1] for name in names if "/" in name}
            return len(sections) >= 12
        except Exception:
            return False

    def _audit_ok(self) -> bool:
        actions = {item.action for item in self._audit_logs()}
        required = {"fns_test_connection", "russian_post_test_connection", "court_arbitr_test_connection"}
        return bool(actions.intersection(required))

    def _integration_logs_ok(self) -> bool:
        logs = self._integration_logs()
        return any(item.operation == "test_connection" and "SANDBOX" in item.mode for item in logs)

    def report(self) -> SandboxPilotReportRead:
        metrics = self.metrics()
        fns = self._readiness_item("fns")
        russian_post = self._readiness_item("russian_post")
        court = self._readiness_item("court")
        issues: list[dict[str, str]] = []
        if metrics.real_sandbox_credentials != "present":
            issues.append(
                {
                    "severity": "MEDIUM",
                    "module": "CREDENTIALS",
                    "description": "Real sandbox credentials are absent or partial in the current environment.",
                    "recommendation": "Request or inject sandbox credentials through env/secrets before limited live exchange.",
                }
            )
        if metrics.sandbox_test_connections_failed > 0:
            issues.append(
                {
                    "severity": "MEDIUM",
                    "module": "INTEGRATIONS",
                    "description": "At least one sandbox test connection ended in failed status.",
                    "recommendation": "Inspect readiness blocking reasons and latest integration logs.",
                }
            )
        if metrics.secrets_leakage_findings > 0:
            issues.append(
                {
                    "severity": "BLOCKER",
                    "module": "SECURITY",
                    "description": "Sensitive sandbox credential values were detected in logs.",
                    "recommendation": "Stop pilot and fix secret scrubbing before any further sandbox use.",
                }
            )
        if metrics.production_flags_enabled_count > 0:
            issues.append(
                {
                    "severity": "BLOCKER",
                    "module": "SECURITY",
                    "description": "One or more production flags are enabled.",
                    "recommendation": "Disable production flags before any sandbox pilot continuation.",
                }
            )

        if metrics.secrets_leakage_findings > 0 or metrics.production_flags_enabled_count > 0:
            status = "FAILED"
            recommendation = "do not proceed"
        elif metrics.real_sandbox_credentials == "absent" or metrics.live_sandbox_calls == "safe-skipped":
            status = "PASSED_WITH_ISSUES"
            recommendation = "repeat with real sandbox credentials"
        else:
            status = "PASSED"
            recommendation = "proceed to limited live sandbox exchange"

        return SandboxPilotReportRead(
            generated_at=datetime.now(UTC),
            status=status,
            production_api="disabled",
            real_sandbox_credentials=metrics.real_sandbox_credentials,
            live_sandbox_calls=metrics.live_sandbox_calls,
            court_submission="disabled",
            fns=fns,
            russian_post=russian_post,
            court_arbitr=court,
            end_to_end_status="ok" if self._latest_export_ok() else "not_verified",
            export_generated=self._latest_export_ok(),
            audit_ok=self._audit_ok(),
            integration_logs_ok=self._integration_logs_ok(),
            secrets_leakage="none" if metrics.secrets_leakage_findings == 0 else "detected",
            metrics=metrics,
            issues=issues,
            recommendation=recommendation,
        )

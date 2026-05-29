from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import IntegrationApproval, IntegrationApprovalEnvironment, IntegrationApprovalStatus
from app.schemas.integration import (
    IntegrationCredentialsStatusItemRead,
    IntegrationCredentialsStatusRead,
    SandboxReadinessItemRead,
    SandboxReadinessRead,
)
from app.services.integration_service import IntegrationService
from app.services.integration_approval_service import INTEGRATION_NAME_MAP


class SandboxService:
    def __init__(self, db: Session):
        self.db = db
        self.settings: Settings = get_settings()
        self.integration = IntegrationService(db)

    @staticmethod
    def _integration_key(integration_name: str) -> str:
        key = integration_name.strip().lower()
        if key in {"fns", "russian_post", "court"}:
            return key
        normalized = INTEGRATION_NAME_MAP.get(integration_name.strip(), integration_name.strip())
        return {
            "FNS": "fns",
            "RUSSIAN_POST": "russian_post",
            "COURT_ARBITR": "court",
        }.get(normalized, key)

    @staticmethod
    def _approval_names(integration_name: str) -> set[str]:
        key = SandboxService._integration_key(integration_name)
        return {
            "fns": {"fns", "FNS"},
            "russian_post": {"russian_post", "RUSSIAN_POST"},
            "court": {"court", "court_arbitr", "COURT_ARBITR"},
        }[key]

    def approval_status(self, integration_name: str) -> str:
        approval = self.latest_approval(integration_name)
        if approval is None:
            return IntegrationApprovalStatus.REQUESTED.value
        if approval.status != IntegrationApprovalStatus.APPROVED.value:
            return approval.status
        if approval.expires_at is not None:
            expires_at = approval.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < datetime.now(UTC):
                if approval.status != IntegrationApprovalStatus.EXPIRED.value:
                    approval.status = IntegrationApprovalStatus.EXPIRED.value
                    approval.updated_at = datetime.now(UTC)
                    self.db.add(approval)
                    self.db.commit()
                return IntegrationApprovalStatus.EXPIRED.value
        return approval.status

    def latest_approval(self, integration_name: str) -> IntegrationApproval | None:
        return self.db.scalar(
            select(IntegrationApproval)
            .where(
                IntegrationApproval.integration_name.in_(self._approval_names(integration_name)),
                IntegrationApproval.environment == IntegrationApprovalEnvironment.SANDBOX.value,
            )
            .order_by(IntegrationApproval.created_at.desc())
        )

    def has_active_approval(self, integration_name: str) -> bool:
        return self.approval_status(integration_name) == IntegrationApprovalStatus.APPROVED.value

    def credentials_present(self, integration_name: str) -> bool:
        integration_name = self._integration_key(integration_name)
        if integration_name == "fns":
            return all(
                [
                    bool(self.settings.fns_sandbox_token.strip()),
                    bool(self.settings.fns_sandbox_client_id.strip()),
                    bool(self.settings.fns_sandbox_client_secret.strip()),
                ]
            )
        if integration_name == "russian_post":
            return all(
                [
                    bool(self.settings.russian_post_sandbox_app_token.strip()),
                    bool(self.settings.russian_post_sandbox_user_key.strip()),
                    bool(self.settings.russian_post_sandbox_client_secret.strip()),
                ]
            )
        if integration_name == "court":
            return any(
                [
                    bool(self.settings.court_sandbox_token.strip()),
                    bool(self.settings.court_provider_sandbox_api_key.strip()),
                    bool(self.settings.court_sandbox_client_secret.strip()),
                ]
            )
        return False

    def sandbox_flag(self, integration_name: str) -> bool:
        integration_name = self._integration_key(integration_name)
        return {
            "fns": self.settings.enable_fns_sandbox,
            "russian_post": self.settings.enable_russian_post_sandbox,
            "court": self.settings.enable_court_sandbox,
        }[integration_name]

    def sandbox_mode(self, integration_name: str) -> str:
        integration_name = self._integration_key(integration_name)
        return {
            "fns": self.settings.fns_provider_mode,
            "russian_post": self.settings.russian_post_mode,
            "court": self.settings.court_provider_mode,
        }[integration_name]

    def provider_name(self, integration_name: str) -> str:
        integration_name = self._integration_key(integration_name)
        return {
            "fns": self.settings.fns_provider,
            "russian_post": self.settings.russian_post_provider,
            "court": self.settings.court_arbitr_provider,
        }[integration_name]

    def production_credentials_present(self, integration_name: str) -> bool:
        integration_name = self._integration_key(integration_name)
        if integration_name == "fns":
            return False
        if integration_name == "russian_post":
            return all(
                [
                    bool(self.settings.russian_post_app_token.strip()),
                    bool(self.settings.russian_post_user_key.strip()),
                ]
            )
        if integration_name == "court":
            return False
        return False

    def readiness_item(self, integration_name: str) -> SandboxReadinessItemRead:
        flag = self.sandbox_flag(integration_name)
        credentials_present = self.credentials_present(integration_name)
        approval_status = self.approval_status(integration_name)
        approval = self.latest_approval(integration_name)
        last_log = self.integration.latest_log(integration_name=integration_name, operation="test_connection")
        last_failed_log = self.integration.latest_log(integration_name=integration_name, status="FAILED")
        if not flag:
            test_connection_status = "disabled"
        elif not credentials_present:
            test_connection_status = "credentials_missing"
        elif approval_status != IntegrationApprovalStatus.APPROVED.value:
            test_connection_status = "approval_required"
        elif last_log is None:
            test_connection_status = "not_tested"
        elif last_log.status == "SUCCESS":
            test_connection_status = "ok"
        else:
            test_connection_status = "failed"

        blocking_reasons: list[str] = []
        if not flag:
            blocking_reasons.append("sandbox_flag_disabled")
        if not credentials_present:
            blocking_reasons.append("sandbox_credentials_missing")
        if approval_status != IntegrationApprovalStatus.APPROVED.value:
            blocking_reasons.append(f"sandbox_approval_{approval_status.lower()}")

        return SandboxReadinessItemRead(
            sandbox_flag=flag,
            credentials_present=credentials_present,
            test_connection_status=test_connection_status,
            ready_for_sandbox=not blocking_reasons,
            blocking_reasons=blocking_reasons,
            mode=self.sandbox_mode(integration_name),
            provider=self.provider_name(integration_name),
            approval_status=approval_status,
            active_approval=approval_status == IntegrationApprovalStatus.APPROVED.value,
            approval_expires_at=approval.expires_at if approval is not None else None,
            last_test_connection_status=None if last_log is None else ("ok" if last_log.status == "SUCCESS" else "failed"),
            last_test_connection_at=None if last_log is None else (last_log.finished_at or last_log.created_at),
            last_error_code=None if last_failed_log is None else (last_failed_log.error_code or None),
        )

    def readiness(self) -> SandboxReadinessRead:
        return SandboxReadinessRead(
            fns=self.readiness_item("fns"),
            russian_post=self.readiness_item("russian_post"),
            court=self.readiness_item("court"),
        )

    def credentials_status(self) -> IntegrationCredentialsStatusRead:
        return IntegrationCredentialsStatusRead(
            fns=IntegrationCredentialsStatusItemRead(
                sandbox_credentials_present=self.credentials_present("fns"),
                production_credentials_present=self.production_credentials_present("fns"),
            ),
            russian_post=IntegrationCredentialsStatusItemRead(
                sandbox_credentials_present=self.credentials_present("russian_post"),
                production_credentials_present=self.production_credentials_present("russian_post"),
            ),
            court_arbitr=IntegrationCredentialsStatusItemRead(
                sandbox_credentials_present=self.credentials_present("court"),
                production_credentials_present=self.production_credentials_present("court"),
            ),
        )

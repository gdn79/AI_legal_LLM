from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IntegrationRequestLog


SENSITIVE_MARKERS = {"TOKEN", "SECRET", "PASSWORD", "API_KEY", "APP_TOKEN", "USER_KEY", "AUTH", "KEY"}


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

    @classmethod
    def is_sensitive_key(cls, key: str) -> bool:
        normalized = key.upper()
        return any(marker in normalized for marker in SENSITIVE_MARKERS)

    @classmethod
    def scrub_value(cls, value):
        if isinstance(value, dict):
            return {str(key): ("[REDACTED]" if cls.is_sensitive_key(str(key)) else cls.scrub_value(item)) for key, item in value.items()}
        if isinstance(value, list):
            return [cls.scrub_value(item) for item in value]
        if isinstance(value, tuple):
            return [cls.scrub_value(item) for item in value]
        if isinstance(value, str):
            return value if len(value) <= 500 else f"{value[:497]}..."
        return value

    @classmethod
    def to_json(cls, payload: dict | list | None) -> str:
        return json.dumps(cls.scrub_value(payload or {}), ensure_ascii=False, sort_keys=True)

    def create_log(
        self,
        *,
        integration_name: str,
        provider: str,
        mode: str,
        operation: str,
        request_id: str,
        idempotency_key: str = "",
        created_by_id: int | None = None,
        case_id: int | None = None,
        organization_id: int | None = None,
        safe_request_metadata: dict | None = None,
    ) -> IntegrationRequestLog:
        entry = IntegrationRequestLog(
            integration_name=integration_name,
            provider=provider,
            mode=mode,
            operation=operation,
            request_id=request_id,
            idempotency_key=idempotency_key,
            status="STARTED",
            started_at=datetime.now(UTC),
            safe_request_metadata_json=self.to_json(safe_request_metadata),
            safe_response_metadata_json=self.to_json({}),
            created_by_id=created_by_id,
            case_id=case_id,
            organization_id=organization_id,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def finish_log(
        self,
        entry: IntegrationRequestLog,
        *,
        status: str,
        http_status: int | None,
        safe_response_metadata: dict | None = None,
        error_code: str = "",
        error_message: str = "",
    ) -> IntegrationRequestLog:
        now = datetime.now(UTC)
        started_at = entry.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        entry.status = status
        entry.http_status = http_status
        entry.finished_at = now
        entry.duration_ms = max(int((now - started_at).total_seconds() * 1000), 0)
        entry.error_code = error_code
        entry.error_message = error_message[:500]
        entry.safe_response_metadata_json = self.to_json(safe_response_metadata)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_logs(
        self,
        *,
        integration_name: str | None = None,
        operation: str | None = None,
        status: str | None = None,
    ) -> list[IntegrationRequestLog]:
        query = select(IntegrationRequestLog).order_by(IntegrationRequestLog.created_at.desc())
        if integration_name:
            query = query.where(IntegrationRequestLog.integration_name == integration_name)
        if operation:
            query = query.where(IntegrationRequestLog.operation == operation)
        if status:
            query = query.where(IntegrationRequestLog.status == status)
        return list(self.db.scalars(query.limit(100)))

    def latest_log(
        self,
        *,
        integration_name: str,
        operation: str | None = None,
        status: str | None = None,
    ) -> IntegrationRequestLog | None:
        query = select(IntegrationRequestLog).where(IntegrationRequestLog.integration_name == integration_name)
        if operation:
            query = query.where(IntegrationRequestLog.operation == operation)
        if status:
            query = query.where(IntegrationRequestLog.status == status)
        query = query.order_by(IntegrationRequestLog.created_at.desc())
        return self.db.scalar(query)


def integration_http_error(
    *,
    status_code: int,
    integration_name: str,
    operation: str,
    provider: str,
    mode: str,
    error_code: str,
    safe_message: str,
    retryable: bool,
    manual_action_required: bool,
    details_safe_json: dict[str, str | int | bool | None] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "integration_name": integration_name,
            "operation": operation,
            "provider": provider,
            "mode": mode,
            "error_code": error_code,
            "safe_message": safe_message,
            "retryable": retryable,
            "manual_action_required": manual_action_required,
            "details_safe_json": details_safe_json or {},
        },
    )

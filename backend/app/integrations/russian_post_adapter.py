from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class RussianPostAdapter(ABC):
    @abstractmethod
    def create_dispatch(
        self,
        *,
        case_id: int,
        organization_name: str,
        recipient_name: str,
        recipient_address: str,
        dispatch_kind: str,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def refresh_status(self, *, external_dispatch_id: str | None, tracking_number: str | None) -> dict:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def policy(self) -> dict:
        raise NotImplementedError


class MockRussianPostAdapter(RussianPostAdapter):
    def create_dispatch(
        self,
        *,
        case_id: int,
        organization_name: str,
        recipient_name: str,
        recipient_address: str,
        dispatch_kind: str,
    ) -> dict:
        dispatch_key = f"RP-{case_id}-{dispatch_kind}".upper()
        return {
            "external_dispatch_id": dispatch_key,
            "tracking_number": f"TRACK-{case_id:05d}",
            "status": "CREATED",
            "source": "MOCK_FOR_DEV",
            "status_payload": {
                "organization_name": organization_name,
                "recipient_name": recipient_name,
                "recipient_address": recipient_address,
                "dispatch_kind": dispatch_kind,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }

    def refresh_status(self, *, external_dispatch_id: str | None, tracking_number: str | None) -> dict:
        return {
            "external_dispatch_id": external_dispatch_id or "MOCK-DISPATCH",
            "tracking_number": tracking_number or "TRACK-MOCK",
            "status": "DELIVERED",
            "source": "MOCK_FOR_DEV",
            "status_payload": {
                "delivered_at": datetime.now(UTC).isoformat(),
            },
        }

    def test_connection(self) -> dict:
        return {
            "provider": "russian_post",
            "mode": "MOCK_FOR_DEV",
            "status": "ok",
            "ok": True,
            "detail": "Mock Russian Post provider is available. No letters were sent.",
            "external_calls": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 1,
            "retry_backoff_seconds": 1,
            "rate_limit_per_minute": 10,
            "idempotency_required": True,
        }


class RussianPostSandboxProvider(RussianPostAdapter):
    def create_dispatch(
        self,
        *,
        case_id: int,
        organization_name: str,
        recipient_name: str,
        recipient_address: str,
        dispatch_kind: str,
    ) -> dict:
        return {
            "external_dispatch_id": f"SANDBOX-{case_id}-{dispatch_kind}".upper(),
            "tracking_number": f"SANDBOX-TRACK-{case_id:05d}",
            "status": "CREATED",
            "source": "RUSSIAN_POST_SANDBOX_READY",
            "status_payload": {
                "organization_name": organization_name,
                "recipient_name": recipient_name,
                "recipient_address": recipient_address,
                "dispatch_kind": dispatch_kind,
                "dry_run": True,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        }

    def normalize_address(self, address: str) -> dict:
        return {
            "normalized_address": address.strip(),
            "status": "ok" if address.strip() else "invalid",
            "source": "RUSSIAN_POST_SANDBOX_READY",
        }

    def create_letter(self, request: dict, dry_run: bool = True) -> dict:
        return {
            "letter_id": request.get("idempotency_key", "sandbox-letter"),
            "status": "ready" if dry_run else "blocked",
            "dry_run": dry_run,
        }

    def send_letter(self, letter_id: str, dry_run: bool = True) -> dict:
        return {
            "letter_id": letter_id,
            "status": "ready" if dry_run else "blocked",
            "dry_run": dry_run,
        }

    def refresh_status(self, *, external_dispatch_id: str | None, tracking_number: str | None) -> dict:
        return {
            "external_dispatch_id": external_dispatch_id or "SANDBOX-DISPATCH",
            "tracking_number": tracking_number or "SANDBOX-TRACK",
            "status": "SENT",
            "source": "RUSSIAN_POST_SANDBOX_READY",
            "status_payload": {"dry_run": True, "updated_at": datetime.now(UTC).isoformat()},
        }

    def test_connection(self) -> dict:
        return {
            "provider": "russian_post",
            "mode": "RUSSIAN_POST_SANDBOX_READY",
            "status": "ready",
            "ok": True,
            "detail": "Sandbox Russian Post provider stub is ready. No letters were sent.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 1,
            "retry_backoff_seconds": 1,
            "rate_limit_per_minute": 10,
            "idempotency_required": True,
        }


class UnsupportedRussianPostAdapter(RussianPostAdapter):
    def __init__(self, mode: str):
        self.mode = mode

    def create_dispatch(
        self,
        *,
        case_id: int,
        organization_name: str,
        recipient_name: str,
        recipient_address: str,
        dispatch_kind: str,
    ) -> dict:
        raise NotImplementedError(f"Russian Post adapter mode {self.mode} is not configured in the current MVP")

    def refresh_status(self, *, external_dispatch_id: str | None, tracking_number: str | None) -> dict:
        raise NotImplementedError(f"Russian Post adapter mode {self.mode} is not configured in the current MVP")

    def test_connection(self) -> dict:
        return {
            "provider": "russian_post",
            "mode": self.mode,
            "status": "disabled",
            "ok": False,
            "detail": f"Russian Post adapter mode {self.mode} is not configured in the current MVP",
            "external_calls": False,
            "sandbox": "SANDBOX" in self.mode,
            "credentials_present": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 0,
            "max_retries": 0,
            "retry_backoff_seconds": 0,
            "rate_limit_per_minute": 0,
            "idempotency_required": True,
        }


def get_russian_post_adapter(mode: str) -> RussianPostAdapter:
    if mode in {"MOCK_FOR_DEV", "MANUAL_UPLOAD"}:
        return MockRussianPostAdapter()
    if mode == "RUSSIAN_POST_SANDBOX_READY":
        return RussianPostSandboxProvider()
    return UnsupportedRussianPostAdapter(mode)

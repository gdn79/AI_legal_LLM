from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class FnsCompanyAdapter(ABC):
    @abstractmethod
    def lookup_company(self, inn: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def policy(self) -> dict:
        raise NotImplementedError


class MockFnsCompanyAdapter(FnsCompanyAdapter):
    def lookup_company(self, inn: str) -> dict:
        suffix = inn[-4:].rjust(4, "0")
        incomplete = inn.endswith("0000")
        return {
            "inn": inn,
            "kpp": "" if incomplete else f"7701{suffix}",
            "short_name": f"Mock Org {suffix}",
            "full_name": "" if incomplete else f"Mock Organization {suffix}",
            "ogrn": f"1027700{suffix}",
            "legal_address": "" if incomplete else f"Moscow, Test street, {int(suffix) % 50 + 1}",
            "director_name": "" if incomplete else f"Director {suffix}",
            "director_position": "" if incomplete else "General Director",
            "source": "MOCK_FNS_PROVIDER",
            "actual_at": datetime.now(UTC).isoformat(),
        }

    def test_connection(self) -> dict:
        return {
            "provider": "fns",
            "mode": "MOCK_FOR_DEV",
            "status": "ok",
            "ok": True,
            "detail": "Mock FNS provider is available. No external calls were made.",
            "external_calls": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 2,
            "retry_backoff_seconds": 2,
            "rate_limit_per_minute": 30,
            "idempotency_required": True,
        }


class ManualFnsCompanyAdapter(FnsCompanyAdapter):
    def lookup_company(self, inn: str) -> dict:
        suffix = inn[-4:].rjust(4, "0")
        return {
            "inn": inn,
            "kpp": "",
            "short_name": f"MANUAL_{suffix}",
            "full_name": "",
            "ogrn": "",
            "legal_address": "",
            "director_name": "",
            "director_position": "",
            "source": "MANUAL_UPLOAD",
            "actual_at": datetime.now(UTC).isoformat(),
        }

    def test_connection(self) -> dict:
        return {
            "provider": "fns",
            "mode": "MANUAL_UPLOAD",
            "status": "ok",
            "ok": True,
            "detail": "Manual FNS mode is configured. Data must be provided manually.",
            "external_calls": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 0,
            "max_retries": 0,
            "retry_backoff_seconds": 0,
            "rate_limit_per_minute": 0,
            "idempotency_required": False,
        }


class LocalEgrulFilesAdapter(FnsCompanyAdapter):
    def lookup_company(self, inn: str) -> dict:
        suffix = inn[-4:].rjust(4, "0")
        return {
            "inn": inn,
            "kpp": f"7701{suffix}",
            "short_name": f"LOCAL_{suffix}",
            "full_name": f"Local EGRUL Organization {suffix}",
            "ogrn": f"1027700{suffix}",
            "legal_address": f"Local archive street, {int(suffix) % 50 + 1}",
            "director_name": f"Local Director {suffix}",
            "director_position": "General Director",
            "source": "LOCAL_EGRUL_FILES",
            "actual_at": datetime.now(UTC).isoformat(),
        }

    def test_connection(self) -> dict:
        return {
            "provider": "fns",
            "mode": "LOCAL_EGRUL_FILES",
            "status": "ok",
            "ok": True,
            "detail": "Local EGRUL file mode is configured. No external calls were made.",
            "external_calls": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 0,
            "max_retries": 0,
            "retry_backoff_seconds": 0,
            "rate_limit_per_minute": 0,
            "idempotency_required": True,
        }


class FnsSandboxProvider(FnsCompanyAdapter):
    def lookup_company(self, inn: str) -> dict:
        return self.lookup_by_inn(inn, dry_run=True)

    def lookup_by_inn(self, inn: str, dry_run: bool = True) -> dict:
        suffix = inn[-4:].rjust(4, "0")
        return {
            "inn": inn,
            "kpp": f"7801{suffix}",
            "short_name": f"SANDBOX_{suffix}",
            "full_name": f"Sandbox FNS Organization {suffix}",
            "ogrn": f"1037800{suffix}",
            "legal_address": f"Sandbox street, {int(suffix) % 40 + 1}",
            "director_name": f"Sandbox Director {suffix}",
            "director_position": "General Director",
            "source": "FNS_SANDBOX_READY",
            "actual_at": datetime.now(UTC).isoformat(),
            "dry_run": dry_run,
        }

    def test_connection(self) -> dict:
        return {
            "provider": "fns",
            "mode": "FNS_SANDBOX_READY",
            "status": "ready",
            "ok": True,
            "detail": "Sandbox FNS provider stub is ready. No external calls were made.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 2,
            "retry_backoff_seconds": 2,
            "rate_limit_per_minute": 30,
            "idempotency_required": True,
        }


class UnsupportedFnsCompanyAdapter(FnsCompanyAdapter):
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def lookup_company(self, inn: str) -> dict:  # noqa: ARG002
        raise NotImplementedError(f"FNS provider mode {self.mode} is not configured in the current MVP")

    def test_connection(self) -> dict:
        return {
            "provider": "fns",
            "mode": self.mode,
            "status": "disabled",
            "ok": False,
            "detail": f"FNS provider mode {self.mode} is not configured in the current MVP",
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
            "idempotency_required": False,
        }


def get_fns_company_adapter(mode: str) -> FnsCompanyAdapter:
    if mode == "MOCK_FOR_DEV":
        return MockFnsCompanyAdapter()
    if mode == "MANUAL_UPLOAD":
        return ManualFnsCompanyAdapter()
    if mode == "LOCAL_EGRUL_FILES":
        return LocalEgrulFilesAdapter()
    if mode == "FNS_SANDBOX_READY":
        return FnsSandboxProvider()
    return UnsupportedFnsCompanyAdapter(mode)

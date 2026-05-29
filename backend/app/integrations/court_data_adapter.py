from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, date, datetime


class CourtArbitrAdapter(ABC):
    @abstractmethod
    def search_cases(
        self,
        *,
        organization_name: str,
        inn: str,
        date_from: date,
        date_to: date,
        participation_role: str,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def policy(self) -> dict:
        raise NotImplementedError


class MockCourtArbitrAdapter(CourtArbitrAdapter):
    def search_cases(
        self,
        *,
        organization_name: str,
        inn: str,
        date_from: date,
        date_to: date,
        participation_role: str,
    ) -> list[dict]:
        return [
            {
                "external_case_uid": f"{inn}-A40-10001",
                "case_number": "А40-10001/2026",
                "court_name": "Арбитражный суд города Москвы",
                "participant_role": participation_role,
                "claim_subject": f"Взыскание задолженности в пользу {organization_name}",
                "case_date": date_from.isoformat(),
                "source": "MOCK_FOR_DEV",
                "events": [
                    {"event_date": date_from.isoformat(), "event_type": "registered", "description": "Дело зарегистрировано"},
                    {"event_date": date_to.isoformat(), "event_type": "hearing_set", "description": "Назначено судебное заседание"},
                ],
                "snapshot_payload": {
                    "organization_name": organization_name,
                    "inn": inn,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "participant_role": participation_role,
                },
            },
            {
                "external_case_uid": f"{inn}-A40-10002",
                "case_number": "А40-10002/2026",
                "court_name": "Арбитражный суд города Москвы",
                "participant_role": participation_role,
                "claim_subject": f"Неосновательное обогащение в пользу {organization_name}",
                "case_date": date_to.isoformat(),
                "source": "MOCK_FOR_DEV",
                "events": [
                    {"event_date": date_to.isoformat(), "event_type": "registered", "description": "Карточка дела загружена"},
                ],
                "snapshot_payload": {
                    "organization_name": organization_name,
                    "inn": inn,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "participant_role": participation_role,
                },
            },
        ]

    def test_connection(self) -> dict:
        return {
            "provider": "court_arbitr",
            "mode": "MOCK_FOR_DEV",
            "status": "ok",
            "ok": True,
            "detail": "Mock court provider is available. No external search or scraping was performed.",
            "external_calls": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 1,
            "retry_backoff_seconds": 2,
            "rate_limit_per_minute": 10,
            "idempotency_required": True,
        }


class CourtSandboxProvider(CourtArbitrAdapter):
    def search_cases(
        self,
        *,
        organization_name: str,
        inn: str,
        date_from: date,
        date_to: date,
        participation_role: str,
    ) -> list[dict]:
        return self.import_cases(
            {
                "organization_name": organization_name,
                "inn": inn,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "participation_role": participation_role,
            },
            dry_run=True,
        )["cases"]

    def import_cases(self, request: dict, dry_run: bool = True) -> dict:
        inn = request["inn"]
        organization_name = request["organization_name"]
        date_from = request["date_from"]
        participation_role = request["participation_role"]
        return {
            "dry_run": dry_run,
            "cases": [
                {
                    "external_case_uid": f"{inn}-SANDBOX-1",
                    "case_number": "A40-SANDBOX-1/2026",
                    "court_name": "Sandbox Arbitration Court",
                    "participant_role": participation_role,
                    "claim_subject": f"Sandbox import for {organization_name}",
                    "case_date": date_from,
                    "source": "COURT_SANDBOX_READY",
                    "events": [{"event_date": date_from, "event_type": "registered", "description": "Sandbox import event"}],
                    "snapshot_payload": request,
                }
            ],
        }

    def get_case_card(self, external_case_id: str) -> dict:
        return {
            "external_case_id": external_case_id,
            "source": "COURT_SANDBOX_READY",
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def submit_package(self, package_id: int, dry_run: bool = True) -> dict:
        return {
            "package_id": package_id,
            "dry_run": dry_run,
            "status": "blocked" if not dry_run else "ready",
        }

    def test_connection(self) -> dict:
        return {
            "provider": "court_arbitr",
            "mode": "COURT_SANDBOX_READY",
            "status": "ready",
            "ok": True,
            "detail": "Sandbox court provider stub is ready. No external search or submission was performed.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }

    def policy(self) -> dict:
        return {
            "timeout_seconds": 30,
            "max_retries": 1,
            "retry_backoff_seconds": 2,
            "rate_limit_per_minute": 10,
            "idempotency_required": True,
        }


class UnsupportedCourtArbitrAdapter(CourtArbitrAdapter):
    def __init__(self, mode: str):
        self.mode = mode

    def search_cases(
        self,
        *,
        organization_name: str,
        inn: str,
        date_from: date,
        date_to: date,
        participation_role: str,
    ) -> list[dict]:
        raise NotImplementedError(f"Court arbitr adapter mode {self.mode} is not configured in the current MVP")

    def test_connection(self) -> dict:
        return {
            "provider": "court_arbitr",
            "mode": self.mode,
            "status": "disabled",
            "ok": False,
            "detail": f"Court arbitr adapter mode {self.mode} is not configured in the current MVP",
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


def get_court_data_adapter(mode: str) -> CourtArbitrAdapter:
    if mode in {"MOCK_FOR_DEV", "MANUAL_IMPORT"}:
        return MockCourtArbitrAdapter()
    if mode == "COURT_SANDBOX_READY":
        return CourtSandboxProvider()
    return UnsupportedCourtArbitrAdapter(mode)

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.fns_company_adapter import get_fns_company_adapter
from app.models import (
    AuthorityScope,
    Employee,
    EmployeeHistory,
    FnsCompanyLookupLog,
    Organization,
    OrganizationReviewStatus,
    OrganizationSnapshot,
    PowerOfAttorney,
    PowerOfAttorneyHistory,
    PowerOfAttorneyStatus,
    Signatory,
    SignatoryType,
    User,
)
from app.services.integration_service import integration_http_error
from app.services.sandbox_service import SandboxService
from app.services.storage_service import LocalStorageService


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.storage = LocalStorageService()

    def lookup_preview(self, inn: str, *, sandbox: bool = False, dry_run: bool = True) -> dict:
        payload = self._lookup_fns_payload(inn, sandbox=sandbox, dry_run=dry_run)
        return payload

    def create_or_refresh_by_inn(self, inn: str, *, sandbox: bool = False, dry_run: bool = False) -> Organization:
        payload = self._lookup_fns_payload(inn, sandbox=sandbox, dry_run=dry_run)
        organization = self.db.scalar(select(Organization).where(Organization.inn == inn))
        existing_payload = None
        if organization is None:
            organization = Organization(inn=inn)
            self.db.add(organization)
            self.db.flush()
        else:
            snapshot = self.db.scalar(
                select(OrganizationSnapshot)
                .where(OrganizationSnapshot.organization_id == organization.id)
                .order_by(OrganizationSnapshot.created_at.desc())
            )
            if snapshot is not None:
                existing_payload = snapshot.raw_payload
        self._apply_fns_payload(organization, payload)
        new_payload = self._snapshot_compare_payload(payload)
        if existing_payload != new_payload:
            self._create_snapshot(organization, payload)
            self._create_lookup_log(organization, inn, payload)
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def refresh_organization(self, organization_id: int) -> Organization:
        organization = self.get_organization(organization_id)
        payload = self._lookup_fns_payload(organization.inn, sandbox=False, dry_run=False)
        self._apply_fns_payload(organization, payload)
        self._create_snapshot(organization, payload)
        self._create_lookup_log(organization, organization.inn, payload)
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def list_organizations(self) -> list[Organization]:
        return list(self.db.scalars(select(Organization).order_by(Organization.created_at.desc())))

    def get_organization(self, organization_id: int) -> Organization:
        organization = self.db.get(Organization, organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        return organization

    def list_snapshots(self, organization_id: int) -> list[OrganizationSnapshot]:
        self.get_organization(organization_id)
        return list(
            self.db.scalars(
                select(OrganizationSnapshot)
                .where(OrganizationSnapshot.organization_id == organization_id)
                .order_by(OrganizationSnapshot.created_at.desc())
            )
        )

    def list_lookup_logs(self, organization_id: int) -> list[FnsCompanyLookupLog]:
        self.get_organization(organization_id)
        return list(
            self.db.scalars(
                select(FnsCompanyLookupLog)
                .where(FnsCompanyLookupLog.organization_id == organization_id)
                .order_by(FnsCompanyLookupLog.created_at.desc())
            )
        )

    def create_employee(
        self,
        *,
        organization_id: int,
        full_name: str,
        position: str,
        email: str,
        user_id: int | None,
    ) -> Employee:
        organization = self.get_organization(organization_id)
        if user_id is not None and self.db.get(User, user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        employee = Employee(
            organization_id=organization.id,
            user_id=user_id,
            full_name=full_name,
            position=position,
            email=email,
        )
        self.db.add(employee)
        self.db.flush()
        self.db.add(EmployeeHistory(employee_id=employee.id, event_type="created", details=full_name))
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def list_employees(self, organization_id: int) -> list[Employee]:
        self.get_organization(organization_id)
        return list(
            self.db.scalars(
                select(Employee).where(Employee.organization_id == organization_id).order_by(Employee.created_at.desc())
            )
        )

    def get_employee(self, employee_id: int) -> Employee:
        employee = self.db.get(Employee, employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return employee

    def employee_history(self, employee_id: int) -> list[EmployeeHistory]:
        self.get_employee(employee_id)
        return list(
            self.db.scalars(
                select(EmployeeHistory)
                .where(EmployeeHistory.employee_id == employee_id)
                .order_by(EmployeeHistory.created_at.desc())
            )
        )

    def create_signatory(
        self,
        *,
        organization_id: int,
        signatory_type: str,
        employee_id: int | None,
        full_name: str,
        authority_basis: str,
    ) -> Signatory:
        organization = self.get_organization(organization_id)
        employee = None
        if signatory_type == SignatoryType.DIRECTOR.value:
            full_name = organization.current_director_name
            authority_basis = authority_basis or "FNS_DIRECTOR"
        elif signatory_type == SignatoryType.AUTHORIZED_EMPLOYEE.value:
            if employee_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee signatory requires employee_id")
            employee = self.get_employee(employee_id)
            if employee.organization_id != organization.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee belongs to another organization")
            full_name = full_name or employee.full_name
            authority_basis = authority_basis or "POWER_OF_ATTORNEY"
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported signatory type")

        signatory = Signatory(
            organization_id=organization.id,
            employee_id=employee.id if employee else None,
            signatory_type=signatory_type,
            full_name=full_name,
            authority_basis=authority_basis,
        )
        self.db.add(signatory)
        self.db.commit()
        self.db.refresh(signatory)
        return signatory

    def list_signatories(self, organization_id: int) -> list[Signatory]:
        self.get_organization(organization_id)
        return list(
            self.db.scalars(
                select(Signatory).where(Signatory.organization_id == organization_id).order_by(Signatory.created_at.desc())
            )
        )

    def get_signatory(self, signatory_id: int) -> Signatory:
        signatory = self.db.get(Signatory, signatory_id)
        if signatory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signatory not found")
        return signatory

    def create_power_of_attorney(
        self,
        *,
        employee_id: int,
        user_id: int | None,
        number: str,
        issued_at: date,
        expires_at: date,
        authority_scope: list[str],
        file_name: str,
        file_bytes: bytes,
    ) -> PowerOfAttorney:
        employee = self.get_employee(employee_id)
        if user_id is not None and self.db.get(User, user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if expires_at < issued_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expires_at must be after issued_at")
        normalized_scopes = self.normalize_scopes(authority_scope)
        if not normalized_scopes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="authority_scope is required")
        file_path = self.storage.save_bytes(
            subdir=f"organization_{employee.organization_id}/powers_of_attorney",
            filename=file_name,
            payload=file_bytes,
        )
        power = PowerOfAttorney(
            organization_id=employee.organization_id,
            employee_id=employee.id,
            user_id=user_id,
            number=number,
            issued_at=issued_at,
            expires_at=expires_at,
            file_path=file_path,
            authority_scope=self.scope_to_text(normalized_scopes),
            status=self.resolve_power_status(
                current_status=PowerOfAttorneyStatus.ACTIVE.value,
                valid_until=expires_at,
            ),
        )
        self.db.add(power)
        self.db.flush()
        self.db.add(
            PowerOfAttorneyHistory(
                power_of_attorney_id=power.id,
                event_type="created",
                details=f"{number}|{issued_at.isoformat()}|{expires_at.isoformat()}",
            )
        )
        self.db.commit()
        self.db.refresh(power)
        return power

    def list_powers_for_employee(self, employee_id: int) -> list[PowerOfAttorney]:
        self.get_employee(employee_id)
        powers = list(
            self.db.scalars(
                select(PowerOfAttorney)
                .where(PowerOfAttorney.employee_id == employee_id)
                .order_by(PowerOfAttorney.created_at.desc())
            )
        )
        for power in powers:
            self.ensure_power_status(power)
        self.db.commit()
        return powers

    def get_power_of_attorney(self, power_id: int) -> PowerOfAttorney:
        power = self.db.get(PowerOfAttorney, power_id)
        if power is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Power of attorney not found")
        self.ensure_power_status(power)
        self.db.commit()
        self.db.refresh(power)
        return power

    def revoke_power_of_attorney(self, power_id: int) -> PowerOfAttorney:
        power = self.get_power_of_attorney(power_id)
        power.status = PowerOfAttorneyStatus.REVOKED.value
        power.revoked_at = datetime.now(UTC)
        self.db.add(power)
        self.db.add(
            PowerOfAttorneyHistory(
                power_of_attorney_id=power.id,
                event_type="revoked",
                details=power.number,
            )
        )
        self.db.commit()
        self.db.refresh(power)
        return power

    def power_of_attorney_history(self, power_id: int) -> list[PowerOfAttorneyHistory]:
        self.get_power_of_attorney(power_id)
        return list(
            self.db.scalars(
                select(PowerOfAttorneyHistory)
                .where(PowerOfAttorneyHistory.power_of_attorney_id == power_id)
                .order_by(PowerOfAttorneyHistory.created_at.desc())
            )
        )

    def ensure_power_status(self, power: PowerOfAttorney) -> PowerOfAttorneyStatus:
        resolved = self.resolve_power_status(current_status=power.status, valid_until=power.expires_at)
        if power.status != resolved:
            power.status = resolved
            self.db.add(power)
        return PowerOfAttorneyStatus(power.status)

    @staticmethod
    def resolve_power_status(*, current_status: str, valid_until: date) -> str:
        if current_status in {
            PowerOfAttorneyStatus.REVOKED.value,
            PowerOfAttorneyStatus.SUSPENDED.value,
            PowerOfAttorneyStatus.REQUIRES_REVIEW.value,
            PowerOfAttorneyStatus.DRAFT.value,
        }:
            return current_status
        if valid_until < date.today():
            return PowerOfAttorneyStatus.EXPIRED.value
        return PowerOfAttorneyStatus.ACTIVE.value

    def _lookup_fns_payload(self, inn: str, *, sandbox: bool = False, dry_run: bool = True) -> dict:
        mode = "FNS_SANDBOX_READY" if sandbox else self.settings.fns_provider_mode
        if mode == "FNS_SANDBOX_READY":
            sandbox_service = SandboxService(self.db)
            if not self.settings.enable_fns_sandbox:
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="fns",
                    operation="lookup_company",
                    provider=self.settings.fns_provider,
                    mode=mode,
                    error_code="FNS_SANDBOX_DISABLED",
                    safe_message="FNS sandbox is disabled by feature flag.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"enable_fns_sandbox": self.settings.enable_fns_sandbox},
                )
            if not sandbox_service.credentials_present("fns"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="fns",
                    operation="lookup_company",
                    provider=self.settings.fns_provider,
                    mode=mode,
                    error_code="FNS_SANDBOX_CREDENTIALS_MISSING",
                    safe_message="FNS sandbox credentials are not configured.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"credentials_present": False},
                )
            if not sandbox_service.has_active_approval("fns"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="fns",
                    operation="lookup_company",
                    provider=self.settings.fns_provider,
                    mode=mode,
                    error_code="FNS_SANDBOX_APPROVAL_REQUIRED",
                    safe_message="FNS sandbox approval is required before sandbox lookup.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"approval_status": sandbox_service.approval_status("fns")},
                )
        adapter = get_fns_company_adapter(mode)
        if mode == "FNS_SANDBOX_READY" and hasattr(adapter, "lookup_by_inn"):
            return adapter.lookup_by_inn(inn, dry_run=dry_run)
        return adapter.lookup_company(inn)

    def _apply_fns_payload(self, organization: Organization, payload: dict) -> None:
        organization.kpp = payload.get("kpp", "")
        organization.short_name = payload.get("short_name", "")
        organization.full_name = payload.get("full_name", "")
        organization.ogrn = payload.get("ogrn", "")
        organization.legal_address = payload.get("legal_address", "")
        organization.current_director_name = payload.get("director_name", "")
        organization.current_director_position = payload.get("director_position", "")
        organization.source = payload.get("source", "")
        organization.actual_at = datetime.fromisoformat(payload["actual_at"])
        organization.review_status = self._resolve_review_status(payload)
        organization.updated_at = datetime.now(UTC)
        self.db.add(organization)

    def _create_snapshot(self, organization: Organization, payload: dict) -> None:
        snapshot = OrganizationSnapshot(
            organization_id=organization.id,
            source=payload.get("source", ""),
            actual_at=datetime.fromisoformat(payload["actual_at"]),
            raw_payload=self._snapshot_compare_payload(payload),
        )
        self.db.add(snapshot)

    def _create_lookup_log(self, organization: Organization, inn: str, payload: dict) -> None:
        lookup = FnsCompanyLookupLog(
            organization_id=organization.id,
            inn=inn,
            provider_mode=self.settings.fns_provider_mode,
            source=payload.get("source", ""),
            review_status=self._resolve_review_status(payload),
            request_payload=json.dumps({"inn": inn, "provider_mode": self.settings.fns_provider_mode}, ensure_ascii=False),
            response_payload=json.dumps(payload, ensure_ascii=False),
        )
        self.db.add(lookup)

    @staticmethod
    def _resolve_review_status(payload: dict) -> str:
        required = ["kpp", "full_name", "legal_address", "director_name", "director_position"]
        missing = [key for key in required if not str(payload.get(key, "")).strip()]
        if missing:
            return OrganizationReviewStatus.REQUIRES_MANUAL_REVIEW.value
        return OrganizationReviewStatus.VERIFIED.value

    @staticmethod
    def _snapshot_compare_payload(payload: dict) -> str:
        normalized = dict(payload)
        normalized.pop("actual_at", None)
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def normalize_scopes(authority_scope: list[str]) -> list[str]:
        allowed = {scope.value for scope in AuthorityScope}
        normalized = sorted({scope.strip().upper() for scope in authority_scope if scope.strip()})
        invalid = [scope for scope in normalized if scope not in allowed]
        if invalid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported authority scope: {', '.join(invalid)}")
        return normalized

    @staticmethod
    def scope_to_text(authority_scope: list[str]) -> str:
        return ",".join(OrganizationService.normalize_scopes(authority_scope))

    @staticmethod
    def scope_to_list(authority_scope: str) -> list[str]:
        if not authority_scope:
            return []
        return OrganizationService.normalize_scopes(authority_scope.split(","))

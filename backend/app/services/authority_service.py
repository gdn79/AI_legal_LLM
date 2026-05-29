from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuthorityScope,
    Case,
    PowerOfAttorney,
    PowerOfAttorneyStatus,
    SignatoryAuthorityCheck,
    SignatoryType,
)
from app.services.organization_service import OrganizationService


class AuthorityService:
    def __init__(self, db: Session):
        self.db = db
        self.organizations = OrganizationService(db)

    def ensure_case_signatory_has_authority(self, case: Case, *, document_kind: str) -> tuple[bool, str]:
        if case.plaintiff_organization_id is None or case.signatory_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization and signatory must be selected before approval",
            )

        signatory = case.signatory
        organization = case.plaintiff_organization
        if signatory is None or organization is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case representation is incomplete")
        if signatory.organization_id != organization.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signatory belongs to another organization")
        if not signatory.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signatory is inactive")

        required_scopes = self.required_scopes_for_document(document_kind)

        if signatory.signatory_type == SignatoryType.DIRECTOR.value:
            if signatory.full_name != organization.current_director_name:
                self._save_check(
                    signatory_id=signatory.id,
                    case_id=case.id,
                    power_of_attorney_id=None,
                    document_kind=document_kind,
                    required_scopes=required_scopes,
                    result="FAILED",
                    reason="Director signatory no longer matches FNS data",
                )
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Director signatory no longer matches FNS data")
            reason = "Director authority confirmed by FNS data"
            self._save_check(
                signatory_id=signatory.id,
                case_id=case.id,
                power_of_attorney_id=None,
                document_kind=document_kind,
                required_scopes=required_scopes,
                result="PASSED",
                reason=reason,
            )
            return True, reason

        if signatory.employee_id is None:
            self._save_check(
                signatory_id=signatory.id,
                case_id=case.id,
                power_of_attorney_id=None,
                document_kind=document_kind,
                required_scopes=required_scopes,
                result="FAILED",
                reason="Employee signatory requires employee link",
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee signatory requires employee link")

        valid_power, failure_reason = self._find_valid_power(signatory.employee_id, document_kind=document_kind)
        if valid_power is None:
            self._save_check(
                signatory_id=signatory.id,
                case_id=case.id,
                power_of_attorney_id=None,
                document_kind=document_kind,
                required_scopes=required_scopes,
                result="FAILED",
                reason=failure_reason,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=failure_reason,
            )
        reason = f"Authority confirmed by power of attorney {valid_power.number}"
        self._save_check(
            signatory_id=signatory.id,
            case_id=case.id,
            power_of_attorney_id=valid_power.id,
            document_kind=document_kind,
            required_scopes=required_scopes,
            result="PASSED",
            reason=reason,
        )
        return True, reason

    def _find_valid_power(self, employee_id: int, *, document_kind: str) -> tuple[PowerOfAttorney | None, str]:
        today = date.today()
        required_scopes = set(self.required_scopes_for_document(document_kind))
        candidates = list(
            self.db.scalars(
                select(PowerOfAttorney).where(
                    PowerOfAttorney.employee_id == employee_id,
                )
            )
        )
        if not candidates:
            return None, "Valid power of attorney with required authority is required for this signatory"

        last_failure = "Valid power of attorney with required authority is required for this signatory"
        for candidate in candidates:
            candidate_status = self.organizations.ensure_power_status(candidate)
            scopes = set(self.organizations.scope_to_list(candidate.authority_scope))
            if candidate_status in {
                PowerOfAttorneyStatus.REVOKED,
                PowerOfAttorneyStatus.SUSPENDED,
                PowerOfAttorneyStatus.REQUIRES_REVIEW,
                PowerOfAttorneyStatus.DRAFT,
            }:
                last_failure = f"Power of attorney {candidate.number} is not active"
                continue
            if candidate_status == PowerOfAttorneyStatus.EXPIRED or candidate.expires_at < today:
                last_failure = f"Power of attorney {candidate.number} is expired"
                continue
            if not candidate.file_path:
                last_failure = f"Power of attorney {candidate.number} has no supporting file"
                continue
            if not required_scopes.issubset(scopes):
                last_failure = f"Power of attorney {candidate.number} does not include required authority"
                continue
            return candidate, ""
        self.db.commit()
        return None, last_failure

    @staticmethod
    def required_scopes_for_document(document_kind: str) -> list[str]:
        if document_kind == "pretension":
            return [AuthorityScope.SIGN_PRETENSION.value]
        return [AuthorityScope.SIGN_CLAIM.value, AuthorityScope.REPRESENT_IN_COURT.value]

    def _save_check(
        self,
        *,
        signatory_id: int,
        case_id: int | None,
        power_of_attorney_id: int | None,
        document_kind: str,
        required_scopes: list[str],
        result: str,
        reason: str,
    ) -> None:
        self.db.add(
            SignatoryAuthorityCheck(
                signatory_id=signatory_id,
                case_id=case_id,
                power_of_attorney_id=power_of_attorney_id,
                document_kind=document_kind,
                required_scopes=",".join(required_scopes),
                result=result,
                reason=reason,
            )
        )
        self.db.commit()

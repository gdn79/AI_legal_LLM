from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.models import SignatoryAuthorityCheck
from app.repositories.audit_repository import AuditRepository
from app.schemas.signatory import (
    SignatoryAuthorityCheckRead,
    SignatoryAuthorityCheckRequest,
    SignatoryAuthorityCheckResponse,
    SignatoryCreate,
    SignatoryRead,
)
from app.services.audit_service import AuditService
from app.services.authority_service import AuthorityService
from app.services.case_service import CaseService
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["signatories"])


@router.post("/organizations/{organization_id}/signatories", response_model=SignatoryRead)
def create_signatory(
    organization_id: int,
    payload: SignatoryCreate,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    signatory = OrganizationService(db).create_signatory(
        organization_id=organization_id,
        signatory_type=payload.signatory_type,
        employee_id=payload.employee_id,
        full_name=payload.full_name,
        authority_basis=payload.authority_basis,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "signatory_created",
        "signatory",
        str(signatory.id),
        signatory.full_name,
        request_id,
    )
    return signatory


@router.get("/organizations/{organization_id}/signatories", response_model=list[SignatoryRead])
def list_signatories(
    organization_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).list_signatories(organization_id)


@router.get("/signatories/{signatory_id}", response_model=SignatoryRead)
def get_signatory(
    signatory_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).get_signatory(signatory_id)


@router.post("/signatories/{signatory_id}/check-authority", response_model=SignatoryAuthorityCheckResponse)
def check_signatory_authority(
    signatory_id: int,
    payload: SignatoryAuthorityCheckRequest,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    case = CaseService(db).get_case(payload.case_id, current_user)
    case.signatory = OrganizationService(db).get_signatory(signatory_id)
    case.signatory_id = signatory_id
    valid, reason = AuthorityService(db).ensure_case_signatory_has_authority(case, document_kind=payload.document_kind)
    latest = db.scalar(
        select(SignatoryAuthorityCheck)
        .where(SignatoryAuthorityCheck.signatory_id == signatory_id, SignatoryAuthorityCheck.case_id == payload.case_id)
        .order_by(SignatoryAuthorityCheck.checked_at.desc())
    )
    return SignatoryAuthorityCheckResponse(valid=valid, reason=reason, signatory_id=signatory_id, authority_check_id=latest.id if latest else None)


@router.get("/signatories/{signatory_id}/authority-checks", response_model=list[SignatoryAuthorityCheckRead])
def list_signatory_authority_checks(
    signatory_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    signatory = OrganizationService(db).get_signatory(signatory_id)
    return [
        SignatoryAuthorityCheckRead(
            id=item.id,
            signatory_id=item.signatory_id,
            case_id=item.case_id,
            power_of_attorney_id=item.power_of_attorney_id,
            document_kind=item.document_kind,
            required_scopes=OrganizationService.scope_to_list(item.required_scopes),
            result=item.result,
            reason=item.reason,
            checked_at=item.checked_at,
        )
        for item in sorted(signatory.authority_checks, key=lambda check: check.checked_at, reverse=True)
    ]

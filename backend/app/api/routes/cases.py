from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.case import CaseCreate, CaseRead, CaseRepresentationUpdate
from app.services.audit_service import AuditService
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseRead)
def create_case(
    payload: CaseCreate,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).create_case(current_user=current_user, data=payload)
    AuditService(AuditRepository(db)).log(current_user.id, "case_created", "case", str(case.id), case.title, request_id)
    return case


@router.get("", response_model=list[CaseRead])
def list_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaseService(db).list_cases(current_user)


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return CaseService(db).get_case(case_id, current_user)


@router.patch("/{case_id}/representation", response_model=CaseRead)
def assign_representation(
    case_id: int,
    payload: CaseRepresentationUpdate,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    updated = CaseService(db).assign_representation(
        case,
        plaintiff_organization_id=payload.plaintiff_organization_id,
        signatory_id=payload.signatory_id,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "case_representation_updated",
        "case",
        str(updated.id),
        f"org={updated.plaintiff_organization_id};signatory={updated.signatory_id}",
        request_id,
    )
    return updated

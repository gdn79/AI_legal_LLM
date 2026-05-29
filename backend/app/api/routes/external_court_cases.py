from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.court_import import ExternalCourtCaseLinkRequest, ExternalCourtCaseRead
from app.services.audit_service import AuditService
from app.services.court_import_service import CourtImportService

router = APIRouter(prefix="/external-court-cases", tags=["external-court-cases"])


@router.get("", response_model=list[ExternalCourtCaseRead])
def list_external_court_cases(
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return CourtImportService(db).list_cases()


@router.get("/{external_case_id}", response_model=ExternalCourtCaseRead)
def get_external_court_case(
    external_case_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return CourtImportService(db).get_external_case(external_case_id)


@router.post("/{external_case_id}/link", response_model=ExternalCourtCaseRead)
def link_external_court_case(
    external_case_id: int,
    payload: ExternalCourtCaseLinkRequest,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    external_case = CourtImportService(db).link_external_case(external_case_id=external_case_id, case_id=payload.case_id)
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "external_court_case_linked",
        "external_court_case",
        str(external_case.id),
        str(payload.case_id),
        request_id,
    )
    return external_case

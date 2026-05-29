from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.extraction import ExtractionRunResponse
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.post("/{case_id}/run", response_model=ExtractionRunResponse)
def run_extraction(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    facts, warnings = ExtractionService(db).run_for_case(case, actor_user_id=current_user.id, request_id=request_id)
    AuditService(AuditRepository(db)).log(current_user.id, "facts_extracted", "case", str(case.id), f"facts={len(facts)}", request_id)
    return ExtractionRunResponse(case_id=case.id, status=case.status, facts=facts, warnings=warnings)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id, require_role
from app.db.session import get_db
from app.models import ExtractedFact, RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.pretension import DraftUpdate, PretensionRead
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.pretension_service import PretensionService
from app.services.rag_service import RagService

router = APIRouter(prefix="/pretensions", tags=["pretensions"])


@router.get("/{case_id}", response_model=PretensionRead)
def get_pretension(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = CaseService(db).get_case(case_id, current_user)
    return PretensionService(db).get(case.id)


@router.post("/{case_id}/generate", response_model=PretensionRead)
def generate_pretension(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    facts = [fact.value for fact in db.query(ExtractedFact).filter(ExtractedFact.case_id == case.id).all()]
    results = RagService(db).search(query=case.title, case_id=case.id, source_type=None, category=None, top_k=3)
    citations = [f"{item.title}: {item.fragment[:120]}" for item in results]
    pretension = PretensionService(db).generate(
        case.pretension,
        case.title,
        facts,
        citations,
        actor_user_id=current_user.id,
        request_id=request_id,
    )
    AuditService(AuditRepository(db)).log(current_user.id, "pretension_generated", "pretension", str(pretension.id), f"case={case.id}", request_id)
    return pretension


@router.put("/{case_id}", response_model=PretensionRead)
def update_pretension(
    case_id: int,
    payload: DraftUpdate,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    pretension = PretensionService(db).update(case.pretension, payload.content)
    AuditService(AuditRepository(db)).log(current_user.id, "pretension_updated", "pretension", str(pretension.id), f"case={case.id}", request_id)
    return pretension

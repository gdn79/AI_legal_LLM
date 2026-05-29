from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id, require_role
from app.db.session import get_db
from app.models import ExtractedFact, RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.claim import ClaimRead
from app.schemas.pretension import DraftUpdate
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.claim_service import ClaimService
from app.services.rag_service import RagService

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("/{case_id}", response_model=ClaimRead)
def get_claim(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = CaseService(db).get_case(case_id, current_user)
    return ClaimService(db).get(case.id)


@router.post("/{case_id}/generate", response_model=ClaimRead)
def generate_claim(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    facts = [fact.value for fact in db.query(ExtractedFact).filter(ExtractedFact.case_id == case.id).all()]
    rag_service = RagService(db)
    results = rag_service.search(query=case.title, case_id=case.id, source_type=None, category=None, top_k=3)
    citations = [f"{item.title}: {item.fragment[:120]}" for item in results]
    claim = ClaimService(db).generate(
        case.claim,
        case.title,
        facts,
        citations,
        actor_user_id=current_user.id,
        request_id=request_id,
    )
    for source in results:
        rag_service.attach_citation(source_id=source.id, case_id=case.id, target_type="claim", target_id=claim.id, quote=source.fragment[:200])
    AuditService(AuditRepository(db)).log(current_user.id, "claim_generated", "claim", str(claim.id), f"case={case.id}", request_id)
    return claim


@router.put("/{case_id}", response_model=ClaimRead)
def update_claim(
    case_id: int,
    payload: DraftUpdate,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    claim = ClaimService(db).update(case.claim, payload.content)
    AuditService(AuditRepository(db)).log(current_user.id, "claim_updated", "claim", str(claim.id), f"case={case.id}", request_id)
    return claim

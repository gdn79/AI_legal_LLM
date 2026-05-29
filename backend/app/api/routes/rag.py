from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.rag import RagCitationRead, RagSearchRequest, RagSearchResponse, RagSourceCreate, RagSourceRead
from app.services.audit_service import AuditService
from app.services.rag_service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/sources", response_model=RagSourceRead)
def create_source(
    payload: RagSourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    if current_user.role.name not in {RoleName.admin.value, RoleName.lawyer.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    source = RagService(db).ingest(**payload.model_dump())
    AuditService(AuditRepository(db)).log(current_user.id, "rag_source_created", "rag_source", str(source.id), source.title, request_id)
    return source


@router.post("/search", response_model=RagSearchResponse)
def search_sources(
    payload: RagSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    results = RagService(db).search(
        query=payload.query,
        case_id=payload.case_id,
        source_type=payload.source_type,
        category=payload.category,
        top_k=payload.top_k,
    )
    warning = None if results else "требуется проверка юриста"
    return RagSearchResponse(query=payload.query, results=results, warning=warning)


@router.get("/citations/{case_id}", response_model=list[RagCitationRead])
def list_citations(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ = current_user
    return RagService(db).list_citations(case_id=case_id)

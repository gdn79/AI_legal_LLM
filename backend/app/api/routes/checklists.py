from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.checklist import ChecklistItemRead, ChecklistItemUpdate, ChecklistRead
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.checklist_service import ChecklistService

router = APIRouter(prefix="/checklists", tags=["checklists"])


@router.get("/{case_id}", response_model=ChecklistRead)
def get_checklist(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = CaseService(db).get_case(case_id, current_user)
    return ChecklistService(db).get_for_case(case.id)


@router.put("/items/{item_id}", response_model=ChecklistItemRead)
def update_item(
    item_id: int,
    payload: ChecklistItemUpdate,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    item = ChecklistService(db).update_item(item_id, current_user=current_user, is_completed=payload.is_completed, notes=payload.notes)
    AuditService(AuditRepository(db)).log(current_user.id, "checklist_item_updated", "checklist_item", str(item.id), item.title, request_id)
    return item

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import RoleName
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(db: Session = Depends(get_db), _=Depends(require_role(RoleName.admin))):
    return AuditRepository(db).list_recent()

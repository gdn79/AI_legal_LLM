from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import IntegrationRequestLogRead
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/integration-logs", tags=["integration-logs"])


@router.get("", response_model=list[IntegrationRequestLogRead])
def list_integration_logs(
    integration_name: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return IntegrationService(db).list_logs(
        integration_name=integration_name,
        operation=operation,
        status=status,
    )

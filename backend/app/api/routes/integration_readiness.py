from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import IntegrationCredentialsStatusRead, SandboxReadinessRead
from app.services.sandbox_service import SandboxService

router = APIRouter(prefix="/integration-readiness", tags=["integration-readiness"])


@router.get("/sandbox", response_model=SandboxReadinessRead)
def get_sandbox_readiness(
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return SandboxService(db).readiness()


@router.get("/credentials", response_model=IntegrationCredentialsStatusRead)
def get_credentials_readiness(
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return SandboxService(db).credentials_status()

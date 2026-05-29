from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.sandbox_pilot import SandboxPilotMetricsRead, SandboxPilotReportRead
from app.services.sandbox_pilot_service import SandboxPilotService

router = APIRouter(prefix="/sandbox-pilot", tags=["sandbox-pilot"])


@router.get("/metrics", response_model=SandboxPilotMetricsRead)
def get_sandbox_pilot_metrics(
    _: User = Depends(require_role(RoleName.admin, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return SandboxPilotService(db).metrics()


@router.get("/report", response_model=SandboxPilotReportRead)
def get_sandbox_pilot_report(
    _: User = Depends(require_role(RoleName.admin, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return SandboxPilotService(db).report()

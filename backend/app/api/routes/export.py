from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/{case_id}")
def export_case(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    try:
        package = ExportService(db).build_export(case, current_user)
    except HTTPException as exc:
        AuditService(AuditRepository(db)).log(
            current_user.id,
            "case_export_blocked",
            "case",
            str(case.id),
            str(exc.detail),
            request_id,
        )
        raise
    AuditService(AuditRepository(db)).log(current_user.id, "case_exported", "export_package", str(package.id), package.archive_path, request_id)
    return {"id": package.id, "archive_path": package.archive_path}

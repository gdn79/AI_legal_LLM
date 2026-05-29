from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.court_import import CourtSubmissionPackageCreate, CourtSubmissionPackageRead
from app.schemas.integration import DryRunResultRead
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.court_import_service import CourtImportService
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/court-submission", tags=["court-submission"])


@router.post("", response_model=CourtSubmissionPackageRead)
def prepare_court_submission_package(
    payload: CourtSubmissionPackageCreate,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(payload.case_id, current_user)
    package = CourtImportService(db).prepare_submission_package(
        case=case,
        current_user=current_user,
        external_court_case_id=payload.external_court_case_id,
        note=payload.note,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "court_submission_package_prepared",
        "court_submission_package",
        str(package.id),
        package.status,
        request_id,
    )
    return package


@router.post("/{submission_package_id}/dry-run", response_model=DryRunResultRead)
def dry_run_court_submission_package(
    submission_package_id: int,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="court_arbitr",
        provider="manual_submission",
        mode="MANUAL_IMPORT",
        operation="submission_dry_run",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"submission_package_id": submission_package_id},
    )
    result = CourtImportService(db).dry_run_submission_package(submission_package_id, current_user=current_user)
    integration.finish_log(
        entry,
        status="SUCCESS" if result["ready"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ready"] else "COURT_SUBMISSION_DRY_RUN_FAILED",
        error_message="" if result["ready"] else "Court submission dry run reported validation errors.",
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "court_submission_dry_run",
        "court_submission_package",
        str(submission_package_id),
        "dry_run",
        request_id,
    )
    return result


@router.post("/{submission_package_id}/submit")
def submit_court_submission_package(
    submission_package_id: int,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="court_arbitr",
        provider="manual_submission",
        mode="MANUAL_IMPORT",
        operation="submit_package",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"submission_package_id": submission_package_id},
    )
    try:
        package = CourtImportService(db).submit_package(submission_package_id)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={},
            error_code=detail.get("error_code", "COURT_SUBMISSION_FAILED"),
            error_message=detail.get("safe_message", "Court submission failed"),
        )
        raise
    integration.finish_log(
        entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={"submission_package_id": package.id, "status": package.status},
    )
    return {"id": package.id, "status": package.status}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import ProviderConnectionCheck
from app.repositories.audit_repository import AuditRepository
from app.schemas.court_import import CourtImportJobCreate, CourtImportJobRead, ExternalCourtCaseRead
from app.services.audit_service import AuditService
from app.services.court_import_service import CourtImportService
from app.services.integration_service import IntegrationService
from app.services.sandbox_service import SandboxService
from app.core.config import get_settings
from app.integrations.court_data_adapter import get_court_data_adapter

router = APIRouter(prefix="/court-import", tags=["court-import"])


@router.get("/test-connection", response_model=ProviderConnectionCheck)
def test_court_connection(
    sandbox: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    sandbox_service = SandboxService(db)
    mode = "COURT_SANDBOX_READY" if sandbox else settings.court_provider_mode
    provider = "sandbox_court_arbitr_adapter" if sandbox else settings.court_arbitr_provider
    adapter = get_court_data_adapter(mode)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="court_arbitr",
        provider=provider,
        mode=mode,
        operation="test_connection",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"sandbox": sandbox, "sandbox_enabled": settings.enable_court_sandbox},
    )
    if sandbox and not settings.enable_court_sandbox:
        result = {
            "provider": "court_arbitr",
            "mode": mode,
            "status": "disabled",
            "ok": False,
            "detail": "Court sandbox is disabled by feature flag.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": sandbox_service.credentials_present("court"),
        }
    elif sandbox and not sandbox_service.credentials_present("court"):
        result = {
            "provider": "court_arbitr",
            "mode": mode,
            "status": "credentials_missing",
            "ok": False,
            "detail": "Court sandbox credentials are not configured.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }
    elif sandbox and not sandbox_service.has_active_approval("court"):
        result = {
            "provider": "court_arbitr",
            "mode": mode,
            "status": "approval_required",
            "ok": False,
            "detail": "Court sandbox approval is required before enablement.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": True,
        }
    else:
        result = adapter.test_connection()
        if sandbox:
            result["sandbox"] = True
            result["credentials_present"] = sandbox_service.credentials_present("court")
    integration.finish_log(
        entry,
        status="SUCCESS" if result["ok"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ok"] else "COURT_IMPORT_PROVIDER_UNAVAILABLE",
        error_message="" if result["ok"] else result["detail"],
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "court_import_test_connection",
        "integration",
        "court_arbitr",
        f"mode={mode};sandbox={sandbox}",
        request_id,
    )
    return ProviderConnectionCheck(**result)


@router.post("/jobs", response_model=CourtImportJobRead)
def create_job(
    payload: CourtImportJobCreate,
    sandbox: bool = Query(default=False),
    dry_run: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    provider_mode = "COURT_SANDBOX_READY" if sandbox else payload.provider_mode
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="court_arbitr",
        provider=get_settings().court_arbitr_provider,
        mode=provider_mode or get_settings().court_provider_mode,
        operation="import_cases_by_period",
        request_id=request_id,
        idempotency_key=f"{payload.organization_id}:{payload.inn}:{payload.date_from}:{payload.date_to}:{payload.participation_role}:{provider_mode or get_settings().court_provider_mode}:{dry_run}",
        created_by_id=current_user.id,
        organization_id=payload.organization_id,
        safe_request_metadata={
            "inn": payload.inn,
            "date_from": payload.date_from.isoformat(),
            "date_to": payload.date_to.isoformat(),
            "participation_role": payload.participation_role,
            "sandbox": sandbox,
            "dry_run": dry_run or payload.dry_run,
        },
    )
    try:
        job = CourtImportService(db).create_job(
            organization_id=payload.organization_id,
            inn=payload.inn,
            date_from=payload.date_from,
            date_to=payload.date_to,
            participation_role=payload.participation_role,
            provider_mode=provider_mode,
            dry_run=dry_run or payload.dry_run,
            current_user=current_user,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={},
            error_code=detail.get("error_code", "COURT_IMPORT_FAILED"),
            error_message=detail.get("safe_message", "Court import failed"),
        )
        raise
    integration.finish_log(
        entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={
            "job_id": job.id,
            "result_count": job.result_count,
            "status": job.status,
        },
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "court_import_job_created",
        "court_import_job",
        str(job.id),
        payload.inn,
        request_id,
    )
    return job


@router.get("/jobs", response_model=list[CourtImportJobRead])
def list_jobs(
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return CourtImportService(db).list_jobs()


@router.get("/jobs/{job_id}", response_model=CourtImportJobRead)
def get_job(
    job_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return CourtImportService(db).get_job(job_id)


@router.get("/jobs/{job_id}/cases", response_model=list[ExternalCourtCaseRead])
def list_imported_cases(
    job_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return CourtImportService(db).list_cases(job_id)

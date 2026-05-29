from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.integration import ProviderConnectionCheck
from app.services.audit_service import AuditService
from app.services.integration_service import IntegrationService
from app.services.sandbox_service import SandboxService
from app.integrations.court_data_adapter import get_court_data_adapter

router = APIRouter(prefix="/court-arbitr", tags=["court-arbitr"])


@router.post("/test-connection", response_model=ProviderConnectionCheck)
def test_court_arbitr_connection(
    sandbox: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin)),
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
        safe_request_metadata={
            "real_search_enabled": settings.enable_real_court_search,
            "public_search_enabled": settings.enable_public_kad_search,
            "court_submission_enabled": settings.enable_court_submission,
            "sandbox": sandbox,
            "sandbox_enabled": settings.enable_court_sandbox,
        },
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
        "court_arbitr_test_connection",
        "integration",
        "court_arbitr",
        f"mode={mode};sandbox={sandbox}",
        request_id,
    )
    return ProviderConnectionCheck(**result)

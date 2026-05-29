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
from app.integrations.fns_company_adapter import get_fns_company_adapter

router = APIRouter(prefix="/fns", tags=["fns"])


@router.post("/test-connection", response_model=ProviderConnectionCheck)
def test_fns_connection(
    sandbox: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    sandbox_service = SandboxService(db)
    mode = "FNS_SANDBOX_READY" if sandbox else settings.fns_provider_mode
    provider = "sandbox_fns_adapter" if sandbox else settings.fns_provider
    adapter = get_fns_company_adapter(mode)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="fns",
        provider=provider,
        mode=mode,
        operation="test_connection",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={
            "real_api_enabled": settings.enable_real_fns,
            "sandbox": sandbox,
            "sandbox_enabled": settings.enable_fns_sandbox,
        },
    )
    if sandbox and not settings.enable_fns_sandbox:
        result = {
            "provider": "fns",
            "mode": mode,
            "status": "disabled",
            "ok": False,
            "detail": "FNS sandbox is disabled by feature flag.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": sandbox_service.credentials_present("fns"),
        }
    elif sandbox and not sandbox_service.credentials_present("fns"):
        result = {
            "provider": "fns",
            "mode": mode,
            "status": "credentials_missing",
            "ok": False,
            "detail": "FNS sandbox credentials are not configured.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }
    elif sandbox and not sandbox_service.has_active_approval("fns"):
        result = {
            "provider": "fns",
            "mode": mode,
            "status": "approval_required",
            "ok": False,
            "detail": "FNS sandbox approval is required before enablement.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": True,
        }
    else:
        result = adapter.test_connection()
        if sandbox:
            result["sandbox"] = True
            result["credentials_present"] = sandbox_service.credentials_present("fns")
    integration.finish_log(
        entry,
        status="SUCCESS" if result["ok"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ok"] else "FNS_PROVIDER_UNAVAILABLE",
        error_message="" if result["ok"] else result["detail"],
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "fns_test_connection",
        "integration",
        "fns",
        f"mode={mode};sandbox={sandbox}",
        request_id,
    )
    return ProviderConnectionCheck(**result)

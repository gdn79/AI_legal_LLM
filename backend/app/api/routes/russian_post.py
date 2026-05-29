from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import ProviderConnectionCheck
from app.repositories.audit_repository import AuditRepository
from app.schemas.postal_dispatch import PostalDispatchRead, PostalProofCheckRead, PostalProofDocumentRead
from app.services.audit_service import AuditService
from app.services.integration_service import IntegrationService
from app.services.postal_dispatch_service import PostalDispatchService
from app.services.sandbox_service import SandboxService
from app.core.config import get_settings
from app.integrations.russian_post_adapter import get_russian_post_adapter

router = APIRouter(prefix="/russian-post", tags=["russian-post"])


@router.get("/test-connection", response_model=ProviderConnectionCheck)
@router.post("/test-connection", response_model=ProviderConnectionCheck)
def test_russian_post_connection(
    sandbox: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    sandbox_service = SandboxService(db)
    mode = "RUSSIAN_POST_SANDBOX_READY" if sandbox else settings.russian_post_mode
    provider = "sandbox_russian_post_adapter" if sandbox else settings.russian_post_provider
    adapter = get_russian_post_adapter(mode)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="russian_post",
        provider=provider,
        mode=mode,
        operation="test_connection",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={
            "real_post_send_enabled": settings.enable_real_post_send,
            "sandbox": sandbox,
            "sandbox_enabled": settings.enable_russian_post_sandbox,
        },
    )
    if sandbox and not settings.enable_russian_post_sandbox:
        result = {
            "provider": "russian_post",
            "mode": mode,
            "status": "disabled",
            "ok": False,
            "detail": "Russian Post sandbox is disabled by feature flag.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": sandbox_service.credentials_present("russian_post"),
        }
    elif sandbox and not sandbox_service.credentials_present("russian_post"):
        result = {
            "provider": "russian_post",
            "mode": mode,
            "status": "credentials_missing",
            "ok": False,
            "detail": "Russian Post sandbox credentials are not configured.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": False,
        }
    elif sandbox and not sandbox_service.has_active_approval("russian_post"):
        result = {
            "provider": "russian_post",
            "mode": mode,
            "status": "approval_required",
            "ok": False,
            "detail": "Russian Post sandbox approval is required before enablement.",
            "external_calls": False,
            "sandbox": True,
            "credentials_present": True,
        }
    else:
        result = adapter.test_connection()
    integration.finish_log(
        entry,
        status="SUCCESS" if result["ok"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ok"] else "POST_PROVIDER_UNAVAILABLE",
        error_message="" if result["ok"] else result["detail"],
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "russian_post_test_connection",
        "integration",
        "russian_post",
        f"mode={mode};sandbox={sandbox}",
        request_id,
    )
    return ProviderConnectionCheck(**result)


@router.post("/dispatches/{dispatch_id}/status", response_model=PostalDispatchRead)
def refresh_postal_dispatch_status(
    dispatch_id: int,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    dispatch = PostalDispatchService(db).refresh_status(dispatch_id)
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "postal_dispatch_status_updated",
        "postal_dispatch",
        str(dispatch.id),
        dispatch.status,
        request_id,
    )
    return dispatch


@router.post("/dispatches/{dispatch_id}/proofs", response_model=PostalProofDocumentRead)
async def upload_postal_proof(
    dispatch_id: int,
    proof_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    proof = PostalDispatchService(db).upload_proof(
        dispatch_id=dispatch_id,
        proof_type=proof_type,
        file_name=file.filename or "postal-proof.bin",
        file_bytes=await file.read(),
        current_user=current_user,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "postal_proof_uploaded",
        "postal_proof_document",
        str(proof.id),
        proof.proof_type,
        request_id,
    )
    return proof


@router.get("/cases/{case_id}/claim-copy-proof", response_model=PostalProofCheckRead)
def check_claim_copy_proof(
    case_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    service = PostalDispatchService(db)
    dispatch_ids = [item.id for item in service.list_dispatches(case_id) if item.dispatch_kind == "claim_copy"]
    return PostalProofCheckRead(
        case_id=case_id,
        has_claim_copy_proof=service.has_valid_claim_copy_proof(case_id),
        dispatch_ids=dispatch_ids,
    )

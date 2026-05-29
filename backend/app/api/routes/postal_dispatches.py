from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import DryRunResultRead
from app.repositories.audit_repository import AuditRepository
from app.schemas.postal_dispatch import PostalDispatchCreate, PostalDispatchRead
from app.services.audit_service import AuditService
from app.services.integration_service import IntegrationService
from app.services.postal_dispatch_service import PostalDispatchService

router = APIRouter(prefix="/postal-dispatches", tags=["postal-dispatches"])


@router.post("", response_model=PostalDispatchRead)
def create_postal_dispatch(
    payload: PostalDispatchCreate,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    dispatch = PostalDispatchService(db).create_dispatch(
        case_id=payload.case_id,
        organization_id=payload.organization_id,
        dispatch_kind=payload.dispatch_kind,
        recipient_name=payload.recipient_name,
        recipient_address=payload.recipient_address,
        provider_mode=payload.provider_mode,
        idempotency_key=payload.idempotency_key,
        current_user=current_user,
    )
    integration_entry = IntegrationService(db).create_log(
        integration_name="russian_post",
        provider=get_settings().russian_post_provider,
        mode=dispatch.provider_mode,
        operation="create_dispatch",
        request_id=request_id,
        idempotency_key=dispatch.idempotency_key,
        created_by_id=current_user.id,
        case_id=dispatch.case_id,
        organization_id=dispatch.organization_id,
        safe_request_metadata={
            "dispatch_kind": dispatch.dispatch_kind,
            "recipient_name": dispatch.recipient_name,
        },
    )
    IntegrationService(db).finish_log(
        integration_entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={
            "dispatch_id": dispatch.id,
            "status": dispatch.status,
            "tracking_number": dispatch.tracking_number,
        },
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "postal_dispatch_created",
        "postal_dispatch",
        str(dispatch.id),
        dispatch.dispatch_kind,
        request_id,
    )
    return dispatch


@router.post("/{dispatch_id}/send", response_model=DryRunResultRead)
def send_postal_dispatch(
    dispatch_id: int,
    dry_run: bool = Query(default=False),
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    service = PostalDispatchService(db)
    dispatch = service.get_dispatch(dispatch_id)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="russian_post",
        provider=settings.russian_post_provider,
        mode=dispatch.provider_mode,
        operation="send_dispatch_dry_run" if dry_run else "send_dispatch",
        request_id=request_id,
        idempotency_key=dispatch.idempotency_key,
        created_by_id=current_user.id,
        case_id=dispatch.case_id,
        organization_id=dispatch.organization_id,
        safe_request_metadata={"dispatch_id": dispatch.id, "dry_run": dry_run},
    )
    try:
        result = service.send_dispatch(dispatch_id, dry_run=dry_run)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={"ready": False, "errors": [detail.get("safe_message", "Integration request failed")]},
            error_code=detail.get("error_code", "POST_SEND_FAILED"),
            error_message=detail.get("safe_message", "Integration request failed"),
        )
        AuditService(AuditRepository(db)).log(
            current_user.id,
            "postal_dispatch_send_blocked",
            "postal_dispatch",
            str(dispatch.id),
            dispatch.dispatch_kind,
            request_id,
        )
        raise

    integration.finish_log(
        entry,
        status="SUCCESS" if result["ready"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ready"] else "POST_SEND_DRY_RUN_FAILED",
        error_message="" if result["ready"] else "Postal dispatch dry run reported validation errors.",
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "postal_dispatch_send_dry_run" if dry_run else "postal_dispatch_send_blocked",
        "postal_dispatch",
        str(dispatch.id),
        dispatch.dispatch_kind,
        request_id,
    )
    return result


@router.get("", response_model=list[PostalDispatchRead])
def list_postal_dispatches(
    case_id: int | None = Query(default=None),
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return PostalDispatchService(db).list_dispatches(case_id)


@router.get("/{dispatch_id}", response_model=PostalDispatchRead)
def get_postal_dispatch(
    dispatch_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return PostalDispatchService(db).get_dispatch(dispatch_id)

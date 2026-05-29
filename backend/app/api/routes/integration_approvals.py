from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.integration import (
    IntegrationApprovalAction,
    IntegrationApprovalCreate,
    IntegrationApprovalRead,
)
from app.services.audit_service import AuditService
from app.services.integration_approval_service import IntegrationApprovalService

router = APIRouter(prefix="/integration-approvals", tags=["integration-approvals"])


@router.post("", response_model=IntegrationApprovalRead)
def create_approval_request(
    payload: IntegrationApprovalCreate,
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    approval = IntegrationApprovalService(db).request_approval(
        integration_name=payload.integration_name,
        environment=payload.environment,
        reason=payload.reason,
        expires_at=payload.expires_at,
        requested_by=current_user,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "integration_approval_requested",
        "integration_approval",
        str(approval.id),
        f"{approval.integration_name}|{approval.environment}|{approval.status}",
        request_id,
    )
    return approval


@router.get("", response_model=list[IntegrationApprovalRead])
def list_approvals(
    integration_name: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return IntegrationApprovalService(db).list_approvals(
        integration_name=integration_name,
        environment=environment,
        status_value=status,
    )


@router.get("/active", response_model=list[IntegrationApprovalRead])
def list_active_approvals(
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return IntegrationApprovalService(db).list_active()


@router.get("/{approval_id}", response_model=IntegrationApprovalRead)
def get_approval(
    approval_id: int,
    _: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
):
    return IntegrationApprovalService(db).get_approval(approval_id)


@router.post("/{approval_id}/approve", response_model=IntegrationApprovalRead)
def approve_approval(
    approval_id: int,
    payload: IntegrationApprovalAction,
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    approval = IntegrationApprovalService(db).approve(
        approval_id,
        approved_by=current_user,
        reason=payload.reason,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "integration_approval_approved",
        "integration_approval",
        str(approval.id),
        f"{approval.integration_name}|{approval.environment}|{approval.status}",
        request_id,
    )
    return approval


@router.post("/{approval_id}/reject", response_model=IntegrationApprovalRead)
def reject_approval(
    approval_id: int,
    payload: IntegrationApprovalAction,
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    approval = IntegrationApprovalService(db).reject(
        approval_id,
        acted_by=current_user,
        reason=payload.reason,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "integration_approval_rejected",
        "integration_approval",
        str(approval.id),
        f"{approval.integration_name}|{approval.environment}|{approval.status}",
        request_id,
    )
    return approval


@router.post("/{approval_id}/revoke", response_model=IntegrationApprovalRead)
def revoke_approval(
    approval_id: int,
    payload: IntegrationApprovalAction,
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    approval = IntegrationApprovalService(db).revoke(
        approval_id,
        acted_by=current_user,
        reason=payload.reason,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "integration_approval_revoked",
        "integration_approval",
        str(approval.id),
        f"{approval.integration_name}|{approval.environment}|{approval.status}",
        request_id,
    )
    return approval

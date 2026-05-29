from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import Claim, Pretension, RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.workflow import ApprovalResponse
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/{case_id}/approve-pretension", response_model=ApprovalResponse)
def approve_pretension(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    pretension = db.query(Pretension).filter(Pretension.case_id == case.id).one()
    try:
        approved = WorkflowService(db).approve_pretension(pretension, current_user)
    except HTTPException as exc:
        AuditService(AuditRepository(db)).log(
            current_user.id,
            "pretension_approval_blocked",
            "case",
            str(case.id),
            str(exc.detail),
            request_id,
        )
        raise
    AuditService(AuditRepository(db)).log(current_user.id, "pretension_approved", "pretension", str(approved.id), f"case={case.id}", request_id)
    return ApprovalResponse(case_id=case.id, status=case.status, approved=approved.approved)


@router.post("/{case_id}/approve-claim", response_model=ApprovalResponse)
def approve_claim(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    claim = db.query(Claim).filter(Claim.case_id == case.id).one()
    try:
        approved = WorkflowService(db).approve_claim(claim, current_user)
    except HTTPException as exc:
        AuditService(AuditRepository(db)).log(
            current_user.id,
            "claim_approval_blocked",
            "case",
            str(case.id),
            str(exc.detail),
            request_id,
        )
        raise
    AuditService(AuditRepository(db)).log(current_user.id, "claim_approved", "claim", str(approved.id), f"case={case.id}", request_id)
    return ApprovalResponse(case_id=case.id, status=case.status, approved=approved.approved)


@router.post("/{case_id}/court-package-ready", response_model=ApprovalResponse)
def mark_court_package_ready(
    case_id: int,
    current_user: User = Depends(require_role(RoleName.lawyer, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    case = CaseService(db).get_case(case_id, current_user)
    claim = db.query(Claim).filter(Claim.case_id == case.id).one()
    try:
        ready_case = WorkflowService(db).mark_court_package_ready(claim, current_user)
    except HTTPException as exc:
        AuditService(AuditRepository(db)).log(
            current_user.id,
            "court_package_ready_blocked",
            "case",
            str(case.id),
            str(exc.detail),
            request_id,
        )
        raise
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "court_package_ready_confirmed",
        "case",
        str(ready_case.id),
        ready_case.status,
        request_id,
    )
    return ApprovalResponse(case_id=ready_case.id, status=ready_case.status, approved=True)

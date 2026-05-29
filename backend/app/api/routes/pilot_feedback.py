from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.pilot_feedback import (
    PilotFeedbackCreate,
    PilotFeedbackRead,
    PilotFeedbackScreenshotAttach,
    PilotFeedbackUpdate,
)
from app.services.audit_service import AuditService
from app.services.pilot_feedback_service import PilotFeedbackService

router = APIRouter(prefix="/pilot-feedback", tags=["pilot-feedback"])


@router.post("", response_model=PilotFeedbackRead)
def create_feedback(
    payload: PilotFeedbackCreate,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    service = PilotFeedbackService(db)
    try:
        item = service.create(payload, current_user)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "pilot_feedback_created",
        "pilot_feedback",
        str(item.id),
        f"module={item.module};severity={item.severity};case_id={item.case_id}",
        request_id,
    )
    return item


@router.get("", response_model=list[PilotFeedbackRead])
def list_feedback(
    case_id: int | None = Query(default=None),
    module: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    return PilotFeedbackService(db).list(
        current_user,
        case_id=case_id,
        module=module,
        severity=severity,
        status=status,
    )


@router.get("/{feedback_id}", response_model=PilotFeedbackRead)
def get_feedback(
    feedback_id: int,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
):
    try:
        return PilotFeedbackService(db).get(feedback_id, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{feedback_id}", response_model=PilotFeedbackRead)
def update_feedback(
    feedback_id: int,
    payload: PilotFeedbackUpdate,
    current_user: User = Depends(require_role(RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    service = PilotFeedbackService(db)
    try:
        item = service.update(feedback_id, payload, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "pilot_feedback_updated",
        "pilot_feedback",
        str(item.id),
        f"status={item.status};severity={item.severity}",
        request_id,
    )
    return item


@router.post("/{feedback_id}/attach-screenshot", response_model=PilotFeedbackRead)
def attach_screenshot(
    feedback_id: int,
    payload: PilotFeedbackScreenshotAttach,
    current_user: User = Depends(require_role(RoleName.initiator, RoleName.lawyer, RoleName.manager, RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    service = PilotFeedbackService(db)
    try:
        item = service.attach_screenshot(feedback_id, payload.screenshot_document_id, current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "pilot_feedback_screenshot_attached",
        "pilot_feedback",
        str(item.id),
        f"screenshot_document_id={item.screenshot_document_id}",
        request_id,
    )
    return item

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models import Case, Document, PilotFeedback, User
from app.schemas.pilot_feedback import PilotFeedbackCreate, PilotFeedbackUpdate
from app.services.case_service import CaseService


class PilotFeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.case_service = CaseService(db)

    def _validate_case_access(self, case_id: int | None, current_user: User) -> Case | None:
        if case_id is None:
            return None
        return self.case_service.get_case(case_id, current_user)

    def create(self, payload: PilotFeedbackCreate, current_user: User) -> PilotFeedback:
        case = self._validate_case_access(payload.case_id, current_user)
        item = PilotFeedback(
            case_id=case.id if case else None,
            user_id=current_user.id,
            role=current_user.role.name,
            module=payload.module,
            severity=payload.severity,
            title=payload.title,
            description=payload.description,
            expected_behavior=payload.expected_behavior,
            actual_behavior=payload.actual_behavior,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(
        self,
        current_user: User,
        *,
        case_id: int | None = None,
        module: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[PilotFeedback]:
        statement = select(PilotFeedback).order_by(PilotFeedback.created_at.desc())
        if case_id is not None:
            self._validate_case_access(case_id, current_user)
            statement = statement.where(PilotFeedback.case_id == case_id)
        if module:
            statement = statement.where(PilotFeedback.module == module)
        if severity:
            statement = statement.where(PilotFeedback.severity == severity)
        if status:
            statement = statement.where(PilotFeedback.status == status)
        if current_user.role.name not in {"admin", "manager"}:
            accessible_case_ids = [case.id for case in self.case_service.list_cases(current_user)]
            statement = statement.where(
                (PilotFeedback.user_id == current_user.id)
                | (PilotFeedback.case_id.is_not(None) & PilotFeedback.case_id.in_(accessible_case_ids))
            )
        return list(self.db.scalars(statement).all())

    def get(self, feedback_id: int, current_user: User) -> PilotFeedback:
        item = self.db.get(PilotFeedback, feedback_id)
        if item is None:
            raise ValueError("Pilot feedback not found")
        if current_user.role.name in {"admin", "manager"}:
            return item
        if item.user_id == current_user.id:
            return item
        if item.case_id is not None:
            self.case_service.get_case(item.case_id, current_user)
            return item
        raise PermissionError("Insufficient permissions")

    def update(self, feedback_id: int, payload: PilotFeedbackUpdate, current_user: User) -> PilotFeedback:
        item = self.get(feedback_id, current_user)
        for field in ("module", "severity", "title", "description", "expected_behavior", "actual_behavior", "status"):
            value = getattr(payload, field)
            if value is not None:
                setattr(item, field, value)
        item.updated_at = utc_now()
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def attach_screenshot(self, feedback_id: int, screenshot_document_id: int, current_user: User) -> PilotFeedback:
        item = self.get(feedback_id, current_user)
        document = self.db.get(Document, screenshot_document_id)
        if document is None:
            raise ValueError("Document not found")
        if item.case_id is not None and document.case_id != item.case_id:
            raise ValueError("Screenshot document must belong to the same case")
        if item.case_id is None:
            self.case_service.get_case(document.case_id, current_user)
        item.screenshot_document_id = document.id
        item.updated_at = utc_now()
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

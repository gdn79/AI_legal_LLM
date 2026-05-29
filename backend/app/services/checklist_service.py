from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Checklist, ChecklistItem
from app.models import User
from app.services.case_service import CaseService


class ChecklistService:
    def __init__(self, db: Session):
        self.db = db

    def get_for_case(self, case_id: int) -> Checklist:
        return self.db.query(Checklist).filter(Checklist.case_id == case_id).one()

    def update_item(self, item_id: int, *, current_user: User, is_completed: bool, notes: str) -> ChecklistItem:
        item = self.db.get(ChecklistItem, item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found")
        CaseService(self.db).get_case(item.checklist.case_id, current_user)
        item.is_completed = is_completed
        item.notes = notes
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

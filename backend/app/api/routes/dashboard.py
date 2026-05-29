from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import Case, RoleName, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(current_user: User = Depends(require_role(RoleName.manager, RoleName.admin)), db: Session = Depends(get_db)):
    total_cases = db.scalar(select(func.count()).select_from(Case)) or 0
    return {"user_role": current_user.role.name, "total_cases": total_cases}

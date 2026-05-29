from datetime import datetime

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    full_name: str
    position: str = ""
    email: str = ""
    user_id: int | None = None


class EmployeeRead(BaseModel):
    id: int
    organization_id: int
    user_id: int | None
    full_name: str
    position: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployeeHistoryRead(BaseModel):
    id: int
    employee_id: int
    event_type: str
    details: str
    created_at: datetime

    model_config = {"from_attributes": True}

from datetime import date, datetime

from pydantic import BaseModel


class PowerOfAttorneyRead(BaseModel):
    id: int
    organization_id: int
    employee_id: int
    user_id: int | None
    number: str
    issued_at: date
    expires_at: date
    file_path: str
    status: str
    authority_scope: list[str]
    revoked_at: datetime | None
    created_at: datetime


class PowerOfAttorneyHistoryRead(BaseModel):
    id: int
    power_of_attorney_id: int
    event_type: str
    details: str
    created_at: datetime

    model_config = {"from_attributes": True}

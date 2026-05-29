from datetime import datetime

from pydantic import BaseModel


class ClaimRead(BaseModel):
    id: int
    case_id: int
    content: str
    approved: bool
    updated_at: datetime

    model_config = {"from_attributes": True}

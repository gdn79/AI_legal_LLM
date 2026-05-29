from datetime import datetime

from pydantic import BaseModel


class DraftUpdate(BaseModel):
    content: str


class PretensionRead(BaseModel):
    id: int
    case_id: int
    content: str
    approved: bool
    updated_at: datetime

    model_config = {"from_attributes": True}

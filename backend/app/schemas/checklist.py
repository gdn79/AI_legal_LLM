from pydantic import BaseModel


class ChecklistItemRead(BaseModel):
    id: int
    title: str
    is_completed: bool
    notes: str

    model_config = {"from_attributes": True}


class ChecklistRead(BaseModel):
    id: int
    case_id: int
    status: str
    items: list[ChecklistItemRead]

    model_config = {"from_attributes": True}


class ChecklistItemUpdate(BaseModel):
    is_completed: bool
    notes: str = ""

from pydantic import BaseModel


class ApprovalResponse(BaseModel):
    case_id: int
    status: str
    approved: bool

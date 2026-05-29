from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str
    details: str
    request_id: str
    created_at: datetime

    model_config = {"from_attributes": True}

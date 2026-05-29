from datetime import datetime

from pydantic import BaseModel


class DocumentVersionRead(BaseModel):
    id: int
    document_id: int
    version: int
    storage_path: str
    sha256: str
    extracted_text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: int
    case_id: int
    filename: str
    content_type: str
    sha256: str
    extracted_text: str
    is_approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}

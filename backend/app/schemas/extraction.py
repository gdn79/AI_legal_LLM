from datetime import datetime

from pydantic import BaseModel


class ExtractedFactRead(BaseModel):
    id: int
    case_id: int
    document_id: int | None
    fact_type: str
    value: str
    confidence: float
    source_fragment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExtractionRunResponse(BaseModel):
    case_id: int
    status: str
    facts: list[ExtractedFactRead]
    warnings: list[str]

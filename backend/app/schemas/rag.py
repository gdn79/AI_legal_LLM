from datetime import datetime

from pydantic import BaseModel


class RagSourceCreate(BaseModel):
    title: str
    source_type: str
    category: str = ""
    jurisdiction: str = ""
    fragment: str
    document_date: str = ""
    page: int | None = None
    section: str = ""
    url_or_internal_path: str = ""
    case_id: int | None = None


class RagSourceRead(BaseModel):
    id: int
    case_id: int | None
    title: str
    source_type: str
    document_date: str
    jurisdiction: str
    category: str
    fragment: str
    page: int | None
    section: str
    url_or_internal_path: str
    score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class RagSearchRequest(BaseModel):
    query: str
    case_id: int | None = None
    source_type: str | None = None
    category: str | None = None
    top_k: int = 5


class RagSearchResponse(BaseModel):
    query: str
    results: list[RagSourceRead]
    warning: str | None = None


class RagCitationRead(BaseModel):
    id: int
    source_id: int
    case_id: int | None
    target_type: str
    target_id: int | None
    quote: str
    created_at: datetime

    model_config = {"from_attributes": True}

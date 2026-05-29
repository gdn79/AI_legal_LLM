from datetime import datetime

from pydantic import BaseModel


class SignatoryCreate(BaseModel):
    signatory_type: str
    employee_id: int | None = None
    full_name: str = ""
    authority_basis: str = ""


class SignatoryRead(BaseModel):
    id: int
    organization_id: int
    employee_id: int | None
    signatory_type: str
    full_name: str
    authority_basis: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SignatoryAuthorityCheckRequest(BaseModel):
    case_id: int
    document_kind: str


class SignatoryAuthorityCheckResponse(BaseModel):
    valid: bool
    reason: str
    signatory_id: int
    authority_check_id: int | None = None


class SignatoryAuthorityCheckRead(BaseModel):
    id: int
    signatory_id: int
    case_id: int | None
    power_of_attorney_id: int | None
    document_kind: str
    required_scopes: list[str]
    result: str
    reason: str
    checked_at: datetime

    model_config = {"from_attributes": True}

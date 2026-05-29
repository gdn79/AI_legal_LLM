from datetime import datetime

from pydantic import BaseModel


class OrganizationLookupRequest(BaseModel):
    inn: str
    sandbox: bool = False
    dry_run: bool = True


class OrganizationCreate(BaseModel):
    inn: str
    sandbox: bool = False
    dry_run: bool = False


class OrganizationSnapshotRead(BaseModel):
    id: int
    source: str
    actual_at: datetime
    raw_payload: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FnsCompanyLookupLogRead(BaseModel):
    id: int
    organization_id: int | None
    inn: str
    provider_mode: str
    source: str
    review_status: str
    request_payload: str
    response_payload: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationRead(BaseModel):
    id: int
    inn: str
    kpp: str
    short_name: str
    full_name: str
    ogrn: str
    legal_address: str
    current_director_name: str
    current_director_position: str
    review_status: str
    source: str
    actual_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationPreview(BaseModel):
    inn: str
    kpp: str
    short_name: str
    full_name: str
    ogrn: str
    legal_address: str
    director_name: str
    director_position: str
    source: str
    actual_at: str

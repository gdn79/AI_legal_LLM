from datetime import datetime

from pydantic import BaseModel


class PostalDispatchCreate(BaseModel):
    case_id: int
    organization_id: int
    dispatch_kind: str
    recipient_name: str
    recipient_address: str
    provider_mode: str | None = None
    idempotency_key: str | None = None


class PostalDispatchRead(BaseModel):
    id: int
    case_id: int
    organization_id: int
    dispatch_kind: str
    provider_mode: str
    recipient_name: str
    recipient_address: str
    status: str
    tracking_number: str
    external_dispatch_id: str
    source: str
    idempotency_key: str
    status_payload: str
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PostalProofDocumentRead(BaseModel):
    id: int
    postal_dispatch_id: int
    file_name: str
    file_path: str
    proof_type: str
    source: str
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PostalProofCheckRead(BaseModel):
    case_id: int
    has_claim_copy_proof: bool
    dispatch_ids: list[int]


class AddressNormalizationRequest(BaseModel):
    address: str


class AddressNormalizationResultRead(BaseModel):
    normalized_address: str
    status: str
    source: str

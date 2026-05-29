from datetime import datetime

from pydantic import BaseModel


class CaseCreate(BaseModel):
    title: str
    description: str = ""
    claimant_name: str
    respondent_name: str
    claim_amount: float
    assigned_lawyer_id: int | None = None
    plaintiff_organization_id: int | None = None
    signatory_id: int | None = None


class CaseRead(BaseModel):
    id: int
    title: str
    description: str
    claimant_name: str
    respondent_name: str
    claim_amount: float
    status: str
    created_by_id: int
    assigned_lawyer_id: int | None
    plaintiff_organization_id: int | None
    signatory_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseRepresentationUpdate(BaseModel):
    plaintiff_organization_id: int
    signatory_id: int

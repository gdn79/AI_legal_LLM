from datetime import date, datetime

from pydantic import BaseModel


class CourtImportJobCreate(BaseModel):
    organization_id: int
    inn: str
    date_from: date
    date_to: date
    participation_role: str
    provider_mode: str | None = None


class CourtImportJobRead(BaseModel):
    id: int
    organization_id: int
    inn: str
    date_from: date
    date_to: date
    participation_role: str
    provider_mode: str
    status: str
    source: str
    result_count: int
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CourtCaseEventRead(BaseModel):
    id: int
    event_date: date | None
    event_type: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CourtCaseSnapshotRead(BaseModel):
    id: int
    source: str
    snapshot_payload: str
    snapshot_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ExternalCourtCaseRead(BaseModel):
    id: int
    import_job_id: int
    organization_id: int
    external_case_uid: str
    case_number: str
    court_name: str
    participant_role: str
    claim_subject: str
    case_date: date | None
    linked_case_id: int | None
    source: str
    payload_hash: str
    created_at: datetime
    events: list[CourtCaseEventRead] = []
    snapshots: list[CourtCaseSnapshotRead] = []

    model_config = {"from_attributes": True}


class ExternalCourtCaseLinkRequest(BaseModel):
    case_id: int


class CourtSubmissionPackageCreate(BaseModel):
    case_id: int
    external_court_case_id: int | None = None
    note: str = ""


class CourtSubmissionPackageRead(BaseModel):
    id: int
    case_id: int
    organization_id: int
    external_court_case_id: int | None
    status: str
    package_path: str
    created_by_id: int
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}

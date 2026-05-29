from datetime import datetime

from pydantic import BaseModel


class ProviderConnectionCheck(BaseModel):
    provider: str
    mode: str
    status: str
    ok: bool
    detail: str
    external_calls: bool = False
    sandbox: bool = False
    credentials_present: bool = False


class IntegrationErrorRead(BaseModel):
    integration_name: str
    operation: str
    provider: str
    mode: str
    error_code: str
    safe_message: str
    retryable: bool
    manual_action_required: bool
    details_safe_json: dict[str, str | int | bool | None] = {}


class IntegrationRequestLogRead(BaseModel):
    id: int
    integration_name: str
    provider: str
    mode: str
    operation: str
    request_id: str
    idempotency_key: str
    status: str
    http_status: int | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    error_code: str
    error_message: str
    safe_request_metadata_json: str
    safe_response_metadata_json: str
    created_by_id: int | None
    case_id: int | None
    organization_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DryRunResultRead(BaseModel):
    operation: str
    dry_run: bool = True
    ready: bool
    warnings: list[str] = []
    errors: list[str] = []
    safe_preview_json: dict[str, str | int | bool | list[str] | None] = {}


class IntegrationStatusRead(BaseModel):
    integration_name: str
    provider: str
    mode: str
    real_api_enabled: bool
    sandbox_enabled: bool
    warning: str
    last_test_connection: ProviderConnectionCheck | None = None
    last_integration_error: IntegrationRequestLogRead | None = None


class SandboxReadinessItemRead(BaseModel):
    sandbox_flag: bool
    credentials_present: bool
    test_connection_status: str
    ready_for_sandbox: bool
    blocking_reasons: list[str] = []
    mode: str
    provider: str
    approval_status: str
    active_approval: bool = False
    approval_expires_at: datetime | None = None


class SandboxReadinessRead(BaseModel):
    fns: SandboxReadinessItemRead
    russian_post: SandboxReadinessItemRead
    court: SandboxReadinessItemRead


class IntegrationCredentialsStatusItemRead(BaseModel):
    sandbox_credentials_present: bool
    production_credentials_present: bool


class IntegrationCredentialsStatusRead(BaseModel):
    fns: IntegrationCredentialsStatusItemRead
    russian_post: IntegrationCredentialsStatusItemRead
    court_arbitr: IntegrationCredentialsStatusItemRead


class IntegrationApprovalCreate(BaseModel):
    integration_name: str
    environment: str
    reason: str = ""
    expires_at: datetime | None = None


class IntegrationApprovalAction(BaseModel):
    reason: str = ""


class IntegrationApprovalRead(BaseModel):
    id: int
    integration_name: str
    environment: str
    requested_by_id: int | None
    approved_by_id: int | None
    status: str
    reason: str
    approved_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime

from pydantic import BaseModel, Field


class SandboxPilotIntegrationCheckRead(BaseModel):
    credentials_present: bool
    approval_active: bool
    approval_status: str
    approval_expires_at: datetime | None = None
    test_connection_status: str
    last_test_connection_status: str | None = None
    last_test_connection_at: datetime | None = None
    last_error_code: str | None = None
    ready_for_sandbox: bool
    blocking_reasons: list[str] = Field(default_factory=list)


class SandboxPilotMetricsRead(BaseModel):
    generated_at: datetime
    sandbox_test_connections_total: int
    sandbox_test_connections_skipped: int
    sandbox_test_connections_failed: int
    sandbox_dry_runs_total: int
    sandbox_dangerous_operations_blocked: int
    credentials_missing_count: int
    approval_required_count: int
    approval_expired_count: int
    secrets_leakage_findings: int
    production_flags_enabled_count: int
    real_sandbox_credentials: str
    live_sandbox_calls: str


class SandboxPilotReportRead(BaseModel):
    generated_at: datetime
    status: str
    production_api: str
    real_sandbox_credentials: str
    live_sandbox_calls: str
    court_submission: str
    fns: SandboxPilotIntegrationCheckRead
    russian_post: SandboxPilotIntegrationCheckRead
    court_arbitr: SandboxPilotIntegrationCheckRead
    end_to_end_status: str
    export_generated: bool
    audit_ok: bool
    integration_logs_ok: bool
    secrets_leakage: str
    metrics: SandboxPilotMetricsRead
    issues: list[dict[str, str]]
    recommendation: str

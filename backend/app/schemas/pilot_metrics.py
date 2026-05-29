from datetime import date, datetime

from pydantic import BaseModel


class AuthorityMetricsRead(BaseModel):
    checks_total: int
    valid_count: int
    warning_count: int
    invalid_count: int
    blocked_actions_count: int


class AuthorityCaseMetricsRead(AuthorityMetricsRead):
    case_id: int
    title: str


class PilotTimelineEventRead(BaseModel):
    id: str
    case_id: int
    event_type: str
    title: str
    description: str
    created_at: datetime
    actor_user_id: int | None
    actor_role: str | None
    source: str
    severity: str
    related_entity_type: str
    related_entity_id: str


class PilotCaseMetricsRead(BaseModel):
    case_id: int
    title: str
    status: str
    facts_ready_minutes: float | None
    pretension_draft_minutes: float | None
    pretension_review_minutes: float | None
    claim_draft_minutes: float | None
    claim_review_minutes: float | None
    pretension_edits: int
    claim_edits: int
    rag_warnings: int
    authority_warnings: int
    authority_invalids: int
    authority_checks_total: int
    authority: AuthorityMetricsRead
    blocked_actions: int
    feedback_items: int
    pretension_draft_data_status: str = "ok"


class PilotMetricsSummaryRead(BaseModel):
    total_cases: int
    completed_happy_path_cases: int
    blocked_cases: int
    total_feedback_items: int
    blocker_feedback_items: int
    high_feedback_items: int
    feedback_by_severity_total: dict[str, int]
    feedback_by_severity_unresolved: dict[str, int]
    average_pretension_draft_minutes: float
    average_pretension_draft_data_status: str
    average_claim_draft_minutes: float | None
    total_rag_warnings: int
    total_authority_warnings: int
    total_authority_invalids: int
    total_authority_checks: int
    total_blocked_actions: int
    authority: AuthorityMetricsRead
    authority_by_case: list[AuthorityCaseMetricsRead]
    cases: list[PilotCaseMetricsRead]


class PilotTimelineSummaryRead(BaseModel):
    case_id: int
    timeline: list[PilotTimelineEventRead]


class PilotReportRead(BaseModel):
    period: str
    date_from: date | None = None
    date_to: date | None = None
    total_cases: int
    case_statuses: dict[str, int]
    feedback_total: int
    feedback_by_severity_total: dict[str, int]
    feedback_by_severity_unresolved: dict[str, int]
    average_pretension_draft_minutes: float
    average_pretension_draft_data_status: str
    average_claim_draft_minutes: float | None
    ai_rag_warnings: int
    authority_warnings: int
    authority_invalids: int
    authority_checks_total: int
    blocked_actions: int
    exports_generated: int
    exported_case_ids: list[int]
    unresolved_items: list[str]
    timeline_summary: dict[str, int]
    recommendation: str

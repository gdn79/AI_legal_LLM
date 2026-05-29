from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Case,
    CaseStatus,
    ClaimVersion,
    ExportPackage,
    PilotFeedback,
    PretensionVersion,
    RagCitation,
    SignatoryAuthorityCheck,
    User,
)
from app.schemas.pilot_metrics import (
    AuthorityCaseMetricsRead,
    AuthorityMetricsRead,
    PilotCaseMetricsRead,
    PilotMetricsSummaryRead,
    PilotReportRead,
)
from app.services.case_service import CaseService
from app.services.pilot_timeline_service import PilotTimelineService


class PilotMetricsService:
    BLOCKED_AUDIT_ACTIONS = {
        "claim_approval_blocked",
        "pretension_approval_blocked",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.case_service = CaseService(db)
        self.timeline_service = PilotTimelineService(db)

    @staticmethod
    def _minutes_between(start, end):
        if start is None or end is None or end < start:
            return None
        return round((end - start).total_seconds() / 60.0, 2)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _list_cases(self, current_user: User, *, date_from: date | None, date_to: date | None) -> list[Case]:
        cases = (
            list(self.db.scalars(select(Case).order_by(Case.created_at.asc())).all())
            if current_user.role.name in {"admin", "manager"}
            else self.case_service.list_cases(current_user)
        )
        if date_from is None and date_to is None:
            return cases
        start, end = self.timeline_service.normalize_period(date_from, date_to)
        return [
            case
            for case in cases
            if (
                (start is None or self._as_utc(case.created_at) >= start)
                and (end is None or self._as_utc(case.created_at) <= end)
            )
        ]

    def _authority_checks_for_case(self, case_id: int) -> list[SignatoryAuthorityCheck]:
        checks = list(
            self.db.scalars(
                select(SignatoryAuthorityCheck)
                .where(SignatoryAuthorityCheck.case_id == case_id)
                .order_by(SignatoryAuthorityCheck.checked_at.asc())
            )
        )
        deduped: list[SignatoryAuthorityCheck] = []
        seen: set[tuple[int | None, int | None, str, str, str, str]] = set()
        for check in checks:
            key = (
                check.case_id,
                check.signatory_id,
                check.power_of_attorney_id,
                check.document_kind,
                str(check.result).upper(),
                (check.reason or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(check)
        return deduped

    def _blocked_audits_for_case(self, case_id: int) -> list[AuditLog]:
        audits = list(
            self.db.scalars(
                select(AuditLog)
                .where(
                    AuditLog.entity_type == "case",
                    AuditLog.entity_id == str(case_id),
                    AuditLog.action.in_(self.BLOCKED_AUDIT_ACTIONS),
                )
                .order_by(AuditLog.created_at.asc())
            )
        )
        deduped: list[AuditLog] = []
        seen: set[tuple[str, str, str]] = set()
        for audit in audits:
            key = (audit.action, audit.entity_type, audit.entity_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(audit)
        return deduped

    def _authority_metrics(self, case: Case) -> AuthorityMetricsRead:
        checks = self._authority_checks_for_case(case.id)
        valid_count = 0
        warning_count = 0
        invalid_count = 0
        for check in checks:
            result = str(check.result).upper()
            if result in {"PASSED", "VALID", "ALLOWED"}:
                valid_count += 1
            elif result == "WARNING":
                warning_count += 1
            else:
                invalid_count += 1
        blocked_actions_count = len(self._blocked_audits_for_case(case.id))
        return AuthorityMetricsRead(
            checks_total=len(checks),
            valid_count=valid_count,
            warning_count=warning_count,
            invalid_count=invalid_count,
            blocked_actions_count=blocked_actions_count,
        )

    @staticmethod
    def _first_event_at_or_after(
        event_times: list[datetime],
        pivot: datetime | None,
    ) -> datetime | None:
        if not event_times:
            return None
        if pivot is None:
            return event_times[0]
        for item in event_times:
            if item >= pivot:
                return item
        return event_times[0]

    def _count_feedback(self, case_id: int) -> int:
        return len(self.db.scalars(select(PilotFeedback).where(PilotFeedback.case_id == case_id)).all())

    @staticmethod
    def _feedback_counts(items: list[PilotFeedback]) -> tuple[dict[str, int], dict[str, int]]:
        severities = ["BLOCKER", "HIGH", "MEDIUM", "LOW", "IDEA"]
        total = {severity: 0 for severity in severities}
        unresolved = {severity: 0 for severity in severities}
        for item in items:
            severity = item.severity.upper()
            if severity not in total:
                continue
            total[severity] += 1
            if item.status not in {"FIXED", "WONT_FIX", "POSTPONED"}:
                unresolved[severity] += 1
        return total, unresolved

    def _pretension_duration(self, event_times: dict[str, list[datetime]], created_at: datetime | None) -> tuple[float, str]:
        facts_ready_at = self._first_event_at_or_after(event_times.get("FACT_EXTRACTION_COMPLETED", []), created_at)
        pretension_generated_at = self._first_event_at_or_after(
            event_times.get("PRETENSION_GENERATED", []) or event_times.get("PRETENSION_DRAFT_READY", []),
            facts_ready_at or created_at,
        )
        if facts_ready_at is not None and pretension_generated_at is not None:
            value = self._minutes_between(facts_ready_at, pretension_generated_at)
            if value is not None:
                return value, "ok"
        fallback_start = facts_ready_at or created_at
        fallback_end = pretension_generated_at or self._first_event_at_or_after(
            event_times.get("PRETENSION_DRAFT_READY", []),
            fallback_start,
        )
        if fallback_start is not None and fallback_end is not None:
            value = self._minutes_between(fallback_start, fallback_end)
            if value is not None:
                return value, "fallback"
        return 0.0, "not_enough_data"

    def _case_metrics(self, case: Case) -> PilotCaseMetricsRead:
        timeline = self.timeline_service.build_case_timeline(case)
        event_times: dict[str, list[datetime]] = {}
        for event in timeline:
            event_times.setdefault(event.event_type, []).append(event.created_at)

        created_at = self._first_event_at_or_after(event_times.get("CASE_CREATED", []), None) or self._as_utc(case.created_at)
        facts_ready_at = self._first_event_at_or_after(event_times.get("FACT_EXTRACTION_COMPLETED", []), created_at)
        pretension_generated_at = self._first_event_at_or_after(
            event_times.get("PRETENSION_GENERATED", []) or event_times.get("PRETENSION_DRAFT_READY", []),
            facts_ready_at or created_at,
        )
        pretension_approved_at = self._first_event_at_or_after(event_times.get("PRETENSION_APPROVED", []), pretension_generated_at)
        claim_generated_at = self._first_event_at_or_after(event_times.get("CLAIM_GENERATED", []), pretension_generated_at or created_at)
        claim_approved_at = self._first_event_at_or_after(event_times.get("CLAIM_APPROVED", []), claim_generated_at)
        pretension_draft_minutes, pretension_draft_data_status = self._pretension_duration(event_times, created_at)

        pretension_versions = len(
            self.db.scalars(select(PretensionVersion).where(PretensionVersion.pretension_id == case.pretension.id)).all()
        ) if case.pretension else 0
        claim_versions = len(
            self.db.scalars(select(ClaimVersion).where(ClaimVersion.claim_id == case.claim.id)).all()
        ) if case.claim else 0
        rag_warning_count = 1 if len(self.db.scalars(select(RagCitation).where(RagCitation.case_id == case.id)).all()) == 0 else 0
        authority = self._authority_metrics(case)
        return PilotCaseMetricsRead(
            case_id=case.id,
            title=case.title,
            status=case.status,
            facts_ready_minutes=self._minutes_between(created_at, facts_ready_at),
            pretension_draft_minutes=pretension_draft_minutes,
            pretension_review_minutes=self._minutes_between(pretension_generated_at, pretension_approved_at),
            claim_draft_minutes=self._minutes_between(pretension_generated_at or created_at, claim_generated_at),
            claim_review_minutes=self._minutes_between(claim_generated_at, claim_approved_at),
            pretension_edits=max(pretension_versions - 1, 0),
            claim_edits=max(claim_versions - 1, 0),
            rag_warnings=rag_warning_count,
            authority_warnings=authority.warning_count,
            authority_invalids=authority.invalid_count,
            authority_checks_total=authority.checks_total,
            authority=authority,
            blocked_actions=authority.blocked_actions_count,
            feedback_items=self._count_feedback(case.id),
            pretension_draft_data_status=pretension_draft_data_status,
        )

    def summary(self, current_user: User, *, date_from: date | None = None, date_to: date | None = None) -> PilotMetricsSummaryRead:
        cases = self._list_cases(current_user, date_from=date_from, date_to=date_to)
        case_metrics = [self._case_metrics(case) for case in cases]
        pretension_values = [item.pretension_draft_minutes for item in case_metrics if item.pretension_draft_data_status != "not_enough_data"]
        claim_values = [item.claim_draft_minutes for item in case_metrics if item.claim_draft_minutes is not None]
        feedback_items = self.list_feedback_items(current_user, date_from=date_from, date_to=date_to)
        feedback_by_severity_total, feedback_by_severity_unresolved = self._feedback_counts(feedback_items)
        pretension_data_status = "ok" if pretension_values else "not_enough_data"

        authority_by_case = [
            AuthorityCaseMetricsRead(
                case_id=item.case_id,
                title=item.title,
                checks_total=item.authority.checks_total,
                valid_count=item.authority.valid_count,
                warning_count=item.authority.warning_count,
                invalid_count=item.authority.invalid_count,
                blocked_actions_count=item.authority.blocked_actions_count,
            )
            for item in case_metrics
        ]
        total_valid = sum(item.valid_count for item in authority_by_case)
        total_warnings = sum(item.warning_count for item in authority_by_case)
        total_invalids = sum(item.invalid_count for item in authority_by_case)
        total_checks = sum(item.checks_total for item in authority_by_case)
        total_blocked = sum(item.blocked_actions_count for item in authority_by_case)

        return PilotMetricsSummaryRead(
            total_cases=len(case_metrics),
            completed_happy_path_cases=len(
                [item for item in case_metrics if item.status in {CaseStatus.COURT_PACKAGE_READY.value, CaseStatus.EXPORTED.value}]
            ),
            blocked_cases=len([item for item in authority_by_case if item.blocked_actions_count > 0 or item.invalid_count > 0]),
            total_feedback_items=len(feedback_items),
            blocker_feedback_items=feedback_by_severity_unresolved["BLOCKER"],
            high_feedback_items=feedback_by_severity_unresolved["HIGH"],
            feedback_by_severity_total=feedback_by_severity_total,
            feedback_by_severity_unresolved=feedback_by_severity_unresolved,
            average_pretension_draft_minutes=round(mean(pretension_values), 2) if pretension_values else 0.0,
            average_pretension_draft_data_status=pretension_data_status,
            average_claim_draft_minutes=round(mean(claim_values), 2) if claim_values else None,
            total_rag_warnings=sum(item.rag_warnings for item in case_metrics),
            total_authority_warnings=total_warnings,
            total_authority_invalids=total_invalids,
            total_authority_checks=total_checks,
            total_blocked_actions=total_blocked,
            authority=AuthorityMetricsRead(
                checks_total=total_checks,
                valid_count=total_valid,
                warning_count=total_warnings,
                invalid_count=total_invalids,
                blocked_actions_count=total_blocked,
            ),
            authority_by_case=authority_by_case,
            cases=case_metrics,
        )

    def case_metrics(self, case_id: int, current_user: User) -> PilotCaseMetricsRead:
        case = self.case_service.get_case(case_id, current_user)
        return self._case_metrics(case)

    def export(self, current_user: User, export_format: str, *, date_from: date | None = None, date_to: date | None = None) -> str:
        summary = self.summary(current_user, date_from=date_from, date_to=date_to)
        if export_format == "json":
            return summary.model_dump_json(indent=2)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "case_id",
                "title",
                "status",
                "facts_ready_minutes",
                "pretension_draft_minutes",
                "pretension_review_minutes",
                "claim_draft_minutes",
                "claim_review_minutes",
                "pretension_edits",
                "claim_edits",
                "rag_warnings",
                "authority_warnings",
                "authority_invalids",
                "authority_checks_total",
                "blocked_actions",
                "feedback_items",
            ]
        )
        for item in summary.cases:
            writer.writerow(
                [
                    item.case_id,
                    item.title,
                    item.status,
                    item.facts_ready_minutes,
                    item.pretension_draft_minutes,
                    item.pretension_review_minutes,
                    item.claim_draft_minutes,
                    item.claim_review_minutes,
                    item.pretension_edits,
                    item.claim_edits,
                    item.rag_warnings,
                    item.authority_warnings,
                    item.authority_invalids,
                    item.authority_checks_total,
                    item.blocked_actions,
                    item.feedback_items,
                ]
            )
        return buffer.getvalue()

    def report(self, current_user: User, *, date_from: date | None = None, date_to: date | None = None) -> PilotReportRead:
        summary = self.summary(current_user, date_from=date_from, date_to=date_to)
        cases = self._list_cases(current_user, date_from=date_from, date_to=date_to)
        case_statuses: dict[str, int] = {}
        for item in summary.cases:
            case_statuses[item.status] = case_statuses.get(item.status, 0) + 1
        exported_case_ids = [
            case.id
            for case in cases
            if self.db.scalar(select(ExportPackage).where(ExportPackage.case_id == case.id)) is not None
        ]
        feedback_items = self.list_feedback_items(current_user, date_from=date_from, date_to=date_to)
        feedback_by_severity_total, feedback_by_severity_unresolved = self._feedback_counts(feedback_items)
        unresolved_items = [
            f"{item.severity}: {item.title}"
            for item in feedback_items
            if item.severity in {"BLOCKER", "HIGH"} and item.status not in {"FIXED", "WONT_FIX"}
        ]
        recommendation = "go" if len(unresolved_items) == 0 and summary.completed_happy_path_cases >= 2 else "no-go"
        return PilotReportRead(
            period="internal pilot",
            date_from=date_from,
            date_to=date_to,
            total_cases=summary.total_cases,
            case_statuses=case_statuses,
            feedback_total=summary.total_feedback_items,
            feedback_by_severity_total=feedback_by_severity_total,
            feedback_by_severity_unresolved=feedback_by_severity_unresolved,
            average_pretension_draft_minutes=summary.average_pretension_draft_minutes,
            average_pretension_draft_data_status=summary.average_pretension_draft_data_status,
            average_claim_draft_minutes=summary.average_claim_draft_minutes,
            ai_rag_warnings=summary.total_rag_warnings,
            authority_warnings=summary.total_authority_warnings,
            authority_invalids=summary.total_authority_invalids,
            authority_checks_total=summary.total_authority_checks,
            blocked_actions=summary.total_blocked_actions,
            exports_generated=len(exported_case_ids),
            exported_case_ids=exported_case_ids,
            unresolved_items=unresolved_items,
            timeline_summary=self.timeline_service.timeline_summary(cases, date_from=date_from, date_to=date_to),
            recommendation=recommendation,
        )

    def list_feedback_items(self, current_user: User, *, date_from: date | None = None, date_to: date | None = None) -> list[PilotFeedback]:
        statement = select(PilotFeedback).order_by(PilotFeedback.created_at.desc())
        if current_user.role.name not in {"admin", "manager"}:
            accessible_case_ids = [case.id for case in self.case_service.list_cases(current_user)]
            statement = statement.where(
                (PilotFeedback.user_id == current_user.id)
                | (PilotFeedback.case_id.is_not(None) & PilotFeedback.case_id.in_(accessible_case_ids))
            )
        feedback = list(self.db.scalars(statement).all())
        if date_from is None and date_to is None:
            return feedback
        start, end = self.timeline_service.normalize_period(date_from, date_to)
        return [
            item
            for item in feedback
            if (
                (start is None or self._as_utc(item.created_at) >= start)
                and (end is None or self._as_utc(item.created_at) <= end)
            )
        ]

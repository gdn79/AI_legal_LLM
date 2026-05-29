from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Case,
    CourtCaseImportJob,
    CourtSubmissionPackage,
    ExportPackage,
    ExtractedFact,
    PilotFeedback,
    PostalProofDocument,
    RagCitation,
    SignatoryAuthorityCheck,
    User,
    WorkflowEvent,
)
from app.schemas.pilot_metrics import PilotTimelineEventRead
from app.services.case_service import CaseService


class PilotTimelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.case_service = CaseService(db)

    @staticmethod
    def normalize_period(
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[datetime | None, datetime | None]:
        start = datetime.combine(date_from, time.min, tzinfo=UTC) if date_from else None
        end = datetime.combine(date_to, time.max, tzinfo=UTC) if date_to else None
        return start, end

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def build_case_timeline(self, case: Case, *, date_from: date | None = None, date_to: date | None = None) -> list[PilotTimelineEventRead]:
        start, end = self.normalize_period(date_from, date_to)
        user_role_by_id = {
            user.id: user.role.name
            for user in self.db.scalars(select(User)).all()
        }
        events: list[PilotTimelineEventRead] = []

        def add_event(
            *,
            event_id: str,
            event_type: str,
            title: str,
            description: str,
            created_at: datetime,
            actor_user_id: int | None,
            source: str,
            severity: str,
            related_entity_type: str,
            related_entity_id: str,
        ) -> None:
            if created_at is None:
                return
            created_at = self._as_utc(created_at)
            if start and created_at < start:
                return
            if end and created_at > end:
                return
            events.append(
                PilotTimelineEventRead(
                    id=event_id,
                    case_id=case.id,
                    event_type=event_type,
                    title=title,
                    description=description,
                    created_at=created_at,
                    actor_user_id=actor_user_id,
                    actor_role=user_role_by_id.get(actor_user_id),
                    source=source,
                    severity=severity,
                    related_entity_type=related_entity_type,
                    related_entity_id=related_entity_id,
                )
            )

        add_event(
            event_id=f"case-created-{case.id}",
            event_type="CASE_CREATED",
            title="Case created",
            description=case.title,
            created_at=case.created_at,
            actor_user_id=case.created_by_id,
            source="case",
            severity="info",
            related_entity_type="case",
            related_entity_id=str(case.id),
        )

        for document in case.documents:
            add_event(
                event_id=f"document-uploaded-{document.id}",
                event_type="DOCUMENT_UPLOADED",
                title="Document uploaded",
                description=document.filename,
                created_at=document.created_at,
                actor_user_id=case.created_by_id,
                source="document",
                severity="info",
                related_entity_type="document",
                related_entity_id=str(document.id),
            )

        extracted_facts = list(self.db.scalars(select(ExtractedFact).where(ExtractedFact.case_id == case.id)))
        if extracted_facts:
            started_at = min(item.created_at for item in extracted_facts)
            completed_at = max(item.created_at for item in extracted_facts)
            add_event(
                event_id=f"fact-extraction-started-{case.id}",
                event_type="FACT_EXTRACTION_STARTED",
                title="Fact extraction started",
                description=f"{len(extracted_facts)} fact candidates detected",
                created_at=started_at,
                actor_user_id=case.created_by_id,
                source="extracted_fact",
                severity="info",
                related_entity_type="case",
                related_entity_id=str(case.id),
            )
            add_event(
                event_id=f"fact-extraction-completed-{case.id}",
                event_type="FACT_EXTRACTION_COMPLETED",
                title="Fact extraction completed",
                description=f"{len(extracted_facts)} facts saved",
                created_at=completed_at,
                actor_user_id=case.created_by_id,
                source="extracted_fact",
                severity="info",
                related_entity_type="case",
                related_entity_id=str(case.id),
            )

        if case.pretension:
            add_event(
                event_id=f"pretension-generated-{case.pretension.id}",
                event_type="PRETENSION_GENERATED",
                title="Pretension generated",
                description="Pretension draft is available",
                created_at=case.pretension.updated_at,
                actor_user_id=case.assigned_lawyer_id,
                source="pretension",
                severity="info",
                related_entity_type="pretension",
                related_entity_id=str(case.pretension.id),
            )

        if case.claim:
            add_event(
                event_id=f"claim-generated-{case.claim.id}",
                event_type="CLAIM_GENERATED",
                title="Claim generated",
                description="Claim draft is available",
                created_at=case.claim.updated_at,
                actor_user_id=case.assigned_lawyer_id,
                source="claim",
                severity="info",
                related_entity_type="claim",
                related_entity_id=str(case.claim.id),
            )

        workflow_events = list(
            self.db.scalars(select(WorkflowEvent).where(WorkflowEvent.case_id == case.id).order_by(WorkflowEvent.created_at.asc()))
        )
        for event in workflow_events:
            mapping = {
                "FACTS_EXTRACTED": ("FACT_EXTRACTION_COMPLETED", "Facts extracted"),
                "PRETENSION_APPROVED": ("PRETENSION_APPROVED", "Pretension approved"),
                "CLAIM_DRAFT_READY": ("CLAIM_GENERATED", "Claim draft ready"),
                "APPROVED_BY_LAWYER": ("CLAIM_APPROVED", "Claim approved"),
                "COURT_PACKAGE_READY": ("COURT_PACKAGE_READY", "Court package ready"),
            }
            if event.to_status not in mapping:
                continue
            event_type, title = mapping[event.to_status]
            add_event(
                event_id=f"workflow-{event.id}",
                event_type=event_type,
                title=title,
                description=event.comment or event.to_status,
                created_at=event.created_at,
                actor_user_id=event.actor_user_id,
                source="workflow",
                severity="info",
                related_entity_type="workflow_event",
                related_entity_id=str(event.id),
            )

        citations = list(self.db.scalars(select(RagCitation).where(RagCitation.case_id == case.id)))
        if citations:
            add_event(
                event_id=f"rag-sources-{case.id}",
                event_type="RAG_SOURCES_ATTACHED",
                title="RAG sources attached",
                description=f"{len(citations)} citations linked to the case",
                created_at=min(item.created_at for item in citations),
                actor_user_id=case.assigned_lawyer_id,
                source="rag",
                severity="info",
                related_entity_type="rag_citation",
                related_entity_id=str(citations[0].id),
            )

        authority_checks = list(
            self.db.scalars(
                select(SignatoryAuthorityCheck)
                .where(SignatoryAuthorityCheck.case_id == case.id)
                .order_by(SignatoryAuthorityCheck.checked_at.asc())
            )
        )
        for check in authority_checks:
            normalized_result = str(check.result).upper()
            if normalized_result in {"PASSED", "VALID"}:
                event_type = "AUTHORITY_CHECK_PASSED"
                severity = "info"
            elif normalized_result == "WARNING":
                event_type = "AUTHORITY_CHECK_WARNING"
                severity = "warning"
            else:
                event_type = "AUTHORITY_CHECK_FAILED"
                severity = "error"
            add_event(
                event_id=f"authority-check-{check.id}",
                event_type=event_type,
                title="Authority check",
                description=check.reason,
                created_at=check.checked_at,
                actor_user_id=case.assigned_lawyer_id,
                source="signatory_authority_check",
                severity=severity,
                related_entity_type="signatory_authority_check",
                related_entity_id=str(check.id),
            )

        proofs = list(
            self.db.scalars(
                select(PostalProofDocument)
                .join(PostalProofDocument.postal_dispatch)
                .where(PostalProofDocument.postal_dispatch.has(case_id=case.id))
            )
        )
        for proof in proofs:
            if "pretension" in proof.proof_type:
                event_type = "PRETENSION_PROOF_UPLOADED"
                title = "Pretension proof uploaded"
            elif "claim_copy" in proof.proof_type:
                event_type = "CLAIM_COPY_PROOF_UPLOADED"
                title = "Claim copy proof uploaded"
            else:
                event_type = "POSTAL_PROOF_UPLOADED"
                title = "Postal proof uploaded"
            add_event(
                event_id=f"postal-proof-{proof.id}",
                event_type=event_type,
                title=title,
                description=proof.file_name,
                created_at=proof.created_at,
                actor_user_id=proof.created_by_id,
                source="postal_proof",
                severity="info",
                related_entity_type="postal_proof_document",
                related_entity_id=str(proof.id),
            )

        packages = list(
            self.db.scalars(
                select(CourtSubmissionPackage).where(CourtSubmissionPackage.case_id == case.id).order_by(CourtSubmissionPackage.created_at.asc())
            )
        )
        for package in packages:
            add_event(
                event_id=f"court-package-{package.id}",
                event_type="COURT_PACKAGE_CREATED",
                title="Court package created",
                description=package.note or package.status,
                created_at=package.created_at,
                actor_user_id=package.created_by_id,
                source="court_submission_package",
                severity="info",
                related_entity_type="court_submission_package",
                related_entity_id=str(package.id),
            )

        import_jobs = list(
            self.db.scalars(
                select(CourtCaseImportJob)
                .where(CourtCaseImportJob.organization_id == case.plaintiff_organization_id)
                .order_by(CourtCaseImportJob.created_at.asc())
            )
        )
        for job in import_jobs:
            add_event(
                event_id=f"court-import-started-{job.id}",
                event_type="COURT_IMPORT_STARTED",
                title="Court import started",
                description=f"{job.inn} {job.date_from.isoformat()}-{job.date_to.isoformat()}",
                created_at=job.created_at,
                actor_user_id=job.created_by_id,
                source="court_import_job",
                severity="info",
                related_entity_type="court_import_job",
                related_entity_id=str(job.id),
            )
            if job.status == "COMPLETED":
                add_event(
                    event_id=f"court-import-completed-{job.id}",
                    event_type="COURT_IMPORT_COMPLETED",
                    title="Court import completed",
                    description=f"Imported cases: {job.result_count}",
                    created_at=job.created_at,
                    actor_user_id=job.created_by_id,
                    source="court_import_job",
                    severity="info",
                    related_entity_type="court_import_job",
                    related_entity_id=str(job.id),
                )

        export_packages = list(
            self.db.scalars(select(ExportPackage).where(ExportPackage.case_id == case.id).order_by(ExportPackage.created_at.asc()))
        )
        for export_package in export_packages:
            add_event(
                event_id=f"export-generated-{export_package.id}",
                event_type="EXPORT_GENERATED",
                title="Export generated",
                description=export_package.archive_path,
                created_at=export_package.created_at,
                actor_user_id=export_package.created_by_id,
                source="export_package",
                severity="info",
                related_entity_type="export_package",
                related_entity_id=str(export_package.id),
            )

        feedback_items = list(
            self.db.scalars(select(PilotFeedback).where(PilotFeedback.case_id == case.id).order_by(PilotFeedback.created_at.asc()))
        )
        for item in feedback_items:
            add_event(
                event_id=f"pilot-feedback-{item.id}",
                event_type="PILOT_FEEDBACK_CREATED",
                title="Pilot feedback created",
                description=item.title,
                created_at=item.created_at,
                actor_user_id=item.user_id,
                source="pilot_feedback",
                severity=item.severity.lower(),
                related_entity_type="pilot_feedback",
                related_entity_id=str(item.id),
            )

        for audit in self._list_case_audit_logs(case.id):
            mapped = self._map_audit_to_timeline_event(audit, case_id=case.id)
            if mapped is None:
                continue
            add_event(**mapped)

        deduped = self._dedupe(events)
        return sorted(deduped, key=lambda item: (item.created_at, item.event_type, item.id))

    def list_case_timeline(self, case_id: int, current_user: User, *, date_from: date | None = None, date_to: date | None = None) -> list[PilotTimelineEventRead]:
        case = self.case_service.get_case(case_id, current_user)
        return self.build_case_timeline(case, date_from=date_from, date_to=date_to)

    def timeline_summary(self, cases: Iterable[Case], *, date_from: date | None = None, date_to: date | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in cases:
            for event in self.build_case_timeline(case, date_from=date_from, date_to=date_to):
                counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def _list_case_audit_logs(self, case_id: int) -> list[AuditLog]:
        related = list(
            self.db.scalars(
                select(AuditLog)
                .where(
                    (
                        (AuditLog.entity_type == "case")
                        & (AuditLog.entity_id == str(case_id))
                    )
                    | (AuditLog.details.contains(f"case={case_id}"))
                )
                .order_by(AuditLog.created_at.asc())
            )
        )
        return related

    def _map_audit_to_timeline_event(self, audit: AuditLog, *, case_id: int) -> dict | None:
        mapping = {
            "case_representation_updated": ("ORGANIZATION_SELECTED", "Organization and signatory selected", "info"),
            "pretension_approved": ("PRETENSION_APPROVED", "Pretension approved", "info"),
            "claim_approved": ("CLAIM_APPROVED", "Claim approved", "info"),
            "court_package_ready_confirmed": ("COURT_PACKAGE_READY", "Court package ready", "info"),
            "external_court_case_linked": ("EXTERNAL_COURT_CASE_LINKED", "External court case linked", "info"),
            "case_exported": ("EXPORT_GENERATED", "Export generated", "info"),
            "claim_approval_blocked": ("AUTHORITY_CHECK_FAILED", "Claim approval blocked", "error"),
            "pretension_approval_blocked": ("AUTHORITY_CHECK_FAILED", "Pretension approval blocked", "error"),
            "court_package_ready_blocked": ("COURT_PACKAGE_BLOCKED", "Court package blocked", "warning"),
            "case_export_blocked": ("EXPORT_BLOCKED", "Export blocked", "warning"),
        }
        if audit.action not in mapping:
            return None
        event_type, title, severity = mapping[audit.action]
        return {
            "event_id": f"audit-{audit.id}",
            "event_type": event_type,
            "title": title,
            "description": audit.details,
            "created_at": audit.created_at,
            "actor_user_id": audit.actor_user_id,
            "source": "audit",
            "severity": severity,
            "related_entity_type": audit.entity_type,
            "related_entity_id": audit.entity_id,
        }

    @staticmethod
    def _dedupe(events: list[PilotTimelineEventRead]) -> list[PilotTimelineEventRead]:
        seen: set[tuple[str, str, str, datetime]] = set()
        deduped: list[PilotTimelineEventRead] = []
        for event in events:
            key = (
                event.event_type,
                event.related_entity_type,
                event.related_entity_id,
                event.created_at,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

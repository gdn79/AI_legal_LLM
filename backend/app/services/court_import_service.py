from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.integrations.court_data_adapter import get_court_data_adapter
from app.models import (
    Case,
    CourtCaseEvent,
    CourtCaseImportJob,
    CourtCaseSnapshot,
    CourtImportStatus,
    CourtSubmissionPackage,
    CourtSubmissionStatus,
    ExternalCourtCase,
    Organization,
    User,
)
from app.services.export_service import ExportService
from app.services.integration_service import integration_http_error
from app.services.sandbox_service import SandboxService
from app.services.workflow_service import WorkflowService


class CourtImportService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def create_job(
        self,
        *,
        organization_id: int,
        inn: str,
        date_from: date,
        date_to: date,
        participation_role: str,
        provider_mode: str | None,
        dry_run: bool = False,
        current_user: User,
    ) -> CourtCaseImportJob:
        organization = self.db.get(Organization, organization_id)
        if organization is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
        mode = provider_mode or self.settings.court_provider_mode
        sandbox = SandboxService(self.db)
        if mode == "PUBLIC_SEARCH_DISABLED" or (provider_mode == "PUBLIC_SEARCH" and not self.settings.enable_public_kad_search):
            raise integration_http_error(
                status_code=status.HTTP_409_CONFLICT,
                integration_name="court_arbitr",
                operation="import_cases_by_period",
                provider=self.settings.court_arbitr_provider,
                mode=mode,
                error_code="COURT_UNSAFE_MODE_BLOCKED",
                safe_message="Public KAD search is disabled in the current MVP.",
                retryable=False,
                manual_action_required=True,
                details_safe_json={"enable_public_kad_search": self.settings.enable_public_kad_search},
            )
        if mode == "COURT_SANDBOX_READY":
            if not self.settings.enable_court_sandbox:
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="court_arbitr",
                    operation="import_cases_by_period",
                    provider=self.settings.court_arbitr_provider,
                    mode=mode,
                    error_code="COURT_SANDBOX_DISABLED",
                    safe_message="Court sandbox is disabled by feature flag.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"enable_court_sandbox": self.settings.enable_court_sandbox},
                )
            if not sandbox.credentials_present("court"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="court_arbitr",
                    operation="import_cases_by_period",
                    provider=self.settings.court_arbitr_provider,
                    mode=mode,
                    error_code="COURT_SANDBOX_CREDENTIALS_MISSING",
                    safe_message="Court sandbox credentials are not configured.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"credentials_present": False},
                )
            if not sandbox.has_active_approval("court"):
                raise integration_http_error(
                    status_code=status.HTTP_409_CONFLICT,
                    integration_name="court_arbitr",
                    operation="import_cases_by_period",
                    provider=self.settings.court_arbitr_provider,
                    mode=mode,
                    error_code="COURT_SANDBOX_APPROVAL_REQUIRED",
                    safe_message="Court sandbox approval is required before sandbox import.",
                    retryable=False,
                    manual_action_required=True,
                    details_safe_json={"approval_status": sandbox.approval_status("court")},
                )
        adapter = get_court_data_adapter(mode)
        job = CourtCaseImportJob(
            organization_id=organization.id,
            inn=inn,
            date_from=date_from,
            date_to=date_to,
            participation_role=participation_role,
            provider_mode=mode,
            status=CourtImportStatus.PENDING.value,
            source=mode,
            created_by_id=current_user.id,
        )
        self.db.add(job)
        self.db.flush()

        if mode == "COURT_SANDBOX_READY" and hasattr(adapter, "import_cases"):
            response = adapter.import_cases(
                {
                    "organization_name": organization.short_name or organization.full_name or organization.inn,
                    "inn": inn,
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "participation_role": participation_role,
                },
                dry_run=dry_run,
            )
            results = response["cases"]
        else:
            results = adapter.search_cases(
                organization_name=organization.short_name or organization.full_name or organization.inn,
                inn=inn,
                date_from=date_from,
                date_to=date_to,
                participation_role=participation_role,
            )

        created_count = 0
        for item in results:
            existing = self.db.scalar(
                select(ExternalCourtCase).where(ExternalCourtCase.external_case_uid == item["external_case_uid"])
            )
            if existing is not None:
                continue
            external_case = ExternalCourtCase(
                import_job_id=job.id,
                organization_id=organization.id,
                external_case_uid=item["external_case_uid"],
                case_number=item["case_number"],
                court_name=item["court_name"],
                participant_role=item["participant_role"],
                claim_subject=item["claim_subject"],
                case_date=date.fromisoformat(item["case_date"]) if item.get("case_date") else None,
                source=item["source"],
                payload_hash=self._payload_hash(item),
            )
            self.db.add(external_case)
            self.db.flush()

            snapshot_payload = json.dumps(item.get("snapshot_payload", item), ensure_ascii=False, sort_keys=True)
            self.db.add(
                CourtCaseSnapshot(
                    external_court_case_id=external_case.id,
                    source=item["source"],
                    snapshot_payload=snapshot_payload,
                    snapshot_hash=self._hash(snapshot_payload),
                )
            )
            for event in item.get("events", []):
                self.db.add(
                    CourtCaseEvent(
                        external_court_case_id=external_case.id,
                        event_date=date.fromisoformat(event["event_date"]) if event.get("event_date") else None,
                        event_type=event["event_type"],
                        description=event.get("description", ""),
                    )
                )
            created_count += 1

        job.result_count = created_count
        job.status = CourtImportStatus.COMPLETED.value
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def list_jobs(self) -> list[CourtCaseImportJob]:
        return list(self.db.scalars(select(CourtCaseImportJob).order_by(CourtCaseImportJob.created_at.desc())))

    def get_job(self, job_id: int) -> CourtCaseImportJob:
        job = self.db.get(CourtCaseImportJob, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court import job not found")
        return job

    def list_cases(self, job_id: int | None = None) -> list[ExternalCourtCase]:
        query = (
            select(ExternalCourtCase)
            .options(selectinload(ExternalCourtCase.events), selectinload(ExternalCourtCase.snapshots))
            .order_by(ExternalCourtCase.created_at.desc())
        )
        if job_id is not None:
            self.get_job(job_id)
            query = query.where(ExternalCourtCase.import_job_id == job_id)
        return list(self.db.scalars(query))

    def get_external_case(self, external_case_id: int) -> ExternalCourtCase:
        external_case = self.db.scalar(
            select(ExternalCourtCase)
            .options(selectinload(ExternalCourtCase.events), selectinload(ExternalCourtCase.snapshots))
            .where(ExternalCourtCase.id == external_case_id)
        )
        if external_case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="External court case not found")
        return external_case

    def link_external_case(self, *, external_case_id: int, case_id: int) -> ExternalCourtCase:
        external_case = self.get_external_case(external_case_id)
        internal_case = self.db.get(Case, case_id)
        if internal_case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        external_case.linked_case_id = internal_case.id
        self.db.add(external_case)
        self.db.commit()
        self.db.refresh(external_case)
        return self.get_external_case(external_case_id)

    def prepare_submission_package(
        self,
        *,
        case: Case,
        current_user: User,
        external_court_case_id: int | None,
        note: str,
    ) -> CourtSubmissionPackage:
        if case.plaintiff_organization_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Case organization is not selected")
        external_case = None
        if external_court_case_id is not None:
            external_case = self.get_external_case(external_court_case_id)
        WorkflowService(self.db).mark_court_package_ready(case.claim, current_user)
        self.db.refresh(case)

        export_package = ExportService(self.db).build_export(case, current_user, mutate_status=False)
        package_dir = Path(export_package.archive_path).with_suffix("")
        package_dir.mkdir(parents=True, exist_ok=True)
        package_manifest = package_dir / "court_submission_manifest.txt"
        package_manifest.write_text(
            "\n".join(
                [
                    f"case_id={case.id}",
                    f"organization_id={case.plaintiff_organization_id}",
                    f"external_case_uid={external_case.external_case_uid if external_case else ''}",
                    f"note={note}",
                    "submission_mode=MANUAL_ONLY",
                ]
            ),
            encoding="utf-8",
        )

        submission = CourtSubmissionPackage(
            case_id=case.id,
            organization_id=case.plaintiff_organization_id,
            external_court_case_id=external_case.id if external_case else None,
            status=CourtSubmissionStatus.READY_FOR_MANUAL_SUBMISSION.value,
            package_path=str(package_manifest),
            created_by_id=current_user.id,
            note=note,
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def dry_run_submission_package(self, submission_package_id: int, *, current_user: User) -> dict:  # noqa: ARG002
        submission = self.db.get(CourtSubmissionPackage, submission_package_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Court submission package not found")
        case = self.db.get(Case, submission.case_id)
        if case is None or case.claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Related case or claim not found")
        errors: list[str] = []
        warnings: list[str] = []
        try:
            WorkflowService(self.db).mark_court_package_ready(case.claim, current_user)
        except HTTPException as exc:
            errors.append(str(exc.detail))
        if not submission.package_path:
            errors.append("submission_package_path_missing")
        if submission.external_court_case_id is None:
            warnings.append("external_court_case_not_linked")
        return {
            "operation": "court_submission_dry_run",
            "dry_run": True,
            "ready": not errors,
            "warnings": warnings,
            "errors": errors,
            "safe_preview_json": {
                "submission_package_id": submission.id,
                "case_id": submission.case_id,
                "organization_id": submission.organization_id,
                "status": submission.status,
            },
        }

    def submit_package(self, submission_package_id: int) -> CourtSubmissionPackage:
        if not self.settings.enable_court_submission:
            raise integration_http_error(
                status_code=status.HTTP_409_CONFLICT,
                integration_name="court_arbitr",
                operation="submit_package",
                provider=self.settings.court_arbitr_provider,
                mode=self.settings.court_provider_mode,
                error_code="COURT_SUBMISSION_DISABLED",
                safe_message="Court submission is disabled in the current MVP.",
                retryable=False,
                manual_action_required=True,
                details_safe_json={"enable_court_submission": self.settings.enable_court_submission},
            )
        raise integration_http_error(
            status_code=status.HTTP_409_CONFLICT,
            integration_name="court_arbitr",
            operation="submit_package",
            provider=self.settings.court_arbitr_provider,
            mode=self.settings.court_provider_mode,
            error_code="COURT_SUBMISSION_DISABLED",
            safe_message="Real court submission is disabled in the current MVP.",
            retryable=False,
            manual_action_required=True,
            details_safe_json={"enable_court_submission": self.settings.enable_court_submission},
        )

    @staticmethod
    def _hash(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _payload_hash(self, payload: dict) -> str:
        return self._hash(json.dumps(payload, ensure_ascii=False, sort_keys=True))

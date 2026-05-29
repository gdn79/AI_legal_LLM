from __future__ import annotations

import json
from pathlib import Path
from shutil import copy2, rmtree
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AuditLog,
    Case,
    CaseStatus,
    CourtSubmissionPackage,
    Document,
    ExportPackage,
    ExternalCourtCase,
    PostalDispatch,
    RagCitation,
    RagSource,
    SignatoryAuthorityCheck,
    User,
)
from app.services.organization_service import OrganizationService
from app.services.workflow_service import WorkflowService


class ExportService:
    SECTION_NAMES = {
        "source_docs": "01_Исходные_документы",
        "org_authority": "02_Организация_и_полномочия",
        "pretension": "03_Претензия",
        "pretension_dispatch": "04_Отправка_претензии",
        "claim_draft": "05_Проект_иска",
        "approved": "06_Утверждено_юристом",
        "claim_amount": "07_Расчет_требований",
        "rag": "08_Источники_RAG",
        "claim_copy": "09_Направление_копии_иска",
        "court_package": "10_Комплект_для_суда",
        "court_events": "11_КАД_и_судебные_события",
        "audit": "12_Журнал_действий",
    }

    def __init__(self, db: Session):
        self.db = db
        self.root = get_settings().storage_path / "exports"
        self.root.mkdir(parents=True, exist_ok=True)
        self.case_folder_root = get_settings().storage_path / "case_folders"
        self.case_folder_root.mkdir(parents=True, exist_ok=True)

    def build_export(self, case: Case, current_user: User, *, mutate_status: bool = True) -> ExportPackage:
        if case.status not in {CaseStatus.APPROVED_BY_LAWYER.value, CaseStatus.COURT_PACKAGE_READY.value}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Claim must be approved and the court package must pass readiness checks before export",
            )
        if case.status != CaseStatus.COURT_PACKAGE_READY.value:
            WorkflowService(self.db).mark_court_package_ready(case.claim, current_user)
            self.db.refresh(case)

        case_folder = self._build_case_folder(case)
        archive_path = self.root / f"case_{case.id}.zip"
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for source in case_folder.rglob("*"):
                if source.is_file():
                    archive.write(source, arcname=str(source.relative_to(case_folder.parent)))

        package = ExportPackage(case_id=case.id, archive_path=str(archive_path), created_by_id=current_user.id)
        self.db.add(package)
        if mutate_status:
            case.status = CaseStatus.EXPORTED.value
            self.db.add(case)
        self.db.commit()
        self.db.refresh(package)
        return package

    def _build_case_folder(self, case: Case) -> Path:
        base_dir = self.case_folder_root / f"Дело_{case.id}"
        if base_dir.exists():
            rmtree(base_dir)

        section_dirs = {key: base_dir / value for key, value in self.SECTION_NAMES.items()}
        for section_dir in section_dirs.values():
            section_dir.mkdir(parents=True, exist_ok=True)

        self._copy_documents(case.documents, section_dirs["source_docs"])
        self._write_organization_and_authority(case, section_dirs["org_authority"])
        self._write_pretension(case, section_dirs["pretension"])
        self._write_postal_dispatches(case, section_dirs["pretension_dispatch"], dispatch_kind="pretension")
        self._write_claim(case, section_dirs["claim_draft"])
        self._write_approved(case, section_dirs["approved"])
        self._write_claim_amount(case, section_dirs["claim_amount"])
        self._write_rag_report(case, section_dirs["rag"])
        self._write_postal_dispatches(case, section_dirs["claim_copy"], dispatch_kind="claim_copy")
        self._write_court_package(case, section_dirs["court_package"])
        self._write_court_events(case, section_dirs["court_events"])
        self._write_audit_log(case, section_dirs["audit"])
        return base_dir

    def _copy_documents(self, documents: list[Document], destination: Path) -> None:
        for document in documents:
            source = Path(document.storage_path)
            if source.exists():
                copy2(source, destination / source.name)

    def _write_organization_and_authority(self, case: Case, destination: Path) -> None:
        organization = case.plaintiff_organization
        signatory = case.signatory
        if organization is not None:
            (destination / "organization.json").write_text(
                json.dumps(
                    {
                        "id": organization.id,
                        "inn": organization.inn,
                        "kpp": organization.kpp,
                        "ogrn": organization.ogrn,
                        "short_name": organization.short_name,
                        "full_name": organization.full_name,
                        "legal_address": organization.legal_address,
                        "director_name": organization.current_director_name,
                        "director_position": organization.current_director_position,
                        "review_status": organization.review_status,
                        "source": organization.source,
                        "actual_at": organization.actual_at.isoformat(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        if signatory is not None:
            (destination / "signatory.json").write_text(
                json.dumps(
                    {
                        "id": signatory.id,
                        "organization_id": signatory.organization_id,
                        "employee_id": signatory.employee_id,
                        "signatory_type": signatory.signatory_type,
                        "full_name": signatory.full_name,
                        "authority_basis": signatory.authority_basis,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            checks = list(
                self.db.scalars(
                    select(SignatoryAuthorityCheck)
                    .where(SignatoryAuthorityCheck.signatory_id == signatory.id, SignatoryAuthorityCheck.case_id == case.id)
                    .order_by(SignatoryAuthorityCheck.checked_at.desc())
                )
            )
            (destination / "authority_checks.json").write_text(
                json.dumps(
                    [
                        {
                            "id": item.id,
                            "document_kind": item.document_kind,
                            "required_scopes": OrganizationService.scope_to_list(item.required_scopes),
                            "result": item.result,
                            "reason": item.reason,
                            "power_of_attorney_id": item.power_of_attorney_id,
                            "checked_at": item.checked_at.isoformat(),
                        }
                        for item in checks
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if signatory.employee_id is not None:
                employee = signatory.employee
                if employee is not None:
                    (destination / "employee.json").write_text(
                        json.dumps(
                            {
                                "id": employee.id,
                                "full_name": employee.full_name,
                                "position": employee.position,
                                "email": employee.email,
                                "user_id": employee.user_id,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    powers = OrganizationService(self.db).list_powers_for_employee(employee.id)
                    selected_ids = {item.power_of_attorney_id for item in checks if item.power_of_attorney_id}
                    for power in powers:
                        if power.id in selected_ids or not selected_ids:
                            self._copy_if_exists(Path(power.file_path), destination / Path(power.file_path).name)
                    (destination / "powers_of_attorney.json").write_text(
                        json.dumps(
                            [
                                {
                                    "id": power.id,
                                    "number": power.number,
                                    "issued_at": power.issued_at.isoformat(),
                                    "expires_at": power.expires_at.isoformat(),
                                    "status": power.status,
                                    "authority_scope": OrganizationService.scope_to_list(power.authority_scope),
                                    "file_path": power.file_path,
                                }
                                for power in powers
                            ],
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )

    def _write_pretension(self, case: Case, destination: Path) -> None:
        pretension = case.pretension
        (destination / "pretension.txt").write_text(pretension.content if pretension else "", encoding="utf-8")
        (destination / "pretension_versions.json").write_text(
            json.dumps(
                [
                    {
                        "version": version.version,
                        "approved": version.is_approved_snapshot,
                        "created_at": version.created_at.isoformat(),
                    }
                    for version in (pretension.versions if pretension else [])
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_claim(self, case: Case, destination: Path) -> None:
        claim = case.claim
        (destination / "claim.txt").write_text(claim.content if claim else "", encoding="utf-8")
        (destination / "claim_versions.json").write_text(
            json.dumps(
                [
                    {
                        "version": version.version,
                        "approved": version.is_approved_snapshot,
                        "created_at": version.created_at.isoformat(),
                    }
                    for version in (claim.versions if claim else [])
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_approved(self, case: Case, destination: Path) -> None:
        approved_documents = [document for document in case.documents if document.is_approved]
        if approved_documents:
            self._copy_documents(approved_documents, destination)
        if case.claim is not None and case.claim.approved:
            (destination / "approved_claim.txt").write_text(case.claim.content, encoding="utf-8")
        if case.pretension is not None and case.pretension.approved:
            (destination / "approved_pretension.txt").write_text(case.pretension.content, encoding="utf-8")

    def _write_claim_amount(self, case: Case, destination: Path) -> None:
        (destination / "claim_amount.txt").write_text(str(case.claim_amount), encoding="utf-8")
        (destination / "appendix_list.txt").write_text(self._build_appendix_list(case), encoding="utf-8")

    def _write_rag_report(self, case: Case, destination: Path) -> None:
        citations = list(self.db.scalars(select(RagCitation).where(RagCitation.case_id == case.id)))
        source_ids = {citation.source_id for citation in citations}
        sources = list(
            self.db.scalars(
                select(RagSource).where(
                    (RagSource.case_id == case.id) | RagSource.id.in_(source_ids or {-1})
                )
            )
        )
        (destination / "rag_report.json").write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "id": source.id,
                            "title": source.title,
                            "source_type": source.source_type,
                            "category": source.category,
                            "jurisdiction": source.jurisdiction,
                            "fragment": source.fragment,
                            "score": source.score,
                            "path": source.url_or_internal_path,
                        }
                        for source in sources
                    ],
                    "citations": [
                        {
                            "id": citation.id,
                            "source_id": citation.source_id,
                            "target_type": citation.target_type,
                            "target_id": citation.target_id,
                            "quote": citation.quote,
                        }
                        for citation in citations
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_postal_dispatches(self, case: Case, destination: Path, *, dispatch_kind: str) -> None:
        dispatches = [dispatch for dispatch in case.postal_dispatches if dispatch.dispatch_kind == dispatch_kind]
        (destination / "dispatches.json").write_text(
            json.dumps(
                [
                    {
                        "id": dispatch.id,
                        "recipient_name": dispatch.recipient_name,
                        "recipient_address": dispatch.recipient_address,
                        "status": dispatch.status,
                        "tracking_number": dispatch.tracking_number,
                        "source": dispatch.source,
                        "proofs": [
                            {
                                "id": proof.id,
                                "file_name": proof.file_name,
                                "proof_type": proof.proof_type,
                                "file_path": proof.file_path,
                            }
                            for proof in dispatch.proof_documents
                        ],
                    }
                    for dispatch in dispatches
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        for dispatch in dispatches:
            for proof in dispatch.proof_documents:
                self._copy_if_exists(Path(proof.file_path), destination / Path(proof.file_path).name)

    def _write_court_package(self, case: Case, destination: Path) -> None:
        packages = list(
            self.db.scalars(
                select(CourtSubmissionPackage)
                .where(CourtSubmissionPackage.case_id == case.id)
                .order_by(CourtSubmissionPackage.created_at.desc())
            )
        )
        (destination / "submission_packages.json").write_text(
            json.dumps(
                [
                    {
                        "id": package.id,
                        "status": package.status,
                        "package_path": package.package_path,
                        "note": package.note,
                        "created_at": package.created_at.isoformat(),
                    }
                    for package in packages
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        for package in packages:
            self._copy_if_exists(Path(package.package_path), destination / Path(package.package_path).name)
        (destination / "claim.txt").write_text(case.claim.content if case.claim else "", encoding="utf-8")
        (destination / "appendix_list.txt").write_text(self._build_appendix_list(case), encoding="utf-8")

    def _write_court_events(self, case: Case, destination: Path) -> None:
        linked_cases = list(
            self.db.scalars(
                select(ExternalCourtCase).where(ExternalCourtCase.linked_case_id == case.id).order_by(ExternalCourtCase.created_at.desc())
            )
        )
        (destination / "external_court_cases.json").write_text(
            json.dumps(
                [
                    {
                        "id": external_case.id,
                        "external_case_uid": external_case.external_case_uid,
                        "case_number": external_case.case_number,
                        "court_name": external_case.court_name,
                        "participant_role": external_case.participant_role,
                        "claim_subject": external_case.claim_subject,
                        "payload_hash": external_case.payload_hash,
                        "events": [
                            {
                                "event_type": event.event_type,
                                "event_date": event.event_date.isoformat() if event.event_date else None,
                                "description": event.description,
                            }
                            for event in external_case.events
                        ],
                        "snapshots": [
                            {
                                "source": snapshot.source,
                                "snapshot_hash": snapshot.snapshot_hash,
                                "snapshot_payload": snapshot.snapshot_payload,
                            }
                            for snapshot in external_case.snapshots
                        ],
                    }
                    for external_case in linked_cases
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _write_audit_log(self, case: Case, destination: Path) -> None:
        (destination / "audit_log.txt").write_text(self._build_audit_log(case), encoding="utf-8")

    def _build_appendix_list(self, case: Case) -> str:
        lines = ["Appendix list:"]
        for document in case.documents:
            lines.append(f"- {document.filename}")
        if case.pretension:
            lines.append("- pretension.txt")
        if case.claim:
            lines.append("- claim.txt")
        if case.signatory and case.signatory.employee_id is not None:
            lines.append("- powers_of_attorney.json")
        lines.append("- rag_report.json")
        lines.append("- audit_log.txt")
        return "\n".join(lines)

    def _build_audit_log(self, case: Case) -> str:
        related_entity_ids = [str(document.id) for document in case.documents]
        entries = list(
            self.db.scalars(
                select(AuditLog)
                .where(
                    ((AuditLog.entity_type == "case") & (AuditLog.entity_id == str(case.id)))
                    | ((AuditLog.entity_type == "document") & AuditLog.entity_id.in_(related_entity_ids or ["-1"]))
                    | ((AuditLog.entity_type == "postal_dispatch") & (AuditLog.details.contains(str(case.id))))
                    | ((AuditLog.entity_type == "court_submission_package") & (AuditLog.details.contains(str(case.id))))
                )
                .order_by(AuditLog.created_at.asc())
            )
        )
        if not entries:
            return "No audit entries available."
        return "\n".join(
            f"{entry.created_at.isoformat()} | {entry.action} | {entry.entity_type}:{entry.entity_id} | {entry.details}"
            for entry in entries
        )

    @staticmethod
    def _copy_if_exists(source: Path, destination: Path) -> None:
        if source.exists():
            copy2(source, destination)

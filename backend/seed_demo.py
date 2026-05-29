from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.main import seed_defaults
from app.models import (
    Case,
    CaseStatus,
    Claim,
    ClaimVersion,
    CourtCaseImportJob,
    CourtSubmissionPackage,
    Document,
    DocumentVersion,
    ExportPackage,
    ExtractedFact,
    FnsCompanyLookupLog,
    Organization,
    OrganizationReviewStatus,
    OrganizationSnapshot,
    PilotFeedback,
    PilotFeedbackSeverity,
    PilotFeedbackStatus,
    PilotFeedbackModule,
    PostalDispatch,
    PostalDispatchKind,
    PowerOfAttorney,
    PowerOfAttorneyHistory,
    PowerOfAttorneyStatus,
    Pretension,
    PretensionVersion,
    RagCitation,
    User,
    WorkflowEvent,
)
from app.schemas.case import CaseCreate
from app.services.case_service import CaseService
from app.services.court_import_service import CourtImportService
from app.services.authority_service import AuthorityService
from app.services.organization_service import OrganizationService
from app.services.postal_dispatch_service import PostalDispatchService
from app.services.rag_service import RagService
from app.services.storage_service import LocalStorageService
from app.services.workflow_service import WorkflowService


def _save_text(storage: LocalStorageService, subdir: str, filename: str, content: str) -> str:
    return storage.save_bytes(subdir=subdir, filename=filename, payload=content.encode("utf-8"))


def _set_case_timeline(case: Case, *, created_at: datetime) -> None:
    case.created_at = created_at


def _ensure_workflow_event(
    db: Session,
    *,
    case_id: int,
    from_status: str,
    to_status: str,
    actor_user_id: int | None,
    comment: str,
    created_at: datetime,
) -> None:
    existing = db.scalar(
        select(WorkflowEvent).where(
            WorkflowEvent.case_id == case_id,
            WorkflowEvent.to_status == to_status,
        )
    )
    if existing is not None:
        return
    db.add(
        WorkflowEvent(
            case_id=case_id,
            from_status=from_status,
            to_status=to_status,
            actor_user_id=actor_user_id,
            comment=comment,
            created_at=created_at,
        )
    )


def _ensure_document(
    db: Session,
    storage: LocalStorageService,
    *,
    case_id: int,
    filename: str,
    content: str,
    sha256: str,
    approved: bool = True,
) -> Document:
    existing = db.scalar(select(Document).where(Document.case_id == case_id, Document.filename == filename))
    if existing is not None:
        return existing
    path = _save_text(storage, f"case_{case_id}", filename, content)
    document = Document(
        case_id=case_id,
        filename=filename,
        content_type="text/plain",
        storage_path=path,
        sha256=sha256,
        extracted_text=content,
        is_approved=approved,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentVersion(
            document_id=document.id,
            version=1,
            storage_path=path,
            sha256=sha256,
            extracted_text=content,
        )
    )
    return document


def _ensure_fact(db: Session, *, case_id: int, fact_type: str, value: str, confidence: float, source_fragment: str) -> None:
    existing = db.scalar(
        select(ExtractedFact).where(
            ExtractedFact.case_id == case_id,
            ExtractedFact.fact_type == fact_type,
            ExtractedFact.value == value,
        )
    )
    if existing is None:
        db.add(
            ExtractedFact(
                case_id=case_id,
                fact_type=fact_type,
                value=value,
                confidence=confidence,
                source_fragment=source_fragment,
            )
        )


def _ensure_citation(
    rag_service: RagService,
    db: Session,
    *,
    case_id: int,
    title: str,
    fragment: str,
    target_type: str,
    target_id: int,
    quote: str,
) -> None:
    existing = db.scalar(
        select(RagCitation).where(
            RagCitation.case_id == case_id,
            RagCitation.target_type == target_type,
            RagCitation.target_id == target_id,
            RagCitation.quote == quote,
        )
    )
    if existing is not None:
        return
    source = rag_service.ingest(
        title=title,
        source_type="law",
        category=target_type,
        fragment=fragment,
        jurisdiction="RU",
        document_date="2026-05-29",
        section="pilot-demo",
        url_or_internal_path=f"/demo/{target_type}.txt",
        case_id=case_id,
        page=1,
    )
    rag_service.attach_citation(
        source_id=source.id,
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        quote=quote,
    )


def _ensure_feedback(db: Session, *, case_id: int, user_id: int) -> None:
    existing = db.scalar(select(PilotFeedback).where(PilotFeedback.case_id == case_id))
    if existing is not None:
        return
    db.add(
        PilotFeedback(
            case_id=case_id,
            user_id=user_id,
            role="lawyer",
            module=PilotFeedbackModule.AUTHORITY.value,
            severity=PilotFeedbackSeverity.MEDIUM.value,
            title="Authority block remains visible in pilot",
            description="Negative scenario is expected and must stay blocked.",
            expected_behavior="Approval and export are blocked.",
            actual_behavior="Approval and export are blocked.",
            status=PilotFeedbackStatus.TRIAGED.value,
        )
    )


def _bootstrap_sqlite_dev_schema() -> None:
    if engine.dialect.name != "sqlite":
        return

    column_definitions: dict[str, dict[str, str]] = {
        "organizations": {
            "kpp": "ALTER TABLE organizations ADD COLUMN kpp VARCHAR(16) DEFAULT ''",
            "review_status": "ALTER TABLE organizations ADD COLUMN review_status VARCHAR(50) DEFAULT 'VERIFIED'",
            "source": "ALTER TABLE organizations ADD COLUMN source VARCHAR(100) DEFAULT ''",
            "actual_at": "ALTER TABLE organizations ADD COLUMN actual_at DATETIME",
            "updated_at": "ALTER TABLE organizations ADD COLUMN updated_at DATETIME",
        },
        "signatories": {
            "employee_id": "ALTER TABLE signatories ADD COLUMN employee_id INTEGER",
        },
        "powers_of_attorney": {
            "status": "ALTER TABLE powers_of_attorney ADD COLUMN status VARCHAR(50) DEFAULT 'DRAFT'",
            "revoked_at": "ALTER TABLE powers_of_attorney ADD COLUMN revoked_at DATETIME",
        },
        "postal_dispatches": {
            "idempotency_key": "ALTER TABLE postal_dispatches ADD COLUMN idempotency_key VARCHAR(255) DEFAULT ''",
        },
        "documents": {
            "sha256": "ALTER TABLE documents ADD COLUMN sha256 VARCHAR(64) DEFAULT ''",
        },
        "document_versions": {
            "sha256": "ALTER TABLE document_versions ADD COLUMN sha256 VARCHAR(64) DEFAULT ''",
        },
        "external_court_cases": {
            "payload_hash": "ALTER TABLE external_court_cases ADD COLUMN payload_hash VARCHAR(64) DEFAULT ''",
        },
        "court_case_snapshots": {
            "snapshot_hash": "ALTER TABLE court_case_snapshots ADD COLUMN snapshot_hash VARCHAR(64) DEFAULT ''",
        },
    }

    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name, definitions in column_definitions.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
            for column_name, ddl in definitions.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(ddl))


def main() -> None:
    _bootstrap_sqlite_dev_schema()
    Base.metadata.create_all(bind=engine)
    seed_defaults()
    storage = LocalStorageService()

    with Session(engine) as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        lawyer = db.scalar(select(User).where(User.email == "lawyer@example.com"))
        initiator = db.scalar(select(User).where(User.email == "initiator@example.com"))
        if admin is None or lawyer is None or initiator is None:
            raise RuntimeError("Seed users are missing.")

        org_service = OrganizationService(db)
        court_service = CourtImportService(db)
        postal_service = PostalDispatchService(db)
        rag_service = RagService(db)
        workflow = WorkflowService(db)

        organization = db.scalar(select(Organization).where(Organization.inn == "7701234567"))
        if organization is None:
            organization = Organization(
                inn="7701234567",
                kpp="770101001",
                short_name="OOO Alpha",
                full_name="Obshchestvo s ogranichennoy otvetstvennostyu Alpha",
                ogrn="1027700123456",
                legal_address="Moscow, Demo street, 1",
                current_director_name="Ivanov I.I.",
                current_director_position="General Director",
                review_status=OrganizationReviewStatus.VERIFIED.value,
                source="MOCK_FNS_PROVIDER",
            )
            db.add(organization)
            db.flush()
        if not db.scalar(select(OrganizationSnapshot).where(OrganizationSnapshot.organization_id == organization.id)):
            db.add(
                OrganizationSnapshot(
                    organization_id=organization.id,
                    source="MOCK_FNS_PROVIDER",
                    raw_payload=json.dumps({"inn": organization.inn, "kpp": organization.kpp}, ensure_ascii=False),
                )
            )
        if not db.scalar(select(FnsCompanyLookupLog).where(FnsCompanyLookupLog.organization_id == organization.id)):
            db.add(
                FnsCompanyLookupLog(
                    organization_id=organization.id,
                    inn=organization.inn,
                    provider_mode="MOCK_FOR_DEV",
                    source="MOCK_FNS_PROVIDER",
                    review_status=OrganizationReviewStatus.VERIFIED.value,
                    request_payload=json.dumps({"inn": organization.inn}, ensure_ascii=False),
                    response_payload=json.dumps({"short_name": organization.short_name}, ensure_ascii=False),
                )
            )
        db.commit()
        db.refresh(organization)

        director_employee = next((item for item in org_service.list_employees(organization.id) if item.full_name == "Ivanov I.I."), None)
        if director_employee is None:
            director_employee = org_service.create_employee(
                organization_id=organization.id,
                full_name="Ivanov I.I.",
                position="General Director",
                email="director@example.com",
                user_id=None,
            )
        lawyer_employee = next((item for item in org_service.list_employees(organization.id) if item.full_name == "Petrov P.P."), None)
        if lawyer_employee is None:
            lawyer_employee = org_service.create_employee(
                organization_id=organization.id,
                full_name="Petrov P.P.",
                position="Lawyer",
                email=lawyer.email,
                user_id=lawyer.id,
            )
        blocked_employee = next((item for item in org_service.list_employees(organization.id) if item.full_name == "Sidorov S.S."), None)
        if blocked_employee is None:
            blocked_employee = org_service.create_employee(
                organization_id=organization.id,
                full_name="Sidorov S.S.",
                position="Junior Lawyer",
                email="blocked-lawyer@example.com",
                user_id=None,
            )

        director_signatory = next(
            (
                item
                for item in org_service.list_signatories(organization.id)
                if item.signatory_type == "DIRECTOR"
            ),
            None,
        )
        if director_signatory is None:
            director_signatory = org_service.create_signatory(
                organization_id=organization.id,
                signatory_type="DIRECTOR",
                employee_id=None,
                full_name="",
                authority_basis="",
            )
        employee_signatory = next(
            (
                item
                for item in org_service.list_signatories(organization.id)
                if item.signatory_type == "AUTHORIZED_EMPLOYEE" and item.employee_id == lawyer_employee.id
            ),
            None,
        )
        if employee_signatory is None:
            employee_signatory = org_service.create_signatory(
                organization_id=organization.id,
                signatory_type="AUTHORIZED_EMPLOYEE",
                employee_id=lawyer_employee.id,
                full_name="",
                authority_basis="",
            )
        blocked_signatory = next((item for item in org_service.list_signatories(organization.id) if item.employee_id == blocked_employee.id), None)
        if blocked_signatory is None:
            blocked_signatory = org_service.create_signatory(
                organization_id=organization.id,
                signatory_type="AUTHORIZED_EMPLOYEE",
                employee_id=blocked_employee.id,
                full_name="",
                authority_basis="",
            )

        poa_numbers = {item.number for item in org_service.list_powers_for_employee(lawyer_employee.id)}
        if "DEMO-POA-ACTIVE" not in poa_numbers:
            org_service.create_power_of_attorney(
                employee_id=lawyer_employee.id,
                user_id=lawyer.id,
                number="DEMO-POA-ACTIVE",
                issued_at=date(2026, 1, 1),
                expires_at=date(2026, 12, 31),
                authority_scope=["SIGN_PRETENSION", "SIGN_CLAIM", "REPRESENT_IN_COURT"],
                file_name="demo-poa-active.pdf",
                file_bytes=b"demo poa active",
            )
        if "DEMO-POA-EXPIRED" not in poa_numbers:
            power = org_service.create_power_of_attorney(
                employee_id=lawyer_employee.id,
                user_id=lawyer.id,
                number="DEMO-POA-EXPIRED",
                issued_at=date(2025, 1, 1),
                expires_at=date(2025, 12, 31),
                authority_scope=["SIGN_CLAIM"],
                file_name="demo-poa-expired.pdf",
                file_bytes=b"demo poa expired",
            )
            power.status = PowerOfAttorneyStatus.EXPIRED.value
            db.add(power)
            db.add(PowerOfAttorneyHistory(power_of_attorney_id=power.id, event_type="expired", details=power.number))
            db.commit()
        if "DEMO-POA-REVOKED" not in poa_numbers:
            power = org_service.create_power_of_attorney(
                employee_id=lawyer_employee.id,
                user_id=lawyer.id,
                number="DEMO-POA-REVOKED",
                issued_at=date(2026, 1, 1),
                expires_at=date(2026, 12, 31),
                authority_scope=["SIGN_CLAIM"],
                file_name="demo-poa-revoked.pdf",
                file_bytes=b"demo poa revoked",
            )
            power.status = PowerOfAttorneyStatus.REVOKED.value
            power.revoked_at = datetime.now(UTC)
            db.add(power)
            db.add(PowerOfAttorneyHistory(power_of_attorney_id=power.id, event_type="revoked", details=power.number))
            db.commit()
        blocked_power_numbers = {item.number for item in org_service.list_powers_for_employee(blocked_employee.id)}
        if "DEMO-POA-BLOCKED-EXPIRED" not in blocked_power_numbers:
            power = org_service.create_power_of_attorney(
                employee_id=blocked_employee.id,
                user_id=None,
                number="DEMO-POA-BLOCKED-EXPIRED",
                issued_at=date(2025, 1, 1),
                expires_at=date(2025, 12, 31),
                authority_scope=["SIGN_CLAIM"],
                file_name="demo-poa-blocked-expired.pdf",
                file_bytes=b"demo blocked poa expired",
            )
            power.status = PowerOfAttorneyStatus.EXPIRED.value
            db.add(power)
            db.add(PowerOfAttorneyHistory(power_of_attorney_id=power.id, event_type="expired", details=power.number))
            db.commit()
        if "DEMO-POA-BLOCKED-REVOKED" not in blocked_power_numbers:
            power = org_service.create_power_of_attorney(
                employee_id=blocked_employee.id,
                user_id=None,
                number="DEMO-POA-BLOCKED-REVOKED",
                issued_at=date(2026, 1, 1),
                expires_at=date(2026, 12, 31),
                authority_scope=["SIGN_CLAIM"],
                file_name="demo-poa-blocked-revoked.pdf",
                file_bytes=b"demo blocked poa revoked",
            )
            power.status = PowerOfAttorneyStatus.REVOKED.value
            power.revoked_at = datetime.now(UTC)
            db.add(power)
            db.add(PowerOfAttorneyHistory(power_of_attorney_id=power.id, event_type="revoked", details=power.number))
            db.commit()

        base_created_at = datetime.now(UTC) - timedelta(days=2)
        case_specs = [
            {
                "title": "DEMO-001 director happy path",
                "description": "Debt recovery case signed by director.",
                "respondent": "OOO Beta",
                "amount": 1250000.0,
                "signatory_id": director_signatory.id,
                "contract": "Supply contract No 123/24. Debt 1250000 RUB.",
                "citation_quote": "copy of the claim to the respondent",
                "proof_suffix": "001",
                "should_block": False,
                "created_at": base_created_at,
            },
            {
                "title": "DEMO-002 employee happy path",
                "description": "Debt recovery case signed by employee under active POA.",
                "respondent": "OOO Gamma",
                "amount": 2100000.0,
                "signatory_id": employee_signatory.id,
                "contract": "Supply contract No 456/24. Debt 2100000 RUB.",
                "citation_quote": "pretrial procedure must be reflected",
                "proof_suffix": "002",
                "should_block": False,
                "created_at": base_created_at + timedelta(hours=4),
            },
            {
                "title": "DEMO-003 authority block path",
                "description": "Attempted approval with expired or revoked POA must stay blocked.",
                "respondent": "OOO Delta",
                "amount": 480000.0,
                "signatory_id": blocked_signatory.id,
                "contract": "Supply contract No 789/24. Debt 480000 RUB.",
                "citation_quote": "manual review is required if authority is not confirmed",
                "proof_suffix": "003",
                "should_block": True,
                "created_at": base_created_at + timedelta(hours=8),
            },
        ]

        created_cases: list[Case] = []
        for spec in case_specs:
            case = db.scalar(select(Case).where(Case.title == spec["title"]))
            if case is None:
                case = CaseService(db).create_case(
                    current_user=initiator,
                    data=CaseCreate(
                        title=spec["title"],
                        description=spec["description"],
                        claimant_name="OOO Alpha",
                        respondent_name=spec["respondent"],
                        claim_amount=spec["amount"],
                        assigned_lawyer_id=lawyer.id,
                        plaintiff_organization_id=organization.id,
                        signatory_id=spec["signatory_id"],
                    ),
                )
            _set_case_timeline(case, created_at=spec["created_at"])
            case.assigned_lawyer_id = lawyer.id
            case.plaintiff_organization_id = organization.id
            case.signatory_id = spec["signatory_id"]
            db.add(case)
            db.commit()
            db.refresh(case)

            _ensure_document(db, storage, case_id=case.id, filename="contract.txt", content=spec["contract"], sha256=f"demo-sha-{case.id}-1")
            _ensure_document(db, storage, case_id=case.id, filename="act.txt", content=f"Acceptance act for {spec['amount']} RUB.", sha256=f"demo-sha-{case.id}-2")
            _ensure_document(db, storage, case_id=case.id, filename="invoice.txt", content=f"Invoice amount {spec['amount']} RUB.", sha256=f"demo-sha-{case.id}-3")
            _ensure_fact(db, case_id=case.id, fact_type="contract_number", value=spec["title"].split()[0], confidence=0.92, source_fragment=spec["contract"])
            _ensure_fact(db, case_id=case.id, fact_type="claim_amount", value=str(int(spec["amount"])), confidence=0.88, source_fragment=str(spec["amount"]))

            pretension = db.scalar(select(Pretension).where(Pretension.case_id == case.id))
            claim = db.scalar(select(Claim).where(Claim.case_id == case.id))
            if pretension is None or claim is None:
                raise RuntimeError("Case draft documents are missing")
            pretension.content = f"Pretension draft for {spec['title']}."
            claim.content = f"Claim draft for {spec['title']}."
            pretension.updated_at = spec["created_at"] + timedelta(minutes=20)
            claim.updated_at = spec["created_at"] + timedelta(minutes=45)
            db.add(pretension)
            db.add(claim)
            db.commit()

            if not db.scalar(select(PretensionVersion).where(PretensionVersion.pretension_id == pretension.id, PretensionVersion.version == 2)):
                db.add(PretensionVersion(pretension_id=pretension.id, version=2, content=pretension.content, is_approved_snapshot=False))
            if not db.scalar(select(ClaimVersion).where(ClaimVersion.claim_id == claim.id, ClaimVersion.version == 2)):
                db.add(ClaimVersion(claim_id=claim.id, version=2, content=claim.content, is_approved_snapshot=False))

            _ensure_workflow_event(db, case_id=case.id, from_status=CaseStatus.NEW.value, to_status=CaseStatus.FACTS_EXTRACTED.value, actor_user_id=initiator.id, comment="Facts extracted", created_at=spec["created_at"] + timedelta(minutes=10))
            _ensure_workflow_event(db, case_id=case.id, from_status=CaseStatus.FACTS_EXTRACTED.value, to_status=CaseStatus.PRETENSION_DRAFT_READY.value, actor_user_id=lawyer.id, comment="Pretension draft ready", created_at=spec["created_at"] + timedelta(minutes=20))
            _ensure_workflow_event(db, case_id=case.id, from_status=CaseStatus.PRETENSION_APPROVED.value, to_status=CaseStatus.CLAIM_DRAFT_READY.value, actor_user_id=lawyer.id, comment="Claim draft ready", created_at=spec["created_at"] + timedelta(minutes=45))
            db.commit()

            _ensure_citation(
                rag_service,
                db,
                case_id=case.id,
                title=f"RAG source for {spec['title']}",
                fragment=f"Legal source for {spec['title']} says {spec['citation_quote']}.",
                target_type="claim",
                target_id=claim.id,
                quote=spec["citation_quote"],
            )
            if not spec["should_block"]:
                _ensure_citation(
                    rag_service,
                    db,
                    case_id=case.id,
                    title=f"Pretension source for {spec['title']}",
                    fragment=f"Pretrial source for {spec['title']}.",
                    target_type="pretension",
                    target_id=pretension.id,
                    quote="send a pretension before the claim",
                )

            if not spec["should_block"] and not pretension.approved:
                workflow.approve_pretension(pretension, lawyer)
            if not spec["should_block"] and not claim.approved:
                workflow.approve_claim(claim, lawyer)
            if spec["should_block"]:
                try:
                    AuthorityService(db).ensure_case_signatory_has_authority(case, document_kind="claim")
                except Exception:
                    db.rollback()

            if not db.scalar(select(PostalDispatch).where(PostalDispatch.case_id == case.id, PostalDispatch.dispatch_kind == PostalDispatchKind.pretension.value)):
                dispatch = postal_service.create_dispatch(
                    case_id=case.id,
                    organization_id=organization.id,
                    dispatch_kind=PostalDispatchKind.pretension.value,
                    recipient_name=spec["respondent"],
                    recipient_address="Moscow, Respondent street, 7",
                    provider_mode="MOCK_FOR_DEV",
                    current_user=lawyer,
                )
                postal_service.refresh_status(dispatch.id)
                postal_service.upload_proof(
                    dispatch_id=dispatch.id,
                    proof_type="pretension_dispatch_receipt",
                    file_name=f"pretension-proof-{spec['proof_suffix']}.pdf",
                    file_bytes=b"pretension proof",
                    current_user=lawyer,
                )

            if not spec["should_block"] and not db.scalar(select(PostalDispatch).where(PostalDispatch.case_id == case.id, PostalDispatch.dispatch_kind == PostalDispatchKind.claim_copy.value)):
                dispatch = postal_service.create_dispatch(
                    case_id=case.id,
                    organization_id=organization.id,
                    dispatch_kind=PostalDispatchKind.claim_copy.value,
                    recipient_name=spec["respondent"],
                    recipient_address="Moscow, Respondent street, 7",
                    provider_mode="MOCK_FOR_DEV",
                    current_user=lawyer,
                )
                postal_service.refresh_status(dispatch.id)
                postal_service.upload_proof(
                    dispatch_id=dispatch.id,
                    proof_type="claim_copy_dispatch_receipt",
                    file_name=f"claim-copy-proof-{spec['proof_suffix']}.pdf",
                    file_bytes=b"claim copy proof",
                    current_user=lawyer,
                )
                workflow.mark_court_package_ready(claim, lawyer)

            created_cases.append(case)

        if not db.scalar(select(CourtCaseImportJob).where(CourtCaseImportJob.organization_id == organization.id)):
            job = court_service.create_job(
                organization_id=organization.id,
                inn=organization.inn,
                date_from=date(2026, 5, 1),
                date_to=date(2026, 5, 31),
                participation_role="claimant",
                provider_mode="MOCK_FOR_DEV",
                current_user=admin,
            )
            imported_cases = court_service.list_cases(job.id)
            if imported_cases:
                court_service.link_external_case(external_case_id=imported_cases[0].id, case_id=created_cases[1].id)

        for case in created_cases[:2]:
            package = db.scalar(select(CourtSubmissionPackage).where(CourtSubmissionPackage.case_id == case.id))
            if package is None:
                external_case = court_service.list_cases()[0]
                package_path = _save_text(storage, f"case_{case.id}", "court-package.txt", f"Manual court package for {case.title}")
                db.add(
                    CourtSubmissionPackage(
                        case_id=case.id,
                        organization_id=organization.id,
                        external_court_case_id=external_case.id,
                        status="READY_FOR_MANUAL_SUBMISSION",
                        package_path=package_path,
                        created_by_id=lawyer.id,
                        note=f"Demo package for {case.title}",
                    )
                )

        _ensure_feedback(db, case_id=created_cases[2].id, user_id=lawyer.id)
        db.commit()

    print("Demo seed completed.")


if __name__ == "__main__":
    main()

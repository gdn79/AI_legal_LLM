import json
from zipfile import ZipFile

from sqlalchemy import select

from app.models import (
    Case,
    Claim,
    Document,
    FnsCompanyLookupLog,
    OrganizationReviewStatus,
    Party,
    PowerOfAttorneyStatus,
    RoleName,
    SignatoryAuthorityCheck,
    User,
)
from app.schemas.case import CaseCreate
from app.services.case_service import CaseService
from app.services.court_import_service import CourtImportService
from app.services.document_pipeline_service import DocumentPipelineService
from app.services.document_processing_service import DocumentProcessingService
from app.services.export_service import ExportService
from app.services.organization_service import OrganizationService
from app.services.postal_dispatch_service import PostalDispatchService
from app.services.workflow_service import WorkflowService
from app.tests.helpers import build_docx_bytes, build_pdf_bytes, build_xlsx_bytes


def test_seed_users_exist(db_session):
    users = db_session.scalars(select(User)).all()
    assert {user.email for user in users} == {
        "admin@example.com",
        "lawyer@example.com",
        "manager@example.com",
        "initiator@example.com",
        "service-agent@example.com",
    }


def test_case_service_creates_parties_and_checklist(db_session):
    current_user = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    assert current_user is not None

    case = CaseService(db_session).create_case(
        current_user=current_user,
        data=CaseCreate(
            title="Unit case",
            description="Unit description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=5000.0,
            assigned_lawyer_id=2,
        ),
    )

    parties = db_session.scalars(select(Party).where(Party.case_id == case.id)).all()
    assert len(parties) == 2
    assert {party.role for party in parties} == {"claimant", "respondent"}
    assert case.checklist is not None
    assert len(case.checklist.items) == 3


def test_document_processing_service_extracts_supported_formats():
    service = DocumentProcessingService()

    assert service.extract_text(filename="contract.txt", content_type="text/plain", payload="hello".encode()) == "hello"
    assert "Invoice 77" in service.extract_text(
        filename="invoice.pdf",
        content_type="application/pdf",
        payload=build_pdf_bytes("Invoice 77"),
    )
    assert "Contract DOCX Text" in service.extract_text(
        filename="contract.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        payload=build_docx_bytes("Contract DOCX Text"),
    )
    assert "Table Cell Value" in service.extract_text(
        filename="calc.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        payload=build_xlsx_bytes("Table Cell Value"),
    )
    assert "OCR required" in service.extract_text(filename="scan.png", content_type="image/png", payload=b"\x89PNG\r\n")


def test_organization_service_creates_snapshot_director_and_lookup_log(db_session):
    service = OrganizationService(db_session)
    organization = service.create_or_refresh_by_inn("7701234567")
    assert organization.current_director_name
    assert organization.kpp
    assert organization.review_status == OrganizationReviewStatus.VERIFIED.value
    snapshots = service.list_snapshots(organization.id)
    assert snapshots
    lookup_logs = service.list_lookup_logs(organization.id)
    assert lookup_logs
    assert lookup_logs[0].inn == "7701234567"

    director = service.create_signatory(
        organization_id=organization.id,
        signatory_type="DIRECTOR",
        employee_id=None,
        full_name="",
        authority_basis="",
    )
    assert director.full_name == organization.current_director_name
    assert director.authority_basis == "FNS_DIRECTOR"


def test_fns_incomplete_data_requires_manual_review(db_session):
    service = OrganizationService(db_session)
    organization = service.create_or_refresh_by_inn("7701200000")
    assert organization.review_status == OrganizationReviewStatus.REQUIRES_MANUAL_REVIEW.value
    lookup_log = db_session.scalar(select(FnsCompanyLookupLog).where(FnsCompanyLookupLog.organization_id == organization.id))
    assert lookup_log is not None
    assert lookup_log.review_status == OrganizationReviewStatus.REQUIRES_MANUAL_REVIEW.value


def test_repeated_fns_lookup_without_refresh_does_not_duplicate_snapshot(db_session):
    service = OrganizationService(db_session)
    organization = service.create_or_refresh_by_inn("7701234501")
    snapshot_count = len(service.list_snapshots(organization.id))
    lookup_count = len(service.list_lookup_logs(organization.id))
    service.create_or_refresh_by_inn("7701234501")
    assert len(service.list_snapshots(organization.id)) == snapshot_count
    assert len(service.list_lookup_logs(organization.id)) == lookup_count
    service.refresh_organization(organization.id)
    assert len(service.list_snapshots(organization.id)) == snapshot_count + 1
    assert len(service.list_lookup_logs(organization.id)) == lookup_count + 1


def test_workflow_service_saves_director_authority_check(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))
    organizations = OrganizationService(db_session)
    organization = organizations.create_or_refresh_by_inn("7701234567")
    director_signatory = organizations.create_signatory(
        organization_id=organization.id,
        signatory_type="DIRECTOR",
        employee_id=None,
        full_name="",
        authority_basis="",
    )
    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="Workflow case",
            description="Workflow description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
            plaintiff_organization_id=organization.id,
            signatory_id=director_signatory.id,
        ),
    )
    claim = db_session.scalar(select(Claim).where(Claim.case_id == case.id))
    approved = WorkflowService(db_session).approve_claim(claim, lawyer)
    assert approved.approved is True
    check = db_session.scalar(select(SignatoryAuthorityCheck).where(SignatoryAuthorityCheck.signatory_id == director_signatory.id))
    assert check is not None
    assert check.result == "PASSED"


def test_expired_revoked_and_suspended_poa_block_claim_approval(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))
    organizations = OrganizationService(db_session)
    organization = organizations.create_or_refresh_by_inn("7701234568")
    employee = organizations.create_employee(
        organization_id=organization.id,
        full_name="Petrov Employee",
        position="Lawyer",
        email="employee@example.com",
        user_id=None,
    )
    signatory = organizations.create_signatory(
        organization_id=organization.id,
        signatory_type="AUTHORIZED_EMPLOYEE",
        employee_id=employee.id,
        full_name="",
        authority_basis="",
    )
    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="POA case",
            description="Workflow description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
            plaintiff_organization_id=organization.id,
            signatory_id=signatory.id,
        ),
    )
    claim = db_session.scalar(select(Claim).where(Claim.case_id == case.id))

    expired = organizations.create_power_of_attorney(
        employee_id=employee.id,
        user_id=None,
        number="POA-EXPIRED",
        issued_at=claim.updated_at.date().replace(year=2025),
        expires_at=claim.updated_at.date().replace(year=2025),
        authority_scope=["SIGN_CLAIM", "REPRESENT_IN_COURT"],
        file_name="expired.pdf",
        file_bytes=b"expired",
    )
    organizations.ensure_power_status(expired)
    try:
        WorkflowService(db_session).approve_claim(claim, lawyer)
        assert False, "Expired power of attorney should block claim approval"
    except Exception as exc:
        assert "expired" in str(exc).lower()

    active = organizations.create_power_of_attorney(
        employee_id=employee.id,
        user_id=None,
        number="POA-ACTIVE",
        issued_at=claim.updated_at.date(),
        expires_at=claim.updated_at.date().replace(year=2027),
        authority_scope=["SIGN_CLAIM", "REPRESENT_IN_COURT"],
        file_name="active.pdf",
        file_bytes=b"active",
    )
    active.status = PowerOfAttorneyStatus.REVOKED.value
    db_session.add(active)
    db_session.commit()
    try:
        WorkflowService(db_session).approve_claim(claim, lawyer)
        assert False, "Revoked power of attorney should block claim approval"
    except Exception as exc:
        assert "not active" in str(exc).lower()

    active.status = PowerOfAttorneyStatus.SUSPENDED.value
    db_session.add(active)
    db_session.commit()
    try:
        WorkflowService(db_session).approve_claim(claim, lawyer)
        assert False, "Suspended power of attorney should block claim approval"
    except Exception as exc:
        assert "not active" in str(exc).lower()


def test_export_service_rejects_unapproved_claim(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))
    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="Export case",
            description="Export description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
        ),
    )
    try:
        ExportService(db_session).build_export(case, lawyer)
        assert False, "Expected export to fail before approval"
    except Exception as exc:
        assert "court package must pass readiness checks" in str(exc)


def test_court_submission_requires_claim_copy_proof(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))
    organization = OrganizationService(db_session).create_or_refresh_by_inn("7701234572")
    director = OrganizationService(db_session).create_signatory(
        organization_id=organization.id,
        signatory_type="DIRECTOR",
        employee_id=None,
        full_name="",
        authority_basis="",
    )
    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="Court submission case",
            description="Package",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
            plaintiff_organization_id=organization.id,
            signatory_id=director.id,
        ),
    )
    claim = db_session.scalar(select(Claim).where(Claim.case_id == case.id))
    claim.content = "Claim draft for court submission"
    db_session.add(claim)
    db_session.commit()
    WorkflowService(db_session).approve_claim(claim, lawyer)

    try:
        CourtImportService(db_session).prepare_submission_package(
            case=case,
            current_user=lawyer,
            external_court_case_id=None,
            note="manual",
        )
        assert False, "Expected proof gate to block package preparation"
    except Exception as exc:
        assert "доказательство направления копии иска" in str(exc)

    dispatch = PostalDispatchService(db_session).create_dispatch(
        case_id=case.id,
        organization_id=organization.id,
        dispatch_kind="claim_copy",
        recipient_name="OOO Beta",
        recipient_address="Moscow",
        provider_mode="MOCK_FOR_DEV",
        current_user=lawyer,
    )
    PostalDispatchService(db_session).refresh_status(dispatch.id)
    PostalDispatchService(db_session).upload_proof(
        dispatch_id=dispatch.id,
        proof_type="claim_copy_dispatch_receipt",
        file_name="proof.pdf",
        file_bytes=b"proof",
        current_user=lawyer,
    )
    package = CourtImportService(db_session).prepare_submission_package(
        case=case,
        current_user=lawyer,
        external_court_case_id=None,
        note="manual",
    )
    assert package.status == "READY_FOR_MANUAL_SUBMISSION"


def test_document_sha256_and_court_snapshot_hash_are_stored(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    admin = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))

    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="Hash case",
            description="Hash description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
        ),
    )

    pipeline = DocumentPipelineService(db_session)
    class DummyUpload:
        filename = "contract.txt"
        content_type = "text/plain"
        async def read(self):
            return b"hash-payload"
    document = __import__("asyncio").run(
        pipeline.create_document(case_id=case.id, upload=DummyUpload(), current_user=initiator, request_id="test")
    )
    assert document.sha256
    version = document.versions[0]
    assert version.sha256 == document.sha256

    organization = OrganizationService(db_session).create_or_refresh_by_inn("7701234599")
    job = CourtImportService(db_session).create_job(
        organization_id=organization.id,
        inn=organization.inn,
        date_from=case.created_at.date(),
        date_to=case.created_at.date(),
        participation_role="claimant",
        provider_mode="MOCK_FOR_DEV",
        current_user=admin,
    )
    external_case = db_session.scalar(select(Case).where(Case.id == case.id))
    assert job.result_count >= 0
    imported = CourtImportService(db_session).list_cases(job.id)
    assert imported
    assert imported[0].payload_hash
    assert imported[0].snapshots[0].snapshot_hash


def test_export_contains_12_folders_and_core_artifacts(db_session):
    initiator = db_session.scalar(select(User).where(User.email == "initiator@example.com"))
    lawyer = db_session.scalar(select(User).where(User.email == "lawyer@example.com"))
    admin = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    org_service = OrganizationService(db_session)
    organization = org_service.create_or_refresh_by_inn("7701234588")
    employee = org_service.create_employee(
        organization_id=organization.id,
        full_name="Employee Signer",
        position="Counsel",
        email="emp@example.com",
        user_id=None,
    )
    signatory = org_service.create_signatory(
        organization_id=organization.id,
        signatory_type="AUTHORIZED_EMPLOYEE",
        employee_id=employee.id,
        full_name="",
        authority_basis="",
    )
    power = org_service.create_power_of_attorney(
        employee_id=employee.id,
        user_id=None,
        number="POA-EXPORT",
        issued_at=initiator.created_at.date(),
        expires_at=initiator.created_at.date().replace(year=2027),
        authority_scope=["SIGN_PRETENSION", "SIGN_CLAIM", "REPRESENT_IN_COURT"],
        file_name="poa.pdf",
        file_bytes=b"poa",
    )
    case = CaseService(db_session).create_case(
        current_user=initiator,
        data=CaseCreate(
            title="Export full",
            description="Export full description",
            claimant_name="OOO Alpha",
            respondent_name="OOO Beta",
            claim_amount=1000.0,
            assigned_lawyer_id=lawyer.id,
            plaintiff_organization_id=organization.id,
            signatory_id=signatory.id,
        ),
    )
    claim = db_session.scalar(select(Claim).where(Claim.case_id == case.id))
    claim.content = "Claim body"
    case.pretension.content = "Pretension body"
    db_session.add(claim)
    db_session.add(case.pretension)
    document = Document(
        case_id=case.id,
        filename="contract.txt",
        content_type="text/plain",
        storage_path=power.file_path,
        sha256="abc",
        extracted_text="doc",
        is_approved=True,
    )
    db_session.add(document)
    db_session.commit()

    WorkflowService(db_session).approve_pretension(case.pretension, lawyer)
    WorkflowService(db_session).approve_claim(claim, lawyer)

    dispatch = PostalDispatchService(db_session).create_dispatch(
        case_id=case.id,
        organization_id=organization.id,
        dispatch_kind="claim_copy",
        recipient_name="OOO Beta",
        recipient_address="Moscow",
        provider_mode="MOCK_FOR_DEV",
        current_user=lawyer,
    )
    PostalDispatchService(db_session).refresh_status(dispatch.id)
    PostalDispatchService(db_session).upload_proof(
        dispatch_id=dispatch.id,
        proof_type="claim_copy_dispatch_receipt",
        file_name="proof.pdf",
        file_bytes=b"proof",
        current_user=lawyer,
    )
    job = CourtImportService(db_session).create_job(
        organization_id=organization.id,
        inn=organization.inn,
        date_from=case.created_at.date(),
        date_to=case.created_at.date(),
        participation_role="claimant",
        provider_mode="MOCK_FOR_DEV",
        current_user=admin,
    )
    external_case = CourtImportService(db_session).list_cases(job.id)[0]
    CourtImportService(db_session).link_external_case(external_case_id=external_case.id, case_id=case.id)
    CourtImportService(db_session).prepare_submission_package(case=case, current_user=lawyer, external_court_case_id=external_case.id, note="manual")

    exported = ExportService(db_session).build_export(case, lawyer, mutate_status=False)
    with ZipFile(exported.archive_path) as archive:
        names = set(archive.namelist())
    for folder in range(1, 13):
        assert any(name.startswith(f"Дело_{case.id}/{folder:02d}_") for name in names)
    assert any("02_Организация_и_полномочия/powers_of_attorney.json" in name for name in names)
    assert any("09_Направление_копии_иска/proof.pdf" in name for name in names)
    assert any("08_Источники_RAG/rag_report.json" in name for name in names)
    assert any("11_КАД_и_судебные_события/external_court_cases.json" in name for name in names)

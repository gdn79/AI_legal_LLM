from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class RoleName(StrEnum):
    initiator = "initiator"
    lawyer = "lawyer"
    manager = "manager"
    admin = "admin"
    service_agent = "service_agent"


class CaseStatus(StrEnum):
    NEW = "NEW"
    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    EXTRACTION_IN_PROGRESS = "EXTRACTION_IN_PROGRESS"
    FACTS_EXTRACTED = "FACTS_EXTRACTED"
    PRETENSION_DRAFT_READY = "PRETENSION_DRAFT_READY"
    PRETENSION_REVIEW = "PRETENSION_REVIEW"
    PRETENSION_APPROVED = "PRETENSION_APPROVED"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    CLAIM_DRAFT_READY = "CLAIM_DRAFT_READY"
    LAWYER_REVIEW = "LAWYER_REVIEW"
    RETURNED_FOR_REVISION = "RETURNED_FOR_REVISION"
    APPROVED_BY_LAWYER = "APPROVED_BY_LAWYER"
    COURT_PACKAGE_READY = "COURT_PACKAGE_READY"
    EXPORTED = "EXPORTED"
    CLOSED = "CLOSED"
    ERROR_MANUAL_REVIEW = "ERROR_MANUAL_REVIEW"


class SignatoryType(StrEnum):
    DIRECTOR = "DIRECTOR"
    AUTHORIZED_EMPLOYEE = "AUTHORIZED_EMPLOYEE"


class OrganizationReviewStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class PowerOfAttorneyStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class AuthorityScope(StrEnum):
    SIGN_PRETENSION = "SIGN_PRETENSION"
    SIGN_CLAIM = "SIGN_CLAIM"
    REPRESENT_IN_COURT = "REPRESENT_IN_COURT"


class RussianPostMode(StrEnum):
    RUSSIAN_POST_SANDBOX_DISABLED = "RUSSIAN_POST_SANDBOX_DISABLED"
    RUSSIAN_POST_SANDBOX_READY = "RUSSIAN_POST_SANDBOX_READY"
    RUSSIAN_POST_PRODUCTION_DISABLED = "RUSSIAN_POST_PRODUCTION_DISABLED"
    RUSSIAN_POST_OTPRAVKA_API_DISABLED = "RUSSIAN_POST_OTPRAVKA_API_DISABLED"
    RUSSIAN_POST_EZP_API_DISABLED = "RUSSIAN_POST_EZP_API_DISABLED"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    MOCK_FOR_DEV = "MOCK_FOR_DEV"


class PostalDispatchStatus(StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class PostalDispatchKind(StrEnum):
    pretension = "pretension"
    claim_copy = "claim_copy"
    other = "other"


class CourtProviderMode(StrEnum):
    MOCK_FOR_DEV = "MOCK_FOR_DEV"
    MANUAL_IMPORT = "MANUAL_IMPORT"
    COURT_SANDBOX_DISABLED = "COURT_SANDBOX_DISABLED"
    COURT_SANDBOX_READY = "COURT_SANDBOX_READY"
    PRODUCTION_DISABLED = "PRODUCTION_DISABLED"
    OFFICIAL_API_DISABLED = "OFFICIAL_API_DISABLED"
    LICENSED_PROVIDER_API_DISABLED = "LICENSED_PROVIDER_API_DISABLED"
    LICENSED_PROVIDER_SANDBOX_DISABLED = "LICENSED_PROVIDER_SANDBOX_DISABLED"
    PUBLIC_SEARCH_DISABLED = "PUBLIC_SEARCH_DISABLED"


class FnsProviderMode(StrEnum):
    MOCK_FOR_DEV = "MOCK_FOR_DEV"
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    LOCAL_EGRUL_FILES = "LOCAL_EGRUL_FILES"
    FNS_SANDBOX_DISABLED = "FNS_SANDBOX_DISABLED"
    FNS_SANDBOX_READY = "FNS_SANDBOX_READY"
    FNS_PRODUCTION_DISABLED = "FNS_PRODUCTION_DISABLED"
    OFFICIAL_FNS_INTEGRATION_DISABLED = "OFFICIAL_FNS_INTEGRATION_DISABLED"


class CourtImportStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ParticipationRole(StrEnum):
    claimant = "claimant"
    respondent = "respondent"
    any = "any"


class CourtSubmissionStatus(StrEnum):
    DRAFT = "DRAFT"
    READY_FOR_MANUAL_SUBMISSION = "READY_FOR_MANUAL_SUBMISSION"


class PilotFeedbackModule(StrEnum):
    ORGANIZATION = "ORGANIZATION"
    AUTHORITY = "AUTHORITY"
    DOCUMENTS = "DOCUMENTS"
    FACT_EXTRACTION = "FACT_EXTRACTION"
    PRETENSION = "PRETENSION"
    CLAIM = "CLAIM"
    RAG = "RAG"
    POSTAL = "POSTAL"
    COURT = "COURT"
    EXPORT = "EXPORT"
    AUDIT = "AUDIT"
    DASHBOARD = "DASHBOARD"
    UI = "UI"
    OTHER = "OTHER"


class PilotFeedbackSeverity(StrEnum):
    BLOCKER = "BLOCKER"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IDEA = "IDEA"


class PilotFeedbackStatus(StrEnum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    FIXED = "FIXED"
    WONT_FIX = "WONT_FIX"
    POSTPONED = "POSTPONED"


class IntegrationApprovalEnvironment(StrEnum):
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class IntegrationApprovalStatus(StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    role: Mapped[Role] = relationship(back_populates="users")
    employee_profiles: Mapped[list["Employee"]] = relationship(back_populates="user")
    powers_of_attorney: Mapped[list["PowerOfAttorney"]] = relationship(back_populates="user")
    pilot_feedback_items: Mapped[list["PilotFeedback"]] = relationship(back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inn: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    kpp: Mapped[str] = mapped_column(String(16), default="")
    short_name: Mapped[str] = mapped_column(String(255), default="")
    full_name: Mapped[str] = mapped_column(String(500), default="")
    ogrn: Mapped[str] = mapped_column(String(20), default="")
    legal_address: Mapped[str] = mapped_column(Text, default="")
    current_director_name: Mapped[str] = mapped_column(String(255), default="")
    current_director_position: Mapped[str] = mapped_column(String(255), default="")
    review_status: Mapped[str] = mapped_column(String(50), default=OrganizationReviewStatus.VERIFIED.value)
    source: Mapped[str] = mapped_column(String(100), default="")
    actual_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    snapshots: Mapped[list["OrganizationSnapshot"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    fns_lookup_logs: Mapped[list["FnsCompanyLookupLog"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    employees: Mapped[list["Employee"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    signatories: Mapped[list["Signatory"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    powers_of_attorney: Mapped[list["PowerOfAttorney"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    postal_dispatches: Mapped[list["PostalDispatch"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    court_import_jobs: Mapped[list["CourtCaseImportJob"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    external_court_cases: Mapped[list["ExternalCourtCase"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    court_submission_packages: Mapped[list["CourtSubmissionPackage"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    cases: Mapped[list["Case"]] = relationship(back_populates="plaintiff_organization")


class OrganizationSnapshot(Base):
    __tablename__ = "organization_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    actual_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    raw_payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization] = relationship(back_populates="snapshots")


class FnsCompanyLookupLog(Base):
    __tablename__ = "fns_company_lookup_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="")
    review_status: Mapped[str] = mapped_column(String(50), default=OrganizationReviewStatus.VERIFIED.value)
    request_payload: Mapped[str] = mapped_column(Text, default="")
    response_payload: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization | None] = relationship(back_populates="fns_lookup_logs")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization] = relationship(back_populates="employees")
    user: Mapped[User | None] = relationship(back_populates="employee_profiles")
    signatories: Mapped[list["Signatory"]] = relationship(back_populates="employee")
    powers_of_attorney: Mapped[list["PowerOfAttorney"]] = relationship(back_populates="employee")
    history_entries: Mapped[list["EmployeeHistory"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class EmployeeHistory(Base):
    __tablename__ = "employee_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    employee: Mapped[Employee] = relationship(back_populates="history_entries")


class Signatory(Base):
    __tablename__ = "signatories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    signatory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    authority_basis: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization] = relationship(back_populates="signatories")
    employee: Mapped[Employee | None] = relationship(back_populates="signatories")
    cases: Mapped[list["Case"]] = relationship(back_populates="signatory")
    authority_checks: Mapped[list["SignatoryAuthorityCheck"]] = relationship(back_populates="signatory", cascade="all, delete-orphan")


class PowerOfAttorney(Base):
    __tablename__ = "powers_of_attorney"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    number: Mapped[str] = mapped_column(String(100), nullable=False)
    issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    authority_scope: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default=PowerOfAttorneyStatus.DRAFT.value)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization] = relationship(back_populates="powers_of_attorney")
    employee: Mapped[Employee] = relationship(back_populates="powers_of_attorney")
    user: Mapped[User | None] = relationship(back_populates="powers_of_attorney")
    history_entries: Mapped[list["PowerOfAttorneyHistory"]] = relationship(back_populates="power_of_attorney", cascade="all, delete-orphan")


class PowerOfAttorneyHistory(Base):
    __tablename__ = "power_of_attorney_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    power_of_attorney_id: Mapped[int] = mapped_column(ForeignKey("powers_of_attorney.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    power_of_attorney: Mapped[PowerOfAttorney] = relationship(back_populates="history_entries")


class SignatoryAuthorityCheck(Base):
    __tablename__ = "signatory_authority_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signatory_id: Mapped[int] = mapped_column(ForeignKey("signatories.id"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    power_of_attorney_id: Mapped[int | None] = mapped_column(ForeignKey("powers_of_attorney.id"))
    document_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    required_scopes: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    signatory: Mapped[Signatory] = relationship(back_populates="authority_checks")


class PostalDispatch(Base):
    __tablename__ = "postal_dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    dispatch_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_address: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default=PostalDispatchStatus.CREATED.value)
    tracking_number: Mapped[str] = mapped_column(String(255), default="")
    external_dispatch_id: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(100), default="")
    idempotency_key: Mapped[str] = mapped_column(String(255), default="")
    status_payload: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped["Case"] = relationship(back_populates="postal_dispatches")
    organization: Mapped[Organization] = relationship(back_populates="postal_dispatches")
    proof_documents: Mapped[list["PostalProofDocument"]] = relationship(back_populates="postal_dispatch", cascade="all, delete-orphan")


class PostalProofDocument(Base):
    __tablename__ = "postal_proof_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    postal_dispatch_id: Mapped[int] = mapped_column(ForeignKey("postal_dispatches.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    proof_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    postal_dispatch: Mapped[PostalDispatch] = relationship(back_populates="proof_documents")


class CourtCaseImportJob(Base):
    __tablename__ = "court_case_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    participation_role: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=CourtImportStatus.PENDING.value)
    source: Mapped[str] = mapped_column(String(100), default="")
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    organization: Mapped[Organization] = relationship(back_populates="court_import_jobs")
    imported_cases: Mapped[list["ExternalCourtCase"]] = relationship(back_populates="import_job", cascade="all, delete-orphan")


class ExternalCourtCase(Base):
    __tablename__ = "external_court_cases"
    __table_args__ = (UniqueConstraint("external_case_uid", name="uq_external_court_case_uid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_job_id: Mapped[int] = mapped_column(ForeignKey("court_case_import_jobs.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    external_case_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    case_number: Mapped[str] = mapped_column(String(255), nullable=False)
    court_name: Mapped[str] = mapped_column(String(255), default="")
    participant_role: Mapped[str] = mapped_column(String(50), default="")
    claim_subject: Mapped[str] = mapped_column(Text, default="")
    case_date: Mapped[date | None] = mapped_column(Date)
    linked_case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    source: Mapped[str] = mapped_column(String(100), default="")
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    import_job: Mapped[CourtCaseImportJob] = relationship(back_populates="imported_cases")
    organization: Mapped[Organization] = relationship(back_populates="external_court_cases")
    events: Mapped[list["CourtCaseEvent"]] = relationship(back_populates="external_court_case", cascade="all, delete-orphan")
    snapshots: Mapped[list["CourtCaseSnapshot"]] = relationship(back_populates="external_court_case", cascade="all, delete-orphan")
    submission_packages: Mapped[list["CourtSubmissionPackage"]] = relationship(back_populates="external_court_case")


class CourtCaseEvent(Base):
    __tablename__ = "court_case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_court_case_id: Mapped[int] = mapped_column(ForeignKey("external_court_cases.id"), nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    external_court_case: Mapped[ExternalCourtCase] = relationship(back_populates="events")


class CourtCaseSnapshot(Base):
    __tablename__ = "court_case_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_court_case_id: Mapped[int] = mapped_column(ForeignKey("external_court_cases.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="")
    snapshot_payload: Mapped[str] = mapped_column(Text, default="")
    snapshot_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    external_court_case: Mapped[ExternalCourtCase] = relationship(back_populates="snapshots")


class CourtSubmissionPackage(Base):
    __tablename__ = "court_submission_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    external_court_case_id: Mapped[int | None] = mapped_column(ForeignKey("external_court_cases.id"))
    status: Mapped[str] = mapped_column(String(100), default=CourtSubmissionStatus.DRAFT.value)
    package_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped["Case"] = relationship(back_populates="court_submission_packages")
    organization: Mapped[Organization] = relationship(back_populates="court_submission_packages")
    external_court_case: Mapped[ExternalCourtCase | None] = relationship(back_populates="submission_packages")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    claimant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    respondent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=CaseStatus.NEW.value, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_lawyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    plaintiff_organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    signatory_id: Mapped[int | None] = mapped_column(ForeignKey("signatories.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    parties: Mapped[list["Party"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    extracted_facts: Mapped[list["ExtractedFact"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    pretension: Mapped["Pretension | None"] = relationship(back_populates="case", uselist=False, cascade="all, delete-orphan")
    claim: Mapped["Claim | None"] = relationship(back_populates="case", uselist=False, cascade="all, delete-orphan")
    checklist: Mapped["Checklist | None"] = relationship(back_populates="case", uselist=False, cascade="all, delete-orphan")
    workflow_events: Mapped[list["WorkflowEvent"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    exports: Mapped[list["ExportPackage"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    postal_dispatches: Mapped[list["PostalDispatch"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    court_submission_packages: Mapped[list["CourtSubmissionPackage"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    plaintiff_organization: Mapped[Organization | None] = relationship(back_populates="cases")
    signatory: Mapped[Signatory | None] = relationship(back_populates="cases")
    pilot_feedback_items: Mapped[list["PilotFeedback"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="parties")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "version", name="uq_document_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    document: Mapped[Document] = relationship(back_populates="versions")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    fact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_fragment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="extracted_facts")


class Pretension(Base):
    __tablename__ = "pretensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="pretension")
    versions: Mapped[list["PretensionVersion"]] = relationship(back_populates="pretension", cascade="all, delete-orphan")


class PretensionVersion(Base):
    __tablename__ = "pretension_versions"
    __table_args__ = (UniqueConstraint("pretension_id", "version", name="uq_pretension_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pretension_id: Mapped[int] = mapped_column(ForeignKey("pretensions.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_approved_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    pretension: Mapped[Pretension] = relationship(back_populates="versions")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="claim")
    versions: Mapped[list["ClaimVersion"]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class ClaimVersion(Base):
    __tablename__ = "claim_versions"
    __table_args__ = (UniqueConstraint("claim_id", "version", name="uq_claim_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_approved_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    claim: Mapped[Claim] = relationship(back_populates="versions")


class RagSource(Base):
    __tablename__ = "rag_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    document_date: Mapped[str] = mapped_column(String(50), default="")
    jurisdiction: Mapped[str] = mapped_column(String(100), default="")
    category: Mapped[str] = mapped_column(String(100), default="")
    fragment: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(255), default="")
    url_or_internal_path: Mapped[str] = mapped_column(String(500), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    citations: Mapped[list["RagCitation"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class RagCitation(Base):
    __tablename__ = "rag_citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("rag_sources.id"), nullable=False)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    source: Mapped[RagSource] = relationship(back_populates="citations")


class Checklist(Base):
    __tablename__ = "checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="checklist")
    items: Mapped[list["ChecklistItem"]] = relationship(back_populates="checklist", cascade="all, delete-orphan")


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    checklist: Mapped[Checklist] = relationship(back_populates="items")


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    from_status: Mapped[str] = mapped_column(String(50), default="")
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="workflow_events")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ExportPackage(Base):
    __tablename__ = "export_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    archive_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case] = relationship(back_populates="exports")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class IntegrationRequestLog(Base):
    __tablename__ = "integration_request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    integration_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), default="")
    mode: Mapped[str] = mapped_column(String(100), default="")
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), default="")
    idempotency_key: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    http_status: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str] = mapped_column(String(100), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    safe_request_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    safe_response_metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class IntegrationApproval(Base):
    __tablename__ = "integration_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    integration_name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(50), default=IntegrationApprovalStatus.REQUESTED.value)
    reason: Mapped[str] = mapped_column(Text, default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PilotFeedback(Base):
    __tablename__ = "pilot_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    actual_behavior: Mapped[str] = mapped_column(Text, default="")
    screenshot_document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(String(50), default=PilotFeedbackStatus.NEW.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    case: Mapped[Case | None] = relationship(back_populates="pilot_feedback_items")
    user: Mapped[User] = relationship(back_populates="pilot_feedback_items")

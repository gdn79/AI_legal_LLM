from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models import RoleName, User
from app.schemas.integration import ProviderConnectionCheck
from app.repositories.audit_repository import AuditRepository
from app.schemas.organization import (
    FnsCompanyLookupLogRead,
    OrganizationCreate,
    OrganizationLookupRequest,
    OrganizationPreview,
    OrganizationRead,
    OrganizationSnapshotRead,
)
from app.services.audit_service import AuditService
from app.services.integration_service import IntegrationService
from app.services.organization_service import OrganizationService
from app.integrations.fns_company_adapter import get_fns_company_adapter

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/test-connection/fns", response_model=ProviderConnectionCheck)
def test_fns_connection(
    current_user: User = Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    adapter = get_fns_company_adapter(settings.fns_provider_mode)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="fns",
        provider=settings.fns_provider,
        mode=settings.fns_provider_mode,
        operation="test_connection",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"real_api_enabled": settings.enable_real_fns},
    )
    result = adapter.test_connection()
    integration.finish_log(
        entry,
        status="SUCCESS" if result["ok"] else "FAILED",
        http_status=200,
        safe_response_metadata=result,
        error_code="" if result["ok"] else "FNS_PROVIDER_UNAVAILABLE",
        error_message="" if result["ok"] else result["detail"],
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "fns_test_connection",
        "integration",
        "fns",
        f"mode={settings.fns_provider_mode}",
        request_id,
    )
    return ProviderConnectionCheck(**result)


@router.post("/lookup-by-inn", response_model=OrganizationPreview)
def lookup_by_inn(
    payload: OrganizationLookupRequest,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="fns",
        provider=settings.fns_provider,
        mode=settings.fns_provider_mode,
        operation="lookup_preview",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"inn": payload.inn},
    )
    try:
        preview = OrganizationService(db).lookup_preview(payload.inn)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={},
            error_code=detail.get("error_code", "FNS_LOOKUP_FAILED"),
            error_message=detail.get("safe_message", "FNS lookup preview failed"),
        )
        raise
    integration.finish_log(
        entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={"source": preview.get("source", ""), "dry_run": preview.get("dry_run", False)},
    )
    return preview


@router.post("", response_model=OrganizationRead)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="fns",
        provider=settings.fns_provider,
        mode=settings.fns_provider_mode,
        operation="lookup_company",
        request_id=request_id,
        created_by_id=current_user.id,
        safe_request_metadata={"inn": payload.inn},
    )
    try:
        organization = OrganizationService(db).create_or_refresh_by_inn(payload.inn)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={},
            error_code=detail.get("error_code", "FNS_LOOKUP_FAILED"),
            error_message=detail.get("safe_message", "FNS organization lookup failed"),
        )
        raise
    integration.finish_log(
        entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={"organization_id": organization.id, "review_status": organization.review_status},
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "organization_created",
        "organization",
        str(organization.id),
        organization.inn,
        request_id,
    )
    return organization


@router.get("", response_model=list[OrganizationRead])
def list_organizations(
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).list_organizations()


@router.get("/{organization_id}", response_model=OrganizationRead)
def get_organization(
    organization_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).get_organization(organization_id)


@router.post("/{organization_id}/refresh-fns", response_model=OrganizationRead)
def refresh_organization(
    organization_id: int,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    settings = get_settings()
    organization_before = OrganizationService(db).get_organization(organization_id)
    integration = IntegrationService(db)
    entry = integration.create_log(
        integration_name="fns",
        provider=settings.fns_provider,
        mode=settings.fns_provider_mode,
        operation="refresh_lookup_company",
        request_id=request_id,
        created_by_id=current_user.id,
        organization_id=organization_id,
        safe_request_metadata={"inn": organization_before.inn},
    )
    try:
        organization = OrganizationService(db).refresh_organization(organization_id)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        integration.finish_log(
            entry,
            status="FAILED",
            http_status=exc.status_code,
            safe_response_metadata={},
            error_code=detail.get("error_code", "FNS_LOOKUP_FAILED"),
            error_message=detail.get("safe_message", "FNS organization refresh failed"),
        )
        raise
    integration.finish_log(
        entry,
        status="SUCCESS",
        http_status=200,
        safe_response_metadata={"organization_id": organization.id, "review_status": organization.review_status},
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "organization_refreshed",
        "organization",
        str(organization.id),
        organization.inn,
        request_id,
    )
    return organization


@router.get("/{organization_id}/snapshots", response_model=list[OrganizationSnapshotRead])
def list_snapshots(
    organization_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).list_snapshots(organization_id)


@router.get("/{organization_id}/lookup-logs", response_model=list[FnsCompanyLookupLogRead])
def list_lookup_logs(
    organization_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).list_lookup_logs(organization_id)

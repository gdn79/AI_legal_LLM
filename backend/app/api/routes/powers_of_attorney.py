from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.power_of_attorney import PowerOfAttorneyHistoryRead, PowerOfAttorneyRead
from app.services.audit_service import AuditService
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["powers-of-attorney"])


def to_power_read(item) -> PowerOfAttorneyRead:
    return PowerOfAttorneyRead(
        id=item.id,
        organization_id=item.organization_id,
        employee_id=item.employee_id,
        user_id=item.user_id,
        number=item.number,
        issued_at=item.issued_at,
        expires_at=item.expires_at,
        file_path=item.file_path,
        status=item.status,
        authority_scope=OrganizationService.scope_to_list(item.authority_scope),
        revoked_at=item.revoked_at,
        created_at=item.created_at,
    )


@router.post("/employees/{employee_id}/powers-of-attorney", response_model=PowerOfAttorneyRead)
async def create_power_of_attorney(
    employee_id: int,
    number: str = Form(...),
    issued_at: date = Form(...),
    expires_at: date = Form(...),
    authority_scope: str = Form(...),
    user_id: int | None = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    power = OrganizationService(db).create_power_of_attorney(
        employee_id=employee_id,
        user_id=user_id,
        number=number,
        issued_at=issued_at,
        expires_at=expires_at,
        authority_scope=[item.strip() for item in authority_scope.split(",") if item.strip()],
        file_name=file.filename or "power_of_attorney.pdf",
        file_bytes=await file.read(),
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "power_of_attorney_created",
        "power_of_attorney",
        str(power.id),
        power.number,
        request_id,
    )
    return to_power_read(power)


@router.get("/employees/{employee_id}/powers-of-attorney", response_model=list[PowerOfAttorneyRead])
def list_powers_for_employee(
    employee_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return [to_power_read(item) for item in OrganizationService(db).list_powers_for_employee(employee_id)]


@router.get("/powers-of-attorney/{power_id}", response_model=PowerOfAttorneyRead)
def get_power_of_attorney(
    power_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return to_power_read(OrganizationService(db).get_power_of_attorney(power_id))


@router.post("/powers-of-attorney/{power_id}/revoke", response_model=PowerOfAttorneyRead)
def revoke_power_of_attorney(
    power_id: int,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    power = OrganizationService(db).revoke_power_of_attorney(power_id)
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "power_of_attorney_revoked",
        "power_of_attorney",
        str(power.id),
        power.number,
        request_id,
    )
    return to_power_read(power)


@router.get("/powers-of-attorney/{power_id}/history", response_model=list[PowerOfAttorneyHistoryRead])
def power_history(
    power_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).power_of_attorney_history(power_id)

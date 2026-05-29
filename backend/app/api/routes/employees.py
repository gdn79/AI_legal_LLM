from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName, User
from app.repositories.audit_repository import AuditRepository
from app.schemas.employee import EmployeeCreate, EmployeeHistoryRead, EmployeeRead
from app.services.audit_service import AuditService
from app.services.organization_service import OrganizationService

router = APIRouter(tags=["employees"])


@router.post("/organizations/{organization_id}/employees", response_model=EmployeeRead)
def create_employee(
    organization_id: int,
    payload: EmployeeCreate,
    current_user: User = Depends(require_role(RoleName.admin, RoleName.lawyer)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    employee = OrganizationService(db).create_employee(
        organization_id=organization_id,
        full_name=payload.full_name,
        position=payload.position,
        email=payload.email,
        user_id=payload.user_id,
    )
    AuditService(AuditRepository(db)).log(
        current_user.id,
        "employee_created",
        "employee",
        str(employee.id),
        employee.full_name,
        request_id,
    )
    return employee


@router.get("/organizations/{organization_id}/employees", response_model=list[EmployeeRead])
def list_employees(
    organization_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).list_employees(organization_id)


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).get_employee(employee_id)


@router.get("/employees/{employee_id}/history", response_model=list[EmployeeHistoryRead])
def employee_history(
    employee_id: int,
    _: User = Depends(require_role(RoleName.admin, RoleName.lawyer, RoleName.manager)),
    db: Session = Depends(get_db),
):
    return OrganizationService(db).employee_history(employee_id)

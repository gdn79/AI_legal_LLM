from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_request_id, require_role
from app.db.session import get_db
from app.models import RoleName
from app.repositories.audit_repository import AuditRepository
from app.schemas.settings import SettingRead, SettingUpdate
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingRead])
def list_settings(db: Session = Depends(get_db), _=Depends(require_role(RoleName.admin))):
    return SettingsService(db).list_settings_safe()


@router.put("/{key}", response_model=SettingRead)
def upsert_setting(
    key: str,
    payload: SettingUpdate,
    current_user=Depends(require_role(RoleName.admin)),
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
):
    setting = SettingsService(db).upsert(key=key, value=payload.value, description=payload.description)
    audit_details = SettingsService.build_audit_details(key=key, value=payload.value)
    AuditService(AuditRepository(db)).log(current_user.id, "setting_updated", "system_setting", key, audit_details, request_id)
    return {
        "key": setting.key,
        "value": SettingsService.mask_value(setting.key, setting.value),
        "description": setting.description,
    }

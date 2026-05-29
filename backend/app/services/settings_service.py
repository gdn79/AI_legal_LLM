from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models import SystemSetting


SENSITIVE_KEY_MARKERS = {"TOKEN", "SECRET", "PASSWORD", "API_KEY", "KEY"}
SENSITIVE_KEYS = {
    "LLM_API_KEY",
    "RUSSIAN_POST_APP_TOKEN",
    "RUSSIAN_POST_USER_KEY",
    "FNS_SANDBOX_TOKEN",
    "FNS_SANDBOX_CLIENT_ID",
    "FNS_SANDBOX_CLIENT_SECRET",
    "RUSSIAN_POST_SANDBOX_APP_TOKEN",
    "RUSSIAN_POST_SANDBOX_USER_KEY",
    "RUSSIAN_POST_SANDBOX_CLIENT_SECRET",
    "COURT_SANDBOX_TOKEN",
    "COURT_PROVIDER_SANDBOX_API_KEY",
    "COURT_SANDBOX_CLIENT_SECRET",
    "COURT_ARBITR_TOKEN",
    "JWT_SECRET",
}


class SettingsService:
    def __init__(self, db: Session):
        self.db = db

    def list_settings(self) -> list[SystemSetting]:
        return self.db.query(SystemSetting).order_by(SystemSetting.key.asc()).all()

    def list_settings_safe(self) -> list[dict[str, str]]:
        return [
            {
                "key": item.key,
                "value": self.mask_value(item.key, item.value),
                "description": item.description,
            }
            for item in self.list_settings()
        ]

    def upsert(self, *, key: str, value: str, description: str) -> SystemSetting:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == key).one_or_none()
        if setting is None:
            setting = SystemSetting(key=key, value=value, description=description)
        else:
            setting.value = value
            setting.description = description
            setting.updated_at = utc_now()
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    @classmethod
    def mask_value(cls, key: str, value: str) -> str:
        if not cls.is_sensitive_key(key):
            return value
        if not value:
            return ""
        return "[REDACTED]"

    @staticmethod
    def is_sensitive_key(key: str) -> bool:
        normalized = key.upper()
        if normalized in SENSITIVE_KEYS:
            return True
        return any(marker in normalized for marker in SENSITIVE_KEY_MARKERS)

    @classmethod
    def build_audit_details(cls, *, key: str, value: str) -> str:
        if cls.is_sensitive_key(key):
            return f"{key}: sensitive value updated [REDACTED]"
        preview = value.strip().replace("\r", " ").replace("\n", " ")
        if len(preview) > 80:
            preview = f"{preview[:77]}..."
        return f"{key}: value updated to '{preview}'"

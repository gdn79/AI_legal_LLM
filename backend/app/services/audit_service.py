from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    def log(self, actor_user_id: int | None, action: str, entity_type: str, entity_id: str, details: str, request_id: str):
        return self.repository.create(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            request_id=request_id,
        )

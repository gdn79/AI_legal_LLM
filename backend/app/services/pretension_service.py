from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models import CaseStatus, Pretension, PretensionVersion
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.llm_service import LLMService


class PretensionService:
    def __init__(self, db: Session, llm_service: LLMService | None = None):
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.audit = AuditService(AuditRepository(db))

    def get(self, case_id: int) -> Pretension:
        pretension = self.db.query(Pretension).filter(Pretension.case_id == case_id).one()
        return pretension

    def update(self, pretension: Pretension, content: str) -> Pretension:
        if pretension.approved:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved pretension cannot be modified")
        pretension.content = content
        pretension.updated_at = utc_now()
        next_version = len(pretension.versions) + 1
        self.db.add(PretensionVersion(pretension_id=pretension.id, version=next_version, content=content, is_approved_snapshot=pretension.approved))
        pretension.case.status = CaseStatus.PRETENSION_REVIEW.value
        self.db.add(pretension)
        self.db.commit()
        self.db.refresh(pretension)
        return pretension

    def generate(
        self,
        pretension: Pretension,
        case_title: str,
        facts: list[str],
        citations: list[str],
        *,
        actor_user_id: int | None = None,
        request_id: str = "system",
    ) -> Pretension:
        result = self.llm_service.complete_json(
            "generate_pretension",
            {"case_title": case_title, "facts": facts, "citations": citations},
        )
        self.audit.log(
            actor_user_id,
            "llm_prompt_executed",
            "llm_request",
            f"pretension:{pretension.id}",
            "generate_pretension",
            request_id,
        )
        content = str(result.get("content", ""))
        pretension.content = content
        pretension.updated_at = utc_now()
        pretension.case.status = CaseStatus.PRETENSION_DRAFT_READY.value
        next_version = len(pretension.versions) + 1
        self.db.add(PretensionVersion(pretension_id=pretension.id, version=next_version, content=content, is_approved_snapshot=False))
        self.db.add(pretension)
        self.db.commit()
        self.db.refresh(pretension)
        return pretension

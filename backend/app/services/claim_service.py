from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models import CaseStatus, Claim, ClaimVersion
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.llm_service import LLMService


class ClaimService:
    def __init__(self, db: Session, llm_service: LLMService | None = None):
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.audit = AuditService(AuditRepository(db))

    def get(self, case_id: int) -> Claim:
        return self.db.query(Claim).filter(Claim.case_id == case_id).one()

    def update(self, claim: Claim, content: str) -> Claim:
        if claim.approved:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approved claim cannot be modified")
        claim.content = content
        claim.updated_at = utc_now()
        claim.case.status = CaseStatus.LAWYER_REVIEW.value
        next_version = len(claim.versions) + 1
        self.db.add(ClaimVersion(claim_id=claim.id, version=next_version, content=content, is_approved_snapshot=claim.approved))
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def generate(
        self,
        claim: Claim,
        case_title: str,
        facts: list[str],
        citations: list[str],
        *,
        actor_user_id: int | None = None,
        request_id: str = "system",
    ) -> Claim:
        result = self.llm_service.complete_json(
            "generate_claim",
            {"case_title": case_title, "facts": facts, "citations": citations},
        )
        self.audit.log(
            actor_user_id,
            "llm_prompt_executed",
            "llm_request",
            f"claim:{claim.id}",
            "generate_claim",
            request_id,
        )
        content = str(result.get("content", ""))
        claim.content = content
        claim.updated_at = utc_now()
        claim.case.status = CaseStatus.CLAIM_DRAFT_READY.value
        next_version = len(claim.versions) + 1
        self.db.add(ClaimVersion(claim_id=claim.id, version=next_version, content=content, is_approved_snapshot=False))
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

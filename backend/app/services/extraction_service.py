from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Case, CaseStatus, Document, ExtractedFact
from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.services.llm_service import LLMService


class ExtractionService:
    def __init__(self, db: Session, llm_service: LLMService | None = None):
        self.db = db
        self.llm_service = llm_service or LLMService()
        self.audit = AuditService(AuditRepository(db))

    def run_for_case(
        self,
        case: Case,
        *,
        actor_user_id: int | None = None,
        request_id: str = "system",
    ) -> tuple[list[ExtractedFact], list[str]]:
        self.db.query(ExtractedFact).filter(ExtractedFact.case_id == case.id).delete()
        warnings: list[str] = []
        facts: list[ExtractedFact] = []
        case.status = CaseStatus.EXTRACTION_IN_PROGRESS.value
        self.db.add(case)
        self.db.flush()

        documents = self.db.query(Document).filter(Document.case_id == case.id).all()
        for document in documents:
            prompt_name = self._resolve_prompt_name(document.filename)
            llm_payload = self.llm_service.complete_json(
                prompt_name,
                {"filename": document.filename, "text": document.extracted_text or ""},
            )
            self.audit.log(
                actor_user_id,
                "llm_prompt_executed",
                "llm_request",
                f"extract:{document.id}",
                prompt_name,
                request_id,
            )
            for warning in llm_payload.get("warnings", []):
                warnings.append(str(warning))
            for item in llm_payload.get("facts", []):
                fact = ExtractedFact(
                    case_id=case.id,
                    document_id=document.id,
                    fact_type=str(item.get("type", "detected_fact")),
                    value=str(item.get("value", "")),
                    confidence=float(item.get("confidence", 0.0)),
                    source_fragment=str(item.get("source_fragment", ""))[:200],
                )
                self.db.add(fact)
                facts.append(fact)

        case.status = CaseStatus.FACTS_EXTRACTED.value if facts else CaseStatus.ERROR_MANUAL_REVIEW.value
        self.db.add(case)
        self.db.commit()
        for fact in facts:
            self.db.refresh(fact)
        return facts, warnings

    def _resolve_prompt_name(self, filename: str) -> str:
        lower = filename.lower()
        if "act" in lower or "акт" in lower:
            return "extract_act_facts"
        if "invoice" in lower or "счет" in lower or "счёт" in lower:
            return "extract_invoice_facts"
        return "extract_contract_facts"

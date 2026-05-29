from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    version: str
    input_schema: dict
    output_schema: dict
    template: str
    created_at: str


class PromptRegistry:
    def __init__(self) -> None:
        created_at = datetime(2026, 5, 29, tzinfo=UTC).isoformat()
        self._prompts = {
            "extract_contract_facts": PromptDefinition(
                name="extract_contract_facts",
                version="1.1.0",
                input_schema={"filename": "str", "text": "str"},
                output_schema={"facts": "list[object]", "warnings": "list[str]"},
                template=(
                    "Извлеки факты из договора. Верни JSON c keys facts и warnings. "
                    "Каждый факт должен иметь type, value, confidence, source_document, source_fragment."
                ),
                created_at=created_at,
            ),
            "extract_act_facts": PromptDefinition(
                name="extract_act_facts",
                version="1.1.0",
                input_schema={"filename": "str", "text": "str"},
                output_schema={"facts": "list[object]", "warnings": "list[str]"},
                template=(
                    "Извлеки факты из акта или УПД. Верни JSON c keys facts и warnings. "
                    "Каждый факт должен иметь type, value, confidence, source_document, source_fragment."
                ),
                created_at=created_at,
            ),
            "extract_invoice_facts": PromptDefinition(
                name="extract_invoice_facts",
                version="1.1.0",
                input_schema={"filename": "str", "text": "str"},
                output_schema={"facts": "list[object]", "warnings": "list[str]"},
                template=(
                    "Извлеки факты из счета. Верни JSON c keys facts и warnings. "
                    "Каждый факт должен иметь type, value, confidence, source_document, source_fragment."
                ),
                created_at=created_at,
            ),
            "summarize_case": PromptDefinition(
                name="summarize_case",
                version="1.0.0",
                input_schema={"case_title": "str", "facts": "list[str]"},
                output_schema={"summary": "str", "warnings": "list[str]"},
                template="Подготовь краткое резюме дела без юридического утверждения. Верни JSON c summary и warnings.",
                created_at=created_at,
            ),
            "generate_rag_queries": PromptDefinition(
                name="generate_rag_queries",
                version="1.0.0",
                input_schema={"case_title": "str", "facts": "list[str]"},
                output_schema={"queries": "list[str]", "warnings": "list[str]"},
                template="Сгенерируй поисковые запросы для RAG. Верни JSON c queries и warnings.",
                created_at=created_at,
            ),
            "generate_pretension": PromptDefinition(
                name="generate_pretension",
                version="1.1.0",
                input_schema={"case_title": "str", "facts": "list[str]", "citations": "list[str]"},
                output_schema={"content": "str", "warnings": "list[str]", "citations": "list[str]"},
                template=(
                    "Подготовь черновик претензии. Не утверждай документ. "
                    "Верни JSON c content, warnings, citations. Если источников нет, включи warning "
                    "'требуется проверка юриста'."
                ),
                created_at=created_at,
            ),
            "review_pretension": PromptDefinition(
                name="review_pretension",
                version="1.0.0",
                input_schema={"content": "str", "citations": "list[str]"},
                output_schema={"risks": "list[str]", "warnings": "list[str]"},
                template="Проверь черновик претензии и верни JSON c risks и warnings без юридического утверждения.",
                created_at=created_at,
            ),
            "generate_claim": PromptDefinition(
                name="generate_claim",
                version="1.1.0",
                input_schema={"case_title": "str", "facts": "list[str]", "citations": "list[str]"},
                output_schema={"content": "str", "warnings": "list[str]", "citations": "list[str]"},
                template=(
                    "Подготовь черновик искового заявления. Не утверждай документ. "
                    "Верни JSON c content, warnings, citations. Если источников нет, включи warning "
                    "'требуется проверка юриста'."
                ),
                created_at=created_at,
            ),
            "detect_claim_risks": PromptDefinition(
                name="detect_claim_risks",
                version="1.0.0",
                input_schema={"case_title": "str", "claim_content": "str", "citations": "list[str]"},
                output_schema={"risks": "list[object]", "warnings": "list[str]"},
                template="Определи риски по иску. Верни JSON c risks и warnings.",
                created_at=created_at,
            ),
            "generate_appendix_list": PromptDefinition(
                name="generate_appendix_list",
                version="1.0.0",
                input_schema={"documents": "list[str]", "has_power_of_attorney": "bool"},
                output_schema={"appendices": "list[str]", "warnings": "list[str]"},
                template="Сформируй список приложений к иску. Верни JSON c appendices и warnings.",
                created_at=created_at,
            ),
            "answer_lawyer_comment": PromptDefinition(
                name="answer_lawyer_comment",
                version="1.0.0",
                input_schema={"comment": "str", "context": "str"},
                output_schema={"answer": "str", "warnings": "list[str]"},
                template="Подготовь ответ на комментарий юриста. Верни JSON c answer и warnings.",
                created_at=created_at,
            ),
            "check_signatory_authority_context": PromptDefinition(
                name="check_signatory_authority_context",
                version="1.0.0",
                input_schema={"organization": "object", "signatory": "object", "power_of_attorney": "object|null"},
                output_schema={"summary": "str", "warnings": "list[str]"},
                template="Подготовь справку по контексту полномочий подписанта. Верни JSON c summary и warnings.",
                created_at=created_at,
            ),
            "generate_rag_report": PromptDefinition(
                name="generate_rag_report",
                version="1.0.0",
                input_schema={"sources": "list[object]", "citations": "list[object]"},
                output_schema={"report": "str", "warnings": "list[str]"},
                template="Сформируй краткий RAG report. Верни JSON c report и warnings.",
                created_at=created_at,
            ),
            "generate_export_summary": PromptDefinition(
                name="generate_export_summary",
                version="1.0.0",
                input_schema={"case_title": "str", "status": "str", "sections": "list[str]"},
                output_schema={"summary": "str", "warnings": "list[str]"},
                template="Сформируй summary экспортного комплекта. Верни JSON c summary и warnings.",
                created_at=created_at,
            ),
        }

    def get(self, name: str) -> PromptDefinition:
        return self._prompts[name]

    def list(self) -> list[PromptDefinition]:
        return list(self._prompts.values())

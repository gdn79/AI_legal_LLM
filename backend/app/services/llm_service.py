from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.prompts import PromptRegistry

MANUAL_REVIEW_WARNING = "требуется проверка юриста"


class LLMService:
    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport
        self.registry = PromptRegistry()

    def complete_json(self, prompt_name: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        prompt = self.registry.get(prompt_name)
        if self.settings.llm_model.startswith("stub-"):
            return self._mock_response(prompt_name, input_payload)

        response_text = self._chat_completion(
            system_message=prompt.template,
            user_payload=input_payload,
        )
        try:
            return self._extract_json(response_text)
        except ValueError:
            return self._mock_response(prompt_name, input_payload)

    def _chat_completion(self, *, system_message: str, user_payload: dict[str, Any]) -> str:
        with httpx.Client(
            base_url=self.settings.llm_base_url,
            timeout=30.0,
            transport=self.transport,
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
        ) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": self.settings.llm_model,
                    "temperature": self.settings.llm_temperature,
                    "max_tokens": self.settings.llm_max_tokens,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
        return payload["choices"][0]["message"]["content"]

    def _extract_json(self, text: str) -> dict[str, Any]:
        fenced_match = re.search(r"```json\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced_match:
            return json.loads(fenced_match.group(1))
        object_match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if object_match:
            return json.loads(object_match.group(1))
        raise ValueError("JSON payload not found in LLM response")

    def _mock_response(self, prompt_name: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        if prompt_name.startswith("extract_"):
            return self._mock_fact_extraction(input_payload)
        if prompt_name == "summarize_case":
            return self._summary_payload(input_payload)
        if prompt_name == "generate_rag_queries":
            return self._rag_queries_payload(input_payload)
        if prompt_name == "generate_pretension":
            return self._draft_payload("претензии", input_payload)
        if prompt_name == "review_pretension":
            return self._pretension_review_payload(input_payload)
        if prompt_name == "generate_claim":
            return self._draft_payload("искового заявления", input_payload)
        if prompt_name == "detect_claim_risks":
            return self._claim_risks_payload(input_payload)
        if prompt_name == "generate_appendix_list":
            return self._appendix_payload(input_payload)
        if prompt_name == "answer_lawyer_comment":
            return {"answer": f"Требуется юридическая проверка: {input_payload.get('comment', '')}".strip(), "warnings": []}
        if prompt_name == "check_signatory_authority_context":
            return self._authority_context_payload(input_payload)
        if prompt_name == "generate_rag_report":
            return self._rag_report_payload(input_payload)
        if prompt_name == "generate_export_summary":
            return self._export_summary_payload(input_payload)
        return {"warnings": [MANUAL_REVIEW_WARNING]}

    def _mock_fact_extraction(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        text = str(input_payload.get("text", ""))
        filename = str(input_payload.get("filename", "document"))
        warnings: list[str] = []
        facts: list[dict[str, Any]] = []

        patterns = {
            "contract_number": r"(?:договор|contract)\s*(?:№|no\.?)\s*([A-Za-zА-Яа-я0-9/-]+)",
            "invoice_number": r"(?:счет|invoice)\s*(?:№|no\.?)\s*([A-Za-zА-Яа-я0-9/-]+)",
            "claim_amount": r"(\d[\d\s]{1,20}(?:[.,]\d{2})?)\s*(?:руб|₽|RUB)",
        }
        for fact_type, pattern in patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            facts.append(
                {
                    "type": fact_type,
                    "value": match.group(1).strip(),
                    "confidence": 0.83,
                    "source_document": filename,
                    "source_fragment": text[:200],
                }
            )

        if not facts:
            warnings.append(f"В документе {filename} не найдено достаточно фактов")
        return {"facts": facts, "warnings": warnings}

    def _summary_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        facts = input_payload.get("facts", []) or []
        summary = f"Дело: {input_payload.get('case_title', '')}. Фактов: {len(facts)}."
        return {"summary": summary.strip(), "warnings": [] if facts else [MANUAL_REVIEW_WARNING]}

    def _rag_queries_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        title = str(input_payload.get("case_title", "")).strip()
        facts = [str(item) for item in (input_payload.get("facts", []) or [])]
        queries = [title] if title else []
        queries.extend(facts[:3])
        if not queries:
            queries = ["досудебный порядок взыскания задолженности"]
        return {"queries": queries, "warnings": []}

    def _draft_payload(self, document_kind: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        facts = [str(item) for item in (input_payload.get("facts", []) or [])]
        citations = [str(item) for item in (input_payload.get("citations", []) or [])]
        warnings = self._manual_review_warnings(input_payload, citations=citations)
        citations_block = "\n".join(f"- {item}" for item in citations) or f"- источник не найден, {MANUAL_REVIEW_WARNING}"
        facts_block = "\n".join(f"- {item}" for item in facts) or f"- {MANUAL_REVIEW_WARNING}"
        content = (
            f"Проект {document_kind} по делу: {input_payload.get('case_title', '')}\n\n"
            "Внимание: это черновик. Юридически значимое решение принимает юрист.\n\n"
            f"Факты:\n{facts_block}\n\n"
            f"Источники:\n{citations_block}\n"
        )
        return {"content": content, "warnings": warnings, "citations": citations}

    def _pretension_review_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        citations = [str(item) for item in (input_payload.get("citations", []) or [])]
        risks = [] if citations else ["Отсутствуют подтвержденные правовые источники."]
        warnings = [] if citations else [MANUAL_REVIEW_WARNING]
        return {"risks": risks, "warnings": warnings}

    def _claim_risks_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        citations = [str(item) for item in (input_payload.get("citations", []) or [])]
        risks = []
        if not citations:
            risks.append(
                {
                    "level": "critical",
                    "title": "Отсутствуют citations",
                    "description": "Для проекта иска не найдены подтвержденные правовые источники.",
                    "recommended_action": "Добавить RAG-источники и проверить проект юристом.",
                }
            )
        return {"risks": risks, "warnings": [] if citations else [MANUAL_REVIEW_WARNING]}

    def _appendix_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        documents = [str(item) for item in (input_payload.get("documents", []) or [])]
        appendices = documents[:]
        if bool(input_payload.get("has_power_of_attorney")):
            appendices.append("доверенность")
        if not appendices:
            appendices.append("список приложений требует ручной проверки")
        return {"appendices": appendices, "warnings": []}

    def _authority_context_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        organization = input_payload.get("organization") or {}
        signatory = input_payload.get("signatory") or {}
        power = input_payload.get("power_of_attorney")
        warnings: list[str] = []
        if not organization:
            warnings.append("организация не указана")
        if not signatory:
            warnings.append("подписант не указан")
        if signatory and signatory.get("signatory_type") == "AUTHORIZED_EMPLOYEE" and not power:
            warnings.append("доверенность не указана")
        return {
            "summary": (
                f"Организация: {organization.get('short_name') or organization.get('inn') or 'не указана'}. "
                f"Подписант: {signatory.get('full_name') or 'не указан'}."
            ),
            "warnings": warnings or ([] if power or signatory.get("signatory_type") == "DIRECTOR" else [MANUAL_REVIEW_WARNING]),
        }

    def _rag_report_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        sources = input_payload.get("sources", []) or []
        citations = input_payload.get("citations", []) or []
        warnings = [] if citations else [MANUAL_REVIEW_WARNING]
        report = f"RAG report: sources={len(sources)}, citations={len(citations)}."
        return {"report": report, "warnings": warnings}

    def _export_summary_payload(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        sections = input_payload.get("sections", []) or []
        summary = (
            f"Экспорт по делу {input_payload.get('case_title', '')}: статус {input_payload.get('status', '')}. "
            f"Разделов: {len(sections)}."
        )
        return {"summary": summary, "warnings": []}

    def _manual_review_warnings(self, input_payload: dict[str, Any], *, citations: list[str]) -> list[str]:
        warnings: list[str] = []
        if not citations:
            warnings.append(MANUAL_REVIEW_WARNING)
        organization = input_payload.get("organization")
        if organization is None:
            warnings.append("организация не указана, требуется ручная проверка")
        signatory = input_payload.get("signatory")
        if signatory is None:
            warnings.append("подписант не указан, требуется ручная проверка")
        if input_payload.get("requires_power_of_attorney") and not input_payload.get("power_of_attorney"):
            warnings.append("доверенность отсутствует, требуется ручная проверка")
        return list(dict.fromkeys(warnings))

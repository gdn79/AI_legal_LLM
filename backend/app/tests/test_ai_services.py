from io import BytesIO
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import Settings
from app.models import AuditLog, RagCitation
from app.prompts import PromptRegistry
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.qdrant_service import QdrantService
from app.services.rag_service import RagService


def login(client, email: str):
    response = client.post("/api/auth/login", json={"email": email, "password": "ChangeMe123!"})
    assert response.status_code == 200
    return response.json()["access_token"]


def create_case(client, token: str, assigned_lawyer_id: int | None = None):
    payload = {
        "title": "Debt recovery semantic dispute",
        "description": "Contract dispute",
        "claimant_name": "OOO Alpha",
        "respondent_name": "OOO Beta",
        "claim_amount": 100000.0,
        "assigned_lawyer_id": assigned_lawyer_id,
    }
    response = client.post("/api/cases", headers={"Authorization": f"Bearer {token}"}, json=payload)
    assert response.status_code == 200
    return response.json()["id"]


def _build_rag_service(db_session):
    settings = Settings(
        qdrant_url="http://localhost:6333",
        rag_chunk_size=120,
        rag_chunk_overlap=20,
        embedding_model="stub-embedding",
        llm_model="stub-openai-compatible",
    )
    return RagService(
        db_session,
        settings=settings,
        embedding_service=EmbeddingService(settings=settings),
        qdrant_service=QdrantService(settings=settings),
    )


def _ingest_local_corpus(rag_service: RagService, corpus_dir: Path) -> None:
    for file_path in sorted(corpus_dir.glob("*.txt")):
        rag_service.ingest(
            title=file_path.stem.replace("_", " ").title(),
            source_type="law",
            category="claim",
            fragment=file_path.read_text(encoding="utf-8"),
            jurisdiction="RU",
            document_date="2026-05-29",
            section="demo",
            url_or_internal_path=str(file_path),
            case_id=None,
            page=1,
        )


def test_prompt_registry_contains_full_prepilot_prompt_set():
    registry = PromptRegistry()
    names = {prompt.name for prompt in registry.list()}
    assert {
        "extract_contract_facts",
        "extract_act_facts",
        "extract_invoice_facts",
        "summarize_case",
        "generate_rag_queries",
        "generate_pretension",
        "review_pretension",
        "generate_claim",
        "detect_claim_risks",
        "generate_appendix_list",
        "answer_lawyer_comment",
        "check_signatory_authority_context",
        "generate_rag_report",
        "generate_export_summary",
    } <= names
    assert all(registry.get(name).version for name in names)


def test_llm_service_parses_json_from_openai_compatible_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"content":"Draft","warnings":["требуется проверка юриста"],"citations":[]}\n```'
                        }
                    }
                ]
            },
        )

    settings = Settings(llm_model="real-model", llm_base_url="http://mock-llm")
    service = LLMService(settings=settings, transport=httpx.MockTransport(handler))
    payload = service.complete_json("generate_claim", {"case_title": "Case", "facts": [], "citations": []})
    assert payload["content"] == "Draft"
    assert payload["warnings"] == ["требуется проверка юриста"]


def test_rag_service_chunks_and_searches_semantically_with_local_corpus(db_session):
    rag_service = _build_rag_service(db_session)
    corpus_dir = Path(__file__).parent / "fixtures" / "rag"
    _ingest_local_corpus(rag_service, corpus_dir)

    queries = [
        "досудебный порядок взыскания задолженности",
        "какие приложения нужны к иску",
        "как оформить расчет требований",
        "правовое обоснование взыскания задолженности",
        "основания для претензии по договору",
    ]
    for query in queries:
        results = rag_service.search(query=query, case_id=None, source_type="law", category="claim", top_k=3)
        assert results
        assert 1 <= len(results) <= 3
        top = results[0]
        assert top.id is not None
        assert top.title
        assert top.fragment
        assert top.source_type == "law"
        assert top.category == "claim"


def test_extraction_logs_llm_requests_and_claim_creates_citations(client, db_session):
    admin_token = login(client, "admin@example.com")
    initiator_token = login(client, "initiator@example.com")
    lawyer_token = login(client, "lawyer@example.com")
    case_id = create_case(client, initiator_token, assigned_lawyer_id=2)

    source = client.post(
        "/api/rag/sources",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Debt recovery obligations",
            "source_type": "law",
            "category": "debt",
            "fragment": "Debt recovery allows a creditor to recover debt after a contract breach.",
            "jurisdiction": "RU",
        },
    )
    assert source.status_code == 200

    upload = client.post(
        f"/api/documents/{case_id}",
        headers={"Authorization": f"Bearer {initiator_token}"},
        files={"file": ("contract.txt", BytesIO("Contract No 123/24 amount 100000 RUB".encode("utf-8")), "text/plain")},
    )
    assert upload.status_code == 200

    extraction = client.post(f"/api/extraction/{case_id}/run", headers={"Authorization": f"Bearer {initiator_token}"})
    assert extraction.status_code == 200
    llm_audit = db_session.scalars(select(AuditLog).where(AuditLog.entity_type == "llm_request")).all()
    assert any(item.action == "llm_prompt_executed" for item in llm_audit)

    claim = client.post(f"/api/claims/{case_id}/generate", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert claim.status_code == 200
    assert "Внимание" in claim.json()["content"]

    citations = client.get(f"/api/rag/citations/{case_id}", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert citations.status_code == 200
    assert citations.json()
    persisted = db_session.scalars(select(RagCitation).where(RagCitation.case_id == case_id)).all()
    assert persisted


def test_claim_generation_warns_when_no_source_found(client):
    initiator_token = login(client, "initiator@example.com")
    lawyer_token = login(client, "lawyer@example.com")
    case_id = create_case(client, initiator_token, assigned_lawyer_id=2)
    upload = client.post(
        f"/api/documents/{case_id}",
        headers={"Authorization": f"Bearer {initiator_token}"},
        files={"file": ("contract.txt", BytesIO(b"Contract No 555/24"), "text/plain")},
    )
    assert upload.status_code == 200
    extraction = client.post(f"/api/extraction/{case_id}/run", headers={"Authorization": f"Bearer {initiator_token}"})
    assert extraction.status_code == 200

    claim = client.post(f"/api/claims/{case_id}/generate", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert claim.status_code == 200
    assert "требуется проверка юриста" in claim.json()["content"]


def test_mock_llm_does_not_invent_organization_signatory_or_poa():
    service = LLMService(settings=Settings(llm_model="stub-openai-compatible"))
    result = service.complete_json(
        "generate_claim",
        {
            "case_title": "No authority context",
            "facts": ["debt is claimed"],
            "citations": ["source-1"],
            "organization": None,
            "signatory": None,
            "requires_power_of_attorney": True,
            "power_of_attorney": None,
        },
    )
    warnings = " ".join(result["warnings"])
    assert "организация не указана" in warnings
    assert "подписант не указан" in warnings
    assert "доверенность отсутствует" in warnings


def test_mock_llm_authority_context_requires_manual_review_when_poa_missing():
    service = LLMService(settings=Settings(llm_model="stub-openai-compatible"))
    result = service.complete_json(
        "check_signatory_authority_context",
        {
            "organization": {"short_name": "ООО Альфа"},
            "signatory": {"full_name": "Петров П.П.", "signatory_type": "AUTHORIZED_EMPLOYEE"},
            "power_of_attorney": None,
        },
    )
    assert "доверенность не указана" in result["warnings"]


def test_generate_rag_report_and_export_summary_return_structured_json():
    service = LLMService(settings=Settings(llm_model="stub-openai-compatible"))
    rag_report = service.complete_json("generate_rag_report", {"sources": [{"id": 1}], "citations": [{"id": 1}]})
    export_summary = service.complete_json(
        "generate_export_summary",
        {"case_title": "Demo case", "status": "COURT_PACKAGE_READY", "sections": ["01", "02"]},
    )
    assert "report" in rag_report
    assert rag_report["warnings"] == []
    assert "summary" in export_summary

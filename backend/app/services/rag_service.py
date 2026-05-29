from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import RagCitation, RagSource
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService


class RagService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        embedding_service: EmbeddingService | None = None,
        qdrant_service: QdrantService | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.embedding_service = embedding_service or EmbeddingService(self.settings)
        self.qdrant_service = qdrant_service or QdrantService(self.settings)

    def ingest(self, **kwargs) -> RagSource:
        source = RagSource(**kwargs)
        score_seed = len(source.fragment or "") / 100
        source.score = round(min(score_seed, 0.99), 2)
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)

        chunks = self._chunk_text(source.fragment or "")
        if chunks:
            vectors = self.embedding_service.embed_texts(chunks)
            self.qdrant_service.ensure_collection(len(vectors[0]))
            points = []
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False), start=1):
                points.append(
                    {
                        "id": int(f"{source.id}{index:03d}"),
                        "vector": vector,
                        "payload": {
                            "source_id": source.id,
                            "fragment": chunk,
                            "title": source.title,
                            "source_type": source.source_type,
                            "category": source.category,
                            "case_id": source.case_id,
                            "document_date": source.document_date,
                            "jurisdiction": source.jurisdiction,
                            "section": source.section,
                            "url_or_internal_path": source.url_or_internal_path,
                            "page": source.page,
                        },
                    }
                )
            self.qdrant_service.upsert(points)
        return source

    def search(self, *, query: str, case_id: int | None, source_type: str | None, category: str | None, top_k: int) -> list[RagSource]:
        semantic_results = self._semantic_search(query=query, case_id=case_id, source_type=source_type, category=category, top_k=top_k)
        if semantic_results:
            return semantic_results

        statement = self.db.query(RagSource)
        if case_id is not None:
            statement = statement.filter((RagSource.case_id == case_id) | (RagSource.case_id.is_(None)))
        if source_type:
            statement = statement.filter(RagSource.source_type == source_type)
        if category:
            statement = statement.filter(RagSource.category == category)
        candidates = statement.order_by(desc(RagSource.score), desc(RagSource.created_at)).limit(max(top_k * 10, 20)).all()
        if not query.strip():
            return candidates[:top_k]

        tokens = [token.lower() for token in query.split() if token.strip()]
        ranked = []
        for source in candidates:
            haystack = f"{source.title} {source.fragment}".lower()
            token_matches = sum(1 for token in tokens if token in haystack)
            if token_matches:
                ranked.append((token_matches, source.score, source))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item[2] for item in ranked[:top_k]]

    def attach_citation(self, *, source_id: int, case_id: int | None, target_type: str, target_id: int | None, quote: str) -> RagCitation:
        citation = RagCitation(source_id=source_id, case_id=case_id, target_type=target_type, target_id=target_id, quote=quote)
        self.db.add(citation)
        self.db.commit()
        self.db.refresh(citation)
        return citation

    def list_citations(self, *, case_id: int) -> list[RagCitation]:
        return (
            self.db.query(RagCitation)
            .filter(RagCitation.case_id == case_id)
            .order_by(RagCitation.created_at.desc())
            .all()
        )

    def _semantic_search(
        self,
        *,
        query: str,
        case_id: int | None,
        source_type: str | None,
        category: str | None,
        top_k: int,
    ) -> list[RagSource]:
        try:
            vector = self.embedding_service.embed_texts([query])[0]
            hits = self.qdrant_service.search(vector=vector, limit=top_k * 2)
        except Exception:
            return []
        results: list[RagSource] = []
        seen_source_ids: set[int] = set()
        for hit in hits:
            payload = hit.get("payload", {})
            source_id = payload.get("source_id")
            if not source_id or source_id in seen_source_ids:
                continue
            source = self.db.get(RagSource, source_id)
            if not source:
                continue
            if case_id is not None and source.case_id not in {None, case_id}:
                continue
            if source_type and source.source_type != source_type:
                continue
            if category and source.category != category:
                continue
            source.fragment = str(payload.get("fragment") or source.fragment)
            source.score = float(hit.get("score") or source.score)
            results.append(source)
            seen_source_ids.add(source_id)
            if len(results) >= top_k:
                break
        return results

    def _chunk_text(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        size = max(self.settings.rag_chunk_size, 50)
        overlap = min(max(self.settings.rag_chunk_overlap, 0), size // 2)
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
        return [chunk for chunk in chunks if chunk]

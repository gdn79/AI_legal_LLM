from __future__ import annotations

import hashlib

import httpx

from app.core.config import Settings, get_settings


class EmbeddingService:
    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.settings.embedding_model.startswith("stub-") or self.settings.llm_model.startswith("stub-"):
            return [self._stub_embedding(text) for text in texts]

        with httpx.Client(
            base_url=self.settings.llm_base_url,
            timeout=20.0,
            transport=self.transport,
            headers={"Authorization": f"Bearer {self.settings.llm_api_key}"},
        ) as client:
            response = client.post(
                "/v1/embeddings",
                json={"model": self.settings.embedding_model, "input": texts},
            )
            response.raise_for_status()
            payload = response.json()
        return [item["embedding"] for item in payload["data"]]

    def _stub_embedding(self, text: str, dimensions: int = 8) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(dimensions):
            chunk = digest[index * 4 : index * 4 + 4]
            if len(chunk) < 4:
                chunk = chunk.ljust(4, b"\x00")
            value = int.from_bytes(chunk, "big", signed=False)
            values.append(round((value % 2000) / 1000 - 1.0, 6))
        return values

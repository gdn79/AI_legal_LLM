from __future__ import annotations

import math

import httpx

from app.core.config import Settings, get_settings


class QdrantService:
    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport
        self._points: dict[str, list[dict]] = {}

    def ensure_collection(self, vector_size: int) -> None:
        if self.transport is None or self.settings.qdrant_url.startswith("http://localhost"):
            self._points.setdefault(self.settings.qdrant_collection, [])
            return
        with httpx.Client(base_url=self.settings.qdrant_url, timeout=10.0, transport=self.transport) as client:
            client.put(
                f"/collections/{self.settings.qdrant_collection}",
                json={"vectors": {"size": vector_size, "distance": "Cosine"}},
            ).raise_for_status()

    def upsert(self, points: list[dict]) -> None:
        if self.transport is None or self.settings.qdrant_url.startswith("http://localhost"):
            bucket = self._points.setdefault(self.settings.qdrant_collection, [])
            bucket.extend(points)
            return
        with httpx.Client(base_url=self.settings.qdrant_url, timeout=10.0, transport=self.transport) as client:
            client.put(
                f"/collections/{self.settings.qdrant_collection}/points",
                json={"points": points},
            ).raise_for_status()

    def search(self, vector: list[float], limit: int) -> list[dict]:
        if self.transport is None or self.settings.qdrant_url.startswith("http://localhost"):
            points = self._points.get(self.settings.qdrant_collection, [])
            scored = [
                {
                    "id": point["id"],
                    "score": self._cosine_similarity(vector, point["vector"]),
                    "payload": point["payload"],
                }
                for point in points
            ]
            return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
        with httpx.Client(base_url=self.settings.qdrant_url, timeout=10.0, transport=self.transport) as client:
            response = client.post(
                f"/collections/{self.settings.qdrant_collection}/points/search",
                json={"vector": vector, "limit": limit, "with_payload": True},
            )
            response.raise_for_status()
            return response.json().get("result", [])

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

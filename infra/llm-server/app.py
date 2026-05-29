from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse


app = FastAPI(title="OpenAI-Compatible LLM Stub", version="0.1.0")


def _model_name() -> str:
    return os.getenv("LLM_MODEL", "stub-openai-compatible")


def _embedding_from_text(text: str, dimensions: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for index in range(dimensions):
        chunk = digest[index * 4 : index * 4 + 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\x00")
        value = int.from_bytes(chunk, "big", signed=False)
        values.append(round((value % 2000) / 1000 - 1.0, 6))
    return values


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-stub"}


@app.get("/v1/models")
def models() -> dict[str, Any]:
    model = _model_name()
    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": 0,
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="messages must be a non-empty list")

    last_user_message = ""
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            last_user_message = str(message.get("content", ""))
            break

    model = str(payload.get("model") or _model_name())
    response_text = (
        "Stub OpenAI-compatible response. Replace infra/llm-server with a real local LLM server. "
        f"Last user message: {last_user_message[:400]}"
    )

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(datetime.now(timezone.utc).timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


@app.post("/v1/embeddings")
def embeddings(payload: dict[str, Any]) -> dict[str, Any]:
    input_data = payload.get("input")
    if isinstance(input_data, str):
        texts = [input_data]
    elif isinstance(input_data, list):
        texts = [str(item) for item in input_data]
    else:
        raise HTTPException(status_code=400, detail="input must be a string or list of strings")

    model = str(payload.get("model") or os.getenv("EMBEDDING_MODEL", "stub-embedding"))
    data = [
        {
            "object": "embedding",
            "index": index,
            "embedding": _embedding_from_text(text),
        }
        for index, text in enumerate(texts)
    ]

    return {
        "object": "list",
        "model": model,
        "data": data,
        "usage": {
            "prompt_tokens": 0,
            "total_tokens": 0,
        },
    }


@app.exception_handler(Exception)
def unexpected_error_handler(_: Any, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"LLM stub error: {exc}"})

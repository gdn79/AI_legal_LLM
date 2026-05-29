from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_models_endpoint() -> None:
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json()["object"] == "list"


def test_chat_completion_endpoint() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["role"] == "assistant"

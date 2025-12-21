from fastapi.testclient import TestClient

from app.main import create_app


class _FakeGeminiService:
    async def generate_chat_response(self, message: str, history):
        return f"echo:{message}"


def test_chat_happy_path(monkeypatch):
    app = create_app()

    # Lazy import to avoid importing the real GeminiService
    import app.api.chat as chat_api

    app.dependency_overrides[chat_api.get_gemini_service] = lambda: _FakeGeminiService()

    client = TestClient(app)
    r = client.post("/api/v1/chat", json={"message": "hi", "history": []})
    assert r.status_code == 200
    assert r.json() == {"response": "echo:hi"}


def test_chat_schema_defaults(monkeypatch):
    app = create_app()

    import app.api.chat as chat_api

    app.dependency_overrides[chat_api.get_gemini_service] = lambda: _FakeGeminiService()

    client = TestClient(app)
    r = client.post("/api/v1/chat", json={"message": "hi"})
    assert r.status_code == 200

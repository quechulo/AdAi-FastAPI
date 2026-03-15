from fastapi.testclient import TestClient

from app.main import create_app


class _FakeGeminiService:
    async def generate_chat_response(self, message: str, history):
        return (f"chat:{message}", 0.2, 100)


class _FakeAdAgentServiceWithBreakdown:
    async def analyze_and_get_ad(self, history, latest_message: str):
        return {
            "ad_text": "[Tent](https://example.com/tent)",
            "generation_time": 0.5,
            "used_tokens": 70,
            "ad_llm_tokens": 70,
            "ad_embedding_tokens": 20,
        }


class _FakeAdAgentServiceLegacy:
    async def analyze_and_get_ad(self, history, latest_message: str):
        return {
            "ad_text": None,
            "generation_time": 0.1,
            "used_tokens": 30,
        }


def test_agentic_chat_includes_ad_embedding_tokens_in_breakdown():
    app = create_app()

    import app.api.agentic as agentic_api

    app.dependency_overrides[agentic_api.get_gemini_service] = (
        lambda: _FakeGeminiService()
    )
    app.dependency_overrides[agentic_api.get_agentic_service] = (
        lambda: _FakeAdAgentServiceWithBreakdown()
    )

    client = TestClient(app)
    r = client.post(
        "/api/v1/agentic-chat",
        json={"message": "I plan to go camping", "history": []},
    )

    assert r.status_code == 200
    payload = r.json()

    assert payload["generation_time"] == 0.5
    assert payload["used_tokens"] == 190
    assert payload["ad_used_tokens"] == 90

    assert payload["breakdown"]["ad_llm_tokens"] == 70
    assert payload["breakdown"]["ad_embedding_tokens"] == 20
    assert payload["breakdown"]["ad_total_tokens"] == 90

    assert payload["metadata"]["chat_used_tokens"] == 100
    assert payload["metadata"]["ad_llm_tokens"] == 70
    assert payload["metadata"]["ad_embedding_tokens"] == 20


def test_agentic_chat_keeps_legacy_ad_response_compatibility():
    app = create_app()

    import app.api.agentic as agentic_api

    app.dependency_overrides[agentic_api.get_gemini_service] = (
        lambda: _FakeGeminiService()
    )
    app.dependency_overrides[agentic_api.get_agentic_service] = (
        lambda: _FakeAdAgentServiceLegacy()
    )

    client = TestClient(app)
    r = client.post(
        "/api/v1/agentic-chat",
        json={"message": "hello", "history": []},
    )

    assert r.status_code == 200
    payload = r.json()

    assert payload["used_tokens"] == 130
    assert payload["ad_used_tokens"] == 30
    assert payload["breakdown"]["ad_llm_tokens"] == 30
    assert payload["breakdown"]["ad_embedding_tokens"] == 0
    assert payload["breakdown"]["ad_total_tokens"] == 30

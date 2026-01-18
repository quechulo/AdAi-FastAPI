from fastapi.testclient import TestClient

from app.main import create_app


class _FakeRagService:
    async def answer(self, message: str, history, top_k: int):
        # Return one citation to validate schema.
        return {
            "response": f"echo:{message}",
            "citations": [
                {
                    "score": 0.75,
                    "distance": 0.25,
                    "ad": {
                        "id": 123,
                        "title": "Test Ad",
                        "description": "Test Description",
                        "keywords": ["k1", "k2"],
                        "url": "https://example.com",
                        "image_url": None,
                        "cpc": "1.23",
                    },
                }
            ],
        }


def test_rag_happy_path_with_citations():
    app = create_app()

    import app.api.rag as rag_api

    app.dependency_overrides[rag_api.get_rag_service] = lambda: _FakeRagService()

    client = TestClient(app)
    r = client.post(
        "/api/v1/rag-chat",
        json={"message": "hi", "history": [], "top_k": 3},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "echo:hi"
    assert isinstance(body["citations"], list)
    assert body["citations"][0]["score"] == 0.75
    assert body["citations"][0]["distance"] == 0.25
    assert body["citations"][0]["ad"]["id"] == 123


def test_rag_schema_defaults():
    app = create_app()

    import app.api.rag as rag_api

    app.dependency_overrides[rag_api.get_rag_service] = lambda: _FakeRagService()

    client = TestClient(app)
    r = client.post("/api/v1/rag-chat", json={"message": "hi"})
    assert r.status_code == 200


def test_rag_top_k_validation():
    app = create_app()

    import app.api.rag as rag_api

    app.dependency_overrides[rag_api.get_rag_service] = lambda: _FakeRagService()

    client = TestClient(app)
    r = client.post("/api/v1/rag-chat", json={"message": "hi", "top_k": 0})
    assert r.status_code == 422

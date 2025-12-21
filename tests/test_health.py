from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoints():
    client = TestClient(create_app())

    r = client.get("/")
    assert r.status_code == 200

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

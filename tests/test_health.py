from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    # Should at least contain these keys
    assert body.get("status") in {"healthy", "unhealthy"}
    assert "environment" in body or body.get("status") == "unhealthy"

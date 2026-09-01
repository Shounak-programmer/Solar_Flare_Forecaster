"""Test health check endpoints for cloud deployment."""
from fastapi.testclient import TestClient
from app.dashboard_server import app

client = TestClient(app)


def test_root_health():
    """Verify /health returns 200 OK for Render / Docker health checks."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_api_health():
    """Verify /api/health returns valid telemetry status and replay count."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["n_days"] > 0
    assert len(data["replay_days"]) == data["n_days"]

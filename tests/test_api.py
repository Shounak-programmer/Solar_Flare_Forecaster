"""Test REST API operational and telemetry endpoints."""
from fastapi.testclient import TestClient
from app.dashboard_server import app

client = TestClient(app)


def test_system_status():
    """Verify system status model structure."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ingestion_status"] in ["healthy", "degraded", "offline"]
    assert data["model_status"] == "healthy"
    assert "version" in data


def test_forecasts_latest():
    """Verify latest forecast endpoint returns valid probabilities."""
    response = client.get("/api/forecasts/latest")
    assert response.status_code == 200
    data = response.json()
    assert "probability_15m" in data
    assert 0.0 <= data["probability_15m"] <= 1.0
    assert "alert_level" in data


def test_post_forecast_validation():
    """Verify POST /api/forecasts validates payload schema."""
    payload = {
        "probability_15m": 0.42,
        "probability_30m": 0.28,
        "probability_60m": 0.15,
        "alert_level": "WARNING",
        "source": "pytest_client"
    }
    response = client.post("/api/forecasts", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_alerts_endpoint():
    """Verify alerts retrieval."""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_live_stream_endpoint():
    """Verify live stream bridge endpoint."""
    response = client.get("/api/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"

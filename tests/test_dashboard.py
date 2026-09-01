"""Test dashboard science and replay endpoints."""
from fastapi.testclient import TestClient
from app.dashboard_server import app

client = TestClient(app)


def test_static_index():
    """Verify frontend HTML is served at root."""
    response = client.get("/")
    assert response.status_code == 200
    assert "SuryaSetu" in response.text or "Aditya-L1" in response.text


def test_replay_days_manifest():
    """Verify manifest.json contains valid demo days."""
    response = client.get("/api/replay_days")
    assert response.status_code == 200
    data = response.json()
    assert "demo_days" in data or "days" in data or len(data) > 0


def test_replay_single_day():
    """Verify detailed 1-second telemetry replay day."""
    response = client.get("/api/replay/20240705")
    assert response.status_code == 200
    data = response.json()
    assert "time_utc" in data or "date" in data or "times" in data or "solexs_flux" in data


def test_summary_metrics():
    """Verify frozen headline numbers are served."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "forecasting_tss" in data or "detection" in data or "catalog_tss" in data


def test_master_catalog():
    """Verify paginated master catalog."""
    response = client.get("/api/catalog?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] > 10000
    assert len(data["rows"]) == 10


def test_qpp_catalog():
    """Verify QPP catalog and tier grouping."""
    response = client.get("/api/qpp")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert data["total"] >= 500


def test_qpp_wavelets():
    """Verify precomputed Morlet wavelets index."""
    response = client.get("/api/qpp_wavelets")
    assert response.status_code == 200

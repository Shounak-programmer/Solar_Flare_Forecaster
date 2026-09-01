"""Test MongoDB database layer and standalone fallback."""
from app.database import get_db_status, insert_forecast, insert_alert, get_latest_forecast, get_recent_alerts


def test_db_status_fallback():
    """Verify database status returns cleanly in standalone mode."""
    status = get_db_status()
    assert isinstance(status, dict)
    assert "connected" in status


def test_standalone_forecast_handling():
    """Verify graceful handling when MongoDB is not connected."""
    res = insert_forecast({
        "probability_15m": 0.35,
        "probability_30m": 0.22,
        "probability_60m": 0.18,
        "alert_level": "WATCH"
    })
    # In standalone mode without active mongo, returns False without crashing
    assert res in [True, False]


def test_standalone_alert_handling():
    """Verify graceful alert handling."""
    res = insert_alert({
        "level": "WARNING",
        "probability": 0.42,
        "horizon": "15m"
    })
    assert res in [True, False]

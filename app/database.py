"""MongoDB connection layer and data access helpers for SuryaSetu."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

logger = logging.getLogger("suryasetu.database")

MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "suryasetu").strip()

_client = None
_db = None


def get_mongo_client():
    """Returns the MongoClient instance or None if not configured."""
    global _client
    if not MONGODB_URI:
        return None
    if _client is None:
        try:
            from pymongo import MongoClient
            _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            # Test ping
            _client.admin.command("ping")
            logger.info("Connected successfully to MongoDB Atlas")
        except Exception as exc:
            logger.warning(f"MongoDB connection failed: {exc}. Running in standalone fallback mode.")
            _client = None
    return _client


def get_database():
    """Returns the active MongoDB database or None."""
    global _db
    client = get_mongo_client()
    if client is not None:
        _db = client[MONGODB_DATABASE]
        return _db
    return None


def get_db_status() -> dict[str, Any]:
    """Returns connection health and status info."""
    if not MONGODB_URI:
        return {"connected": False, "reason": "MONGODB_URI not configured (standalone mode)"}
    client = get_mongo_client()
    if client is not None:
        try:
            client.admin.command("ping")
            return {
                "connected": True,
                "database": MONGODB_DATABASE,
                "collections": ["forecasts", "alerts", "system_status", "site_stats"]
            }
        except Exception as e:
            return {"connected": False, "reason": str(e)}
    return {"connected": False, "reason": "Connection failed"}


def insert_forecast(record: dict[str, Any]) -> bool:
    """Inserts a forecast record into the 'forecasts' collection."""
    db = get_database()
    if db is None:
        return False
    try:
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        db.forecasts.insert_one(record)
        return True
    except Exception as e:
        logger.error(f"Error inserting forecast: {e}")
        return False


def get_latest_forecast() -> Optional[dict[str, Any]]:
    """Fetches the latest forecast record from MongoDB or returns None."""
    db = get_database()
    if db is None:
        return None
    try:
        doc = db.forecasts.find_one(sort=[("timestamp", -1)])
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception as e:
        logger.error(f"Error fetching latest forecast: {e}")
        return None


def get_recent_alerts(limit: int = 20) -> list[dict[str, Any]]:
    """Fetches the most recent alerts from the 'alerts' collection."""
    db = get_database()
    if db is None:
        return []
    try:
        cursor = db.alerts.find().sort("timestamp", -1).limit(limit)
        results = []
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []


def insert_alert(record: dict[str, Any]) -> bool:
    """Inserts an alert record into the 'alerts' collection."""
    db = get_database()
    if db is None:
        return False
    try:
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        db.alerts.insert_one(record)
        return True
    except Exception as e:
        logger.error(f"Error inserting alert: {e}")
        return False


def increment_visitor_count() -> int:
    """Atomically increments the global visitor counter and returns the new count.
    Uses upsert so the document is created automatically on first visit.
    Falls back to an in-memory counter when MongoDB is unavailable.
    """
    db = get_database()
    if db is None:
        # Standalone fallback — keep an in-memory counter
        increment_visitor_count._standalone_count = getattr(
            increment_visitor_count, "_standalone_count", 0
        ) + 1
        return increment_visitor_count._standalone_count
    try:
        from pymongo import ReturnDocument
        result = db.site_stats.find_one_and_update(
            {"_id": "visitor_counter"},
            {"$inc": {"count": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(result.get("count", 1))
    except Exception as e:
        logger.error(f"Error incrementing visitor count: {e}")
        return -1


def get_visitor_count() -> int:
    """Returns the current visitor count without incrementing it."""
    db = get_database()
    if db is None:
        return getattr(increment_visitor_count, "_standalone_count", 0)
    try:
        doc = db.site_stats.find_one({"_id": "visitor_counter"})
        return int(doc["count"]) if doc else 0
    except Exception as e:
        logger.error(f"Error fetching visitor count: {e}")
        return -1

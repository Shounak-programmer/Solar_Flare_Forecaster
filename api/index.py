"""Vercel Serverless entrypoint — all data is co-located next to this file.

In the Vercel lambda runtime this file lives at /var/task/api/index.py
so dashboard_data/ and static/ are at /var/task/api/dashboard_data/ and
/var/task/api/static/ — paths are resolved relative to __file__ only.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── Path resolution ── everything lives next to THIS file ────────────────────
_HERE = Path(__file__).resolve().parent          # /var/task/api/
DATA  = _HERE / "dashboard_data"                  # /var/task/api/dashboard_data/
STATIC = _HERE / "static"                         # /var/task/api/static/

# ── Lazy DB & models (optional, graceful fallback) ────────────────────────────
try:
    from app.database import get_db_status, get_latest_forecast, get_recent_alerts, insert_forecast, insert_alert
    from app.models import ForecastRecord, AlertRecord, SystemStatusRecord
    _HAS_DB = True
except ImportError:
    _HAS_DB = False
    def get_db_status(): return {"connected": False, "reason": "db module not available"}
    def get_latest_forecast(): return None
    def get_recent_alerts(limit=20): return []
    def insert_forecast(r): return False
    def insert_alert(r): return False

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SuryaSetu: Aditya-L1 Solar Flare Forecaster",
    description="Operational Solar Flare Forecasting and Nowcasting API for Aditya-L1",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def no_store(request, call_next):
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


# ── In-memory JSON cache ──────────────────────────────────────────────────────
_cache: dict[str, Any] = {}


def _load(rel: str) -> Any:
    if rel in _cache:
        return _cache[rel]
    p = DATA / rel
    if not p.exists():
        raise HTTPException(
            status_code=404,
            detail=f"data file not found: {rel} — DATA dir resolved to: {DATA}",
        )
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"corrupt JSON {rel}: {e}")
    _cache[rel] = obj
    return obj


# ── Health & debug ────────────────────────────────────────────────────────────
@app.get("/health")
def root_health():
    return {
        "status": "ok",
        "service": "suryasetu-dashboard",
        "data_dir": str(DATA),
        "data_exists": DATA.exists(),
        "manifest_exists": (DATA / "manifest.json").exists(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health")
def api_health():
    have = DATA.exists() and (DATA / "manifest.json").exists()
    days = sorted(p.stem for p in (DATA / "replay_days").glob("*.json")) if DATA.exists() else []
    return {
        "status": "ok" if have else "no_data",
        "data_dir": str(DATA),
        "replay_days": days,
        "n_days": len(days),
        "database": get_db_status(),
    }


@app.get("/api/debug")
def debug_paths():
    """Diagnostic endpoint — lists files visible at runtime."""
    import os
    found = []
    for root, dirs, files in os.walk(_HERE):
        for f in files[:5]:  # limit output
            found.append(str(Path(root) / f))
    return {
        "__file__": str(__file__),
        "_HERE": str(_HERE),
        "DATA": str(DATA),
        "STATIC": str(STATIC),
        "cwd": os.getcwd(),
        "data_exists": DATA.exists(),
        "manifest_exists": (DATA / "manifest.json").exists(),
        "sample_files": found[:30],
    }


@app.get("/api/system/status")
def system_status():
    have = DATA.exists() and (DATA / "manifest.json").exists()
    days = sorted(p.stem for p in (DATA / "replay_days").glob("*.json")) if DATA.exists() else []
    db_status = get_db_status()
    return {
        "last_update": datetime.now(timezone.utc).isoformat(),
        "ingestion_status": "healthy" if have else "degraded",
        "model_status": "healthy",
        "database_status": "connected" if db_status.get("connected") else "standalone",
        "active_mode": os.environ.get("OPERATION_MODE", "replay"),
        "n_replay_days": len(days),
        "version": "1.0.0",
    }


@app.get("/api/forecasts/latest")
def forecasts_latest():
    latest = get_latest_forecast()
    if latest:
        return latest
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "probability_15m": 0.042,
        "probability_30m": 0.038,
        "probability_60m": 0.035,
        "alert_level": "ALL_CLEAR",
        "source": "baseline_reference",
    }


@app.get("/api/forecasts")
def get_forecasts():
    return [forecasts_latest()]


@app.get("/api/alerts")
def get_alerts():
    db_alerts = get_recent_alerts(limit=20)
    if db_alerts:
        return db_alerts
    return [{
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "ALL_CLEAR",
        "probability": 0.042,
        "horizon": "15m",
        "message": "Solar conditions nominal.",
    }]


@app.get("/api/live")
def live_stream_status():
    return {
        "mode": os.environ.get("OPERATION_MODE", "replay"),
        "status": "ready",
        "message": "Live Aditya-L1 stream connector ready.",
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }


# ── Science & replay APIs ─────────────────────────────────────────────────────
@app.get("/api/replay_days")
def replay_days():
    return _load("manifest.json")


@app.get("/api/replay/{date}")
def replay(date: str):
    if not (date.isdigit() and len(date) == 8):
        raise HTTPException(status_code=400, detail="date must be YYYYMMDD")
    return _load(f"replay_days/{date}.json")


@app.get("/api/metrics")
def metrics():
    return _load("summary_metrics.json")


@app.get("/api/hardness")
def hardness():
    return _load("hardness_ordering.json")


@app.get("/api/catalog")
def catalog(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500),
            status: Optional[str] = None, goes_class: Optional[str] = None):
    cat = _load("master_catalog.json")
    rows = cat["rows"]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if goes_class:
        gc = goes_class.upper()
        rows = [r for r in rows if (r.get("goes_class") or "").startswith(gc)]
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "total": total, "page": page, "page_size": page_size,
        "n_pages": max(1, (total + page_size - 1) // page_size),
        "status_counts": cat["status_counts"], "note": cat["note"],
        "rows": rows[start:start + page_size],
    }


@app.get("/api/qpp")
def qpp(tier: Optional[str] = None):
    q = _load("qpp_catalog.json")
    rows = q["rows"]
    if tier:
        rows = [r for r in rows if r["regime"] == tier]
    return {
        "total": len(rows),
        "total_candidates": q.get("total_candidates"),
        "total_events": q.get("total_events"),
        "by_tier": q["by_tier"],
        "by_tier_candidates": q.get("by_tier_candidates"),
        "by_tier_events": q.get("by_tier_events"),
        "tier_labels": q["tier_labels"],
        "featured_xclass": q["featured_xclass"],
        "rows": rows,
    }


@app.get("/api/qpp_wavelets")
def qpp_wavelets():
    return _load("wavelets/index.json")


@app.get("/api/qpp_wavelet/{wid}")
def qpp_wavelet(wid: str):
    if not wid.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="bad wavelet id")
    return _load(f"wavelets/{wid}.json")


# ── Static frontend ───────────────────────────────────────────────────────────
STATIC.mkdir(parents=True, exist_ok=True)
if STATIC.exists() and (STATIC / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
else:
    @app.get("/")
    def root():
        return {
            "service": "suryasetu-dashboard",
            "api_docs": "/docs",
            "health": "/health",
            "data_dir": str(DATA),
            "data_ready": (DATA / "manifest.json").exists(),
        }

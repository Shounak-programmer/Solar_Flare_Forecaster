"""Data models for Aditya-L1 Solar Flare Forecasting & MongoDB layer."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class ForecastRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    probability_15m: float = Field(..., ge=0.0, le=1.0, description="Calibrated risk for 15-min horizon")
    probability_30m: float = Field(..., ge=0.0, le=1.0, description="Calibrated risk for 30-min horizon")
    probability_60m: float = Field(..., ge=0.0, le=1.0, description="Calibrated risk for 60-min horizon")
    alert_level: str = Field(default="ALL_CLEAR", description="ALL_CLEAR | WATCH | WARNING")
    source: Optional[str] = Field(default="aditya_l1_xgboost_calibrated")
    meta: Optional[dict[str, Any]] = None


class AlertRecord(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: str = Field(..., description="WATCH | WARNING | CRITICAL")
    probability: float = Field(..., ge=0.0, le=1.0)
    horizon: str = Field(default="15m", description="15m | 30m | 60m")
    message: Optional[str] = None
    acknowledged: bool = False


class SystemStatusRecord(BaseModel):
    last_update: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ingestion_status: str = Field(default="healthy", description="healthy | degraded | offline")
    model_status: str = Field(default="healthy", description="healthy | standby | offline")
    database_status: str = Field(default="connected")
    active_mode: str = Field(default="replay", description="replay | live")
    n_replay_days: int = 0
    version: str = "1.0.0"

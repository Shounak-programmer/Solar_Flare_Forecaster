"""Run one detector's pipeline over a set of days and collect events.

Importable helpers (used by tuning Stage 2 and scaling Stage 3) plus a CLI for
ad-hoc runs:

    python scripts/09_detect_per_detector.py --detector solexs_sdd2 \
        --threshold 4.5 --date 20241003
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import DETECTORS, load_detector_day  # noqa: E402
from src.detection.detector_pipeline import (  # noqa: E402
    ExcessResult, compute_excess, detect_from_excess, events_to_frame,
)

LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
DET_DIR = PROJECT_ROOT / "data" / "processed" / "detections"
CHOSEN = PROJECT_ROOT / "data" / "processed" / "reports" / "chosen_thresholds.json"


def detect_day(date_str: str, detector: str, threshold: float,
               exr: ExcessResult | None = None) -> pd.DataFrame:
    utc, cr, g, isf = load_detector_day(date_str, detector)
    if exr is None:
        exr = compute_excess(cr, g, isf)
    events = detect_from_excess(utc, cr, exr, g, threshold)
    df = events_to_frame(events)
    if len(df):
        df.insert(0, "detector", detector)
        df.insert(1, "date", date_str)
    return df


def all_days() -> list[str]:
    return sorted(p.stem for p in LBL_DIR.glob("*.parquet"))


def build_all_catalogs() -> dict[str, pd.DataFrame]:
    """Run every detector at its tuned threshold over all days; write 5 parquets."""
    DET_DIR.mkdir(parents=True, exist_ok=True)
    thresholds = {d: v["threshold"] for d, v in json.load(open(CHOSEN)).items()}
    days = all_days()
    out: dict[str, pd.DataFrame] = {}
    t0 = time.time()
    for det in DETECTORS:
        th = thresholds[det]
        frames = []
        for d in days:
            frames.append(detect_day(d, det, th))
        cat = pd.concat([f for f in frames if len(f)], ignore_index=True) \
            if any(len(f) for f in frames) else events_to_frame([])
        cat_path = DET_DIR / f"{det}_detections.parquet"
        cat.to_parquet(cat_path, index=False)
        out[det] = cat
        print(f"  {det:14s} thr={th}  events={len(cat):6d}  -> {cat_path.name}  "
              f"({time.time()-t0:.0f}s)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-all", action="store_true",
                    help="Run all 5 detectors at tuned thresholds over all days")
    ap.add_argument("--detector", choices=list(DETECTORS))
    ap.add_argument("--threshold", type=float)
    ap.add_argument("--date")
    args = ap.parse_args()

    if args.build_all:
        print(f"Building 5 detector catalogs over {len(all_days())} days ...")
        build_all_catalogs()
        return 0

    if not (args.detector and args.threshold and args.date):
        ap.error("single-day mode needs --detector --threshold --date")
    df = detect_day(args.date, args.detector, args.threshold)
    print(f"{len(df)} events detected on {args.date} by {args.detector} "
          f"at {args.threshold} sigma")
    if len(df):
        show = df[["peak_utc", "peak_rate", "peak_bgsub", "max_significance",
                   "duration_s", "rise_time_s"]].copy()
        print(show.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

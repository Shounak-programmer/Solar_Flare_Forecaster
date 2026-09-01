"""Build the master joint coverage manifest CSV.

One row per calendar day in the joint-coverage window (the earliest day with
either SoLEXS or HEL1OS data, through the latest such day). Records what
exists raw, what was built, and basic GTI counts.

Output: data/processed/coverage_manifest.csv
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import (
    HEL1OS_DETECTORS,
    discover_hel1os,
    discover_solexs,
    hel1os_obs_for_date,
)
from src.data.schema import DETECTOR_BANDS, rate_column, gti_column

PARQUET_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"
OUT_PATH = PROJECT_ROOT / "data" / "processed" / "coverage_manifest.csv"


def _per_day_stats(parquet_path: Path) -> tuple[int, int, int, int]:
    """Return (n_rows, n_detectors_present, solexs_gti_sec, hel1os_total_gti_sec)."""
    df = pd.read_parquet(parquet_path, columns=None)
    n_rows = len(df)
    seen: set[str] = set()
    n_dets = 0
    for det, band in DETECTOR_BANDS:
        if det in seen:
            continue
        rc, gc = rate_column(det, band), gti_column(det)
        if rc in df.columns and gc in df.columns:
            v = df[rc].to_numpy()
            g = df[gc].to_numpy()
            if ((~np.isnan(v)) & g).any():
                n_dets += 1
                seen.add(det)
    sx_gti = int(df["solexs_sdd2_gti"].sum()) if "solexs_sdd2_gti" in df.columns else 0
    h_total = 0
    for det in HEL1OS_DETECTORS:
        col = f"hel1os_{det}_gti"
        if col in df.columns:
            h_total += int(df[col].sum())
    return n_rows, n_dets, sx_gti, h_total


def main() -> int:
    print("Indexing raw data ...")
    hel_obs = discover_hel1os()
    solexs_map = discover_solexs()
    hel_days: set[str] = set()
    for obs in hel_obs:
        cur, end = obs.start.date(), obs.end.date()
        while cur <= end:
            hel_days.add(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
    sx_days = set(solexs_map.keys())

    all_days = sorted(hel_days | sx_days)
    start = datetime.strptime(all_days[0], "%Y%m%d").date()
    end = datetime.strptime(all_days[-1], "%Y%m%d").date()
    print(f"Joint window {start} .. {end}  ({(end-start).days+1} calendar days)")

    rows = []
    cur = start
    n_built = 0
    while cur <= end:
        ds = cur.strftime("%Y%m%d")
        has_sx = ds in sx_days
        has_h = ds in hel_days
        has_joint = has_sx and has_h
        pq = PARQUET_DIR / f"{ds}.parquet"
        parquet_exists = pq.exists()

        n_rows = n_dets = sx_gti = h_gti = 0
        notes = ""
        if parquet_exists:
            try:
                n_rows, n_dets, sx_gti, h_gti = _per_day_stats(pq)
                n_built += 1
                if n_dets < 5:
                    notes = f"partial_coverage_{n_dets}of5_detectors"
            except Exception as exc:  # noqa: BLE001
                notes = f"read_failed:{type(exc).__name__}"
        else:
            if has_joint:
                notes = "build_missing"
            elif has_sx:
                notes = "solexs_only"
            elif has_h:
                notes = "hel1os_only"
            else:
                notes = "no_raw_data"

        rows.append({
            "date": cur.isoformat(),
            "has_solexs": has_sx,
            "has_hel1os": has_h,
            "has_joint": has_joint,
            "parquet_exists": parquet_exists,
            "n_rows": n_rows,
            "n_detectors_present": n_dets,
            "solexs_gti_seconds": sx_gti,
            "hel1os_total_gti_seconds": h_gti,
            "notes": notes,
        })
        cur += timedelta(days=1)

    df = pd.DataFrame(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH}")
    print(f"  total calendar days       = {len(df)}")
    print(f"  has_solexs                = {int(df['has_solexs'].sum())}")
    print(f"  has_hel1os                = {int(df['has_hel1os'].sum())}")
    print(f"  has_joint                 = {int(df['has_joint'].sum())}")
    print(f"  parquet_exists            = {int(df['parquet_exists'].sum())}")
    print(f"  partial_coverage flagged  = {int(df['notes'].str.startswith('partial').sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

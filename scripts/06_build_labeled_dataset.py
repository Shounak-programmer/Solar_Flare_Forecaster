"""Phase 2 — build per-second labeled dataset.

For each joint-coverage day (from coverage_manifest.csv), join the daily wide
light curve with SWPC flare labels + GOES XRS + F10.7 + SSN + AR count and
write data/processed/labeled_seconds/{YYYYMMDD}.parquet.

CLI:
  --date YYYYMMDD   build one day
  --all             build all days where parquet_exists=True in the manifest
  --force           overwrite existing outputs
  --workers N       parallel workers (default 1)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.labeling import label_flares_for_day  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
LC_DIR = PROCESSED / "daily_lightcurves"
OUT_DIR = PROCESSED / "labeled_seconds"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT = PROCESSED / "labeling_report.txt"

P_MANIFEST = PROCESSED / "coverage_manifest.csv"
P_FLARES = PROCESSED / "flares_swpc.parquet"
P_GOES = PROCESSED / "goes_xrs_combined.parquet"
P_INDICES = PROCESSED / "solar_indices_daily.parquet"
P_AR = PROCESSED / "active_regions_daily.parquet"


# ── Module-level state for multiprocessing workers (loaded once per process) ─
_FLARES: pd.DataFrame | None = None
_GOES: pd.DataFrame | None = None
_INDICES: pd.DataFrame | None = None
_AR_COUNTS: pd.Series | None = None


def _load_auxiliaries() -> None:
    global _FLARES, _GOES, _INDICES, _AR_COUNTS
    if _FLARES is None:
        _FLARES = pd.read_parquet(P_FLARES)
    if _GOES is None:
        _GOES = pd.read_parquet(P_GOES).sort_values("utc").reset_index(drop=True)
    if _INDICES is None:
        idx = pd.read_parquet(P_INDICES)
        idx["date"] = pd.to_datetime(idx["date"]).dt.date
        _INDICES = idx.set_index("date")
    if _AR_COUNTS is None:
        ar = pd.read_parquet(P_AR)
        ar["date"] = pd.to_datetime(ar["date"]).dt.date
        _AR_COUNTS = ar.groupby("date").size()


def _slice_flares_for_day(day: date) -> pd.DataFrame:
    """Flares whose peak is within [day - 6h, day + 30h] — buffered for cross-day
    forecast labels. Index preserved as `flare_id`."""
    day_start = pd.Timestamp(day, tz="UTC")
    lo = day_start - pd.Timedelta(hours=6)
    hi = day_start + pd.Timedelta(hours=30)
    return _FLARES[(_FLARES["peak_utc"] >= lo) & (_FLARES["peak_utc"] <= hi)]


def _slice_goes_for_day(day: date) -> pd.DataFrame:
    day_start = pd.Timestamp(day, tz="UTC")
    day_end = day_start + pd.Timedelta(days=1)
    return _GOES[(_GOES["utc"] >= day_start) & (_GOES["utc"] < day_end)]


def label_one_day(date_str: str, force: bool = False) -> dict:
    """Returns a stats dict; never raises (errors captured in the dict)."""
    _load_auxiliaries()
    out_path = OUT_DIR / f"{date_str}.parquet"
    if out_path.exists() and not force:
        return {"date": date_str, "status": "skipped", "out": str(out_path)}

    t0 = time.time()
    lc_path = LC_DIR / f"{date_str}.parquet"
    if not lc_path.exists():
        return {"date": date_str, "status": "missing_lc", "out": None}

    try:
        df = pd.read_parquet(lc_path)
        day = datetime.strptime(date_str, "%Y%m%d").date()
        flares = _slice_flares_for_day(day)
        goes = _slice_goes_for_day(day)
        idx_row = _INDICES.loc[day] if day in _INDICES.index else None
        ar_n = int(_AR_COUNTS.loc[day]) if day in _AR_COUNTS.index else None
        labeled = label_flares_for_day(
            df_wide=df,
            flares_swpc=flares,
            goes_xrs=goes,
            indices_row=idx_row,
            ar_count=ar_n,
        )
        labeled.to_parquet(out_path, index=False, compression="zstd")

        # stats
        flare_secs = int((labeled["is_flare"] == 1).sum())
        ids = labeled.loc[labeled["is_flare"] == 1, "flare_id"].dropna().unique()
        n_events = int(len(ids))
        class_counts = {
            L: int((labeled["flare_class_letter"] == L).sum())
            for L in ("B", "C", "M", "X")
        }
        return {
            "date": date_str,
            "status": "ok",
            "rows": len(labeled),
            "flare_seconds": flare_secs,
            "flare_events": n_events,
            "classes": class_counts,
            "time": time.time() - t0,
            "out": str(out_path),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "date": date_str,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "time": time.time() - t0,
        }


def _format_line(s: dict) -> str:
    if s["status"] == "ok":
        return (
            f"{s['date']}  rows={s['rows']}  flare_seconds={s['flare_seconds']}  "
            f"flare_events={s['flare_events']}  classes={s['classes']}  "
            f"time={s['time']:.1f}s"
        )
    if s["status"] == "skipped":
        return f"{s['date']}  SKIPPED (exists)"
    if s["status"] == "missing_lc":
        return f"{s['date']}  MISSING_LC"
    return f"{s['date']}  FAILED {s.get('error', '')}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="Build only YYYYMMDD")
    ap.add_argument("--all", action="store_true",
                    help="Build every day where the daily LC parquet exists")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing outputs")
    ap.add_argument("--workers", type=int, default=1,
                    help="Parallel worker processes (default 1)")
    args = ap.parse_args()

    manifest = pd.read_csv(P_MANIFEST)
    built_days = manifest.loc[manifest["parquet_exists"] == True, "date"].tolist()
    built_days = [d.replace("-", "") for d in built_days]

    if args.date:
        dates: list[str] = [args.date]
    elif args.all:
        dates = sorted(built_days)
    else:
        ap.error("Pass --date or --all")
        return 2

    print(f"Phase 2 labeling: {len(dates)} day(s), workers={args.workers}, "
          f"force={args.force}")

    t_total = time.time()
    summaries: list[dict] = []

    with open(REPORT, "a", encoding="utf-8", buffering=1) as rep:
        rep.write(f"# labeling started {datetime.utcnow().isoformat()}Z  "
                  f"days={len(dates)}\n")
        if args.workers <= 1:
            for i, d in enumerate(dates, 1):
                s = label_one_day(d, force=args.force)
                summaries.append(s)
                line = _format_line(s)
                rep.write(line + "\n")
                print(f"[{i:>4}/{len(dates)}] {line}")
                if s["status"] == "failed":
                    print(s.get("traceback", ""), file=sys.stderr)
        else:
            # multiprocessing: each worker process loads auxiliaries on its first call
            from multiprocessing import Pool
            with Pool(processes=args.workers, initializer=_load_auxiliaries) as pool:
                args_iter = [(d, args.force) for d in dates]
                for i, s in enumerate(
                    pool.starmap(label_one_day, args_iter), 1
                ):
                    summaries.append(s)
                    line = _format_line(s)
                    rep.write(line + "\n")
                    print(f"[{i:>4}/{len(dates)}] {line}")

        # Aggregate summary
        ok = [s for s in summaries if s["status"] == "ok"]
        skipped = [s for s in summaries if s["status"] == "skipped"]
        failed = [s for s in summaries if s["status"] == "failed"]
        missing = [s for s in summaries if s["status"] == "missing_lc"]
        total_flare_s = sum(s["flare_seconds"] for s in ok)
        total_events = sum(s["flare_events"] for s in ok)
        class_tot = {"B": 0, "C": 0, "M": 0, "X": 0}
        for s in ok:
            for k, v in s["classes"].items():
                class_tot[k] += v
        summary = (
            f"\n# summary {datetime.utcnow().isoformat()}Z  "
            f"built={len(ok)}  skipped={len(skipped)}  failed={len(failed)}  "
            f"missing_lc={len(missing)}  "
            f"total_flare_seconds={total_flare_s}  total_events={total_events}  "
            f"classes={class_tot}  total_time={time.time() - t_total:.1f}s\n"
        )
        rep.write(summary)
        if failed:
            rep.write("# failures:\n")
            for s in failed:
                rep.write(f"#   {s['date']}  {s.get('error','')}\n")
        print(summary.strip())
        if failed:
            for s in failed:
                print(f"  FAILED {s['date']}: {s.get('error','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

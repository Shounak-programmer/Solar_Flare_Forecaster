"""Phase 1 — build daily Parquet light curves on a common 1 Hz UTC grid.

For each UTC day with any SoLEXS or HEL1OS coverage, write one Parquet file
``data/processed/daily_lightcurves/YYYYMMDD.parquet`` with 86400 rows and
columns:

  utc                              : UTC timestamp (datetime64[ns, UTC])
  solexs_sdd2_total                : cts/s on SDD2 (single band)
  solexs_sdd2_gti                  : bool
  hel1os_{det}_{band}              : cts/s per HEL1OS detector & energy band
  hel1os_{det}_gti                 : bool, per detector
       where det ∈ cdte1/cdte2/czt1/czt2 and band labels follow loaders.py.

Run with no args to build every available day, or pass --date YYYYMMDD
to build just one (useful for the Oct 3 2024 validation).
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd  # noqa: F401  (used by build_day)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import (
    HEL1OS_DETECTORS,
    DetectorLC,
    HEL1OSObs,
    bands_for,
    discover_hel1os,
    discover_solexs,
    hel1os_obs_for_date,
    load_hel1os_lightcurves,
    load_solexs_lightcurve,
)

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"


# ─────────────────────────────────────────────────────────────────────────────
# Grid helpers
# ─────────────────────────────────────────────────────────────────────────────
def _bin_to_grid(times: np.ndarray, values: np.ndarray, grid_t0: float, n_sec: int) -> np.ndarray:
    """Map (unix_times, values) → 1-Hz grid by nearest-second assignment.
    Returns float64 array of length ``n_sec`` filled with NaN outside coverage."""
    out = np.full(n_sec, np.nan, dtype=np.float64)
    if times.size == 0:
        return out
    idx = np.rint(times - grid_t0).astype(np.int64)
    inrange = (idx >= 0) & (idx < n_sec)
    if inrange.any():
        out[idx[inrange]] = values[inrange]
    return out


def _gti_mask(gti: list[tuple[float, float]], grid_t0: float, n_sec: int) -> np.ndarray:
    mask = np.zeros(n_sec, dtype=bool)
    for s, e in gti:
        i0 = max(0, int(np.ceil(s - grid_t0)))
        i1 = min(n_sec, int(np.floor(e - grid_t0)) + 1)
        if i1 > i0:
            mask[i0:i1] = True
    return mask


def _apply_lc(df: pd.DataFrame, col: str, lc_values: np.ndarray) -> None:
    """Fill non-NaN positions from lc_values into df[col] without clobbering
    earlier-written values (lets multiple HEL1OS obs in one day stitch)."""
    have_new = ~np.isnan(lc_values)
    if not have_new.any():
        return
    existing = df[col].to_numpy(copy=False)
    take = have_new & np.isnan(existing)
    if take.any():
        existing[take] = lc_values[take]


# ─────────────────────────────────────────────────────────────────────────────
# Build one day
# ─────────────────────────────────────────────────────────────────────────────
def build_day(
    date_str: str,
    hel_obs_list: list[HEL1OSObs],
    solexs_map: dict[str, Path],
) -> pd.DataFrame:
    day = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    grid_t0 = day.timestamp()
    n_sec = 86400
    grid_t = grid_t0 + np.arange(n_sec, dtype=np.float64)

    df = pd.DataFrame(
        {"utc": pd.to_datetime(grid_t, unit="s", utc=True)}
    )

    # SoLEXS columns
    df["solexs_sdd2_total"] = np.nan
    df["solexs_sdd2_gti"] = False
    sx_zip = solexs_map.get(date_str)
    if sx_zip is not None:
        try:
            sx_lc = load_solexs_lightcurve(sx_zip)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] SoLEXS {sx_zip.name}: {exc}", file=sys.stderr)
            sx_lc = None
        if sx_lc is not None:
            t, c = sx_lc.bands["total"]
            _apply_lc(df, "solexs_sdd2_total",
                      _bin_to_grid(t, c, grid_t0, n_sec))
            df["solexs_sdd2_gti"] = _gti_mask(sx_lc.gti, grid_t0, n_sec)

    # HEL1OS columns
    for det in HEL1OS_DETECTORS:
        for label, _ in bands_for(det):
            df[f"hel1os_{det}_{label}"] = np.nan
        df[f"hel1os_{det}_gti"] = False

    for obs in hel1os_obs_for_date(hel_obs_list, day):
        try:
            dets = load_hel1os_lightcurves(obs.path)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] HEL1OS {obs.path.name}: {exc}", file=sys.stderr)
            traceback.print_exc()
            continue

        for det, lc in dets.items():
            for label, (t, c) in lc.bands.items():
                _apply_lc(
                    df, f"hel1os_{det}_{label}",
                    _bin_to_grid(t, c, grid_t0, n_sec),
                )
            gti_col = f"hel1os_{det}_gti"
            df[gti_col] = df[gti_col].to_numpy() | _gti_mask(lc.gti, grid_t0, n_sec)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────
def all_dates(hel_obs_list: list[HEL1OSObs], solexs_map: dict[str, Path]) -> list[str]:
    """Union of all dates with either HEL1OS or SoLEXS coverage."""
    dates: set[str] = set(solexs_map.keys())
    for obs in hel_obs_list:
        d = obs.start.date()
        end = obs.end.date()
        cur = d
        while cur <= end:
            dates.add(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
    return sorted(dates)


def joint_dates(hel_obs_list: list[HEL1OSObs], solexs_map: dict[str, Path]) -> list[str]:
    """Dates with BOTH HEL1OS and SoLEXS coverage."""
    hel_dates: set[str] = set()
    for obs in hel_obs_list:
        cur = obs.start.date()
        end = obs.end.date()
        while cur <= end:
            hel_dates.add(cur.strftime("%Y%m%d"))
            cur += timedelta(days=1)
    return sorted(hel_dates & set(solexs_map.keys()))


def _detector_list_for_day(df, hel_obs_list, solexs_map, date_str) -> list[str]:
    """Detectors with at least one in-GTI, non-NaN sample on this day."""
    from src.data.schema import DETECTOR_BANDS, rate_column, gti_column  # local import
    present: list[str] = []
    seen: set[str] = set()
    for det, band in DETECTOR_BANDS:
        if det in seen:
            continue
        rc, gc = rate_column(det, band), gti_column(det)
        if rc in df.columns and gc in df.columns:
            v = df[rc].to_numpy()
            g = df[gc].to_numpy()
            if ((~np.isnan(v)) & g).any():
                present.append(det)
                seen.add(det)
    return present


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="Build only YYYYMMDD (e.g. 20241003)")
    ap.add_argument("--all", action="store_true",
                    help="Build all joint days (both SoLEXS and HEL1OS present)")
    ap.add_argument("--out", default=str(OUT_DIR), help="Output directory")
    ap.add_argument("--overwrite", action="store_true",
                    help="Re-write existing parquet files")
    ap.add_argument("--report",
                    default=str(PROJECT_ROOT / "data" / "processed" / "build_report.txt"),
                    help="Per-day build report (append mode)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    print("Indexing HEL1OS ...")
    hel_obs = discover_hel1os()
    print(f"  {len(hel_obs)} unique observations (highest version per timestamp)")

    print("Indexing SoLEXS ...")
    solexs_map = discover_solexs()
    print(f"  {len(solexs_map)} daily observations")

    if args.date:
        dates = [args.date]
    elif args.all:
        dates = joint_dates(hel_obs, solexs_map)
    else:
        dates = all_dates(hel_obs, solexs_map)
    print(f"Will build {len(dates)} day(s). Report: {report_path}")

    t_total = time.time()
    n_ok = 0
    n_skip = 0
    failures: list[tuple[str, str]] = []

    with open(report_path, "a", encoding="utf-8", buffering=1) as rep:
        rep.write(f"# build started {datetime.utcnow().isoformat()}Z  "
                  f"days={len(dates)}\n")
        for i, date_str in enumerate(dates, 1):
            out_path = out_dir / f"{date_str}.parquet"
            if out_path.exists() and not args.overwrite:
                n_skip += 1
                continue
            t0 = time.time()
            try:
                df = build_day(date_str, hel_obs, solexs_map)
                df.to_parquet(out_path, index=False, compression="zstd")
                dt = time.time() - t0
                dets = _detector_list_for_day(df, hel_obs, solexs_map, date_str)
                line = (f"{date_str}  rows={len(df)}  "
                        f"detectors={dets}  build_time={dt:.2f}s")
                rep.write(line + "\n")
                n_ok += 1
                print(f"[{i:>4}/{len(dates)}] {line}")
            except Exception as exc:  # noqa: BLE001
                msg = f"FAILED: {type(exc).__name__}: {exc}"
                rep.write(f"{date_str}  {msg}\n")
                failures.append((date_str, msg))
                print(f"[{i:>4}/{len(dates)}] {date_str}  {msg}",
                      file=sys.stderr)
                traceback.print_exc()

        summary = (
            f"\n# summary {datetime.utcnow().isoformat()}Z  "
            f"built={n_ok}  skipped(existing)={n_skip}  "
            f"failed={len(failures)}  "
            f"total_time={time.time() - t_total:.1f}s\n"
        )
        rep.write(summary)
        if failures:
            rep.write("# failures:\n")
            for d, m in failures:
                rep.write(f"#   {d}  {m}\n")

    print(summary.strip())
    if failures:
        print("Failures:")
        for d, m in failures:
            print(f"  {d}  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

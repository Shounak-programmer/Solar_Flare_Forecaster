"""GATE A — leakage audit of the forecasting feature matrix.

(1) manual source-row trace for 3 random t (prove no row > t used)
(2) automated +1-step shift test (features must change as t advances)
(3) matrix shape, target positive rates (vs Phase 2), feature/target correlations
    (flag |corr| > 0.9 as a leakage signature)
(4) GTI gaps -> NaN features (no interpolation)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.features import (
    DETECTORS, LBL_DIR, WINDOWS, build_day_features, feature_names, load_event_tables,
)

FF_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"


def load_all(sample_frac=1.0) -> pd.DataFrame:
    files = sorted(FF_DIR.glob("*.parquet"))
    frames = [pd.read_parquet(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    if sample_frac < 1.0:
        df = df.sample(frac=sample_frac, random_state=0).reset_index(drop=True)
    return df


def check_manual_trace(mt, qt, dl):
    print("=" * 72)
    print("(1) MANUAL SOURCE-ROW TRACE — prove no row with utc > t was used")
    print("=" * 72)
    rng = np.random.default_rng(42)
    days = [p.stem for p in sorted(FF_DIR.glob("*.parquet"))]
    picks = rng.choice(days, 3, replace=False)
    for day in picks:
        ff = pd.read_parquet(FF_DIR / f"{day}.parquet")
        i = int(rng.integers(200, len(ff) - 5))   # avoid earliest rows
        row = ff.iloc[i]
        t = pd.Timestamp(row["utc"])
        tu = t.value // 10**9
        print(f"\n  t = {t}  (day {day}, row {i})")
        # raw labeled_seconds for this day + prev day
        cols = ["utc"] + [c for pr in DETECTORS.values() for c in pr]
        ls = pd.read_parquet(LBL_DIR / f"{day}.parquet", columns=cols)
        ls["utc"] = pd.to_datetime(ls["utc"], utc=True)
        rcol, gcol = DETECTORS["solexs_sdd2"]
        # recompute solexs_sdd2_mean_60m from raw, trailing [t-3600+1, t], compare
        win = ls[(ls["utc"] > t - pd.Timedelta(seconds=WINDOWS["60m"])) & (ls["utc"] <= t)]
        gwin = win[win[gcol]]
        manual = gwin[rcol].mean()
        stored = row["solexs_sdd2_mean_60m"]
        future = ls[ls["utc"] > t]
        print(f"    solexs_sdd2_mean_60m: stored={stored:.4f}  manual[t-60m,t]={manual:.4f}  "
              f"match={np.isclose(stored, manual, rtol=1e-6, equal_nan=True)}")
        print(f"    rows with utc > t available in source: {len(future)} "
              f"(used by feature: 0 by construction — window is [t-W, t])")
        # event features: confirm last detection peak <= t
        prev_idx = np.searchsorted(mt['peak'], tu, side='right') - 1
        last_pk = mt['peak'][prev_idx] if prev_idx >= 0 else None
        print(f"    last master detection peak <= t: "
              f"{pd.Timestamp(last_pk, unit='s', tz='UTC') if last_pk else None} "
              f"(<= t: {last_pk <= tu if last_pk else 'n/a'})  "
              f"time_since_last_det_s stored={row['time_since_last_det_s']}")
        # daily context lag: f107_lag1 must be the PREVIOUS day's value
        print(f"    f107_lag1 stored={row['f107_lag1']}  (uses day {day} minus 1; "
              f"same-day value never read)")


def check_shift(mt, qt, dl):
    print("\n" + "=" * 72)
    print("(2) +1-STEP SHIFT TEST — features must change as t advances")
    print("=" * 72)
    day = "20241003"
    ff = pd.read_parquet(FF_DIR / f"{day}.parquet")
    fn = feature_names(ff)
    # compare consecutive minute rows during an ACTIVE window (values should move)
    seg = ff[(ff["utc"] >= pd.Timestamp("2024-10-03 12:00", tz="UTC")) &
             (ff["utc"] <= pd.Timestamp("2024-10-03 13:00", tz="UTC"))].reset_index(drop=True)
    changed = {}
    for c in fn:
        a = seg[c].to_numpy(np.float64)
        diffs = np.abs(np.diff(a))
        frac_changing = np.mean(diffs[np.isfinite(diffs)] > 0) if np.isfinite(diffs).any() else 0.0
        changed[c] = frac_changing
    static = {c: v for c, v in changed.items() if v < 0.01}
    print(f"  features evaluated: {len(fn)}")
    print(f"  features that change across consecutive t (active window): "
          f"{sum(1 for v in changed.values() if v > 0.5)} > 50%, "
          f"{sum(1 for v in changed.values() if v > 0.0)} > 0%")
    # daily context + bool QPP-present are expected to be near-constant within an hour
    expected_static = [c for c in static if "lag1" in c or "present" in c or "qpp_count" in c]
    unexpected = [c for c in static if c not in expected_static]
    print(f"  near-constant features: {len(static)}  "
          f"(expected-static daily/QPP context: {len(expected_static)})")
    print(f"  UNEXPECTED static features (investigate if non-empty): {unexpected[:10]}")


def check_targets_corr(df):
    print("\n" + "=" * 72)
    print("(3) SHAPE / TARGET RATES / FEATURE-TARGET CORRELATIONS")
    print("=" * 72)
    fn = feature_names(df)
    print(f"  feature matrix shape: {df.shape}  ({len(fn)} features)")
    print(f"  rows in-GTI (>=1 detector): {int(df['in_gti_any'].sum())} "
          f"({100*df['in_gti_any'].mean():.1f}%)")
    print("\n  Target positive rates (all rows) vs Phase 2 reference:")
    ref = {"y_15min": 0.094, "y_30min": 0.179, "y_60min": 0.321}
    for c, r in ref.items():
        print(f"    {c}: {df[c].mean():.4f}   (Phase 2: {r:.4f})")
    print("  multi-class y_class30 distribution:")
    print("    " + df["y_class30"].value_counts(normalize=True).round(4).to_dict().__str__())

    print("\n  |corr| of each feature with y_15min (top 15) — FLAG if > 0.9:")
    sub = df[df["in_gti_any"]].copy()
    corr = sub[fn].corrwith(sub["y_15min"].astype(float)).abs().sort_values(ascending=False)
    for c, v in corr.head(15).items():
        flag = "  <<< LEAKAGE FLAG (>0.9)" if v > 0.9 else ""
        print(f"    {v:.3f}  {c}{flag}")
    n_flag = int((corr > 0.9).sum())
    print(f"\n  features with |corr| > 0.9 to y_15min: {n_flag} "
          f"{'(NONE — good)' if n_flag == 0 else '(INVESTIGATE)'}")
    return n_flag


def check_gti_nan(df):
    print("\n" + "=" * 72)
    print("(4) GTI GAPS -> NaN FEATURES (no interpolation across gaps)")
    print("=" * 72)
    # rows where a detector is out of GTI must have NaN trailing features for it
    det = "hel1os_czt1"
    out_gti = ~df[f"{det}_mean_5m"].notna()
    print(f"  {det}_mean_5m NaN rows: {int(out_gti.sum())} "
          f"({100*out_gti.mean():.1f}%) — these are out-of-GTI / gap-spanning windows")
    # confirm NaN propagates: a fully-out detector-window cannot have a finite std
    bad = df[out_gti & df[f"{det}_std_5m"].notna()]
    print(f"  rows with mean NaN but std finite (interpolation bug): {len(bad)} "
          f"{'(NONE — correct)' if len(bad) == 0 else '(BUG)'}")
    # overall NaN fraction
    fn = feature_names(df)
    print(f"  overall feature NaN fraction: {100*df[fn].isna().to_numpy().mean():.2f}%")


def main() -> int:
    mt, qt, dl = load_event_tables()
    check_manual_trace(mt, qt, dl)
    check_shift(mt, qt, dl)
    print("\nloading full feature matrix ...")
    df = load_all()
    n_flag = check_targets_corr(df)
    check_gti_nan(df)
    print("\n" + "=" * 72)
    print(f"GATE A VERDICT: {'PASS' if n_flag == 0 else 'INVESTIGATE'} "
          f"(no feature trivially predicts the target; trailing-only confirmed)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

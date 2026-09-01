"""Leakage-safe forecasting feature engineering (Phase 4, Stage 4a).

Every feature is computed from data at or before the row timestamp ``t`` using
**trailing** windows only (pandas ``rolling(center=False)`` includes index t and
the W-1 seconds before it; nothing after t). Rows are sampled at 1-minute
cadence; targets are aligned (not recomputed) from ``labeled_seconds``.

Leakage decisions (audited at GATE A):
  - Daily context (F10.7, sunspot number, AR count) is **lagged by 1 day**: a
    forecast at time t on day D uses day (D-1)'s values, which are fully known
    by t. (The labeled_seconds broadcast uses same-day values — not used here.)
  - Flare-history features come from our **master-catalog detections** (peaks
    <= t), NOT from the SWPC catalogue. SWPC is the label source and is not
    available in real time, so using it would be label leakage. We therefore do
    NOT use the labeled_seconds ``time_since_last_peak_sec`` (SWPC-derived).
  - ``time_to_next_peak_sec`` is future-derived and is never used.
  - Trailing windows that cross a GTI gap return NaN (rolling ``min_periods``
    requires enough in-GTI samples; out-of-GTI seconds are set NaN pre-roll).
  - The Neupert residual needs k fit on TRAIN only, so it is formed in Stage 4b
    from the components emitted here (``soft_ddt_5m`` and ``hel1os_hard_rate``).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
PROC = PROJECT_ROOT / "data" / "processed"

# detector -> total-band rate column + gti column
DETECTORS: dict[str, tuple[str, str]] = {
    "solexs_sdd2": ("solexs_sdd2_total", "solexs_sdd2_gti"),
    "hel1os_cdte1": ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti"),
    "hel1os_cdte2": ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti"),
    "hel1os_czt1": ("hel1os_czt1_18_160kev", "hel1os_czt1_gti"),
    "hel1os_czt2": ("hel1os_czt2_18_160kev", "hel1os_czt2_gti"),
}
SOFT = "solexs_sdd2"           # soft X-ray channel
HARD = "hel1os_czt1"           # primary hard X-ray channel
WINDOWS = {"5m": 300, "15m": 900, "30m": 1800, "60m": 3600}
MA_SHORT = 60                  # short trailing mean for derivatives (s)
TARGET_COLS = ["flare_in_next_15min", "flare_in_next_30min",
               "flare_in_next_60min", "max_class_in_next_30min"]


# ---------------------------------------------------------------------------
# Global event tables (sorted once; queried with searchsorted, peaks <= t only)
# ---------------------------------------------------------------------------
def load_event_tables():
    master = pd.read_parquet(PROC / "detections" / "master_flare_catalog.parquet")
    m = master.sort_values("master_peak_unix")
    master_tbl = dict(
        peak=m["master_peak_unix"].to_numpy(np.int64),
        rate=m["peak_rate_max"].to_numpy(np.float64),
        ndet=m["n_detectors"].to_numpy(np.int64),
    )
    qpp = pd.read_parquet(PROC / "detections" / "qpp_catalog.parquet")
    qpp = qpp.drop_duplicates("master_peak_utc").copy()
    qpp["u"] = qpp["master_peak_utc"].astype("int64") // 10**9
    qpp = qpp.sort_values("u")
    qpp_tbl = {"all": qpp["u"].to_numpy(np.int64)}
    for reg in ("classic", "intermediate", "short"):
        qpp_tbl[reg] = np.sort(qpp.loc[qpp["regime"] == reg, "u"].to_numpy(np.int64))

    # daily context, lagged by 1 day -> indexed by the day it is VALID FOR
    idx = pd.read_parquet(PROC / "solar_indices_daily.parquet")
    idx["date"] = pd.to_datetime(idx["date"]).dt.date
    ar = pd.read_parquet(PROC / "active_regions_daily.parquet")
    ar["date"] = pd.to_datetime(ar["date"]).dt.date
    arc = ar.groupby("date").size().rename("ar_count")
    daily = idx.set_index("date").join(arc)
    daily_lag = {}
    for d, row in daily.iterrows():
        valid_for = d + pd.Timedelta(days=1)            # usable from the next day
        daily_lag[valid_for.isoformat() if hasattr(valid_for, "isoformat") else str(valid_for)] = (
            float(row.get("f107_observed", np.nan)),
            float(row.get("sunspot_number", np.nan)) if not pd.isna(row.get("sunspot_number")) else np.nan,
            float(row.get("ar_count", np.nan)) if not pd.isna(row.get("ar_count")) else np.nan,
        )
    return master_tbl, qpp_tbl, daily_lag


def _trailing(series: pd.Series, win: int, stat: str, min_frac: float = 0.5):
    mp = max(1, int(win * min_frac))
    r = series.rolling(win, center=False, min_periods=mp)
    return {"mean": r.mean(), "std": r.std(), "max": r.max(), "median": r.median()}[stat]


def _count_before(sorted_t: np.ndarray, t: np.ndarray, win_s: int) -> np.ndarray:
    """Count of events in (t-win_s, t] for each t (events strictly <= t)."""
    hi = np.searchsorted(sorted_t, t, side="right")
    lo = np.searchsorted(sorted_t, t - win_s, side="right")
    return (hi - lo).astype(np.int64)


# ---------------------------------------------------------------------------
# Per-day feature builder
# ---------------------------------------------------------------------------
def build_day_features(day: str, master_tbl, qpp_tbl, daily_lag) -> pd.DataFrame:
    cols = ["utc"] + [c for pair in DETECTORS.values() for c in pair] + TARGET_COLS
    df = pd.read_parquet(LBL_DIR / f"{day}.parquet", columns=cols)
    df["utc"] = pd.to_datetime(df["utc"], utc=True)

    # prepend previous calendar day's last hour for trailing-window continuity
    prev = (pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}") - pd.Timedelta(days=1)).strftime("%Y%m%d")
    prev_path = LBL_DIR / f"{prev}.parquet"
    n_prepend = 0
    if prev_path.exists():
        pdf = pd.read_parquet(prev_path, columns=cols).tail(WINDOWS["60m"])
        pdf["utc"] = pd.to_datetime(pdf["utc"], utc=True)
        df = pd.concat([pdf, df], ignore_index=True)
        n_prepend = len(pdf)

    # per-detector gti-masked rate + trailing stats
    feat = {}
    rate_ma = {}
    for det, (rcol, gcol) in DETECTORS.items():
        r = df[rcol].astype(np.float64).copy()
        r[~df[gcol].to_numpy(bool)] = np.nan          # out-of-GTI -> NaN (no cross-gap)
        rate_ma[det] = _trailing(r, MA_SHORT, "mean", min_frac=0.3)
        for wname, w in WINDOWS.items():
            feat[f"{det}_mean_{wname}"] = _trailing(r, w, "mean")
            feat[f"{det}_std_{wname}"] = _trailing(r, w, "std")
            feat[f"{det}_max_{wname}"] = _trailing(r, w, "max")
        # trailing background (median) + threshold-crossing count over the hour
        bg = _trailing(r, WINDOWS["60m"], "median")
        thr = bg + 3.0 * np.sqrt(np.clip(bg, 1.0, None))
        above = (r > thr).astype(np.float64)
        above[r.isna().to_numpy()] = np.nan
        feat[f"{det}_xcross_60m"] = above.rolling(
            WINDOWS["60m"], center=False, min_periods=int(WINDOWS["60m"] * 0.5)).sum()
        if det == HARD:
            feat["hel1os_hard_rate"] = rate_ma[det]
            feat["hel1os_hard_bgsub"] = rate_ma[det] - bg

    # physics precursors: trailing one-sided derivatives of the SHORT trailing mean
    soft = rate_ma[SOFT]
    for wname, w in (("5m", 300), ("15m", 900), ("30m", 1800)):
        feat[f"soft_ddt_{wname}"] = (soft - soft.shift(w)) / w
    hardness = rate_ma[HARD] / soft.replace(0, np.nan)
    feat["hardness_ratio"] = hardness
    feat["hardness_ddt_15m"] = (hardness - hardness.shift(900)) / 900

    fdf = pd.DataFrame(feat)
    fdf["utc"] = df["utc"].to_numpy()

    # keep current-day minute marks only (drop prepended tail), at :00 of each minute
    fdf = fdf.iloc[n_prepend:].reset_index(drop=True)
    sec_of_day = (fdf["utc"].astype("int64") // 10**9) % 86400
    minute_mask = (sec_of_day % 60 == 0).to_numpy()
    out = fdf[minute_mask].reset_index(drop=True)
    t = (out["utc"].astype("int64") // 10**9).to_numpy(np.int64)

    # event-based features (peaks strictly <= t)
    mp = master_tbl["peak"]
    prev_idx = np.searchsorted(mp, t, side="right") - 1
    has_prev = prev_idx >= 0
    tsl = np.full(len(t), np.nan)
    tsl[has_prev] = t[has_prev] - mp[prev_idx[has_prev]]
    out["time_since_last_det_s"] = tsl
    lpr = np.full(len(t), np.nan); lnd = np.full(len(t), np.nan)
    lpr[has_prev] = master_tbl["rate"][prev_idx[has_prev]]
    lnd[has_prev] = master_tbl["ndet"][prev_idx[has_prev]]
    out["last_det_peak_rate"] = lpr
    out["last_det_n_detectors"] = lnd
    for wname, w in (("1h", 3600), ("3h", 10800), ("6h", 21600)):
        out[f"det_rate_{wname}"] = _count_before(mp, t, w)

    # QPP trailing features (QPP flare peaks <= t)
    out["qpp_count_60m"] = _count_before(qpp_tbl["all"], t, 3600)
    out["qpp_present_60m"] = (out["qpp_count_60m"] > 0).astype(np.int8)
    for reg in ("classic", "intermediate", "short"):
        out[f"qpp_count_{reg}_60m"] = _count_before(qpp_tbl[reg], t, 3600)

    # daily context, lagged 1 day
    dkey = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    f107, ssn, arc = daily_lag.get(dkey, (np.nan, np.nan, np.nan))
    out["f107_lag1"] = f107
    out["sunspot_number_lag1"] = ssn
    out["ar_count_lag1"] = arc

    # targets aligned from labeled_seconds at the same minute marks
    tgt = df.iloc[n_prepend:].reset_index(drop=True)[minute_mask].reset_index(drop=True)
    out["y_15min"] = tgt["flare_in_next_15min"].astype(np.int8).to_numpy()
    out["y_30min"] = tgt["flare_in_next_30min"].astype(np.int8).to_numpy()
    out["y_60min"] = tgt["flare_in_next_60min"].astype(np.int8).to_numpy()
    out["y_class30"] = tgt["max_class_in_next_30min"].astype(str).to_numpy()

    # observability flag: at least one detector in GTI at t
    in_gti_any = np.zeros(len(out), dtype=bool)
    for det in DETECTORS:
        in_gti_any |= out[f"{det}_mean_5m"].notna().to_numpy()
    out["in_gti_any"] = in_gti_any
    out.insert(0, "day", day)
    return out


FEATURE_COLUMNS_NON_FEATURE = {"utc", "day", "y_15min", "y_30min", "y_60min",
                               "y_class30", "in_gti_any"}


def feature_names(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in FEATURE_COLUMNS_NON_FEATURE]

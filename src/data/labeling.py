"""Per-second supervision labels for daily light curve parquets.

The public entry point is :func:`label_flares_for_day`. It takes one day's
wide light-curve DataFrame plus the relevant slices of the auxiliary tables,
and appends the label columns spec'd in Phase 2.

Label columns added
-------------------
is_flare                    int8  (0/1)
flare_id                    Int64  (nullable)
flare_class_letter          category[B,C,M,X]  (nullable)
flare_class_magnitude       float64  (NaN where no flare)
flare_phase                 category[quiet,pre,rise,peak,decay]
time_to_next_peak_sec       Int64  (NaN if next peak >6 h away)
time_since_last_peak_sec    Int64  (NaN if last peak >6 h ago)
flare_in_next_15min         int8  (0/1)
flare_in_next_30min         int8  (0/1)
flare_in_next_60min         int8  (0/1)
max_class_in_next_30min     category[B,C,M,X]  (NaN if none)
active_ar_count             Int64  (broadcast)
f107_observed               float64  (broadcast)
sunspot_number              Int64  (broadcast)
goes_xrsb_flux              float64  (1-min minute-of-day broadcast to 1 Hz)

Multi-flare overlap precedence (rare):
  is_flare    : union (any active flare → 1)
  class/id    : higher GOES class wins; on tie, higher magnitude
  flare_phase : peak > rise/decay > pre > quiet, applied so the highest-class
                active flare's phase ends up on top
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CLASS_RANK: dict[str, int] = {"B": 1, "C": 2, "M": 3, "X": 4}
RANK_TO_LETTER: dict[int, str] = {v: k for k, v in CLASS_RANK.items()}
LETTER_CATS: list[str] = ["B", "C", "M", "X"]
PHASE_CATS: list[str] = ["quiet", "pre", "rise", "peak", "decay"]
_PHASE_QUIET, _PHASE_PRE, _PHASE_RISE, _PHASE_PEAK, _PHASE_DECAY = 0, 1, 2, 3, 4


def _float_to_Int64(x: np.ndarray) -> pd.arrays.IntegerArray:
    """np.float64 array (NaN allowed) → pandas Int64 nullable array."""
    out = pd.array(np.zeros(len(x), dtype=np.int64), dtype="Int64")
    mask = np.isnan(x)
    if (~mask).any():
        out[~mask] = np.rint(x[~mask]).astype(np.int64)
    out[mask] = pd.NA
    return out


def _rank_letter_array(ranks: np.ndarray) -> pd.Categorical:
    table = np.array(["", "B", "C", "M", "X"], dtype=object)
    s = pd.Series(table[ranks]).replace("", np.nan)
    return pd.Categorical(s, categories=LETTER_CATS)


def label_flares_for_day(
    df_wide: pd.DataFrame,
    flares_swpc: pd.DataFrame,
    goes_xrs: pd.DataFrame | None,
    indices_row: pd.Series | None,
    ar_count: int | None,
    forecast_horizons_min: list[int] = (15, 30, 60),
) -> pd.DataFrame:
    if "utc" not in df_wide.columns:
        raise ValueError("df_wide must have a 'utc' column")
    if len(df_wide) == 0:
        raise ValueError("df_wide is empty")

    # Anchor on the day's 00:00:00 UTC implied by the first row.
    utc = df_wide["utc"]
    if not pd.api.types.is_datetime64_any_dtype(utc):
        utc = pd.to_datetime(utc, utc=True)
    day_start_ts = utc.iloc[0].floor("D")
    day_end_ts = day_start_ts + pd.Timedelta(days=1)
    day_start_unix = day_start_ts.timestamp()
    n_sec = len(df_wide)

    # ── per-second label buffers ─────────────────────────────────────────────
    is_flare = np.zeros(n_sec, dtype=np.int8)
    flare_id_arr = np.full(n_sec, -1, dtype=np.int64)
    class_rank_arr = np.zeros(n_sec, dtype=np.int8)
    class_mag_arr = np.full(n_sec, np.nan, dtype=np.float64)
    phase_arr = np.zeros(n_sec, dtype=np.int8)  # default 0 == quiet

    # ── slice flares intersecting today's 24 h ───────────────────────────────
    if flares_swpc is None or len(flares_swpc) == 0:
        active = flares_swpc.iloc[0:0] if flares_swpc is not None else pd.DataFrame()
    else:
        active = flares_swpc[
            (flares_swpc["end_utc"] >= day_start_ts)
            & (flares_swpc["start_utc"] < day_end_ts)
        ].copy()

    if len(active):
        active["_rank"] = (
            active["goes_class_letter"].map(CLASS_RANK).fillna(0).astype(np.int8)
        )
        # Sort ascending so higher-class writes overwrite lower-class for the
        # same overlapping seconds (class/id/phase precedence).
        active = active.sort_values(
            ["_rank", "goes_class_magnitude"], na_position="first"
        )

        starts = active["start_utc"].dt.tz_convert("UTC").astype("int64").to_numpy() / 1e9
        peaks = active["peak_utc"].dt.tz_convert("UTC").astype("int64").to_numpy() / 1e9
        ends = active["end_utc"].dt.tz_convert("UTC").astype("int64").to_numpy() / 1e9
        ranks = active["_rank"].to_numpy()
        mags = active["goes_class_magnitude"].to_numpy()
        ids = active.index.to_numpy()

        for s, p, e, r, m, fid in zip(starts, peaks, ends, ranks, mags, ids):
            s0 = int(np.floor(s - day_start_unix))
            e0 = int(np.floor(e - day_start_unix)) + 1  # inclusive end second
            i0 = max(0, s0)
            i1 = min(n_sec, e0)
            if i1 > i0:
                is_flare[i0:i1] = 1
                # class/id only if we have a real class letter
                if r > 0:
                    class_rank_arr[i0:i1] = r
                    class_mag_arr[i0:i1] = m if not np.isnan(m) else np.nan
                flare_id_arr[i0:i1] = int(fid)

        # Phase: pre first, then rise/decay, then peak. All sorted ascending by
        # class so highest-class active flare's phase ends up on top.
        for s, p, e in zip(starts, peaks, ends):
            pre_lo = int(np.floor(s - 30 * 60 - day_start_unix))
            pre_hi = int(np.floor(s - day_start_unix))
            lo, hi = max(0, pre_lo), min(n_sec, pre_hi)
            if hi > lo:
                # Only paint pre where currently quiet — never demote rise/decay/peak.
                mask = phase_arr[lo:hi] == _PHASE_QUIET
                phase_arr[lo:hi][mask] = _PHASE_PRE

        for s, p, e in zip(starts, peaks, ends):
            rs_lo = int(np.floor(s - day_start_unix))
            rs_hi = int(np.floor(p - day_start_unix))
            lo, hi = max(0, rs_lo), min(n_sec, rs_hi)
            if hi > lo:
                phase_arr[lo:hi] = _PHASE_RISE
            dc_lo = int(np.floor(p - day_start_unix)) + 1
            dc_hi = int(np.floor(e - day_start_unix)) + 1
            lo, hi = max(0, dc_lo), min(n_sec, dc_hi)
            if hi > lo:
                phase_arr[lo:hi] = _PHASE_DECAY

        for p in peaks:
            pk_lo = int(np.floor(p - 30 - day_start_unix))
            pk_hi = int(np.floor(p + 30 - day_start_unix)) + 1
            lo, hi = max(0, pk_lo), min(n_sec, pk_hi)
            if hi > lo:
                phase_arr[lo:hi] = _PHASE_PEAK

    # ── forecast columns based on ALL peaks in the buffered window ───────────
    if flares_swpc is None or len(flares_swpc) == 0:
        peaks_unix = np.array([], dtype=np.float64)
        peak_ranks = np.array([], dtype=np.int8)
    else:
        peaks_unix = (
            flares_swpc["peak_utc"].dt.tz_convert("UTC").astype("int64").to_numpy()
            / 1e9
        ).astype(np.float64)
        peak_ranks = (
            flares_swpc["goes_class_letter"].map(CLASS_RANK).fillna(0)
            .astype(np.int8).to_numpy()
        )
        order = np.argsort(peaks_unix)
        peaks_unix = peaks_unix[order]
        peak_ranks = peak_ranks[order]

    seconds_unix = day_start_unix + np.arange(n_sec, dtype=np.float64)
    SIX_HOURS = 6.0 * 3600.0

    # time_to_next_peak — first peak strictly > t
    if peaks_unix.size:
        idx_next = np.searchsorted(peaks_unix, seconds_unix, side="right")
        valid_next = idx_next < peaks_unix.size
        ttn = np.full(n_sec, np.nan, dtype=np.float64)
        ttn[valid_next] = (
            peaks_unix[np.clip(idx_next, 0, peaks_unix.size - 1)][valid_next]
            - seconds_unix[valid_next]
        )
        ttn[ttn > SIX_HOURS] = np.nan
    else:
        ttn = np.full(n_sec, np.nan, dtype=np.float64)

    # time_since_last_peak — last peak <= t (side='right' then -1)
    if peaks_unix.size:
        idx_prev = np.searchsorted(peaks_unix, seconds_unix, side="right") - 1
        valid_prev = idx_prev >= 0
        tsl = np.full(n_sec, np.nan, dtype=np.float64)
        tsl[valid_prev] = (
            seconds_unix[valid_prev]
            - peaks_unix[np.clip(idx_prev, 0, peaks_unix.size - 1)][valid_prev]
        )
        tsl[tsl > SIX_HOURS] = np.nan
    else:
        tsl = np.full(n_sec, np.nan, dtype=np.float64)

    # flare_in_next_Xmin: mark [peak - X*60, peak) for each peak
    forecast_cols: dict[str, np.ndarray] = {}
    for X in forecast_horizons_min:
        col = np.zeros(n_sec, dtype=np.int8)
        win_sec = X * 60
        for pt in peaks_unix:
            lo = int(np.ceil(pt - win_sec - day_start_unix))
            hi = int(np.ceil(pt - day_start_unix))
            lo = max(0, lo)
            hi = min(n_sec, hi)
            if hi > lo:
                col[lo:hi] = 1
        forecast_cols[f"flare_in_next_{X}min"] = col

    # max_class_in_next_30min — same window, write low-rank first
    max_class_rank = np.zeros(n_sec, dtype=np.int8)
    if peaks_unix.size:
        rank_order = np.argsort(peak_ranks)
        for i in rank_order:
            r = int(peak_ranks[i])
            if r == 0:
                continue
            pt = peaks_unix[i]
            lo = max(0, int(np.ceil(pt - 30 * 60 - day_start_unix)))
            hi = min(n_sec, int(np.ceil(pt - day_start_unix)))
            if hi > lo:
                max_class_rank[lo:hi] = r

    # ── GOES xrsb 1-min → 1-sec broadcast ────────────────────────────────────
    goes_arr = np.full(n_sec, np.nan, dtype=np.float64)
    if goes_xrs is not None and len(goes_xrs) > 0:
        g = goes_xrs[
            (goes_xrs["utc"] >= day_start_ts) & (goes_xrs["utc"] < day_end_ts)
        ]
        if len(g):
            t_sec = (g["utc"].astype("int64").to_numpy() / 1e9) - day_start_unix
            min_idx = np.floor(t_sec / 60).astype(np.int64)
            vals = g["xrsb_flux"].to_numpy(dtype=np.float64)
            valid = (min_idx >= 0) & (min_idx < 1440)
            min_idx, vals = min_idx[valid], vals[valid]
            minute_arr = np.full(1440, np.nan, dtype=np.float64)
            minute_arr[min_idx] = vals
            full_sec = np.repeat(minute_arr, 60)
            n_copy = min(n_sec, full_sec.size)
            goes_arr[:n_copy] = full_sec[:n_copy]

    # ── assemble output ──────────────────────────────────────────────────────
    out = df_wide.copy()
    out["is_flare"] = is_flare
    out["flare_id"] = pd.array(
        np.where(flare_id_arr < 0, pd.NA, flare_id_arr), dtype="Int64"
    )
    out["flare_class_letter"] = _rank_letter_array(class_rank_arr)
    out["flare_class_magnitude"] = class_mag_arr
    out["flare_phase"] = pd.Categorical(
        [PHASE_CATS[i] for i in phase_arr], categories=PHASE_CATS
    )
    out["time_to_next_peak_sec"] = _float_to_Int64(ttn)
    out["time_since_last_peak_sec"] = _float_to_Int64(tsl)
    for k, v in forecast_cols.items():
        out[k] = v
    out["max_class_in_next_30min"] = _rank_letter_array(max_class_rank)

    # broadcast scalars (nullable)
    ar = ar_count if ar_count is not None and not pd.isna(ar_count) else pd.NA
    out["active_ar_count"] = pd.array([ar] * n_sec, dtype="Int64")
    f107 = (
        float(indices_row["f107_observed"])
        if indices_row is not None
        and "f107_observed" in indices_row
        and not pd.isna(indices_row["f107_observed"])
        else np.nan
    )
    out["f107_observed"] = np.full(n_sec, f107, dtype=np.float64)
    ssn = (
        int(indices_row["sunspot_number"])
        if indices_row is not None
        and "sunspot_number" in indices_row
        and not pd.isna(indices_row["sunspot_number"])
        else pd.NA
    )
    out["sunspot_number"] = pd.array([ssn] * n_sec, dtype="Int64")
    out["goes_xrsb_flux"] = goes_arr
    return out

"""Single-detector classical flare detection pipeline.

Implements the classical template:

    smooth (boxcar ~70 s) -> label-free background -> significance ->
    persistence runs -> refine to surrounding local minima ->
    measure per-event attributes -> drop < 60 s -> link homologous events.

Detection is **independent of the Phase-2 labels**: the background uses the
label-free 10th-percentile estimator (``is_flare=None``), so detections can be
fairly matched against the SWPC catalogue without circularity.

The expensive, threshold-independent part (``compute_excess``) is separated
from the cheap per-threshold extraction (``detect_from_excess``) so that
threshold tuning can compute the excess once per (day, detector) and sweep
thresholds for free.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from .background import DEFAULT_WINDOW_S, rolling_background
from .significance import excess_significance, persistence_runs, poisson_sigma

DEFAULT_SMOOTH_S = 70
DEFAULT_MIN_DURATION_S = 60
DEFAULT_LINK_GAP_S = 120        # merge above-threshold runs <2 min apart
DEFAULT_EDGE_LOOKBACK_S = 1800  # cap on flanking-minimum search (+/-30 min)
DEFAULT_PEAK_SEP_S = 300        # min separation between distinct flare peaks
DEFAULT_PEAK_PROMINENCE = 1.0   # min excess-prominence (sigma) for a sub-peak
PREFLARE_BG_S = 1800            # preflare background averaging window


def boxcar(x: np.ndarray, w: int) -> np.ndarray:
    """NaN-aware centered boxcar smoothing."""
    s = pd.Series(np.asarray(x, dtype=np.float64))
    return s.rolling(w, center=True, min_periods=max(1, w // 4)).mean().to_numpy()


@dataclass
class ExcessResult:
    smoothed: np.ndarray
    background: np.ndarray
    sigma: np.ndarray
    excess: np.ndarray


def compute_excess(
    count_rate: np.ndarray,
    gti_mask: np.ndarray,
    is_flare: np.ndarray | None = None,
    smooth_s: int = DEFAULT_SMOOTH_S,
    bg_window_s: int = DEFAULT_WINDOW_S,
) -> ExcessResult:
    """Threshold-independent: smooth, background, Poisson excess.

    The background is the rolling estimate of the *smoothed* rate (Option A):
    boxcar-smoothing removes the zero/burst bimodality of low-count hard-X-ray
    data, so the median recovers the true quiescent level (~tens of cts/s for
    CZT) instead of collapsing to 0 as a 10th-percentile of the raw rate does.
    When ``is_flare`` is provided the label-aware median (with +/-30 min flare
    dilation) is used; otherwise the label-free 10th-percentile fallback runs on
    the smoothed rate. Uniform across all five detectors; SoLEXS is unaffected
    because its smoothed median ~= its raw quiet floor.
    """
    cr = np.asarray(count_rate, dtype=np.float64)
    smoothed = boxcar(cr, smooth_s)
    bg = rolling_background(smoothed, gti_mask, is_flare=is_flare, window_s=bg_window_s)
    sig = poisson_sigma(bg)
    ex = excess_significance(smoothed, bg)
    return ExcessResult(smoothed, bg, sig, ex)


def _merge_runs(runs: list[tuple[int, int]], gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    merged = [list(runs[0])]
    for s, e in runs[1:]:
        if s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def _valley_before(y: np.ndarray, idx: int, lower: int, lookback: int) -> int:
    """Index of the minimum of ``y`` between max(lower, idx-lookback) and idx —
    the start-of-rise valley, bounded so events don't run into neighbours."""
    lo = max(lower, idx - lookback)
    seg = y[lo:idx + 1]
    if seg.size == 0 or np.all(np.isnan(seg)):
        return idx
    return lo + int(np.nanargmin(seg))


def _valley_after(y: np.ndarray, idx: int, upper: int, lookahead: int) -> int:
    """Index of the minimum of ``y`` between idx and min(upper, idx+lookahead)."""
    hi = min(upper, idx + lookahead + 1)
    seg = y[idx:hi]
    if seg.size == 0 or np.all(np.isnan(seg)):
        return idx
    return idx + int(np.nanargmin(seg))


@dataclass
class FlareEvent:
    start_idx: int
    peak_idx: int
    end_idx: int
    start_utc: pd.Timestamp
    peak_utc: pd.Timestamp
    end_utc: pd.Timestamp
    duration_s: int
    peak_rate: float
    preflare_bg: float
    peak_bgsub: float
    max_significance: float
    rise_time_s: int
    max_derivative: float


def detect_from_excess(
    utc: pd.Series,
    count_rate: np.ndarray,
    exr: ExcessResult,
    gti_mask: np.ndarray,
    threshold_sigma: float,
    min_duration_s: int = DEFAULT_MIN_DURATION_S,
    link_gap_s: int = DEFAULT_LINK_GAP_S,
    edge_lookback_s: int = DEFAULT_EDGE_LOOKBACK_S,
) -> list[FlareEvent]:
    """Extract flare events at one threshold from a precomputed excess."""
    cr = np.asarray(count_rate, dtype=np.float64)
    g = np.asarray(gti_mask, dtype=bool)
    sm = exr.smoothed
    ex = exr.excess

    runs = persistence_runs(ex, threshold_sigma, min_len_s=min_duration_s, gti_mask=g)
    runs = _merge_runs(runs, link_gap_s)

    events: list[FlareEvent] = []
    for r0, r1 in runs:
        seg_ex = ex[r0:r1]
        if seg_ex.size == 0 or np.all(np.isnan(seg_ex)):
            continue
        seg = np.nan_to_num(seg_ex, nan=-np.inf)
        # Distinct flare peaks within the interval: local maxima of the excess,
        # separated by >= peak_sep and standing >= prominence sigma above the
        # intervening valleys. This splits clustered flares into separate events.
        peaks, _ = find_peaks(seg, distance=DEFAULT_PEAK_SEP_S,
                              prominence=DEFAULT_PEAK_PROMINENCE)
        if peaks.size == 0:
            peaks = np.array([int(np.argmax(seg))])
        peak_idxs = [r0 + int(p) for p in peaks]

        for k, peak_idx in enumerate(peak_idxs):
            # boundaries: valley between this peak and its neighbours, capped at
            # the interval edges and the lookback window.
            left_bound = peak_idxs[k - 1] if k > 0 else r0
            right_bound = peak_idxs[k + 1] if k + 1 < len(peak_idxs) else r1 - 1
            start_idx = _valley_before(sm, peak_idx, left_bound, edge_lookback_s)
            end_idx = _valley_after(sm, peak_idx, right_bound, edge_lookback_s)
            # refine the true peak (max raw rate) near the excess-peak
            w0 = max(start_idx, peak_idx - DEFAULT_PEAK_SEP_S)
            w1 = min(end_idx, peak_idx + DEFAULT_PEAK_SEP_S) + 1
            local = cr[w0:w1]
            if local.size and not np.all(np.isnan(local)):
                peak_idx = w0 + int(np.nanargmax(local))
            duration = end_idx - start_idx
            if duration < min_duration_s:
                continue

            lo = max(0, start_idx - PREFLARE_BG_S)
            pre_vals = cr[lo:start_idx][g[lo:start_idx]]
            preflare_bg = (float(np.nanmedian(pre_vals)) if pre_vals.size
                           else float(exr.background[start_idx]))
            if not np.isfinite(preflare_bg):
                preflare_bg = 0.0

            peak_rate = float(cr[peak_idx])
            peak_bgsub = peak_rate - preflare_bg
            max_sig = float(np.nanmax(ex[start_idx:end_idx + 1]))
            rise_time = max(0, peak_idx - start_idx)
            if peak_idx > start_idx:
                deriv = np.diff(sm[start_idx:peak_idx + 1])
                max_deriv = float(np.nanmax(deriv)) if deriv.size else 0.0
            else:
                max_deriv = 0.0

            events.append(FlareEvent(
                start_idx=start_idx, peak_idx=peak_idx, end_idx=end_idx,
                start_utc=utc.iloc[start_idx], peak_utc=utc.iloc[peak_idx],
                end_utc=utc.iloc[end_idx], duration_s=int(duration),
                peak_rate=peak_rate, preflare_bg=preflare_bg, peak_bgsub=peak_bgsub,
                max_significance=max_sig, rise_time_s=int(rise_time),
                max_derivative=max_deriv,
            ))

    events.sort(key=lambda e: e.peak_idx)
    return events


def events_to_frame(events: list[FlareEvent]) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=[f.name for f in FlareEvent.__dataclass_fields__.values()])
    return pd.DataFrame([asdict(e) for e in events])


def detect_flares(
    utc: pd.Series,
    count_rate: np.ndarray,
    gti_mask: np.ndarray,
    threshold_sigma: float,
    is_flare: np.ndarray | None = None,
    smooth_s: int = DEFAULT_SMOOTH_S,
    bg_window_s: int = DEFAULT_WINDOW_S,
    min_duration_s: int = DEFAULT_MIN_DURATION_S,
) -> list[FlareEvent]:
    """Convenience one-shot: compute excess then extract events at one threshold."""
    exr = compute_excess(count_rate, gti_mask, is_flare, smooth_s, bg_window_s)
    return detect_from_excess(utc, count_rate, exr, gti_mask, threshold_sigma,
                              min_duration_s=min_duration_s)

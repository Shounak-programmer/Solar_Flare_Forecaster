"""Label-aware rolling background estimation, per detector.

The background is the slowly-varying quiescent count rate underneath flares.
Two modes:

- **Training / label-aware** (``is_flare`` provided): rolling *median* over a
  30-min window EXCLUDING flagged flare seconds, so flares never inflate their
  own background. Windows with too few quiet seconds widen adaptively, then
  fall back to the segment-global quiet median.

  The ``is_flare`` exclusion mask is **dilated** by ``flare_pad_s`` (default
  30 min) before use. This is necessary because the SWPC ``[start, end]``
  interval is tighter than the true elevated-emission window: a flare's
  impulsive rise and (especially) its soft-X-ray gradual-decay tail extend
  well past the catalogued end, where ``is_flare`` is already 0. Without
  dilation those unlabelled-but-elevated seconds dominate the median and the
  background climbs into the flare (verified on the 2024-10-03 X9.0: plain
  exclusion gives a peak background of ~11,600 cts/s vs a true quiet floor of
  ~330; ±30 min dilation brings it back to ~650).
- **Inference / unlabelled** (``is_flare=None``): rolling 10th-percentile of
  the window — a robust low-envelope estimate that approximates the quiet floor
  without needing labels.

GTI is always respected: the day is split into GTI-contiguous segments and the
rolling window never bridges a gap (no background is computed across dead time).
Background is NaN wherever the detector is out of GTI.

Each detector is processed independently — backgrounds are never shared.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WINDOW_S = 1800          # 30 min
DEFAULT_MIN_QUIET_S = 120        # need >=2 min of quiet data in a window
WIDEN_FACTOR = 4                 # adaptive widen multiplier
INFERENCE_PERCENTILE = 0.10      # 10th-percentile fallback when unlabelled
DEFAULT_FLARE_PAD_S = 1800       # dilate is_flare mask ±30 min before excluding


def _dilate_mask(mask: np.ndarray, pad: int) -> np.ndarray:
    """Grow a boolean mask by ``pad`` samples on each side (rolling-max)."""
    if pad <= 0:
        return np.asarray(mask, dtype=bool)
    s = pd.Series(np.asarray(mask, dtype=np.int8))
    grown = s.rolling(2 * pad + 1, center=True, min_periods=1).max()
    return grown.to_numpy() > 0


def gti_segments(gti_mask: np.ndarray) -> list[tuple[int, int]]:
    """Return [start, end) index pairs of contiguous GTI-True runs."""
    g = np.asarray(gti_mask, dtype=bool)
    if not g.any():
        return []
    edges = np.diff(g.astype(np.int8))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)
    if g[0]:
        starts = [0] + starts
    if g[-1]:
        ends = ends + [len(g)]
    return list(zip(starts, ends))


def rolling_background(
    count_rate: np.ndarray,
    gti_mask: np.ndarray,
    is_flare: np.ndarray | None = None,
    window_s: int = DEFAULT_WINDOW_S,
    min_quiet_s: int = DEFAULT_MIN_QUIET_S,
    flare_pad_s: int = DEFAULT_FLARE_PAD_S,
) -> np.ndarray:
    """Compute the per-second background for one detector over one day.

    Parameters
    ----------
    count_rate : (N,) float  counts/sec
    gti_mask   : (N,) bool    True where the detector is observing
    is_flare   : (N,) int/bool or None
        If given, seconds with is_flare==1 are excluded from the background
        (label-aware). If None, the inference 10th-percentile fallback is used.
    window_s, min_quiet_s : window length and minimum quiet samples.

    Returns
    -------
    (N,) float background; NaN outside GTI.
    """
    cr = np.asarray(count_rate, dtype=np.float64)
    gti = np.asarray(gti_mask, dtype=bool)
    n = cr.size
    bg = np.full(n, np.nan, dtype=np.float64)

    # quiet = valid samples used to estimate background
    quiet = cr.copy()
    invalid = ~gti
    if is_flare is not None:
        invalid |= _dilate_mask(np.asarray(is_flare, dtype=bool), flare_pad_s)
    quiet[invalid] = np.nan

    wide = window_s * WIDEN_FACTOR
    for s, e in gti_segments(gti):
        seg = pd.Series(quiet[s:e])
        if seg.notna().sum() == 0:
            # no quiet samples at all in this segment -> fall back to the raw
            # segment median if any valid raw samples exist, else leave NaN.
            raw_seg = cr[s:e]
            bg[s:e] = np.nanmedian(raw_seg) if np.isfinite(raw_seg).any() else np.nan
            continue
        if is_flare is not None:
            est = seg.rolling(window_s, center=True, min_periods=min_quiet_s).median()
            est = est.fillna(
                seg.rolling(wide, center=True, min_periods=max(1, min_quiet_s // 2)).median()
            )
            est = est.fillna(seg.median())
        else:
            est = seg.rolling(window_s, center=True, min_periods=min_quiet_s).quantile(
                INFERENCE_PERCENTILE
            )
            est = est.fillna(
                seg.rolling(wide, center=True, min_periods=max(1, min_quiet_s // 2)).quantile(
                    INFERENCE_PERCENTILE
                )
            )
            est = est.fillna(seg.quantile(INFERENCE_PERCENTILE))
        bg[s:e] = est.to_numpy()

    return bg

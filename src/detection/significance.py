"""Poisson significance of a count-rate excess above background.

For binned X-ray count rates the per-second noise is Poisson, so the standard
deviation of the background is sqrt(background) (with a floor of 1 count to
avoid division blow-ups in deep quiescence). The excess in units of sigma is

    excess(t) = (count_rate(t) - background(t)) / sqrt(max(background(t), 1))

A detection requires the excess to stay above a threshold for a minimum
duration (persistence), which rejects single-second Poisson spikes.
"""
from __future__ import annotations

import numpy as np

SIGMA_FLOOR = 1.0


def poisson_sigma(background: np.ndarray) -> np.ndarray:
    return np.sqrt(np.maximum(np.asarray(background, dtype=np.float64), SIGMA_FLOOR))


def excess_significance(
    count_rate: np.ndarray, background: np.ndarray
) -> np.ndarray:
    """(count_rate - background) / sigma, in units of sigma. NaN-propagating."""
    cr = np.asarray(count_rate, dtype=np.float64)
    bg = np.asarray(background, dtype=np.float64)
    return (cr - bg) / poisson_sigma(bg)


def persistence_runs(
    excess: np.ndarray,
    threshold: float,
    min_len_s: int = 60,
    gti_mask: np.ndarray | None = None,
) -> list[tuple[int, int]]:
    """Return [start, end) index runs where excess >= threshold continuously for
    at least ``min_len_s`` seconds (optionally restricted to in-GTI seconds).

    NaN excess values break a run (treated as below threshold).
    """
    ex = np.asarray(excess, dtype=np.float64)
    flag = ex >= threshold
    flag &= np.isfinite(ex)
    if gti_mask is not None:
        flag &= np.asarray(gti_mask, dtype=bool)

    runs: list[tuple[int, int]] = []
    if not flag.any():
        return runs
    padded = np.concatenate(([0], flag.astype(np.int8), [0]))
    edges = np.diff(padded)
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    for s, e in zip(starts, ends):
        if (e - s) >= min_len_s:
            runs.append((int(s), int(e)))
    return runs

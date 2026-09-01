"""Detection evaluation: per-bin skill scores and operational baselines.

The master catalogue is scored as a per-bin nowcast against the SWPC catalogue
on a fixed in-GTI time grid, alongside two operational baselines on the SAME
bins (Bloomfield 2012 / Camporeale 2025 framing):

  - climatology : predict at the historical base rate (a random/constant
    forecast -> TSS = 0 by construction).
  - persistence : predict a flare in this bin iff a flare occurred in the
    previous in-GTI bin (recent activity continues).

Beating BOTH baselines is the bar for claiming skill over the operational
reference (Camporeale 2025: even the official NOAA forecast barely clears them).
"""
from __future__ import annotations

import numpy as np

from .matching import Contingency


def binary_contingency(obs: np.ndarray, pred: np.ndarray) -> Contingency:
    obs = np.asarray(obs, dtype=bool)
    pred = np.asarray(pred, dtype=bool)
    tp = int(np.sum(obs & pred))
    fp = int(np.sum(~obs & pred))
    fn = int(np.sum(obs & ~pred))
    tn = int(np.sum(~obs & ~pred))
    return Contingency(tp=tp, fp=fp, fn=fn, tn=tn)


def persistence_prediction(obs: np.ndarray, segment: np.ndarray,
                           trailing_bins: int = 1) -> np.ndarray:
    """Predict bin b positive iff any of the previous ``trailing_bins`` in-GTI
    bins (same contiguous segment) was positive. ``trailing_bins=1`` is one-step
    persistence; larger windows give persistence its best shot (recent activity
    continues). Bins without enough same-segment history predict 0."""
    obs = np.asarray(obs, dtype=bool)
    segment = np.asarray(segment)
    pred = np.zeros_like(obs)
    for k in range(1, trailing_bins + 1):
        same = np.zeros_like(obs)
        same[k:] = segment[k:] == segment[:-k]
        shifted = np.zeros_like(obs)
        shifted[k:] = obs[:-k]
        pred |= shifted & same
    return pred


def climatology_contingency(obs: np.ndarray, rng_seed: int = 0) -> Contingency:
    """Expected contingency of a random forecast issued at the base rate.

    A base-rate random predictor has POD = POFD = base_rate, hence TSS = 0.
    Returned as expected (fractional rounded) counts for completeness.
    """
    obs = np.asarray(obs, dtype=bool)
    n = obs.size
    p = obs.mean()                      # base rate
    n_pos = int(obs.sum())
    n_neg = n - n_pos
    tp = int(round(p * n_pos))
    fn = n_pos - tp
    fp = int(round(p * n_neg))
    tn = n_neg - fp
    return Contingency(tp=tp, fp=fp, fn=fn, tn=tn)

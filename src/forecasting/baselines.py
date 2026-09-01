"""Reference forecasters: climatology, persistence, logistic regression, XGBoost.

All operate on the leakage-safe feature matrix. Probabilistic models have their
decision threshold tuned on validation (maximize TSS), then applied to test.
"""
from __future__ import annotations

import numpy as np


def climatology_probability(train_y: np.ndarray) -> float:
    """Constant forecast = train base rate. A constant predictor has TSS 0."""
    return float(np.mean(train_y))


def persistence_probability(det_rate_trailing: np.ndarray) -> np.ndarray:
    """Persistence score = recent detection activity (a trailing flare count).
    Higher recent activity -> higher predicted flare probability. The decision
    threshold (how much recent activity triggers an alarm) is tuned on val."""
    x = np.asarray(det_rate_trailing, dtype=np.float64)
    return np.nan_to_num(x, nan=0.0)


def neupert_residual(hard_rate: np.ndarray, soft_ddt: np.ndarray, k: float) -> np.ndarray:
    """HEL1OS hard X-ray minus k * d(soft)/dt (Neupert). k is fit on TRAIN only."""
    return np.asarray(hard_rate, np.float64) - k * np.asarray(soft_ddt, np.float64)


def fit_neupert_k(hard_rate: np.ndarray, soft_ddt: np.ndarray) -> float:
    """OLS slope of hard on d(soft)/dt over TRAIN rows (finite, positive ddt)."""
    h = np.asarray(hard_rate, np.float64)
    s = np.asarray(soft_ddt, np.float64)
    m = np.isfinite(h) & np.isfinite(s) & (s > 0)
    if m.sum() < 100:
        return 0.0
    return float(np.polyfit(s[m], h[m], 1)[0])

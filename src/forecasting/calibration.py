"""Isotonic-regression calibration + reliability metrics.

Isotonic regression is monotonic, so it preserves the ranking of predictions ->
TSS and the TSS-optimal threshold are essentially unchanged; what it improves is
probability *reliability* (Brier score, ECE), which is what the dashboard's
risk gauge and the all-clear decision need.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


def fit_isotonic(p_val: np.ndarray, y_val: np.ndarray) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(np.asarray(p_val, float), np.asarray(y_val, float))
    return iso


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, float); p = np.asarray(p, float)
    return float(np.mean((p - y) ** 2))


def reliability_curve(y: np.ndarray, p: np.ndarray, n_bins: int = 10):
    """Return (mean_pred, obs_freq, count) per probability bin (equal-width)."""
    y = np.asarray(y, float); p = np.asarray(p, float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, n_bins - 1)
    mean_pred, obs_freq, count = [], [], []
    for b in range(n_bins):
        m = idx == b
        n = int(m.sum())
        count.append(n)
        mean_pred.append(float(p[m].mean()) if n else np.nan)
        obs_freq.append(float(y[m].mean()) if n else np.nan)
    return np.array(mean_pred), np.array(obs_freq), np.array(count)


def expected_calibration_error(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    mean_pred, obs_freq, count = reliability_curve(y, p, n_bins)
    n = np.asarray(count, float)
    valid = n > 0
    return float(np.sum(np.abs(obs_freq[valid] - mean_pred[valid]) * n[valid]) / n.sum())

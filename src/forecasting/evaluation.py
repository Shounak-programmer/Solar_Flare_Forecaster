"""Forecasting evaluation metrics. TSS is the optimization target; accuracy is
never reported as a headline (imbalance trap)."""
from __future__ import annotations

import numpy as np


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y = np.asarray(y_true).astype(bool)
    p = np.asarray(y_pred).astype(bool)
    tp = int(np.sum(y & p)); fp = int(np.sum(~y & p))
    fn = int(np.sum(y & ~p)); tn = int(np.sum(~y & ~p))
    pod = tp / (tp + fn) if (tp + fn) else 0.0           # recall / hit rate
    pofd = fp / (fp + tn) if (fp + tn) else 0.0
    far = fp / (tp + fp) if (tp + fp) else 0.0           # false-alarm ratio
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    tss = pod - pofd
    denom = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
    hss = (2 * (tp * tn - fp * fn) / denom) if denom else 0.0
    return dict(tss=tss, hss=hss, pod=pod, far=far, precision=precision,
                pofd=pofd, tp=tp, fp=fp, fn=fn, tn=tn)


def best_threshold(y_true: np.ndarray, prob: np.ndarray,
                   grid: np.ndarray | None = None) -> tuple[float, float]:
    """Threshold maximizing TSS (tuned on validation, applied to test)."""
    if grid is None:
        grid = np.unique(np.quantile(prob, np.linspace(0.01, 0.99, 99)))
    best_t, best_tss = 0.5, -1.0
    for t in grid:
        m = binary_metrics(y_true, prob >= t)
        if m["tss"] > best_tss:
            best_tss, best_t = m["tss"], float(t)
    return best_t, best_tss


def per_class_recall(y_true: np.ndarray, y_pred: np.ndarray,
                     class_label: np.ndarray) -> dict:
    """POD (recall) of positive windows broken down by upcoming-flare class."""
    y = np.asarray(y_true).astype(bool)
    p = np.asarray(y_pred).astype(bool)
    out = {}
    for c in ("B", "C", "M", "X"):
        sel = y & (np.asarray(class_label) == c)
        n = int(sel.sum())
        hit = int((p & sel).sum())
        out[c] = (hit, n, hit / n if n else float("nan"))
    return out

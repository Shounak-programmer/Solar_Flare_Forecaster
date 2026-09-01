"""Match detected events to a reference catalogue and compute skill scores.

Used by threshold tuning (Stage 2), scaling (Stage 3) and final evaluation
(Stage 6). The contingency table uses event-matching for TP/FP/FN (a detection
counts as a hit if its peak is within ``tol_s`` of a catalogue peak) and a
fixed time-bin grid to define the negative-opportunity count for TN, so that
TSS = POD - POFD is well defined.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

DEFAULT_TOL_S = 180          # +/- 3 min match tolerance (Neupert peak-timing offset)
DEFAULT_BIN_S = 360          # 6-min negative-opportunity bin (== 2*tol)


@dataclass
class Contingency:
    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def pod(self) -> float:                      # recall / probability of detection
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def far(self) -> float:                      # false alarm ratio (of detections)
        d = self.tp + self.fp
        return self.fp / d if d else 0.0

    @property
    def pofd(self) -> float:                     # probability of false detection
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def tss(self) -> float:                      # true skill statistic (Peirce)
        return self.pod - self.pofd

    @property
    def hss(self) -> float:                      # Heidke skill score
        tp, fp, fn, tn = self.tp, self.fp, self.fn, self.tn
        denom = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
        return (2 * (tp * tn - fp * fn) / denom) if denom else 0.0

    def as_dict(self) -> dict:
        return dict(tp=self.tp, fp=self.fp, fn=self.fn, tn=self.tn,
                    pod=self.pod, far=self.far, pofd=self.pofd,
                    precision=self.precision, tss=self.tss, hss=self.hss)


def match_events(
    detection_peaks: np.ndarray,    # int64 unix seconds, sorted
    catalog_peaks: np.ndarray,      # int64 unix seconds, sorted
    tol_s: int = DEFAULT_TOL_S,
) -> tuple[int, int, int, np.ndarray, np.ndarray]:
    """Greedy one-to-one match within +/- tol_s.

    Returns (tp, fp, fn, matched_detection_mask, matched_catalog_mask). Each
    catalogue peak matches at most one detection and vice-versa.
    """
    det = np.asarray(detection_peaks, dtype=np.int64)
    cat = np.asarray(catalog_peaks, dtype=np.int64)
    det_matched = np.zeros(det.size, dtype=bool)
    cat_matched = np.zeros(cat.size, dtype=bool)

    if det.size and cat.size:
        order = np.argsort(det)
        det_sorted = det[order]
        for ci, cpk in enumerate(cat):
            lo = np.searchsorted(det_sorted, cpk - tol_s, side="left")
            hi = np.searchsorted(det_sorted, cpk + tol_s, side="right")
            best = -1
            best_dt = tol_s + 1
            for di in range(lo, hi):
                oi = order[di]
                if det_matched[oi]:
                    continue
                dt = abs(int(det[oi]) - int(cpk))
                if dt < best_dt:
                    best_dt = dt
                    best = oi
            if best >= 0:
                det_matched[best] = True
                cat_matched[ci] = True

    tp = int(cat_matched.sum())
    fn = int((~cat_matched).sum())
    fp = int((~det_matched).sum())
    return tp, fp, fn, det_matched, cat_matched


def negative_opportunities(total_gti_seconds: int, n_catalog: int,
                           bin_s: int = DEFAULT_BIN_S) -> int:
    """Number of negative (non-flare) time bins = total bins - positives."""
    n_bins = int(total_gti_seconds // bin_s)
    return max(0, n_bins - n_catalog)


def contingency(
    detection_peaks: np.ndarray,
    catalog_peaks: np.ndarray,
    total_gti_seconds: int,
    tol_s: int = DEFAULT_TOL_S,
    bin_s: int = DEFAULT_BIN_S,
) -> Contingency:
    tp, fp, fn, _, _ = match_events(detection_peaks, catalog_peaks, tol_s)
    neg = negative_opportunities(total_gti_seconds, len(catalog_peaks), bin_s)
    tn = max(0, neg - fp)
    return Contingency(tp=tp, fp=fp, fn=fn, tn=tn)

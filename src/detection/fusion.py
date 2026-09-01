"""Master-catalog fusion of single-detector detections into physical flares.

Grouping = **bounded single-linkage**. Detections are swept in peak-time order;
a detection joins the current cluster only if it is within ``link_window_s`` of
the previous member AND the cluster's total peak span stays within
``max_span_s``. The span cap is the anti-over-merge fix: plain transitive
Union-Find chains A-B-C across active periods into 60-min blobs, whereas a real
flare's cross-detector peaks span at most the Neupert offset (~3 min). Pure
mutual-nearest-neighbour linkage was rejected because it fragments a tight
5-detector cluster (only the closest pair is mutual, the rest split off and
under-count ``n_detectors``).

Each master flare stores its member peak times so that downstream matching is
done **member-aware** (a master matches a catalogue flare if ANY member peak is
within tolerance), which is faithful to what the detectors actually saw and
immune to the median-peak drift caused by the Neupert offset.

Per master flare:
  master_peak  = median of member peaks   (display attribute only)
  master_start = earliest member start
  master_end   = latest member end
  n_detectors  = number of distinct detectors contributing (1-5)
  member_peaks_unix = list of member peak times (for member-aware matching)
  confidence   = (n_detectors / 5) * geomean(per-detector max significance)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_LINK_WINDOW_S = 180   # max gap between consecutive member peaks
DEFAULT_MAX_SPAN_S = 240      # max total peak span of one physical flare (~Neupert)

_COLS = [
    "master_peak_utc", "master_start_utc", "master_end_utc",
    "master_peak_unix", "master_start_unix", "master_end_unix",
    "n_detectors", "n_members", "detectors", "member_peaks_unix",
    "max_significance", "peak_rate_max", "confidence",
]


def _cluster_ids(peaks: np.ndarray, link_window_s: int, max_span_s: int) -> np.ndarray:
    """Bounded single-linkage cluster id for peak-sorted detections."""
    ids = np.zeros(peaks.size, dtype=np.int64)
    if peaks.size == 0:
        return ids
    cid = 0
    anchor = peaks[0]
    prev = peaks[0]
    for k in range(1, peaks.size):
        p = peaks[k]
        if (p - prev) <= link_window_s and (p - anchor) <= max_span_s:
            ids[k] = cid
        else:
            cid += 1
            ids[k] = cid
            anchor = p
        prev = p
    return ids


def fuse_detections(
    det: pd.DataFrame,
    link_window_s: int = DEFAULT_LINK_WINDOW_S,
    max_span_s: int = DEFAULT_MAX_SPAN_S,
) -> pd.DataFrame:
    """Fuse a concatenated multi-detector detection table into a master catalog.

    ``det`` needs columns: detector, peak_unix, start_unix, end_unix,
    max_significance, peak_rate. One row out per physical flare.
    """
    if len(det) == 0:
        return pd.DataFrame(columns=_COLS)

    d = det.sort_values("peak_unix").reset_index(drop=True)
    peaks = d["peak_unix"].to_numpy(np.int64)
    d = d.assign(_comp=_cluster_ids(peaks, link_window_s, max_span_s))

    rows = []
    for _, grp in d.groupby("_comp", sort=False):
        member_peaks = sorted(int(x) for x in grp["peak_unix"].to_numpy())
        master_peak = int(np.median(member_peaks))
        per_det_sig = grp.groupby("detector")["max_significance"].max()
        dets = sorted(per_det_sig.index.tolist())
        n_det = len(dets)
        sig_clip = np.clip(per_det_sig.to_numpy(np.float64), 1e-6, None)
        geomean = float(np.exp(np.mean(np.log(sig_clip))))
        rows.append({
            "master_peak_unix": master_peak,
            "master_start_unix": int(grp["start_unix"].min()),
            "master_end_unix": int(grp["end_unix"].max()),
            "n_detectors": n_det,
            "n_members": int(len(grp)),
            "detectors": ",".join(dets),
            "member_peaks_unix": member_peaks,
            "max_significance": float(grp["max_significance"].max()),
            "peak_rate_max": float(grp["peak_rate"].max()),
            "confidence": (n_det / 5.0) * geomean,
        })

    out = pd.DataFrame(rows).sort_values("master_peak_unix").reset_index(drop=True)
    out["master_peak_utc"] = pd.to_datetime(out["master_peak_unix"], unit="s", utc=True)
    out["master_start_utc"] = pd.to_datetime(out["master_start_unix"], unit="s", utc=True)
    out["master_end_utc"] = pd.to_datetime(out["master_end_unix"], unit="s", utc=True)
    return out[_COLS]


def member_match_mask(master: pd.DataFrame, catalog_unix: np.ndarray,
                      tol_s: int) -> np.ndarray:
    """Boolean mask: does each master flare have ANY member peak within tol_s of
    any catalogue peak? (member-aware matching, immune to median drift)."""
    cat = np.sort(np.asarray(catalog_unix, dtype=np.int64))
    out = np.zeros(len(master), dtype=bool)
    if cat.size == 0:
        return out
    for i, mp in enumerate(master["member_peaks_unix"].to_numpy()):
        for p in mp:
            lo = np.searchsorted(cat, p - tol_s, side="left")
            if lo < cat.size and cat[lo] <= p + tol_s:
                out[i] = True
                break
    return out

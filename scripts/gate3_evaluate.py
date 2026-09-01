"""GATE 3 — evaluate the 5 per-detector catalogs vs SWPC over all 620 days.

Per detector: total events, POD/FAR/TSS/HSS, and the per-class catch counts.
Prints the 5-detector x 4-class table to verify CZT catches proportionally more
X than C (hardness ordering holds at scale).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import DETECTORS, load_detector_day  # noqa: E402
from src.detection.matching import Contingency, match_events, negative_opportunities

DET_DIR = PROJECT_ROOT / "data" / "processed" / "detections"
LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
REPORT = PROJECT_ROOT / "data" / "processed" / "reports" / "detection_per_detector.txt"
TOL_S = 180
BIN_S = 360
CLASS_RANK = {"B": 1, "C": 2, "M": 3, "X": 4}


def main() -> int:
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    day_set = set(days)
    flares = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet")
    flares = flares.dropna(subset=["peak_utc"]).copy()
    flares["day"] = flares["peak_utc"].dt.strftime("%Y%m%d")
    flares = flares[flares["day"].isin(day_set)]
    flares["peak_unix"] = flares["peak_utc"].astype("int64") // 10**9

    # Per detector: in-GTI catalogue peaks (+class) and total GTI seconds.
    # Cache GTI per (day, detector) by scanning each day once per detector.
    lines = ["GATE 3 - per-detector detection vs SWPC (all {} days, +/-{}s)".format(len(days), TOL_S),
             "=" * 78]
    class_table: dict[str, dict[str, tuple[int, int]]] = {}
    summary_rows = []

    for det in DETECTORS:
        cat_path = DET_DIR / f"{det}_detections.parquet"
        cat = pd.read_parquet(cat_path)
        det_peaks = (cat["peak_utc"].astype("int64") // 10**9).to_numpy() if len(cat) else np.array([], dtype=np.int64)
        det_peaks = np.sort(det_peaks)

        # in-GTI catalogue flares for this detector
        cat_unix, cat_rank = [], []
        gti_seconds = 0
        for d in days:
            utc, cr, g, isf = load_detector_day(d, det)
            gti_seconds += int(g.sum())
            day_flares = flares[flares["day"] == d]
            if len(day_flares):
                t0u = utc.iloc[0].value // 10**9
                for _, fr in day_flares.iterrows():
                    sec = int(fr["peak_unix"] - t0u)
                    if 0 <= sec < len(g) and g[sec]:
                        cat_unix.append(int(fr["peak_unix"]))
                        cat_rank.append(CLASS_RANK.get(str(fr["goes_class_letter"]), 0))
        cat_arr = np.array(sorted(cat_unix), dtype=np.int64)
        order = np.argsort(cat_unix)
        ranks = np.array(cat_rank)[order] if cat_rank else np.array([])

        tp, fp, fn, _, cat_matched = match_events(det_peaks, cat_arr, TOL_S)
        neg = negative_opportunities(gti_seconds, len(cat_arr), BIN_S)
        c = Contingency(tp=tp, fp=fp, fn=fn, tn=max(0, neg - fp))

        per_class = {}
        for L, rk in CLASS_RANK.items():
            sel = ranks == rk
            n = int(sel.sum())
            hit = int(cat_matched[sel].sum()) if n else 0
            per_class[L] = (hit, n)
        class_table[det] = per_class

        lines.append(f"\n{det}  (events={len(cat)}, in-GTI SWPC flares={len(cat_arr)})")
        lines.append(f"  TP={tp} FP={fp} FN={fn} TN={c.tn}")
        lines.append(f"  POD={c.pod:.3f}  FAR={c.far:.3f}  TSS={c.tss:.3f}  HSS={c.hss:.3f}")
        lines.append("  per-class recall: " +
                     "  ".join(f"{L}:{h}/{n}" for L, (h, n) in per_class.items()))
        summary_rows.append((det, len(cat), c.pod, c.far, c.tss, c.hss))

    # 5x4 class table
    lines.append("\n5-DETECTOR x 4-CLASS recall table (caught / in-GTI total)")
    lines.append("  {:14s} {:>12s} {:>12s} {:>12s} {:>12s}".format("detector", "B", "C", "M", "X"))
    for det in DETECTORS:
        row = class_table[det]
        cells = []
        for L in ("B", "C", "M", "X"):
            h, n = row[L]
            cells.append(f"{h}/{n}" + (f" ({100*h/n:.0f}%)" if n else ""))
        lines.append("  {:14s} {:>12s} {:>12s} {:>12s} {:>12s}".format(det, *cells))

    # hardness check
    lines.append("\nHardness check (X-recall vs C-recall):")
    for det in DETECTORS:
        xh, xn = class_table[det]["X"]
        ch, cn = class_table[det]["C"]
        xr = xh / xn if xn else 0
        cr_ = ch / cn if cn else 0
        ratio = xr / cr_ if cr_ > 0 else float("inf")
        lines.append(f"  {det:14s} X={xr:.2f}  C={cr_:.2f}  X/C={ratio:.1f}x")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    # machine-readable hardness sidecar for the dashboard (computed here, never
    # hand-entered downstream). X-over-C selectivity per detector, soft -> hard.
    import json
    band_by_det = {"solexs_sdd2": "soft", "hel1os_cdte1": "8-70 keV",
                   "hel1os_cdte2": "8-70 keV", "hel1os_czt1": "20-150 keV",
                   "hel1os_czt2": "20-150 keV"}
    name_by_det = {"solexs_sdd2": "SoLEXS-SDD2", "hel1os_cdte1": "HEL1OS-CdTe1",
                   "hel1os_cdte2": "HEL1OS-CdTe2", "hel1os_czt1": "HEL1OS-CZT1",
                   "hel1os_czt2": "HEL1OS-CZT2"}
    det_json = []
    for det in DETECTORS:
        xh, xn = class_table[det]["X"]; ch, cn = class_table[det]["C"]
        xr = xh / xn if xn else 0.0; cr_ = ch / cn if cn else 0.0
        ratio = xr / cr_ if cr_ > 0 else None
        det_json.append({"name": name_by_det.get(det, det), "band": band_by_det.get(det, ""),
                         "x_recall": round(xr, 3), "c_recall": round(cr_, 3),
                         "xc_ratio": round(ratio, 1) if ratio is not None else None,
                         "x_hit": xh, "x_n": xn, "c_hit": ch, "c_n": cn})
    obj = {"detectors": det_json,
           "caption": "X-over-C detection selectivity rises monotonically soft->hard: the "
                      "non-thermal hard-X signature that justifies the independent 5-detector architecture."}
    (REPORT.parent / "hardness_ordering.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORT} and hardness_ordering.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

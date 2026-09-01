"""STAGE 2 — TSS-optimal threshold tuning, independently per detector.

Tuning set: all 2024 labeled days (mentor: most active / best test data) plus
the 4 anchor X-class days. For each detector the threshold-independent excess is
computed once per day, then events are extracted at every candidate threshold
and matched to the SWPC catalogue (peak within +/-2 min). The TSS-maximizing
threshold is selected per detector.

Outputs:
  data/processed/reports/threshold_tuning.txt
  data/processed/reports/chosen_thresholds.json
  data/validation/gate2_tss_curves.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import DETECTORS, load_detector_day  # type: ignore
from src.detection.detector_pipeline import compute_excess, detect_from_excess
from src.detection.matching import Contingency, match_events, negative_opportunities

LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
REPORTS = PROJECT_ROOT / "data" / "processed" / "reports"
OUT_TXT = REPORTS / "threshold_tuning.txt"
OUT_JSON = REPORTS / "chosen_thresholds.json"
OUT_PNG = PROJECT_ROOT / "data" / "validation" / "gate2_tss_curves.png"

THRESHOLDS = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
ANCHORS = ["20241003", "20241001", "20260201", "20251114"]
TOL_S = 180
BIN_S = 360


def tuning_days() -> list[str]:
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    d2024 = [d for d in days if d.startswith("2024")]
    return sorted(set(d2024) | set(ANCHORS))


def class_rank(letter: str) -> int:
    return {"B": 1, "C": 2, "M": 3, "X": 4}.get(letter, 0)


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    days = tuning_days()
    print(f"Tuning over {len(days)} days, {len(DETECTORS)} detectors, "
          f"{len(THRESHOLDS)} thresholds each")

    flares = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet")
    flares = flares.dropna(subset=["peak_utc"]).copy()
    flares["peak_unix"] = flares["peak_utc"].astype("int64") // 10**9
    day_set = set(days)
    flares["day"] = flares["peak_utc"].dt.strftime("%Y%m%d")
    flares = flares[flares["day"].isin(day_set)]

    # results[detector][threshold] -> Contingency ; plus per-class POD at chosen
    results: dict[str, dict[float, Contingency]] = {d: {} for d in DETECTORS}
    detpeaks: dict[str, dict[float, list[int]]] = {
        d: {th: [] for th in THRESHOLDS} for d in DETECTORS
    }
    gti_seconds: dict[str, int] = {d: 0 for d in DETECTORS}
    # catalogue peaks that are in-GTI for each detector (threshold-independent)
    cat_unix: dict[str, list[int]] = {d: [] for d in DETECTORS}
    cat_rank: dict[str, list[int]] = {d: [] for d in DETECTORS}

    t0 = time.time()
    for di, det in enumerate(DETECTORS, 1):
        for date_str in days:
            utc, cr, g, isf = load_detector_day(date_str, det)
            gti_seconds[det] += int(g.sum())
            exr = compute_excess(cr, g, is_flare=isf)
            for th in THRESHOLDS:
                evs = detect_from_excess(utc, cr, exr, g, th)
                for e in evs:
                    detpeaks[det][th].append(int(e.peak_utc.value // 10**9))
            # in-GTI catalogue flares for this detector on this day
            day_flares = flares[flares["day"] == date_str]
            if len(day_flares):
                t0u = utc.iloc[0].value // 10**9
                for _, fr in day_flares.iterrows():
                    sec = int(fr["peak_unix"] - t0u)
                    if 0 <= sec < len(g) and g[sec]:
                        cat_unix[det].append(int(fr["peak_unix"]))
                        cat_rank[det].append(class_rank(str(fr["goes_class_letter"])))
        print(f"  [{di}/{len(DETECTORS)}] {det} done ({time.time()-t0:.0f}s)")

    # build contingency per threshold
    chosen: dict[str, dict] = {}
    lines: list[str] = []
    lines.append("STAGE 2 - TSS THRESHOLD TUNING")
    lines.append(f"tuning days={len(days)}  thresholds={THRESHOLDS}  tol=+/-{TOL_S}s")
    lines.append("=" * 70)

    curves: dict[str, list[float]] = {}
    for det in DETECTORS:
        cat = np.array(sorted(cat_unix[det]), dtype=np.int64)
        neg = negative_opportunities(gti_seconds[det], len(cat), BIN_S)
        lines.append(f"\n{det}  (in-GTI SWPC flares={len(cat)}, "
                     f"neg-opportunities={neg}, GTI days~{gti_seconds[det]//86400})")
        lines.append(f"  {'thr':>4} {'TP':>5} {'FP':>6} {'FN':>5} {'POD':>6} "
                     f"{'FAR':>6} {'POFD':>7} {'TSS':>7} {'HSS':>7}")
        curve = []
        best_th, best_tss = THRESHOLDS[0], -2.0
        for th in THRESHOLDS:
            det_peaks = np.array(sorted(detpeaks[det][th]), dtype=np.int64)
            tp, fp, fn, _, _ = match_events(det_peaks, cat, TOL_S)
            tn = max(0, neg - fp)
            c = Contingency(tp=tp, fp=fp, fn=fn, tn=tn)
            results[det][th] = c
            curve.append(c.tss)
            lines.append(f"  {th:>4.1f} {tp:>5} {fp:>6} {fn:>5} {c.pod:>6.3f} "
                         f"{c.far:>6.3f} {c.pofd:>7.4f} {c.tss:>7.4f} {c.hss:>7.4f}")
            if c.tss > best_tss:
                best_tss, best_th = c.tss, th
        curves[det] = curve

        # per-class POD at the chosen threshold
        det_peaks = np.array(sorted(detpeaks[det][best_th]), dtype=np.int64)
        _, _, _, _, cat_matched = match_events(det_peaks, cat, TOL_S)
        ranks = np.array(cat_rank[det])
        per_class = {}
        for L, rk in [("B", 1), ("C", 2), ("M", 3), ("X", 4)]:
            sel = ranks == rk
            n = int(sel.sum())
            hit = int(cat_matched[sel].sum()) if n else 0
            per_class[L] = (hit, n)
        chosen[det] = {"threshold": best_th, "tss": best_tss,
                       "per_class_pod": {k: v for k, v in per_class.items()}}
        lines.append(f"  --> CHOSEN threshold = {best_th} sigma (TSS={best_tss:.4f})")
        lines.append("      per-class recall at chosen: " +
                     "  ".join(f"{L}:{h}/{n}" for L, (h, n) in per_class.items()))

    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {d: {"threshold": chosen[d]["threshold"], "tss": chosen[d]["tss"]}
         for d in DETECTORS}, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {OUT_TXT}\nWrote {OUT_JSON}")

    # TSS curves plot
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for det in DETECTORS:
        ax.plot(THRESHOLDS, curves[det], marker="o", label=det)
        bt = chosen[det]["threshold"]
        bi = THRESHOLDS.index(bt)
        ax.scatter([bt], [curves[det][bi]], s=140, facecolors="none",
                   edgecolors="black", zorder=5)
    ax.set_xlabel("threshold (sigma)")
    ax.set_ylabel("TSS vs SWPC")
    ax.set_title("GATE 2 - TSS vs threshold (circled = chosen per detector)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=140)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

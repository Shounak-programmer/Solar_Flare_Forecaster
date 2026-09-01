"""STAGE 6 - final evaluation vs baselines + metrics report.

Per-bin nowcast scoring of the master catalogue against SWPC on a 6-min in-GTI
grid, with climatology and persistence baselines on the same bins. Writes
data/processed/reports/detection_metrics.txt and prints the GATE 6 block.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import DETECTORS, LBL_DIR
from src.detection.evaluation import (
    binary_contingency, climatology_contingency, persistence_prediction,
)
from src.detection.fusion import member_match_mask
from src.detection.matching import match_events

PROC = PROJECT_ROOT / "data" / "processed"
DET_DIR = PROC / "detections"
REPORT = PROC / "reports" / "detection_metrics.txt"
BIN_S = 360
TOL_S = 180
CLASS_RANK = {"B": 1, "C": 2, "M": 3, "X": 4}


def build_bin_series():
    """Per-bin observed (SWPC) and master-predicted arrays on the in-GTI grid."""
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    gti_cols = [c for _, c in DETECTORS.values()]

    swpc = pd.read_parquet(PROC / "flares_swpc.parquet").dropna(subset=["peak_utc"]).copy()
    swpc["day"] = swpc["peak_utc"].dt.strftime("%Y%m%d")
    swpc["u"] = swpc["peak_utc"].astype("int64") // 10**9
    swpc_by_day = {d: g["u"].to_numpy() for d, g in swpc.groupby("day")}
    swpc_cls_by_day = {d: g["goes_class_letter"].to_numpy() for d, g in swpc.groupby("day")}

    master = pd.read_parquet(DET_DIR / "master_flare_catalog.parquet")
    master["day"] = master["master_peak_utc"].dt.strftime("%Y%m%d")
    mpk_by_day = {d: np.concatenate(g["member_peaks_unix"].to_list())
                  for d, g in master.groupby("day")}

    obs_list, pred_list, seg_list = [], [], []
    # also accumulate per-class observed flare detection (member-aware, event)
    seg_id = 0
    nbins_per_day = 86400 // BIN_S
    for d in days:
        df = pd.read_parquet(LBL_DIR / f"{d}.parquet", columns=gti_cols)
        union = np.zeros(len(df), dtype=bool)
        for gc in gti_cols:
            union |= df[gc].to_numpy(bool)
        t0 = pd.Timestamp(f"{d[:4]}-{d[4:6]}-{d[6:]}", tz="UTC").value // 10**9
        # bin-level in-GTI fraction
        ug = union[: nbins_per_day * BIN_S].reshape(nbins_per_day, BIN_S)
        valid = ug.mean(axis=1) > 0.5
        if not valid.any():
            continue
        obs = np.zeros(nbins_per_day, dtype=bool)
        pred = np.zeros(nbins_per_day, dtype=bool)
        if d in swpc_by_day:
            b = ((swpc_by_day[d] - t0) // BIN_S).astype(int)
            b = b[(b >= 0) & (b < nbins_per_day)]
            obs[b] = True
        if d in mpk_by_day:
            b = ((mpk_by_day[d] - t0) // BIN_S).astype(int)
            b = b[(b >= 0) & (b < nbins_per_day)]
            pred[b] = True
        # contiguous-valid-bin segments for persistence
        seg = np.full(nbins_per_day, -1, dtype=np.int64)
        cur = -1
        prev_valid = False
        for i in range(nbins_per_day):
            if valid[i]:
                if not prev_valid:
                    cur = seg_id
                    seg_id += 1
                seg[i] = cur
            prev_valid = valid[i]
        keep = valid
        obs_list.append(obs[keep]); pred_list.append(pred[keep]); seg_list.append(seg[keep])

    return (np.concatenate(obs_list), np.concatenate(pred_list),
            np.concatenate(seg_list))


def main() -> int:
    print("Building per-bin nowcast series (6-min in-GTI bins) ...")
    obs, master_pred, seg = build_bin_series()
    n = obs.size

    master_c = binary_contingency(obs, master_pred)
    pers_c = binary_contingency(obs, persistence_prediction(obs, seg, 1))
    pers5_c = binary_contingency(obs, persistence_prediction(obs, seg, 5))
    clim_c = climatology_contingency(obs)

    # event-level master metrics (from GATE 4, member-aware) for the headline catalog
    eval_txt = (PROC / "reports" / "master_catalog_eval.txt").read_text(encoding="utf-8")

    # QPP regime tiers
    qpp = pd.read_parquet(DET_DIR / "qpp_catalog.parquet")
    regime_flares = qpp.drop_duplicates("master_peak_utc")["regime"].value_counts().to_dict()

    L = []
    L.append("STAGE 6 - DETECTION METRICS vs BASELINES")
    L.append("=" * 70)
    L.append(f"per-bin nowcast grid: {BIN_S}s bins, in-GTI only, N={n} bins")
    L.append(f"base rate (flare bins): {obs.mean():.5f}  ({int(obs.sum())} positive bins)")
    L.append("")
    L.append(f"{'method':14s} {'POD':>7} {'FAR':>7} {'TSS':>8} {'HSS':>8}")
    for name, c in [("master", master_c), ("persistence-1bin", pers_c),
                    ("persistence-30min", pers5_c), ("climatology", clim_c)]:
        L.append(f"{name:18s} {c.pod:>7.3f} {c.far:>7.3f} {c.tss:>8.4f} {c.hss:>8.4f}")
    L.append("")
    best_pers_tss = max(pers_c.tss, pers5_c.tss)
    beats_pers = master_c.tss > best_pers_tss
    beats_clim = master_c.tss > clim_c.tss
    L.append(f"master TSS ({master_c.tss:.4f}) beats best persistence ({best_pers_tss:.4f}): "
             f"{'YES' if beats_pers else 'NO'} (+{master_c.tss-best_pers_tss:.4f})")
    L.append(f"master TSS ({master_c.tss:.4f}) beats climatology ({clim_c.tss:.4f}): "
             f"{'YES' if beats_clim else 'NO'} (+{master_c.tss-clim_c.tss:.4f})")
    L.append(f">>> BEATS BOTH BASELINES: {'YES' if (beats_pers and beats_clim) else 'NO'}")
    L.append("")
    L.append("FRAMING (read before citing): this is NOWCASTING / DETECTION skill,")
    L.append("not forecasting. The master detects CONCURRENT flares from live X-ray")
    L.append("data and beats persistence + climatology at that task (the correct")
    L.append("floor). It does NOT claim to beat an operational FORECASTER -- the")
    L.append("master sees the present, a forecaster predicts the future. The")
    L.append("like-for-like Camporeale (2025) comparison vs the NOAA operational")
    L.append("forecast belongs to Phase 4 forecasting, not here.")
    L.append("")
    L.append("QPP catalogue regime tiers (distinct flares):")
    for r in ("classic", "intermediate", "short"):
        L.append(f"  {r:13s}: {regime_flares.get(r, 0)}")
    L.append("")
    L.append("Event-level master metrics (member-aware, from GATE 4):")
    for line in eval_txt.splitlines():
        if any(k in line for k in ("MASTER POD", "best single", "per-class", "B:", "C:", "M:", "X:",
                                   "CONFIRMED", "SUB-THRESHOLD", "CANDIDATE", "catalog-aware", "strict",
                                   "POD=")):
            L.append("  " + line.strip())

    REPORT.write_text("\n".join(L), encoding="utf-8")

    # ── machine-readable sidecar for the dashboard (no hand-entered numbers) ──
    import json
    import re

    def _ev(txt):
        """Parse the event-level master block from master_catalog_eval.txt into
        a structured dict (the same numbers cited in the report, never re-typed)."""
        out = {}
        m = re.search(r"MASTER POD = ([\d.]+)", txt)
        if m:
            out["master_pod"] = float(m.group(1))
        m = re.search(r"best single detector.*?= ([\d.]+)", txt)
        if m:
            out["best_single_pod"] = float(m.group(1))
        pc = {}
        for lab in ("B", "C", "M", "X"):
            mm = re.search(rf"\n\s*{lab}: (\d+)/(\d+)", txt)
            if mm:
                pc[lab] = [int(mm.group(1)), int(mm.group(2))]
        out["per_class"] = pc
        for key, tag in (("catalog_aware", "catalog-aware"), ("strict", "strict")):
            mm = re.search(tag + r".*?\n\s*POD=([\d.]+) FAR=([\d.]+) TSS=([\d.]+) HSS=([\d.]+)", txt, re.S)
            if mm:
                out[key] = dict(pod=float(mm.group(1)), far=float(mm.group(2)),
                                tss=float(mm.group(3)), hss=float(mm.group(4)))
        for key, tag in (("confirmed", "CONFIRMED"), ("sub_threshold", "SUB-THRESHOLD"),
                         ("candidate_novel", "CANDIDATE NOVEL")):
            mm = re.search(tag + r".*?(\d+)\s+\(([\d.]+)%\)", txt)
            if mm:
                out[key] = [int(mm.group(1)), float(mm.group(2))]
        return out

    ev = _ev(eval_txt)
    nowcast = {name: dict(pod=round(c.pod, 4), far=round(c.far, 4),
                          tss=round(c.tss, 4), hss=round(c.hss, 4))
               for name, c in (("master", master_c), ("persistence_1bin", pers_c),
                               ("persistence_30min", pers5_c), ("climatology", clim_c))}
    detection_json = {
        "nowcast_grid": {"bin_s": BIN_S, "n_bins": int(n), "base_rate": round(float(obs.mean()), 5)},
        "nowcast": nowcast,
        "event_level": ev,
        "qpp_regime_flares": {r: int(regime_flares.get(r, 0)) for r in ("classic", "intermediate", "short")},
        "framing": "NOWCASTING / DETECTION skill (concurrent), not forecasting.",
    }
    (REPORT.parent / "detection_metrics.json").write_text(json.dumps(detection_json, indent=2), encoding="utf-8")
    print("\n".join(L))
    print(f"\nWrote {REPORT} and detection_metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

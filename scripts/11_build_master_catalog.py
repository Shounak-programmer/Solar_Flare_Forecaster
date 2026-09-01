"""STAGE 4 — fuse the 5 detector catalogs into a master flare catalog and run
the 3-way evaluation (CONFIRMED / SUB-THRESHOLD / CANDIDATE NOVEL).

Outputs:
  data/processed/detections/master_flare_catalog.parquet
  data/processed/reports/master_catalog_eval.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import DETECTORS, LBL_DIR
from src.detection.fusion import fuse_detections, member_match_mask
from src.detection.matching import Contingency, match_events, negative_opportunities

DET_DIR = PROJECT_ROOT / "data" / "processed" / "detections"
REPORT = PROJECT_ROOT / "data" / "processed" / "reports" / "master_catalog_eval.txt"
MASTER_PATH = DET_DIR / "master_flare_catalog.parquet"
TOL_S = 180
BIN_S = 360
CLASS_RANK = {"B": 1, "C": 2, "M": 3, "X": 4}
SINGLE_BEST_POD = 0.851   # SoLEXS single-detector POD from GATE 3


def load_all_detections() -> pd.DataFrame:
    frames = []
    for det in DETECTORS:
        c = pd.read_parquet(DET_DIR / f"{det}_detections.parquet")
        if not len(c):
            continue
        c = c.copy()
        c["peak_unix"] = c["peak_utc"].astype("int64") // 10**9
        c["start_unix"] = c["start_utc"].astype("int64") // 10**9
        c["end_unix"] = c["end_utc"].astype("int64") // 10**9
        frames.append(c[["detector", "peak_unix", "start_unix", "end_unix",
                         "max_significance", "peak_rate"]])
    return pd.concat(frames, ignore_index=True)


def union_gti_for_flares(flares: pd.DataFrame):
    """For each SWPC flare, is it observable by >=1 detector (union GTI)?
    Also returns total union-GTI seconds across all days (for neg-opportunities)."""
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    gti_cols = [c for _, c in DETECTORS.values()]
    flares = flares.copy()
    flares["day"] = flares["peak_utc"].dt.strftime("%Y%m%d")
    flares["peak_unix"] = flares["peak_utc"].astype("int64") // 10**9
    observable = np.zeros(len(flares), dtype=bool)
    flares = flares.reset_index(drop=True)
    by_day = {d: idx.tolist() for d, idx in flares.groupby("day").groups.items()}
    union_seconds = 0
    for d in days:
        df = pd.read_parquet(LBL_DIR / f"{d}.parquet", columns=["utc"] + gti_cols)
        union = np.zeros(len(df), dtype=bool)
        for gc in gti_cols:
            union |= df[gc].to_numpy(bool)
        union_seconds += int(union.sum())
        if d in by_day:
            t0u = df["utc"].iloc[0].value // 10**9
            for ridx in by_day[d]:
                sec = int(flares.at[ridx, "peak_unix"] - t0u)
                if 0 <= sec < len(union) and union[sec]:
                    observable[ridx] = True
    return observable, union_seconds


def main() -> int:
    print("Loading 5 detector catalogs and fusing ...")
    det = load_all_detections()
    master = fuse_detections(det)
    DET_DIR.mkdir(parents=True, exist_ok=True)
    master.to_parquet(MASTER_PATH, index=False)
    print(f"  master flares: {len(master)}  (from {len(det)} single-detector detections)")

    # ---- reference catalogues ----
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    day_set = set(days)
    swpc = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet")
    swpc = swpc.dropna(subset=["peak_utc"]).copy()
    swpc["day"] = swpc["peak_utc"].dt.strftime("%Y%m%d")
    swpc = swpc[swpc["day"].isin(day_set)].reset_index(drop=True)
    swpc["peak_unix"] = swpc["peak_utc"].astype("int64") // 10**9

    hek = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_hek.parquet")
    hek = hek.dropna(subset=["peak_utc"]).copy()
    hek["day"] = hek["peak_utc"].dt.strftime("%Y%m%d")
    hek = hek[hek["day"].isin(day_set)]
    hek_unix = np.sort((hek["peak_utc"].astype("int64") // 10**9).to_numpy())

    # Pooled member peaks = every single-detector detection (member-aware recall).
    member_peaks_all = np.sort(det["peak_unix"].to_numpy(np.int64))

    # ---- master recall vs SWPC (observable flares only, member-aware) ----
    print("Computing union-GTI observability ...")
    observable, union_seconds = union_gti_for_flares(swpc)
    swpc_obs = swpc[observable].reset_index(drop=True)
    swpc_obs = swpc_obs.sort_values("peak_unix").reset_index(drop=True)
    swpc_obs_unix = swpc_obs["peak_unix"].to_numpy(np.int64)

    # A SWPC flare is recalled if ANY detection (member) is within tol.
    tp, _, fn, _, swpc_matched = match_events(member_peaks_all, swpc_obs_unix, TOL_S)
    pod = tp / (tp + fn) if (tp + fn) else 0.0

    # best single detector on the SAME common (union) denominator
    best_single_pod, best_single_name = 0.0, ""
    for dn in DETECTORS:
        c = pd.read_parquet(DET_DIR / f"{dn}_detections.parquet")
        dpk = np.sort((c["peak_utc"].astype("int64") // 10**9).to_numpy())
        tpd, _, fnd, _, _ = match_events(dpk, swpc_obs_unix, TOL_S)
        p = tpd / (tpd + fnd) if (tpd + fnd) else 0.0
        if p > best_single_pod:
            best_single_pod, best_single_name = p, dn

    # ---- 3-way classification of every master flare (member-aware) ----
    m_in_swpc = member_match_mask(master, swpc_obs_unix, TOL_S)
    m_in_hek = member_match_mask(master, hek_unix, TOL_S)
    confirmed = m_in_swpc
    subthresh = (~m_in_swpc) & m_in_hek
    candidate = (~m_in_swpc) & (~m_in_hek)
    n_conf, n_sub, n_cand = int(confirmed.sum()), int(subthresh.sum()), int(candidate.sum())

    nd = master["n_detectors"].to_numpy()
    cand_multi = int((candidate & (nd >= 2)).sum())
    cand_single = int((candidate & (nd == 1)).sum())

    # ---- contingencies ----
    neg = negative_opportunities(union_seconds, len(swpc_obs_unix), BIN_S)
    fp_all = n_sub + n_cand          # strict: every non-SWPC master = FP
    strict = Contingency(tp=tp, fp=fp_all, fn=fn, tn=max(0, neg - fp_all))
    cataware = Contingency(tp=tp, fp=n_cand, fn=fn, tn=max(0, neg - n_cand))

    # ---- per-class master recall (member-aware) ----
    swpc_obs["rank"] = swpc_obs["goes_class_letter"].map(CLASS_RANK).fillna(0).astype(int)
    _, _, _, _, cat_matched = match_events(member_peaks_all, swpc_obs_unix, TOL_S)
    per_class = {}
    ranks = swpc_obs["rank"].to_numpy()
    for L, rk in CLASS_RANK.items():
        sel = ranks == rk
        nflare = int(sel.sum())
        hit = int(cat_matched[sel].sum()) if nflare else 0
        per_class[L] = (hit, nflare)

    # ---- report ----
    L = []
    L.append("STAGE 4 - MASTER CATALOG + 3-WAY EVALUATION")
    L.append("=" * 70)
    L.append(f"single-detector detections fused: {len(det)}")
    L.append(f"master physical flares:           {len(master)}")
    L.append(f"  n_detectors distribution: " +
             "  ".join(f"{k}:{int((nd==k).sum())}" for k in range(1, 6)))
    span = (master['master_end_unix'] - master['master_start_unix'])
    peakspan = master['member_peaks_unix'].apply(lambda x: max(x) - min(x))
    L.append(f"  PEAK span (chaining diagnostic): median={int(np.median(peakspan))}s "
             f"max={int(peakspan.max())}s  (cap=240s, violations={int((peakspan>240).sum())})")
    L.append(f"  start-to-end span (flare duration): median={int(np.median(span))}s "
             f"max={int(span.max())}s ({span.max()/60:.1f} min, single long-decay flares)")
    L.append(f"  n_members: max={int(master['n_members'].max())} mean={master['n_members'].mean():.2f}")
    L.append("")
    L.append("MASTER RECALL vs SWPC (observable flares, member-aware, common denom)")
    L.append(f"  observable SWPC flares (union-GTI): {len(swpc_obs_unix)}")
    L.append(f"  TP={tp}  FN={fn}")
    L.append(f"  >>> MASTER POD = {pod:.3f}")
    L.append(f"  >>> best single detector ({best_single_name}, same denom) = {best_single_pod:.3f}")
    delta = pod - best_single_pod
    L.append(f"  >>> {'PASS' if pod > best_single_pod else 'FAIL'}: master "
             f"{'exceeds' if pod>best_single_pod else 'does NOT exceed'} best single "
             f"detector by {delta:+.3f}")
    L.append("")
    L.append("  per-class master recall:")
    for Lc, (h, nn) in per_class.items():
        L.append(f"    {Lc}: {h}/{nn}" + (f" ({100*h/nn:.0f}%)" if nn else ""))
    L.append("")
    L.append("SKILL SCORES")
    L.append(f"  catalog-aware (candidate-novel = FP, per Sarwade):")
    L.append(f"    POD={cataware.pod:.3f} FAR={cataware.far:.3f} TSS={cataware.tss:.3f} HSS={cataware.hss:.3f}")
    L.append(f"  strict (all non-SWPC = FP):")
    L.append(f"    POD={strict.pod:.3f} FAR={strict.far:.3f} TSS={strict.tss:.3f} HSS={strict.hss:.3f}")
    L.append("")
    L.append("3-WAY BREAKDOWN of master flares")
    L.append(f"  CONFIRMED (in SWPC):            {n_conf}  ({100*n_conf/len(master):.1f}%)")
    L.append(f"  SUB-THRESHOLD (HEK only):       {n_sub}  ({100*n_sub/len(master):.1f}%)")
    L.append(f"  CANDIDATE NOVEL (neither):      {n_cand}  ({100*n_cand/len(master):.1f}%)")
    L.append(f"    candidate-novel multi-detector (n>=2): {cand_multi}  "
             f"({100*cand_multi/max(n_cand,1):.1f}% of candidates)")
    L.append(f"    candidate-novel single-detector:       {cand_single}  "
             f"({100*cand_single/max(n_cand,1):.1f}% of candidates)")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\nWrote {MASTER_PATH}\nWrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

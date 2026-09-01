"""STAGE 5 — DEFENSIBILITY UPGRADES (new analysis; changes NO frozen results).

Reads existing artifacts (saved test predictions, forecast features, detection
catalogs) and produces four defensibility outputs:

  A. Block-bootstrap 95% CIs over DAYS (respects autocorrelation; ~2000 resamples)
     for forecast TSS(15/30/60), ECE, Brier, FAR and detection catalog-aware TSS.
  B. Lead-time distribution for every TEST M/X flare (first Watch / Warning
     crossing before peak; "no warning" vs "no coverage" distinguished).
  C. Fusion ablation: SAME XGBoost config retrained on SoLEXS-only /
     HEL1OS-only / combined features (new comparison; combined stays frozen).
  D. Cost-loss relative value curve V(C/L) at the Watch and Warning operating
     points (15-min horizon), saved as SVG.

Every section starts by REPRODUCING the frozen headline number from artifacts
and fails loudly on drift. Outputs: data/processed/reports/defensibility_*.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.calibration import (
    brier_score, expected_calibration_error, fit_isotonic,
)
from src.forecasting.evaluation import best_threshold, binary_metrics
from src.detection.matching import match_events

PROC = PROJECT_ROOT / "data" / "processed"
FF_DIR = PROC / "forecast_features"
FCAST = PROC / "forecasts"
REPORTS = PROC / "reports"
LBL_DIR = PROC / "labeled_seconds"
DET_DIR = PROC / "detections"

TRAIN, VAL, TEST = ("20240701", "20250630"), ("20250701", "20251231"), ("20260101", "20260613")
HORIZONS = ["y_15min", "y_30min", "y_60min"]
N_BOOT = 2000
RNG = np.random.default_rng(20260702)
TOL_S, BIN_S = 180, 360

# frozen references (fail loudly on drift)
FROZEN = dict(tss15=0.346, ece15=0.0061, brier15=0.0702, far15=0.801,
              det_tss=0.840, watch=0.0961, warning=0.2006)


def _check(name: str, got: float, want: float, tol: float):
    if abs(got - want) > tol:
        raise SystemExit(f"FROZEN-NUMBER DRIFT: {name} reproduced as {got:.4f}, "
                         f"expected {want} (tol {tol}) — investigate before proceeding.")
    print(f"  reproduced {name} = {got:.4f} (frozen {want}) OK")


def day_of_unix(u: np.ndarray) -> np.ndarray:
    return pd.to_datetime(u, unit="s", utc=True).strftime("%Y%m%d").to_numpy()


def pctl_ci(vals: np.ndarray) -> tuple[float, float]:
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


# ═════════════════════════════════════════════════════════════════════════════
# A. BLOCK BOOTSTRAP CIs
# ═════════════════════════════════════════════════════════════════════════════
def load_labels_only() -> pd.DataFrame:
    cols = ["day", "in_gti_any", "y_15min", "y_30min", "y_60min"]
    frames = [pd.read_parquet(f, columns=cols) for f in sorted(FF_DIR.glob("*.parquet"))]
    df = pd.concat(frames, ignore_index=True)
    return df[df["in_gti_any"]].reset_index(drop=True)


def bootstrap_metric(day_ids: np.ndarray, uniq_days: np.ndarray, fn, n_boot=N_BOOT):
    """Resample DAYS with replacement; fn(row_mask_indices) -> metric value."""
    day_to_rows = {d: np.where(day_ids == d)[0] for d in uniq_days}
    out = np.empty(n_boot)
    for b in range(n_boot):
        pick = RNG.choice(uniq_days, size=uniq_days.size, replace=True)
        idx = np.concatenate([day_to_rows[d] for d in pick])
        out[b] = fn(idx)
    return out


def section_a(lines: list[str], js: dict):
    print("\n[A] Block-bootstrap CIs over test days ...")
    z = np.load(FCAST / "calibrated_test_predictions.npz")
    p15, y15, thr15, u = z["p15_cal"], z["y15"], float(z["thr15"]), z["utc_unix"]
    days = day_of_unix(u)
    uniq = np.unique(days)
    print(f"  test rows={len(y15)}  test days={len(uniq)}")

    # reproduce frozen point estimates from the saved predictions
    m = binary_metrics(y15, p15 >= thr15)
    _check("forecast TSS 15-min (calibrated)", m["tss"], FROZEN["tss15"], 0.0015)
    _check("FAR 15-min", m["far"], FROZEN["far15"], 0.0015)
    _check("ECE 15-min", expected_calibration_error(y15, p15), FROZEN["ece15"], 0.0015)
    _check("Brier 15-min", brier_score(y15, p15), FROZEN["brier15"], 0.0015)

    # 30/60-min: saved UNCALIBRATED test probs + threshold re-tuned on val probs
    # (isotonic is monotonic -> identical classifications; frozen table confirms)
    zb = np.load(FCAST / "baseline_test_predictions.npz", allow_pickle=True)
    lbl = load_labels_only()
    d_all = lbl["day"].to_numpy()
    va_lbl = lbl[(d_all >= VAL[0]) & (d_all <= VAL[1])]
    thr_h, p_h, y_h = {}, {}, {}
    for h in HORIZONS[1:]:
        thr_h[h], _ = best_threshold(va_lbl[h].to_numpy(), zb[f"xgb_valprob_{h}"])
        p_h[h], y_h[h] = zb[f"xgb_prob_{h}"], zb[f"y_true_{h}"]
        tss_pt = binary_metrics(y_h[h], p_h[h] >= thr_h[h])["tss"]
        print(f"  point TSS {h} (uncal @val-thr) = {tss_pt:.4f}")

    boots = {}
    boots["tss_15min"] = bootstrap_metric(days, uniq,
        lambda i: binary_metrics(y15[i], p15[i] >= thr15)["tss"])
    boots["far_15min"] = bootstrap_metric(days, uniq,
        lambda i: binary_metrics(y15[i], p15[i] >= thr15)["far"])
    boots["ece_15min"] = bootstrap_metric(days, uniq,
        lambda i: expected_calibration_error(y15[i], p15[i]))
    boots["brier_15min"] = bootstrap_metric(days, uniq,
        lambda i: brier_score(y15[i], p15[i]))
    for h in HORIZONS[1:]:
        boots[f"tss_{h[2:]}"] = bootstrap_metric(days, uniq,
            lambda i, h=h: binary_metrics(y_h[h][i], p_h[h][i] >= thr_h[h])["tss"])

    # ---- detection catalog-aware TSS: per-day contingency components ----
    print("  building per-day detection components (620-day union GTI scan) ...")
    det_frames = [pd.read_parquet(DET_DIR / f"{dn}_detections.parquet")
                  for dn in ("solexs_sdd2", "hel1os_cdte1", "hel1os_cdte2",
                             "hel1os_czt1", "hel1os_czt2")]
    det = pd.concat(det_frames, ignore_index=True)
    member_peaks = np.sort((det["peak_utc"].astype("int64") // 10**9).to_numpy(np.int64))

    lbl_days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    swpc = pd.read_parquet(PROC / "flares_swpc.parquet").dropna(subset=["peak_utc"]).copy()
    swpc["day"] = swpc["peak_utc"].dt.strftime("%Y%m%d")
    swpc = swpc[swpc["day"].isin(set(lbl_days))].reset_index(drop=True)
    swpc["peak_unix"] = swpc["peak_utc"].astype("int64") // 10**9

    hek = pd.read_parquet(PROC / "flares_hek.parquet").dropna(subset=["peak_utc"]).copy()
    hek["day"] = hek["peak_utc"].dt.strftime("%Y%m%d")
    hek = hek[hek["day"].isin(set(lbl_days))]
    hek_unix = np.sort((hek["peak_utc"].astype("int64") // 10**9).to_numpy(np.int64))

    from scripts.detect_helpers import DETECTORS as DET_MAP
    gti_cols = [c for _, c in DET_MAP.values()]
    observable = np.zeros(len(swpc), dtype=bool)
    union_by_day = {}
    by_day = {d: idx.tolist() for d, idx in swpc.groupby("day").groups.items()}
    for d in lbl_days:
        df = pd.read_parquet(LBL_DIR / f"{d}.parquet", columns=["utc"] + gti_cols)
        union = np.zeros(len(df), dtype=bool)
        for gc in gti_cols:
            union |= df[gc].to_numpy(bool)
        union_by_day[d] = int(union.sum())
        if d in by_day:
            t0u = df["utc"].iloc[0].value // 10**9
            for ridx in by_day[d]:
                sec = int(swpc.at[ridx, "peak_unix"] - t0u)
                if 0 <= sec < len(union) and union[sec]:
                    observable[ridx] = True
    swpc_obs = swpc[observable].sort_values("peak_unix").reset_index(drop=True)
    obs_unix = swpc_obs["peak_unix"].to_numpy(np.int64)
    tp_tot, _, fn_tot, _, matched = match_events(member_peaks, obs_unix, TOL_S)

    from src.detection.fusion import member_match_mask
    master = pd.read_parquet(DET_DIR / "master_flare_catalog.parquet")
    m_in_swpc = member_match_mask(master, obs_unix, TOL_S)
    m_in_hek = member_match_mask(master, hek_unix, TOL_S)
    candidate = (~m_in_swpc) & (~m_in_hek)
    master_day = pd.to_datetime(master["master_peak_unix"], unit="s", utc=True).dt.strftime("%Y%m%d").to_numpy()

    # per-day components
    comp = {}
    obs_day = swpc_obs["day"].to_numpy()
    for d in lbl_days:
        sel = obs_day == d
        comp[d] = dict(tp=int(matched[sel].sum()), fn=int((sel & ~matched).sum()),
                       nobs=int(sel.sum()),
                       fp=int(candidate[master_day == d].sum()),
                       u=union_by_day[d])
    # exact reproduction check on the full-set contingency
    U = sum(c["u"] for c in comp.values()); NOBS = sum(c["nobs"] for c in comp.values())
    FP = sum(c["fp"] for c in comp.values())
    neg = max(0, U // BIN_S - NOBS); tn = max(0, neg - FP)
    pod = tp_tot / (tp_tot + fn_tot); tss_det = pod - FP / (FP + tn)
    _check("detection catalog-aware TSS", tss_det, FROZEN["det_tss"], 0.0015)

    darr = np.array(lbl_days)
    tpv = np.array([comp[d]["tp"] for d in darr]); fnv = np.array([comp[d]["fn"] for d in darr])
    fpv = np.array([comp[d]["fp"] for d in darr]); uv = np.array([comp[d]["u"] for d in darr])
    nov = np.array([comp[d]["nobs"] for d in darr])
    det_boot = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = RNG.integers(0, len(darr), size=len(darr))
        tp_, fn_, fp_ = tpv[pick].sum(), fnv[pick].sum(), fpv[pick].sum()
        neg_ = max(0, uv[pick].sum() // BIN_S - nov[pick].sum())
        tn_ = max(0, neg_ - fp_)
        pod_ = tp_ / (tp_ + fn_) if tp_ + fn_ else 0.0
        det_boot[b] = pod_ - (fp_ / (fp_ + tn_) if fp_ + tn_ else 0.0)
    boots["detection_tss_catalog_aware"] = det_boot

    lines.append(f"A. BLOCK-BOOTSTRAP 95% CIs (resampling DAYS, {N_BOOT} resamples)")
    lines.append(f"   (respects within-day autocorrelation; forecast = {len(uniq)} test days;")
    lines.append(f"    detection = {len(darr)} catalog days)")
    point = dict(tss_15min=m["tss"], far_15min=m["far"],
                 ece_15min=expected_calibration_error(y15, p15),
                 brier_15min=brier_score(y15, p15),
                 tss_30min=binary_metrics(y_h["y_30min"], p_h["y_30min"] >= thr_h["y_30min"])["tss"],
                 tss_60min=binary_metrics(y_h["y_60min"], p_h["y_60min"] >= thr_h["y_60min"])["tss"],
                 detection_tss_catalog_aware=tss_det)
    order = ["tss_15min", "tss_30min", "tss_60min", "ece_15min", "brier_15min",
             "far_15min", "detection_tss_catalog_aware"]
    js["ci"] = {}
    for k in order:
        lo, hi = pctl_ci(boots[k])
        lines.append(f"   {k:32s} point={point[k]:.4f}   95% CI [{lo:.4f}, {hi:.4f}]")
        js["ci"][k] = dict(point=round(point[k], 4), lo=round(lo, 4), hi=round(hi, 4))
    lines.append("   NOTE: 30/60-min CIs use the saved UNCALIBRATED test probabilities at")
    lines.append("   the val-tuned threshold (isotonic is monotonic; frozen table equal).")
    lines.append("")


# ═════════════════════════════════════════════════════════════════════════════
# B. LEAD-TIME DISTRIBUTION (TEST M/X flares)
# ═════════════════════════════════════════════════════════════════════════════
def section_b(lines: list[str], js: dict):
    print("\n[B] Lead-time distribution for TEST M/X flares ...")
    z = np.load(FCAST / "calibrated_test_predictions.npz")
    p15, u = z["p15_cal"], z["utc_unix"]
    watch, warning = FROZEN["watch"], FROZEN["warning"]
    thr15 = float(z["thr15"])
    if abs(thr15 - watch) > 5e-4:
        print(f"  note: npz thr15={thr15:.4f} vs summary watch={watch} — using npz value")
        watch = thr15

    swpc = pd.read_parquet(PROC / "flares_swpc.parquet").dropna(subset=["peak_utc"]).copy()
    swpc["day"] = swpc["peak_utc"].dt.strftime("%Y%m%d")
    mx = swpc[(swpc["day"] >= TEST[0]) & (swpc["day"] <= TEST[1])
              & swpc["goes_class_letter"].isin(["M", "X"])].copy()
    mx["peak_unix"] = mx["peak_utc"].astype("int64") // 10**9
    print(f"  test M/X flares: {len(mx)} (M={int((mx.goes_class_letter=='M').sum())}, "
          f"X={int((mx.goes_class_letter=='X').sum())})")

    SEARCH_S, COV_S = 3600, 900          # search 60 min pre-peak; coverage window 15 min
    rows = []
    for _, fr in mx.iterrows():
        pk = int(fr["peak_unix"])
        cov = (u >= pk - COV_S) & (u <= pk)              # frozen all-clear convention
        win = (u >= pk - SEARCH_S) & (u <= pk)
        rec = dict(peak_utc=str(fr["peak_utc"])[:16], goes_class=fr["goes_class"],
                   letter=fr["goes_class_letter"], coverage=bool(cov.any()))
        for name, thr in (("watch", watch), ("warning", warning)):
            lead = None
            if win.any():
                fire = win & (p15 >= thr)
                if fire.any():
                    lead = round((pk - int(u[np.argmax(fire)])) / 60.0, 1)
            rec[f"lead_{name}_min"] = lead
        rows.append(rec)
    lt = pd.DataFrame(rows)

    lines.append("B. LEAD-TIME DISTRIBUTION — TEST M/X flares (first threshold crossing")
    lines.append(f"   in [peak-60min, peak]; calibrated 15-min risk; Watch={watch:.4f},")
    lines.append(f"   Warning={warning:.4f}; 'no coverage' = no in-GTI rows in [peak-15min, peak]")
    lines.append("   and no earlier crossing. Leads are CAPPED at the 60-min search window —")
    lines.append("   median 60 means risk was already elevated >=1 h before peak (active periods).")
    js["leadtime"] = {}
    for name in ("watch", "warning"):
        col = f"lead_{name}_min"
        for letter in ("MX", "M", "X"):
            sub = lt if letter == "MX" else lt[lt.letter == letter]
            led = sub[col].dropna().astype(float)
            # categories: warned (crossed in search window) / no-warning (had
            # coverage, never crossed) / no-coverage (no rows in [peak-15m,peak]
            # AND never crossed earlier in the search window either)
            miss_mask = sub[col].isna()
            missed = int((miss_mask & sub["coverage"]).sum())
            no_cov = int((miss_mask & ~sub["coverage"]).sum())
            tag = f"{name.upper():8s} {letter:2s}"
            if len(led):
                q1, q3 = np.percentile(led, [25, 75])
                lines.append(f"   {tag}: warned {len(led)}/{len(sub)}  "
                             f"median={led.median():.0f} min  IQR=[{q1:.0f},{q3:.0f}]  "
                             f"range=[{led.min():.0f},{led.max():.0f}]  "
                             f"no-warning={missed}  no-coverage={no_cov}")
            else:
                lines.append(f"   {tag}: warned 0/{len(sub)}  no-warning={missed}  no-coverage={no_cov}")
            if letter == "MX":
                js["leadtime"][name] = dict(
                    n=len(sub), warned=int(len(led)),
                    median_min=float(led.median()) if len(led) else None,
                    iqr=[float(q1), float(q3)] if len(led) else None,
                    min=float(led.min()) if len(led) else None,
                    max=float(led.max()) if len(led) else None,
                    no_warning=missed, no_coverage=no_cov)
    # X-class event table (small, print all)
    lines.append("   X-class detail:")
    for _, r in lt[lt.letter == "X"].iterrows():
        lines.append(f"     {r.peak_utc} {r.goes_class:>5}  watch_lead="
                     f"{r.lead_watch_min if r.lead_watch_min is not None else '-':>5}  "
                     f"warning_lead={r.lead_warning_min if r.lead_warning_min is not None else '-':>5}  "
                     f"{'NO-COVERAGE' if not r.coverage else ''}")
    js["leadtime"]["x_detail"] = [
        {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
        for r in lt[lt.letter == "X"].to_dict("records")]
    lines.append("")


# ═════════════════════════════════════════════════════════════════════════════
# C. FUSION ABLATION (same config, SoLEXS-only / HEL1OS-only / combined)
# ═════════════════════════════════════════════════════════════════════════════
def section_c(lines: list[str], js: dict):
    import xgboost as xgb
    from src.forecasting.baselines import fit_neupert_k, neupert_residual
    from src.forecasting.features import feature_names

    print("\n[C] Fusion ablation (3 feature sets x 3 horizons, frozen config) ...")
    t0 = time.time()
    df = pd.concat([pd.read_parquet(f) for f in sorted(FF_DIR.glob("*.parquet"))],
                   ignore_index=True)
    df = df[df["in_gti_any"]].reset_index(drop=True)
    feats = feature_names(df)
    trm = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[trm, "hel1os_hard_rate"].to_numpy(),
                      df.loc[trm, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]

    context = [f for f in feats if f in ("f107_lag1", "sunspot_number_lag1", "ar_count_lag1")]
    solexs = [f for f in feats if f.startswith("solexs_") or f.startswith("soft_ddt")] + context
    hel1os = [f for f in feats if f.startswith("hel1os_") or f.startswith("qpp_")] + context
    sets = {"solexs_only": solexs, "hel1os_only": hel1os, "combined": feats}
    # cross-detector + fused-catalog features live ONLY in combined:
    excluded = sorted(set(feats) - set(solexs) - set(hel1os))

    d = df["day"].to_numpy()
    tr = df[(d >= TRAIN[0]) & (d <= TRAIN[1])]
    va = df[(d >= VAL[0]) & (d <= VAL[1])]
    te = df[(d >= TEST[0]) & (d <= TEST[1])]

    js["ablation"] = {"feature_counts": {k2: len(v) for k2, v in sets.items()},
                      "context_in_all": context, "combined_only": excluded, "tss": {}}
    res = {}
    for sname, cols in sets.items():
        for h in HORIZONS:
            ytr, yva, yte = tr[h].to_numpy(), va[h].to_numpy(), te[h].to_numpy()
            spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                                    eval_metric="aucpr", early_stopping_rounds=30,
                                    tree_method="hist", n_jobs=4)
            clf.fit(tr[cols], ytr, eval_set=[(va[cols], yva)], verbose=False)
            pva, pte = clf.predict_proba(va[cols])[:, 1], clf.predict_proba(te[cols])[:, 1]
            iso = fit_isotonic(pva, yva)
            thr, _ = best_threshold(yva, iso.transform(pva))
            res[(sname, h)] = binary_metrics(yte, iso.transform(pte) >= thr)["tss"]
            print(f"  {sname:12s} {h}: TSS={res[(sname,h)]:.4f}  ({time.time()-t0:.0f}s)")

    # combined must reproduce the frozen table (within retrain jitter)
    _check("ablation combined TSS 15-min", res[("combined", "y_15min")], FROZEN["tss15"], 0.02)

    lines.append("C. FUSION ABLATION — same XGBoost config + isotonic + val-tuned threshold")
    lines.append(f"   feature sets: solexs_only={len(solexs)}  hel1os_only={len(hel1os)}  "
                 f"combined={len(feats)} (frozen system of record)")
    lines.append(f"   shared context in all sets: {', '.join(context)}")
    lines.append(f"   combined-only (cross-detector / fused-catalog history): {', '.join(excluded)}")
    lines.append(f"   {'set':14s} {'15min':>8} {'30min':>8} {'60min':>8}")
    for sname in sets:
        row = f"   {sname:14s}"
        for h in HORIZONS:
            row += f" {res[(sname, h)]:>8.4f}"
        lines.append(row)
        js["ablation"]["tss"][sname] = {h: round(res[(sname, h)], 4) for h in HORIZONS}
    lines.append("   NOTE: new comparison table; the existing combined model and its frozen")
    lines.append("   numbers (0.346/0.229/0.205) remain the system of record.")
    lines.append("")


# ═════════════════════════════════════════════════════════════════════════════
# D. COST-LOSS RELATIVE VALUE CURVE (Richardson 2000)
# ═════════════════════════════════════════════════════════════════════════════
def section_d(lines: list[str], js: dict):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print("\n[D] Cost-loss relative value curves ...")
    z = np.load(FCAST / "calibrated_test_predictions.npz")
    p15, y15 = z["p15_cal"], z["y15"].astype(bool)
    s = float(y15.mean())
    ops = {"Watch (0.096)": FROZEN["watch"], "Warning (0.20)": FROZEN["warning"]}
    r = np.geomspace(0.01, 1.0, 300)

    fig, ax = plt.subplots(figsize=(8, 5.2), constrained_layout=True)
    colors = {"Watch (0.096)": "#e0a526", "Warning (0.20)": "#d35400"}
    js["value"] = dict(base_rate=round(s, 4), curves={})
    lines.append("D. COST-LOSS RELATIVE VALUE V(C/L) — Richardson (2000), 15-min horizon")
    lines.append(f"   base rate s={s:.4f} (15-min pre-flare windows, test)")
    for name, thr in ops.items():
        m = binary_metrics(y15, p15 >= thr)
        H, F = m["pod"], m["pofd"]
        e_clim = np.minimum(r, s)
        e_fc = F * r * (1 - s) + H * r * s + (1 - H) * s
        e_perf = s * r
        with np.errstate(divide="ignore", invalid="ignore"):
            V = (e_clim - e_fc) / (e_clim - e_perf)
        V = np.clip(V, -1, 1)
        vmax = float(np.nanmax(V))
        rng = r[V > 0]
        lines.append(f"   {name:16s} POD={H:.3f} POFD={F:.4f}  Vmax={vmax:.3f} "
                     f"at C/L={r[np.nanargmax(V)]:.3f}  V>0 for C/L in "
                     f"[{rng.min():.3f}, {rng.max():.3f}]" if rng.size else
                     f"   {name:16s} no positive-value range")
        js["value"]["curves"][name] = dict(
            pod=round(H, 4), pofd=round(F, 4), vmax=round(vmax, 4),
            cl_at_vmax=round(float(r[np.nanargmax(V)]), 4),
            v_positive_range=[round(float(rng.min()), 4), round(float(rng.max()), 4)] if rng.size else None)
        ax.plot(r, V, lw=2.4, color=colors[name], label=name)
    ax.axhline(0, color="#95a2b2", lw=1)
    ax.axvline(s, color="#1a3a5c", lw=1, ls="--", alpha=.6)
    ax.text(s * 1.05, 0.92, f"base rate s={s:.3f}", color="#1a3a5c", fontsize=9)
    ax.set_xscale("log"); ax.set_xlim(0.01, 1); ax.set_ylim(-0.05, 1)
    ax.set_xlabel("cost/loss ratio  C/L"); ax.set_ylabel("relative economic value  V")
    ax.set_title("Relative value of the 15-min flare forecast (test, calibrated)")
    ax.grid(alpha=.3); ax.legend()
    for ext in ("svg",):
        fig.savefig(REPORTS / f"defensibility_value.{ext}")
    plt.close(fig)
    lines.append(f"   plot: {REPORTS / 'defensibility_value.svg'}")
    lines.append("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="ci,leadtime,ablation,value")
    args = ap.parse_args()
    todo = set(args.only.split(","))

    REPORTS.mkdir(parents=True, exist_ok=True)
    sections = dict(ci=section_a, leadtime=section_b, ablation=section_c, value=section_d)
    for key in ("ci", "leadtime", "ablation", "value"):
        if key not in todo:
            continue
        lines = [f"DEFENSIBILITY — {key.upper()}  (generated {pd.Timestamp.utcnow():%Y-%m-%d %H:%M} UTC)",
                 "=" * 72]
        js = {}
        sections[key](lines, js)
        (REPORTS / f"defensibility_{key}.txt").write_text("\n".join(lines), encoding="utf-8")
        (REPORTS / f"defensibility_{key}.json").write_text(
            json.dumps(js, indent=1, allow_nan=False, default=str), encoding="utf-8")
        print("\n".join(lines))
        print(f"wrote {REPORTS / f'defensibility_{key}.txt'} (+.json)")


if __name__ == "__main__":
    main()

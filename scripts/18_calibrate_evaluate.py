"""STAGE 4d - isotonic calibration + final forecasting evaluation (GATE D).

XGBoost is the primary model (Gate C). Calibrate on validation, evaluate on
test; reliability before/after; quiet->X-class all-clear test; final metrics
vs baselines at all horizons. TSS is the headline (accuracy never reported).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.baselines import (
    climatology_probability, fit_neupert_k, neupert_residual, persistence_probability,
)
from src.forecasting.calibration import (
    brier_score, expected_calibration_error, fit_isotonic, reliability_curve,
)
from src.forecasting.evaluation import best_threshold, binary_metrics, per_class_recall
from src.forecasting.features import feature_names

FF_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"
REPORTS = PROJECT_ROOT / "data" / "processed" / "reports"
FCAST = PROJECT_ROOT / "data" / "processed" / "forecasts"
VALID = PROJECT_ROOT / "data" / "validation"
TRAIN, VAL, TEST = ("20240701", "20250630"), ("20250701", "20251231"), ("20260101", "20260613")
HORIZONS = ["y_15min", "y_30min", "y_60min"]


def main() -> int:
    t0 = time.time()
    for d in (REPORTS, FCAST, VALID):
        d.mkdir(parents=True, exist_ok=True)
    print("loading features ...", flush=True)
    df = pd.concat([pd.read_parquet(f) for f in sorted(FF_DIR.glob("*.parquet"))],
                   ignore_index=True)
    df = df[df["in_gti_any"]].reset_index(drop=True)
    feats = feature_names(df)
    trm = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[trm, "hel1os_hard_rate"].to_numpy(), df.loc[trm, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]

    d = df["day"].to_numpy()
    tr = df[(d >= TRAIN[0]) & (d <= TRAIN[1])]
    va = df[(d >= VAL[0]) & (d <= VAL[1])]
    te = df[(d >= TEST[0]) & (d <= TEST[1])].reset_index(drop=True)
    Xtr, Xva, Xte = tr[feats], va[feats], te[feats]

    lines = ["STAGE 4d - CALIBRATION + FINAL EVALUATION (XGBoost primary)", "=" * 72]
    lines.append(f"train {TRAIN[0]}..{TRAIN[1]} | val {VAL[0]}..{VAL[1]} | test {TEST[0]}..{TEST[1]}")
    lines.append(f"rows: train={len(tr)} val={len(va)} test={len(te)}")

    final = {}
    cal_p15_test = None
    thr15 = None
    for h in HORIZONS:
        ytr, yva, yte = tr[h].to_numpy(), va[h].to_numpy(), te[h].to_numpy()
        spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
        clf = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                                eval_metric="aucpr", early_stopping_rounds=30,
                                tree_method="hist", n_jobs=4)
        clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        pva = clf.predict_proba(Xva)[:, 1]; pte = clf.predict_proba(Xte)[:, 1]

        # isotonic calibration: fit on val, apply to test
        iso = fit_isotonic(pva, yva)
        pte_cal = iso.transform(pte); pva_cal = iso.transform(pva)
        thr, _ = best_threshold(yva, pva_cal)
        m_unc = binary_metrics(yte, pte >= best_threshold(yva, pva)[0])
        m_cal = binary_metrics(yte, pte_cal >= thr)
        final[h] = dict(uncal=m_unc, cal=m_cal,
                        brier_before=brier_score(yte, pte), brier_after=brier_score(yte, pte_cal),
                        ece_before=expected_calibration_error(yte, pte),
                        ece_after=expected_calibration_error(yte, pte_cal))
        if h == "y_15min":
            cal_p15_test = pte_cal; thr15 = thr
            pte15_unc = pte
            yte15 = yte
            rel_before = reliability_curve(yte, pte)
            rel_after = reliability_curve(yte, pte_cal)

    # ---- baselines on test (same denominator) ----
    base = {}
    for h in HORIZONS:
        yte = te[h].to_numpy(); yva = va[h].to_numpy()
        base[("climatology", h)] = 0.0
        best_pw, best_cfg = -1, None
        for col in ("det_rate_1h", "det_rate_3h", "det_rate_6h"):
            thr_p, tss_p = best_threshold(yva, persistence_probability(va[col].to_numpy()))
            if tss_p > best_pw:
                best_pw, best_cfg = tss_p, (col, thr_p)
        pcol, pthr = best_cfg
        base[("persistence", h)] = binary_metrics(
            yte, persistence_probability(te[pcol].to_numpy()) >= pthr)["tss"]

    # ---- reliability diagram ----
    fig, ax = plt.subplots(figsize=(7, 7), constrained_layout=True)
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
    mp, of, _ = rel_before
    ax.plot(mp, of, "o-", color="tab:red", label="XGBoost (uncalibrated)")
    mp, of, _ = rel_after
    ax.plot(mp, of, "s-", color="tab:green", label="XGBoost + isotonic")
    ax.set_xlabel("predicted probability"); ax.set_ylabel("observed frequency")
    ax.set_title("15-min reliability diagram (test)"); ax.legend(); ax.grid(alpha=0.3)
    fig.savefig(VALID / "forecast_reliability.png", dpi=140); plt.close(fig)

    # ---- per-class recall (calibrated 15-min) ----
    pc = per_class_recall(yte15, cal_p15_test >= thr15, te["y_class30"].to_numpy())

    # ---- quiet -> X-class all-clear test ----
    swpc = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet").dropna(subset=["peak_utc"])
    swpc = swpc.copy(); swpc["day"] = swpc["peak_utc"].dt.strftime("%Y%m%d")
    te_u = (te["utc"].astype("int64") // 10**9).to_numpy()         # unix seconds
    swpc_u = (swpc["peak_utc"].astype("int64") // 10**9).to_numpy()
    # "quiet" = no significant (M/X) flare in the prior 12h. C-flares are
    # near-constant background at solar max, so M/X-free is the operationally
    # meaningful all-clear state (the Camporeale failure mode).
    mx_u = (swpc.loc[swpc["goes_class_letter"].isin(["M", "X"]), "peak_utc"].astype("int64") // 10**9).to_numpy()
    tx = swpc[(swpc["goes_class_letter"] == "X") & (swpc["day"] >= TEST[0]) & (swpc["day"] <= TEST[1])]
    allclear = []
    for _, fr in tx.iterrows():
        peak_u = int(pd.Timestamp(fr["peak_utc"]).value // 10**9)
        start_u = int(pd.Timestamp(fr["start_utc"]).value // 10**9)
        quiet_lo = start_u - 12 * 3600
        n_prior = int(((mx_u >= quiet_lo) & (mx_u < start_u)).sum())   # prior M/X count
        is_quiet = n_prior == 0
        # alarm: any calibrated 15-min prediction >= thr in [peak-15min, peak]
        win = (te_u >= peak_u - 900) & (te_u <= peak_u)
        flagged = bool(np.any(cal_p15_test[win] >= thr15)) if win.any() else False
        lead = np.nan
        if win.any() and flagged:
            fire = (cal_p15_test >= thr15) & win
            if fire.any():
                lead = (peak_u - int(te_u[np.argmax(fire)])) / 60.0
        allclear.append(dict(peak=pd.Timestamp(fr["peak_utc"]), goes_class=fr["goes_class"],
                             quiet=is_quiet, n_prior_6h=n_prior, flagged=flagged,
                             lead_min=lead, has_rows=bool(win.any())))
    ac = pd.DataFrame(allclear)

    # ---- report ----
    lines.append("\nFINAL TSS table (test) - calibrated XGBoost vs baselines:")
    lines.append(f"  {'horizon':9s} {'clim':>7} {'persist':>8} {'XGB(cal)':>9}")
    for h in HORIZONS:
        lines.append(f"  {h:9s} {base[('climatology',h)]:>7.3f} {base[('persistence',h)]:>8.3f} "
                     f"{final[h]['cal']['tss']:>9.3f}")
    lines.append("\n15-min full metrics (calibrated XGBoost):")
    m = final["y_15min"]["cal"]
    lines.append(f"  TSS={m['tss']:.3f} HSS={m['hss']:.3f} POD={m['pod']:.3f} "
                 f"FAR={m['far']:.3f} precision={m['precision']:.3f}")
    lines.append("\nCalibration (test) before -> after isotonic:")
    for h in HORIZONS:
        f = final[h]
        lines.append(f"  {h}: Brier {f['brier_before']:.4f} -> {f['brier_after']:.4f}   "
                     f"ECE {f['ece_before']:.4f} -> {f['ece_after']:.4f}   "
                     f"TSS {f['uncal']['tss']:.3f} -> {f['cal']['tss']:.3f} (monotonic, preserved)")
    lines.append("\nPer-class recall, calibrated 15-min (POD on pre-flare windows; X denom=test events):")
    for c in ("B", "C", "M", "X"):
        hit, n, r = pc[c]
        lines.append(f"  {c}: {hit}/{n}" + (f" ({r:.2f})" if n else " (none)"))
    n_x = len(ac); n_quiet = int(ac["quiet"].sum())
    no_rows = int((~ac["has_rows"]).sum())
    lines.append(f"\nQUIET->X-CLASS ALL-CLEAR TEST (test set; {n_x} X-flares; quiet = no M/X in prior 12h):")
    flagged_quiet = int((ac["quiet"] & ac["flagged"]).sum())
    flagged_all = int(ac["flagged"].sum())
    lines.append(f"  quiet->X transitions in test: {n_quiet}; flagged before peak: {flagged_quiet}/{n_quiet}")
    lines.append(f"  ALL test X-flares flagged in [peak-15min,peak]: {flagged_all}/{n_x} "
                 f"({no_rows} had no in-GTI feature rows in the pre-peak window)")
    for _, r in ac.iterrows():
        tag = "QUIET->X" if r["quiet"] else "active"
        lead = f"{r['lead_min']:.0f}min" if r["flagged"] and not np.isnan(r["lead_min"]) else "-"
        rows = "" if r["has_rows"] else " NO-COVERAGE"
        lines.append(f"    {r['peak']:%Y-%m-%d %H:%M} {r['goes_class']:>5} [{tag:8s}] "
                     f"priorMX_12h={r['n_prior_6h']} flagged={'YES' if r['flagged'] else 'no'} lead={lead}{rows}")

    np.savez(FCAST / "calibrated_test_predictions.npz",
             p15_cal=cal_p15_test, p15_uncal=pte15_unc, y15=yte15,
             thr15=thr15, utc_unix=te_u)
    (REPORTS / "forecasting_metrics.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORTS/'forecasting_metrics.txt'} and {VALID/'forecast_reliability.png'} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""STAGE 4b — time-respecting split + four reference forecasters.

climatology / persistence / logistic regression / XGBoost, evaluated on a
held-out LATER test period. TSS is the headline (accuracy never reported).
Writes reports/forecasting_baselines.txt and saved test predictions.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from src.forecasting.baselines import (
    climatology_probability, fit_neupert_k, neupert_residual, persistence_probability,
)
from src.forecasting.evaluation import best_threshold, binary_metrics, per_class_recall
from src.forecasting.features import feature_names

FF_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"
REPORTS = PROJECT_ROOT / "data" / "processed" / "reports"
FCAST_DIR = PROJECT_ROOT / "data" / "processed" / "forecasts"
HORIZONS = ["y_15min", "y_30min", "y_60min"]

TRAIN = ("20240701", "20250630")
VAL = ("20250701", "20251231")
TEST = ("20260101", "20260613")


def load_matrix() -> pd.DataFrame:
    frames = [pd.read_parquet(f) for f in sorted(FF_DIR.glob("*.parquet"))]
    df = pd.concat(frames, ignore_index=True)
    return df[df["in_gti_any"]].reset_index(drop=True)   # need >=1 detector to forecast


def split(df):
    d = df["day"].to_numpy()
    return (df[(d >= TRAIN[0]) & (d <= TRAIN[1])].copy(),
            df[(d >= VAL[0]) & (d <= VAL[1])].copy(),
            df[(d >= TEST[0]) & (d <= TEST[1])].copy())


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    FCAST_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("loading feature matrix ...")
    df = load_matrix()
    feats = feature_names(df)

    # Neupert residual: k fit on TRAIN only, applied to all splits
    tr_mask = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[tr_mask, "hel1os_hard_rate"].to_numpy(),
                      df.loc[tr_mask, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]
    print(f"  Neupert k (train OLS) = {k:.4f}")

    train, val, test = split(df)
    print(f"  train={len(train)}  val={len(val)}  test={len(test)} rows  ({time.time()-t0:.0f}s)")

    Xtr, Xva, Xte = train[feats], val[feats], test[feats]
    lines = ["STAGE 4b - BASELINES (time-respecting split)", "=" * 72]
    lines.append(f"train {TRAIN[0]}..{TRAIN[1]}  val {VAL[0]}..{VAL[1]}  test {TEST[0]}..{TEST[1]}")
    lines.append(f"rows: train={len(train)} val={len(val)} test={len(test)}")

    results = {}        # (model, horizon) -> test metrics
    xgb_importance = None
    saved_preds = {"y_true_15min": test["y_15min"].to_numpy(),
                   "y_class30": test["y_class30"].to_numpy()}

    for horizon in HORIZONS:
        ytr, yva, yte = train[horizon].to_numpy(), val[horizon].to_numpy(), test[horizon].to_numpy()

        # 1. climatology (constant base rate -> TSS 0)
        clim_p = climatology_probability(ytr)
        # constant predictor: TSS is 0 regardless of threshold; report all-positive degenerate
        results[("climatology", horizon)] = binary_metrics(yte, np.ones_like(yte))
        results[("climatology", horizon)]["tss"] = 0.0

        # 2. persistence (trailing detection activity; best window tuned on val)
        best_pers, best_pw = None, -1
        for col in ("det_rate_1h", "det_rate_3h", "det_rate_6h"):
            score_va = persistence_probability(val[col].to_numpy())
            thr, tss_va = best_threshold(yva, score_va)
            if tss_va > best_pw:
                best_pw, best_pers = tss_va, (col, thr)
        pcol, pthr = best_pers
        results[("persistence", horizon)] = binary_metrics(
            yte, persistence_probability(test[pcol].to_numpy()) >= pthr)
        results[("persistence", horizon)]["_cfg"] = f"{pcol}>={pthr:.2f}"

        # 3. logistic regression (class-weighted)
        lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                           LogisticRegression(class_weight="balanced", max_iter=2000))
        lr.fit(Xtr, ytr)
        p_va = lr.predict_proba(Xva)[:, 1]; p_te = lr.predict_proba(Xte)[:, 1]
        thr, _ = best_threshold(yva, p_va)
        results[("logreg", horizon)] = binary_metrics(yte, p_te >= thr)

        # 4. XGBoost (scale_pos_weight)
        spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
        clf = xgb.XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
            eval_metric="aucpr", early_stopping_rounds=30, tree_method="hist",
            n_jobs=4)
        clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        p_va = clf.predict_proba(Xva)[:, 1]; p_te = clf.predict_proba(Xte)[:, 1]
        thr, _ = best_threshold(yva, p_va)
        results[("xgboost", horizon)] = binary_metrics(yte, p_te >= thr)
        results[("xgboost", horizon)]["_thr"] = thr
        saved_preds[f"xgb_prob_{horizon}"] = p_te
        saved_preds[f"xgb_valprob_{horizon}"] = p_va
        saved_preds[f"y_true_{horizon}"] = yte
        if horizon == "y_15min":
            imp = clf.get_booster().get_score(importance_type="gain")
            xgb_importance = sorted(imp.items(), key=lambda kv: -kv[1])
            xgb_thr_15 = thr
            xgb_pte_15 = p_te

    # ---- report: TSS table ----
    lines.append("\nTSS table (test set):")
    lines.append(f"  {'model':14s} {'15min':>8} {'30min':>8} {'60min':>8}")
    for model in ("climatology", "persistence", "logreg", "xgboost"):
        row = "  " + f"{model:14s}"
        for h in HORIZONS:
            row += f" {results[(model, h)]['tss']:>8.4f}"
        lines.append(row)

    lines.append("\nFull metrics at 15-min (primary):")
    lines.append(f"  {'model':14s} {'TSS':>7} {'HSS':>7} {'POD':>7} {'FAR':>7} {'prec':>7}")
    for model in ("climatology", "persistence", "logreg", "xgboost"):
        m = results[(model, "y_15min")]
        lines.append(f"  {model:14s} {m['tss']:>7.3f} {m['hss']:>7.3f} {m['pod']:>7.3f} "
                     f"{m['far']:>7.3f} {m['precision']:>7.3f}")
    lines.append(f"  (persistence cfg: {results[('persistence','y_15min')].get('_cfg')})")

    # ---- XGBoost feature importance ----
    lines.append("\nXGBoost feature importance (gain) - top 20:")
    physics = {"soft_ddt_5m", "soft_ddt_15m", "soft_ddt_30m", "hardness_ratio",
               "hardness_ddt_15m", "neupert_resid", "hel1os_hard_bgsub", "hel1os_hard_rate"}
    qpp = {c for c in feats if c.startswith("qpp")}
    for i, (name, gain) in enumerate(xgb_importance[:20], 1):
        tag = ""
        if name in physics:
            tag = "  [PHYSICS precursor]"
        elif name in qpp:
            tag = "  [QPP]"
        lines.append(f"  {i:>2}. {name:28s} {gain:10.1f}{tag}")
    # where do physics/qpp features rank?
    rank = {name: i for i, (name, _) in enumerate(xgb_importance, 1)}
    lines.append("\n  precursor feature ranks (of {} features):".format(len(xgb_importance)))
    for f in sorted(physics | qpp):
        lines.append(f"    {f:28s} rank {rank.get(f, 'unused')}")

    # ---- per-class recall (XGBoost 15-min) ----
    pc = per_class_recall(test["y_15min"].to_numpy(), xgb_pte_15 >= xgb_thr_15,
                          test["y_class30"].to_numpy())
    lines.append("\nXGBoost 15-min per-class recall (POD on pre-flare windows by class):")
    for c in ("B", "C", "M", "X"):
        hit, n, r = pc[c]
        lines.append(f"  {c}: {hit}/{n}" + (f" ({r:.2f})" if n else " (no events)"))

    # save predictions for Stage 4c/4d
    np.savez(FCAST_DIR / "baseline_test_predictions.npz", **saved_preds)
    (REPORTS / "forecasting_baselines.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORTS/'forecasting_baselines.txt'}  ({time.time()-t0:.0f}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

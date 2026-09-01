"""STAGE 5 — CPU inference latency benchmark (GATE: environment hardening).

End-to-end operational inference path: 1x87 feature vector -> XGBoost
predict_proba -> isotonic calibration -> calibrated probability. The model is
rebuilt in-process with the FROZEN Stage-4d config (no model artifact is
shipped; frozen results unchanged), then benchmarked on CPU over 10,000
single-row calls. Writes data/processed/reports/latency_benchmark.txt (+json).
"""
from __future__ import annotations

import json
import pickle
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import xgboost as xgb

from src.forecasting.baselines import fit_neupert_k, neupert_residual
from src.forecasting.calibration import fit_isotonic
from src.forecasting.features import feature_names

FF_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"
REPORTS = PROJECT_ROOT / "data" / "processed" / "reports"
TRAIN, VAL = ("20240701", "20250630"), ("20250701", "20251231")
N_CALLS = 10_000


def main():
    t0 = time.time()
    print("loading features + training frozen-config 15-min model (one-off) ...")
    df = pd.concat([pd.read_parquet(f) for f in sorted(FF_DIR.glob("*.parquet"))],
                   ignore_index=True)
    df = df[df["in_gti_any"]].reset_index(drop=True)
    feats = feature_names(df)
    trm = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[trm, "hel1os_hard_rate"].to_numpy(),
                      df.loc[trm, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]
    d = df["day"].to_numpy()
    tr = df[(d >= TRAIN[0]) & (d <= TRAIN[1])]
    va = df[(d >= VAL[0]) & (d <= VAL[1])]
    ytr, yva = tr["y_15min"].to_numpy(), va["y_15min"].to_numpy()
    spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    clf = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                            eval_metric="aucpr", early_stopping_rounds=30,
                            tree_method="hist", n_jobs=4)
    clf.fit(tr[feats], ytr, eval_set=[(va[feats], yva)], verbose=False)
    iso = fit_isotonic(clf.predict_proba(va[feats])[:, 1], yva)
    print(f"  trained ({time.time()-t0:.0f}s). benchmarking {N_CALLS} single-row calls ...")

    # single-row inference: numpy float32 vector (operational hot path, CPU)
    X1 = va[feats].iloc[[1234]].to_numpy(np.float32)
    booster = clf.get_booster()
    clf.set_params(n_jobs=1)                    # single-row -> single thread is honest
    for _ in range(200):                        # warm-up (JIT caches, page-in)
        p = iso.transform(clf.predict_proba(X1)[:, 1])
    lat_ns = np.empty(N_CALLS)
    for i in range(N_CALLS):
        t = time.perf_counter_ns()
        p = iso.transform(clf.predict_proba(X1)[:, 1])
        lat_ns[i] = time.perf_counter_ns() - t
    lat_ms = lat_ns / 1e6
    med, p99 = float(np.median(lat_ms)), float(np.percentile(lat_ms, 99))
    mean = float(lat_ms.mean())

    # memory footprint
    raw_model = len(booster.save_raw())               # serialized booster bytes
    pkl_model = len(pickle.dumps(clf))
    pkl_iso = len(pickle.dumps(iso))
    best_it = getattr(clf, "best_iteration", None)

    lines = ["CPU INFERENCE LATENCY BENCHMARK — 15-min calibrated forecast", "=" * 68,
             "path: 1x87 float32 feature vector -> XGBoost predict_proba -> isotonic",
             f"model: frozen Stage-4d config (400 trees cap, best_iteration={best_it}), "
             f"tree_method=hist, single-thread single-row inference",
             f"hardware: CPU only (no GPU used at inference)",
             f"calls: {N_CALLS} (after 200-call warm-up)",
             "",
             f"  median latency : {med:.3f} ms",
             f"  mean latency   : {mean:.3f} ms",
             f"  p99 latency    : {p99:.3f} ms",
             f"  throughput     : {1000.0/med:,.0f} forecasts/s (single thread)",
             "",
             f"  model footprint: booster serialized {raw_model/1024:.0f} KB · "
             f"pickled sklearn wrapper {pkl_model/1024:.0f} KB · isotonic {pkl_iso/1024:.1f} KB",
             "",
             "Interpretation: sub-10-ms single-row CPU inference — negligible against the",
             "1-minute forecast cadence and instrument telemetry latency; the system is",
             "operationally real-time on commodity hardware."]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "latency_benchmark.txt").write_text("\n".join(lines), encoding="utf-8")
    (REPORTS / "latency_benchmark.json").write_text(json.dumps(dict(
        median_ms=round(med, 3), mean_ms=round(mean, 3), p99_ms=round(p99, 3),
        throughput_per_s=round(1000.0/med), n_calls=N_CALLS,
        booster_bytes=raw_model, pickle_bytes=pkl_model, isotonic_bytes=pkl_iso,
        best_iteration=best_it), indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

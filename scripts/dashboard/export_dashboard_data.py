"""STAGE 0 — export pre-computed dashboard JSON.

Runs the model OFFLINE (here, during export — never at dashboard runtime) and
writes a self-contained dashboard_data/ folder the frontend reads directly. No
parquet, no model code is touched when the dashboard serves.

Outputs:
  dashboard_data/replay_days/{YYYYMMDD}.json   (per demo day)
  dashboard_data/summary_metrics.json
  dashboard_data/hardness_ordering.json
  dashboard_data/master_catalog.json
  dashboard_data/qpp_catalog.json
  dashboard_data/manifest.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.detection.detector_pipeline import compute_excess
from src.forecasting.baselines import fit_neupert_k, neupert_residual, persistence_probability
from src.forecasting.calibration import expected_calibration_error, brier_score, reliability_curve
from src.forecasting.evaluation import best_threshold, binary_metrics, per_class_recall
from src.forecasting.features import feature_names

PROC = PROJECT_ROOT / "data" / "processed"
FF = PROC / "forecast_features"
LC = PROC / "daily_lightcurves"
DET = PROC / "detections"
OUT = PROJECT_ROOT / "dashboard_data"
TRAIN, VAL, TEST = ("20240701", "20250630"), ("20250701", "20251231"), ("20260101", "20260613")
HORIZONS = ["y_15min", "y_30min", "y_60min"]
BIN = 10                       # light-curve downsample seconds
# total-band rate column + gti per detector + display name + colour key
DETECTORS = [
    ("solexs_sdd2", "solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS SDD2 (soft)", 3.5),
    ("hel1os_cdte1", "hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti", "HEL1OS CdTe1", 2.0),
    ("hel1os_cdte2", "hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti", "HEL1OS CdTe2", 2.0),
    ("hel1os_czt1", "hel1os_czt1_18_160kev", "hel1os_czt1_gti", "HEL1OS CZT1 (hard)", 2.0),
    ("hel1os_czt2", "hel1os_czt2_18_160kev", "hel1os_czt2_gti", "HEL1OS CZT2 (hard)", 2.0),
]
# Curated archive of REAL days (all pre-computed; every day tagged TEST/VAL/TRAIN by
# split_of(), in_sample derived, GTI gaps preserved as null, saturation caveat intact).
# Held-out (TEST) days lead; in-sample TRAIN days are clearly flagged in the UI.
DEMO_DAYS = [
    # ── TEST (held-out — genuine forecast) ──
    ("20260201", "X8.1", "TEST", "showstopper"),    # the demo: held-out forecast test
    ("20260118", "X1.9", "TEST", "allclear"),       # held-out quiet->X (Camporeale failure mode)
    ("20260204", "X4.2", "TEST", "gti_miss"),        # coverage gap -> honest miss
    ("20260202", "X2.8", "TEST", "xclass"),
    ("20260203", "X1.5", "TEST", "xclass"),
    ("20260330", "X1.4", "TEST", "xclass"),
    ("20260424", "X2.5", "TEST", "xclass"),
    ("20260603", "X1.0", "TEST", "xclass"),
    ("20260404", "M7.5", "TEST", "mclass"),
    ("20260426", "M6.0", "TEST", "mclass"),
    ("20260320", "quiet", "TEST", "quiet"),
    ("20260101", "quiet", "TEST", "quiet"),
    # ── VAL ──
    ("20251114", "X4.0", "VAL", "anchor"),
    ("20251104", "X1.8", "VAL", "xclass"),
    ("20251109", "X1.7", "VAL", "xclass"),
    ("20251110", "X1.2", "VAL", "xclass"),
    ("20251201", "X1.9", "VAL", "xclass"),
    ("20251208", "X1.1", "VAL", "xclass"),
    ("20251105", "M8.6", "VAL", "mclass"),
    ("20251206", "M8.1", "VAL", "mclass"),
    ("20250701", "quiet", "VAL", "quiet"),
    # ── TRAIN (in-sample illustration) ──
    ("20241003", "X9.0", "TRAIN", "famous"),        # recognisable monster flare
    ("20241001", "X7.1", "TRAIN", "anchor"),
    ("20240914", "X4.5", "TRAIN", "xclass"),
    ("20241024", "X3.3", "TRAIN", "xclass"),
    ("20250514", "X2.7", "TRAIN", "xclass"),
    ("20241031", "X2.0", "TRAIN", "xclass"),
    ("20241007", "X2.1", "TRAIN", "xclass"),
    ("20240716", "X1.9", "TRAIN", "xclass"),
    ("20240728", "M9.9", "TRAIN", "mclass"),
    ("20241125", "M9.4", "TRAIN", "mclass"),
    ("20240705", "quiet", "TRAIN", "quiet"),
    ("20250306", "quiet", "TRAIN", "quiet"),
]
LEAD_WINDOW_S = 900            # bounded operational lead: only [peak-15min, peak]
PRECISION_TARGET = 0.40        # raised "Warning" operating point (limit alarm fatigue)


def split_of(d: str) -> str:
    return "TRAIN" if d <= TRAIN[1] else ("VAL" if d <= VAL[1] else "TEST")


def jround(x, nd=2):
    """JSON-safe rounding: NaN/inf -> None (preserves GTI gaps as null).
    Type-agnostic: float32 NaN is not a Python-float subclass, so cast first."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(xf):
        return None
    return round(xf, nd)


def arr_json(a, nd=2):
    return [jround(v, nd) for v in a]


# ─────────────────────────────────────────────────────────────────────────────
# Model training (offline)
# ─────────────────────────────────────────────────────────────────────────────
def train_models():
    print("training calibrated XGBoost (offline) ...", flush=True)
    df = pd.concat([pd.read_parquet(f) for f in sorted(FF.glob("*.parquet"))], ignore_index=True)
    df = df[df["in_gti_any"]].reset_index(drop=True)
    feats = feature_names(df)
    trm = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[trm, "hel1os_hard_rate"].to_numpy(), df.loc[trm, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]
    d = df["day"].to_numpy()
    tr, va, te = df[(d <= TRAIN[1])], df[(d >= VAL[0]) & (d <= VAL[1])], df[(d >= TEST[0])]
    models = {}
    metrics = {}
    rel = {}
    base_pers = {}
    y15 = p15_cal = thr15 = None
    for h in HORIZONS:
        ytr, yva, yte = tr[h].to_numpy(), va[h].to_numpy(), te[h].to_numpy()
        spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
        clf = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                                eval_metric="aucpr", early_stopping_rounds=30, tree_method="hist", n_jobs=4)
        clf.fit(tr[feats], ytr, eval_set=[(va[feats], yva)], verbose=False)
        pva, pte = clf.predict_proba(va[feats])[:, 1], clf.predict_proba(te[feats])[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(pva, yva)
        pte_cal, pva_cal = iso.transform(pte), iso.transform(pva)
        thr, _ = best_threshold(yva, pva_cal)
        models[h] = (clf, iso, thr)
        mc = binary_metrics(yte, pte_cal >= thr)
        metrics[h] = dict(tss=mc["tss"],
                          **{kk: mc[kk] for kk in ("hss", "pod", "far", "precision")},
                          brier_before=brier_score(yte, pte), brier_after=brier_score(yte, pte_cal),
                          ece_before=expected_calibration_error(yte, pte), ece_after=expected_calibration_error(yte, pte_cal),
                          thr=thr)
        # baseline: best persistence (col+thr tuned on val) -> test TSS, same denominator
        best_tss_p, best_cfg = -1.0, ("det_rate_1h", 0.5)
        for col in ("det_rate_1h", "det_rate_3h", "det_rate_6h"):
            tp_thr, tp_tss = best_threshold(yva, persistence_probability(va[col].to_numpy()))
            if tp_tss > best_tss_p:
                best_tss_p, best_cfg = tp_tss, (col, tp_thr)
        pcol, pthr = best_cfg
        base_pers[h] = binary_metrics(yte, persistence_probability(te[pcol].to_numpy()) >= pthr)["tss"]
        if h == "y_15min":
            y15, p15_cal, thr15 = yte, pte_cal, float(thr)
            rel["before"] = reliability_curve(yte, pte)
            rel["after"] = reliability_curve(yte, pte_cal)
            imp = clf.get_booster().get_score(importance_type="gain")
            metrics["_importance"] = sorted(imp.items(), key=lambda kv: -kv[1])[:10]
            # alert operating points (15-min, calibrated, tuned on val):
            #   Watch   = TSS-optimal point (sensitive)
            #   Warning = raised higher-precision point (limit alarm fatigue)
            watch_thr = float(thr)
            warning_thr, far_at_tss = _operating_points(yva, iso.transform(clf.predict_proba(va[feats])[:, 1]),
                                                        watch_thr, PRECISION_TARGET)
            metrics["_alert"] = {"watch": watch_thr, "warning": warning_thr,
                                 "far_at_tss": far_at_tss, "precision_target": PRECISION_TARGET}
    # baselines + per-class recall (15-min), computed from the model just trained
    metrics["_baselines"] = {"climatology": {h: 0.0 for h in HORIZONS}, "persistence": base_pers}
    metrics["_per_class"] = per_class_recall(y15, p15_cal >= thr15, te["y_class30"].to_numpy())
    # test-set 15-min predictions for the quiet->X all-clear test (computed in main with SWPC)
    metrics["_test15"] = {"utc_unix": (te["utc"].astype("int64") // 10**9).to_numpy(),
                          "p15_cal": p15_cal, "thr15": thr15}
    return models, k, feats, metrics, rel


def compute_all_clear(test15, swpc):
    """Quiet->X-class all-clear test on the TEST set, computed from the calibrated
    15-min predictions (Camporeale 2025 failure mode). 'quiet' = no M/X in prior 12h.
    Reproduces the canonical Stage-4d numbers; nothing here is hand-entered."""
    te_u = test15["utc_unix"]; p = test15["p15_cal"]; thr = test15["thr15"]
    sw = swpc.dropna(subset=["peak_utc"]).copy()
    sw["day"] = sw["peak_utc"].dt.strftime("%Y%m%d")
    mx_u = (sw.loc[sw["goes_class_letter"].isin(["M", "X"]), "peak_utc"].astype("int64") // 10**9).to_numpy()
    tx = sw[(sw["goes_class_letter"] == "X") & (sw["day"] >= TEST[0]) & (sw["day"] <= TEST[1])]
    rows, n_quiet, flag_quiet, flag_all, no_cov = [], 0, 0, 0, 0
    for _, fr in tx.iterrows():
        peak_u = int(pd.Timestamp(fr["peak_utc"]).value // 10**9)
        start_u = int(pd.Timestamp(fr["start_utc"]).value // 10**9)
        n_prior = int(((mx_u >= start_u - 12 * 3600) & (mx_u < start_u)).sum())
        is_quiet = n_prior == 0
        win = (te_u >= peak_u - LEAD_WINDOW_S) & (te_u <= peak_u)
        has_rows = bool(win.any())
        flagged = bool(np.any(p[win] >= thr)) if has_rows else False
        lead = None
        if flagged:
            fire = (p >= thr) & win
            if fire.any():
                lead = round((peak_u - int(te_u[np.argmax(fire)])) / 60.0, 0)
        n_quiet += is_quiet; flag_quiet += (is_quiet and flagged); flag_all += flagged
        no_cov += (not has_rows)
        rows.append({"peak_utc": pd.Timestamp(fr["peak_utc"]).strftime("%Y-%m-%d %H:%M"),
                     "goes_class": fr["goes_class"], "quiet": is_quiet, "flagged": flagged,
                     "lead_min": lead, "has_rows": has_rows})
    return {"n_x": len(rows), "n_quiet": n_quiet, "quiet_flagged": flag_quiet,
            "all_flagged": flag_all, "no_coverage": no_cov, "rows": rows}


def _operating_points(yva, pva, tss_thr, prec_target):
    """Return (warning_thr, far_at_tss). Warning = lowest threshold (>= TSS point)
    whose precision >= prec_target on validation — a higher-precision operating
    point that limits alarm fatigue while staying as sensitive as allowed."""
    far_at_tss = binary_metrics(yva, pva >= tss_thr)["far"]
    grid = np.unique(np.quantile(pva, np.linspace(0.5, 0.999, 200)))
    warning = tss_thr
    for t in grid:
        if t < tss_thr:
            continue
        m = binary_metrics(yva, pva >= t)
        if m["precision"] >= prec_target and m["pod"] > 0:
            warning = float(t)
            break
    return warning, far_at_tss


# ─────────────────────────────────────────────────────────────────────────────
# Per-day forecast series (1-min) with alert timeline
# ─────────────────────────────────────────────────────────────────────────────
def forecast_day(day, models, k, feats, watch_thr, warn_thr):
    f = pd.read_parquet(FF / f"{day}.parquet")
    f["neupert_resid"] = neupert_residual(f["hel1os_hard_rate"], f["soft_ddt_5m"], k)
    ingti = f["in_gti_any"].to_numpy().astype(bool)
    t_unix = (f["utc"].astype("int64") // 10**9).to_numpy()
    out = {"t": [int(x) for x in t_unix]}
    series = {}
    for h, (clf, iso, thr) in models.items():
        p = iso.transform(clf.predict_proba(f[feats])[:, 1])
        p = np.where(ingti, p, np.nan)
        series[h] = p
        out[h] = arr_json(p, 4)
    p15 = series["y_15min"]
    # confidence band (binomial-style around the calibrated risk)
    neff = 150.0
    lo = np.clip(p15 - 1.64 * np.sqrt(np.clip(p15 * (1 - p15), 0, None) / neff), 0, 1)
    hi = np.clip(p15 + 1.64 * np.sqrt(np.clip(p15 * (1 - p15), 0, None) / neff), 0, 1)
    out["y_15min_lo"] = arr_json(np.where(ingti, lo, np.nan), 4)
    out["y_15min_hi"] = arr_json(np.where(ingti, hi, np.nan), 4)
    # alert timeline
    alert = np.full(len(p15), "nocov", dtype=object)
    fin = np.isfinite(p15)
    alert[fin & (p15 < watch_thr)] = "quiet"
    alert[fin & (p15 >= watch_thr) & (p15 < warn_thr)] = "watch"
    alert[fin & (p15 >= warn_thr)] = "warning"
    out["alert"] = list(alert)
    out["thresholds"] = {"watch": jround(watch_thr, 4), "warning": jround(warn_thr, 4)}
    n_warn = int(np.sum(np.isfinite(p15) & (p15 >= warn_thr)))
    n_watch = int(np.sum(np.isfinite(p15) & (p15 >= watch_thr) & (p15 < warn_thr)))
    out["alert_minutes"] = {"warning": n_warn, "watch": n_watch}
    # solar-context features (1-min) for the Operations console
    ctx_cols = {"hardness_ratio": "hardness_ratio", "neupert_resid": "neupert_resid",
                "f107": "f107_lag1", "sunspot": "sunspot_number_lag1",
                "ar_count": "ar_count_lag1", "time_since_last_s": "time_since_last_det_s"}
    ctx = {}
    for jk, col in ctx_cols.items():
        v = f[col].to_numpy(np.float64)
        if jk in ("hardness_ratio", "neupert_resid"):      # light-curve derived -> NaN out of GTI
            v = np.where(ingti, v, np.nan)
        ctx[jk] = arr_json(v, 3)
    out["context"] = ctx
    out["coverage_pct"] = round(100.0 * float(ingti.mean()), 1)
    return out, t_unix, p15, warn_thr


# ─────────────────────────────────────────────────────────────────────────────
# Per-day detector light curves + background band (10s)
# ─────────────────────────────────────────────────────────────────────────────
def detector_series_day(day):
    df = pd.read_parquet(LC / f"{day}.parquet")
    t = (df["utc"].astype("int64") // 10**9).to_numpy()
    n = (len(df) // BIN) * BIN
    t10 = t[:n:BIN]
    dets = {}
    for key, rate_col, gti_col, name, thr in DETECTORS:
        cr = df[rate_col].to_numpy(np.float64)
        g = df[gti_col].to_numpy(bool)
        exr = compute_excess(cr, g)                  # label-free background (inference path)
        crm = np.where(g, cr, np.nan)
        band = exr.background + thr * exr.sigma
        band = np.where(g & np.isfinite(exr.background), band, np.nan)
        bgm = np.where(g, exr.background, np.nan)
        def ds(a):
            b = a[:n].reshape(-1, BIN)
            with np.errstate(all="ignore"):
                return np.nanmean(b, axis=1)
        dets[key] = dict(name=name, rate=arr_json(ds(crm), 1),
                         background=arr_json(ds(bgm), 1), band=arr_json(ds(band), 1))
    return [int(x) for x in t10], dets


# ─────────────────────────────────────────────────────────────────────────────
# Replay day assembly
# ─────────────────────────────────────────────────────────────────────────────
def export_replay_day(day, label, role, models, k, feats, swpc, master, watch_thr, warn_thr):
    t10, dets = detector_series_day(day)
    fc, ft, p15, warn_thr = forecast_day(day, models, k, feats, watch_thr, warn_thr)
    d0 = pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}", tz="UTC")
    d1 = d0 + pd.Timedelta(days=1)
    # actual flares (SWPC)
    sf = swpc[(swpc["peak_utc"] >= d0) & (swpc["peak_utc"] < d1)]
    flares = [{"peak": int(r.peak_utc.value // 10**9), "start": int(r.start_utc.value // 10**9),
               "goes_class": r.goes_class, "letter": r.goes_class_letter, "noaa_ar": (int(r.noaa_ar) if pd.notna(r.noaa_ar) else None)}
              for r in sf.itertuples()]
    # detected events (master catalog)
    md = master[(master["master_peak_utc"] >= d0) & (master["master_peak_utc"] < d1)]
    detected = [{"peak": int(r.master_peak_unix), "n_detectors": int(r.n_detectors),
                 "confidence": jround(r.confidence, 2), "detectors": r.detectors}
                for r in md.itertuples()]
    # bounded operational lead: Warning active only within [peak-15min, peak].
    # The model is a 15-min forecaster -> lead is capped at 15 min (honest).
    lead = []
    warn = np.isfinite(p15) & (p15 >= warn_thr)
    for fr in flares:
        pk = fr["peak"]
        win_mask = (ft >= pk - LEAD_WINDOW_S) & (ft <= pk)
        warn_in_win = win_mask & warn
        if warn_in_win.any():
            first = int(ft[np.argmax(warn_in_win)])
            lead.append({"peak": pk, "goes_class": fr["goes_class"], "first_warning": first,
                         "lead_min": round((pk - first) / 60, 1), "flagged": True})
        else:
            covered = bool(np.isfinite(p15[win_mask]).any())
            lead.append({"peak": pk, "goes_class": fr["goes_class"], "first_warning": None,
                         "lead_min": None, "flagged": False,
                         "reason": "no_coverage" if not covered else "below_threshold"})
    obj = {
        "date": day, "label": label, "role": role, "split": split_of(day),
        "in_sample": split_of(day) != "TEST",
        "lc_t": t10, "detectors": dets,
        "forecast": fc,
        "actual_flares": flares, "detected_events": detected, "lead_times": lead,
        "notes": {"saturation": "SoLEXS peak amplitude is saturation-limited for M/X (not a magnitude proxy).",
                  "framing": "Forecast target = P(a flare PEAKS in (t, t+15min]); features <= t (causal). "
                             "Detection = nowcasting (concurrent) — a separate task."},
    }
    (OUT / "replay_days" / f"{day}.json").write_text(json.dumps(obj, allow_nan=False), encoding="utf-8")
    return obj


# ─────────────────────────────────────────────────────────────────────────────
def _load_json(path, what, fix):
    if not path.exists():
        raise SystemExit(f"ERROR: missing {what}: {path}\n  -> {fix}")
    return json.loads(path.read_text(encoding="utf-8"))


def export_summary(metrics, rel, all_clear):
    """Every number here is COMPUTED (forecasting: from the model just trained;
    all-clear: from its test predictions) or READ from a stage's machine-readable
    sidecar (detection: 13_evaluate.py/gate3; TFT: 17_train_tft.py). No literals."""
    reports = PROJECT_ROOT / "data" / "processed" / "reports"
    det = _load_json(reports / "detection_metrics.json", "detection metrics",
                     "run: python scripts/13_evaluate.py  (also needs gate3_evaluate.py for hardness)")
    tft = _load_json(reports / "tft_metrics.json", "TFT metrics",
                     "run: python scripts/17_train_tft.py")
    ev = det.get("event_level", {})
    pc_det = ev.get("per_class", {})
    pc = metrics["_per_class"]                       # forecast 15-min {C:(hit,n,rate),...}
    base = metrics["_baselines"]

    def det_recall(lab):
        if lab in pc_det:
            h, n = pc_det[lab]
            return f"{h}/{n} ({round(100 * h / n) if n else 0}%)"
        return None

    # all-clear, no-coverage breakdown -> the honest "8/8 observed" framing
    obs_flagged = all_clear["all_flagged"]
    obs_total = all_clear["n_x"] - all_clear["no_coverage"]
    obj = {
        "forecast_tss": {h: jround(metrics[h]["tss"], 3) for h in HORIZONS},
        "baselines": {"climatology": base["climatology"],
                      "persistence": {h: jround(base["persistence"][h], 3) for h in HORIZONS}},
        "tft_tss": {h: jround((tft.get("tss") or {}).get(h), 3) for h in HORIZONS},
        "forecast_15min": {kk: jround(metrics["y_15min"][kk], 3) for kk in ("tss", "hss", "pod", "far", "precision")},
        "calibration": {h: {"brier_before": jround(metrics[h]["brier_before"], 4),
                            "brier_after": jround(metrics[h]["brier_after"], 4),
                            "ece_before": jround(metrics[h]["ece_before"], 4),
                            "ece_after": jround(metrics[h]["ece_after"], 4)} for h in HORIZONS},
        "reliability": {
            "before": {"pred": arr_json(rel["before"][0], 3), "obs": arr_json(rel["before"][1], 3)},
            "after": {"pred": arr_json(rel["after"][0], 3), "obs": arr_json(rel["after"][1], 3)}},
        "feature_importance": [{"name": n, "gain": jround(g, 1),
                                "physics": n in {"soft_ddt_5m", "soft_ddt_15m", "soft_ddt_30m", "neupert_resid",
                                                 "hardness_ratio", "hardness_ddt_15m", "hel1os_hard_bgsub"}}
                               for n, g in metrics["_importance"]],
        "per_class_15min": {c: [pc[c][0], pc[c][1], jround(pc[c][2], 2)] for c in ("X", "M", "C", "B")},
        "x_test_denominator": all_clear["n_x"],
        "detection": {"tss": jround((ev.get("catalog_aware") or {}).get("tss"), 3),
                      "label": "NOWCASTING (concurrent detection)",
                      "per_class_recall": {c: det_recall(c) for c in ("X", "M", "C", "B")}},
        "all_clear": {"quiet_to_x": f"{all_clear['quiet_flagged']}/{all_clear['n_quiet']}",
                      "all_x": f"{all_clear['all_flagged']}/{all_clear['n_x']}",
                      "observed_x": f"{obs_flagged}/{obs_total}",
                      "no_coverage": all_clear["no_coverage"],
                      "rows": all_clear["rows"]},
        "alert_operating_points": {
            "watch_tss_optimal": jround(metrics["_alert"]["watch"], 4),
            "warning_high_precision": jround(metrics["_alert"]["warning"], 4),
            "far_at_tss_optimal": jround(metrics["_alert"]["far_at_tss"], 3),
            "note": "Watch = TSS-optimal (sensitive, FAR ~0.80 — the documented rare-event challenge, Camporeale 2025). Warning = raised to precision >= 0.40 to limit alarm fatigue (standard operational tradeoff)."},
        "framing": "Forecast TSS is a PREDICTION result (15-min lead), beating climatology + persistence (Camporeale 2025). Detection TSS is NOWCASTING (concurrent), a separate task.",
    }
    (OUT / "summary_metrics.json").write_text(json.dumps(obj, allow_nan=False), encoding="utf-8")


def export_hardness():
    """Pass through the hardness ordering computed by gate3_evaluate.py (per-detector
    X/C selectivity over all 620 days) — never re-typed here."""
    src = PROJECT_ROOT / "data" / "processed" / "reports" / "hardness_ordering.json"
    obj = _load_json(src, "hardness ordering", "run: python scripts/gate3_evaluate.py")
    (OUT / "hardness_ordering.json").write_text(json.dumps(obj, allow_nan=False), encoding="utf-8")


def export_master_catalog(master, swpc, hek):
    su = np.sort(swpc["peak_unix"].to_numpy()); hu = np.sort((hek["peak_utc"].astype("int64") // 10**9).to_numpy())
    def status(mp):
        if np.any(np.abs(su - mp) <= 180): return "confirmed"
        if np.any(np.abs(hu - mp) <= 180): return "sub_threshold"
        return "candidate_novel"
    cls_by_u = {int(u): l for u, l in zip(swpc["peak_unix"], swpc["goes_class"])}
    rows = []
    for r in master.itertuples():
        mp = int(r.master_peak_unix)
        near = [int(u) for u in su if abs(u - mp) <= 180]
        rows.append({"date": pd.Timestamp(mp, unit="s", tz="UTC").strftime("%Y-%m-%d"),
                     "peak": mp, "goes_class": cls_by_u.get(near[0]) if near else None,
                     "n_detectors": int(r.n_detectors), "confidence": jround(r.confidence, 2),
                     "status": status(mp), "saturation_flag": "solexs" in r.detectors})
    rows.sort(key=lambda x: -x["peak"])
    obj = {"total": len(rows), "rows": rows,
           "status_counts": {s: sum(1 for x in rows if x["status"] == s) for s in ("confirmed", "sub_threshold", "candidate_novel")},
           "note": "saturation_flag=true -> SoLEXS is a member; its peak amplitude is saturation-limited (do not size flares by it)."}
    (OUT / "master_catalog.json").write_text(json.dumps(obj, allow_nan=False), encoding="utf-8")


def export_qpp(qpp):
    def attribution(reg):
        return "confirmed_regime" if reg in ("classic", "intermediate") else "pending_instrumental"
    rows = [{"date": pd.Timestamp(r.master_peak_utc).strftime("%Y-%m-%d %H:%M"),
             "peak": int(pd.Timestamp(r.master_peak_utc).value // 10**9),
             "detector": r.detector, "period_s": jround(r.period_s, 1), "regime": r.regime,
             "significance": jround(r.significance_sigma, 1), "n_cycles": jround(r.n_cycles, 0),
             "goes_class": r.goes_class if pd.notna(r.goes_class) else None,
             "solar_attribution": attribution(r.regime)} for r in qpp.itertuples()]
    # candidates = individual significant detections; events = distinct flares.
    tiers = ("classic", "intermediate", "short")
    by_tier_candidates = {t: int((qpp["regime"] == t).sum()) for t in tiers}
    ev = qpp.drop_duplicates("master_peak_utc")
    by_tier_events = {t: int((ev["regime"] == t).sum()) for t in tiers}
    # featured X-class example
    feat = qpp[(qpp.goes_class == "X")].sort_values("significance_sigma", ascending=False)
    featured = None
    if len(feat):
        fr = feat.iloc[0]
        featured = {"date": pd.Timestamp(fr.master_peak_utc).strftime("%Y-%m-%d %H:%M"),
                    "period_s": jround(fr.period_s, 1), "significance": jround(fr.significance_sigma, 1),
                    "n_cycles": jround(fr.n_cycles, 0), "detector": fr.detector}
    obj = {"total_candidates": len(qpp), "total_events": int(qpp["master_peak_utc"].nunique()),
           "by_tier": by_tier_candidates, "by_tier_candidates": by_tier_candidates,
           "by_tier_events": by_tier_events,
           "rows": sorted(rows, key=lambda x: -x["significance"])[:500], "featured_xclass": featured,
           "tier_labels": {"classic": "classic >=16s (robustly solar - lead with these)",
                           "intermediate": "intermediate 8-16s",
                           "short": "short 4-8s (PENDING instrumental cross-check, Inglis 2011)"}}
    (OUT / "qpp_catalog.json").write_text(json.dumps(obj, allow_nan=False), encoding="utf-8")


def main():
    t0 = time.time()
    OUT.mkdir(exist_ok=True); (OUT / "replay_days").mkdir(exist_ok=True)
    models, k, feats, metrics, rel = train_models()
    swpc = pd.read_parquet(PROC / "flares_swpc.parquet").dropna(subset=["peak_utc"]).copy()
    swpc["peak_unix"] = swpc["peak_utc"].astype("int64") // 10**9
    hek = pd.read_parquet(PROC / "flares_hek.parquet").dropna(subset=["peak_utc"])
    master = pd.read_parquet(DET / "master_flare_catalog.parquet")
    qpp = pd.read_parquet(DET / "qpp_catalog.parquet")

    watch_thr, warn_thr = metrics["_alert"]["watch"], metrics["_alert"]["warning"]
    print(f"  alert operating points: Watch(TSS-opt)={watch_thr:.4f}  "
          f"Warning(prec>={PRECISION_TARGET})={warn_thr:.4f}  FAR@TSS={metrics['_alert']['far_at_tss']:.3f}",
          flush=True)
    manifest = {"demo_days": [], "alert": {"watch": jround(watch_thr, 4), "warning": jround(warn_thr, 4),
                                           "far_at_tss": jround(metrics["_alert"]["far_at_tss"], 3)}}
    for day, label, split_lbl, role in DEMO_DAYS:
        o = export_replay_day(day, label, role, models, k, feats, swpc, master, watch_thr, warn_thr)
        xflag = [l for l in o["lead_times"] if l["goes_class"].startswith("X")]
        manifest["demo_days"].append({"date": day, "label": label, "split": split_of(day),
                                      "role": role, "in_sample": o["in_sample"],
                                      "n_flares": len(o["actual_flares"]),
                                      "warning_minutes": o["forecast"]["alert_minutes"]["warning"],
                                      "watch_minutes": o["forecast"]["alert_minutes"]["watch"],
                                      "x_flagged": [{"class": l["goes_class"], "lead_min": l["lead_min"],
                                                     "flagged": l["flagged"]} for l in xflag]})
        xs = "  ".join(f"{x['goes_class']}:{'flagged '+str(x['lead_min'])+'m' if x['flagged'] else 'NOT('+x.get('reason','')+')'}"
                       for x in [l for l in o['lead_times'] if l['goes_class'].startswith('X')])
        print(f"  {day} {label:6s} {split_of(day):5s}  warn_min={o['forecast']['alert_minutes']['warning']:4d}  {xs}", flush=True)
    all_clear = compute_all_clear(metrics["_test15"], swpc)
    print(f"  all-clear (test): quiet->X {all_clear['quiet_flagged']}/{all_clear['n_quiet']}  "
          f"all-X {all_clear['all_flagged']}/{all_clear['n_x']}  ({all_clear['no_coverage']} no-coverage)", flush=True)
    export_summary(metrics, rel, all_clear)
    export_hardness()
    export_master_catalog(master, swpc, hek)
    export_qpp(qpp)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    print(f"\nDONE in {time.time()-t0:.0f}s. Files in {OUT}/", flush=True)


if __name__ == "__main__":
    main()

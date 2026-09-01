"""STAGE 4c — single time-boxed TFT run (CPU), evaluated on the SAME test set
and denominator as XGBoost. Hard rule: if it does not beat XGBoost 15-min TSS,
XGBoost remains the primary model.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.baselines import fit_neupert_k, neupert_residual
from src.forecasting.evaluation import best_threshold, binary_metrics
from src.forecasting.features import feature_names
from src.forecasting.tft_model import (
    FlareTFT, SequenceDataset, focal_loss, predict_proba,
)

FF_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"
REPORTS = PROJECT_ROOT / "data" / "processed" / "reports"
FCAST = PROJECT_ROOT / "data" / "processed" / "forecasts"
TRAIN, VAL, TEST = ("20240701", "20250630"), ("20250701", "20251231"), ("20260101", "20260613")
STATIC = ["f107_lag1", "sunspot_number_lag1", "ar_count_lag1"]
HORIZONS = ["y_15min", "y_30min", "y_60min"]
LOOKBACK = 60
WALLCLOCK_CAP_S = 3000        # ~50 min hard cap for the single run
torch.manual_seed(0); np.random.seed(0)


def build_arrays():
    frames = [pd.read_parquet(f) for f in sorted(FF_DIR.glob("*.parquet"))]
    df = pd.concat(frames, ignore_index=True).sort_values(["day", "utc"]).reset_index(drop=True)
    feats = feature_names(df)
    tr = (df["day"] >= TRAIN[0]) & (df["day"] <= TRAIN[1])
    k = fit_neupert_k(df.loc[tr, "hel1os_hard_rate"].to_numpy(), df.loc[tr, "soft_ddt_5m"].to_numpy())
    df["neupert_resid"] = neupert_residual(df["hel1os_hard_rate"], df["soft_ddt_5m"], k)
    feats = feats + ["neupert_resid"]
    tv_cols = [c for c in feats if c not in STATIC]
    # standardize on train finite values
    mu = df.loc[tr, feats].mean(); sd = df.loc[tr, feats].std().replace(0, 1)
    df[feats] = (df[feats] - mu) / sd
    df[feats] = df[feats].fillna(0.0)          # impute to train mean (0 after z-score)
    df["minute_of_day"] = df["utc"].dt.hour * 60 + df["utc"].dt.minute
    return df, tv_cols


def valid_end_indices(df, lo, hi):
    """Global positions whose trailing 60-min window stays within one day and
    whose end row is in-GTI with a defined target."""
    m = (df["day"] >= lo) & (df["day"] <= hi)
    sub = df[m]
    ok = (sub["minute_of_day"] >= LOOKBACK - 1) & sub["in_gti_any"] & sub["y_15min"].notna()
    return sub.index[ok.to_numpy()].to_numpy()


def main() -> int:
    t0 = time.time()
    print("building arrays ...")
    df, tv_cols = build_arrays()
    tv = df[tv_cols].to_numpy(np.float32)
    st = df[STATIC].to_numpy(np.float32)
    y = df[HORIZONS].to_numpy(np.float32)

    idx_tr = valid_end_indices(df, *TRAIN)
    idx_va = valid_end_indices(df, *VAL)
    idx_te = valid_end_indices(df, *TEST)
    print(f"  valid sequences: train={len(idx_tr)} val={len(idx_va)} test={len(idx_te)}")

    # subsample train for the CPU budget: all positives + 4x negatives
    ytr15 = y[idx_tr, 0]
    pos = idx_tr[ytr15 == 1]; neg = idx_tr[ytr15 == 0]
    rng = np.random.default_rng(0)
    neg_s = rng.choice(neg, size=min(len(neg), 4 * len(pos)), replace=False)
    idx_tr_s = np.concatenate([pos, neg_s]); rng.shuffle(idx_tr_s)
    print(f"  train subsample: {len(idx_tr_s)} ({len(pos)} pos + {len(neg_s)} neg)", flush=True)

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_bf16 = dev.type == "cuda" and torch.cuda.is_bf16_supported()
    amp_dtype = torch.bfloat16 if use_bf16 else torch.float16
    BS_TR, BS_EV = (1024, 2048) if dev.type == "cuda" else (512, 1024)
    print(f"  device={dev} ({torch.cuda.get_device_name(0) if dev.type=='cuda' else 'cpu'})  "
          f"amp={'bf16' if use_bf16 else ('fp16' if dev.type=='cuda' else 'off')}  "
          f"batch_train={BS_TR}", flush=True)
    pin = dev.type == "cuda"
    mk = lambda idx, bs, sh: DataLoader(
        SequenceDataset(tv, st, y, idx, LOOKBACK), batch_size=bs, shuffle=sh,
        num_workers=0, pin_memory=pin)
    dl_tr = mk(idx_tr_s, BS_TR, True)
    # val subsample for fast per-epoch TSS monitoring
    va_mon = rng.choice(idx_va, size=min(len(idx_va), 40000), replace=False)
    dl_va_mon = mk(np.sort(va_mon), BS_EV, False)

    model = FlareTFT(n_tv=len(tv_cols), n_static=len(STATIC)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scaler = torch.cuda.amp.GradScaler(enabled=(dev.type == "cuda" and not use_bf16))
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  model params: {n_params:,}", flush=True)

    best_tss, best_state, patience, bad = -1.0, None, 4, 0
    for epoch in range(1, 21):
        t_ep = time.time()
        model.train(); tl = 0.0
        for xb, sb, yb in dl_tr:
            xb = xb.to(dev, non_blocking=True); sb = sb.to(dev, non_blocking=True)
            yb = yb.to(dev, non_blocking=True)
            opt.zero_grad()
            with torch.autocast(device_type=dev.type, dtype=amp_dtype, enabled=dev.type == "cuda"):
                loss = focal_loss(model(xb, sb), yb)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            tl += loss.item()
        # monitor val TSS (15-min) on subsample
        p_mon, _ = predict_proba(model, dl_va_mon, 3, dev, amp_dtype=amp_dtype)
        ymon = y[np.sort(va_mon), 0]
        _, tss_mon = best_threshold(ymon, p_mon[:, 0])
        elapsed = time.time() - t0
        print(f"  epoch {epoch:2d}  loss={tl/len(dl_tr):.4f}  val15_TSS={tss_mon:.4f}  "
              f"epoch_s={time.time()-t_ep:.1f}  total_s={elapsed:.0f}", flush=True)
        if tss_mon > best_tss:
            best_tss, best_state, bad = tss_mon, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= patience:
                print("  early stop"); break
        if elapsed > WALLCLOCK_CAP_S:
            print("  wallclock cap hit"); break

    model.load_state_dict(best_state)
    # full val (threshold tuning) + full test (eval), same protocol as XGBoost
    dl_va = mk(np.sort(idx_va), BS_EV, False)
    dl_te = mk(np.sort(idx_te), BS_EV, False)
    p_va, _ = predict_proba(model, dl_va, 3, dev, amp_dtype=amp_dtype)
    p_te, te_std = predict_proba(model, dl_te, 3, dev, mc_samples=20, amp_dtype=amp_dtype)
    yva = y[np.sort(idx_va)]; yte = y[np.sort(idx_te)]

    dev_name = torch.cuda.get_device_name(0) if dev.type == "cuda" else "cpu"
    lines = [f"STAGE 4c - TFT (single run, device={dev.type}: {dev_name}, amp={'bf16' if use_bf16 else 'off'})",
             "=" * 60,
             f"params={n_params:,}  lookback={LOOKBACK}min  train_subsample={len(idx_tr_s)}",
             f"valid test sequences={len(idx_te)} (XGBoost test rows=210253; TFT drops the "
             f"first 59 min/day with no full 60-min lookback -> ~4% fewer points, same period)",
             "", "TSS (test), threshold tuned on val:"]
    tft_tss = {}
    for hi, h in enumerate(HORIZONS):
        thr, _ = best_threshold(yva[:, hi], p_va[:, hi])
        m = binary_metrics(yte[:, hi], p_te[:, hi] >= thr)
        tft_tss[h] = m["tss"]
        lines.append(f"  {h}: TSS={m['tss']:.4f} POD={m['pod']:.3f} FAR={m['far']:.3f} HSS={m['hss']:.3f}")
    # variable-selection weights
    vsn = model._last_vsn.cpu().numpy()
    order = np.argsort(-vsn)
    lines.append("\nTFT variable-selection weights - top 15:")
    for r, j in enumerate(order[:15], 1):
        lines.append(f"  {r:>2}. {tv_cols[j]:28s} {vsn[j]:.4f}")
    lines.append(f"\nMC-dropout mean uncertainty (test 15-min std): {np.nanmean(te_std[:,0]):.4f}")

    np.savez(FCAST / "tft_test_predictions.npz",
             p_te=p_te, te_std=te_std, idx_te=np.sort(idx_te),
             yte=yte, p_va=p_va, idx_va=np.sort(idx_va), yva=yva)
    (REPORTS / "tft_metrics.txt").write_text("\n".join(lines), encoding="utf-8")
    # machine-readable sidecar consumed by the dashboard export (no hand-entered
    # numbers downstream — the dashboard reads this file, never a literal).
    import json
    (REPORTS / "tft_metrics.json").write_text(json.dumps(
        {"tss": {h: round(float(tft_tss[h]), 4) for h in HORIZONS},
         "device": dev.type, "params": int(n_params),
         "note": "single time-boxed run; XGBoost remains primary unless TFT beats its 15-min TSS"},
        indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORTS/'tft_metrics.txt'}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

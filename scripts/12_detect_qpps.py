"""STAGE 5 - QPP detection.

Order of operations:
  1. SYNTHETIC-INJECTION SUB-GATE: inject a 30 s sinusoid into flat+noise and
     confirm the wavelet/Vaughan pipeline recovers it at 30 s; also confirm a
     pure red-noise control yields NO significant QPP (false-positive guard).
     -> data/validation/gate5_qpp_synthetic.png   (must pass first)
  2. Run QPP detection on master-catalogue flares (X-class first), using the
     HEL1OS CZT1/CZT2 hard X-ray over each flare's [start, peak] impulsive window.
     -> data/processed/detections/qpp_catalog.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.detect_helpers import LBL_DIR
from src.detection.qpp_detection import (
    detect_qpp, detrend_envelope, fourier_rednoise, morlet_power,
)

DET_DIR = PROJECT_ROOT / "data" / "processed" / "detections"
VALID = PROJECT_ROOT / "data" / "validation"
QPP_PATH = DET_DIR / "qpp_catalog.parquet"
REPORT = PROJECT_ROOT / "data" / "processed" / "reports" / "qpp_report.txt"

CZT_BANDS = {"hel1os_czt1": "hel1os_czt1_18_160kev",
             "hel1os_czt2": "hel1os_czt2_18_160kev"}
CZT_GTI = {"hel1os_czt1": "hel1os_czt1_gti", "hel1os_czt2": "hel1os_czt2_gti"}


# ---------------------------------------------------------------------------
# 1. SYNTHETIC SUB-GATE
# ---------------------------------------------------------------------------
def synthetic_subgate() -> bool:
    rng = np.random.default_rng(20260625)
    n = 600
    t = np.arange(n)
    inj_period = 30.0

    # (a) flat baseline + white noise + injected 30 s sinusoid
    base = 100.0 + 8.0 * np.sin(2 * np.pi * t / inj_period)
    sig = base + rng.normal(0, 3.0, n)

    # (b) pure red-noise control (AR(1)) -> must yield NO QPP
    red = np.zeros(n)
    for i in range(1, n):
        red[i] = 0.95 * red[i - 1] + rng.normal(0, 1.0)
    red = 100.0 + 10.0 * red

    qpps = detect_qpp(sig, "synthetic", dt=1.0)
    recovered = [q for q in qpps if abs(q.period_s - inj_period) <= 4]
    red_qpps = detect_qpp(red, "synthetic_red", dt=1.0)

    fr = fourier_rednoise(detrend_envelope(sig))
    wper = np.geomspace(2, n / 3, 48)
    wp = morlet_power(detrend_envelope(sig), wper)

    fig, ax = plt.subplots(3, 1, figsize=(12, 11), constrained_layout=True)
    ax[0].plot(t, sig, lw=0.7, color="tab:blue")
    ax[0].set_title("(a) Synthetic: flat + white noise + injected 30 s sinusoid")
    ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("rate")

    im = ax[1].pcolormesh(t, wper, wp, shading="auto", cmap="viridis")
    ax[1].axhline(inj_period, color="red", ls="--", lw=1, label="injected 30 s")
    ax[1].set_yscale("log"); ax[1].set_ylabel("period (s)"); ax[1].set_xlabel("time (s)")
    ax[1].set_title("(b) Morlet wavelet power - should concentrate at 30 s")
    ax[1].legend(loc="upper right"); fig.colorbar(im, ax=ax[1], label="power")

    ax[2].loglog(fr["freqs"], fr["periodogram"], color="gray", lw=0.8, label="periodogram")
    ax[2].loglog(fr["freqs"], fr["model"], color="black", lw=1, label="red-noise fit")
    ax[2].loglog(fr["freqs"], fr["model"] * fr["g_crit"] / 2, color="magenta", ls="--",
                 lw=1, label="95% global threshold")
    ax[2].axvline(1 / inj_period, color="red", ls=":", lw=1, label="1/30 s")
    ax[2].set_xlabel("frequency (Hz)"); ax[2].set_ylabel("power")
    ax[2].set_title("(c) Vaughan 2005 red-noise test (power-law fit + global 95%)")
    ax[2].legend(loc="lower left", fontsize=8)

    VALID.mkdir(parents=True, exist_ok=True)
    fig.suptitle("GATE 5 sub-gate - synthetic QPP injection recovery", fontsize=13)
    fig.savefig(VALID / "gate5_qpp_synthetic.png", dpi=140)
    plt.close(fig)

    print("SYNTHETIC SUB-GATE")
    print(f"  injected period: {inj_period} s")
    if recovered:
        q = recovered[0]
        print(f"  RECOVERED at {q.period_s:.1f} s  ({q.significance_sigma:.1f} sigma global)")
    else:
        print(f"  NOT recovered (found: {[round(q.period_s,1) for q in qpps]})")
    print(f"  red-noise control significant QPPs: {len(red_qpps)} (must be 0)")
    ok = bool(recovered) and len(red_qpps) == 0
    print(f"  SUB-GATE: {'PASS' if ok else 'FAIL'}")
    print(f"  wrote {VALID/'gate5_qpp_synthetic.png'}")
    return ok


# ---------------------------------------------------------------------------
# 2. REAL FLARES
# ---------------------------------------------------------------------------
from functools import lru_cache


@lru_cache(maxsize=8)
def _load_day(day: str):
    cols = ["utc"] + list(CZT_BANDS.values()) + list(CZT_GTI.values())
    df = pd.read_parquet(LBL_DIR / f"{day}.parquet", columns=cols)
    u = (df["utc"].astype("int64") // 10**9).to_numpy()
    return u, df


def load_czt_window(day: str, start_unix: int, peak_unix: int, detector: str):
    band, gti = CZT_BANDS[detector], CZT_GTI[detector]
    u, df = _load_day(day)
    m = (u >= start_unix) & (u <= peak_unix) & df[gti].to_numpy(bool)
    return df[band].to_numpy(np.float64)[m]


def run_real_flares(swpc_class_map: dict[int, str]) -> pd.DataFrame:
    master = pd.read_parquet(DET_DIR / "master_flare_catalog.parquet")
    # prioritise the most impulsive: those with a CZT member, X-class first
    master = master.copy()
    master["has_czt"] = master["detectors"].str.contains("czt")
    cand = master[master["has_czt"]].copy()
    cand["day"] = cand["master_peak_utc"].dt.strftime("%Y%m%d")
    print(f"\nREAL FLARES: {len(cand)} master flares have a CZT member")

    records = []
    for _, fl in cand.iterrows():
        start_u, peak_u = int(fl["master_start_unix"]), int(fl["master_peak_unix"])
        if peak_u - start_u < 30:        # need >=30 s impulsive window
            continue
        for det in CZT_BANDS:
            if det not in fl["detectors"]:
                continue
            rate = load_czt_window(fl["day"], start_u, peak_u, det)
            for q in detect_qpp(rate, det):
                records.append({
                    "master_peak_utc": fl["master_peak_utc"],
                    "flare_start_utc": fl["master_start_utc"],
                    "detector": det,
                    "period_s": q.period_s,
                    "time_s_into_rise": q.time_s,
                    "significance_sigma": q.significance_sigma,
                    "global_p": q.global_p,
                    "n_cycles": q.n_cycles,
                    "n_detectors": int(fl["n_detectors"]),
                    "peak_rate_max": float(fl["peak_rate_max"]),
                })
    qpp = pd.DataFrame(records)
    return qpp, master


def main() -> int:
    ok = synthetic_subgate()
    if not ok:
        print("\nSUB-GATE FAILED - not running real flares. Fix the pipeline first.")
        return 1

    # class lookup for reporting (match master peaks to SWPC class)
    swpc = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet")
    swpc = swpc.dropna(subset=["peak_utc"]).copy()
    swpc["u"] = swpc["peak_utc"].astype("int64") // 10**9

    qpp, master = run_real_flares({})
    print(f"\nQPP catalogue: {len(qpp)} significant QPP detections "
          f"in {qpp['master_peak_utc'].nunique() if len(qpp) else 0} distinct flares")

    if len(qpp):
        # assign GOES class to each QPP flare (nearest SWPC within 180s)
        su = np.sort(swpc["u"].to_numpy())
        cls_by_u = dict(zip(swpc["u"], swpc["goes_class_letter"]))
        def nearest_class(ts):
            i = np.searchsorted(su, ts)
            best, bestdt = None, 181
            for k in (i-1, i):
                if 0 <= k < len(su) and abs(su[k]-ts) < bestdt:
                    bestdt = abs(su[k]-ts); best = cls_by_u.get(su[k])
            return best
        qpp_u = (qpp["master_peak_utc"].astype("int64")//10**9)
        qpp["goes_class"] = [nearest_class(int(x)) for x in qpp_u]
        # regime tiers (see GATE 5): classic >=16s is robustly solar; short 4-8s
        # is real signal pending instrumental cross-check; 8-16s intermediate.
        qpp["regime"] = np.where(qpp.period_s >= 16, "classic",
                          np.where(qpp.period_s < 8, "short", "intermediate"))
        QPP_PATH.parent.mkdir(parents=True, exist_ok=True)
        qpp.to_parquet(QPP_PATH, index=False)
        print("\nPeriod distribution (s): "
              f"min={qpp.period_s.min():.1f} median={qpp.period_s.median():.1f} "
              f"max={qpp.period_s.max():.1f}")
        print("QPP flares by class (distinct flares):")
        per = qpp.drop_duplicates("master_peak_utc").groupby("goes_class").size()
        print(per.to_string())
        # overall clearest
        best = qpp.sort_values("significance_sigma", ascending=False).iloc[0]
        print(f"\nClearest QPP overall: {best['master_peak_utc']}  {best['detector']}  "
              f"period={best['period_s']:.1f}s  {best['significance_sigma']:.1f} sigma  "
              f"class={best['goes_class']}  cycles={best['n_cycles']:.1f}")
        # feature an X-class example (mentor prioritised X-class); fall back to overall
        xq = qpp[qpp["goes_class"] == "X"].sort_values("significance_sigma", ascending=False)
        feat = xq.iloc[0] if len(xq) else best
        print(f"Featured X-class QPP: {feat['master_peak_utc']}  {feat['detector']}  "
              f"period={feat['period_s']:.1f}s  {feat['significance_sigma']:.1f} sigma  "
              f"class={feat['goes_class']}  cycles={feat['n_cycles']:.1f}")
        plot_clearest(feat)
    print(f"\nWrote {QPP_PATH}")
    return 0


def plot_clearest(best: pd.Series) -> None:
    day = pd.Timestamp(best["master_peak_utc"]).strftime("%Y%m%d")
    start_u = int(pd.Timestamp(best["flare_start_utc"]).value // 10**9)
    peak_u = int(pd.Timestamp(best["master_peak_utc"]).value // 10**9)
    rate = load_czt_window(day, start_u, peak_u, best["detector"])
    resid = detrend_envelope(rate)
    n = len(resid); t = np.arange(n)
    wper = np.geomspace(2, max(6, n / 3), 48)
    wp = morlet_power(resid, wper)
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    ax[0].plot(t, rate, lw=0.8, color="tab:green", label="CZT rate")
    ax[0].set_title(f"Clearest QPP - {best['master_peak_utc']} {best['detector']} "
                    f"({best['goes_class']}-class, P={best['period_s']:.1f}s, "
                    f"{best['significance_sigma']:.1f} sigma)")
    ax[0].set_xlabel("s into impulsive window"); ax[0].set_ylabel("cts/s"); ax[0].legend()
    im = ax[1].pcolormesh(t, wper, wp, shading="auto", cmap="viridis")
    ax[1].axhline(best["period_s"], color="red", ls="--", label=f"{best['period_s']:.1f}s")
    ax[1].set_yscale("log"); ax[1].set_ylabel("period (s)")
    ax[1].set_xlabel("s into impulsive window")
    ax[1].set_title("Morlet wavelet power"); ax[1].legend(loc="upper right")
    fig.colorbar(im, ax=ax[1], label="power")
    fig.savefig(VALID / "gate5_qpp_clearest.png", dpi=140)
    plt.close(fig)
    print(f"  wrote {VALID/'gate5_qpp_clearest.png'}")


if __name__ == "__main__":
    raise SystemExit(main())

"""STAGE 0 — Phase 3 data precheck (read-only).

Produces data/validation/phase3_precheck.png (6 log-scale panels) and prints
assertions [A]-[F]. Verifies the processed data and our plotting are correct
BEFORE any detection code is written.
"""
from __future__ import annotations

import sys
from datetime import timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
LC_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"
LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
OUT_PNG = PROJECT_ROOT / "data" / "validation" / "phase3_precheck.png"

ANCHOR = "20241003"        # X9.0
GAP_DAY = "20240705"       # known intra-day CdTe1 GTI gap (~21 min)
QUIET_DAY = "20241021"     # 100% quiet day

DETS = [
    ("solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS SDD2", "tab:blue"),
    ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti", "CdTe1", "tab:orange"),
    ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti", "CdTe2", "tab:red"),
    ("hel1os_czt1_18_160kev", "hel1os_czt1_gti", "CZT1", "tab:green"),
    ("hel1os_czt2_18_160kev", "hel1os_czt2_gti", "CZT2", "tab:olive"),
]


def load(date_str: str, cols=None) -> pd.DataFrame:
    df = pd.read_parquet(LC_DIR / f"{date_str}.parquet", columns=cols)
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)
    return df


def gti_log_safe(df: pd.DataFrame, rate_col: str, gti_col: str) -> np.ndarray:
    """Rate with out-of-GTI and non-positive -> NaN (breaks + log-safe)."""
    v = df[rate_col].to_numpy(dtype=np.float64).copy()
    if gti_col in df.columns:
        v[~df[gti_col].to_numpy(dtype=bool)] = np.nan
    v[~(v > 0)] = np.nan
    return v


def boxcar(x: np.ndarray, w: int) -> np.ndarray:
    """NaN-aware boxcar smoothing."""
    s = pd.Series(x)
    return s.rolling(w, center=True, min_periods=max(1, w // 4)).mean().to_numpy()


def main() -> int:
    results: dict[str, str] = {}

    # ── load anchor day ──────────────────────────────────────────────────────
    df = load(ANCHOR)
    t = df["utc"]
    soft = gti_log_safe(df, "solexs_sdd2_total", "solexs_sdd2_gti")
    czt = gti_log_safe(df, "hel1os_czt1_18_160kev", "hel1os_czt1_gti")

    fig, axes = plt.subplots(6, 1, figsize=(14, 20), constrained_layout=True)

    # Panel 1 — SoLEXS soft full day
    ax = axes[0]
    ax.plot(t, soft, color="tab:blue", lw=0.5)
    ax.set_yscale("log"); ax.set_ylabel("cts/s")
    ax.set_title("1. SoLEXS SDD2 soft X-ray — 2024-10-03 (expect smooth rise / slow decay)")
    ax.grid(True, which="both", alpha=0.25)

    # Panel 2 — CZT1 hard full day
    ax = axes[1]
    ax.plot(t, czt, color="tab:green", lw=0.5)
    ax.set_yscale("log"); ax.set_ylabel("cts/s")
    ax.set_title("2. HEL1OS CZT1 hard X-ray 18-160 keV — 2024-10-03 (expect sharper/spikier)")
    ax.grid(True, which="both", alpha=0.25)

    # Panel 3 — Neupert check, zoom 12:00-12:45
    ax = axes[2]
    zlo = pd.Timestamp("2024-10-03 12:00", tz="UTC")
    zhi = pd.Timestamp("2024-10-03 12:45", tz="UTC")
    m = (t >= zlo) & (t <= zhi)
    soft_z = soft.copy()
    soft_sm = boxcar(soft_z, 60)
    dsoft = np.gradient(soft_sm)            # per-second derivative of soft
    dsoft_sm = boxcar(dsoft, 60)
    # rates on log (left), derivative on linear twin (right)
    ax.plot(t[m], soft[m], color="tab:blue", lw=0.8, label="SoLEXS soft (log L)")
    ax.plot(t[m], czt[m], color="tab:green", lw=0.8, label="CZT hard (log L)")
    ax.set_yscale("log"); ax.set_ylabel("cts/s (log)")
    ax2 = ax.twinx()
    ax2.plot(t[m], dsoft_sm[m], color="purple", lw=1.4, ls="--",
             label="d(SoLEXS soft)/dt smoothed (linear R)")
    ax2.set_ylabel("d(soft)/dt  (cts/s/s, linear)")
    ax.set_title("3. NEUPERT CHECK 12:00-12:45 — CZT hard (green) should track d(soft)/dt (purple)")
    ax.grid(True, which="both", alpha=0.25)
    l1, lab1 = ax.get_legend_handles_labels()
    l2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, lab1 + lab2, loc="upper right", fontsize=8)

    # Panel 4 — SoLEXS + GOES XRSB dual axis
    ax = axes[3]
    lbl = pd.read_parquet(LBL_DIR / f"{ANCHOR}.parquet", columns=["utc", "goes_xrsb_flux"])
    if not pd.api.types.is_datetime64_any_dtype(lbl["utc"]):
        lbl["utc"] = pd.to_datetime(lbl["utc"], utc=True)
    ax.plot(t, soft, color="tab:blue", lw=0.5, label="SoLEXS soft")
    ax.set_yscale("log"); ax.set_ylabel("SoLEXS cts/s", color="tab:blue")
    axg = ax.twinx()
    g = lbl["goes_xrsb_flux"].to_numpy()
    g[~(g > 0)] = np.nan
    axg.plot(lbl["utc"], g, color="tab:red", lw=0.7, label="GOES XRSB")
    axg.set_yscale("log"); axg.set_ylabel("GOES XRSB W/m^2", color="tab:red")
    ax.set_title("4. SoLEXS soft + GOES XRSB (dual log y) — peaks should align")
    ax.grid(True, which="both", alpha=0.25)

    # Panel 5 — GTI gap day, verify break not interpolation
    ax = axes[4]
    dfg = load(GAP_DAY)
    cdte_masked = gti_log_safe(dfg, "hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti")
    # naive (interpolated) reference for contrast: raw values, no gti mask
    raw = dfg["hel1os_cdte1_1p8_90kev"].to_numpy(dtype=np.float64).copy()
    raw[~(raw > 0)] = np.nan
    gti_false = ~dfg["hel1os_cdte1_gti"].to_numpy(dtype=bool)
    ax.plot(dfg["utc"], cdte_masked, color="tab:orange", lw=0.6,
            label="CdTe1 GTI-masked (breaks at gap)")
    # shade the gap
    if gti_false.any():
        ax.fill_between(dfg["utc"], 0, 1, where=gti_false,
                        transform=ax.get_xaxis_transform(),
                        color="gray", alpha=0.25, step="mid", label="GTI=False (gap)")
    ax.set_yscale("log"); ax.set_ylabel("cts/s")
    ax.set_title(f"5. GTI-gap day {GAP_DAY} CdTe1 — gap must be a BREAK, not interpolated")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper right", fontsize=8)

    # Panel 6 — quiet day, all 5 detectors
    ax = axes[5]
    dfq = load(QUIET_DAY)
    tq = dfq["utc"]
    floors = {}
    for rate_col, gti_col, label, color in DETS:
        v = gti_log_safe(dfq, rate_col, gti_col)
        ax.plot(tq, v, color=color, lw=0.4, label=label, alpha=0.8)
        floors[label] = float(np.nanmedian(v)) if np.isfinite(v).any() else float("nan")
    ax.set_yscale("log"); ax.set_ylabel("cts/s")
    ax.set_title(f"6. Quiet day {QUIET_DAY} — all 5 detector noise floors")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper right", fontsize=8, ncol=5)

    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("UT")
    fig.suptitle("Phase 3 STAGE 0 — data precheck (all flux panels log y)", fontsize=14)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=130)
    plt.close(fig)
    print(f"Wrote {OUT_PNG}\n")

    # ── ASSERTIONS ───────────────────────────────────────────────────────────
    print("ASSERTIONS")
    print("-" * 64)

    # [A] hard peak <= soft peak (Neupert) for X9.0
    soft_peak_t = t.iloc[int(np.nanargmax(soft))]
    czt_peak_t = t.iloc[int(np.nanargmax(czt))]
    a_pass = czt_peak_t <= soft_peak_t
    results["A"] = "PASS" if a_pass else "FAIL"
    print(f"[A] Neupert: CZT1 peak ({czt_peak_t:%H:%M:%S}) <= SoLEXS peak "
          f"({soft_peak_t:%H:%M:%S})  -> {results['A']}")

    # [B] every flux panel log
    flux_axes = [axes[0], axes[1], axes[5]]  # pure-flux panels
    # panels 2(idx2),3(idx3),4 mix; check their primary scale is log too
    log_ok = all(a.get_yscale() == "log" for a in axes)
    results["B"] = "PASS" if log_ok else "FAIL"
    print(f"[B] All 6 panels' primary y-axis = log -> {results['B']}")

    # [C] GTI gaps are NaN, not interpolated
    gap_vals = cdte_masked[gti_false]
    c_pass = bool(gti_false.any()) and bool(np.all(np.isnan(gap_vals)))
    results["C"] = "PASS" if c_pass else "FAIL"
    print(f"[C] GTI-gap seconds are NaN on {GAP_DAY} "
          f"({int(gti_false.sum())} gap-sec, all NaN={np.all(np.isnan(gap_vals))}) "
          f"-> {results['C']}")

    # [D] SoLEXS peak vs GOES XRSB peak within 3 min on Oct 3
    gv = lbl["goes_xrsb_flux"].to_numpy()
    gv2 = gv.copy(); gv2[~(gv2 > 0)] = np.nan
    goes_peak_t = lbl["utc"].iloc[int(np.nanargmax(gv2))]
    dmin = abs((soft_peak_t - goes_peak_t).total_seconds()) / 60.0
    d_pass = dmin <= 3.0
    results["D"] = "PASS" if d_pass else "FAIL"
    print(f"[D] SoLEXS peak {soft_peak_t:%H:%M} vs GOES XRSB peak {goes_peak_t:%H:%M}: "
          f"{dmin:.1f} min apart -> {results['D']}")

    # [E] quiet-day baselines physically sane
    print(f"[E] Quiet-day {QUIET_DAY} median count rates (cts/s):")
    for k, v in floors.items():
        print(f"      {k:14s} {v:10.2f}")
    czt_floor = np.nanmean([floors.get("CZT1", np.nan), floors.get("CZT2", np.nan)])
    cdte_floor = np.nanmean([floors.get("CdTe1", np.nan), floors.get("CdTe2", np.nan)])
    e_pass = (np.isfinite(floors.get("SoLEXS SDD2", np.nan))
              and 10 <= floors["SoLEXS SDD2"] <= 5000
              and czt_floor > cdte_floor)
    results["E"] = "PASS" if e_pass else "CHECK"
    print(f"      SoLEXS in [10,5000]={10 <= floors.get('SoLEXS SDD2',0) <= 5000}, "
          f"CZT({czt_floor:.1f}) > CdTe({cdte_floor:.1f})={czt_floor>cdte_floor} "
          f"-> {results['E']}")

    # [F] across all 620 days, per-detector >=90% GTI coverage count
    print("[F] Per-detector days with >=90% GTI coverage (of 620):")
    gti_cols = {d[2]: d[1] for d in DETS}
    counts = {k: 0 for k in gti_cols}
    n_days = 0
    for p in sorted(LC_DIR.glob("*.parquet")):
        cols = list(gti_cols.values())
        d = pd.read_parquet(p, columns=cols)
        n_days += 1
        for label, gcol in gti_cols.items():
            if d[gcol].mean() >= 0.90:
                counts[label] += 1
    for label in gti_cols:
        print(f"      {label:14s} {counts[label]:4d}/{n_days}  "
              f"({100*counts[label]/n_days:.1f}%)")
    results["F"] = "INFO"

    print("\nSUMMARY:", "  ".join(f"{k}:{v}" for k, v in results.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

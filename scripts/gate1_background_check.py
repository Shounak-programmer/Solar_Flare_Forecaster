"""GATE 1 — verify label-aware background on the X9.0 day (read-only).

Plots count rate, background, and bg+N*sigma for SoLEXS and CZT1 on 2024-10-03
(log y) and prints background/sigma/peak-excess stats. Confirms the background
tracks the quiet floor and does not climb into the flare.
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
from src.detection.background import rolling_background
from src.detection.significance import excess_significance, poisson_sigma

LBL = PROJECT_ROOT / "data" / "processed" / "labeled_seconds" / "20241003.parquet"
OUT = PROJECT_ROOT / "data" / "validation" / "gate1_background.png"
PEAK = pd.Timestamp("2024-10-03 12:18", tz="UTC")
N_SIGMA = 5
SPECS = [
    ("solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS SDD2", "tab:blue"),
    ("hel1os_czt1_18_160kev", "hel1os_czt1_gti", "HEL1OS CZT1", "tab:green"),
]


def main() -> int:
    df = pd.read_parquet(LBL)
    df["utc"] = pd.to_datetime(df["utc"], utc=True)
    t = df["utc"]
    isf = df["is_flare"].to_numpy()
    pidx = int(np.argmin(np.abs((t - PEAK).values)))
    w = ((t >= PEAK - pd.Timedelta(minutes=15)) & (t <= PEAK + pd.Timedelta(minutes=15))).to_numpy()
    pre = ((t >= pd.Timestamp("2024-10-03 11:00", tz="UTC"))
           & (t < pd.Timestamp("2024-10-03 12:00", tz="UTC"))).to_numpy()

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True, constrained_layout=True)
    print("GATE 1 REPORT - X9.0 day 2024-10-03")
    print("=" * 60)
    for ax, (rate, gti, label, color) in zip(axes, SPECS):
        cr = df[rate].to_numpy(float)
        g = df[gti].to_numpy(bool)
        bg = rolling_background(cr, g, is_flare=isf)
        sig = poisson_sigma(bg)
        ex = excess_significance(cr, bg)

        crp = cr.copy(); crp[~g] = np.nan; crp[~(crp > 0)] = np.nan
        bgp = bg.copy(); bgp[~(bgp > 0)] = np.nan
        band = bg + N_SIGMA * sig; band[~(band > 0)] = np.nan
        ax.plot(t, crp, color=color, lw=0.4, label=f"{label} count rate")
        ax.plot(t, bgp, color="black", lw=1.1, label="background (label-aware, +/-30min dilation)")
        ax.plot(t, band, color="magenta", lw=0.7, ls="--", label=f"bg + {N_SIGMA} sigma")
        ax.axvline(PEAK, color="red", ls=":", lw=1, label="X9.0 12:18")
        ax.set_yscale("log"); ax.set_ylabel("cts/s"); ax.set_title(label)
        ax.grid(True, which="both", alpha=0.25); ax.legend(loc="upper left", fontsize=8)

        bg_pre = np.nanmedian(bg[pre & g])
        print(f"\n{label}:")
        print(f"  bg pre-flare 11:00-12:00 (quiet floor): {bg_pre:8.1f} cts/s")
        print(f"  bg at 12:18 peak:                       {bg[pidx]:8.1f} cts/s")
        print(f"  bg max within +/-15min:                 {np.nanmax(bg[w]):8.1f} cts/s")
        print(f"  sigma at peak:                          {sig[pidx]:8.2f}")
        print(f"  PEAK EXCESS (sigma):                    {np.nanmax(ex[w]):8.0f}")
        ratio = bg[pidx] / max(bg_pre, 1)
        print(f"  bg_at_peak / floor:                     {ratio:8.2f}x -> "
              f"{'OK stays at floor' if ratio < 2.5 else 'WARN rises'}")

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("UT on 2024-10-03")
    fig.suptitle("GATE 1 - label-aware background (+/-30min dilation) vs X9.0", fontsize=13)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=140)
    plt.close(fig)
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

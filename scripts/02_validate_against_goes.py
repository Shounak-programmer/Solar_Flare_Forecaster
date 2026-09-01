"""Phase 1 validation — plot the 2024-10-03 X9.0 flare in SoLEXS + HEL1OS.

Reads ``data/processed/daily_lightcurves/20241003.parquet`` and plots:

  - SoLEXS SDD2 (soft X-ray total)
  - HEL1OS CdTe1 5–20 keV (hard X-ray, low-energy)
  - HEL1OS CZT1 20–40 keV (hard X-ray, mid-energy)

with a vertical reference line at the GOES X9.0 peak (12:18 UT on 2024-10-03).

Output: ``data/validation/oct3_2024_phase1.png``

The plot should show a clear, simultaneous spike in all three panels at the
GOES peak. If a detector's GTI is False over the flare window, the panel is
annotated accordingly (still plotted, just flagged).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"
OUT_PATH = PROJECT_ROOT / "data" / "validation" / "oct3_2024_phase1.png"

DATE = "20241003"
GOES_PEAK = datetime(2024, 10, 3, 12, 18, tzinfo=timezone.utc)

PANELS = [
    ("solexs_sdd2_total",      "solexs_sdd2_gti",     "SoLEXS SDD2 (total)",   "tab:blue"),
    ("hel1os_cdte1_5_20kev",   "hel1os_cdte1_gti",    "HEL1OS CdTe1 5–20 keV", "tab:orange"),
    ("hel1os_czt1_20_40kev",   "hel1os_czt1_gti",     "HEL1OS CZT1 20–40 keV", "tab:red"),
]


def main() -> int:
    pq = PARQUET_DIR / f"{DATE}.parquet"
    if not pq.exists():
        print(f"ERROR: {pq} not found. Build it first with:\n"
              f"  python scripts/01_build_daily_lightcurves.py --date {DATE}",
              file=sys.stderr)
        return 1

    df = pd.read_parquet(pq)
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        len(PANELS), 1, figsize=(12, 8), sharex=True, constrained_layout=True
    )

    # Restrict view to a 4 h window around the peak so the spike is visible.
    t_lo = pd.Timestamp(GOES_PEAK) - pd.Timedelta(hours=2)
    t_hi = pd.Timestamp(GOES_PEAK) + pd.Timedelta(hours=2)
    win = df[(df["utc"] >= t_lo) & (df["utc"] <= t_hi)]

    peak_row = df.iloc[(df["utc"] - pd.Timestamp(GOES_PEAK)).abs().argsort()[:1]]
    peak_idx = peak_row.index[0]
    peak_gti_window = df.loc[peak_idx - 30 : peak_idx + 30]

    for ax, (rate_col, gti_col, label, color) in zip(axes, PANELS):
        if rate_col not in win.columns:
            ax.text(0.5, 0.5, f"missing column: {rate_col}",
                    ha="center", va="center", transform=ax.transAxes)
            continue

        ax.plot(win["utc"], win[rate_col], color=color, lw=0.6, label=label)
        ax.axvline(GOES_PEAK, color="black", ls="--", lw=1.2,
                   label="GOES X9.0 peak 12:18 UT")
        ax.set_ylabel("cts/s")
        ax.set_title(label)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)

        n_valid = int(win[rate_col].notna().sum())
        peak_gti_ok = bool(peak_gti_window[gti_col].any()) if gti_col in df.columns else False
        msg = f"valid samples in ±2h window: {n_valid}"
        if not peak_gti_ok:
            msg += "  [GTI=False at peak ±30s]"
        ax.text(0.01, 0.97, msg, transform=ax.transAxes,
                ha="left", va="top", fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8))

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("UT on 2024-10-03")
    fig.suptitle("Aditya-L1 Phase 1 validation — 2024-10-03 X9.0 flare",
                 fontsize=13)

    fig.savefig(OUT_PATH, dpi=140)
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")

    # Summary stats so the run output alone tells you if validation passed.
    print("\nPer-panel summary (±2 h window):")
    for rate_col, gti_col, label, _ in PANELS:
        if rate_col not in df.columns:
            continue
        col = win[rate_col]
        gti_ok = bool(peak_gti_window[gti_col].any()) if gti_col in df.columns else False
        if col.notna().any():
            mx = float(col.max())
            mx_t = win.loc[col.idxmax(), "utc"]
            print(f"  {label:30s}  max={mx:10.2f} cts/s at {mx_t}  "
                  f"peak_gti={gti_ok}")
        else:
            print(f"  {label:30s}  NO DATA in window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

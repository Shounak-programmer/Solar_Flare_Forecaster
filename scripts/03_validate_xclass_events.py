"""Reproduce the Phase 1 validation plot for arbitrary X-class events.

For each (date, peak_utc, goes_class) entry below:
  - Load the daily Parquet (plus the next day if the ±2h window crosses 00:00).
  - Plot SoLEXS SDD2, HEL1OS CdTe1 5-20 keV, HEL1OS CZT1 20-40 keV.
  - Mark the GOES peak with a vertical line.
  - Print per-detector peak times so alignment with GOES can be verified.

Save to data/validation/{YYYYMMDD}_phase1.png.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"
OUT_DIR = PROJECT_ROOT / "data" / "validation"

EVENTS = [
    # (peak_utc, goes_class) — top two X-class events after 2024-07-01
    # (excluding the X9.0 already validated in 02_validate_against_goes.py)
    (datetime(2026, 2, 1, 23, 57, tzinfo=timezone.utc), "X8.1"),
    (datetime(2024, 10, 1, 22, 20, tzinfo=timezone.utc), "X7.1"),
]

PANELS = [
    ("solexs_sdd2_total",    "solexs_sdd2_gti",  "SoLEXS SDD2 (total)",     "tab:blue"),
    ("hel1os_cdte1_5_20kev", "hel1os_cdte1_gti", "HEL1OS CdTe1 5-20 keV",   "tab:orange"),
    ("hel1os_czt1_20_40kev", "hel1os_czt1_gti",  "HEL1OS CZT1 20-40 keV",   "tab:red"),
]


def load_window(peak: datetime, hours: float = 2.0) -> pd.DataFrame:
    """Load enough daily parquets to cover [peak-h, peak+h]."""
    t_lo = peak - timedelta(hours=hours)
    t_hi = peak + timedelta(hours=hours)
    days_needed: list[str] = []
    cur = t_lo.date()
    while cur <= t_hi.date():
        days_needed.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    frames = []
    for d in days_needed:
        p = PARQUET_DIR / f"{d}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"missing {p}")
        frames.append(pd.read_parquet(p))
    df = pd.concat(frames, ignore_index=True)
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)
    df = df[(df["utc"] >= pd.Timestamp(t_lo)) & (df["utc"] <= pd.Timestamp(t_hi))]
    return df.reset_index(drop=True)


def plot_event(peak: datetime, goes_class: str) -> None:
    win = load_window(peak, hours=2.0)
    date_str = peak.strftime("%Y%m%d")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{date_str}_phase1.png"

    fig, axes = plt.subplots(
        len(PANELS), 1, figsize=(12, 8), sharex=True, constrained_layout=True
    )
    for ax, (rate_col, gti_col, label, color) in zip(axes, PANELS):
        if rate_col not in win.columns:
            ax.text(0.5, 0.5, f"missing: {rate_col}", ha="center", va="center",
                    transform=ax.transAxes)
            continue
        ax.plot(win["utc"], win[rate_col], color=color, lw=0.6, label=label)
        ax.axvline(peak, color="black", ls="--", lw=1.2,
                   label=f"GOES {goes_class} peak {peak:%H:%M} UT")
        ax.set_ylabel("cts/s")
        ax.set_title(label)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)
        n_valid = int(win[rate_col].notna().sum())
        msg = f"valid samples: {n_valid}"
        ax.text(0.01, 0.97, msg, transform=ax.transAxes, ha="left", va="top",
                fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel(f"UT on {peak:%Y-%m-%d}")
    fig.suptitle(f"Phase 1 validation - {peak:%Y-%m-%d} {goes_class}", fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"Wrote {out_path}")

    # Per-detector peak times for alignment check.
    print(f"\nEvent: {goes_class} GOES peak = {peak.isoformat()}")
    for rate_col, gti_col, label, _ in PANELS:
        col = win[rate_col]
        if not col.notna().any():
            print(f"  {label:30s}  NO DATA")
            continue
        i = col.idxmax()
        t_peak = win.loc[i, "utc"]
        delta = (t_peak - pd.Timestamp(peak)).total_seconds()
        sign = "+" if delta >= 0 else "-"
        print(f"  {label:30s}  max={float(col.max()):10.2f} cts/s  "
              f"at {t_peak}  ({sign}{abs(delta):.0f}s vs GOES)")


def main() -> int:
    for peak, gclass in EVENTS:
        plot_event(peak, gclass)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

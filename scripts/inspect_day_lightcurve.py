"""Inspect & plot one processed day's light curves (read-only).

Usage: python scripts/inspect_day_lightcurve.py YYYYMMDD

Four log-scale panels (SoLEXS / CdTe1+2 / CZT1+2 / all-five), GTI gaps shown as
line breaks, is_flare regions shaded, SWPC flare peaks marked.
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
LC_DIR = PROJECT_ROOT / "data" / "processed" / "daily_lightcurves"
LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
OUT_DIR = PROJECT_ROOT / "data" / "validation"


def gti_masked(df: pd.DataFrame, rate_col: str, gti_col: str) -> np.ndarray:
    """Return rate values with out-of-GTI and non-positive set to NaN, so the
    line breaks at gaps and log scale is safe."""
    v = df[rate_col].to_numpy(dtype=np.float64).copy()
    if gti_col in df.columns:
        v[~df[gti_col].to_numpy(dtype=bool)] = np.nan
    v[~(v > 0)] = np.nan  # log-safe; also drops zero-count seconds
    return v


def annotate_peak(ax, t, v, label):
    finite = np.isfinite(v)
    if not finite.any():
        return
    i = int(np.nanargmax(v))
    pk_t, pk_v = t.iloc[i], v[i]
    ax.annotate(f"{label} peak {pk_v:,.0f} cts/s @ {pk_t:%H:%M:%S}",
                xy=(pk_t, pk_v), xytext=(0.99, 0.95),
                textcoords="axes fraction", ha="right", va="top", fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.8))


def main() -> int:
    date_str = sys.argv[1] if len(sys.argv) > 1 else "20251114"
    lc_path = LC_DIR / f"{date_str}.parquet"
    if not lc_path.exists():
        print(f"No daily LC parquet for {date_str}")
        return 1
    df = pd.read_parquet(lc_path)
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)
    t = df["utc"]

    lbl = None
    lbl_path = LBL_DIR / f"{date_str}.parquet"
    if lbl_path.exists():
        lbl = pd.read_parquet(lbl_path, columns=["utc", "is_flare"])
        if not pd.api.types.is_datetime64_any_dtype(lbl["utc"]):
            lbl["utc"] = pd.to_datetime(lbl["utc"], utc=True)

    # SWPC flares this day
    fl = pd.read_parquet(PROJECT_ROOT / "data" / "processed" / "flares_swpc.parquet")
    day0 = pd.Timestamp(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}", tz="UTC")
    flares = fl[(fl.peak_utc >= day0) & (fl.peak_utc < day0 + pd.Timedelta(days=1))]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True,
                             constrained_layout=True)

    panels = [
        ("SoLEXS SDD2 total", [("solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS SDD2", "tab:blue")]),
        ("HEL1OS CdTe 1.8-90 keV", [
            ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti", "CdTe1", "tab:orange"),
            ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti", "CdTe2", "tab:red")]),
        ("HEL1OS CZT 18-160 keV", [
            ("hel1os_czt1_18_160kev", "hel1os_czt1_gti", "CZT1", "tab:green"),
            ("hel1os_czt2_18_160kev", "hel1os_czt2_gti", "CZT2", "tab:olive")]),
        ("All five detectors (total bands)", [
            ("solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS", "tab:blue"),
            ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti", "CdTe1", "tab:orange"),
            ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti", "CdTe2", "tab:red"),
            ("hel1os_czt1_18_160kev", "hel1os_czt1_gti", "CZT1", "tab:green"),
            ("hel1os_czt2_18_160kev", "hel1os_czt2_gti", "CZT2", "tab:olive")]),
    ]

    for ax, (title, series) in zip(axes, panels):
        # shade is_flare regions
        if lbl is not None:
            isf = lbl["is_flare"].to_numpy()
            ax.fill_between(lbl["utc"], 0, 1, where=isf == 1,
                            transform=ax.get_xaxis_transform(),
                            color="orange", alpha=0.15, step="mid",
                            label="is_flare==1", zorder=0)
        peak_v = -1.0
        peak_lbl = ""
        for rate_col, gti_col, label, color in series:
            v = gti_masked(df, rate_col, gti_col)
            ax.plot(t, v, color=color, lw=0.6, label=label)
            if np.isfinite(v).any() and np.nanmax(v) > peak_v:
                peak_v = np.nanmax(v)
                peak_series = v
                peak_lbl = label
        if peak_v > 0:
            annotate_peak(ax, t, peak_series, peak_lbl)
        # flare peak verticals
        for _, fr in flares.iterrows():
            ax.axvline(fr.peak_utc, color="black", ls="--", lw=0.6, alpha=0.5)
        ax.set_yscale("log")
        ax.set_ylabel("cts/s")
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(loc="upper left", fontsize=8, ncol=3)

    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlim(day0, day0 + pd.Timedelta(days=1))
    axes[-1].set_xlabel(f"UT on {day0:%Y-%m-%d}")
    fig.suptitle(f"Aditya-L1 light curves — {day0:%Y-%m-%d}  "
                 f"({len(flares)} SWPC flares; dashed = flare peaks)", fontsize=13)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"lightcurve_{date_str}.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")

    # Per-detector peak report
    print("\nPer-detector peaks (in-GTI, log-positive):")
    for rate_col, gti_col, label in [
        ("solexs_sdd2_total", "solexs_sdd2_gti", "SoLEXS SDD2"),
        ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti", "HEL1OS CdTe1"),
        ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti", "HEL1OS CdTe2"),
        ("hel1os_czt1_18_160kev", "hel1os_czt1_gti", "HEL1OS CZT1"),
        ("hel1os_czt2_18_160kev", "hel1os_czt2_gti", "HEL1OS CZT2"),
    ]:
        v = gti_masked(df, rate_col, gti_col)
        if np.isfinite(v).any():
            i = int(np.nanargmax(v))
            print(f"  {label:16s} max={np.nanmax(v):10,.0f} cts/s at {t.iloc[i]:%H:%M:%S} UT")
        else:
            print(f"  {label:16s} no in-GTI data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

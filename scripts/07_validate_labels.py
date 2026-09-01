"""Phase 2 label validation — asserts known X-class events have correct labels.

For each (date, peak_time, class_letter, class_mag), check that the labeled
parquet has:
  - is_flare == 1 at the peak second
  - flare_class_letter and ~ flare_class_magnitude correct
  - flare_in_next_30min == 1 thirty minutes before the peak

Also produces 4-panel plots at data/validation/labels_{date}.png for visual
inspection.
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
LABELED_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"
OUT_DIR = PROJECT_ROOT / "data" / "validation"

EVENTS = [
    ("20241003", datetime(2024, 10, 3, 12, 18, tzinfo=timezone.utc), "X", 9.0),
    ("20241001", datetime(2024, 10, 1, 22, 20, tzinfo=timezone.utc), "X", 7.1),
    ("20260201", datetime(2026, 2, 1, 23, 57, tzinfo=timezone.utc), "X", 8.1),
]


def _nearest_row(df: pd.DataFrame, ts: datetime) -> pd.Series:
    ts_p = pd.Timestamp(ts)
    i = (df["utc"] - ts_p).abs().idxmin()
    return df.loc[i]


def validate_one(date_str: str, peak: datetime, expect_letter: str,
                 expect_mag: float) -> tuple[bool, list[str]]:
    pq = LABELED_DIR / f"{date_str}.parquet"
    if not pq.exists():
        return False, [f"missing parquet {pq}"]
    df = pd.read_parquet(pq)
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)

    errs: list[str] = []
    peak_row = _nearest_row(df, peak)
    if int(peak_row["is_flare"]) != 1:
        errs.append(f"is_flare!=1 at peak ({peak_row['utc']})")
    got_letter = peak_row["flare_class_letter"]
    if str(got_letter) != expect_letter:
        errs.append(f"flare_class_letter={got_letter} != {expect_letter}")
    got_mag = peak_row["flare_class_magnitude"]
    if pd.isna(got_mag) or abs(float(got_mag) - expect_mag) > 0.5:
        errs.append(f"flare_class_magnitude={got_mag} != ~{expect_mag}")

    pre30_row = _nearest_row(df, peak - pd.Timedelta(minutes=30))
    if int(pre30_row["flare_in_next_30min"]) != 1:
        errs.append(f"flare_in_next_30min!=1 at peak-30min")

    midnight_row = _nearest_row(df, peak.replace(hour=0, minute=0, second=0))
    # next_60min at 00:00:00 should usually be 0 (no flare in first hour for these days)
    if int(midnight_row["flare_in_next_60min"]) == 1:
        errs.append(f"flare_in_next_60min=1 at midnight (unexpected for these days)")

    return len(errs) == 0, errs


def plot_one(date_str: str, peak: datetime, expect_letter: str,
             expect_mag: float) -> Path:
    df = pd.read_parquet(LABELED_DIR / f"{date_str}.parquet")
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)

    # ±2h window
    t_lo = pd.Timestamp(peak) - pd.Timedelta(hours=2)
    t_hi = pd.Timestamp(peak) + pd.Timedelta(hours=2)
    # crosses midnight? load adjacent day too
    if t_lo.date() != t_hi.date():
        for d_off in (-1, 1):
            other = (peak.date() + pd.Timedelta(days=d_off)).strftime("%Y%m%d")
            p = LABELED_DIR / f"{other}.parquet"
            if p.exists():
                df2 = pd.read_parquet(p)
                if not pd.api.types.is_datetime64_any_dtype(df2["utc"]):
                    df2["utc"] = pd.to_datetime(df2["utc"], utc=True)
                df = pd.concat([df, df2], ignore_index=True)
    win = df[(df["utc"] >= t_lo) & (df["utc"] <= t_hi)].sort_values("utc")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"labels_{date_str}.png"

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True,
                             constrained_layout=True)
    # 1. SoLEXS soft X-ray
    ax = axes[0]
    ax.plot(win["utc"], win["solexs_sdd2_total"], color="tab:blue", lw=0.6)
    ax.set_ylabel("SoLEXS SDD2\ncts/s")
    ax.set_title("SoLEXS soft X-ray light curve")
    ax.grid(True, alpha=0.3)

    # 2. is_flare colored region
    ax = axes[1]
    ax.plot(win["utc"], win["solexs_sdd2_total"], color="lightgray", lw=0.5)
    ax.fill_between(win["utc"], 0, win["solexs_sdd2_total"].max(),
                    where=win["is_flare"] == 1, color="tab:orange", alpha=0.45,
                    label="is_flare == 1")
    ax.set_ylabel("is_flare overlay")
    ax.set_title("is_flare (active flare window from SWPC catalog)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # 3. flare_in_next_30min
    ax = axes[2]
    ax.plot(win["utc"], win["solexs_sdd2_total"], color="lightgray", lw=0.5)
    ax.fill_between(win["utc"], 0, win["solexs_sdd2_total"].max(),
                    where=win["flare_in_next_30min"] == 1,
                    color="tab:green", alpha=0.4,
                    label="flare_in_next_30min == 1")
    ax.set_ylabel("forecast overlay")
    ax.set_title("flare_in_next_30min (30-min precursor window)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # 4. GOES xrsb
    ax = axes[3]
    if win["goes_xrsb_flux"].notna().any():
        ax.plot(win["utc"], win["goes_xrsb_flux"], color="tab:red", lw=0.8,
                label="GOES xrsb_flux (joined)")
        ax.set_yscale("log")
    else:
        ax.text(0.5, 0.5, "no GOES data joined for this window",
                ha="center", va="center", transform=ax.transAxes)
    ax.set_ylabel("xrsb_flux\nW/m^2")
    ax.set_title("GOES XRS-B (joined per-second from 1-min grid)")
    ax.legend(loc="upper right")
    ax.grid(True, which="both", alpha=0.3)

    for ax in axes:
        ax.axvline(peak, color="black", ls="--", lw=1.0,
                   label=f"GOES {expect_letter}{expect_mag} peak {peak:%H:%M} UT")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel(f"UT on {peak:%Y-%m-%d}")
    fig.suptitle(f"Phase 2 labels — {peak:%Y-%m-%d} {expect_letter}{expect_mag}",
                 fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    return out_path


def class_distribution(date_str: str) -> None:
    df = pd.read_parquet(LABELED_DIR / f"{date_str}.parquet")
    total = len(df)
    print(f"\nClass distribution for {date_str} (whole day, {total} sec):")
    print(f"  {'class':>10} {'seconds':>10} {'percent':>8}")
    quiet = (df["is_flare"] == 0).sum()
    print(f"  {'quiet':>10} {int(quiet):>10} {100.0 * quiet / total:>7.2f}%")
    for L in ("B", "C", "M", "X"):
        n = int((df["flare_class_letter"] == L).sum())
        print(f"  {L:>10} {n:>10} {100.0 * n / total:>7.2f}%")
    print(f"\nPhase distribution for {date_str}:")
    for ph in ("quiet", "pre", "rise", "peak", "decay"):
        n = int((df["flare_phase"] == ph).sum())
        print(f"  {ph:>10} {n:>10} {100.0 * n / total:>7.2f}%")


def main() -> int:
    all_ok = True
    for ds, peak, letter, mag in EVENTS:
        pq = LABELED_DIR / f"{ds}.parquet"
        if not pq.exists():
            print(f"[SKIP] {ds} {letter}{mag} — labeled parquet not built yet")
            continue
        ok, errs = validate_one(ds, peak, letter, mag)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {ds} {letter}{mag} peak={peak.isoformat()}")
        for e in errs:
            print(f"    - {e}")
        if ok:
            out = plot_one(ds, peak, letter, mag)
            print(f"    plot: {out}")
        all_ok &= ok

    # detailed distribution for the X9.0 day (Task 3.3)
    class_distribution("20241003")

    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

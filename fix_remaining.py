"""Fix remaining pipeline failures: F10.7, NOAA SRS, and validation plot."""

import os
import sys
import time
import tarfile
import ftplib
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO, BytesIO

import pandas as pd
import numpy as np
import requests

ROOT = Path("data")
START = "2024-02-01"
END = "2026-06-15"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ══════════════════════════════════════════════════════════════════
# FIX 1: F10.7 — Julian Date conversion
# ══════════════════════════════════════════════════════════════════
def fix_f107():
    log("=" * 60)
    log("FIX: F10.7 solar radio flux (Julian Date conversion)")
    log("=" * 60)

    out_dir = ROOT / "indices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "f107_daily.csv"

    try:
        from astropy.time import Time

        url = "https://lasp.colorado.edu/lisird/latis/dap/penticton_radio_flux.csv"
        log("  Downloading from LISIRD...")
        r = requests.get(url, timeout=60)
        r.raise_for_status()

        df_full = pd.read_csv(StringIO(r.text))
        log(f"  Got {len(df_full)} total rows")

        # Convert Julian Date to datetime
        jd_col = df_full.columns[0]  # "time (Julian Date)"
        jd_values = df_full[jd_col].values
        dates = Time(jd_values, format="jd").to_datetime()
        df_full["date"] = dates

        # Filter to date range
        mask = (df_full["date"] >= pd.Timestamp(START)) & (
            df_full["date"] <= pd.Timestamp(END)
        )
        df = df_full[mask][["date", df_full.columns[1], df_full.columns[2]]].copy()
        df.columns = ["date", "observed_flux", "adjusted_flux"]
        df.to_csv(out_file, index=False)
        log(f"  Saved {len(df)} rows to {out_file}")

        # Quick stats
        log(f"  F10.7 range: {df['adjusted_flux'].min():.1f} – {df['adjusted_flux'].max():.1f} SFU")
        return True

    except Exception as e:
        log(f"  F10.7 fix failed: {e}")
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════════════════════════
# FIX 2: NOAA SRS — download from FTP tar.gz archives
# ══════════════════════════════════════════════════════════════════
def fix_srs():
    log("=" * 60)
    log("FIX: NOAA SRS (download tar.gz archives from SWPC FTP)")
    log("=" * 60)

    out_dir = ROOT / "active_regions" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    years = [2024, 2025, 2026]
    total_files = 0

    try:
        ftp = ftplib.FTP("ftp.swpc.noaa.gov", timeout=30)
        ftp.login()
        log("  Connected to ftp.swpc.noaa.gov")

        for year in years:
            archive_name = f"{year}_SRS.tar.gz"
            ftp_path = f"/pub/warehouse/{year}/{archive_name}"

            log(f"  Downloading {archive_name}...")
            buf = BytesIO()
            try:
                ftp.retrbinary(f"RETR {ftp_path}", buf.write)
                buf.seek(0)
                log(f"    Downloaded {len(buf.getvalue()) / 1024:.0f} KB")

                # Extract
                with tarfile.open(fileobj=buf, mode="r:gz") as tf:
                    members = tf.getmembers()
                    extracted = 0
                    for m in members:
                        if m.isfile() and "SRS" in m.name:
                            # Extract just the filename
                            basename = os.path.basename(m.name)
                            out_path = out_dir / basename
                            if not out_path.exists():
                                f_in = tf.extractfile(m)
                                if f_in:
                                    out_path.write_bytes(f_in.read())
                                    extracted += 1
                    total_files += extracted
                    log(f"    Extracted {extracted} new SRS files for {year}")

            except ftplib.error_perm as e:
                if "550" in str(e):
                    log(f"    {archive_name} not found (year may be incomplete)")
                else:
                    log(f"    FTP error: {e}")

        ftp.quit()

    except Exception as e:
        log(f"  FTP connection failed: {e}")
        traceback.print_exc()

    # Count total files
    all_srs = list(out_dir.glob("*.txt"))
    log(f"  Total SRS files: {len(all_srs)}")

    # Filter to date range
    start_dt = datetime.strptime(START, "%Y-%m-%d")
    end_dt = datetime.strptime(END, "%Y-%m-%d")
    in_range = 0
    for f in all_srs:
        try:
            date_str = f.stem.replace("SRS", "")
            dt = datetime.strptime(date_str, "%Y%m%d")
            if start_dt <= dt <= end_dt:
                in_range += 1
        except ValueError:
            pass
    log(f"  Files in date range: {in_range}")
    return len(all_srs) > 0


# ══════════════════════════════════════════════════════════════════
# FIX 3: Validation plot — fix ax.text() duplicate x
# ══════════════════════════════════════════════════════════════════
def fix_validation_plot():
    log("=" * 60)
    log("FIX: Validation plot (GOES XRS 2024-10-03 X9.0 flare)")
    log("=" * 60)

    out_path = ROOT / "validation_oct3_2024.png"
    xrs_dir = ROOT / "goes" / "xrs"

    try:
        import xarray as xr
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        candidates = list(xrs_dir.glob("*d20241003*")) + list(xrs_dir.glob("*20241003*"))
        if not candidates:
            candidates = sorted(xrs_dir.glob("*202410*"))

        if not candidates:
            log("  No GOES XRS file found for 2024-10-03")
            return False

        log(f"  Found {len(candidates)} candidate file(s): {candidates[0].name}")

        ds = xr.open_dataset(candidates[0])
        time_var = None
        for v in ["time", "time_tag"]:
            if v in ds.dims or v in ds.coords:
                time_var = v
                break

        xrsb = ds["xrsb_flux"] if "xrsb_flux" in ds else None
        xrsa = ds["xrsa_flux"] if "xrsa_flux" in ds else None

        fig, ax = plt.subplots(figsize=(12, 5))

        if xrsb is not None:
            ax.plot(ds[time_var], xrsb, "r-", linewidth=0.8, label="GOES 1-8 Å (long)")
        if xrsa is not None:
            ax.plot(ds[time_var], xrsa, "b-", linewidth=0.8, label="GOES 0.5-4 Å (short)")

        ax.set_yscale("log")
        ax.set_ylabel("Flux (W/m²)")
        ax.set_xlabel("UTC")
        ax.set_title("GOES-16 XRS — 2024-10-03 (X9.0 flare ~12:18 UT)")
        ax.legend()

        # Add GOES class reference lines (fixed — no duplicate x param)
        for level, label in [
            (1e-8, "A"),
            (1e-7, "B"),
            (1e-6, "C"),
            (1e-5, "M"),
            (1e-4, "X"),
        ]:
            ax.axhline(y=level, color="gray", linestyle="--", alpha=0.3)
            ax.text(
                0.01, level * 1.2, label,
                fontsize=8, color="gray",
                transform=ax.get_yaxis_transform(),
            )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close()
        ds.close()
        log(f"  Plot saved to {out_path}")
        return True

    except Exception as e:
        log(f"  Validation plot failed: {e}")
        traceback.print_exc()
        return False


# ══════════════════════════════════════════════════════════════════
# Update README
# ══════════════════════════════════════════════════════════════════
def update_readme():
    log("=" * 60)
    log("Regenerating data/README.md")
    log("=" * 60)

    readme = ROOT / "README.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Gather stats
    goes_dir = ROOT / "goes" / "xrs"
    goes_files = list(goes_dir.glob("*.nc"))
    goes_size = sum(f.stat().st_size for f in goes_files)

    swpc_file = ROOT / "goes" / "events" / "flares_swpc.csv"
    hek_file = ROOT / "hek" / "flares_all.csv"
    f107_file = ROOT / "indices" / "f107_daily.csv"
    ssn_file = ROOT / "indices" / "sunspot_daily.csv"
    srs_dir = ROOT / "active_regions" / "raw"
    srs_files = list(srs_dir.glob("*.txt")) if srs_dir.exists() else []

    lines = [
        "# Auxiliary Datasets Inventory",
        "",
        f"Generated: {ts}",
        f"Date range: {START} to {END}",
        "",
        "## Downloaded Datasets",
        "",
        "| # | Dataset | Priority | Status | Size | Files/Rows | Notes |",
        "|---|---------|----------|--------|------|------------|-------|",
    ]

    def fsize(p):
        if p.exists():
            s = p.stat().st_size
            for u in ["B", "KB", "MB"]:
                if s < 1024:
                    return f"{s:.1f} {u}"
                s /= 1024
            return f"{s:.1f} GB"
        return "—"

    # Dataset 1
    lines.append(
        f"| 1 | GOES-16 XRS 1-min flux | CRITICAL | PARTIAL | "
        f"{goes_size/1024/1024:.1f} MB | {len(goes_files)} files | "
        f"Fido returned 431; GOES-16 data may end before 2026-06 |"
    )

    # Dataset 2
    if swpc_file.exists():
        df = pd.read_csv(swpc_file)
        classes = df["goes_class"].dropna().str[0].value_counts().to_dict() if "goes_class" in df.columns else {}
        lines.append(
            f"| 2 | SWPC flare catalog | CRITICAL | OK | {fsize(swpc_file)} | "
            f"{len(df)} rows | Classes: {classes} |"
        )

    # Dataset 3
    if hek_file.exists():
        df = pd.read_csv(hek_file)
        lines.append(
            f"| 3 | Full HEK flare catalog | HIGH | OK | {fsize(hek_file)} | "
            f"{len(df)} rows | All FRM providers |"
        )

    # Dataset 4
    if f107_file.exists() and f107_file.stat().st_size > 200:
        df = pd.read_csv(f107_file)
        flux = df["adjusted_flux"] if "adjusted_flux" in df.columns else df.iloc[:, 1]
        lines.append(
            f"| 4 | F10.7 solar radio flux | HIGH | OK | {fsize(f107_file)} | "
            f"{len(df)} rows | Range: {flux.min():.1f}–{flux.max():.1f} SFU |"
        )
    else:
        lines.append("| 4 | F10.7 solar radio flux | HIGH | FAILED | — | 0 | LISIRD unavailable |")

    # Dataset 5
    if ssn_file.exists():
        df = pd.read_csv(ssn_file)
        lines.append(
            f"| 5 | Intl Sunspot Number | HIGH | OK | {fsize(ssn_file)} | "
            f"{len(df)} rows | SSN range: {df['ssn'].min():.0f}–{df['ssn'].max():.0f} |"
        )

    # Dataset 6
    srs_size = sum(f.stat().st_size for f in srs_files)
    srs_status = "OK" if len(srs_files) >= 600 else ("PARTIAL" if srs_files else "FAILED")
    lines.append(
        f"| 6 | NOAA SRS active regions | MEDIUM | {srs_status} | "
        f"{srs_size/1024/1024:.1f} MB | {len(srs_files)} files | "
        f"From SWPC FTP archive |"
    )

    lines.append("")
    lines.append("## Validation")
    lines.append("")
    val_plot = ROOT / "validation_oct3_2024.png"
    if val_plot.exists():
        lines.append("- `validation_oct3_2024.png` — GOES XRS on 2024-10-03 showing X9.0 flare at ~12:18 UT")
    else:
        lines.append("- Validation plot not generated")

    lines.append("")
    lines.append("## Directory Structure")
    lines.append("```")
    lines.append("data/")
    lines.append("├── goes/xrs/              # GOES-16 XRS 1-min NetCDF files")
    lines.append("├── goes/events/           # flares_swpc.csv")
    lines.append("├── hek/                   # flares_all.csv (full HEK catalog)")
    lines.append("├── indices/               # f107_daily.csv, sunspot_daily.csv")
    lines.append("├── active_regions/raw/    # NOAA SRS daily .txt files")
    lines.append("├── validation_oct3_2024.png")
    lines.append("└── README.md")
    lines.append("```")

    readme.write_text("\n".join(lines), encoding="utf-8")
    log(f"  README updated: {readme}")


if __name__ == "__main__":
    f107_ok = fix_f107()
    srs_ok = fix_srs()
    plot_ok = fix_validation_plot()
    update_readme()

    log("")
    log("=" * 60)
    log("FIX RESULTS")
    log("=" * 60)
    log(f"  F10.7:           {'OK' if f107_ok else 'FAILED'}")
    log(f"  NOAA SRS:        {'OK' if srs_ok else 'FAILED'}")
    log(f"  Validation plot: {'OK' if plot_ok else 'FAILED'}")

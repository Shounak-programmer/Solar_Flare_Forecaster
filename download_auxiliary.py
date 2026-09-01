"""
Auxiliary dataset download pipeline for Aditya-L1 solar flare forecasting.
Fetches GOES XRS, flare catalogs, solar indices, and NOAA SRS data.

Usage:  python download_auxiliary.py
Re-run safe: skips already-downloaded files.
"""

import os
import sys
import time
import json
import traceback
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

import pandas as pd
import numpy as np
import requests
from tqdm import tqdm

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ── Config ──────────────────────────────────────────────────────────
START = "2024-02-01"
END = "2026-06-15"
ROOT = Path("data")
MAX_RETRIES = 3

STATUS = {}  # dataset_name -> {status, size, count, notes}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def retry(fn, retries=MAX_RETRIES, label="operation"):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            wait = 2 ** attempt * 5
            log(f"  {label} attempt {attempt+1}/{retries} failed: {e}")
            if attempt < retries - 1:
                log(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def format_size(nbytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def dir_size(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())


# ════════════════════════════════════════════════════════════════════
# DATASET 1: GOES-16 XRS 1-minute avg flux
# ════════════════════════════════════════════════════════════════════
def download_goes_xrs():
    log("=" * 60)
    log("DATASET 1: GOES-16 XRS 1-minute flux [CRITICAL]")
    log("=" * 60)

    out_dir = ROOT / "goes" / "xrs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Try sunpy Fido first
    success = False
    try:
        log("Trying sunpy Fido search...")
        from sunpy.net import Fido, attrs as a

        def do_search():
            return Fido.search(
                a.Time(START, END),
                a.Instrument("XRS"),
                a.goes.SatelliteNumber(16),
                a.Resolution("avg1m"),
            )

        result = retry(do_search, label="Fido.search")
        total_files = result.file_num
        log(f"  Fido found {total_files} files")

        if total_files > 0:
            log("  Fetching files (this may take a while)...")
            fetched = Fido.fetch(
                result,
                path=str(out_dir) + "/{file}",
                progress=True,
                max_conn=5,
            )
            n_fetched = len(fetched)
            n_errors = len(fetched.errors)
            log(f"  Fetched {n_fetched} files, {n_errors} errors")
            if n_fetched > 100:
                success = True

    except Exception as e:
        log(f"  Fido failed: {e}")

    # Fallback: direct NCEI download
    if not success:
        log("Falling back to direct NCEI download...")
        base_url = "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes16/l2/data/xrsf-l2-avg1m_science/"

        start_dt = datetime.strptime(START, "%Y-%m-%d")
        end_dt = datetime.strptime(END, "%Y-%m-%d")

        current = start_dt.replace(day=1)
        months = []
        while current <= end_dt:
            months.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        failed_months = []
        for month_dt in tqdm(months, desc="GOES XRS months"):
            yyyy = month_dt.strftime("%Y")
            mm = month_dt.strftime("%m")
            month_url = f"{base_url}{yyyy}/{mm}/"

            try:
                resp = requests.get(month_url, timeout=30)
                if resp.status_code != 200:
                    failed_months.append(month_dt.strftime("%Y-%m"))
                    continue

                import re
                nc_files = re.findall(
                    r'href="(sci_xrsf-l2-avg1m_g16_d\d{8}_v\d+-\d+\.nc)"',
                    resp.text,
                )

                for ncf in nc_files:
                    local = out_dir / ncf
                    if local.exists() and local.stat().st_size > 1000:
                        continue
                    file_url = f"{month_url}{ncf}"
                    for attempt in range(MAX_RETRIES):
                        try:
                            r = requests.get(file_url, timeout=60)
                            if r.status_code == 200 and len(r.content) > 1000:
                                local.write_bytes(r.content)
                                break
                        except Exception:
                            time.sleep(2**attempt)

            except Exception as e:
                failed_months.append(month_dt.strftime("%Y-%m"))
                log(f"  Failed month {month_dt.strftime('%Y-%m')}: {e}")

        if failed_months:
            log(f"  Failed months: {failed_months}")

    # Verify
    nc_files = list(out_dir.glob("*.nc"))
    total_size = sum(f.stat().st_size for f in nc_files)
    notes = []

    if len(nc_files) >= 600:
        status = "OK"
    elif len(nc_files) > 0:
        status = "PARTIAL"
        notes.append(f"Expected ~870 files, got {len(nc_files)}")
    else:
        status = "FAILED"
        notes.append("No files downloaded")

    # Sample verification
    if nc_files:
        try:
            import xarray as xr
            sample = xr.open_dataset(nc_files[0])
            vars_found = list(sample.data_vars)
            has_xrsa = "xrsa_flux" in vars_found
            has_xrsb = "xrsb_flux" in vars_found
            sample.close()
            if has_xrsa and has_xrsb:
                notes.append("Verified: xrsa_flux + xrsb_flux present")
            else:
                notes.append(f"WARNING: variables = {vars_found}")
        except Exception as e:
            notes.append(f"Sample verify failed: {e}")

    STATUS["GOES XRS 1-min"] = {
        "status": status,
        "size": format_size(total_size),
        "count": f"{len(nc_files)} files",
        "notes": "; ".join(notes),
        "critical": True,
    }
    log(f"  Result: {status} — {len(nc_files)} files, {format_size(total_size)}")
    return nc_files


# ════════════════════════════════════════════════════════════════════
# DATASET 2: SWPC flare event catalog
# ════════════════════════════════════════════════════════════════════
def download_swpc_flares():
    log("=" * 60)
    log("DATASET 2: SWPC flare event catalog [CRITICAL]")
    log("=" * 60)

    out_dir = ROOT / "goes" / "events"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "flares_swpc.csv"

    if out_file.exists() and out_file.stat().st_size > 1000:
        df = pd.read_csv(out_file)
        log(f"  Already exists with {len(df)} rows, skipping")
        STATUS["SWPC flare catalog"] = {
            "status": "OK" if len(df) >= 1000 else "PARTIAL",
            "size": format_size(out_file.stat().st_size),
            "count": f"{len(df)} rows",
            "notes": "Loaded from cache",
            "critical": True,
        }
        return df

    df = None

    # Try sunpy HEK
    try:
        log("  Querying HEK for SWPC flares...")
        from sunpy.net import Fido, attrs as a

        # Query in yearly chunks to avoid timeouts
        all_tables = []
        chunk_starts = pd.date_range(START, END, freq="6ME").tolist()
        if pd.Timestamp(END) not in chunk_starts:
            chunk_starts.append(pd.Timestamp(END))

        prev = pd.Timestamp(START)
        for cs in chunk_starts:
            if cs <= prev:
                continue
            log(f"    Chunk: {prev.strftime('%Y-%m-%d')} to {cs.strftime('%Y-%m-%d')}")

            def do_query(s=prev, e=cs):
                return Fido.search(
                    a.Time(s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")),
                    a.hek.FL,
                    a.hek.FRM.Name == "SWPC",
                )

            try:
                result = retry(do_query, label="HEK SWPC query")
                if len(result) > 0 and result.file_num > 0:
                    tbl = result["hek"]
                    all_tables.append(tbl)
                    log(f"      Got {len(tbl)} rows")
            except Exception as e:
                log(f"      Chunk failed: {e}")
            prev = cs

        if all_tables:
            all_dfs = [tbl.to_pandas() for tbl in all_tables]
            df_raw = pd.concat(all_dfs, ignore_index=True)

            keep = [
                "event_starttime", "event_peaktime", "event_endtime",
                "fl_goescls", "fl_peakflux", "ar_noaanum", "hgc_x", "hgc_y",
            ]
            available = [c for c in keep if c in df_raw.columns]
            df = df_raw[available].copy()
            renames = {
                "event_starttime": "start",
                "event_peaktime": "peak",
                "event_endtime": "end",
                "fl_goescls": "goes_class",
                "fl_peakflux": "peak_flux",
                "ar_noaanum": "noaa_ar",
                "hgc_x": "lon",
                "hgc_y": "lat",
            }
            df.rename(columns={k: v for k, v in renames.items() if k in df.columns}, inplace=True)
            df.to_csv(out_file, index=False)
            log(f"  Saved {len(df)} rows to {out_file}")

    except Exception as e:
        log(f"  HEK query failed: {e}")
        traceback.print_exc()

    # Verify
    if df is not None and len(df) > 0:
        status = "OK" if len(df) >= 1000 else "PARTIAL"
        notes = []
        if "goes_class" in df.columns:
            classes = df["goes_class"].dropna().str[0].value_counts()
            notes.append(f"Class distribution: {classes.to_dict()}")
    else:
        status = "FAILED"
        df = pd.DataFrame()
        notes = ["No data retrieved from HEK"]

    STATUS["SWPC flare catalog"] = {
        "status": status,
        "size": format_size(out_file.stat().st_size) if out_file.exists() else "0 B",
        "count": f"{len(df)} rows",
        "notes": "; ".join(notes),
        "critical": True,
    }
    log(f"  Result: {status} — {len(df)} rows")
    return df


# ════════════════════════════════════════════════════════════════════
# DATASET 3: Full HEK flare catalog
# ════════════════════════════════════════════════════════════════════
def download_hek_full():
    log("=" * 60)
    log("DATASET 3: Full HEK flare catalog [HIGH]")
    log("=" * 60)

    out_dir = ROOT / "hek"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "flares_all.csv"

    if out_file.exists() and out_file.stat().st_size > 1000:
        df = pd.read_csv(out_file)
        log(f"  Already exists with {len(df)} rows, skipping")
        STATUS["Full HEK catalog"] = {
            "status": "OK",
            "size": format_size(out_file.stat().st_size),
            "count": f"{len(df)} rows",
            "notes": "Loaded from cache",
        }
        return df

    df = None
    try:
        log("  Querying HEK for ALL flares (no FRM filter)...")
        from sunpy.net import Fido, attrs as a

        all_tables = []
        # Use 3-month chunks for the unfiltered query (larger result set)
        chunk_starts = pd.date_range(START, END, freq="3ME").tolist()
        if pd.Timestamp(END) not in chunk_starts:
            chunk_starts.append(pd.Timestamp(END))

        prev = pd.Timestamp(START)
        for cs in chunk_starts:
            if cs <= prev:
                continue
            log(f"    Chunk: {prev.strftime('%Y-%m-%d')} to {cs.strftime('%Y-%m-%d')}")

            def do_query(s=prev, e=cs):
                return Fido.search(
                    a.Time(s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")),
                    a.hek.FL,
                )

            try:
                result = retry(do_query, label="HEK full query")
                if len(result) > 0 and result.file_num > 0:
                    tbl = result["hek"]
                    all_tables.append(tbl)
                    log(f"      Got {len(tbl)} rows")
            except Exception as e:
                log(f"      Chunk failed: {e}")
            prev = cs

        if all_tables:
            all_dfs = [tbl.to_pandas() for tbl in all_tables]
            df_raw = pd.concat(all_dfs, ignore_index=True)

            keep = [
                "event_starttime", "event_peaktime", "event_endtime",
                "fl_goescls", "fl_peakflux", "ar_noaanum",
                "hgc_x", "hgc_y", "frm_name", "frm_institute",
            ]
            available = [c for c in keep if c in df_raw.columns]
            df = df_raw[available].copy()
            df.to_csv(out_file, index=False)
            log(f"  Saved {len(df)} rows to {out_file}")

    except Exception as e:
        log(f"  HEK query failed: {e}")
        traceback.print_exc()

    if df is not None and len(df) > 0:
        status = "OK"
    else:
        status = "FAILED"
        df = pd.DataFrame()

    STATUS["Full HEK catalog"] = {
        "status": status,
        "size": format_size(out_file.stat().st_size) if out_file.exists() else "0 B",
        "count": f"{len(df)} rows",
        "notes": "",
    }
    log(f"  Result: {status} — {len(df)} rows")
    return df


# ════════════════════════════════════════════════════════════════════
# DATASET 4: F10.7 solar radio flux
# ════════════════════════════════════════════════════════════════════
def download_f107():
    log("=" * 60)
    log("DATASET 4: F10.7 solar radio flux [HIGH]")
    log("=" * 60)

    out_dir = ROOT / "indices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "f107_daily.csv"

    if out_file.exists() and out_file.stat().st_size > 1000:
        df = pd.read_csv(out_file)
        log(f"  Already exists with {len(df)} rows, skipping")
        STATUS["F10.7 daily"] = {
            "status": "OK" if len(df) >= 800 else "PARTIAL",
            "size": format_size(out_file.stat().st_size),
            "count": f"{len(df)} rows",
            "notes": "Loaded from cache",
        }
        return df

    df = None

    # Primary: LASP LISIRD
    try:
        log("  Trying LASP LISIRD...")
        url = "https://lasp.colorado.edu/lisird/latis/dap/penticton_radio_flux.csv"

        def fetch_lisird():
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r.text

        text = retry(fetch_lisird, label="LISIRD F10.7")
        df_full = pd.read_csv(StringIO(text))
        log(f"  Got {len(df_full)} total rows from LISIRD")

        # Filter to our date range
        time_col = df_full.columns[0]
        if "time" in time_col.lower():
            df_full["date"] = pd.to_datetime(df_full[time_col])
        else:
            df_full["date"] = pd.to_datetime(df_full.iloc[:, 0])

        mask = (df_full["date"] >= START) & (df_full["date"] <= END)
        df = df_full[mask].copy()
        df.to_csv(out_file, index=False)
        log(f"  Saved {len(df)} rows to {out_file}")

    except Exception as e:
        log(f"  LISIRD failed: {e}")

    # Fallback: NRCan
    if df is None or len(df) < 100:
        try:
            log("  Trying NRCan fallback...")
            url = "https://www.spaceweather.gc.ca/forecast-prevision/solar-solaire/solarflux/sx-5-en.php"
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                # Try to parse the text table
                lines = r.text.split("\n")
                records = []
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5 and parts[0].isdigit():
                        try:
                            date = pd.Timestamp(
                                year=int(parts[0]),
                                month=int(parts[1]),
                                day=int(parts[2]),
                            )
                            flux = float(parts[3])
                            records.append({"date": date, "f107": flux})
                        except (ValueError, IndexError):
                            continue
                if records:
                    df = pd.DataFrame(records)
                    mask = (df["date"] >= START) & (df["date"] <= END)
                    df = df[mask]
                    df.to_csv(out_file, index=False)
                    log(f"  NRCan fallback: saved {len(df)} rows")
        except Exception as e:
            log(f"  NRCan fallback also failed: {e}")

    if df is not None and len(df) > 0:
        status = "OK" if len(df) >= 800 else "PARTIAL"
        notes = f"Rows in window: {len(df)}"
    else:
        status = "FAILED"
        df = pd.DataFrame()
        notes = "No data retrieved"

    STATUS["F10.7 daily"] = {
        "status": status,
        "size": format_size(out_file.stat().st_size) if out_file.exists() else "0 B",
        "count": f"{len(df)} rows",
        "notes": notes,
    }
    log(f"  Result: {status} — {len(df)} rows")
    return df


# ════════════════════════════════════════════════════════════════════
# DATASET 5: International Sunspot Number
# ════════════════════════════════════════════════════════════════════
def download_sunspot():
    log("=" * 60)
    log("DATASET 5: International Sunspot Number [HIGH]")
    log("=" * 60)

    out_dir = ROOT / "indices"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "sunspot_daily.csv"

    if out_file.exists() and out_file.stat().st_size > 1000:
        df = pd.read_csv(out_file)
        log(f"  Already exists with {len(df)} rows, skipping")
        STATUS["Sunspot daily"] = {
            "status": "OK" if len(df) >= 800 else "PARTIAL",
            "size": format_size(out_file.stat().st_size),
            "count": f"{len(df)} rows",
            "notes": "Loaded from cache",
        }
        return df

    df = None
    try:
        log("  Downloading from SILSO...")
        url = "https://www.sidc.be/SILSO/INFO/sndtotcsv.php"

        def fetch_silso():
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r.text

        text = retry(fetch_silso, label="SILSO sunspot")
        ssn = pd.read_csv(
            StringIO(text),
            sep=";",
            header=None,
            names=["year", "month", "day", "dec_year", "ssn", "std", "obs", "definitive"],
        )
        ssn["date"] = pd.to_datetime(
            ssn[["year", "month", "day"]].astype(int), errors="coerce"
        )
        ssn = ssn.dropna(subset=["date"])

        mask = (ssn["date"] >= START) & (ssn["date"] <= END)
        df = ssn.loc[mask, ["date", "ssn", "std"]].copy()
        df.to_csv(out_file, index=False)
        log(f"  Saved {len(df)} rows to {out_file}")

    except Exception as e:
        log(f"  SILSO download failed: {e}")
        traceback.print_exc()

    if df is not None and len(df) > 0:
        status = "OK" if len(df) >= 800 else "PARTIAL"
        notes = f"SSN range: {df['ssn'].min():.0f} - {df['ssn'].max():.0f}"
    else:
        status = "FAILED"
        df = pd.DataFrame()
        notes = "No data retrieved"

    STATUS["Sunspot daily"] = {
        "status": status,
        "size": format_size(out_file.stat().st_size) if out_file.exists() else "0 B",
        "count": f"{len(df)} rows",
        "notes": notes,
    }
    log(f"  Result: {status}")
    return df


# ════════════════════════════════════════════════════════════════════
# DATASET 6: NOAA SRS active regions
# ════════════════════════════════════════════════════════════════════
def download_srs():
    log("=" * 60)
    log("DATASET 6: NOAA SRS active regions [MEDIUM]")
    log("=" * 60)

    out_dir = ROOT / "active_regions" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    start_dt = datetime.strptime(START, "%Y-%m-%d")
    end_dt = datetime.strptime(END, "%Y-%m-%d")
    days = [start_dt + timedelta(days=i) for i in range((end_dt - start_dt).days + 1)]

    # Count already downloaded
    existing = set(f.stem for f in out_dir.glob("*.txt") if f.stat().st_size > 0)
    log(f"  Already have {len(existing)} SRS files")

    failed = []
    skipped_404 = 0

    to_download = []
    for d in days:
        yyyymmdd = d.strftime("%Y%m%d")
        if f"{yyyymmdd}SRS" in existing:
            continue
        to_download.append(d)

    if not to_download:
        log("  All SRS files already downloaded")
    else:
        log(f"  Need to download {len(to_download)} SRS files")
        for d in tqdm(to_download, desc="NOAA SRS"):
            yyyymmdd = d.strftime("%Y%m%d")
            out_path = out_dir / f"{yyyymmdd}SRS.txt"
            url = f"https://services.swpc.noaa.gov/text/srs/{yyyymmdd}SRS.txt"

            ok = False
            for attempt in range(MAX_RETRIES):
                try:
                    r = requests.get(url, timeout=15)
                    if r.status_code == 200 and len(r.text) > 100:
                        out_path.write_text(r.text)
                        ok = True
                        break
                    elif r.status_code == 404:
                        skipped_404 += 1
                        ok = True  # not an error, just no data
                        break
                    else:
                        time.sleep(2**attempt)
                except requests.exceptions.RequestException:
                    time.sleep(2**attempt)

            if not ok:
                failed.append(yyyymmdd)

    # Verify
    all_srs = list(out_dir.glob("*.txt"))
    total_size = sum(f.stat().st_size for f in all_srs)

    notes = []
    if failed:
        notes.append(f"{len(failed)} days failed")
    if skipped_404:
        notes.append(f"{skipped_404} days returned 404 (no SRS)")

    if len(all_srs) >= 600:
        status = "OK"
    elif len(all_srs) > 0:
        status = "PARTIAL"
    else:
        status = "FAILED"

    STATUS["NOAA SRS"] = {
        "status": status,
        "size": format_size(total_size),
        "count": f"{len(all_srs)} files",
        "notes": "; ".join(notes),
    }
    log(f"  Result: {status} — {len(all_srs)} files")
    return failed


# ════════════════════════════════════════════════════════════════════
# VALIDATION PLOT: GOES XRS on 2024-10-03 (X9.0 flare)
# ════════════════════════════════════════════════════════════════════
def make_validation_plot():
    log("=" * 60)
    log("VALIDATION: GOES XRS on 2024-10-03 (X9.0 flare)")
    log("=" * 60)

    out_path = ROOT / "validation_oct3_2024.png"
    xrs_dir = ROOT / "goes" / "xrs"

    try:
        import xarray as xr
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        # Find the file for 2024-10-03
        candidates = list(xrs_dir.glob("*d20241003*")) + list(xrs_dir.glob("*20241003*"))
        if not candidates:
            # Try all October 2024 files and filter by date
            candidates = sorted(xrs_dir.glob("*202410*"))

        if not candidates:
            log("  No GOES XRS file found for 2024-10-03")
            return

        log(f"  Found {len(candidates)} candidate file(s)")

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

        # Add GOES class reference lines
        for level, label in [
            (1e-8, "A"),
            (1e-7, "B"),
            (1e-6, "C"),
            (1e-5, "M"),
            (1e-4, "X"),
        ]:
            ax.axhline(y=level, color="gray", linestyle="--", alpha=0.3)
            ax.text(
                ax.get_xlim()[0] if ax.get_xlim()[0] != 0 else 0.01,
                level * 1.2,
                label,
                fontsize=8,
                color="gray",
                transform=ax.get_yaxis_transform(),
                x=0.01,
            )

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.tight_layout()
        fig.savefig(out_path, dpi=150)
        plt.close()
        ds.close()
        log(f"  Plot saved to {out_path}")

    except Exception as e:
        log(f"  Validation plot failed: {e}")
        traceback.print_exc()


# ════════════════════════════════════════════════════════════════════
# README generation
# ════════════════════════════════════════════════════════════════════
def generate_readme():
    log("=" * 60)
    log("Generating data/README.md")
    log("=" * 60)

    readme = ROOT / "README.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Auxiliary Datasets Inventory",
        "",
        f"Generated: {ts}",
        "",
        "## Coverage",
        f"Date range: {START} to {END}",
        "",
        "## Downloaded",
        "",
        "| Dataset | Status | Size | Files / Rows | Notes |",
        "|---------|--------|------|-------------|-------|",
    ]

    for name, info in STATUS.items():
        critical = " **[CRITICAL]**" if info.get("critical") else ""
        lines.append(
            f"| {name}{critical} | {info['status']} | {info['size']} "
            f"| {info['count']} | {info.get('notes', '')} |"
        )

    lines.append("")
    lines.append("## Quick sanity checks")
    lines.append("")

    # Flare class distribution
    swpc_file = ROOT / "goes" / "events" / "flares_swpc.csv"
    if swpc_file.exists():
        df = pd.read_csv(swpc_file)
        if "goes_class" in df.columns:
            classes = df["goes_class"].dropna().str[0].value_counts().sort_index()
            lines.append(f"- **Flare class distribution (SWPC):** {classes.to_dict()}")

    # F10.7 range
    f107_file = ROOT / "indices" / "f107_daily.csv"
    if f107_file.exists():
        df = pd.read_csv(f107_file)
        flux_cols = [c for c in df.columns if "flux" in c.lower() or "f107" in c.lower() or "adjusted" in c.lower()]
        if flux_cols:
            col = flux_cols[0]
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(vals) > 0:
                lines.append(f"- **F10.7 range:** {vals.min():.1f} – {vals.max():.1f} SFU")

    # Sunspot range
    ssn_file = ROOT / "indices" / "sunspot_daily.csv"
    if ssn_file.exists():
        df = pd.read_csv(ssn_file)
        if "ssn" in df.columns:
            lines.append(f"- **Sunspot number range:** {df['ssn'].min():.0f} – {df['ssn'].max():.0f}")

    # GOES XRS sample
    xrs_dir = ROOT / "goes" / "xrs"
    nc_files = list(xrs_dir.glob("*.nc"))
    if nc_files:
        try:
            import xarray as xr
            ds = xr.open_dataset(nc_files[0])
            lines.append(f"- **GOES XRS sample variables:** {list(ds.data_vars)}")
            ds.close()
        except Exception:
            pass

    lines.append("")
    lines.append("## Known issues")
    lines.append("")
    issues_found = False
    for name, info in STATUS.items():
        if info["status"] in ("FAILED", "PARTIAL"):
            lines.append(f"- **{name}:** {info['status']} — {info.get('notes', 'unknown')}")
            issues_found = True
    if not issues_found:
        lines.append("- None")

    lines.append("")
    lines.append("## Validation")
    lines.append("")
    val_plot = ROOT / "validation_oct3_2024.png"
    if val_plot.exists():
        lines.append(
            "- `validation_oct3_2024.png` — GOES XRS on 2024-10-03 showing X9.0 flare at ~12:18 UT"
        )
    else:
        lines.append("- Validation plot not generated (GOES XRS data may be missing for that date)")

    readme.write_text("\n".join(lines), encoding="utf-8")
    log(f"  README written to {readme}")


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════
def main():
    log("=" * 60)
    log("Aditya-L1 Auxiliary Data Download Pipeline")
    log(f"Date range: {START} to {END}")
    log("=" * 60)

    download_goes_xrs()
    download_swpc_flares()
    download_hek_full()
    download_f107()
    download_sunspot()
    download_srs()
    make_validation_plot()
    generate_readme()

    # Final summary
    log("")
    log("=" * 60)
    log("FINAL SUMMARY")
    log("=" * 60)
    print()
    print(f"{'Dataset':<25} {'Status':<10} {'Size':<12} {'Count':<15} Notes")
    print("-" * 100)
    for name, info in STATUS.items():
        crit = " *" if info.get("critical") else ""
        print(
            f"{name + crit:<25} {info['status']:<10} {info['size']:<12} "
            f"{info['count']:<15} {info.get('notes', '')}"
        )
    print()

    # Check critical datasets
    critical_failures = [
        name for name, info in STATUS.items()
        if info.get("critical") and info["status"] == "FAILED"
    ]
    if critical_failures:
        log(f"CRITICAL FAILURES: {critical_failures}")
        log("Next action: check network connectivity and retry, or download manually.")
        return 1
    else:
        log("All critical datasets OK. Pipeline complete.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

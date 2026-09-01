"""Standardize all auxiliary datasets into ML-ready Parquets.

Outputs written to data/processed/:
  goes_xrs_combined.parquet      (Task 3a)
  flares_swpc.parquet            (Task 3b)
  flares_hek.parquet             (Task 3c)
  solar_indices_daily.parquet    (Task 3d)
  active_regions_daily.parquet   (Task 3e)
"""
from __future__ import annotations

import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUT_DIR = DATA_DIR / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GOES_CLASS_RE = re.compile(r"^([BCMX])([\d.]+)$", re.IGNORECASE)


def parse_goes_class(s: str | float) -> tuple[str | None, float | None]:
    """Return (letter, magnitude) for a GOES class string like "M3.2".
    Returns (None, None) for missing/malformed values."""
    if not isinstance(s, str) or not s:
        return None, None
    m = GOES_CLASS_RE.match(s.strip())
    if not m:
        return None, None
    return m.group(1).upper(), float(m.group(2))


# ─────────────────────────────────────────────────────────────────────────────
# Task 3a — GOES XRS combine
# ─────────────────────────────────────────────────────────────────────────────
def build_goes_xrs() -> Path:
    import netCDF4

    nc_files = sorted((DATA_DIR / "goes" / "xrs").glob("sci_xrsf-l2-avg1m_*.nc"))
    print(f"[3a] GOES XRS: {len(nc_files)} NetCDF files")
    frames = []
    sat_re = re.compile(r"_g(\d+)_", re.IGNORECASE)
    for f in nc_files:
        try:
            with netCDF4.Dataset(f) as nc:
                t = nc.variables["time"][:]  # masked array of float seconds since 2000-01-01 12:00:00 UTC
                xrsa = nc.variables["xrsa_flux"][:]
                xrsb = nc.variables["xrsb_flux"][:]
                # Convert masked → NaN
                xrsa = np.ma.filled(xrsa, np.nan).astype(np.float64)
                xrsb = np.ma.filled(xrsb, np.nan).astype(np.float64)
                t_arr = np.ma.filled(t, np.nan).astype(np.float64)
                # Epoch: 2000-01-01 12:00:00 UTC
                epoch = pd.Timestamp("2000-01-01 12:00:00", tz="UTC")
                utc = epoch + pd.to_timedelta(t_arr, unit="s")
                m = sat_re.search(f.name)
                sat = f"GOES-{int(m.group(1))}" if m else "GOES-?"
                frames.append(pd.DataFrame({
                    "utc": utc,
                    "xrsa_flux": xrsa,
                    "xrsb_flux": xrsb,
                    "satellite": sat,
                }))
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] {f.name}: {exc}", file=sys.stderr)

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("utc").drop_duplicates(subset="utc", keep="first")

    # Resample to uniform 1-min grid covering the full span. Gaps stay NaN.
    full_idx = pd.date_range(df["utc"].min().floor("min"),
                             df["utc"].max().ceil("min"),
                             freq="1min", tz="UTC")
    df = df.set_index("utc").reindex(full_idx)
    df.index.name = "utc"
    df["satellite"] = df["satellite"].ffill().bfill()
    df = df.reset_index()

    df["satellite"] = df["satellite"].astype("category")
    out = OUT_DIR / "goes_xrs_combined.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    print(f"  wrote {out}  rows={len(df)}  span={df['utc'].min()} .. {df['utc'].max()}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 3b — SWPC flares
# ─────────────────────────────────────────────────────────────────────────────
def build_swpc_flares() -> Path:
    src = DATA_DIR / "goes" / "events" / "flares_swpc.csv"
    df = pd.read_csv(src)
    df = df.rename(columns={
        "start": "start_utc", "peak": "peak_utc", "end": "end_utc",
    })
    for c in ("start_utc", "peak_utc", "end_utc"):
        df[c] = pd.to_datetime(df[c], utc=True)
    letters, mags = zip(*df["goes_class"].apply(parse_goes_class))
    df["goes_class_letter"] = letters
    df["goes_class_magnitude"] = mags
    df["duration_seconds"] = (df["end_utc"] - df["start_utc"]).dt.total_seconds().astype("Int64")
    df["noaa_ar"] = pd.to_numeric(df["noaa_ar"], errors="coerce").astype("Int64")
    df = df[[
        "start_utc", "peak_utc", "end_utc", "goes_class",
        "goes_class_letter", "goes_class_magnitude", "peak_flux",
        "noaa_ar", "lon", "lat", "duration_seconds",
    ]]
    df = df.sort_values("peak_utc").reset_index(drop=True)
    out = OUT_DIR / "flares_swpc.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    print(f"[3b] SWPC flares: wrote {out}  rows={len(df)}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 3c — HEK flares
# ─────────────────────────────────────────────────────────────────────────────
def build_hek_flares() -> Path:
    src = DATA_DIR / "hek" / "flares_all.csv"
    df = pd.read_csv(src)
    df = df.rename(columns={
        "event_starttime": "start_utc",
        "event_peaktime":  "peak_utc",
        "event_endtime":   "end_utc",
        "fl_goescls":      "goes_class",
        "fl_peakflux":     "peak_flux",
        "ar_noaanum":      "noaa_ar",
        "hgc_x":           "lon",
        "hgc_y":           "lat",
    })
    for c in ("start_utc", "peak_utc", "end_utc"):
        df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    letters, mags = zip(*df["goes_class"].apply(parse_goes_class))
    df["goes_class_letter"] = letters
    df["goes_class_magnitude"] = mags
    df["duration_seconds"] = (df["end_utc"] - df["start_utc"]).dt.total_seconds().astype("Int64")
    df["noaa_ar"] = pd.to_numeric(df["noaa_ar"], errors="coerce").astype("Int64")
    df = df[[
        "start_utc", "peak_utc", "end_utc", "goes_class",
        "goes_class_letter", "goes_class_magnitude", "peak_flux",
        "noaa_ar", "lon", "lat", "duration_seconds",
    ]]
    df = df.dropna(subset=["peak_utc"]).sort_values("peak_utc").reset_index(drop=True)
    out = OUT_DIR / "flares_hek.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    print(f"[3c] HEK flares: wrote {out}  rows={len(df)}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 3d — Solar indices merge
# ─────────────────────────────────────────────────────────────────────────────
def build_solar_indices() -> Path:
    f107 = pd.read_csv(DATA_DIR / "indices" / "f107_daily.csv")
    f107["date"] = pd.to_datetime(f107["date"], utc=False, errors="coerce").dt.date
    f107 = (
        f107.dropna(subset=["date"])
        .groupby("date", as_index=False)
        .agg(f107_observed=("observed_flux", "mean"),
             f107_adjusted=("adjusted_flux", "mean"))
    )

    ssn = pd.read_csv(DATA_DIR / "indices" / "sunspot_daily.csv")
    ssn["date"] = pd.to_datetime(ssn["date"], errors="coerce").dt.date
    ssn = ssn.dropna(subset=["date"]).rename(
        columns={"ssn": "sunspot_number", "std": "sunspot_std"}
    )

    df = pd.merge(f107, ssn, on="date", how="outer").sort_values("date")
    df["sunspot_number"] = df["sunspot_number"].astype("Int64")
    out = OUT_DIR / "solar_indices_daily.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    print(f"[3d] Solar indices: wrote {out}  rows={len(df)}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 3e — NOAA SRS active regions
# ─────────────────────────────────────────────────────────────────────────────
SRS_LOC_RE = re.compile(r"^([NS])(\d{2})([EW])(\d{2})$")


def _parse_location(loc: str) -> tuple[float | None, float | None]:
    """Heliographic 'N15W23' → (lat=+15, lon=+23). 'S' negative lat, 'E' negative lon."""
    m = SRS_LOC_RE.match(loc.strip())
    if not m:
        return None, None
    ns, lat, ew, lon = m.groups()
    lat_v = int(lat) * (1 if ns.upper() == "N" else -1)
    lon_v = int(lon) * (1 if ew.upper() == "W" else -1)
    return float(lat_v), float(lon_v)


def _parse_srs_file(path: Path) -> tuple[pd.DataFrame | None, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # Date from filename prefix: YYYYMMDD
    name = path.name
    m = re.match(r"^(\d{8})SRS\.txt$", name, re.IGNORECASE)
    if not m:
        return None, "filename_not_dated"
    date = datetime.strptime(m.group(1), "%Y%m%d").date()

    lines = text.splitlines()
    # Find Section I and the next section (IA, II, etc.)
    in_section = False
    rows: list[dict] = []
    header_seen = False
    for ln in lines:
        s = ln.strip()
        if s.lower().startswith("i.") and "regions with sunspots" in s.lower():
            in_section = True
            header_seen = False
            continue
        if in_section:
            # Stop at next section header
            if re.match(r"^I[AB]?\.", s) or re.match(r"^II\.", s):
                break
            if not s:
                continue
            if not header_seen and s.lower().startswith("nmbr"):
                header_seen = True
                continue
            if not header_seen:
                continue
            # Parse a data row. Columns:
            # Nmbr  Location  Lo  Area  Z  LL  NN  Mag Type...(rest)
            parts = s.split(None, 7)
            if len(parts) < 8:
                # Allow rows where Mag Type is single word (alpha)
                parts = s.split(None, 7)
                if len(parts) < 7:
                    continue
                parts.append("")
            try:
                nmbr = int(parts[0])
                location = parts[1]
                lo = int(parts[2])
                area = int(parts[3])
                z = parts[4]
                ll = int(parts[5])
                nn = int(parts[6])
                mag_type = parts[7].strip() if len(parts) > 7 else ""
            except (ValueError, IndexError):
                continue
            lat_v, lon_v = _parse_location(location)
            rows.append({
                "date": date,
                "noaa_ar": nmbr,
                "location_str": location,
                "lat_hg": lat_v,
                "lon_hg": lon_v,
                "area_millionths": area,
                "z_class": z,
                "num_spots": nn,
                "mag_class": mag_type,
            })
    if not rows:
        # Empty Section I is legal (no spotted regions). Still a successful parse.
        return pd.DataFrame(columns=[
            "date", "noaa_ar", "location_str", "lat_hg", "lon_hg",
            "area_millionths", "z_class", "num_spots", "mag_class",
        ]).astype({"date": "object"}), "empty_section"
    return pd.DataFrame(rows), "ok"


def build_active_regions() -> Path:
    srs_dir = DATA_DIR / "active_regions" / "raw"
    files = sorted(srs_dir.glob("*SRS.txt"))
    print(f"[3e] SRS active regions: {len(files)} files")
    frames: list[pd.DataFrame] = []
    failures: list[tuple[str, str]] = []
    empty_ok = 0
    for f in files:
        try:
            df_one, status = _parse_srs_file(f)
            if df_one is None:
                failures.append((f.name, status))
                continue
            if status == "empty_section":
                empty_ok += 1
            if not df_one.empty:
                frames.append(df_one)
        except Exception as exc:  # noqa: BLE001
            failures.append((f.name, f"{type(exc).__name__}: {exc}"))

    if failures:
        rep = OUT_DIR / "srs_parse_failures.txt"
        with open(rep, "w", encoding="utf-8") as fh:
            for name, reason in failures:
                fh.write(f"{name}\t{reason}\n")
        print(f"  {len(failures)} failed (logged to {rep.name})")
    success_rate = 1.0 - len(failures) / len(files)
    print(f"  parse success rate: {success_rate * 100:.1f}%  "
          f"(empty-section-but-ok: {empty_ok})")

    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame(columns=[
            "date", "noaa_ar", "location_str", "lat_hg", "lon_hg",
            "area_millionths", "z_class", "num_spots", "mag_class",
        ])
    df = df.sort_values(["date", "noaa_ar"]).reset_index(drop=True)
    df["noaa_ar"] = df["noaa_ar"].astype("Int64")
    df["num_spots"] = df["num_spots"].astype("Int64")
    df["area_millionths"] = df["area_millionths"].astype("Int64")
    out = OUT_DIR / "active_regions_daily.parquet"
    df.to_parquet(out, index=False, compression="zstd")
    print(f"  wrote {out}  rows={len(df)}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — validation summaries
# ─────────────────────────────────────────────────────────────────────────────
def _summarize(path: Path, time_cols: list[str], critical_cols: list[str]) -> None:
    print(f"\n--- {path.name} ---")
    df = pd.read_parquet(path)
    print(f"  rows: {len(df):,}")
    for c in time_cols:
        if c in df.columns:
            s = df[c].dropna()
            if len(s):
                print(f"  {c} range: {s.min()} .. {s.max()}  unique={s.nunique():,}")
    for c in critical_cols:
        if c in df.columns:
            n_null = int(df[c].isna().sum())
            print(f"  nulls in {c}: {n_null}")
    print("  sample (5 rows):")
    print(df.head(5).to_string(max_colwidth=40))


def validate_goes_oct3(goes_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    df = pd.read_parquet(goes_path)
    df = df[(df["utc"] >= "2024-10-03") & (df["utc"] < "2024-10-04")].copy()
    if df.empty:
        raise RuntimeError("GOES validation: no rows for 2024-10-03")
    peak_val = float(df["xrsb_flux"].max())
    peak_t = df.loc[df["xrsb_flux"].idxmax(), "utc"]
    print(f"\n[GOES validation Oct 3 2024]  xrsb peak = {peak_val:.3e} W/m^2  "
          f"at {peak_t}")
    if not (5e-4 <= peak_val <= 5e-3):
        raise RuntimeError(
            f"GOES Oct 3 peak {peak_val:.3e} W/m^2 outside expected X-class range "
            f"(~9e-4). Processing likely wrong; STOP."
        )

    out = DATA_DIR / "validation" / "goes_xrs_oct3_2024.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    ax.plot(df["utc"], df["xrsb_flux"], color="tab:red", lw=0.9, label="XRS-B 1-8 A")
    ax.plot(df["utc"], df["xrsa_flux"], color="tab:blue", lw=0.6, label="XRS-A 0.5-4 A")
    ax.axvline(pd.Timestamp("2024-10-03 12:18", tz="UTC"), color="black", ls="--",
               lw=1.2, label="GOES X9.0 peak 12:18 UT")
    ax.set_yscale("log")
    ax.set_ylabel("Flux (W/m^2)")
    ax.set_xlabel("UT on 2024-10-03")
    ax.set_title(f"GOES-16 XRS validation: X9.0 peak = {peak_val:.2e} W/m^2 at {peak_t:%H:%M}")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"  wrote {out}")


def main() -> int:
    print("=" * 70)
    print("STANDARDIZING AUXILIARY DATASETS")
    print("=" * 70)
    goes_p = build_goes_xrs()
    swpc_p = build_swpc_flares()
    hek_p  = build_hek_flares()
    idx_p  = build_solar_indices()
    ar_p   = build_active_regions()

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARIES")
    print("=" * 70)
    _summarize(goes_p, ["utc"], ["xrsa_flux", "xrsb_flux"])
    _summarize(swpc_p, ["start_utc", "peak_utc", "end_utc"],
               ["peak_utc", "goes_class", "goes_class_letter"])
    _summarize(hek_p,  ["start_utc", "peak_utc", "end_utc"],
               ["peak_utc"])
    _summarize(idx_p,  ["date"], ["f107_observed", "sunspot_number"])
    _summarize(ar_p,   ["date"], ["noaa_ar", "area_millionths"])

    validate_goes_oct3(goes_p)
    print("\nAll outputs in", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

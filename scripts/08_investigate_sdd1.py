"""SDD1 exhaustive investigation — Tasks 1-3 of the SDD1 verdict workflow.

Walks every SoLEXS observation directory (or zip), inventories SDD1 vs SDD2
file presence + size, deep-inspects any SDD1 .lc.gz / .pi.gz that exist, and
produces a verdict-ready report.

Outputs:
  data/processed/sdd1_file_inventory.csv
  data/processed/sdd1_deep_inspection.md
  data/validation/sdd1_vs_sdd2_oct3_2024.png   (only if SDD1 LC for that day)
"""
from __future__ import annotations

import gzip
import io
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOLEXS_ROOT = PROJECT_ROOT / "data" / "SoLEXUS"
OUT_CSV = PROJECT_ROOT / "data" / "processed" / "sdd1_file_inventory.csv"
OUT_MD = PROJECT_ROOT / "data" / "processed" / "sdd1_deep_inspection.md"
PLOT_PATH = PROJECT_ROOT / "data" / "validation" / "sdd1_vs_sdd2_oct3_2024.png"

DIR_RE = re.compile(r"^AL1_SLX_L1_(\d{8})_v[\d.]+$", re.IGNORECASE)
ZIP_RE = re.compile(r"^AL1_SLX_L1_(\d{8})_v[\d.]+\.zip$", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# File listing abstraction — handles directory OR zip
# ─────────────────────────────────────────────────────────────────────────────
def list_obs_files(obs_path: Path) -> dict[str, list[tuple[str, int]]]:
    """Return {"SDD1": [(member_name, size), ...], "SDD2": [...]} for one
    observation. ``member_name`` is the basename only; ``size`` is the
    *uncompressed* size if the file is a .gz, else the on-disk size."""
    out = {"SDD1": [], "SDD2": []}

    def _record(sd: str, name: str, raw_size: int, is_gz: bool, get_bytes):
        if is_gz:
            try:
                # cheap uncompressed-size by reading the gzip trailer
                raw = get_bytes()
                size = len(gzip.decompress(raw))
            except Exception:
                size = raw_size
        else:
            size = raw_size
        out[sd].append((name, size))

    if obs_path.is_dir():
        for sd in ("SDD1", "SDD2"):
            sd_path = obs_path / sd
            if not sd_path.is_dir():
                continue
            for f in sd_path.iterdir():
                if f.is_file():
                    _record(sd, f.name, f.stat().st_size,
                            f.name.lower().endswith(".gz"),
                            lambda f=f: f.read_bytes())
    elif obs_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(obs_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                parts = info.filename.replace("\\", "/").split("/")
                if len(parts) < 2:
                    continue
                sd = next((p for p in parts if p.upper() in ("SDD1", "SDD2")), None)
                if sd is None:
                    continue
                _record(sd.upper(), parts[-1], info.file_size,
                        info.filename.lower().endswith(".gz"),
                        lambda zf=zf, n=info.filename: zf.read(n))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — inventory
# ─────────────────────────────────────────────────────────────────────────────
def discover_observations() -> list[tuple[str, Path]]:
    """Return sorted [(YYYYMMDD, path), ...]."""
    obs: list[tuple[str, Path]] = []
    for p in SOLEXS_ROOT.iterdir():
        if p.is_dir():
            m = DIR_RE.match(p.name)
            if m:
                obs.append((m.group(1), p))
        elif p.is_file():
            m = ZIP_RE.match(p.name)
            if m:
                obs.append((m.group(1), p))
    obs.sort()
    return obs


def build_inventory(observations: list[tuple[str, Path]]) -> pd.DataFrame:
    rows = []
    for i, (date_s, obs_path) in enumerate(observations, 1):
        if i % 100 == 0:
            print(f"  scanning {i}/{len(observations)}...")
        files = list_obs_files(obs_path)
        sdd1_names = [n for n, _ in files["SDD1"]]
        sdd2_names = [n for n, _ in files["SDD2"]]
        size_map = {n: s for n, s in files["SDD1"]}

        def has(ext: str) -> bool:
            return any(n.lower().endswith(ext) for n in sdd1_names)

        def find_size(ext: str) -> int:
            return max((s for n, s in files["SDD1"]
                        if n.lower().endswith(ext)), default=0)

        sdd2_has_lc = any(n.lower().endswith(".lc.gz") for n in sdd2_names)
        sdd2_has_pi = any(n.lower().endswith(".pi.gz") for n in sdd2_names)

        # File types as ordered, comma-separated suffix list
        types = sorted({n.split(".", 1)[-1] for n in sdd1_names})

        rows.append({
            "date": f"{date_s[:4]}-{date_s[4:6]}-{date_s[6:]}",
            "sdd1_exists": bool(sdd1_names) or (obs_path / "SDD1").exists() if obs_path.is_dir() else bool(sdd1_names),
            "n_files": len(sdd1_names),
            "file_types": ",".join(types),
            "has_gti": has(".gti.gz"),
            "has_lc": has(".lc.gz"),
            "has_pi": has(".pi.gz"),
            "has_hk": has(".hk.gz"),
            "gti_size_bytes": find_size(".gti.gz"),
            "lc_size_bytes": find_size(".lc.gz"),
            "pi_size_bytes": find_size(".pi.gz"),
            "sdd2_has_lc": sdd2_has_lc,
            "sdd2_has_pi": sdd2_has_pi,
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Task 2 — deep inspection
# ─────────────────────────────────────────────────────────────────────────────
def _read_member(obs_path: Path, sd: str, suffix: str) -> bytes | None:
    """Return raw (already gunzipped) bytes for one SDD member."""
    if obs_path.is_dir():
        sd_dir = obs_path / sd
        if not sd_dir.is_dir():
            return None
        for f in sd_dir.iterdir():
            if f.name.lower().endswith(suffix):
                raw = f.read_bytes()
                return gzip.decompress(raw) if suffix.endswith(".gz") else raw
        return None
    if obs_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(obs_path) as zf:
            for n in zf.namelist():
                if f"/{sd}/" in n.replace("\\", "/") and n.lower().endswith(suffix):
                    raw = zf.read(n)
                    return gzip.decompress(raw) if suffix.endswith(".gz") else raw
    return None


def deep_inspect_gti(obs_path: Path, sd: str) -> dict:
    """Inspect the GTI FITS for one SDD."""
    raw = _read_member(obs_path, sd, ".gti.gz")
    if raw is None:
        return {"present": False}
    with fits.open(io.BytesIO(raw), memmap=False) as hdul:
        hdr0 = hdul[0].header
        info = {
            "present": True,
            "n_hdus": len(hdul),
            "primary_TSTART": hdr0.get("TSTART", ""),
            "primary_TSTOP": hdr0.get("TSTOP", ""),
        }
        try:
            gti = hdul["GTI"].data
            hdr1 = hdul["GTI"].header
        except KeyError:
            gti = hdul[1].data
            hdr1 = hdul[1].header
        info["n_gti_rows"] = 0 if gti is None else int(len(gti))
        info["exposure"] = hdr1.get("EXPOSURE", None)
        return info


def deep_inspect_lc(obs_path: Path, sd: str) -> dict:
    raw = _read_member(obs_path, sd, ".lc.gz")
    if raw is None:
        return {"present": False}
    with fits.open(io.BytesIO(raw), memmap=False) as hdul:
        info_buf = io.StringIO()
        hdul.info(output=info_buf)
        rate = hdul["RATE"].data
        hdr = hdul["RATE"].header
        counts = np.asarray(rate["COUNTS"], dtype=np.float64)
        times = np.asarray(rate["TIME"], dtype=np.float64)
        return {
            "present": True,
            "hdu_info": info_buf.getvalue(),
            "n_rows": int(len(counts)),
            "n_nonnan": int(np.isfinite(counts).sum()),
            "n_nonzero": int((counts > 0).sum()),
            "counts_min": float(np.nanmin(counts)) if counts.size else None,
            "counts_max": float(np.nanmax(counts)) if counts.size else None,
            "counts_mean": float(np.nanmean(counts)) if counts.size else None,
            "counts_median": float(np.nanmedian(counts)) if counts.size else None,
            "TSTART": hdr.get("TSTART", None),
            "TSTOP": hdr.get("TSTOP", None),
            "time_first": float(times[0]) if times.size else None,
            "time_last": float(times[-1]) if times.size else None,
        }


def correlate_with_sdd2(obs_path: Path) -> dict:
    raw1 = _read_member(obs_path, "SDD1", ".lc.gz")
    raw2 = _read_member(obs_path, "SDD2", ".lc.gz")
    if raw1 is None or raw2 is None:
        return {"available": False}
    with fits.open(io.BytesIO(raw1), memmap=False) as h1, \
            fits.open(io.BytesIO(raw2), memmap=False) as h2:
        t1 = np.asarray(h1["RATE"].data["TIME"], dtype=np.float64)
        c1 = np.asarray(h1["RATE"].data["COUNTS"], dtype=np.float64)
        t2 = np.asarray(h2["RATE"].data["TIME"], dtype=np.float64)
        c2 = np.asarray(h2["RATE"].data["COUNTS"], dtype=np.float64)
    common = np.intersect1d(t1.astype(np.int64), t2.astype(np.int64))
    if common.size < 100:
        return {"available": True, "n_common": int(common.size), "corr": None}
    m1 = {int(t): float(c) for t, c in zip(t1, c1)}
    m2 = {int(t): float(c) for t, c in zip(t2, c2)}
    a1 = np.array([m1[t] for t in common])
    a2 = np.array([m2[t] for t in common])
    finite = np.isfinite(a1) & np.isfinite(a2)
    if finite.sum() < 100 or a1[finite].std() == 0 or a2[finite].std() == 0:
        return {"available": True, "n_common": int(common.size), "corr": None}
    corr = float(np.corrcoef(a1[finite], a2[finite])[0, 1])
    return {"available": True, "n_common": int(common.size), "corr": corr,
            "sdd1_mean": float(np.nanmean(a1)),
            "sdd2_mean": float(np.nanmean(a2))}


# ─────────────────────────────────────────────────────────────────────────────
# Task 3 — Oct 3 X9.0 validation plot
# ─────────────────────────────────────────────────────────────────────────────
def plot_oct3(obs_path: Path) -> Path | None:
    raw1 = _read_member(obs_path, "SDD1", ".lc.gz")
    raw2 = _read_member(obs_path, "SDD2", ".lc.gz")
    if raw1 is None or raw2 is None:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from datetime import timezone

    with fits.open(io.BytesIO(raw1), memmap=False) as h1, \
            fits.open(io.BytesIO(raw2), memmap=False) as h2:
        t1 = pd.to_datetime(np.asarray(h1["RATE"].data["TIME"]), unit="s", utc=True)
        c1 = np.asarray(h1["RATE"].data["COUNTS"], dtype=np.float64)
        t2 = pd.to_datetime(np.asarray(h2["RATE"].data["TIME"]), unit="s", utc=True)
        c2 = np.asarray(h2["RATE"].data["COUNTS"], dtype=np.float64)

    peak = pd.Timestamp("2024-10-03 12:18", tz="UTC")
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    axes[0].plot(t1, c1, color="tab:purple", lw=0.5)
    axes[0].set_title("SoLEXS SDD1 — full day")
    axes[0].set_ylabel("cts/s")
    axes[1].plot(t2, c2, color="tab:blue", lw=0.5)
    axes[1].set_title("SoLEXS SDD2 — full day")
    axes[1].set_ylabel("cts/s")
    z_lo = pd.Timestamp("2024-10-03 12:00", tz="UTC")
    z_hi = pd.Timestamp("2024-10-03 13:00", tz="UTC")
    m1 = (t1 >= z_lo) & (t1 <= z_hi)
    m2 = (t2 >= z_lo) & (t2 <= z_hi)
    axes[2].plot(t1[m1], c1[m1], color="tab:purple", lw=0.8, label="SDD1")
    axes[2].plot(t2[m2], c2[m2], color="tab:blue", lw=0.8, label="SDD2")
    axes[2].set_title("SDD1 vs SDD2 — 12:00–13:00 UT (X9.0 peak window)")
    axes[2].set_ylabel("cts/s")
    axes[2].legend()
    for ax in axes:
        ax.axvline(peak, color="black", ls="--", lw=1)
        ax.grid(True, alpha=0.3)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    fig.suptitle("SDD1 vs SDD2 — 2024-10-03 X9.0 flare", fontsize=13)
    fig.savefig(PLOT_PATH, dpi=140)
    plt.close(fig)
    return PLOT_PATH


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────
def write_md(report_sections: list[str]) -> None:
    OUT_MD.write_text("\n\n".join(report_sections), encoding="utf-8")


def main() -> int:
    obs = discover_observations()
    print(f"Discovered {len(obs)} SoLEXS observations")

    print("Building file inventory ...")
    inv = build_inventory(obs)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    inv.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")

    n_total = len(inv)
    n_sdd1_dir = int(inv["sdd1_exists"].sum())
    n_sdd1_lc = int(inv["has_lc"].sum())
    n_sdd1_pi = int(inv["has_pi"].sum())
    n_only_gti = int(((inv["has_gti"]) & (~inv["has_lc"]) & (~inv["has_pi"])).sum())
    print(f"\n[Inventory summary]")
    print(f"  total observations:       {n_total}")
    print(f"  with SDD1 dir/files:      {n_sdd1_dir}  ({100*n_sdd1_dir/n_total:.1f}%)")
    print(f"  with SDD1 .lc.gz:         {n_sdd1_lc}  ({100*n_sdd1_lc/n_total:.1f}%)")
    print(f"  with SDD1 .pi.gz:         {n_sdd1_pi}  ({100*n_sdd1_pi/n_total:.1f}%)")
    print(f"  with SDD1 only .gti.gz:   {n_only_gti}  ({100*n_only_gti/n_total:.1f}%)")
    if n_sdd1_lc:
        lc_sizes = inv.loc[inv["has_lc"], "lc_size_bytes"]
        print(f"  SDD1 LC size: min={lc_sizes.min()}  max={lc_sizes.max()}  "
              f"mean={lc_sizes.mean():.0f}  n={len(lc_sizes)}")

    # ── Task 2: deep inspection ──────────────────────────────────────────────
    sections = ["# SDD1 deep inspection report",
                f"Generated: {datetime.utcnow().isoformat()}Z",
                f"\nObservations scanned: **{n_total}**",
                f"\nSee `data/processed/sdd1_file_inventory.csv` for full file census."]

    print("\nDeep-inspecting GTI files (5-sample, including known-empty cases) ...")
    obs_map = {ds: p for ds, p in obs}
    sample_dates = inv["date"].iloc[[0, len(inv)//4, len(inv)//2,
                                      3*len(inv)//4, len(inv)-1]].tolist()
    for d in sample_dates:
        d_key = d.replace("-", "")
        p = obs_map.get(d_key)
        if p is None:
            continue
        gi = deep_inspect_gti(p, "SDD1")
        sections.append(
            f"## GTI inspection — {d} (SDD1)\n"
            f"```\n"
            f"present:           {gi['present']}\n"
            f"n_hdus:            {gi.get('n_hdus','-')}\n"
            f"primary TSTART:    {gi.get('primary_TSTART','-')!r}\n"
            f"primary TSTOP:     {gi.get('primary_TSTOP','-')!r}\n"
            f"GTI rows:          {gi.get('n_gti_rows','-')}\n"
            f"EXPOSURE keyword:  {gi.get('exposure','-')}\n"
            f"```"
        )

    if n_sdd1_lc:
        sections.append("## Light curve inspection (up to 10 samples)")
        lc_inv = inv[inv["has_lc"]].head(10)
        for _, row in lc_inv.iterrows():
            d = row["date"]
            d_key = d.replace("-", "")
            p = obs_map.get(d_key)
            if p is None:
                continue
            li = deep_inspect_lc(p, "SDD1")
            cor = correlate_with_sdd2(p)
            sections.append(
                f"### {d} (SDD1 light curve)\n"
                f"```\n{li.get('hdu_info','-')}```\n"
                f"```\n"
                f"rows:           {li.get('n_rows','-')}\n"
                f"non-NaN:        {li.get('n_nonnan','-')}\n"
                f"non-zero:       {li.get('n_nonzero','-')}\n"
                f"counts min:     {li.get('counts_min','-')}\n"
                f"counts max:     {li.get('counts_max','-')}\n"
                f"counts mean:    {li.get('counts_mean','-')}\n"
                f"counts median:  {li.get('counts_median','-')}\n"
                f"TSTART (hdr):   {li.get('TSTART','-')}\n"
                f"TSTOP  (hdr):   {li.get('TSTOP','-')}\n"
                f"time_first:     {li.get('time_first','-')}\n"
                f"time_last:      {li.get('time_last','-')}\n"
                f"--- correlation with SDD2 ---\n"
                f"available:      {cor.get('available')}\n"
                f"common samples: {cor.get('n_common','-')}\n"
                f"sdd1 mean cps:  {cor.get('sdd1_mean','-')}\n"
                f"sdd2 mean cps:  {cor.get('sdd2_mean','-')}\n"
                f"pearson corr:   {cor.get('corr','-')}\n"
                f"```"
            )

    write_md(sections)
    print(f"Wrote {OUT_MD}")

    # ── Task 3: Oct 3 plot ───────────────────────────────────────────────────
    oct3 = obs_map.get("20241003")
    plot_out: Path | None = None
    if oct3 is not None and n_sdd1_lc > 0:
        if inv.loc[inv.date == "2024-10-03", "has_lc"].any():
            plot_out = plot_oct3(oct3)
            print(f"Wrote {plot_out}")
        else:
            print("Oct 3 has no SDD1 .lc.gz — skipping comparison plot")

    # ── Final summary block ──────────────────────────────────────────────────
    n_nonempty = n_sdd1_lc  # by definition, lc presence == has data
    print()
    print("=" * 63)
    print("SDD1 INVESTIGATION COMPLETE")
    print("=" * 63)
    print(f"Total SoLEXS observations:       {n_total}")
    print(f"SDD1 directories present:        {n_sdd1_dir}  ({100*n_sdd1_dir/n_total:.1f}%)")
    print(f"SDD1 light curve files present:  {n_sdd1_lc}  ({100*n_sdd1_lc/n_total:.1f}%)")
    print(f"SDD1 spectrum files present:     {n_sdd1_pi}  ({100*n_sdd1_pi/n_total:.1f}%)")
    print(f"SDD1 with non-empty data:        {n_nonempty}  ({100*n_nonempty/n_total:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

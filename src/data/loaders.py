"""Aditya-L1 SoLEXS + HEL1OS FITS loaders.

Reads light curves and GTIs directly from zip archives using ``zipfile`` +
``BytesIO``, without ever extracting the ~365 GB of FITS to disk.

See ``PROJECT_CONTEXT.md`` for the on-disk layout and schema reference.

Public entry points
-------------------
- ``discover_hel1os()`` / ``discover_solexs()``  — index the data roots.
- ``load_hel1os_lightcurves(zip_path)``           — per-detector LC + GTI from
  one HEL1OS observation zip (~12 h).
- ``load_solexs_lightcurve(zip_path)``            — SDD2 LC + GTI from one
  SoLEXS daily zip.
- ``DetectorLC``                                  — common in-memory shape:
  ``bands``  : dict[band_label -> (unix_t[float64], rate[float64])]
  ``gti``    : list of (start_unix, stop_unix) intervals
"""
from __future__ import annotations

import gzip
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from astropy.io import fits

# Data-root paths come from src.config (env-overridable; see that module).
# Keeping the names here preserves every existing `from src.data.loaders import
# HEL1OS_ROOT` import while removing the hardcoded absolute paths.
from src.config import HEL1OS_ROOT, SOLEXS_ROOT  # noqa: F401

# MJD reference: MJD 40587.0 == 1970-01-01 00:00:00 UTC.
_MJD_UNIX_EPOCH_DAYS = 40587.0

HEL1OS_DETECTORS: tuple[str, ...] = ("cdte1", "cdte2", "czt1", "czt2")

# (label, HDU EXTNAME template). Label is used downstream as a column suffix.
HEL1OS_CDTE_BANDS: list[tuple[str, str]] = [
    ("5_20kev",   "CDTE{N}_LC_BAND_5.00KEV_TO_20.00KEV"),
    ("20_30kev",  "CDTE{N}_LC_BAND_20.00KEV_TO_30.00KEV"),
    ("30_40kev",  "CDTE{N}_LC_BAND_30.00KEV_TO_40.00KEV"),
    ("40_60kev",  "CDTE{N}_LC_BAND_40.00KEV_TO_60.00KEV"),
    ("1p8_90kev", "CDTE{N}_LC_BAND_1.80KEV_TO_90.00KEV"),
]
HEL1OS_CZT_BANDS: list[tuple[str, str]] = [
    ("20_40kev",  "CZT{N}_LC_BAND_20.00KEV_TO_40.00KEV"),
    ("40_60kev",  "CZT{N}_LC_BAND_40.00KEV_TO_60.00KEV"),
    ("60_80kev",  "CZT{N}_LC_BAND_60.00KEV_TO_80.00KEV"),
    ("80_150kev", "CZT{N}_LC_BAND_80.00KEV_TO_150.00KEV"),
    ("18_160kev", "CZT{N}_LC_BAND_18.00KEV_TO_160.00KEV"),
]

HEL1OS_ZIP_RE = re.compile(
    r"^HLS_(\d{8})_(\d{6})_(\d+)sec_lev1_V(\d{3})\.zip$", re.IGNORECASE
)
SOLEXS_ZIP_RE = re.compile(
    r"^AL1_SLX_L1_(\d{8})_v[\d.]+\.zip$", re.IGNORECASE
)
SOLEXS_DIR_RE = re.compile(
    r"^AL1_SLX_L1_(\d{8})_v[\d.]+$", re.IGNORECASE
)


# ─────────────────────────────────────────────────────────────────────────────
# Time helpers
# ─────────────────────────────────────────────────────────────────────────────
def mjd_to_unix_seconds(mjd: np.ndarray | float) -> np.ndarray | float:
    return (np.asarray(mjd, dtype=np.float64) - _MJD_UNIX_EPOCH_DAYS) * 86400.0


def bands_for(detector: str) -> list[tuple[str, str]]:
    return HEL1OS_CDTE_BANDS if detector.startswith("cdte") else HEL1OS_CZT_BANDS


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class DetectorLC:
    """Per-detector light curve(s) + good-time intervals on a unix time axis."""
    bands: dict[str, tuple[np.ndarray, np.ndarray]]
    gti: list[tuple[float, float]] = field(default_factory=list)


@dataclass(frozen=True)
class HEL1OSObs:
    """One HEL1OS observation zip (~12 h). Parsed from the filename."""
    path: Path
    start: datetime
    duration_sec: int
    version: int

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.duration_sec)

    @property
    def timestamp_key(self) -> str:
        return self.start.strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────────────
# Discovery — index the data roots
# ─────────────────────────────────────────────────────────────────────────────
def discover_hel1os(root: Path = HEL1OS_ROOT) -> list[HEL1OSObs]:
    """Return one ``HEL1OSObs`` per unique observation timestamp, picking the
    highest version when duplicates exist."""
    root = Path(root)
    seen: dict[str, HEL1OSObs] = {}
    for p in root.rglob("*.zip"):
        m = HEL1OS_ZIP_RE.match(p.name)
        if not m:
            continue
        date_s, time_s, dur_s, ver_s = m.groups()
        start = datetime.strptime(date_s + time_s, "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
        obs = HEL1OSObs(p, start, int(dur_s), int(ver_s))
        cur = seen.get(obs.timestamp_key)
        if cur is None or obs.version > cur.version:
            seen[obs.timestamp_key] = obs
    return sorted(seen.values(), key=lambda o: o.start)


def discover_solexs(root: Path = SOLEXS_ROOT) -> dict[str, Path]:
    """Return ``{YYYYMMDD: path}`` for SoLEXS daily observations.

    Handles two layouts: either ``AL1_SLX_L1_YYYYMMDD_v1.0.zip`` archives in
    ``root``, or already-extracted ``AL1_SLX_L1_YYYYMMDD_v1.0/`` directories.
    The mapped value is the zip path or the directory path; the loader
    dispatches on whichever it is.
    """
    root = Path(root)
    out: dict[str, Path] = {}
    for p in root.iterdir():
        if p.is_file():
            m = SOLEXS_ZIP_RE.match(p.name)
            if m:
                out[m.group(1)] = p
        elif p.is_dir():
            m = SOLEXS_DIR_RE.match(p.name)
            if m:
                out[m.group(1)] = p
    return out


def hel1os_obs_for_date(
    obs_list: list[HEL1OSObs], day: datetime
) -> list[HEL1OSObs]:
    """All observations whose [start, end) interval overlaps the UTC day."""
    if day.tzinfo is None:
        day = day.replace(tzinfo=timezone.utc)
    day_start = day
    day_end = day + timedelta(days=1)
    return [o for o in obs_list if o.start < day_end and o.end > day_start]


# ─────────────────────────────────────────────────────────────────────────────
# FITS-in-zip access helpers
# ─────────────────────────────────────────────────────────────────────────────
def _read_bytes_from_zip(zf: zipfile.ZipFile, internal_name: str) -> bytes:
    raw = zf.read(internal_name)
    if internal_name.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw


def _open_fits(buf: bytes) -> fits.HDUList:
    return fits.open(io.BytesIO(buf), memmap=False)


def _find_internal(zf: zipfile.ZipFile, *suffixes: str) -> str | None:
    """First member whose lowercased name ends with any of the given suffixes."""
    needles = tuple(s.lower() for s in suffixes)
    for name in zf.namelist():
        lname = name.lower()
        if any(lname.endswith(n) for n in needles):
            return name
    return None


# ─────────────────────────────────────────────────────────────────────────────
# HEL1OS loader
# ─────────────────────────────────────────────────────────────────────────────
def load_hel1os_lightcurves(zip_path: Path) -> dict[str, DetectorLC]:
    """Read all four detectors' pre-binned light curves + GTIs from one
    HEL1OS observation zip. Returns ``{detector: DetectorLC}``.

    Missing detectors (no LC or no GTI member) are silently skipped.
    """
    zip_path = Path(zip_path)
    out: dict[str, DetectorLC] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for det in HEL1OS_DETECTORS:
            sub = "cdte" if det.startswith("cdte") else "czt"
            lc_member = _find_internal(zf, f"/{sub}/lightcurve_{det}.fits")
            gti_member = _find_internal(zf, f"/aux/gti{det}.fits")
            if lc_member is None or gti_member is None:
                continue

            n_upper = det[-1]  # "1" or "2"
            band_defs = bands_for(det)

            bands: dict[str, tuple[np.ndarray, np.ndarray]] = {}
            with _open_fits(_read_bytes_from_zip(zf, lc_member)) as hdul:
                for label, hdu_tmpl in band_defs:
                    extname = hdu_tmpl.format(N=n_upper)
                    try:
                        data = hdul[extname].data
                    except KeyError:
                        continue
                    mjd = np.asarray(data["MJD"], dtype=np.float64)
                    ctr = np.asarray(data["CTR"], dtype=np.float64)
                    bands[label] = (mjd_to_unix_seconds(mjd), ctr)

            gti_intervals: list[tuple[float, float]] = []
            with _open_fits(_read_bytes_from_zip(zf, gti_member)) as hdul:
                gti_extname = f"GTI_{det.upper()}"
                try:
                    gtbl = hdul[gti_extname].data
                except KeyError:
                    gtbl = hdul[1].data
                if gtbl is not None and len(gtbl) > 0:
                    starts = mjd_to_unix_seconds(
                        np.asarray(gtbl["tstart"], dtype=np.float64)
                    )
                    stops = mjd_to_unix_seconds(
                        np.asarray(gtbl["tstop"], dtype=np.float64)
                    )
                    gti_intervals = list(zip(starts.tolist(), stops.tolist()))

            if bands:
                out[det] = DetectorLC(bands=bands, gti=gti_intervals)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# SoLEXS loader (SDD2 only — SDD1 has no science data)
# ─────────────────────────────────────────────────────────────────────────────
def _read_solexs_members(path: Path) -> tuple[bytes, bytes] | None:
    """Return raw (already gunzipped) bytes for (lc_fits, gti_fits), or None."""
    path = Path(path)
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            lc_m = _find_internal(zf, "sdd2_l1.lc.gz")
            gti_m = _find_internal(zf, "sdd2_l1.gti.gz")
            if lc_m is None or gti_m is None:
                return None
            return (
                _read_bytes_from_zip(zf, lc_m),
                _read_bytes_from_zip(zf, gti_m),
            )
    if path.is_dir():
        sdd2 = path / "SDD2"
        if not sdd2.is_dir():
            return None
        lc_files = list(sdd2.glob("*SDD2_L1.lc.gz"))
        gti_files = list(sdd2.glob("*SDD2_L1.gti.gz"))
        if not lc_files or not gti_files:
            return None
        return (
            gzip.decompress(lc_files[0].read_bytes()),
            gzip.decompress(gti_files[0].read_bytes()),
        )
    return None


def load_solexs_lightcurve(path: Path) -> DetectorLC | None:
    """Read SoLEXS SDD2 light curve + GTI from one daily observation. Accepts
    either a ``.zip`` archive or an already-extracted observation directory.
    Returns ``None`` if SDD2 LC or GTI is missing/empty."""
    raw = _read_solexs_members(Path(path))
    if raw is None:
        return None
    lc_bytes, gti_bytes = raw

    with _open_fits(lc_bytes) as hdul:
        rate = hdul["RATE"].data
        t = np.asarray(rate["TIME"], dtype=np.float64)
        counts = np.asarray(rate["COUNTS"], dtype=np.float64)

    gti_intervals: list[tuple[float, float]] = []
    with _open_fits(gti_bytes) as hdul:
        try:
            gtbl = hdul["GTI"].data
        except KeyError:
            gtbl = hdul[1].data
        if gtbl is not None and len(gtbl) > 0:
            starts = np.asarray(gtbl["START"], dtype=np.float64)
            stops = np.asarray(gtbl["STOP"], dtype=np.float64)
            gti_intervals = list(zip(starts.tolist(), stops.tolist()))

    if t.size == 0 or not gti_intervals:
        return None
    return DetectorLC(bands={"total": (t, counts)}, gti=gti_intervals)

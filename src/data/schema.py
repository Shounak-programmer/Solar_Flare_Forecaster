"""Schema conventions and wide↔tidy reshaping for daily light curve Parquets.

Canonical on-disk format is the **wide** schema produced by
``scripts/01_build_daily_lightcurves.py``: one row per UTC second, one column
per detector×band rate, plus a per-detector ``..._gti`` bool. This module
exposes:

- ``DETECTOR_BANDS``      : ordered list of (detector, band) pairs we ship.
- ``rate_column(d,b)`` / ``gti_column(d)`` : canonical column names.
- ``to_tidy(df_wide, ...)`` : reshape wide → long with optional GTI filtering.
- ``available_detectors(df_wide)`` : detectors that have any non-NaN data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Detector + band catalog. Detector name uses the form that appears in
# instrument papers and judge-facing material (CdTe1, CdTe2, CZT1, CZT2,
# SoLEXS-SDD2). The underlying column-name slug is lowercase for safety.
SOLEXS_BANDS: tuple[str, ...] = ("total",)
HEL1OS_CDTE_BAND_LABELS: tuple[str, ...] = (
    "5_20kev", "20_30kev", "30_40kev", "40_60kev", "1p8_90kev",
)
HEL1OS_CZT_BAND_LABELS: tuple[str, ...] = (
    "20_40kev", "40_60kev", "60_80kev", "80_150kev", "18_160kev",
)

DETECTOR_BANDS: list[tuple[str, str]] = (
    [("SoLEXS-SDD2", b) for b in SOLEXS_BANDS]
    + [(f"HEL1OS-CdTe{n}", b) for n in (1, 2) for b in HEL1OS_CDTE_BAND_LABELS]
    + [(f"HEL1OS-CZT{n}",  b) for n in (1, 2) for b in HEL1OS_CZT_BAND_LABELS]
)


def _slug(detector: str) -> str:
    """Map a public detector name (e.g. "HEL1OS-CdTe1") to its column slug
    (e.g. "hel1os_cdte1"). SoLEXS-SDD2 → "solexs_sdd2"."""
    return detector.lower().replace("-", "_")


def rate_column(detector: str, band: str) -> str:
    return f"{_slug(detector)}_{band}"


def gti_column(detector: str) -> str:
    return f"{_slug(detector)}_gti"


def available_detectors(df_wide: pd.DataFrame) -> list[str]:
    """Detectors whose rate columns exist in ``df_wide``."""
    out: list[str] = []
    seen: set[str] = set()
    for det, band in DETECTOR_BANDS:
        if det in seen:
            continue
        if rate_column(det, band) in df_wide.columns:
            out.append(det)
            seen.add(det)
    return out


def to_tidy(
    df_wide: pd.DataFrame,
    *,
    apply_gti: bool = True,
    drop_nan: bool = True,
    detectors: list[str] | None = None,
) -> pd.DataFrame:
    """Reshape a wide daily Parquet to tidy/long form.

    Columns out: ``utc``, ``detector``, ``band``, ``count_rate``, ``in_gti``.

    Parameters
    ----------
    df_wide
        DataFrame with columns ``utc`` + per-detector rate/gti columns,
        as written by ``scripts/01_build_daily_lightcurves.py``.
    apply_gti
        If True (default), drop rows where the detector's GTI is False.
    drop_nan
        If True (default), drop rows with NaN ``count_rate``.
    detectors
        Optional subset of detector names to include (defaults to all present).
    """
    if "utc" not in df_wide.columns:
        raise ValueError("df_wide must have a 'utc' column")
    keep_dets = set(detectors) if detectors else set(available_detectors(df_wide))
    utc = df_wide["utc"].to_numpy()

    pieces: list[pd.DataFrame] = []
    for det, band in DETECTOR_BANDS:
        if det not in keep_dets:
            continue
        rc, gc = rate_column(det, band), gti_column(det)
        if rc not in df_wide.columns:
            continue
        rates = df_wide[rc].to_numpy()
        gti = (
            df_wide[gc].to_numpy().astype(bool)
            if gc in df_wide.columns
            else np.ones(len(df_wide), dtype=bool)
        )
        mask = np.ones(len(df_wide), dtype=bool)
        if apply_gti:
            mask &= gti
        if drop_nan:
            mask &= ~np.isnan(rates)
        if not mask.any():
            continue
        pieces.append(pd.DataFrame({
            "utc": utc[mask],
            "detector": det,
            "band": band,
            "count_rate": rates[mask],
            "in_gti": gti[mask],
        }))

    if not pieces:
        return pd.DataFrame(
            columns=["utc", "detector", "band", "count_rate", "in_gti"]
        )
    out = pd.concat(pieces, ignore_index=True)
    out["detector"] = out["detector"].astype("category")
    out["band"] = out["band"].astype("category")
    return out

"""Shared detection helpers (importable; the numbered run-scripts have leading
digits and can't be imported)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LBL_DIR = PROJECT_ROOT / "data" / "processed" / "labeled_seconds"

# detector -> (total-band rate column, gti column)
DETECTORS: dict[str, tuple[str, str]] = {
    "solexs_sdd2": ("solexs_sdd2_total", "solexs_sdd2_gti"),
    "hel1os_cdte1": ("hel1os_cdte1_1p8_90kev", "hel1os_cdte1_gti"),
    "hel1os_cdte2": ("hel1os_cdte2_1p8_90kev", "hel1os_cdte2_gti"),
    "hel1os_czt1": ("hel1os_czt1_18_160kev", "hel1os_czt1_gti"),
    "hel1os_czt2": ("hel1os_czt2_18_160kev", "hel1os_czt2_gti"),
}


def load_detector_day(date_str: str, detector: str):
    """Return (utc Series, count_rate float64, gti bool, is_flare int8)."""
    rate_col, gti_col = DETECTORS[detector]
    df = pd.read_parquet(LBL_DIR / f"{date_str}.parquet",
                         columns=["utc", rate_col, gti_col, "is_flare"])
    if not pd.api.types.is_datetime64_any_dtype(df["utc"]):
        df["utc"] = pd.to_datetime(df["utc"], utc=True)
    return (df["utc"], df[rate_col].to_numpy(np.float64),
            df[gti_col].to_numpy(bool), df["is_flare"].to_numpy(np.int8))

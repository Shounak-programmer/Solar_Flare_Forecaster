"""Central path configuration.

All data-root paths are read from environment variables so the pipeline is
portable (laptop, lab box, cloud VM) without editing source. Defaults preserve
the original development layout, so existing runs keep working unchanged.

Override by setting any of these before running:
    ADITYA_PROJECT_ROOT   project root (default: repo root inferred from this file)
    ADITYA_HEL1OS_ROOT    HEL1OS raw-zip archive  (default: <project>/data/HEL1OS)
    ADITYA_SOLEXS_ROOT    SoLEXS raw-zip archive  (default: <project>/data/SoLEXS)
    ADITYA_DATA_ROOT      processed/aux data root (default: <project>/data)

On Windows PowerShell:  $env:ADITYA_HEL1OS_ROOT = "D:/Data/HEL1OS"
On bash:                export ADITYA_HEL1OS_ROOT=/data/HEL1OS
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = two levels up from this file (src/config.py -> src -> repo).
_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROJECT_ROOT = Path(os.environ.get("ADITYA_PROJECT_ROOT", _DEFAULT_PROJECT_ROOT))
DATA_ROOT = Path(os.environ.get("ADITYA_DATA_ROOT", PROJECT_ROOT / "data"))

# Raw instrument archives (configurable via env vars).
HEL1OS_ROOT = Path(os.environ.get("ADITYA_HEL1OS_ROOT", DATA_ROOT / "HEL1OS"))
SOLEXS_ROOT = Path(os.environ.get("ADITYA_SOLEXS_ROOT", DATA_ROOT / "SoLEXS"))

# Common processed sub-roots (single source of truth for downstream scripts).
PROCESSED = DATA_ROOT / "processed"
REPORTS = PROCESSED / "reports"

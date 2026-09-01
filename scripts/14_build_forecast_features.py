"""Stage 4a — build the leakage-safe forecasting feature matrix (1-min cadence).

Writes one parquet per day to data/processed/forecast_features/. Parallel.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.features import (
    LBL_DIR, build_day_features, load_event_tables,
)

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "forecast_features"

_TABLES = None


def _init():
    global _TABLES
    _TABLES = load_event_tables()


def _one(day: str) -> tuple[str, int, str]:
    try:
        out = build_day_features(day, *_TABLES)
        out.to_parquet(OUT_DIR / f"{day}.parquet", index=False)
        return day, len(out), "ok"
    except Exception as exc:  # noqa: BLE001
        import traceback
        return day, 0, f"FAIL {type(exc).__name__}: {exc}\n{traceback.format_exc()}"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    days = sorted(p.stem for p in LBL_DIR.glob("*.parquet"))
    print(f"Building forecast features for {days[0]}..{days[-1]} ({len(days)} days)")
    t0 = time.time()
    from multiprocessing import Pool
    ok = 0
    fails = []
    with Pool(4, initializer=_init) as pool:
        for i, (day, n, status) in enumerate(pool.imap_unordered(_one, days), 1):
            if status == "ok":
                ok += 1
            else:
                fails.append((day, status))
            if i % 100 == 0:
                print(f"  {i}/{len(days)} ({time.time()-t0:.0f}s)")
    print(f"Done: {ok} ok, {len(fails)} failed, {time.time()-t0:.0f}s")
    for d, s in fails[:5]:
        print(f"  FAIL {d}: {s.splitlines()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

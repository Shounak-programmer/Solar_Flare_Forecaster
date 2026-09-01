"""HEL1OS coverage audit against the SoLEXS reference timeline (read-only).

Steps 1-5 of the coverage-audit workflow. Produces:
  data/processed/hel1os_coverage_audit.csv
  data/processed/hel1os_missing_dates.txt
and prints the summary block.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOLEXS_ROOT = PROJECT_ROOT / "data" / "SoLEXUS"
HEL1OS_ROOT = PROJECT_ROOT / "data" / "HEL1OS"
OUT_CSV = PROJECT_ROOT / "data" / "processed" / "hel1os_coverage_audit.csv"
OUT_TXT = PROJECT_ROOT / "data" / "processed" / "hel1os_missing_dates.txt"
MANIFEST = PROJECT_ROOT / "data" / "processed" / "coverage_manifest.csv"

SOLEXS_DIR_RE = re.compile(r"^AL1_SLX_L1_(\d{8})_v[\d.]+$", re.IGNORECASE)
SOLEXS_ZIP_RE = re.compile(r"^AL1_SLX_L1_(\d{8})_v[\d.]+\.zip$", re.IGNORECASE)
HEL1OS_RE = re.compile(
    r"^HLS_(\d{8})_(\d{6})_(\d+)sec_lev1_V(\d{3})\.zip$", re.IGNORECASE
)

FULL_THRESHOLD = 0.90


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — SoLEXS reference timeline
# ─────────────────────────────────────────────────────────────────────────────
def build_solexs_dates() -> set[str]:
    dates: set[str] = set()
    for p in SOLEXS_ROOT.iterdir():
        if p.is_dir():
            m = SOLEXS_DIR_RE.match(p.name)
        elif p.is_file():
            m = SOLEXS_ZIP_RE.match(p.name)
        else:
            m = None
        if m:
            dates.add(m.group(1))
    return dates


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — HEL1OS date+coverage map
# ─────────────────────────────────────────────────────────────────────────────
def build_hel1os_map() -> dict[str, dict]:
    """Return {YYYYMMDD: {n_obs, seconds, spans:[(start_dt,end_dt)], fraction}}.

    Observations are de-duplicated by (date, start_time) keeping highest
    version. Durations are clipped to the calendar day they belong to so an
    observation spanning midnight contributes seconds to each day correctly.
    """
    # de-dup by (date, start_time) -> (version, duration)
    best: dict[tuple[str, str], tuple[int, int]] = {}
    for p in HEL1OS_ROOT.iterdir():
        if not p.is_file():
            continue
        m = HEL1OS_RE.match(p.name)
        if not m:
            continue
        date_s, time_s, dur_s, ver_s = m.groups()
        key = (date_s, time_s)
        ver, dur = int(ver_s), int(dur_s)
        cur = best.get(key)
        if cur is None or ver > cur[0]:
            best[key] = (ver, dur)

    # accumulate per-calendar-day, splitting across midnight
    day_spans: dict[str, list[tuple[datetime, datetime]]] = {}
    for (date_s, time_s), (_ver, dur) in best.items():
        start = datetime.strptime(date_s + time_s, "%Y%m%d%H%M%S")
        end = start + timedelta(seconds=dur)
        cur = start
        while cur < end:
            day = cur.date()
            day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
            seg_end = min(end, day_end)
            day_spans.setdefault(day.strftime("%Y%m%d"), []).append((cur, seg_end))
            cur = seg_end

    out: dict[str, dict] = {}
    for d, spans in day_spans.items():
        spans.sort()
        total_sec = sum((e - s).total_seconds() for s, e in spans)
        out[d] = {
            "n_obs": len(spans),
            "seconds": int(total_sec),
            "spans": spans,
            "fraction": min(1.0, total_sec / 86400.0),
        }
    return out


def merge_spans(spans: list[tuple[datetime, datetime]],
                gap_tol: int = 60) -> list[tuple[datetime, datetime]]:
    """Merge spans separated by <= gap_tol seconds for readable display."""
    if not spans:
        return []
    merged = [spans[0]]
    for s, e in spans[1:]:
        ps, pe = merged[-1]
        if (s - pe).total_seconds() <= gap_tol:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


def fmt_spans(spans: list[tuple[datetime, datetime]]) -> str:
    merged = merge_spans(spans)
    return "; ".join(f"{s:%H:%M}-{e:%H:%M}" for s, e in merged)


def missing_part_of_day(spans: list[tuple[datetime, datetime]]) -> str:
    """Human description of which part of the day is NOT covered."""
    merged = merge_spans(spans)
    if not merged:
        return "all day missing"
    day = merged[0][0].date()
    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    gaps = []
    cursor = day_start
    for s, e in merged:
        if (s - cursor).total_seconds() > 300:  # >5 min gap
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if (day_end - cursor).total_seconds() > 300:
        gaps.append((cursor, day_end))
    if not gaps:
        return "negligible gaps"
    return ", ".join(f"{g0:%H:%M}-{g1:%H:%M} missing" for g0, g1 in gaps)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — classify
# ─────────────────────────────────────────────────────────────────────────────
def classify(has_sx: bool, has_h: bool, fraction: float) -> str:
    if has_h and fraction >= FULL_THRESHOLD:
        return "FULL"
    if has_h and fraction > 0:
        return "PARTIAL"
    if has_sx and not has_h:
        return "MISSING"
    if has_h and not has_sx:
        return "NO_SOLEXS"
    return "NEITHER"


def consecutive_runs(dates: list[date]) -> list[tuple[date, date, int]]:
    if not dates:
        return []
    dates = sorted(dates)
    runs = []
    run_start = prev = dates[0]
    for d in dates[1:]:
        if (d - prev).days == 1:
            prev = d
        else:
            runs.append((run_start, prev, (prev - run_start).days + 1))
            run_start = prev = d
    runs.append((run_start, prev, (prev - run_start).days + 1))
    return runs


def main() -> int:
    # STEP 1
    sx_dates = build_solexs_dates()
    sx_sorted = sorted(sx_dates)
    sx_d0 = datetime.strptime(sx_sorted[0], "%Y%m%d").date()
    sx_d1 = datetime.strptime(sx_sorted[-1], "%Y%m%d").date()
    sx_internal_gaps = []
    cur = sx_d0
    while cur <= sx_d1:
        if cur.strftime("%Y%m%d") not in sx_dates:
            sx_internal_gaps.append(cur)
        cur += timedelta(days=1)
    print("[STEP 1] SoLEXS reference timeline")
    print(f"  total SoLEXS dates: {len(sx_dates)}")
    print(f"  earliest: {sx_d0}   latest: {sx_d1}")
    print(f"  internal missing calendar days: {len(sx_internal_gaps)}")
    if sx_internal_gaps:
        for r0, r1, n in consecutive_runs(sx_internal_gaps):
            tag = f"{r0}" if n == 1 else f"{r0} to {r1} ({n} days)"
            print(f"    SoLEXS gap: {tag}")

    # STEP 2
    hel_map = build_hel1os_map()
    print("\n[STEP 2] HEL1OS coverage map")
    print(f"  HEL1OS dates with >=1 observation: {len(hel_map)}")

    # STEP 3 — full range across both
    all_d0 = min(sx_d0, min(datetime.strptime(d, "%Y%m%d").date() for d in hel_map))
    all_d1 = max(sx_d1, max(datetime.strptime(d, "%Y%m%d").date() for d in hel_map))

    rows = []
    cur = all_d0
    while cur <= all_d1:
        ds = cur.strftime("%Y%m%d")
        has_sx = ds in sx_dates
        h = hel_map.get(ds)
        has_h = h is not None
        frac = h["fraction"] if has_h else 0.0
        status = classify(has_sx, has_h, frac)
        rows.append({
            "date": cur.isoformat(),
            "has_solexs": has_sx,
            "has_hel1os": has_h,
            "hel1os_n_obs": h["n_obs"] if has_h else 0,
            "hel1os_seconds": h["seconds"] if has_h else 0,
            "hel1os_day_fraction": round(frac, 4),
            "time_spans": fmt_spans(h["spans"]) if has_h else "",
            "status": status,
        })
        cur += timedelta(days=1)

    df = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\n[STEP 3] wrote {OUT_CSV}  ({len(df)} calendar days)")

    # STEP 4 — missing-dates report
    missing_df = df[df.status == "MISSING"]
    partial_df = df[df.status == "PARTIAL"]
    missing_dates = [datetime.strptime(d, "%Y-%m-%d").date()
                     for d in missing_df.date]

    lines: list[str] = []
    lines.append("HEL1OS MISSING / PARTIAL COVERAGE REPORT")
    lines.append(f"Generated: {datetime.utcnow().isoformat()}Z")
    lines.append(f"Reference timeline: SoLEXS ({sx_d0} .. {sx_d1})")
    lines.append("=" * 70)
    lines.append("")
    lines.append("SECTION A - COMPLETELY MISSING (SoLEXS has it, HEL1OS does not)")
    lines.append("-" * 70)
    runs = consecutive_runs(missing_dates)
    for r0, r1, n in runs:
        if n == 1:
            lines.append(f"{r0}")
        else:
            lines.append(f"{r0} to {r1} ({n} days)")
    lines.append(f"\n  Section A total: {len(missing_dates)} missing dates "
                 f"in {len(runs)} run(s)")
    lines.append("")
    lines.append("SECTION B - PARTIAL COVERAGE (HEL1OS present, < 90% of day)")
    lines.append("-" * 70)
    for _, r in partial_df.iterrows():
        ds = r.date.replace("-", "")
        spans = hel_map[ds]["spans"]
        pct = int(round(r.hel1os_day_fraction * 100))
        lines.append(f"{r.date}: {pct}% covered, present {r.time_spans}, "
                     f"{missing_part_of_day(spans)}")
    lines.append(f"\n  Section B total: {len(partial_df)} partial dates")
    lines.append("")
    lines.append("SECTION C - RE-DOWNLOAD LIST (Section A dates)")
    lines.append("-" * 70)
    bare = [d.isoformat() for d in missing_dates]
    lines.append("# comma-separated:")
    lines.append(",".join(bare))
    lines.append("")
    lines.append("# newline-separated:")
    lines.extend(bare)
    OUT_TXT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[STEP 4] wrote {OUT_TXT}")

    # STEP 5 — summary block
    counts = df.status.value_counts().to_dict()
    largest = max(runs, key=lambda r: r[2]) if runs else None

    # impact on our 496 built joint days
    impact_n = 0
    if MANIFEST.exists():
        mf = pd.read_csv(MANIFEST)
        built = set(mf.loc[mf.parquet_exists == True, "date"])
        impact_n = len(set(missing_df.date) & built)  # should be 0 by construction
    missing_in_sx_window = missing_df[
        (missing_df.date >= sx_d0.isoformat())
        & (missing_df.date <= sx_d1.isoformat())
    ]

    print()
    print("=" * 63)
    print("HEL1OS COVERAGE AUDIT")
    print("=" * 63)
    print(f"Date range audited:              {all_d0} to {all_d1}")
    print(f"Total calendar days in range:    {len(df)}")
    print(f"SoLEXS dates present:            {len(sx_dates)}")
    print(f"HEL1OS dates present:            {len(hel_map)}")
    print()
    print(f"FULL coverage days:              {counts.get('FULL', 0)}")
    print(f"PARTIAL coverage days:           {counts.get('PARTIAL', 0)}")
    print(f"COMPLETELY MISSING days:         {counts.get('MISSING', 0)}   <-- need re-download")
    print(f"NO_SOLEXS (HEL1OS only):         {counts.get('NO_SOLEXS', 0)}")
    print(f"NEITHER (true gaps):             {counts.get('NEITHER', 0)}")
    print()
    if largest:
        print(f"Largest missing run:             {largest[2]} days "
              f"({largest[0]} to {largest[1]})")
    else:
        print(f"Largest missing run:             0 days")
    print(f"Missing days inside SoLEXS")
    print(f"  reference window:              {len(missing_in_sx_window)}")
    print(f"Built joint days affected:       {impact_n} of 496")
    print("=" * 63)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

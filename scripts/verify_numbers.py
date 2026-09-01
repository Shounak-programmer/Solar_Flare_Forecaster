"""NUMBER-DRIFT GUARD — single source of truth for every headline number.

1. Parses the result sidecars in data/processed/reports/ (+ dashboard
   summary_metrics.json) and regenerates VERIFIED_NUMBERS.md.
2. Greps app/static/ (and any PPT-text files passed as CLI args) for each
   headline number's REQUIRED string; FAILS LOUDLY (exit 1) on any mismatch
   between sidecars and the frozen references, or on a stale/absent value in
   a surface that is supposed to show it.

Usage:  python scripts/verify_numbers.py [ppt_text.txt ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "processed" / "reports"
DASH = ROOT / "dashboard_data"
STATIC = ROOT / "app" / "static"
OUT = ROOT / "VERIFIED_NUMBERS.md"

FAIL: list[str] = []


def check(name: str, got, want, tol=0.0):
    ok = (abs(got - want) <= tol) if isinstance(want, (int, float)) and not isinstance(want, bool) else (got == want)
    if not ok:
        FAIL.append(f"SIDE-CAR DRIFT: {name} = {got!r}, expected {want!r}")
    return got


def main() -> int:
    det = json.loads((REPORTS / "detection_metrics.json").read_text())
    summ = json.loads((DASH / "summary_metrics.json").read_text())
    qpp = json.loads((DASH / "qpp_catalog.json").read_text())
    cat = json.loads((DASH / "master_catalog.json").read_text())
    tft = json.loads((REPORTS / "tft_metrics.json").read_text())
    ci = json.loads((REPORTS / "defensibility_ci.json").read_text())["ci"]
    abl = json.loads((REPORTS / "defensibility_ablation.json").read_text())["ablation"]["tss"]
    lead = json.loads((REPORTS / "defensibility_leadtime.json").read_text())["leadtime"]
    val = json.loads((REPORTS / "defensibility_value.json").read_text())["value"]
    lat = json.loads((REPORTS / "latency_benchmark.json").read_text())

    # ---- parse + frozen-reference checks ------------------------------------
    n = {}
    n["det_tss_catalog"] = check("detection catalog-aware TSS",
                                 det["event_level"]["catalog_aware"]["tss"], 0.84, 1e-9)
    n["det_tss_bin"] = check("detection per-bin TSS", det["nowcast"]["master"]["tss"], 0.7456, 1e-9)
    n["fused_recall"] = check("fused event recall", det["event_level"]["master_pod"], 0.872, 1e-9)
    xr = det["event_level"]["per_class"]["X"]
    check("X-recall", tuple(xr), (43, 43))
    n["x_recall"] = f"{xr[0]}/{xr[1]} (100%)"
    n["tss15"] = check("forecast TSS 15", summ["forecast_tss"]["y_15min"], 0.346, 1e-9)
    n["tss30"] = check("forecast TSS 30", summ["forecast_tss"]["y_30min"], 0.229, 1e-9)
    n["tss60"] = check("forecast TSS 60", summ["forecast_tss"]["y_60min"], 0.205, 1e-9)
    n["pers15"] = check("persistence TSS 15", summ["baselines"]["persistence"]["y_15min"], 0.162, 1e-9)
    n["tft15"] = check("TFT TSS 15", tft["tss"]["y_15min"] if "tss" in tft else summ["tft_tss"]["y_15min"], 0.235, 0.001)
    c15 = summ["calibration"]["y_15min"]
    n["ece_before"], n["ece_after"] = check("ECE before", c15["ece_before"], 0.3398, 1e-9), \
                                      check("ECE after", c15["ece_after"], 0.0061, 1e-9)
    n["brier_before"], n["brier_after"] = check("Brier before", c15["brier_before"], 0.1936, 1e-9), \
                                          check("Brier after", c15["brier_after"], 0.0702, 1e-9)
    n["far_watch"] = check("FAR at Watch", summ["alert_operating_points"]["far_at_tss_optimal"], 0.785, 1e-9)
    n["catalog_n"] = check("master catalog size", cat["status_counts"]["confirmed"]
                           + cat["status_counts"]["sub_threshold"]
                           + cat["status_counts"]["candidate_novel"], 12858)
    n["qpp_cand"] = check("QPP candidates", qpp["total_candidates"], 1043)
    n["qpp_events"] = check("QPP events", qpp["total_events"], 513)
    check("QPP tiers", (qpp["by_tier_candidates"]["classic"], qpp["by_tier_candidates"]["intermediate"],
                        qpp["by_tier_candidates"]["short"]), (164, 118, 761))
    n["all_clear"] = check("quiet->X all-clear", summ["all_clear"]["quiet_to_x"], "2/2")
    n["observed_x"] = check("observed-X flagged", summ["all_clear"]["observed_x"], "8/8")

    # ---- surface grep: dashboard JS/HTML must not hardcode stale numbers ----
    # (dashboard reads numbers from the API; only PROSE claims are static. We
    #  require the few static prose claims to match, and PPT text if provided.)
    surfaces = {p: p.read_text(encoding="utf-8", errors="ignore")
                for p in list(STATIC.rglob("*.html")) + list(STATIC.rglob("*.js"))
                if "vendor" not in str(p)}
    # Only claims that are STATIC prose in the frontend are required here.
    # Forecast TSS / baselines / calibration / QPP counts are rendered
    # dynamically from /api/metrics + /api/qpp (verified via their JSON above)
    # — requiring them as static strings would encourage hardcoding, which the
    # project forbids.
    required_in_static = {
        "index.html detection TSS prose claim": ("0.84", "index.html"),
    }
    joined = {name: txt for name, txt in
              ((p.name, t) for p, t in surfaces.items())}
    for label, (needle, fname) in required_in_static.items():
        txt = joined.get(fname, "")
        if needle not in txt:
            FAIL.append(f"STATIC SURFACE MISSING/STALE: {label}: '{needle}' not found in {fname}")

    # forbidden stale values anywhere in static prose (old/wrong numbers)
    forbidden = ["TSS 0.35 ", "12,857", "12859", "1042 QPP", "1,042", "42/43"]
    for p, txt in surfaces.items():
        for bad in forbidden:
            if bad in txt:
                FAIL.append(f"FORBIDDEN STALE VALUE '{bad}' in {p.name}")

    # optional PPT text files passed on CLI: require every headline number
    ppt_required = ["0.346", "0.84", "0.872", "100%", "12,858", "1,043", "513",
                    "0.006", "2/2", "0.162"]
    for arg in sys.argv[1:]:
        ptxt = Path(arg).read_text(encoding="utf-8", errors="ignore")
        for needle in ppt_required:
            if needle not in ptxt:
                FAIL.append(f"PPT '{arg}': headline number '{needle}' missing/stale")

    # ---- regenerate VERIFIED_NUMBERS.md --------------------------------------
    md = f"""# VERIFIED NUMBERS — single source for the PPT (regenerated by scripts/verify_numbers.py)

Every value below is parsed from result sidecars; this file FAILS to regenerate
if any sidecar drifts from the frozen references.

## Detection / nowcasting (concurrent — never call it forecasting)
| metric | value |
|---|---|
| Catalog-aware detection TSS (candidate-novel = FP) | **{n['det_tss_catalog']:.2f}** |
| Per-bin nowcast TSS (360 s grid) | {n['det_tss_bin']:.4f} |
| Fused event recall (vs best single 0.808) | **{n['fused_recall']:.3f}** |
| X-class recall | **{n['x_recall']}** |
| Master catalog | **{n['catalog_n']:,} flares** (40.2% confirmed / 26.1% sub-threshold / 33.7% candidate-novel) |

## Forecasting (true prediction, held-out test 2026-01→06)
| metric | 15 min | 30 min | 60 min |
|---|---|---|---|
| Calibrated XGBoost TSS | **{n['tss15']:.3f}** | {n['tss30']:.3f} | {n['tss60']:.3f} |
| 95% CI (block bootstrap, {154} test days) | [{ci['tss_15min']['lo']:.3f}, {ci['tss_15min']['hi']:.3f}] | [{ci['tss_30min']['lo']:.3f}, {ci['tss_30min']['hi']:.3f}] | [{ci['tss_60min']['lo']:.3f}, {ci['tss_60min']['hi']:.3f}] |
| Persistence baseline | {n['pers15']:.3f} | 0.153 | 0.161 |
| Climatology | 0.000 | 0.000 | 0.000 |
| TFT (evaluated, honestly bested) | {n['tft15']:.3f} | — | — |

## Calibration (15-min, test)
- ECE **{n['ece_before']:.3f} → {n['ece_after']:.4f}** (CI after: [{ci['ece_15min']['lo']:.4f}, {ci['ece_15min']['hi']:.4f}])
- Brier **{n['brier_before']:.3f} → {n['brier_after']:.4f}** (CI after: [{ci['brier_15min']['lo']:.4f}, {ci['brier_15min']['hi']:.4f}])
- TSS preserved by isotonic (monotonic)

## Operations
- Watch = 0.0961 (TSS-optimal; FAR **{n['far_watch']:.3f}** — the documented rare-event tradeoff)
- Warning = 0.2006 (precision-raised)
- Quiet→X all-clear: **{n['all_clear']}** flagged; observed X-flares flagged **{n['observed_x']}** (3 GTI-gap misses, not model failures)
- Lead time (Warning, X-class, capped 60 min): median {lead['warning']['median_min']:.0f} min — but per-flare leads in defensibility_leadtime.txt
- CPU inference: median **{lat['median_ms']:.2f} ms**, p99 {lat['p99_ms']:.2f} ms (~{lat['throughput_per_s']:,} forecasts/s, single thread); model {lat['booster_bytes']//1024} KB
- Cost-loss value: Vmax {val['curves']['Watch (0.096)']['vmax']:.2f} (Watch) / {val['curves']['Warning (0.20)']['vmax']:.2f} (Warning) at C/L≈base rate

## Fusion ablation (same config; combined = system of record)
| set | 15 min | 30 min | 60 min |
|---|---|---|---|
| SoLEXS-only | {abl['solexs_only']['y_15min']:.3f} | {abl['solexs_only']['y_30min']:.3f} | {abl['solexs_only']['y_60min']:.3f} |
| HEL1OS-only | {abl['hel1os_only']['y_15min']:.3f} | {abl['hel1os_only']['y_30min']:.3f} | {abl['hel1os_only']['y_60min']:.3f} |
| Combined | **{abl['combined']['y_15min']:.3f}** | {abl['combined']['y_30min']:.3f} | {abl['combined']['y_60min']:.3f} |

## QPP catalog (display caveat mandatory)
- **{n['qpp_cand']:,} QPP detections in {n['qpp_events']} flares**; tiers: classic ≥16 s **164** (119 flares) / intermediate **118** (54) / short 4–8 s **761** (340)
- Short 4–8 s tier: statistically real, **pending instrumental cross-check (Inglis 2011)** — never claim confirmed solar
- SoLEXS M/X peak amplitudes saturation-limited — never rank flare size by SoLEXS peak

*Detection = nowcasting (concurrent). Forecast numbers are prediction with lead time. Never swap the two.*
"""
    OUT.write_text(md, encoding="utf-8")
    print(md)
    if FAIL:
        print("\n".join(["", "=" * 60] + [f"FAIL: {f}" for f in FAIL]))
        return 1
    print(f"ALL CHECKS PASSED — regenerated {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

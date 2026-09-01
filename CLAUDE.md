# Aditya-L1 Solar Flare Forecasting & Nowcasting — PS-15 (ISRO BAH 2026)

Forecasts and nowcasts solar flares from Aditya-L1 SoLEXS (soft X-ray) +
HEL1OS (hard X-ray) L1 data. Four layers: detection (5 detectors + fusion),
master flare catalog + QPP catalog, leakage-safe 15/30/60-min probabilistic
forecasting (calibrated XGBoost), and a replay-driven operations dashboard.

## FROZEN-RESULTS RULE (read first)

The science is FROZEN. Do NOT retrain, re-detect, re-tune, or edit anything
under `src/detection/` or `src/forecasting/` in a way that changes results.
Headline numbers live in `data/processed/reports/*.{txt,json}` and are
mirrored in `dashboard_data/summary_metrics.json`:

- Detection: catalog-aware TSS **0.840** (per-bin 0.7456), fused event recall
  **0.872**, X-recall **43/43 (100%)**
- Forecast TSS (test): **0.346 / 0.229 / 0.205** (15/30/60 min); baselines:
  persistence 0.162, climatology 0.000; TFT honestly bested (0.235)
- Calibration 15-min: ECE **0.340 → 0.006**, Brier **0.194 → 0.070**
- Operating points: Watch 0.0961 (FAR 0.785 — documented rare-event tradeoff),
  Warning 0.2006; quiet→X all-clear **2/2**, observed X flagged **8/8**
- Master catalog **12,858** flares (40.2% confirmed / 26.1% sub-threshold /
  33.7% candidate-novel); QPP catalog **1,043 detections in 513 flares**
  (tiers 164 classic / 118 intermediate / 761 short)

NEVER hardcode fresh numbers into the dashboard or slides — read them from the
report sidecars (see `scripts/verify_numbers.py`, which fails loudly on drift).
The short 4–8 s QPP tier is ALWAYS labelled "pending instrumental cross-check
(Inglis 2011)" — never claimed as confirmed solar. SoLEXS peak amplitudes are
saturation-limited for M/X flares (`reports/SATURATION_NOTE.md`) — never rank
flare size by SoLEXS peak rate.

## Project map

```
app/                    FastAPI dashboard (serves PRE-COMPUTED JSON only)
  dashboard_server.py     no model code at runtime; in-memory JSON cache
  static/                 index.html + css/ + js/ (Plotly vendored in vendor/)
dashboard_data/         exported replay days, catalogs, wavelets, metrics
data/processed/         parquet artifacts + reports/ (result sidecars)
scripts/                numbered pipeline stages 01–20 + dashboard/ exports
  19_defensibility.py     bootstrap CIs, lead-times, ablation, value curves
  20_latency_benchmark.py CPU inference latency
  verify_numbers.py       number-drift guard → VERIFIED_NUMBERS.md
src/                    detection/ + forecasting/ library code (FROZEN)
```

## Running the dashboard

```
uvicorn app.dashboard_server:app --host 127.0.0.1 --port 8000
```
(or `run_dashboard.bat`). Fully offline: Plotly is vendored at
`app/static/vendor/plotly-2.35.2.min.js`; every API response is a
pre-computed file from `dashboard_data/`. To refresh exported data:
`python scripts/dashboard/export_dashboard_data.py` (+ `export_wavelets.py`).
Server caches JSON in memory — restart it after re-exporting.

## Gate workflow

Work proceeds in explicit gates: diagnose → fix → verify → STOP and report,
waiting for "proceed" unless told otherwise. Root-cause before fixing; minimal
diffs; never fabricate data or numbers; every claim verified by reading files
or running code. If a frozen result would change, STOP and ask. Commit per
completed gate with clear messages; never commit junk (`nul`, backups).

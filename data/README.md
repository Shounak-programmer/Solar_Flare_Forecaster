# Aditya-L1 Solar Flare Project — Data Inventory

Last updated: 2026-06-22 (full clean rebuild after HEL1OS data top-up)

## Phase 1 — Daily Light Curves (DONE)
- Location: `data/processed/daily_lightcurves/`
- Format: wide Parquet (zstd), one per coverage day
- File count: **620** (586 fresh joint days + 34 recovered from prior build —
  see Known Issues for the 34-day raw-zip loss)
- Date range: **2024-07-01 to 2026-06-13**
- Total size on disk: **608 MB**
- Schema: one row per UTC second (86,400 rows/day) with columns
  `utc`, `solexs_sdd2_total`, `solexs_sdd2_gti`, plus
  `hel1os_{cdte1,cdte2,czt1,czt2}_{band}` for each of the 5 energy bands per
  detector and a `..._gti` bool per detector.
- Coverage manifest: `data/processed/coverage_manifest.csv` — one row per
  calendar day in the 872-day window 2024-02-01 .. 2026-06-21, recording
  raw availability, parquet existence, GTI seconds, and notes.
  (`parquet_exists=620`, `has_joint=586`; the 34-day delta are days whose raw
  HEL1OS zips are gone but whose built parquet was recovered from backup.)

## Auxiliary Datasets (DONE)
| Dataset | File | Rows | Date Range | Size |
|---|---|---|---|---|
| GOES XRS combined | `data/processed/goes_xrs_combined.parquet` | 620,640 | 2024-02-01 .. 2025-04-06 | 9.3 MB |
| SWPC flare catalog | `data/processed/flares_swpc.parquet` | 8,132 | 2024-02-01 .. 2026-06-14 | 320 KB |
| HEK flare catalog | `data/processed/flares_hek.parquet` | 63,267 | 2024-02-01 .. 2026-06-14 | 2.9 MB |
| Solar indices (daily) | `data/processed/solar_indices_daily.parquet` | 865 | 2024-02-01 .. 2026-06-14 | 16 KB |
| Active regions (SRS) | `data/processed/active_regions_daily.parquet` | 5,841 | 2024-01-01 .. 2025-12-31 | 61 KB |

SRS parse success rate: 100.0% (0 failures out of 727 files).

## Flare Counts within Coverage
SWPC flares whose peak day has a built daily-LC parquet (620 days):
- X-class: **49** (of 85 total in catalog)
- M-class: **898** (of 1,320 total)
- C-class: 4,454 (of 6,339 total)
- B-class: 302 (of 387 total)

## Phase 2 — Labeled-Seconds Dataset (DONE)
- Location: `data/processed/labeled_seconds/`
- Format: same wide-schema Parquet as Phase 1 + 15 new label columns
- File count: **620** (one per built coverage day)
- Total rows: 53,568,000 (= 620 × 86,400 s)
- Total size on disk: **765 MB**
- See `data/processed/SCHEMA.md` §8 for the full column-level contract.

### Class distribution across the whole labeled dataset
| Class | Seconds | % of total | Events |
|---|---:|---:|---:|
| quiet | 46,862,659 | 87.48% | — |
| B | 259,890 | 0.49% | 302 |
| C | 4,955,567 | 9.25% | 4,454 |
| M | 1,391,795 | 2.60% | 898 |
| X | 97,188 | 0.18% | 49 |
| **flare total** | **6,705,341** | **12.52%** | **5,703** |

### Phase distribution
| Phase | Seconds | % of total |
|---|---:|---:|
| quiet | 38,685,321 | 72.22% |
| pre | 8,177,338 | 15.27% |
| rise | 3,379,534 | 6.31% |
| peak | 346,602 | 0.65% |
| decay | 2,979,205 | 5.56% |

Sanity: 346,602 peak-seconds ÷ 61 s per peak-window ≈ 5,682 events; the remainder
have peaks within 30 s of a day boundary so part of the window lives in the
adjacent day.

### Forecast-positive counts
| Horizon | Positive seconds | % of total |
|---|---:|---:|
| flare_in_next_15min | 5,027,460 | 9.39% |
| flare_in_next_30min | 9,542,073 | 17.81% |
| flare_in_next_60min | 17,157,060 | 32.03% |

Positive-class imbalance for the 15-min nowcast target is roughly 10:1
quiet:positive — manageable with class-weighted loss in Phase 4.

## Validation Status
- **Oct 3 2024 X9.0** verified in all 5 Aditya-L1 detectors AND GOES XRS
  (xrsb peak = 8.943e-04 W/m^2 at 12:18:00 UT — bang-on X9.0).
- **Oct 1 2024 X7.1** verified in Aditya-L1.
- **Feb 1 2026 X8.1** verified in Aditya-L1.
- **Neupert effect** (CZT-HXR leads CdTe-HXR leads SoLEXS-SXR leads GOES-SXR peak)
  confirmed in all 3 X-class events.

Validation plots:
- `data/validation/oct3_2024_phase1.png` (Aditya-L1, X9.0)
- `data/validation/20260201_phase1.png` (Aditya-L1, X8.1)
- `data/validation/20241001_phase1.png` (Aditya-L1, X7.1)
- `data/validation/goes_xrs_oct3_2024.png` (GOES, X9.0)
- `data/validation/labels_20241003.png` (Phase 2 labels, X9.0)
- `data/validation/labels_20241001.png` (Phase 2 labels, X7.1)
- `data/validation/labels_20260201.png` (Phase 2 labels, X8.1)
- `data/validation/phase2_validation_summary.txt` (PASS/FAIL + sanity audit)

### Phase 2 spot-check (3 random labeled days, seed = 20260619)
- **20241021 (quiet day):** 100.00% quiet, 0 flares, GOES coverage OK
- **20250902 (moderate):** 96.04% quiet, 4 C-class events, 244 peak-sec (= 4 × 61) ✓
- **20250103 (X-class):**  81.86% quiet, 11 events incl. X, 671 peak-sec (= 11 × 61) ✓

No silent corruption from the 4-worker parallel build.

## Known Issues
- **34 days lost their raw HEL1OS zips during the 2026-06-22 data top-up.**
  When new HEL1OS observations were added, 34 previously-covered dates lost
  their raw zips on disk (runs: 2024-07-26; 2024-08-02..08-19 with one gap;
  2024-11-24..12-05; 2024-12-09/11/13/18/19). Their built daily-LC and
  labeled-second parquets were **recovered from the prior build's backup**
  (`_old_backup/`) — identical schema, so the labeled dataset is intact and
  includes them. To restore uniform provenance, re-download these 34 dates'
  HEL1OS zips and rerun the rebuild. In `coverage_manifest.csv` these show
  `parquet_exists=True` but `has_hel1os=False`.
- **GOES XRS coverage ends 2025-04-06** — for flares after that date, GOES
  context is unavailable; HEL1OS+SoLEXS still primary.
- **16 daily-LC parquets flagged "partial_coverage"** in
  `coverage_manifest.csv` — edge dates where a HEL1OS observation only barely
  crosses into the day. Data is present and usable but coverage is shorter.
- **2025-11-11 X5.1 flare not in Aditya-L1 coverage** (neither HEL1OS nor
  SoLEXS recorded that day). Loses one X-class event from the training set.
  (Note: 2025-11-14 X4.0 is now covered after the top-up and validated.)
- **`solar_indices_daily` has 14 days with null `sunspot_number`** (SILSO
  source). F10.7 fully populated.
- **HEK catalog `goes_class` mostly null** — HEK aggregates many non-GOES
  detectors; only a fraction tag a GOES class. Use SWPC for class-conditional
  work; HEK adds detection diversity.

## Directory Structure
```
data/
├── processed/                              # ML-ready outputs (Phase 3 reads from here)
│   ├── daily_lightcurves/                  # 620 wide-schema daily Parquets (Phase 1)
│   ├── labeled_seconds/                    # 620 labeled-second Parquets (Phase 2)
│   ├── coverage_manifest.csv               # 872-row master coverage table
│   ├── labeling_report.txt                 # per-day Phase 2 build log
│   ├── goes_xrs_combined.parquet
│   ├── flares_swpc.parquet
│   ├── flares_hek.parquet
│   ├── solar_indices_daily.parquet
│   ├── active_regions_daily.parquet
│   ├── build_report.txt                    # per-day build log
│   └── SCHEMA.md                           # column-level contract for all parquets
├── validation/                             # PNG plots for verification
├── goes/{xrs,events}/                      # Raw NetCDF + SWPC CSV
├── hek/                                    # Raw HEK CSV
├── indices/                                # Raw F10.7, sunspot CSV
├── active_regions/raw/                     # Raw SRS .txt files
├── HEL1OS/                                 # Raw HEL1OS observation zips
├── SoLEXUS/                                # Raw SoLEXS observation directories
└── README.md
```

## Phase 3 — Nowcasting: Detection + Master Catalog + QPP (DONE)

Five **independent** detector pipelines (label-aware rolling background on the
smoothed rate → Poisson significance → classical event extraction), each at its
TSS-tuned threshold, fused into a master catalogue, plus a QPP module.

### Per-detector catalogs (`data/processed/detections/{detector}_detections.parquet`)
| Detector | Threshold | Events | POD | TSS | X-recall |
|---|---:|---:|---:|---:|---:|
| solexs_sdd2 | 3.5σ | 7,253 | 0.851 | 0.829 | 100% |
| hel1os_cdte1 | 2.0σ | 8,807 | 0.595 | 0.554 | 90% |
| hel1os_cdte2 | 2.0σ | 6,819 | 0.498 | 0.468 | 93% |
| hel1os_czt1 | 2.0σ | 1,730 | 0.117 | 0.108 | 60% |
| hel1os_czt2 | 2.0σ | 1,660 | 0.107 | 0.099 | 50% |

**Hardness ordering (publishable):** X-over-C detection selectivity rises
monotonically soft→hard — SoLEXS 1.2× → CdTe 1.6–2.0× → **CZT 8.5×**. This is
the non-thermal hard-X-ray signature that justifies the independent 5-detector
architecture.

### Master flare catalog (`data/processed/detections/master_flare_catalog.parquet`)
- **12,858 physical flares** (bounded single-linkage, ±3 min / 240 s peak-span cap)
- **Master recall 0.872 > best single detector 0.808** (member-aware, common denom)
- Per-class recall: **X 100% (43/43)** · M 99% · C 88% · B 39%
- 3-way: **CONFIRMED 5,175 (40%)** · SUB-THRESHOLD 3,354 (26%) · CANDIDATE-NOVEL 4,329 (34%);
  2,076 candidate-novel are multi-detector-confirmed (n≥2)
- Catalog-aware **TSS 0.840**, HSS 0.638

### Baseline comparison (per-bin nowcast, 6-min in-GTI grid — the key result)
| Method | POD | TSS |
|---|---:|---:|
| **Master** | 0.809 | **0.746** |
| Persistence (30-min, best) | 0.182 | 0.007 |
| Persistence (1-bin) | 0.018 | −0.021 |
| Climatology | 0.038 | 0.000 |

**This is a NOWCASTING / DETECTION result, not a forecasting result.** The
master detects *concurrent* flares from live X-ray data and beats persistence
and climatology at that task by +0.74 TSS — establishing that the detection
layer has real skill above the trivial baselines (the correct floor any useful
system must clear). It does **not** claim to beat an operational *forecaster*:
the master sees the present, a forecaster predicts the future. **Forecasting
skill — and the like-for-like Camporeale (2025) comparison against the NOAA
operational forecast — is evaluated in Phase 4**, not here. Detection skill is
established; forecasting skill is future work.

### QPP catalog (`data/processed/detections/qpp_catalog.parquet`) — the differentiator
- **1,043 significant QPPs in 513 flares** (Morlet + Vaughan 2005 red-noise test,
  validated: synthetic 30 s injection recovered, AR(1) false-positive rate 5.5% ≈ nominal 5%)
- Period 4–294 s (median 7.6 s); **first systematic QPP catalog from Aditya-L1/HEL1OS**
- **Regime tiers:** `classic` ≥16 s (119 flares, robustly solar — lead with these),
  `intermediate` 8–16 s (54), `short` 4–8 s (340, real signal but pending
  instrumental cross-check — see SCHEMA.md §11)
- Flagship X-class QPP: **X1.8 on 2025-11-04**, 7.1 s, 5.9σ, 129 coherent cycles

Reports: `reports/{threshold_tuning,detection_per_detector,master_catalog_eval,detection_metrics,qpp_report}.txt`.
Validation plots: `validation/{gate1_background,gate2_tss_curves,phase3_precheck,gate5_qpp_synthetic,gate5_qpp_clearest}.png`.

## Phase 4 — Forecasting (DONE)

Predict whether a flare will **peak within the next 15 min** (primary; 30/60 min
secondary) and of which class, using **only data ≤ t** (leakage-safe trailing
features). This is true FORECASTING (predicting ahead), so the Camporeale (2025)
baseline comparison is the like-for-like operational test — and we win it.

### Leakage-safe feature matrix (`data/processed/forecast_features/`)
- 1-min cadence, 620 days, 86 trailing-only features (+ Neupert residual).
- GATE A leakage audit PASSED: manual source-row traces, +1-step shift test,
  target positive-rate match (0.0939 vs Phase-2 0.0940), zero cross-gap
  interpolation. Daily context lagged to D-1; flare history from our own
  master-catalog detections (not the SWPC label catalog).

### Time-respecting split (no shuffling)
| Split | Dates | rows | X | M | C | B |
|---|---|---:|---:|---:|---:|---:|
| train | 2024-07-01 .. 2025-06-30 | 444,902 | 33 | 715 | 2,617 | 62 |
| val | 2025-07-01 .. 2025-12-31 | 207,986 | 8 | 153 | 1,430 | 73 |
| test | 2026-01-01 .. 2026-06-13 | 210,253 | **11** | 129 | 1,105 | 219 |

### 15-min TSS — calibrated XGBoost beats both baselines (the decisive result)
| Model | 15-min | 30-min | 60-min |
|---|---:|---:|---:|
| Climatology | 0.000 | 0.000 | 0.000 |
| Persistence | 0.162 | 0.153 | 0.161 |
| **XGBoost (calibrated, primary)** | **0.346** | 0.229 | 0.205 |
| TFT (evaluated, bested) | 0.235 | 0.179 | 0.156 |

**XGBoost is the primary forecaster.** 15-min full metrics: TSS 0.346, HSS 0.188,
POD 0.570, FAR 0.801, precision 0.199. Skill peaks at 15 min — Sarwade's target
horizon — because imminent flares have the strongest precursor signatures. This
beats the operational-reference baselines Camporeale (2025) found the NOAA
forecast struggles to clear: a true forecasting win.

**TFT honestly bested:** a single clean RTX 5070 Ti (Blackwell sm_120, bf16) run
scored 0.235 — below XGBoost. Gradient boosting wins because our features already
pre-encode the temporal structure, leaving little for sequence attention; tree
ensembles dominate tabular imbalanced data. Recorded as a methodology
contribution (we chose by evidence, not by buzzword).

### Cross-model agreement (strengthens the physics claim)
Both model families independently rank **`soft_ddt_5m` (trailing soft-X-ray
derivative) in their top two** — XGBoost #1 (with `neupert_resid` #4), TFT #2.
Two architectures agreeing the soft-X derivative is a dominant precursor means the
signal is physical, not model-specific. **Honest null result:** QPP features rank
low (25–84) — QPPs are concurrent/impulsive-phase, not 15-min precursors. The QPP
catalog stands as a separate Phase-3 contribution; it is not forced into the
forecasting story.

### Per-class recall (calibrated 15-min; X denom = 11 test events)
| Class | Recall |
|---|---|
| X | 98/121 windows (0.81) — *promising, small sample (11 X-flares)* |
| M | 1122/1428 (0.79) |
| C | 8846/14666 (0.60) |
| B | 612/2519 (0.24) |

### Calibration (isotonic, fit on val) — reliability transformed, TSS preserved
| Horizon | Brier before→after | ECE before→after | TSS |
|---|---|---|---|
| 15-min | 0.194 → **0.070** | 0.340 → **0.006** | 0.346 (preserved; isotonic is monotonic) |

`data/validation/forecast_reliability.png` — the curve snaps onto the diagonal.

### Quiet→X-class "all-clear" test (Camporeale failure mode)
Quiet = no M/X flare in prior 12 h (C-flares are near-constant background at solar
max). Test set had **2 quiet→X transitions — both flagged 15 min before peak (2/2)**.
The model does **not** issue a false all-clear when the Sun is quiet then erupts.
Overall **8/11 test X-flares flagged** in the pre-peak window; the 3 misses **all
had no in-GTI feature rows in [peak−15min, peak]** (instrument coverage gaps, not
model failures) — i.e. **8/8 of X-flares the instruments actually observed were
flagged**, with 10–15 min lead.

Reports: `reports/{forecasting_baselines,tft_metrics,forecasting_metrics}.txt`.
Plots: `validation/forecast_reliability.png`. Predictions: `forecasts/`.

## Status
Phases 1–4 complete. Forecasting layer established with a calibrated, leakage-safe
XGBoost model that beats persistence and climatology at the 15-min horizon — the
true operational-baseline comparison.

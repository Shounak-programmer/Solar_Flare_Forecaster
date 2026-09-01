# Processed Parquet Schemas — Phase 1 Contract

**All timestamps are UTC unless explicitly noted.** Phase 2 must read from
these files only; any change here is a breaking-contract change.

Generated 2026-06-18 from `scripts/01_build_daily_lightcurves.py` and
`scripts/05_standardize_auxiliary.py`.

---

## 1. `daily_lightcurves/{YYYYMMDD}.parquet`

**Purpose:** one file per joint-coverage day; 1 Hz unified light curves from
all five Aditya-L1 detectors, on a common UTC grid, with per-detector GTI
masks.

> **Note on SoLEXS SDD1:** intentionally absent — see
> [`SDD1_VERDICT.md`](SDD1_VERDICT.md). The L1 pipeline emits empty
> `.gti.gz` placeholders for SDD1 in every observation (741/741 confirmed);
> no light curves or spectra are produced for that detector.

**Sort:** `utc` ascending. **Rows:** exactly 86,400 (one per UTC second).

| Column | Type | Unit / Description |
|---|---|---|
| `utc` | datetime64[ns, UTC] | UTC timestamp at the start of each 1-second bin |
| `solexs_sdd2_total` | float64 | SoLEXS SDD2 total counts/sec |
| `solexs_sdd2_gti` | bool | True if this second is inside a SoLEXS GTI |
| `hel1os_cdte1_5_20kev`    | float64 | HEL1OS CdTe1 5–20 keV  cts/sec |
| `hel1os_cdte1_20_30kev`   | float64 | HEL1OS CdTe1 20–30 keV cts/sec |
| `hel1os_cdte1_30_40kev`   | float64 | HEL1OS CdTe1 30–40 keV cts/sec |
| `hel1os_cdte1_40_60kev`   | float64 | HEL1OS CdTe1 40–60 keV cts/sec |
| `hel1os_cdte1_1p8_90kev`  | float64 | HEL1OS CdTe1 1.8–90 keV cts/sec (wideband) |
| `hel1os_cdte1_gti` | bool | True if this second is inside CdTe1 GTI |
| `hel1os_cdte2_*`   | float64 / bool | same 5 bands + gti for CdTe2 |
| `hel1os_czt1_20_40kev`    | float64 | HEL1OS CZT1 20–40 keV cts/sec |
| `hel1os_czt1_40_60kev`    | float64 | HEL1OS CZT1 40–60 keV cts/sec |
| `hel1os_czt1_60_80kev`    | float64 | HEL1OS CZT1 60–80 keV cts/sec |
| `hel1os_czt1_80_150kev`   | float64 | HEL1OS CZT1 80–150 keV cts/sec |
| `hel1os_czt1_18_160kev`   | float64 | HEL1OS CZT1 18–160 keV cts/sec (wideband) |
| `hel1os_czt1_gti` | bool | True if this second is inside CZT1 GTI |
| `hel1os_czt2_*`   | float64 / bool | same 5 bands + gti for CZT2 |

**Missing-value convention:** NaN in any rate column = no instrument sample at
that second; pair with the matching `..._gti` bool to distinguish
"in-GTI but no count yet" vs "outside-GTI gap". Total columns: 26.

**Helper:** `src/data/schema.to_tidy(df_wide)` reshapes this wide schema into
the long form (`utc, detector, band, count_rate, in_gti`) for groupby/plot
code that prefers it.

---

## 2. `coverage_manifest.csv`

**Purpose:** single source of truth for what raw data exists and what was
built, day-by-day across the joint coverage window.

**Sort:** `date` ascending. **Rows:** 872 (one per calendar day 2024-02-01 .. 2026-06-21).

| Column | Type | Description |
|---|---|---|
| `date` | date (YYYY-MM-DD) | UTC calendar date |
| `has_solexs` | bool | SoLEXS daily observation exists on disk |
| `has_hel1os` | bool | At least one HEL1OS observation overlaps this day |
| `has_joint` | bool | `has_solexs AND has_hel1os` |
| `parquet_exists` | bool | daily_lightcurves/{date}.parquet was built |
| `n_rows` | int | rows in the parquet (86,400 if built, else 0) |
| `n_detectors_present` | int 0–5 | detectors with ≥1 in-GTI non-NaN sample |
| `solexs_gti_seconds` | int | total True-seconds in `solexs_sdd2_gti` |
| `hel1os_total_gti_seconds` | int | sum of True-seconds across all 4 HEL1OS `_gti` columns |
| `notes` | str | e.g. `""`, `"solexs_only"`, `"hel1os_only"`, `"no_raw_data"`, `"partial_coverage_NofM_detectors"`, `"build_missing"`, `"read_failed:..."` |

---

## 3. `goes_xrs_combined.parquet`

**Purpose:** GOES-R XRS 1-min flux for the SXR context channel that defines
the GOES flare class (B/C/M/X letter from `xrsb_flux`).

**Sort:** `utc` ascending. **Grid:** uniform 1 minute, gaps left as NaN.

| Column | Type | Unit / Description |
|---|---|---|
| `utc` | datetime64[ns, UTC] | minute timestamp |
| `xrsa_flux` | float64 | 0.5–4 Å (short) flux, W/m² |
| `xrsb_flux` | float64 | 1–8 Å (long) flux, W/m² — flare-class channel |
| `satellite` | category | e.g. `"GOES-16"` |

Coverage: **2024-02-01 .. 2025-04-06.** Days outside this window have no
GOES context — use Aditya-L1 alone or impute.

---

## 4. `flares_swpc.parquet`

**Purpose:** authoritative SWPC GOES-flare catalog (B/C/M/X labels with
explicit class strings and AR numbers).

**Sort:** `peak_utc` ascending. **Rows:** 8,132.

| Column | Type | Unit / Description |
|---|---|---|
| `start_utc` | datetime64[ns, UTC] | flare start |
| `peak_utc`  | datetime64[ns, UTC] | flare peak (SXR) |
| `end_utc`   | datetime64[ns, UTC] | flare end |
| `goes_class` | str | full class string e.g. `"M3.2"` |
| `goes_class_letter` | str | one of `B`/`C`/`M`/`X` (one row in catalog is null/malformed) |
| `goes_class_magnitude` | float64 | numeric part, e.g. M3.2 → 3.2 |
| `peak_flux` | float64 | peak xrsb flux (W/m²) — often NaN in source |
| `noaa_ar` | Int64 | NOAA active-region number, nullable |
| `lon` | float64 | heliographic longitude (degrees) |
| `lat` | float64 | heliographic latitude (degrees) |
| `duration_seconds` | Int64 | `end_utc - start_utc` in seconds |

---

## 5. `flares_hek.parquet`

**Purpose:** the wider HEK flare catalog (multi-detector, multi-FRM). Use as
detection-diversity supplement to `flares_swpc`.

**Sort:** `peak_utc` ascending. **Rows:** 63,267.

| Column | Type | Unit / Description |
|---|---|---|
| `start_utc`, `peak_utc`, `end_utc` | datetime64[ns, UTC] | as in SWPC |
| `goes_class` | str | GOES class if reported (mostly null in HEK) |
| `goes_class_letter` | str | derived; mostly null |
| `goes_class_magnitude` | float64 | derived; mostly null |
| `peak_flux` | float64 | reporter's own peak flux value (units depend on FRM) |
| `noaa_ar` | Int64 | NOAA AR number, nullable |
| `lon`, `lat` | float64 | reporter's heliographic coords |
| `duration_seconds` | Int64 | `end_utc - start_utc` in seconds |

**Caveat:** `peak_flux` units differ by FRM and are not GOES W/m². Treat
HEK as a detection list, not a flux source.

---

## 6. `solar_indices_daily.parquet`

**Purpose:** daily solar activity context covariates (F10.7, sunspot number).

**Sort:** `date` ascending. **Rows:** 865.

| Column | Type | Unit / Description |
|---|---|---|
| `date` | date (YYYY-MM-DD) | UTC calendar date |
| `f107_observed` | float64 | 10.7-cm flux, observed, SFU (10⁻²² W m⁻² Hz⁻¹) |
| `f107_adjusted` | float64 | F10.7, 1-AU-adjusted, SFU |
| `sunspot_number` | Int64 | SILSO international daily sunspot number (14 days null) |
| `sunspot_std` | float64 | SILSO daily standard deviation |

---

## 7. `active_regions_daily.parquet`

**Purpose:** parsed NOAA SRS active-region catalog, Section I (spotted regions).

**Sort:** `(date, noaa_ar)` ascending. **Rows:** 5,841 (727 days, ~8 ARs/day mean).

| Column | Type | Unit / Description |
|---|---|---|
| `date` | date (YYYY-MM-DD) | report date (data valid as of `date - 0000Z`) |
| `noaa_ar` | Int64 | NOAA active-region number |
| `location_str` | str | e.g. `"S20W77"` — heliographic letter form |
| `lat_hg` | float64 | heliographic latitude (N positive, S negative) |
| `lon_hg` | float64 | heliographic longitude (W positive, E negative) |
| `area_millionths` | Int64 | sunspot group area in millionths of the solar hemisphere |
| `z_class` | str | Modified Zürich (McIntosh) class, e.g. `"Hsx"`, `"Dao"` |
| `num_spots` | Int64 | number of spots in the group |
| `mag_class` | str | Mount Wilson magnetic class, e.g. `"Alpha"`, `"Beta-Gamma-Delta"` |

---

## 8. `labeled_seconds/{YYYYMMDD}.parquet`

**Purpose:** Phase 2 supervision dataset. One file per joint-coverage day,
identical 1 Hz UTC grid to `daily_lightcurves/{YYYYMMDD}.parquet`, with all
Phase-1 columns kept verbatim plus 15 new label columns. Phase 3 (per-detector
detection) and Phase 4 (forecasting) train on these files.

**Sort:** `utc` ascending. **Rows:** 86,400 per day. **Files:** 620 (one per built coverage day).

All Phase-1 columns (utc, per-detector rate/gti) are passed through unchanged
— see Section 1.

### New label columns

| Column | Type | Description |
|---|---|---|
| `is_flare` | int8 (0/1) | 1 if this UTC second falls inside any SWPC flare's `[start_utc, end_utc]` (both inclusive) |
| `flare_id` | Int64 (nullable) | Index of the SWPC flare row from `flares_swpc.parquet` that owns this second; `NA` outside any flare. On overlap, the higher-class flare's id wins. |
| `flare_class_letter` | category[B,C,M,X] (nullable) | GOES letter of the owning flare; `NA` outside any flare |
| `flare_class_magnitude` | float64 | Numeric part of the class (e.g. M3.2 → 3.2); `NaN` outside any flare |
| `flare_phase` | category[quiet,pre,rise,peak,decay] | See semantics below |
| `time_to_next_peak_sec` | Int64 (nullable) | Seconds until the next flare peak from this second; `NA` if no peak in the next 6 hours |
| `time_since_last_peak_sec` | Int64 (nullable) | Seconds since the most recent flare peak ≤ this second; `NA` if no peak in the last 6 hours |
| `flare_in_next_15min` | int8 (0/1) | 1 iff any flare peaks in `(t, t + 15 min]` |
| `flare_in_next_30min` | int8 (0/1) | 1 iff any flare peaks in `(t, t + 30 min]` |
| `flare_in_next_60min` | int8 (0/1) | 1 iff any flare peaks in `(t, t + 60 min]` |
| `max_class_in_next_30min` | category[B,C,M,X] (nullable) | Highest class peaking in `(t, t + 30 min]`; `NA` if none |
| `active_ar_count` | Int64 (nullable) | Number of NOAA SRS active regions reported for this day (from `active_regions_daily.parquet`); broadcast to all 86,400 rows |
| `f107_observed` | float64 | Observed F10.7 daily flux (SFU); broadcast |
| `sunspot_number` | Int64 (nullable) | SILSO daily sunspot number; broadcast |
| `goes_xrsb_flux` | float64 | GOES XRS-B 1-min flux broadcast to 1 Hz (minute `m`'s value is held for seconds `[m*60, m*60+60)`). `NaN` outside GOES coverage (i.e. after 2025-04-06) or within a 1-min gap. |

### `flare_phase` semantics

- `quiet` (default) — not in any flare and not within 30 min before any flare start
- `pre` — `[start_utc − 30 min, start_utc)` AND not currently in any other flare
- `rise` — `[start_utc, peak_utc)`
- `peak` — `[peak_utc − 30 s, peak_utc + 30 s]` (61 contiguous seconds per peak)
- `decay` — `(peak_utc, end_utc]`

Phase precedence on overlap: `peak > rise/decay > pre > quiet`. Implementation
writes layers in this order, so the highest-priority active flare's phase ends
up on top.

### `flare_class_letter` precedence on multi-flare overlap

Class rank: `X (4) > M (3) > C (2) > B (1)`. When a second falls in two flares,
the higher-rank flare's `flare_id`, `flare_class_letter`, and
`flare_class_magnitude` are recorded. Ties broken by larger magnitude.
`is_flare` is always 1 if any flare overlaps.

### Cross-day buffer for forecast labels

For each day's labels, the SWPC catalog is filtered to
`peak_utc ∈ [day_start − 6 h, day_start + 30 h]` so that:
- a flare starting in the previous day still drives `is_flare`/`rise`/`peak` here
- a flare peaking in the next day still drives `flare_in_next_*` and
  `time_to_next_peak_sec` here
- a peak in the previous day still drives `time_since_last_peak_sec` here

The 6 h window matches the cap on `time_to_next_peak_sec` and
`time_since_last_peak_sec`; values beyond 6 h are `NA`.

### Null conventions

`NA` (pandas `pd.NA` / `Int64`/`Categorical`) is used for "no observation" /
"no applicable flare". `NaN` is used for float columns where the value
genuinely doesn't exist (no flare → no `flare_class_magnitude`; no GOES
coverage → no `goes_xrsb_flux`). The two are interchangeable for downstream
masking; both serialize cleanly via zstd Parquet.

---

## 9. `detections/{detector}_detections.parquet` (Phase 3, 5 files)

**Purpose:** independent single-detector flare catalogue, one file per detector
(`solexs_sdd2`, `hel1os_cdte1`, `hel1os_cdte2`, `hel1os_czt1`, `hel1os_czt2`),
each detected at its TSS-tuned threshold (`reports/chosen_thresholds.json`:
solexs 3.5σ, cdte1/cdte2/czt1/czt2 2.0σ). One row per detected flare event.

**Sort:** `peak_utc` ascending within each file.

| Column | Type | Unit / Description |
|---|---|---|
| `detector` | str | detector name |
| `date` | str | YYYYMMDD of the source day file |
| `start_idx` / `peak_idx` / `end_idx` | int | second-of-day indices (debug) |
| `start_utc` / `peak_utc` / `end_utc` | datetime64[ns,UTC] | event start / peak / end |
| `duration_s` | int | `end - start` seconds |
| `peak_rate` | float64 | peak count rate, cts/s |
| `preflare_bg` | float64 | median quiet rate in the 30-min pre-start window, cts/s |
| `peak_bgsub` | float64 | `peak_rate - preflare_bg` (can be negative on a decay tail) |
| `max_significance` | float64 | peak excess over background, in σ |
| `rise_time_s` | int | `peak - start` seconds (Neupert proxy denominator) |
| `max_derivative` | float64 | max d/dt of the smoothed rate on the rise (Neupert proxy) |

Detection is **label-free** at inference (background uses the smoothed-rate
estimator, never `is_flare`), so the catalogues can be matched to SWPC without
circularity. Background is the rolling median of the *smoothed* rate (Option A)
so low-count CZT does not collapse to a zero background.

> ⚠️ **SoLEXS saturation caveat** (`solexs_sdd2` catalog only): `peak_rate`,
> `peak_bgsub`, and `max_significance` are **underestimated for M/X-class peaks**.
> The SoLEXS L1 light curve is the spectral (slow) chain, uncorrected; it
> saturates paralyzably (deadtime 13.65 µs, observable ceiling ≈ 26,951 cts/s,
> per Sarwade et al. 2025) and can **invert the ordering** of peaks for the
> largest flares (e.g. the X9.0's SoLEXS peak is *below* the X8.1/X7.1).
> **Rise-phase values are unaffected** — and detection triggers on the rise, so
> recall is intact. Do not use the SoLEXS peak as a flare-magnitude proxy. HEL1OS
> CdTe/CZT have headroom (not pinned). See `reports/SATURATION_NOTE.md`.

---

## 10. `detections/master_flare_catalog.parquet` (Phase 3)

**Purpose:** fused multi-detector master catalogue — connected physical flares
from the 5 single-detector catalogues. Bounded single-linkage: detections link
if peaks are within ±3 min (Neupert window) AND the cluster peak-span stays
≤ 240s (anti-over-merge; prevents A-B-C chaining of distinct flares).

**Sort:** `master_peak_utc` ascending. **Rows:** 12,858.

| Column | Type | Unit / Description |
|---|---|---|
| `master_peak_utc` / `_start_utc` / `_end_utc` | datetime64[ns,UTC] | median member peak / earliest start / latest end |
| `master_peak_unix` / `_start_unix` / `_end_unix` | int64 | same, unix seconds |
| `n_detectors` | int | distinct detectors contributing (1–5) |
| `n_members` | int | total member detections |
| `detectors` | str | comma-joined detector names |
| `member_peaks_unix` | list[int64] | member peak times — **use these for member-aware matching** (immune to median-peak drift from the Neupert offset) |
| `max_significance` | float64 | max member σ |
| `peak_rate_max` | float64 | max member peak rate, cts/s |
| `confidence` | float64 | `(n_detectors/5) × geomean(per-detector max σ)` — higher = more detectors + stronger |

**Matching rule:** a master flare matches a catalogue flare if ANY
`member_peaks_unix` is within ±3 min. `master_peak_utc` is a display attribute
only (the median can drift off the soft-X peak when a hard-X CZT member leads).

> ⚠️ **SoLEXS saturation caveat:** `peak_rate_max` and `confidence` are mildly
> depressed for M/X flares **when SoLEXS-SDD2 is the peak member** (its peak
> saturates at ≈ 26,951 cts/s; `confidence` includes SoLEXS's capped
> significance in its geomean). HEL1OS members are far from their own ceilings,
> so fusion ranking is robust; don't use `peak_rate_max` to size M/X flares.
> See `reports/SATURATION_NOTE.md`.

---

## 11. `detections/qpp_catalog.parquet` (Phase 3)

**Purpose:** quasi-periodic pulsations detected in HEL1OS CZT hard X-ray over
each flare's `[start, peak]` impulsive window. Morlet wavelet + Vaughan (2005)
red-noise significance (power-law + white-floor continuum via Whittle
likelihood; validated by synthetic injection + a calibrated 5.5% false-positive
rate on AR(1) red noise). One row per significant (95% global) QPP.

**Sort:** by source flare. **Rows:** 1,043 QPPs in 513 distinct flares.

| Column | Type | Unit / Description |
|---|---|---|
| `master_peak_utc` | datetime64[ns,UTC] | source master flare peak |
| `flare_start_utc` | datetime64[ns,UTC] | impulsive-window start |
| `detector` | str | `hel1os_czt1` or `hel1os_czt2` |
| `period_s` | float64 | QPP period, seconds (search band 4–300 s) |
| `time_s_into_rise` | float64 | time of peak wavelet power, s from window start |
| `significance_sigma` | float64 | global significance, equivalent Gaussian σ |
| `global_p` | float64 | Vaughan global p-value |
| `n_cycles` | float64 | cycles of this period spanned by the window |
| `n_detectors` | int | n_detectors of the source master flare |
| `peak_rate_max` | float64 | source flare peak rate |
| `goes_class` | str (nullable) | GOES class of the source flare (None if non-SWPC) |
| `regime` | category | **tier** — `classic` (≥16 s, robustly solar), `intermediate` (8–16 s), `short` (4–8 s) |

**Regime tiers (see GATE 5):** lead scientific claims with `classic` (and the
X-class examples) — these sit in the established solar-QPP band and are immune
to the 1 s cadence limit. The `short` (4–8 s) tier is **statistically real**
(median 59 coherent cycles, distinct from red-noise false positives) but is
**pending cross-check against HEL1OS instrumental periodicities** (telemetry /
readout / spin) before solar attribution — it is near the 2 s Nyquist period
of the 1 s-binned light curves.

---

## 12. `forecast_features/{YYYYMMDD}.parquet` (Phase 4)

**Purpose:** leakage-safe forecasting feature matrix, 1-min cadence, 1,440 rows
per day, 93 columns (86 trailing features + targets + metadata). **Every feature
uses only data ≤ t** (trailing windows; GATE A audited). Not git-tracked (337 MB;
regenerate with `scripts/14_build_forecast_features.py`).

**Sort:** `utc` ascending per day. Leakage-safety conventions:
- Daily context (`f107_lag1`, `sunspot_number_lag1`, `ar_count_lag1`) is lagged to
  day **D-1** — provably no same-day/future value.
- Flare-history features (`time_since_last_det_s`, `det_rate_1h/3h/6h`,
  `last_det_*`) come from our **master-catalog detections**, not the SWPC label
  catalogue (which is not available at real inference time).
- GTI gaps → NaN (rolling `min_periods`; no interpolation across gaps).
- The SWPC-derived `time_since_last_peak_sec` and the future `time_to_next_peak_sec`
  from labeled_seconds are **excluded** as features (label leakage / future).

| Column group | Examples | Notes |
|---|---|---|
| metadata | `utc`, `day`, `in_gti_any` | forecast only where ≥1 detector observing |
| physics precursors | `soft_ddt_5m/15m/30m`, `hardness_ratio`, `hardness_ddt_15m`, `hel1os_hard_rate`, `hel1os_hard_bgsub` | trailing soft-X derivative, hardness, trailing-background-subtracted hard rate |
| QPP | `qpp_present_60m`, `qpp_count_60m`, `qpp_count_{classic,intermediate,short}_60m` | QPPs with master peak ≤ t |
| activity (lagged D-1) | `f107_lag1`, `sunspot_number_lag1`, `ar_count_lag1` | static-style daily context |
| flare history (detections) | `time_since_last_det_s`, `last_det_peak_rate`, `last_det_n_detectors`, `det_rate_1h/3h/6h` | from master catalog, peaks ≤ t |
| per-detector trailing stats | `{det}_mean/std/max_{5m,15m,30m,60m}`, `{det}_xcross_60m` | 5 detectors × {mean,std,max} × 4 windows + hourly threshold-crossings |
| **targets** (aligned, not recomputed) | `y_15min`, `y_30min`, `y_60min`, `y_class30` | from labeled_seconds `flare_in_next_*` / `max_class_in_next_30min` |

`neupert_resid` (= hard_rate − k·soft_ddt) is formed at model time with **k fit on
TRAIN only** (leakage-safe), not stored per-day.

> ⚠️ **SoLEXS saturation caveat:** features built on the SoLEXS *peak* —
> `solexs_*_max_*`, `hardness_ratio`, `neupert_resid` — are distorted **at the
> peak of M/X flares** (the saturated soft denominator makes `hardness_ratio`
> over-estimated; `solexs_*_max_*` are capped near 26,951 cts/s). **Rise-phase
> values are unaffected**, and the dominant predictor `soft_ddt_5m` is computed
> on the rise — so forecasting skill (15-min TSS 0.346) is not compromised. The
> HEL1OS hard-X numerator has headroom (not "doubly distorted"). See
> `reports/SATURATION_NOTE.md`.

---

## 13. `forecasts/*.npz` (Phase 4 predictions)

Saved test/val predictions (not git-tracked; regenerate via scripts 16/17/18):
- `baseline_test_predictions.npz` — XGBoost/LR test+val probabilities per horizon.
- `tft_test_predictions.npz` — TFT test/val probabilities + MC-dropout std.
- `calibrated_test_predictions.npz` — isotonic-calibrated 15-min test probabilities
  (`p15_cal`, `p15_uncal`, `y15`, `thr15`, `utc_unix`).

Primary model = **calibrated XGBoost** (15-min TSS 0.346). Thresholds tuned on
validation, evaluated on test. See `reports/forecasting_metrics.txt`.

---

## Cross-file join conventions for Phase 2

- **Time joins** to a daily_lightcurves file: floor the LC `utc` to minute
  to align with `goes_xrs_combined`; floor to day for `solar_indices_daily`
  and `active_regions_daily`.
- **Flare → LC label join:** for each row in `flares_swpc`, the labeled-second
  window is `[start_utc, end_utc]` (inclusive) restricted to the day's LC.
  Pre-flare precursor windows: `[peak_utc - 30min, peak_utc - 5min]`.
- **Active-region context:** an SRS row is valid for the day it was *reported*
  on (`date`) — i.e. valid for `[date 00:00Z, date+1 00:00Z)`. Multiple ARs
  per day are normal; aggregate to per-day features by sum/max as needed.

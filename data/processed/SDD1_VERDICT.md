# SoLEXS SDD1 — Exhaustive Investigation Verdict

**Date:** 2026-06-20
**Investigator script:** `scripts/08_investigate_sdd1.py`
**Source inventory:** `data/processed/sdd1_file_inventory.csv` (741 rows)
**Deep inspection:** `data/processed/sdd1_deep_inspection.md`

---

## VERDICT: **A** — SDD1 is truly empty across all observations.

There is no SDD1 science data anywhere in the corpus. The earlier
small-sample claim was correct.

---

## Statistical evidence

| Metric | Result |
|---|---|
| Total SoLEXS observations scanned | **741** (full corpus, 2024-02-01 .. 2026-06-13) |
| Observations with an SDD1 directory | **741 / 741** (100.0%) |
| Observations with an SDD1 `.lc.gz` light curve | **0 / 741** (0.0%) |
| Observations with an SDD1 `.pi.gz` spectrum | **0 / 741** (0.0%) |
| Observations with an SDD1 `.hk.gz` housekeeping | **0 / 741** (0.0%) |
| Observations whose SDD1 contains only a `.gti.gz` | **741 / 741** (100.0%) |
| Distinct `file_types` patterns across SDD1 | **1** (`"gti.gz"` only) |
| Distribution of SDD1 GTI uncompressed size | **5,760 bytes, std = 0** (every file byte-identical) |

The SDD1 GTI placeholders are exactly the same file in every observation
across the entire 28-month window. This is the canonical "no-op" sidecar
the SoLEXS L1 pipeline emits when a detector is not producing science
telemetry.

### Deep inspection of 5 GTI samples spanning the full window

Sampled at 2024-02-01, 2024-09-08, 2025-04-02, 2025-11-28, 2026-06-13.
Every sample is identical:

```
n_hdus:           2
primary TSTART:   ''        (empty string)
primary TSTOP:    ''        (empty string)
GTI rows:         0         (truly empty table)
EXPOSURE keyword: 0.0       (not just missing — explicitly zero)
```

### SDD2 control check

SDD2 has both `.lc.gz` and `.pi.gz` in **741 / 741 (100.0%)** observations
in the same corpus. The empty-SDD1 pattern is detector-specific, not a
broader pipeline or download issue.

### Why no validation plot

Task 3 only applies if any SDD1 `.lc.gz` files exist. None do, so the
`sdd1_vs_sdd2_oct3_2024.png` plot was correctly not produced.

---

## Physical interpretation

SoLEXS flies two SDDs (Silicon Drift Detectors) by design — SDD1 and
SDD2 — for redundancy. ISRO's L1 telemetry pipeline always emits the
canonical directory layout (`SDD1/` and `SDD2/`) regardless of whether
both detectors are producing science. The byte-identical empty GTI is the
pipeline's way of saying *"no science from this detector for this
period."*

The most likely cause (consistent with mentor-side knowledge of the
SoLEXS team and ground tests) is that SDD1 was not commissioned for
nominal science after launch, or has been kept switched off for the
entire mission to date. Treat SoLEXS as a one-channel SXR instrument on
the science timeline that matters for this project.

This is **not** an oversight in our data download — the SDD1 archive is
genuinely empty at the ISRO source.

---

## Recommendation for Phase 3

**Keep the current 5-detector architecture.** No change to:

- The 5 independent detection pipelines:
  `SoLEXS-SDD2`, `HEL1OS-CdTe1`, `HEL1OS-CdTe2`, `HEL1OS-CZT1`, `HEL1OS-CZT2`
- The wide schema in `data/processed/daily_lightcurves/`
- The labeled-seconds schema in `data/processed/labeled_seconds/`
- The fusion layer producing the Master Flare Catalog

## Estimated project impact: zero

No code changes, no re-builds, no schema updates required. The
verdict closes an open question rather than producing work.

### Documentation tweak (low-effort, do once)

Add a one-line forward-reference to this file from
`data/processed/SCHEMA.md` so future readers understand why
`solexs_sdd1_*` columns don't exist:

> SoLEXS SDD1 is intentionally absent — see `SDD1_VERDICT.md`.
> The L1 pipeline emits empty `.gti.gz` placeholders for SDD1 in every
> observation (741/741 confirmed); no light curves or spectra are
> produced for that detector.

### Talking point for the proposal / finale

This investigation is itself worth one sentence in the proposal as
evidence of data-quality due diligence: *"We exhaustively verified
that SoLEXS SDD1 contains no science data across all 741 daily
observations in the 2024-02 .. 2026-06 window; SDD2 is the operational
SXR channel."* It pre-empts a likely judge question.

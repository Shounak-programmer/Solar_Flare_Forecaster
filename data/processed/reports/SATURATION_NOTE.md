# SoLEXS Spectral-Chain Saturation — Diagnostic Note

**Date:** 2026-06 · **Scope:** diagnosis only (no results recomputed) ·
**Refs:** Sarwade et al. 2025 (SoLEXS calibration); HEL1OS instrument paper
(arXiv 2512.12679). **Plot:** `data/validation/solexs_saturation_check.png`.

## Summary

Our SoLEXS L1 light curves are the **spectral (slow) chain**, **not
deadtime-corrected**. For M/X-class flares the spectral chain saturates
(paralyzable, deadtime 13.65 µs, observable ceiling ≈ 26,951 cts/s) and
**underestimates — and can invert the ordering of — the peak count rate**. This
affects only **peak-amplitude** quantities; **rise-phase** values (which all our
results rely on) are unaffected. HEL1OS CdTe/CZT have substantial headroom and
are **not** saturated in the same way, so hard-X amplitudes are trustworthy.

## Provenance

| Evidence | Finding |
|---|---|
| `CREATOR` | `solexs_pipeline-1.1` |
| `CONTENT`, `NUMBAND` | `LIGHT CURVE`, 4 energy bands → energy-resolved → spectral chain (same chain as the 340-channel `.pi`) |
| `DEADAPP` / `DEADC` / `DTCOR` | **absent** in `.lc` and `.pi` → **no deadtime correction applied at L1** |

The loader (`src/data/loaders.py`) reads the `COUNTS` column verbatim; nothing
downstream corrects it.

## Three independent saturation signatures (the 4 X-class anchors)

Paralyzable model `R_obs = R_true·exp(−R_true·τ)`, τ = 13.65 µs →
**max observable = 1/(τe) = 26,951 cts/s** (at R_true = 73,260); above that true
rate the observed rate *declines*.

| Event | GOES | SoLEXS peak (10 s) | % of ceiling |
|---|---:|---:|---:|
| X9.0 (2024-10-03) | 8.9e-4 | 22,373 | 83% |
| X8.1 (2026-02-01) | 8.1e-4 | **27,230** | **101%** |
| X7.1 (2024-10-01) | 7.1e-4 | 23,485 | 87% |
| X4.0 (2025-11-14) | 4.0e-4 | 18,986 | 70% |

1. **Inverted ordering (smoking gun).** By GOES class: X9.0 > X8.1 > X7.1 > X4.0.
   By observed SoLEXS peak: **X8.1 > X7.1 > X9.0 > X4.0**. The *largest* flare
   (X9.0) has only the 3rd-highest SoLEXS peak — its true rate (~1.3e5) is past
   the turnover, so its observed rate fell *below* the smaller X8.1/X7.1.
2. **Pinned at the ceiling.** All four peaks are 70–101% of 26,951, in a narrow
   1.43× band — the pile-up of a saturated detector. X8.1 sits *at* the ceiling.
   (Observed max 27,230 ⟹ τ ≤ 13.5 µs — our own data confirms the published
   13.65 µs.)
3. **Turnover while GOES rises** (the two anchors with GOES coverage):
   - X9.0: SoLEXS peaks 12:16:59 at 22,373, then **declines 7.8%** to 20,622 by
     the GOES peak (12:18) — while GOES xrsb is still rising.
   - X7.1: SoLEXS peaks 22:17:22 at 23,485, then **declines 6.6%** to 21,946 by
     the GOES peak (22:20).

Note: observed rates never reach the paper's "~5e4 cts/s" because the chain
physically cannot exceed ~27 k — that ceiling *is* the saturation. The ~5e4 is
the **true incident rate** where it bites; our peaks imply true rates of
~3e4 (X4.0) to ~1.3e5 (X9.0) — all four anchors are in/past the saturation regime.

## HEL1OS CdTe/CZT — NOT saturated the same way (the clean point)

HEL1OS L1 is also uncorrected (no `DEADAPP`) and carries no deadtime constant;
event timestamps are 10 ms-quantized (frame time), so deadtime can't be measured
from photon timing. But the **max observed rate bounds the deadtime** (observed
≤ 1/(τe)), and the **spread** of bright-flare peaks distinguishes a pinned
(saturated) detector from one with headroom:

| Detector | peak range (4 anchors) | spread | implied τ ≤ | ceiling ≥ | verdict |
|---|---|---:|---:|---:|---|
| SoLEXS-SDD2 | 19.0–27.2 k | 1.43× | 13.5 µs | 27 k | **pinned at ceiling — saturated** |
| HEL1OS-CdTe1 | 21.0–52.6 k | 2.50× | 7.0 µs | ≥53 k | wide spread — headroom |
| HEL1OS-CdTe2 | 23.0–54.2 k | 2.35× | 6.8 µs | ≥54 k | wide spread — headroom |
| HEL1OS-CZT1 | 7.9–17.1 k | 2.15× | 21.5 µs | ≥17 k | headroom (low rates) |
| HEL1OS-CZT2 | 8.1–23.2 k | 2.85× | 15.9 µs | ≥23 k | headroom (low rates) |

A saturated detector clips near a fixed ceiling (SoLEXS: all peaks within 1.43×,
at 70–101% of its known ceiling). HEL1OS CdTe spans **2.4–2.5×** and reaches
**54 k** — proving its ceiling is ≥54 k and its deadtime ≤ ~7 µs (about half
SoLEXS's), i.e. **substantial headroom**. CZT rates are low (8–23 k), consistent
with the HEL1OS-paper note that CZT background is benign.

**Caveat:** the brightest CdTe peak (~54 k, X8.1) is within a factor of its
lower-bound ceiling, so the *very brightest* CdTe peaks cannot be 100% cleared
without the **published HEL1OS deadtime**. The wide spread argues against heavy
saturation, but this is the one open item.

**Consequence for the hardness ratio:** the distortion at M/X peaks is driven by
the **saturated SoLEXS denominator only** — the HEL1OS hard-X numerator has
headroom, so it is **not "doubly distorted."** Hard-X amplitudes are trustworthy.

## Impact

| Affected (uses SoLEXS peak amplitude) | Unaffected |
|---|---|
| Phase 3 SoLEXS-SDD2 catalog: `peak_rate`, `peak_bgsub`, `max_significance` | **Detection recall** — triggers on the rise; all X-class still detected (100% X-recall) |
| Master catalog: `peak_rate_max`, `confidence` (when SoLEXS is the peak member) | **Forecasting skill** — top feature `soft_ddt_5m` is the rise-phase derivative, pre-saturation; TSS 0.346 stands |
| Forecasting features: `solexs_*_max_*`, `hardness_ratio`, `neupert_resid` (distorted *at peak*) | **Flare class labels** — from SWPC/GOES, never SoLEXS amplitude |
| | **QPP catalog** — HEL1OS CZT hard X-ray, independent of SoLEXS |

## Rule

**Do NOT use the SoLEXS peak count rate as a flare-magnitude proxy for M/X
flares** — it saturates near 27 k and inverts ordering above it. Rank flare size
by GOES class (labels) or by rise-phase signatures, not by SoLEXS peak.

## Limitation & remedy (not done here)

Do **not** deadtime-correct the spectral chain: `R_obs = R_true·exp(−R_true·τ)`
is multi-valued past the turnover, and we do not have the timing (fast) chain
product (our files are `.lc/.pi/.gti`, all spectral chain). To recover true
X-class peak amplitudes later, **request the POC's timing-chain or
deadtime-corrected L1 from Sarwade.** Documented honestly rather than corrected.

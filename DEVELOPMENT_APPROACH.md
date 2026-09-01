# Aditya-L1 Solar Flare System — Deep Research & Development Approach

*A grounded assessment of the current system, where it sits against the 2024–2025 literature, and a concrete roadmap for further development and architectural evolution.*

---

## 0. How to read this document

This is a research/architecture review, not a task list. It has three parts:

1. **Where the project is today** — an honest, layer-by-layer state of what is built (§1–2).
2. **Where it sits scientifically** — benchmarking against the current literature, and the single most important framing correction (§3).
3. **Where to take it** — two development tracks (harden vs. evolve), a prioritized roadmap, and specific architecture changes (§4–7).

Citations to papers are inline; full list in §8.

---

## 1. What exists today (system map)

The project is a complete, four-layer pipeline. This is genuinely a lot of working machinery — the assessment below is critical *because* the foundation is strong enough to build on.

```
RAW X-RAY (SoLEXS SDD2 + HEL1OS CdTe1/2, CZT1/2)  +  AUX (GOES/SWPC/HEK/F10.7/SRS)
        │
   [1] DATA  scripts/01–09, src/data/
        │  → 1-Hz wide-schema parquet, 620 days, 86,400 rows/day
        │  → labeled_seconds/ (15 label cols incl. flare_in_next_{15,30,60}min)
        ▼
   [2] DETECTION  scripts/09–13, src/detection/
        │  → 5 per-detector Poisson-significance detectors
        │  → bounded single-linkage fusion → master_flare_catalog (12,858 flares)
        │  → QPP catalog (Vaughan red-noise + Morlet wavelet)
        │  → nowcast TSS ≈ 0.84, X-recall 100%
        ▼
   [3] FORECASTING  scripts/14–18, src/forecasting/
        │  → features: soft_ddt, Neupert residual, hardness ratio, event history, QPP, lagged context
        │  → primary: calibrated XGBoost (15-min TSS 0.346); secondary: TFT (0.235, bested)
        │  → Gate-A leakage audit, isotonic calibration (ECE 0.34→0.006)
        ▼
   [4] DASHBOARD  app/ (FastAPI + vanilla JS + Plotly)
           → replay-only; serves pre-exported dashboard_data/*.json
           → tabs: Replay / Performance / Operations / Catalog
```

### Headline numbers (as reported by the pipeline)

| Task | Metric | Value | Baseline beaten |
|---|---|---|---|
| Detection (nowcast) | TSS | **0.84** | persistence 0.007, climatology 0.000 |
| Detection X-class recall | recall | **100%** (43/43) | — |
| Master catalog vs best single detector | POD | **0.872 vs 0.808** | +0.064 |
| Forecast 15-min | TSS | **0.346** | persistence 0.162, climatology 0.000, TFT 0.235 |
| Calibration | ECE | **0.340 → 0.006** | (isotonic) |
| QPP catalog | events | 513 significant in 2+ flares | first Aditya-L1 QPP catalog |

---

## 2. Layer-by-layer assessment (strengths & weaknesses)

### [1] Data engineering — **mature**
**Strengths:** Clean 1-Hz wide schema; rigorous data-quality investigations that match the published instrument papers (see §3.2); cross-day-buffered labeling; coverage manifest tracking 872 calendar days; validated end-to-end on three X-class anchors (X9.0, X7.1, X8.1).

**Weaknesses / debt:**
- Hardcoded absolute paths `I:/Solar Flare ISRO/...` in `src/data/loaders.py` (lines 33–34) and relative `Path("data")` in `download_auxiliary.py` — blocks portability and any cloud deploy.
- 1-Hz resampling is irreversible and discards sub-second structure (SoLEXS ~0.5 s, HEL1OS event list ~10 ms). Fine for forecasting; limiting for QPP science < 4 s.
- No programmatic schema contract (`SCHEMA.md` is prose). Column drift would fail silently downstream.
- Null convention mixing (`NaN` for floats, `pd.NA` for Int64/categorical).
- 34 HEL1OS days recovered from backup (mixed provenance); 14 days missing sunspot number.

### [2] Detection — **strong, the project's most defensible result**
**Strengths:** Five independent detectors with physically-motivated, label-free background (10th-percentile inference mode avoids circularity); bounded single-linkage fusion prevents the "60-minute blob" failure of naive union-find; member-aware matching to SWPC is robust to median drift; the energy-ordered hardness selectivity (1.2× soft → 8.5× hard) is a real physical validation of the multi-detector design; QPP detection uses the correct red-noise null (Vaughan 2005 Whittle fit with the essential white-noise `+C` term) and a synthetic false-positive guard.

**Weaknesses / debt:**
- ~20 hardcoded thresholds (smoothing 70 s, min duration 60 s, link gaps, tolerances) — no sensitivity analysis or ablation showing each stage earns its place.
- Poisson significance assumes independent 1-s counts; this is *violated by exactly the deadtime/pile-up the project documents* for SoLEXS at M/X peaks. Detection survives (triggers on the rise), but significance values at peak are not trustworthy.
- 33.7% of master flares are "candidate-novel" (in neither SWPC nor HEK) with no systematic follow-up — could be real sub-threshold events or false positives; currently unknown.
- Point-estimate metrics only; no bootstrap confidence intervals on TSS/POD.

### [3] Forecasting — **honest but modest; the highest-leverage area**
**Strengths:** This is methodologically careful work. The Gate-A leakage audit (manual source-row trace, +1-step shift test, |corr|>0.9 flag, GTI→NaN check) is better discipline than most published flare-ML papers. Isotonic calibration is correct and the ECE improvement is real. Comparing against persistence *and* climatology *and* an honestly-bested TFT is exactly right. The "quiet→X all-clear" test directly targets the Camporeale (2025) rare-event failure mode.

**Weaknesses / debt:**
- **15-min TSS 0.346 is modest**, and the headline framing risks conflating it with the 0.84 *detection* number (see §3.1 — this is the single most important correction).
- Single TFT run, CPU-budget-capped (~50 min), no hyperparameter sweep or ensemble — the TFT was likely under-trained, so "TFT bested" is weakly supported.
- Temporal split only (train 2024-07→2025-06, val→2025-12, test 2026-01→06). No active-region-partitioned evaluation, which the 2025 review (arXiv 2511.20465) calls essential.
- No SHARP/magnetogram features at all — the entire mainstream of the field is invisible to this system (Aditya-L1 carries no magnetograph; see §4.1).
- X-class test denominator is ~11 events — wide confidence intervals on the most important class.

### [4] Dashboard — **excellent demo artifact, not operational**
**Strengths:** Clean architecture (pre-exported JSON replay = honest, reproducible, zero-latency); thoughtful UX (causal reveal, lead-time callouts, all-clear panel, QPP wavelet gallery); good separation of train/test framing in the UI.

**Weaknesses / debt — including one integrity flag:**
- **🚩 Hardcoded metrics in `scripts/dashboard/export_dashboard_data.py`:** per-class recall (line ~295), all-clear "2/2 … 8/11" (line ~299), and TFT TSS in `performance.js` are *hand-entered*, not computed from the test set. If a model changes, the dashboard silently displays stale numbers. For a scientific demo this is the most important thing to fix — **all displayed metrics must be computed from predictions at export time.**
- Replay-only: cannot ingest live data or run inference. 7 fixed demo days, no arbitrary-date browse.
- No tests (frontend or backend), no auth, open CORS, no OpenAPI docs, in-memory cache never invalidated.

### [5] The "RAG/LLM layer" — **budgeted and provisioned, but does not exist**
`requirements.txt` ships `langchain-*`, `ollama`, `qdrant-client`, `sentence-transformers`, `rank-bm25`, `torch`, `transformers`, and `BUDGET.md` allocates ₹26k+ for a "Qdrant/ollama RAG backend." **No code imports or wires any of it.** It is a planned capability with the dependencies pre-installed and nothing built.

---

## 3. Scientific positioning (where this sits in the field)

### 3.1 The single most important framing correction: **nowcasting ≠ forecasting**

The project produces two very different numbers and they must never be conflated:

- **Detection / nowcasting TSS ≈ 0.84** — "is a flare happening *now*, given the X-ray light curve up to now?" This is a comparatively easy signal-detection task (the flare is *in* the data).
- **Forecasting 15-min TSS ≈ 0.346** — "will a flare peak in the *next* 15 minutes, given only precursors?" This is the genuinely hard, genuinely valuable task.

The dashboard already states this ("Detection TSS 0.84 is nowcasting (separate task)"), which is good. But every external comparison must use the **0.346 forecasting number**, and must state the **horizon (15 min)** and **inputs (X-ray time series only, no magnetograms)**. These three qualifiers determine whether a comparison is fair.

### 3.2 The instrument papers confirm the project's own findings

This is a real strength worth stating loudly. The 2025 SoLEXS in-flight performance paper (arXiv 2509.26292) independently confirms:
- **SDD1 is non-operational** during active periods ("minimal operation mode," "full characterization still pending") — matching the project's `SDD1_VERDICT.md` (741/741 observations empty).
- **SDD2 is the primary detector**, and the spectral chain has **paralyzable deadtime 13.65 µs** with pile-up — matching the project's `SATURATION_NOTE.md` (peak amplitudes saturate and even invert ordering at M/X).
- Crucially, the paper notes **pile-up events are individually recorded by the faster timing chain** — which is the key that unlocks a deadtime correction (see §4.3).
- L1 gives a **100% duty cycle** vs <70% for LEO instruments — a genuine differentiator for *continuous* monitoring that this project should lean into.

HEL1OS (arXiv 2512.12679 / 2025): CdTe 8–70 keV, CZT 20–150 keV, hard X-rays tracing the impulsive/non-thermal phase — which is exactly why the Neupert-residual and hardness features are physically motivated.

### 3.3 Benchmarking against the 2024–2025 literature

| System / paper | Task | Horizon | Inputs | TSS |
|---|---|---|---|---|
| **This project (forecast)** | ≥any-flare | **15 min** | Aditya X-ray TS only | **0.346** |
| Human forecasters (NOAA SWPC) | ≥M | 24 h | all data + expert | 0.3–0.5 |
| Moirai2 foundation TS (2510.23400) | ≥M | 24 h | GOES soft X-ray TS only | **0.736** |
| SigLIP2 image (2510.23400) | ≥M | 24 h | HMI magnetogram | 0.646 |
| SolarFlareNet (transformer) | ≥M | 24 h | SHARP params | >0.83 (offline) |
| CNN-TCN (Xu 2025) | C+/M+ | 24 h | HMI magnetograms | 0.85 |

**What this table really says:**
1. The project is **not directly comparable** to the 0.7–0.85 rows — those are 24-hour, ≥M-class, AR/magnetogram tasks. Different problem.
2. The most relevant external result is **Moirai2 (TSS 0.736 at 24h from soft X-ray *time series alone*, class-balanced)**. This is the strongest evidence that **X-ray-time-series-only forecasting can be far more skillful than this project currently achieves** — and points directly at the architecture upgrade in §4.2.
3. The project's 15-min horizon is a legitimate, under-served niche (most systems forecast 24h). The honest pitch is *"continuous, sub-minute-cadence, short-horizon precursor nowcasting from L1 — complementary to 24h magnetogram forecasting, not competing with it."*

### 3.4 Evaluation-methodology gaps the field considers mandatory (2511.20465 review)

- **Active-region-partitioned splits** (no AR in both train and test) — the project uses temporal splits only. For *short-horizon nowcasting* temporal splits are arguably more operationally honest, but the review's standard should at least be reported alongside.
- **Report TSS with std across folds/bootstraps** — currently point estimates.
- **Move to probabilistic, multi-class, reliability-diagram-backed outputs** — the project already does isotonic calibration and reliability diagrams (ahead of many), but multi-class (B/C/M/X) probabilistic forecasting is only partially built.
- **Submit to the CCMC Flare Scoreboard** for credible, standardized, real-time benchmarking.

---

## 4. Architecture evolution — the high-leverage changes

These are ordered by impact-to-effort. Each is a genuine architecture change, not a tweak.

### 4.1 Add magnetogram-derived features (biggest capability expansion)
**Why:** Aditya-L1 has no magnetograph, so the system is blind to the photospheric magnetic complexity that drives 24-hour forecasting. Fusing free **SDO/HMI SHARP** parameters (or NOAA SRS McIntosh/Hale classes the project *already ingests but underuses*) would let the system forecast at the **6/12/24-hour horizon the operational world actually uses** — without abandoning its short-horizon X-ray strength.
**How:** Add an AR-feature builder pulling SHARP CEA parameters (USFLUX, TOTUSJH, R_VALUE, etc.) per active region; join to the daily context; add 6/12/24h targets. Keep the X-ray precursor model as a separate short-horizon head.
**Note:** This is the path to comparability with the entire mainstream literature. It also fixes the under-use of `active_regions_daily.parquet` (currently only `active_ar_count` is broadcast).

### 4.2 Replace/augment the model with a foundation time-series model
**Why:** Moirai2 reaching TSS 0.736 from X-ray TS alone (vs this project's 0.346) is the loudest signal in the literature that the *modeling*, not the data, is the bottleneck. XGBoost on hand-rolled rolling features leaves signal on the table; the single under-trained TFT doesn't close the gap.
**How:** Fine-tune a pretrained TS foundation model (**Moirai2, Chronos, or TimesFM**) on the 1-Hz/1-min Aditya streams for the forecasting heads. Keep XGBoost as the interpretable, fast, audited baseline (it should remain the fallback per the existing Gate-C rule). Budget a *proper* GPU sweep for the deep model on the owned RTX 5070 Ti — the current 50-min CPU cap is why TFT lost.
**Guardrail:** Re-run the Gate-A leakage audit on any sequence model; foundation models are very capable of finding leakage.

### 4.3 Deadtime-correct SoLEXS to recover peak amplitude
**Why:** The project currently (correctly) refuses to use SoLEXS peak as a magnitude proxy because of saturation. The SoLEXS paper says the **timing chain individually records pile-up events** — so a paralyzable-model inversion `R_true = -W(-R_obs·τ)/τ` (Lambert-W) using τ=13.65 µs, cross-checked against the timing-chain counts, can recover true peak rates. This would turn a documented limitation into a *peak-flux regression* capability and a self-calibrated GOES-class estimator independent of SWPC.
**How:** New `src/data/deadtime.py`; validate the inversion on the X-class anchors against GOES peak flux (cross-cal already shows SoLEXS reads higher at peaks — consistent with un-saturated truth).

### 4.4 Build the real-time inference path (productionize beyond replay)
**Why:** The dashboard is replay-only; there is no way to forecast on incoming data. The L1 100% duty cycle is wasted if the system can't run live.
**How:** A streaming service: ingest latest L1 products → run the same feature builder incrementally → serve live forecasts via a new `/api/live` endpoint, with the replay path unchanged for demos. Add an alert-delivery hook (Twilio/SES are already budgeted) gated on the Warning operating point.

### 4.5 Build the planned RAG/LLM narrative layer (deps already installed)
**Why:** Budgeted, dependencies shipped, zero code. A forecast is more useful to an operator with a generated plain-language briefing ("WATCH: AR 13664 shows rising hard-X hardness + 18 s QPP; 34% chance of ≥C in 15 min; recommended action…").
**How:** Index the flare catalog, QPP catalog, and instrument/calibration notes into Qdrant with `sentence-transformers`; generate operator briefings with a local model via `ollama` (free fallback) or Claude API (budgeted). Use the latest Claude models (Opus 4.8 / Sonnet 4.6) if the API path is chosen — see `requirements.txt` already targets this stack. Keep it strictly grounded in retrieved facts to avoid hallucinated risk numbers.

### 4.6 Multi-task / physics-informed heads (research-forward)
Per the 2025 review's recommended direction: a single model jointly predicting **flare occurrence + peak-flux regression + QPP-presence + class**, sharing the precursor representation. This is the natural endpoint once 4.1–4.3 land.

---

## 5. Engineering hardening (do these regardless of direction)

These are cheap, unblock everything else, and several are correctness issues.

1. **Config management** — move all hardcoded `I:/...` paths and the ~20 detection thresholds into a `config.yaml` + `pydantic-settings` (already a dependency). Blocks cloud deploy today.
2. **🚩 Compute dashboard metrics at export time** — eliminate every hand-entered number in `export_dashboard_data.py` / `performance.js`. Integrity issue.
3. **Schema contract** — a `pyarrow`/`pydantic` schema enforced on parquet load; fail loudly on drift.
4. **Bootstrap confidence intervals** — on every reported TSS/POD/recall, especially X-class (n≈11–43).
5. **Tests + CI** — at minimum, golden-file tests on the three X-class anchors through the full pipeline; pytest on `src/`; GitHub Actions (free, already in budget).
6. **Reproducibility** — pin the random seeds, log the exact split dates and sample counts into each output, and write a one-command pipeline runner (`scripts/00_run_all.py`).
7. **AR-partitioned eval report** — add it alongside the temporal split so reviewers see both.

---

## 6. Prioritized roadmap

Three horizons. Each phase is independently shippable.

### Phase A — Harden & de-risk (low effort, high trust)
- Config management (§5.1); compute-not-hardcode dashboard metrics (§5.2); schema contract (§5.3); bootstrap CIs (§5.4); seed/repro + one-command runner (§5.6); golden-file tests (§5.5).
- **Outcome:** the existing results become portable, reproducible, and trustworthy. *Do this first — it's the foundation for any honest "we improved X" claim later.*

### Phase B — Close the forecasting gap (medium effort, high impact)
- Foundation TS model with a real GPU sweep (§4.2); SoLEXS deadtime correction + peak-flux regression (§4.3); AR-partitioned + temporal dual evaluation (§5.7); proper TFT re-match so the "bested" claim is defensible.
- **Outcome:** 15-min forecasting TSS moves toward the demonstrated ceiling for X-ray-only models; a defensible peak-flux/GOES-class estimator independent of SWPC.

### Phase C — Expand capability & operationalize (higher effort, new value)
- Magnetogram/SHARP fusion → 6/12/24h forecasting (§4.1); real-time inference + alert delivery (§4.4); RAG/LLM operator briefings (§4.5); CCMC Flare Scoreboard submission (§3.4).
- **Outcome:** the system becomes comparable to the mainstream 24h literature *and* operationally live, while keeping its unique L1 continuous short-horizon edge. Multi-task/PINN heads (§4.6) follow naturally.

---

## 7. If you keep one thing and change one thing

- **Keep:** the detection layer and the methodological discipline (label-free background, leakage audit, calibration, honest baselines). That rigor is rarer than the models.
- **Change:** the forecasting model and how its results are framed. The 15-min TSS 0.346 is real but modest; the literature shows X-ray-only models reaching ~0.74; and the headline must always separate **forecasting (0.346, 15 min, X-ray only)** from **nowcasting (0.84)**.

---

## 8. References

- *Advances and Challenges in Solar Flare Prediction: A Review* (2025) — arXiv:2511.20465. Categories, evaluation best practices (AR-partitioned splits, TSS/HSS/MCC/FAR), PINN/multi-task/online-learning directions, CCMC scoreboard.
- *Solar flare forecasting with foundational transformer models across image, video, and time-series modalities* (2025) — arXiv:2510.23400. Moirai2 (time-series) TSS 0.736 > SigLIP2 image 0.646 > VideoMAE 0.604 for 24h ≥M; X-ray time series alone is highly competitive.
- *Solar Low Energy X-ray Spectrometer on board Aditya-L1: Ground Calibration and In-flight Performance* (2025) — arXiv:2509.26292. Confirms SDD1 non-operational, SDD2 primary, 13.65 µs paralyzable deadtime, timing-chain pile-up recording, 100% L1 duty cycle.
- *HEL1OS — A Hard X-ray Spectrometer on Board Aditya-L1* (2025) — arXiv:2512.12679 / Springer Solar Physics. CdTe 8–70 keV, CZT 20–150 keV; impulsive-phase hard X-rays.
- *Verification of the NOAA SWPC solar flare forecast (1998–2024)* (2025) — arXiv:2508.01114. Human operational baseline (major-flare TSS ≈ 0.3–0.5).
- *A Deep Learning Approach to Operational Flare Forecasting* / SolarFlareNet — arXiv:2405.16080. Transformer, operational near-real-time, >0.83 offline 24h ≥M.
- Vaughan (2005), *A simple test for periodic signals in red noise* — the red-noise null used by the project's QPP detector.
- Camporeale (2025) — rare-event "all-clear" failure mode the project's quiet→X test targets.

*Methods and numbers about the existing system in §1–2 are drawn directly from the project source (`src/`, `scripts/`, `data/processed/reports/`, `dashboard_data/`).*

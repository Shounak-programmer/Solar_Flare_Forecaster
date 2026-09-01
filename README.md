# ☀️ Aditya-L1 Solar Flare Nowcasting & Forecasting System

<div align="center">

**ISRO Bharatiya Antariksh Hackathon 2026 · Problem Statement PS-15**  
*Forecasting and Nowcasting of Solar Flares using combined Soft and Hard X-ray data from Aditya-L1*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-3.2%2B-eb5424.svg)](https://xgboost.readthedocs.io/)
[![Status](https://img.shields.io/badge/Science-FROZEN%20%26%20VERIFIED-brightgreen.svg)](#-verified-headline-results)

**Team SURYASETU** · *Adamas University*

</div>

---

## 📌 Executive Summary

Solar flares release up to $10^{25} \text{ Joules}$ of energy in minutes, disrupting satellite avionics, high-frequency (HF) telecommunications, civil aviation polar routes, and India's satellite navigation constellation (**NavIC**). Traditional space-weather systems rely on photospheric magnetograms and slow optical telemetry, frequently missing rapid precursor signatures and failing to predict sudden X-class eruptions from quiet backgrounds.

This repository presents **SURYASETU**, an end-to-end, **X-ray-only, physics-informed** solar flare forecasting and nowcasting system built exclusively on data from India's first solar observatory, **Aditya-L1**:
1. **SoLEXS (Solar Low Energy X-ray Spectrometer):** Soft X-rays ($1\text{--}30\text{ keV}$ / $1\text{--}15\text{ \AA}$) tracking thermal plasma heating and loop expansion.
2. **HEL1OS (High Energy L1 Orbiting X-ray Spectrometer):** Hard X-rays ($10\text{--}150\text{ keV}$) tracking non-thermal accelerated electron beams.

By leveraging the **Neupert Effect** ($F_{\text{HXR}}(t) \propto \frac{d}{dt} F_{\text{SXR}}(t)$) and multi-band hardness ratios, the system provides **10–15 minute advance warning** of impending major flares and concurrently maintains an ultra-low-latency real-time nowcasting detection pipeline.

---

## 🔬 Core Science & Physical Principles

```
           MAGNETIC RECONNECTION IN CORONAL LOOPS
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
 NON-THERMAL ELECTRON BEAMS           DIRECT THERMAL HEATING
 (HEL1OS: 10–150 keV Hard X-rays)     (Early precursor emission)
            │                                 │
            ▼                                 ▼
 CHROMOSPHERIC EVAPORATION ────────► EXPANDING PLASMA LOOPS
                                     (SoLEXS: 1–30 keV Soft X-rays)
```

- **The Neupert Effect Engine:** Hard X-ray bremsstrahlung emission produced by non-thermal electron beam bombardment directly drives the rate of change ($dF_{\text{SXR}}/dt$) of thermal soft X-ray emission. Hard X-ray surges precede soft X-ray peaks by several minutes, unlocking a direct predictive precursor signal without relying on optical magnetogram latency.
- **Instrument-Aware Saturation Inversion:** Accounts for SoLEXS spectral-chain pulse pile-up and saturation limits during peak M/X events (Sarwade et al. 2025). The system never ranks flare magnitude by raw SoLEXS peak amplitude, relying instead on non-saturating rise-phase gradients and HEL1OS headroom.
- **Quasi-Periodic Pulsations (QPP):** Implements Continuous Wavelet Transforms (Morlet CWT) combined with Vaughan (2005) $AR(1)$ red-noise significance modeling to identify magnetohydrodynamic (MHD) sausage/kink mode oscillations in flare loops.

---

## 📊 Verified Headline Results

All metrics are benchmarked on strictly held-out test data (2026-01 → 2026-06) and verified through automated integrity guards (`scripts/verify_numbers.py`).

### 1. Probabilistic Forecasting (Predictive, Ahead of Time)
Evaluated using the True Skill Statistic (**TSS**), robust against extreme class imbalance (Bloomfield et al. 2012).

| Forecast Horizon | Calibrated XGBoost (TSS) | 95% Bootstrap CI | Persistence Baseline | Climatology Baseline |
|:----------------:|:------------------------:|:----------------:|:--------------------:|:--------------------:|
| **15 Minutes**   | **0.346**                | [0.324, 0.366]   | 0.162                | 0.000                |
| **30 Minutes**   | **0.229**                | [0.200, 0.259]   | 0.153                | 0.000                |
| **60 Minutes**   | **0.205**                | [0.169, 0.240]   | 0.161                | 0.000                |

- **Probability Calibration:** Isotonic regression reduced Expected Calibration Error (**ECE**) from **0.340 → 0.006** and Brier score from **0.194 → 0.070**. A 30% forecast probability represents an actual 30% empirical event frequency.
- **Deep Learning Benchmark:** Calibrated XGBoost honestly outperformed Temporal Fusion Transformer (TFT score: 0.235 vs 0.346).
- **Zero-Failure Operational Transitions:** Flagged **2/2 (100%)** quiet-to-X transition events on held-out data:
  - **X8.1 Superflare:** Warned ~**10 minutes** before peak.
  - **X1.9 Major Flare:** Warned ~**15 minutes** before peak.

### 2. Multi-Detector Nowcasting (Concurrent Event Detection)
- **Detection TSS:** **0.840** (Catalog-aware; per-bin 0.7456).
- **Fused Event Recall:** **0.872** (vs best single detector 0.808).
- **X-Class Event Recall:** **100% (43/43 events captured)**.
- **Master Solar Flare Catalog:** **12,858** Aditya-L1 detected events:
  - **40.2%** Confirmed GOES/SWPC matches.
  - **26.1%** Sub-threshold microflares.
  - **33.7%** Candidate-novel detections.

### 3. Cross-Instrument Fusion Ablation
| Instrument Configuration | TSS @ 15 min | TSS @ 30 min | TSS @ 60 min |
|:-------------------------|:------------:|:------------:|:------------:|
| SoLEXS Only (Soft X-ray) | 0.295        | 0.181        | 0.099        |
| HEL1OS Only (Hard X-ray) | 0.265        | 0.171        | 0.149        |
| **Combined SoLEXS + HEL1OS** | **0.345**    | **0.229**    | **0.205**    |

*Combining Soft and Hard X-rays outperforms any single instrument across all forecast horizons.*

### 4. Scientific Discovery: Aditya-L1 QPP Catalog
- First systematic QPP catalog produced from Aditya-L1 observations.
- **1,043 QPP detections across 513 flares**:
  - *Classic Tier (10–120 s):* 164 events.
  - *Intermediate Tier (8–10 s):* 118 events.
  - *Short Tier (4–8 s):* 761 events (*conservatively tagged pending instrumental cross-check*).

---

## 🛠️ Complete Tech Stack

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             TECH STACK ARCHITECTURE                     │
├───────────────────┬──────────────────────────────────────────────────────┤
│ Application Layer │ FastAPI, Uvicorn (ASGI), Pydantic v2, CORS, Cache-Ctl│
├───────────────────┼──────────────────────────────────────────────────────┤
│ Machine Learning  │ XGBoost, Scikit-Learn (Isotonic), PyTorch (TFT bench)│
├───────────────────┼──────────────────────────────────────────────────────┤
│ Signal & Physics  │ Astropy (FITS), PyWavelets (CWT), SciPy, NumPy       │
├───────────────────┼──────────────────────────────────────────────────────┤
│ Data Processing   │ Pandas, PyArrow (Parquet), JSON sidecars             │
├───────────────────┼──────────────────────────────────────────────────────┤
│ Frontend UI / UX  │ Vanilla HTML5/CSS3 (Glassmorphism), ES6+ JS, Plotly  │
│                   │ Canvas Physics Simulators (Reconnection & Neupert)   │
├───────────────────┼──────────────────────────────────────────────────────┤
│ Runtime & Deploy  │ Python 3.10+, PowerShell / Batch, Zero-Cost CPU Opt  │
└───────────────────┴──────────────────────────────────────────────────────┘
```

### Detailed Component Breakdown:

#### 1. Backend & Serving Engine
- **Language:** Python 3.10+ (Tested on 3.11 / 3.12 / 3.14).
- **Framework:** **FastAPI** (`0.135.3+`) with high-throughput asynchronous request routing.
- **ASGI Server:** **Uvicorn** (`0.44.0+`) with custom `no-store` middleware ensuring zero frontend caching issues during operational use.
- **Serving Paradigm:** Serves pre-computed, verified JSON artifacts in-memory with sub-millisecond response latency. Zero live model recalculation needed on demo stage.

#### 2. Machine Learning & Statistical Inference
- **Gradient Boosting:** **XGBoost** (`3.2.0`) trained on leakage-safe rolling window features (15m, 30m, 60m).
- **Probability Calibration:** **Scikit-Learn** (`1.7.2`) Isotonic CalibratedClassifierCV preserving rank-order AUC while minimizing ECE.
- **Validation & Metrics:** Scikit-Learn custom True Skill Statistic (TSS), Heidke Skill Score (HSS), Brier score, and Expected Calibration Error (ECE) pipelines.
- **Deep Sequence Baseline:** **PyTorch** (`2.11.0`) Temporal Fusion Transformer (TFT) with multi-head attention.

#### 3. Signal Processing, Astrophysics & Wavelets
- **Astronomical Data I/O:** **Astropy** (`6.1.7`) for parsing Aditya-L1 Level-1 and Level-2 FITS files.
- **Continuous Wavelet Transform:** **PyWavelets** (`1.8.0`) utilizing complex Morlet wavelets for power spectral density analysis.
- **Numerical Processing:** **NumPy** (`2.2.6`) and **SciPy** (`1.15.3`) for Lomb-Scargle periodograms, CUSUM filtering, red-noise background fitting, and FFTs.

#### 4. High-Performance Data Engineering
- **Columnar Storage:** **PyArrow** (`24.0.0`) Apache Parquet for ultra-fast reading of millions of 1-second synchronized time-series rows.
- **Tabular Wrangling:** **Pandas** (`2.3.3`) for rolling window feature engineering, timestamp alignments, and catalog cross-matching.
- **Network Ingestion:** **Requests** (`2.34.2`) and **Tqdm** (`4.67.3`) for auxiliary data synchronization from NOAA SWPC and ISRO ISSDC.

#### 5. Frontend & Visualization System
- **Structure & Aesthetics:** Clean semantic **HTML5** & **Vanilla CSS3** with dark-mode space-grade UI, glassmorphism cards, responsive multi-column CSS grids, and tabular numerical font metrics.
- **Interactive Telemetry:** **Plotly.js** (`v2.35.2`), fully vendored offline for zero-internet operation.
- **Interactive Physics Engines:** Custom HTML5 Canvas real-time physical simulations illustrating:
  - *Magnetic Reconnection & Particle Acceleration.*
  - *The Neupert Effect (Hard X-ray derivative coupling to Soft X-ray rise).*

---

## 🏗️ System Architecture

```
                    ADITYA-L1 SATELLITE (L1 LAGRANGE POINT)
                        │                     │
                SoLEXS (1–30 keV)      HEL1OS (10–150 keV)
                        │                     │
                        └──────────┬──────────┘
                                   │ Raw FITS Telemetry
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION, CALIBRATION & SYNCHRONIZATION PIPELINE                       │
│    - FITS parser & L1 data sanity audit                                    │
│    - UTC 1-second common timebase resampling                               │
│    - Pulse pile-up & saturation-aware spectral inversion                   │
│    - GOES-XRS / NOAA SWPC / HEK truth alignment                           │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 2. LEAKAGE-SAFE FEATURE ENGINEERING                                        │
│    - Soft X-ray flux derivatives: dF/dt (Neupert proxy)                    │
│    - Multi-band hardness ratios: H(10-25)/S(1-8), H(25-50)/S(1-8)          │
│    - Rolling peak-to-background, CUSUM drifts, rise velocities             │
└──────────────────────┬──────────────────────────────┬──────────────────────┘
                       │                              │
                       ▼                              ▼
┌──────────────────────────────┐    ┌────────────────────────────────────────┐
│ 3. NOWCASTING LAYER          │    │ 4. FORECASTING LAYER                   │
│    - 5-Detector Ensemble:    │    │    - XGBoost multi-horizon models      │
│      • CUSUM Drift           │    │      (15 / 30 / 60 min)                │
│      • Morlet Wavelet        │    │    - Isotonic Probability Calibration  │
│      • Threshold Peak        │    │    - Graded Alert Engine:              │
│      • Rise-Rate Derivative  │    │      • Watch Alert (p >= 0.0961)       │
│      • HEL1OS Hard-X Trigger │    │      • Warning Alert (p >= 0.2006)     │
│    - Disjoint Union-Find     │    │    - 100% Quiet→X Flare Transition Cap │
│    - Master Catalog (12,858) │    └──────────────────┬─────────────────────┘
│    - QPP Wavelet Catalog     │                       │
└──────────────┬───────────────┘                       │
               │                                       │
               └───────────────────┬───────────────────┘
                                   │ Pre-computed JSON & Parquet
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 5. SERVING & INTERACTIVE OPERATIONS DASHBOARD                              │
│    - FastAPI ASGI Server (Sub-millisecond memory cache)                    │
│    - Operations Replay Theater (33 held-out test days)                     │
│    - Live Alert Matrix & NavIC/Aviation advisory generator                 │
│    - Interactive QPP Power Spectra & Master Flare Catalog Browser          │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Directory Map

```
Solar-Flare-Prediction-main/
├── app/                               # Web dashboard application
│   ├── dashboard_server.py            # FastAPI ASGI server & REST endpoints
│   └── static/                        # Frontend assets (Zero CDN dependencies)
│       ├── css/style.css              # Custom responsive dark-theme stylesheet
│       ├── js/                        # Modular frontend scripts
│       │   ├── app.js                 # Core dashboard coordinator & navigation
│       │   ├── replay.js              # Replay Theater playback engine
│       │   ├── performance.js         # Reliability curves & validation charts
│       │   ├── operations.js          # Operations console & alert matrix
│       │   ├── catalog.js             # Master catalog & QPP browser
│       │   └── physics_sims.js        # Reconnection & Neupert Canvas animators
│       ├── vendor/                    # Vendored offline libraries (Plotly 2.35.2)
│       └── index.html                 # Main single-page application
│
├── dashboard_data/                    # Pre-computed verified dashboard artifacts
│   ├── manifest.json                  # Replay day index and metadata
│   ├── master_catalog.json            # 12,858 classified flares
│   ├── qpp_catalog.json               # 1,043 QPP candidate events
│   ├── summary_metrics.json           # Frozen verified headline metrics
│   ├── hardness_ordering.json         # Spectral hardness metrics
│   ├── replay_days/                   # 33 full-day 1-second telemetry JSONs
│   └── wavelets/                      # Pre-computed Morlet wavelet power arrays
│
├── data/                              # Data storage
│   ├── raw/                           # Raw Aditya-L1 FITS & GOES auxiliary data
│   └── processed/                     # Feature parquets, splits & report sidecars
│
├── scripts/                           # Reproducible pipeline stages (01 to 20)
│   ├── 01_ingest_fits.py              # Ingest SoLEXS/HEL1OS FITS into Parquet
│   ├── 02_sync_timegrid.py            # 1-second UTC master synchronization
│   ├── 03_label_flares.py             # Event labeling & cross-catalog matching
│   ├── 04_engineer_features.py        # Neupert derivatives & hardness features
│   ├── 05_train_detectors.py          # 5-detector nowcasting ensemble
│   ├── 06_fuse_detections.py          # Union-Find multi-detector fusion
│   ├── 07_extract_qpp.py              # Morlet CWT & red-noise QPP extraction
│   ├── 08_train_xgboost.py            # 15/30/60-min forecasting models
│   ├── 09_calibrate_probabilities.py  # Isotonic probability calibration
│   ├── 17_train_tft.py                # Temporal Fusion Transformer benchmark
│   ├── 19_defensibility.py            # Bootstrap CIs, lead-times & ablations
│   ├── 20_latency_benchmark.py        # CPU inference latency benchmark
│   ├── verify_numbers.py              # Number-drift guard against frozen data
│   └── dashboard/                     # Data export scripts for dashboard
│       ├── export_dashboard_data.py   # Compiles metrics and replay days
│       └── export_wavelets.py         # Exports wavelet power matrices
│
├── src/                               # Frozen core algorithmic library
│   ├── data/                          # Light-curve builders & loaders
│   ├── detection/                     # Detectors, fusion & QPP algorithms
│   ├── forecasting/                   # Features, baselines, XGBoost & calibration
│   └── config.py                      # Global configuration & path variables
│
├── BUDGET.md                          # Hackathon & deployment budget breakdown
├── IMPLEMENTATION_COST.md             # Engineering effort & resource roadmap
├── DEVELOPMENT_APPROACH.md            # Technical methodology & science defence
├── requirements.txt                   # Pinned dependency manifest
├── run_dashboard.bat                  # One-click Windows dashboard launcher
├── run_pipeline.bat                   # Full pipeline execution script
└── README.md                          # System documentation
```

---

## ⚡ Getting Started & Installation

### Prerequisites
- **Operating System:** Windows 10/11, Ubuntu 20.04+, or macOS.
- **Python:** Python 3.10, 3.11, or 3.12 installed.
- **Hardware:** Standard CPU (Inference takes only **0.20 ms**; GPU is completely optional).

### Step 1: Clone the Repository
```bash
git clone https://github.com/Shhou/Solar-Flare-Prediction-main.git
cd Solar-Flare-Prediction-main
```

### Step 2: Install Dependencies
```bash
# Install runtime & science dependencies
pip install -r requirements.txt
```

*For minimal dashboard-only execution, only `fastapi` and `uvicorn` are required:*
```bash
pip install fastapi uvicorn
```

### Step 3: Launch the Operations Dashboard

#### Option A: Using the Launcher (Windows)
Double-click `run_dashboard.bat` or run:
```cmd
run_dashboard.bat
```

#### Option B: Direct Python CLI
```bash
python -m uvicorn app.dashboard_server:app --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

---

## 🖥️ Dashboard Features & Tour

1. **🎬 Replay Theater:**
   - Interactive timeline scrubber across 33 held-out test days.
   - Synchronized dual-stream SoLEXS (Soft X-ray) and HEL1OS (Hard X-ray) light curves.
   - Real-time probability climb with automatic **Watch** and **Warning** flags before flare peaks.
   - Exact lead-time badge showing advance warning duration.

2. **📈 Performance & Defensibility:**
   - **Reliability Diagram:** Calibration curves showing raw vs isotonic-calibrated probabilities.
   - **TSS Benchmark Comparison:** Head-to-head comparison with Climatology, Persistence, and TFT.
   - **SHAP Feature Importance:** Physical attribution showing the dominance of Neupert rise derivatives and hardness ratios.

3. **🚨 Operations Console:**
   - Real-time 5-detector state indicators with concurrent voting status.
   - Live Graded Alert Matrix (All-Clear / Watch / Warning).
   - Downstream impact translation:
     - **NavIC / GPS:** L-band ionospheric delay advisory.
     - **Aviation:** Polar route HF radio blackouts (PCA events).
     - **Satellites:** Low-Earth orbit drag and single-event upset warnings.

4. **📚 Catalog & Science Hub:**
   - **Master Flare Catalog:** Paginated, filterable database of 12,858 Aditya-L1 detected flares with GOES cross-matching.
   - **QPP Wavelet Gallery:** Interactive 2D Morlet power spectra with 95% and 99% red-noise confidence contours.
   - **Submission Guide:** Interactive system documentation, architecture diagrams, cost breakdown, and team presentation deck.

---

## 🛡️ Reproducibility & Integrity Guard

This project follows strict scientific reproducibility. All reported numbers are guarded against accidental drift:

```bash
# Run the automated verification guard
python scripts/verify_numbers.py
```
*If any metric or reported number drifts from the verified reports, this script fails loudly.*

```bash
# Run the defensibility verification suite
python scripts/19_defensibility.py
```

---

## 👥 Team & Acknowledgements

### **Team SURYASETU** · *Adamas University*
- **Sulagna Dutta** — *B.Tech, 3rd Year* · Pipeline architecture, core logic & physical modeling.
- **Mitra Sarkar** — *3rd Year* · UI/UX design, physics animations & visual presentation.
- **Shounak Chatterjee** — *B.Tech, 3rd Year* · Fullstack development, FastAPI backend & deployment engineering.

### Acknowledgements
Developed for the **ISRO Bharatiya Antariksh Hackathon 2026** (Problem Statement **PS-15**). We gratefully acknowledge the **Indian Space Research Organisation (ISRO)**, the **Aditya-L1 Mission Team**, and the **SoLEXS / HEL1OS Payload Teams** at URSC and PRL whose ground calibration and in-flight performance publications directly enabled this work.

---

## 📜 Key References
- **Sarwade et al. (2025):** *SoLEXS Ground Calibration and In-flight Performance on Aditya-L1*, Solar Physics / arXiv:2509.26292.
- **HEL1OS Payload Team (2025):** *High Energy L1 Orbiting X-ray Spectrometer on Aditya-L1*, Solar Physics / arXiv:2512.12679.
- **Neupert, W. M. (1968):** *Comparison of Solar X-Ray Line Emission with Microwave Emission During Flares*, Astrophysical Journal.
- **Bloomfield et al. (2012):** *Toward Reliable Benchmarking of Solar Flare Forecasting Methods*, The Astrophysical Journal Letters.
- **Vaughan, S. (2005):** *A simple test for periodicities in red noise*, Astronomy & Astrophysics.
- **Inglis, A. R., Zimovets, I. V., & Dennis, B. R. (2011):** *Instrumental Artifacts in Solar Flare Pulsations*, Astronomy & Astrophysics.

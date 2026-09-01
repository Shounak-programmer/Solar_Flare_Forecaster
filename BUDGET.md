# Aditya-L1 Solar Flare Forecasting — Implementation Budget

**ISRO Hackathon · Development & Deployment Phase · Student Team Proposal**

| | |
|---|---|
| **Budget ceiling** | ₹2,00,000 |
| **Total committed** | ₹1,80,000 |
| **Reserve held (unallocated)** | ₹20,000 |
| **Utilisation** | 90% of ceiling |
| **Planning horizon** | 8-month development + demo window |
| **Currency** | INR (₹) |

---

## Why this budget is small (and defensible)

The system is deliberately cheap to run, so funds cover only the **incremental** cost of a live hackathon deployment — not a re-purchase of sunk compute:

- **Hosting is cheap on purpose.** The dashboard server (`app/dashboard_server.py`) replays **pre-exported JSON** from disk — no models or raw FITS touched at request time — so a single small VM hosts the dashboard *and* the Qdrant/ollama RAG backend.
- **GPU spend is a reserve, not the workhorse.** Primary model training already runs on the team's **owned RTX 5070 Ti**. Cloud GPU is budgeted only for reproducibility runs and the finale TFT sweep.
- **Science data is free.** GOES, SoLEXS, HEL1OS, and SRS catalogs from NASA / NOAA SWPC / ISRO ISSDC cost nothing.
- **Built-in cost escapes (~₹26,000 recoverable).** Local `ollama` replaces the paid LLM API at ₹0, and Qdrant can self-host on the VM if funds tighten.

---

## Allocation summary

| # | Category | Subtotal (₹) | Share |
|---|----------|-------------:|------:|
| 1 | Cloud Server Hosting & Deployment | 34,000 | 18.9% |
| 2 | Cloud GPU Compute — Retraining Reserve | 30,000 | 16.7% |
| 3 | API Subscriptions & Services | 37,000 | 20.6% |
| 4 | Essential Hardware | 57,000 | 31.7% |
| 5 | Contingency | 22,000 | 12.2% |
| | **Total committed** | **1,80,000** | **100%** |
| | Reserve held | 20,000 | — |
| | **Ceiling** | **2,00,000** | — |

---

## 1. Cloud Server Hosting & Deployment — ₹34,000

FastAPI + static frontend is light. A single small VM comfortably hosts the dashboard and the Qdrant/ollama RAG backend for the live demo and judging window.

| Item | Basis | Cost (₹) |
|------|------:|---------:|
| Production VM — 4 vCPU / 8 GB / SSD (dashboard + RAG backend, always-on) | 8 mo × 3,000 | 24,000 |
| Object storage + bandwidth / CDN (serves `dashboard_data` JSON & assets) | 8 mo × 650 | 5,200 |
| Automated backup snapshots (daily, 7-day retention) | 8 mo × 450 | 3,600 |
| Domain name (.in / .org.in) — public demo URL | 1 year | 1,200 |
| SSL certificate (Let's Encrypt, auto-renew) | — | FREE |
| Uptime monitoring (UptimeRobot free tier) | — | FREE |
| **Subtotal** | | **34,000** |

---

## 2. Cloud GPU Compute — Retraining Reserve — ₹30,000

Primary training stays on the owned RTX 5070 Ti. This reserve covers spot-priced cloud GPU for reproducibility runs, the TFT hyperparameter sweep, and the finale re-train.

| Item | Basis | Cost (₹) |
|------|------:|---------:|
| GPU instance (A100 40GB / RTX 4090, spot — RunPod / Vast.ai) | 200 hr × 120 | 24,000 |
| Hyperparameter sweep & finale burst reserve | — | 6,000 |
| **Subtotal** | | **30,000** |

---

## 3. API Subscriptions & Services — ₹37,000

Science data (NASA / NOAA SWPC / ISRO ISSDC) is free. Paid spend is the LLM layer and operator alerting — with local `ollama` as a zero-cost fallback.

| Item | Basis | Cost (₹) |
|------|------:|---------:|
| LLM API credits (Claude) — *optional*; forecast-narrative & report RAG (`ollama` = free fallback) | credits | 22,000 |
| Flare-alert delivery (SMS / email — Twilio / SES) | — | 5,000 |
| Hosted vector DB tier (Qdrant Cloud) — or self-host on VM at ₹0 | 8 mo | 4,000 |
| Data-access & misc API buffer (rate-limit upgrades) | — | 6,000 |
| NASA / NOAA SWPC / ISSDC science data (GOES, SoLEXS, HEL1OS, SRS) | — | FREE |
| GitHub Student Pack + CI minutes (repo, Actions, Pages) | — | FREE |
| **Subtotal** | | **37,000** |

---

## 4. Essential Hardware — ₹57,000

GPU is **already owned (RTX 5070 Ti)** and not re-budgeted. These items remove the real bottlenecks: storing bulky FITS data, holding large parquet in memory, and surviving power cuts mid-train.

| Item | Qty | Cost (₹) |
|------|----:|---------:|
| External NVMe SSD — 2 TB (raw FITS + processed parquet archive) | 1 | 14,000 |
| RAM upgrade to 64 GB (large parquet / FITS held in memory) | 1 kit | 12,000 |
| UPS (line-interactive) — protects multi-hour training runs | 1 | 6,000 |
| Demo / dev monitor — 27" QHD | 1 | 16,000 |
| Peripherals, cables, networking (hub, enclosure, cabling) | — | 9,000 |
| GPU — RTX 5070 Ti (already owned, excluded) | owned | 0 |
| **Subtotal** | | **57,000** |

---

## 5. Contingency — ₹22,000

~12% buffer for cloud cost overruns, USD→INR exchange drift on GPU/API spend, and burst usage during the finale.

| Item | Basis | Cost (₹) |
|------|------:|---------:|
| Contingency & exchange-rate buffer (~12% of committed spend) | — | 22,000 |
| **Subtotal** | | **22,000** |

---

## Grand total

| | ₹ |
|---|---:|
| **Total committed budget** | **1,80,000** |
| Reserve held (unallocated) | 20,000 |
| **Ceiling** | **2,00,000** |
| **Headroom** | **20,000** |

---

## Decisions to make before submitting

1. **Horizon** — recurring cloud costs assume an **8-month** dev+demo window. A shorter 3–4 month phase cuts hosting + GPU by ~₹20,000–25,000.
2. **LLM API** — the ₹22,000 Claude credits are *optional*. Committing to local `ollama` only drops the total to ~₹1,58,000.
3. **Vector DB** — self-hosting Qdrant on the VM saves the ₹4,000 hosted-tier line.

> Figures are planning estimates in INR for the development & deployment phase. Cloud line-items are pay-as-you-go and scale down with lower usage. Hardware is one-time capital that outlives the hackathon. Reserve is released only on need.

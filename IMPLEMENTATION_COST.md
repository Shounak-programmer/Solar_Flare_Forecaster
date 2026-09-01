# Implementation Cost Estimate — Development Roadmap

*Cost to implement the Phase A / B / C roadmap in [`DEVELOPMENT_APPROACH.md`](DEVELOPMENT_APPROACH.md). The dominant cost is **engineering time**, not cash — most cash items are already covered by [`BUDGET.md`](BUDGET.md).*

---

## Assumptions

- **Team:** 1 capable ML/data engineer (already familiar with this codebase). A 2-person team roughly halves calendar time.
- **1 person-week = 40 focused hours.** Estimates include normal debugging but *not* open-ended research dead-ends; experiment-heavy tasks carry a buffer.
- **Hardware is already owned** (RTX 5070 Ti, 64 GB RAM, NVMe, UPS — per `BUDGET.md` §4). Not re-counted here.
- **Science data is free** (GOES, SoLEXS, HEL1OS, SRS, SDO/HMI SHARP via JSOC, NOAA SWPC).
- **Labour monetisation** (optional column) uses a blended student/junior-contractor rate of **₹40,000/person-month** (~₹10,000/week). For a student team building on their own time, treat the cash column as the real out-of-pocket and effort as sweat equity.

---

## Phase A — Harden & de-risk

| Task | Effort | Cash |
|---|---:|---:|
| Config management (kill hardcoded `I:/` paths + ~20 thresholds → `config.yaml` + pydantic-settings) | 3 d | ₹0 |
| Compute dashboard metrics at export (remove hand-entered per-class/all-clear/TFT numbers) | 2 d | ₹0 |
| Schema contract (pyarrow/pydantic enforced on parquet load) | 3 d | ₹0 |
| Bootstrap confidence intervals on all reported TSS/POD/recall | 2 d | ₹0 |
| Seeds + reproducibility + one-command pipeline runner | 2 d | ₹0 |
| Golden-file tests (3 X-anchors end-to-end) + pytest on `src/` + GitHub Actions CI | 4 d | ₹0 (free tier) |
| AR-partitioned evaluation reported alongside temporal split | 2 d | ₹0 |
| **Subtotal** | **~18 d ≈ 3.5 wk** | **₹0** |

*Near-zero cash; pure engineering. Highest trust-per-rupee — do first.*

---

## Phase B — Close the forecasting gap

| Task | Effort | Cash |
|---|---:|---:|
| Foundation TS model integration (Chronos / Moirai2 / TimesFM) + data adapter for 1-min streams | 6 d | ₹0 |
| Proper GPU hyperparameter sweep + honest TFT rematch (on owned RTX 5070 Ti; cloud burst only if needed) | 5 d | ₹15,000–25,000 (cloud GPU reserve, *already in BUDGET §2*) |
| SoLEXS deadtime correction (Lambert-W paralyzable inversion, τ=13.65 µs) + timing-chain cross-check + peak-flux regression | 6 d | ₹0 |
| Dual AR/temporal eval harness + writeup | 3 d | ₹0 |
| **Subtotal** | **~20 d ≈ 4 wk** *(5–6 wk with experiment iteration)* | **₹0–25,000** |

*Cash is the cloud-GPU spot reserve, and only if the owned card can't hold the sweep — it usually can.*

---

## Phase C — Expand capability & operationalise

| Task | Effort | Cash (mostly pre-budgeted) |
|---|---:|---:|
| SDO/HMI SHARP feature pipeline (JSOC fetch, AR matching, feature build) + 6/12/24 h targets + retrain | 10 d | ₹0 (data free) |
| Real-time inference service (streaming ingest, incremental features, `/api/live`) | 8 d | hosting: ₹24,000/8 mo *(BUDGET §1)* |
| Alert delivery (Twilio/SES gating on Warning operating point) | 3 d | ₹5,000 *(BUDGET §3)* |
| RAG/LLM operator-briefing layer (Qdrant index + ollama free / Claude API + grounding) | 8 d | ₹0 (ollama) or ₹22,000 (Claude, *BUDGET §3*) |
| CCMC Flare Scoreboard submission (format adapter + ongoing) | 3 d | ₹0 |
| **Subtotal** | **~32 d ≈ 6.5 wk** *(8–10 wk realistic)* | **₹29,000–51,000** (all within existing budget) |

---

## Totals

| | Effort (1 dev) | Calendar (1 dev) | Calendar (2 devs) | New cash |
|---|---:|---:|---:|---:|
| Phase A | 3.5 wk | ~1 month | ~2 wk | ₹0 |
| Phase B | 4 wk (5–6 w/ iteration) | ~1.5 months | ~3–4 wk | ₹0–25,000 |
| Phase C | 6.5 wk (8–10 w/ iteration) | ~2.5 months | ~5–6 wk | ₹29,000–51,000 |
| **All three** | **~14 person-weeks core** (~18–20 with buffers) | **~4–5 months** | **~2.5–3 months** | **₹29,000–76,000** |

**Monetised labour** (if you had to pay for it at ₹40k/person-month): **~₹1,40,000–2,00,000** for the full roadmap solo. For a student team on own time, this is sweat equity ≈ ₹0 out of pocket.

---

## Reconciliation with the existing ₹2,00,000 budget

The roadmap demands **no new budget line.** Every cash item above maps to an allocation already in `BUDGET.md`:

| Roadmap cash need | Existing BUDGET.md line | Allocated |
|---|---|---:|
| Cloud GPU sweep (Phase B) | §2 GPU retraining reserve | ₹30,000 |
| Always-on VM for live inference (Phase C) | §1 hosting | ₹24,000 |
| Alert SMS/email (Phase C) | §3 Twilio/SES | ₹5,000 |
| LLM API for RAG (Phase C, optional) | §3 Claude credits (ollama = ₹0 fallback) | ₹22,000 |
| Vector DB | §3 Qdrant (or self-host ₹0) | ₹4,000 |

**Bottom line:** the roadmap costs roughly **14 person-weeks of focused engineering (~4–5 months solo, ~2.5–3 months for a pair)** and **₹0 in *new* cash** — the ~₹30k–76k it consumes is already sitting in the committed budget, well under the ₹20,000 reserve plus existing headroom.

### Cheapest high-value slice
If time/money is tight, **Phase A alone (~3.5 weeks, ₹0)** makes the existing results portable, reproducible, and trustworthy — and fixes the hardcoded-metrics integrity issue. It is the single best return and a prerequisite for honestly claiming any later improvement.

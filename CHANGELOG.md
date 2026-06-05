# Changelog

All significant milestones, engine capabilities, and research findings are recorded here.
Entries are reverse-chronological. Research verdicts link to full reports in `docs/research/`.

---

## [Unreleased]

### In progress
- D-188 event-confluence forward measurement (infrastructure live since 2026-06-01;
  verdict pending sample accumulation)

---

## 2026-06 — Validation engine hardened; research axes closed

### Engine
- **Mod-C (intra-regime time-holdout):** `SplitMode.TIME_HOLDOUT` added — train/holdout
  split within one regime with construction-window embargo. Closes the forward-persistence
  measurement gap. (PR #208, RR-Y1-010)
- **Verdict-confidence qualifier:** every conjugate result carries `agreement_confidence`
  (HIGH / LOW / CONFOUNDED). CONFOUNDED fires when the eval window is single-regime or a
  shared common-factor is detected. Prevents silent false-positive verdicts. (RR-Y1-009)
- **Iteration lockbox:** single-shot held-out consumption enforced with SHA-256 fingerprint.
  Prevents inadvertent repeated scoring of a sealed holdout set. (RR-Y1-009)
- **Engine operator guide:** `docs/engine/OPERATOR_GUIDE.md` — step-by-step signal
  attachment, Stage-0 protocol, output-vector interpretation.
- **Red-team validation:** engine's first real-data exam (RR-Y1-008) confirmed all three
  structural properties on live BIST data. Surfaced the liquid-universe breadth constraint
  (~38 names at 10M TRY ADV + 7-year continuity): documented market property, not a
  methodology defect.

### Research — closed threads
| Report | Verdict |
|--------|---------|
| [D-208](docs/research/D-208-rapor.md) hi52 re-test (corrected cost) | TRADEABLE-NO — significance wall; NW-\|t\| = 1.70. hi52 thread closed definitively. |
| [D-209](docs/research/D-209-rapor.md) H2b dividend run-up (corrected cost) | TRADEABLE-NO — liquid NW-t = 0.61; signal absent in deployable universe. H2b closed. |
| [D-213](docs/research/D-213-rapor.md) Ex-ante real rate → XU100 | TRADEABLE-NO — correct sign, lag-1 NW-t = −1.82 (sub-2); AR(1) = 0.986 Stambaugh bias. |
| [D-211](docs/research/D-211-rapor.md) Foreign flow → BIST index | TRADEABLE-NO — lag-0 co-movement non-deployable; knowable lag-2 form: sign reversal. |

### Cost model
- **D-207 realistic-cost recalibration:** bloated roll-spread model corrected (~12–20×
  de-inflation). Quoted EOD spread ~flat ~11 bp across BIST liquidity spectrum; microcap
  cost wall = Kyle impact, not spread. Fidelity 8/8 mega stocks in [7,35] bp band.

---

## 2026-05 — Clean universe; cross-sectional factor measurement

### Data
- **D-202 clean universe:** survivorship-bias-clean BIST daily price panel (681 symbols,
  1,848 days, delisted included). Hybrid four-source construction with rights/TERP-adjusted
  corporate actions and +/−10% clip. Replaces bozuk D-200 universe.

### Research — cross-sectional factors
| Report | Verdict |
|--------|---------|
| [D-203](docs/research/D-203-rapor.md) Value + EDGE-2 + hi52 (clean universe) | VALUE = SERAP (gate-2 fail, illiquid-biased). EDGE-2 = genuine, post-2022 narrowing. hi52 = strongest / most regime-resilient. |
| [D-204](docs/research/D-204-rapor.md) hi52 stress-test: realistic cost + OOS | TRADEABLE-NO — round-trip ~340 bp > breakeven ~302 bp at ~88%/month turnover. |
| [D-205](docs/research/D-205-rapor.md) hi52 liquid-first (ADV ≥ 10M TRY, N≤3) | TRADEABLE-NO — cost ratio only modestly improved; EW_FULL_LIQUID bar uncleared. |
| [D-206](docs/research/D-206-rapor.md) NAV discount Z-score mean reversion | SERAP — pooled FE-within beta wrong sign (−0.0185); Driscoll-Kraay \|t\| = −0.81. |
| [NRR-007](docs/research/NRR-007-rapor.md) lowvol63 isolated | ELIMINATED — liquidity premium, not anomaly; gate-4 collapse in liquid universe. |
| [NRR-008](docs/research/NRR-008-rapor.md) Value regime-gated (3rd and final) | ELIMINATED — regime gating did not rescue value. Value thread closed (N≤3 rule). |
| [D-Y1-001](docs/research/D-Y1-001-rapor.md) Value regime-resilience | FRAGILE / REGIME-DEPENDENT — P/B passes 4/4 periods mechanically; E/P fails; OOS collapses. |

### Research — timing signals
| Report | Verdict |
|--------|---------|
| [D-185](docs/research/D-185-rapor.md) Trend motor | DISCREDITED (DEC-044) — gross DD ~99% artefact. |
| [D-186](docs/research/D-186-rapor.md) Trend entry-timing | Entry-timing does not beat fair null at 95th pctile. |
| [D-187](docs/research/D-187-rapor.md) Exposure backtest / honest benchmark | Active timing real −5.7%; random-null pctile 0.17. Static barbell superior. |

### Engine — foundation
- **RR-Y1-005 validation engine:** Mod-A (name-split conjugate) + Mod-B (temporal CPCV)
  implemented. Full statistical stack: rank-IC / IC-IR, Newey-West HAC, CSCV-PBO,
  Deflated Sharpe, market-neutral residualization, benchmark floor.
- **Stage-0 pre-registration enforcer:** engine refuses to run without frozen Stage-0 JSON.
- **Test suite:** 2,015 tests across 127 files, zero-regression CI policy established.
- **CI tiers:** architecture → integration → lint → full regression → security.

---

## 2026-04 and earlier — Infrastructure and live system

- **Signal engine (Phase 4.5):** 5-layer composite (L1 technical, L2 macro, L3 KAP,
  L4 sentiment, L5 smart-money); dynamic normalizer Σ ∈ [0.78, 1.00] (DEC-009).
- **Macro gate:** crisis-only hard exits (VIX > 35 / USDTRY > 3%); CDS percentile
  overlay (DEC-017).
- **Daily production pipeline:** GitHub Actions cron 18:30 IST; IC history persisted
  to parquet; cloud deployment active (D-152).
- **Statistical validation stack:** DSR / PBO / CPCV framework (D-150a-e). Real run
  scheduled Kasım 2026.
- **Track 1 (smart-passive anchor):** deployed and delivering positive real returns
  above deposit-rate benchmark.

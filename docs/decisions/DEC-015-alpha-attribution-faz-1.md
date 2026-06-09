# DEC-015 — Alpha Attribution Infrastructure (Faz 1)

**Status:** Implemented
**Date:** 2026-05-20
**Directive:** D-107
**SPEC:** `SPEC_ALPHA_INFRASTRUCTURE_1`
**Area:** Signal Architecture / Analytics

---

## Context

System lagged BIST100 by ~33pp YTD in a bull regime (system +1.55% vs BIST +29.9%).
Before optimizing `MASTER_WEIGHTS` (Faz 3), we must **measure** layer-by-layer alpha:
- per-layer Information Coefficient (Spearman rank IC)
- IR, t-stat, p-value with multiple-testing awareness
- Brinson-Fachler sector attribution
- Leave-One-Out layer marginal contribution

Faz 1 builds the measurement layer **only**. Engine behaviour unchanged.

---

## Decision

Implement an Alpha Attribution infrastructure consisting of:

1. **Signal log** (`src/data/signal_logger.py`) — daily per-symbol Hive-partitioned
   parquet capturing all 6 layer scores + composite + conviction + context
   (regime, volatility regime, liquidity tier) + `as_of_timestamp` for lookahead audit.

2. **Return filler** (same module) — backfills T+1/T+5/T+20/T+60 forward returns
   at horizon expiry using BIST trading-day calendar (skips holidays + weekends).

3. **Universe snapshot** (`src/data/universe_snapshot.py`) — month-end BIST100
   constituent list keyed by year-month, used for survivorship-free IC analysis.
   Faz 1 captures only current constituents (yfinance + manual BIST30 list);
   Faz 1.5 will manually import 2023-2026 historical CSVs; Faz 2 connects MKK API.

4. **IC calculator** (`src/analytics/ic_calculator.py`) — daily cross-sectional
   Spearman rank IC + IR + t-stat + p-value, sliced by horizon × universe × regime.
   Optional alphalens-reloaded integration behind `try/except import`.

5. **Brinson-Fachler attribution** (`src/analytics/brinson_attribution.py`) —
   sector-level allocation/selection/interaction effects; Carino (1999) geometric
   linking for multi-period. Uses existing `get_sector()` from
   `src/data/database.py`; no SECTOR_SYMBOL_MAP duplication.

6. **Layer attribution** (`src/analytics/layer_attribution.py`) — Leave-One-Out
   marginal IC per layer; optional weekly-batch Shapley decomposition.
   Layer weights imported from `MASTER_WEIGHTS` (PROJECT_GUIDE.md compliance — no
   hardcoded weight dict).

7. **Tier-1 dashboard** (`src/reporting/ic_dashboard.py`) — CLI summary +
   JSON dump (`data/analytics/ic_report_<date>.json`). Renders empty-state
   gracefully when no data has accumulated yet.

8. **Daily hook** in `scripts/daily_update.py` — per-symbol `compute_signal()`
   loop wraps the signal log writer + return filler. Pure-additive (try/except
   per symbol; logging failures never break the briefing pipeline).

9. **Constants** appended to `src/signals/thresholds.py` (IC horizons, rolling
   windows, investable thresholds, paths, volatility regime cutoffs) —
   single source of truth, no magic numbers in analytics/ code.

---

## SPEC reconciliation (5 reality gaps closed)

| Gap | SPEC assumption | Reality | Decision |
|---|---|---|---|
| Signal loop | exists in `daily_update.py` | absent | added as part of D-107 |
| Regime labels | `Bull/Transition/Bear` | `BULL/NEUTRAL/BEAR` | SPEC updated to match code |
| `scipy` | optional | required for `spearmanr` + `t.cdf` | `scipy>=1.11` added |
| `SECTOR_SYMBOL_MAP` | in `thresholds.py` | not present | use existing `get_sector()` |
| Position sizer dict | already a dict | per-call `SizingDecision` | wrap with aggregator |

---

## Out of scope (deferred)

- **VIOP wiring into `MASTER_WEIGHTS`** — VIOP gets logged here, but stays at
  weight=0.0 until IC t-stat ≥ 2.0 is observed (RESEARCH-013).
- **Foreign flow migration to L2** — Faz 1 logs `l5_foreign_flow_raw` baseline only;
  the L2 migration lands in D-108 (RESEARCH-014).
- **`MASTER_WEIGHTS` rebalance** — Faz 3, after ≥1 quarter of clean IC data.
- **MKK API / true historical BIST100** — Faz 1.5/2.
- **Türkçe FinBERT / NLP reform** — RESEARCH-016, separate SPEC.

---

## Survivorship bias disclosure

Faz 1 universe is yfinance-derived (current constituents only). Estimated bias
is +0.003 to +0.005 absolute IC. This is documented in every IC report header
and is acceptable for Faz 1 directional measurement. Faz 1.5/2 close this gap.

---

## Verification

- 23 new tests (`test_signal_logger.py`, `test_universe_snapshot.py`,
  `test_ic_calculator.py`, `test_brinson.py`, `test_layer_attribution.py`).
- Architecture tests green — no hardcoded thresholds in new `src/analytics/`
  or `src/reporting/` modules.
- Empty-state CLI smoke: `python -m src.reporting.ic_dashboard --tier 1`
  renders NO-DATA rows and writes a valid JSON.

---

## Affected files

- `src/signals/thresholds.py` (+IC block, 14 constants)
- `requirements.txt` (+`scipy>=1.11`)
- `src/analytics/__init__.py`, `ic_calculator.py`, `brinson_attribution.py`,
  `layer_attribution.py` (new)
- `src/reporting/__init__.py`, `ic_dashboard.py` (new)
- `src/data/signal_logger.py`, `universe_snapshot.py` (new)
- `scripts/daily_update.py` (+`_write_signal_logs_d107()` hook,
  +`_compute_position_weights_d107()` aggregator)
- `tests/test_signal_logger.py`, `test_universe_snapshot.py`,
  `test_ic_calculator.py`, `test_brinson.py`, `test_layer_attribution.py` (new)

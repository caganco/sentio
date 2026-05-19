# BIST OS — Algorithmic Trading System

A production-ready quantitative signal engine for Borsa İstanbul (BIST), built on the Druckenmiller macro-first hierarchy. The system combines six signal layers — technical, macro, corporate disclosure, sentiment, smart money, and risk — into a conviction-weighted composite that drives position sizing and staged exit management. Phase 4.5 is complete with 742 tests passing; the project is in active data collection for the L5 smart money layer.

---

## Architecture

```
─────────────────────────────────────────────────────────────────
│                     DATA SOURCES                                │
│  yfinance · TCMB EVDS · KAP API · CDS proxy · İş Yatırım       │
──────────────────────┬──────────────────────────────────────────
                       │
──────────────────────┼──────────────────────────────────────────
│                  SIGNAL ENGINE  (src/signals/engine.py)         │
│                                                                 │
│  L1 Technical  ──0.25───                                        │
│  L2 Macro      ──0.20───┤                                        │
│  L3 KAP        ──0.30───┼──► Weighted Sum (0–100)                │
│  L4 Sentiment  ──0.12×conf (SUSPENDED)                          │
│  L5 Smart Money──0.10×conf (RAMP-UP)                            │
│  L6 Risk/Kelly ──0.03───                                        │
│                                                                 │
│  Dynamic normalizer Σ ∈ [0.78, 1.00]  ·  DEC-009               │
──────────────────────┬──────────────────────────────────────────
                       │
──────────────────────┼──────────────────────────────────────────
│             CONVICTION VALIDATOR  (src/signals/conviction_validator.py) │
│                                                                 │
│  score = (composite / 100) × macro_multiplier                  │
│  ≥ 0.68 → BUY-STRONG  ·  0.55–0.67 → BUY-MEDIUM  ·  < 0.55 → WATCH │
──────────────────────┬──────────────────────────────────────────
                       │
──────────────────────┼──────────────────────────────────────────
│             MACRO REGIME GATE  (src/signals/macro_regime_gate.py) │
│                                                                 │
│  BULL  (L2 ≥ 60) → 1.0×  ·  NEUTRAL (45–59) → 0.8×  ·  BEAR → 0.0× │
──────────────────────┬──────────────────────────────────────────
                       │
──────────────────────┼──────────────────────────────────────────
│             POSITION SIZER  (src/risk/position_sizer_v2.py)     │
│                                                                 │
│  BUY-STRONG → 32.5% base  ·  BUY-MEDIUM → 17.5% base           │
│  Caps: max 4 BUY-STRONG · max 2 BUY-MEDIUM · max 30% per sector │
──────────────────────┬──────────────────────────────────────────
                       │
──────────────────────┼──────────────────────────────────────────
│             STAGED EXIT  (src/order_engine/staged_exit_manager.py) │
│                                                                 │
│  TP1 50% · TP2 30% · TP3 20% (trailing)  ·  Stop-loss −8%      │
─────────────────────────────────────────────────────────────────
```

---

## Signal Layers

| Layer | Weight | Status | Description |
|-------|--------|--------|-------------|
| **L1 Technical** | 0.25 | ✅ LIVE | RSI, moving averages, volume analysis via yfinance |
| **L2 Macro** | 0.20 | ✅ LIVE | TCMB policy rate, USD/TRY, CDS spread, DXY, foreign flows |
| **L3 KAP** | 0.30 | ✅ LIVE | Corporate disclosure event scoring (dividends, capital increases, material events) |
| **L4 Sentiment** | 0.12 × conf | ⏸ Suspended | FinBERT/VADER pipeline ready; Turkish news source pending |
| **L5 Smart Money** | 0.10 × conf | 🔄 Ramp-up | Foreign investor ratio + short interest; data collection active |
| **L6 Risk/Kelly** | 0.03 | ✅ LIVE | Kelly criterion-based position guard, circuit breaker |

Layers L4 and L5 use confidence-scaled weighting: when confidence is 0, effective weight is 0 and the dynamic normalizer adjusts automatically (floor 0.78). See [DEC-009](docs/decisions/DEC-009-phase-45-normalizer-derivation.md).

---

## Conviction Framework

The conviction system sits above the raw signal engine, translating the 0–100 composite into actionable tiers with macro context applied.

```
conviction_score = min(1.0, (composite / 100) × macro_multiplier)

macro_multiplier:
  L2 ≥ 65  →  ×1.2  (bullish amplification)
  L2 ≥ 50  →  ×1.0  (neutral)
  L2 < 50  →  ×0.85 (bearish dampening)

tiers:
  ≥ 0.68  →  BUY-STRONG   (32.5% base allocation)
  ≥ 0.55  →  BUY-MEDIUM   (17.5% base allocation)
  < 0.55  →  WATCH
```

**Macro Regime Gate** (`macro_regime_gate.py`) applies a second scaling pass before sizing. BEAR regime (L2 < 45) blocks all new entries. This gate is a Python hard-constraint — not overridable by the LLM Strategist layer. See [DEC-010](docs/decisions/DEC-010-strategist-advisory-boundary.md).

**Staged Exit Ladder** enforces disciplined profit-taking:
- **TP1** → 50% at first technical resistance (ATR × 1.5 fallback)
- **TP2** → 30% at Fibonacci 0.618 extension (ATR × 3.0 fallback)
- **TP3** → 20% trailing stop, tightness varies by macro regime (2–3%)
- **Stop-loss** → −8% hard floor with approach warning at −5.2%

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Core language | Python 3.12 |
| Data | pandas 2.2.2, numpy 1.26.4, yfinance |
| Testing | pytest — 742 tests, 1 skipped |
| Configuration | Single-source constants in `src/signals/thresholds.py` |
| LLM Strategist | Anthropic Claude API (advisory narrative only) |
| Data sources | KAP API, TCMB EVDS, İş Yatırım screener, yfinance |
| Architecture safety | `tests/test_architecture.py` — design invariants enforced |
| CI/CD | GitHub Actions — 4-job pipeline |
| Pre-commit | Tier 1+2 + ruff hooks |

---

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1–3 | ✅ Complete | Technical + macro + KAP layers |
| Phase 4 | ✅ Complete | KAP integration, CDS fallback, foreign flows |
| **Phase 4.5** | ✅ **Complete** | Conviction framework, macro gate, staged exits, L5 foundation |
| Phase 5 | 🔄 Planned | Broker API integration, slippage model, social media sentiment (L4 extension) |

**Current state:** 742 tests passing (zero regression). L5 smart money layer in data collection — foreign ratio data accumulating; full activation at ~Day 20.

---

## Setup

```bash
git clone https://github.com/<user>/bist-trading-system
cd bist-trading-system

pip install -r requirements.txt

# Copy and fill in API keys
cp .env.example .env

# Run test suite
python -m pytest tests/ -q --tb=short
# Expected: 742 passed, 1 skipped

# Run daily update
python scripts/daily_update.py
```

**Required environment variables** (see `.env.example`):
- `ANTHROPIC_API_KEY` — Strategist narrative layer
- `EVDS_API_KEY` — TCMB macro data feed

---

## Repository Structure

```
bist-trading-system/
├── src/
│   ├── signals/          # Core engine + 6 signal layers
│   │   ├── engine.py     # Stateless compute_signal() entry point
│   │   ├── thresholds.py # All constants — single source of truth
│   │   ├── layers/       # L1–L6 layer implementations
│   │   ├── conviction_validator.py
│   │   └── macro_regime_gate.py
│   ├── risk/             # Position sizing, Kelly, drawdown, circuit breaker
│   ├── order_engine/     # Staged exit manager
│   ├── backtest/         # Simulation engine + metrics
│   ├── data/             # KAP, macro, smart money data clients
│   └── utils/            # Config, logging, OS state manager
├── tests/                # 742 tests (unit + integration + architecture)
├── docs/
│   ├── decisions/        # DEC-001 — DEC-010 architecture decision records
│   ├── ARCHITECTURE.md   # Pipeline diagrams
│   ├── DEPENDENCY_MAP.md # Module dependency graph
│   └── DECISIONS.md      # Decision index
├── agents/               # Orchestrator, Analyst, Auditor agent wrappers
├── scripts/              # daily_update.py, backtest runners
└── config.yaml           # Portfolio universe, scanner parameters
```

---

## Design Principles

**Druckenmiller Macro-First Hierarchy:** No individual stock signal can override a BEAR macro regime. Conviction scoring is a derived layer — the quantitative composite always runs first.

**Single Source of Truth:** Every threshold constant lives in `src/signals/thresholds.py`. Architecture tests (`tests/test_architecture.py`) enforce zero hardcoded values in the signal engine.

**LLM Advisory Boundary:** The Claude Strategist layer produces human-readable narrative only. It has no write path to signal computation, conviction scoring, or order execution. See [DEC-010](docs/decisions/DEC-010-strategist-advisory-boundary.md).

**Graceful Layer Degradation:** When L4 or L5 data is unavailable, confidence drops to 0, effective weight drops to 0, and the dynamic normalizer adjusts. No fallback scores inflate the composite.

---

## Decision Records

Architecture decisions are documented in `docs/decisions/` (DEC-001 through DEC-010). Key decisions:

- [DEC-007](docs/decisions/DEC-007.md) — Ruthless Alpha: conviction-based sizing philosophy
- [DEC-008](docs/decisions/DEC-008-verda-independence.md) — L5 VERDA independence
- [DEC-009](docs/decisions/DEC-009-phase-45-normalizer-derivation.md) — Dynamic normalizer derivation
- [DEC-010](docs/decisions/DEC-010-strategist-advisory-boundary.md) — LLM advisory boundary

---

## License

[MIT](LICENSE)

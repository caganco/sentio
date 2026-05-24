# BIST OS — Algorithmic Trading System

**Institutional-grade algorithmic trading OS for Borsa İstanbul (BIST).**
Built on the Druckenmiller macro-first methodology: **Macro → Sector → Stock → Timing.**

A stateless, six-layer quantitative signal engine that fuses technical, macro,
corporate-disclosure, sentiment, smart-money and risk signals into a single
conviction-weighted composite. Conviction drives position sizing through a macro
regime gate and a staged-exit ladder, and every run emits an auditable daily
report. The codebase is built around a single source of truth for all constants,
architecture-invariant tests, and a documented decision-record (ADR) system.

> Phase 4.5 complete · 1,150+ automated tests, green CI · L5 smart-money layer in
> active data collection.

---

## Architecture

```
   DATA SOURCES
   yfinance · TCMB EVDS · KAP · CDS proxy · İş Yatırım · BIST Datastore
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  SIGNAL ENGINE  —  compute_signal()  (stateless, 0–100)      │
 │  L1 Technical · L2 Macro · L3 KAP · L4 Sentiment ·           │
 │  L5 Smart Money · L6 Risk   →  weighted composite            │
 └─────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  CONVICTION VALIDATOR   score = (composite/100) × macro_mult │
 │  ≥0.68 BUY-STRONG · 0.55–0.67 BUY-MEDIUM · <0.55 WATCH        │
 └─────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  MACRO REGIME GATE   L2-step soft scaling × CDS overlay       │
 │  size multiplier 0.3 → 1.0 ; crisis hard-exits force 0×       │
 └─────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  POSITION SIZER   base × macro_scaling × conviction           │
 │  BUY-STRONG 32.5% · BUY-MEDIUM 17.5% · sector cap 40%         │
 └─────────────────────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  STAGED EXIT + DAILY REPORT                                   │
 │  TP1 50% · TP2 30% · TP3 20% trailing · stop −8%             │
 │  → reports/report_YYYY-MM-DD.md  (macro · portfolio · notes)  │
 └─────────────────────────────────────────────────────────────┘
```

---

## Signal Layers

| Layer | Weight | Status | Description |
|-------|--------|--------|-------------|
| **L1 Technical** | 0.25 | ✅ Live | RSI, moving-average stack, volume surge, 52-week proximity (yfinance) |
| **L2 Macro** | 0.20 | ✅ Live | TCMB policy rate, USD/TRY, CDS spread, DXY, weekly net foreign flow |
| **L3 KAP** | 0.30 | ✅ Live | Corporate-disclosure event scoring with event-triggered weight boost |
| **L4 Sentiment** | 0.12 × conf | ⏸ Suspended | FinBERT/NLTK pipeline ready; Turkish news ingestion pending |
| **L5 Smart Money** | 0.10 × conf | 🔄 Ramp-up | Foreign-investor ratio, custody flows, short interest; data accumulating |
| **L6 Risk** | 0.03 | ✅ Live | Volatility/regime risk guard, circuit breaker |

Layers L4 and L5 use **confidence-scaled weighting**: when data is unavailable,
confidence drops to 0, effective weight drops to 0, and a dynamic normalizer
(effective Σ ∈ [0.78, 1.00]) rebalances automatically — no fallback score ever
inflates the composite. See [DEC-009](docs/decisions/DEC-009-phase-45-normalizer-derivation.md).

---

## Conviction, Gate & Sizing

```
conviction_score = min(1.0, (composite / 100) × macro_multiplier)

macro_multiplier:   L2 ≥ 65 → ×1.2   ·   L2 ≥ 50 → ×1.0   ·   L2 < 50 → ×0.85
tiers:              ≥0.68 BUY-STRONG ·  ≥0.55 BUY-MEDIUM  ·  <0.55 WATCH
```

**Macro Regime Gate** translates the L2 macro score into a position-size
multiplier with a soft floor — macro weakness *scales down* exposure instead of
fully blocking it (≈0.3× at the low end, up to 1.0× in a bullish regime), with a
CDS-percentile overlay dampening further in sovereign stress. **Hard exits**
(CDS ≥ 600 bps, USD/TRY shock, portfolio drawdown ≥ 15%) still force 0×. The gate
is a Python hard-constraint — never overridable by the LLM Strategist layer
([DEC-010](docs/decisions/DEC-010-strategist-advisory-boundary.md), [DEC-017](docs/decisions/DEC-017-macro-gate-softening.md)).

**Staged Exit Ladder** enforces disciplined profit-taking: TP1 50% at first
resistance (ATR×1.5 fallback), TP2 30% at Fibonacci 0.618 (ATR×3.0 fallback),
TP3 20% on a regime-aware trailing stop, with a −8% hard stop-loss and an
approach warning before it is hit.

---

## Sample Output

`scripts/daily_update.py` writes a Markdown report per run. *Illustrative
snippet (mock data — the repository ships with no real portfolio or keys):*

```markdown
# Daily Market Report — 2026-05-22

## Macro Snapshot
- **Regime:** NEUTRAL
- **Environment Score:** 54.3
- **USD/TRY:** 33.18   **BRENT:** 81.4   **VIX:** 17.9   **BIST100:** 10,840

## Portfolio
| Ticker | Sector  | P&L% | RSI | Alerts                |
|--------|---------|------|-----|-----------------------|
| AKBNK  | Banking | +5.2 | 61  | —                     |
| EREGL  | Steel   | -3.1 | 38  | Approaching stop-loss |

---
## Strategist Notes
Macro regime is neutral (L2 54): banking momentum intact while steel lags on
soft global demand. AKBNK retains BUY-MEDIUM conviction; EREGL is on watch as
price nears its −8% stop. No new BUY-STRONG entries while the macro gate caps
sizing at 0.8×.
```

---

## Tech Stack

| Area | Technology |
|------|------------|
| Language | Python 3.11+ |
| Data / numerics | pandas, numpy, scipy, pyarrow |
| Market & macro data | yfinance, KAP client, TCMB EVDS, İş Yatırım, BIST Datastore |
| Regime modeling | hmmlearn, scikit-learn (HMM regime-conditional weights) |
| Scraping / parsing | BeautifulSoup, pdfplumber, Playwright |
| NLP | NLTK / FinBERT (sentiment layer) |
| LLM Strategist | Anthropic Claude API (advisory narrative only) |
| Testing | pytest — 1,150+ tests (unit · integration · architecture invariants) |
| CI/CD | GitHub Actions — architecture → integration → lint → full-regression |
| Quality gates | ruff lint + pre-commit (Tier-1/2 tests) on every commit |

---

## Setup

```bash
git clone https://github.com/raypun78/bist-trading-system
cd bist-trading-system

pip install -r requirements.txt

# Copy the template and fill in keys (all optional for offline test runs)
cp .env.example .env

# Run the full test suite
python -m pytest tests/ -q --tb=short
# Expected: all tests pass (2 intentionally skipped)

# Generate a daily report (scans the universe, writes reports/report_<date>.md)
python scripts/daily_update.py --scan --generate-report
```

**Environment variables** (see `.env.example`):

- `EVDS_API_KEY` — TCMB macro data feed ([free registration](https://evds2.tcmb.gov.tr))
- `FMP_API_KEY` — supplementary market data
- `ANTHROPIC_API_KEY` (or `CLAUDE_API_KEY`) — optional; enables the Strategist narrative

The engine and test suite run fully offline; keys are only needed for live data
pulls and the optional LLM narrative.

---

## Repository Structure

```
bist-trading-system/
├── src/
│   ├── signals/              # Core engine + six signal layers
│   │   ├── engine.py         # Stateless compute_signal() entry point
│   │   ├── thresholds.py     # All constants — single source of truth
│   │   ├── conviction_validator.py
│   │   ├── macro_regime_gate.py
│   │   └── layers/           # L1–L6 layer implementations
│   ├── risk/                 # Position sizing, drawdown, circuit breaker
│   ├── order_engine/         # Staged exit manager
│   ├── backtest/             # Simulation engine + metrics
│   ├── data/                 # KAP, macro, smart-money data clients
│   └── utils/                # Config, logging, weight validator, OS state
├── tests/                    # 1,150+ tests (unit · integration · architecture)
├── docs/
│   ├── decisions/            # ADRs: DEC-001 … DEC-017
│   └── DECISIONS.md           # Decision index
├── scripts/                  # daily_update.py, loaders, runners
└── config.yaml               # Universe + scanner parameters
```

---

## Design Principles

- **Macro-first hierarchy** — no single-stock signal overrides a weak macro
  regime; the quantitative composite always runs before any narrative.
- **Single source of truth** — every threshold lives in
  `src/signals/thresholds.py`; `tests/test_architecture.py` fails the build on
  any hardcoded constant in the engine.
- **LLM advisory boundary** — the Claude Strategist produces human-readable
  narrative only, with no write path to signals, conviction, or execution.
- **Graceful degradation** — missing layer data ⇒ confidence 0 ⇒ weight 0 ⇒
  normalizer rebalances; partial data never fabricates conviction.

---

## Decision Records

Architecture decisions are tracked as ADRs in [`docs/decisions/`](docs/decisions/)
(DEC-001 … DEC-017). Highlights:

- [DEC-007](docs/decisions/DEC-007.md) — Ruthless Alpha: conviction-based sizing philosophy
- [DEC-009](docs/decisions/DEC-009-phase-45-normalizer-derivation.md) — Dynamic normalizer derivation
- [DEC-010](docs/decisions/DEC-010-strategist-advisory-boundary.md) — LLM advisory boundary
- [DEC-017](docs/decisions/DEC-017-macro-gate-softening.md) — Macro gate soft scaling

---

## Disclaimer

This project is for **research and educational purposes only**. It is **not
financial or investment advice**, and nothing here is a recommendation to buy or
sell any security. The software is provided “as is”, without warranty of any
kind. Trading financial instruments carries substantial risk of loss. Use at
your own risk.

---

## License

Released under the MIT License.

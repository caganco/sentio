# Sentio

[![CI](https://github.com/caganco/sentio/actions/workflows/ci.yml/badge.svg)](https://github.com/caganco/sentio/actions)
[![mypy](https://img.shields.io/badge/mypy-strict%20(engine)-blue)](https://mypy.readthedocs.io)
[![ruff](https://img.shields.io/badge/ruff-clean-green)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)

Falsifiable signal research for Borsa Istanbul (BIST) - is the edge real, or am I fooling
myself?

Sentio tests whether a BIST signal survives honest scrutiny instead of just looking good in
a backtest. Pre-registration is enforced in code, the pipelines are look-ahead-safe, the data
is survivorship-clean, and the validation engine splits the data along whichever axis
overfitting likes to hide in.

Across everything I tested, no deployable edge survived. In a market this efficient that's the
expected result, and the value here is an honest map of what the data can and can't support,
not a wall of green equity curves.

## How it works

- **Pre-registration is mechanical.** Each hypothesis is frozen in a Stage-0 JSON before any
  result is computed. The engine refuses to run if that file is missing or has drifted, so the
  goalposts can't move after the fact.
- **Null results are the product.** Three axes (cross-sectional factors, timing signals, event
  tilts) are tested and written up whether they work or not. Most don't. Those reports are the
  real output.
- **The validation engine splits where overfit hides.** Name-split for cross-sectional factors,
  purged/embargoed CPCV for timing signals, intra-regime holdout for forward persistence (see
  below).
- **It admits when it can't decide.** Every verdict carries a confidence flag, and CONFOUNDED
  fires automatically when the test window is single-regime. A bare pass with no qualifier is
  never emitted.

## Two tracks

- **Anchor (the deployed idea):** a low-cost, fully-invested smart-passive strategy that beat
  the TL-deposit benchmark in real (CPI-deflated) terms over 2019-2026. It lives in the
  companion repo [ballast-bist](https://github.com/caganco/ballast-bist).
- **Lab (this repo):** the infrastructure for testing whether any edge exists above that
  anchor. So far, none does.

The invariant linking both: **a signal is never expressed as a cash gate.** An idle signal
means a fully-invested equal-weight position, not cash. The rule comes from a post-mortem that
showed forgone beta, not bad stock selection, was the dominant damage channel.

## Data

Daily BIST prices, 2019-2026, 681 symbols, survivorship-clean: delisted tickers stay in,
acquired via the official BIST free dataset, so tests don't silently exclude companies that
went bankrupt. Seven years covers the modern post-2018 regime; it isn't deep history, and that
bounds the statistical power (see [Scope & limits](#scope--limits)).

## Validation engine (`src/engine/`)

A general-purpose, post-hoc-auditable strategy validation tool that enforces research
discipline in code rather than convention.

| Mode | Question answered | Method |
|------|-------------------|--------|
| **Mod-A** (name-split) | Is this cross-sectional overfit to specific tickers? | Disjoint name halves, same window; conjugate agreement across R=50 seed-fixed splits |
| **Mod-B** (temporal CPCV) | Is this timing-signal overfit across time? | Embargoed combinatorial purged cross-validation (Bailey & López de Prado) |
| **Mod-C** (intra-regime holdout) | Does a factor persist forward within one regime? | Train/holdout split with construction-window embargo |

**Statistics:** Rank IC / IC-IR with Newey-West HAC standard errors; real CSCV-PBO; a Deflated
Sharpe bound with honest trial-count binding from Stage-0; market-neutral residuals via
rolling-β neutralization; a benchmark floor of real active return vs `max(CPI, policy-rate)`.

**Reliability hardening:** every conjugate result carries an `agreement_confidence` qualifier
(HIGH / LOW / CONFOUNDED). An iteration lockbox seals a held-out subset with a content hash and
enforces single-shot consumption; tampering is visible in git history.

The `harness()` entry point, the frozen `SplitSpec`, and the full Section-7 output vector are
documented in the [operator guide](docs/engine/OPERATOR_GUIDE.md) and typed in
`src/engine/contracts.py`.

## Research findings

No deployable persistent edge was found across the three tested axes. Cross-sectional factors
hit a cost wall (~42 bp realistic round-trip) and regime instability; timing signals failed to
clear the significance bar across four independent measurement attempts; event-driven tilts are
in forward measurement (recorder live since 2026-06-01, verdict pending). The engine's first
real-data exam also surfaced a structural BIST constraint: the survivorship-honest liquid
universe (~38 names at the 10M TRY ADV floor over seven years) is too small for the name-split
conjugate test at full history. That is a documented property of the market, not a flaw in the
method.

Every directive and its verdict is in the [research registry](docs/RESEARCH_REGISTRY.md); full
reports live in [docs/research/](docs/research/).

## Engineering

| Area | Status |
|------|--------|
| Tests | 2,088 across 138 files; zero-regression policy, CI blocks merge on any failure |
| Type checking | mypy strict on `src/engine/`; older edge modules on a baseline ignore-list being paid down |
| Linting | ruff clean across `src/` and `tests/` |
| Look-ahead safety | forward returns computed as `return[t+1]` on `weights[t]`; verified by a golden byte-repro gate |
| Architecture | `import-linter` contracts block cross-layer imports in CI |
| CI tiers | architecture → integration → lint → full regression → security; all must pass before merge |

## Repository structure

```
sentio/
├── src/
│   ├── engine/        validation engine (harness, contracts, config, Mod-A/B/C)
│   ├── backtest/      backtesting engine + López de Prado statistical validation stack
│   ├── signals/       6-layer signal engine (L1-L6) + regime gate + strategist
│   ├── screening/     factor measurement engines (D-2xx series: event / exposure / trend)
│   ├── analytics/     IC calculator, Brinson attribution, NAV tracker, XBRL scorer
│   ├── data/          fetchers, scrapers, parsers, DataHub router
│   ├── risk/          position sizing, Kelly, drawdown, circuit breaker, stop calculator
│   ├── nlp/           FinBERT / VADER sentiment analyzers
│   └── utils/         logger, weight validator, OS state manager
├── tests/             2,088 tests: unit · integration · architecture invariants · hygiene
├── examples/rry1008/  red-team scripts: graveyard-factor + adversarial overfit probe
├── docs/
│   ├── research/      research reports (RR-xxx, D-xxx, NRR-xxx)
│   ├── RESEARCH_REGISTRY.md   master index of all research reports
│   ├── DECISIONS.md           architecture decision log
│   └── ARCHITECTURE.md        system architecture
├── scripts/           daily_update.py, health_check.py, build_clean_universe.py
├── config.yaml        runtime config (universe, scanner parameters)
└── pyproject.toml     tool config (mypy, ruff, import-linter contracts)
```

## Getting started

**Requirements:** Python 3.11+, dependencies in `requirements.txt`.

```bash
git clone https://github.com/caganco/sentio
cd sentio
pip install -r requirements.txt
cp .env.example .env          # keys all optional for offline runs

# Full test suite (runs fully offline)
python -m pytest tests/ -q --tb=short
# Expected: 2,088 passed, 4 skipped (golden gate: needs a local data snapshot)

# Red-team the engine, no external data required
python examples/rry1008/run_part1_known_answer.py
```

**Environment variables** (see `.env.example`):
- `EVDS_API_KEY` - TCMB EVDS3 macro data (free registration at evds2.tcmb.gov.tr)
- `FMP_API_KEY` - supplementary market data
- `ANTHROPIC_API_KEY` - optional; enables the Strategist narrative layer

The engine and test suite run fully offline; API keys only matter for live data pulls. How to
attach a signal, write a Stage-0, and read the output vector is in the
[operator guide](docs/engine/OPERATOR_GUIDE.md).

## Scope & limits

Stated up front rather than left to be discovered:

- **Trial counting.** A Deflated Sharpe is only as honest as its trial count. N is bound per
  hypothesis-family from Stage-0; the program-level count across 200+ commits is deliberately
  not collapsed into one number. The [research registry](docs/RESEARCH_REGISTRY.md) is the
  audit ledger for that.
- **One market, one person, no live trading.** Solo work on BIST only. Nothing here places
  orders; there is no execution layer and no live-slippage realization. It's a research
  instrument by design, not a deployment.
- **Shallow history.** 2019-2026 is barely more than one regime. The ongoing disinflation gives
  a genuine prospective out-of-sample window, but today the power is whatever seven years buys.
- **Uneven type-checking.** The engine core (`src/engine/`) is mypy-strict; some older edge
  modules are still on a baseline ignore-list being paid down.

## Methodology references

- Harvey, Liu & Zhu (2016). *… and the Cross-Section of Expected Returns.* Review of Financial
  Studies 29(1), 5-68. [Multiple testing in factor research; the `t > 3` threshold.]
- Bailey & López de Prado (2014). *The Deflated Sharpe Ratio.* Journal of Portfolio Management.
  [Deflated Sharpe; the CSCV / PBO framework.]
- McLean & Pontiff (2016). *Does Academic Research Destroy Stock Return Predictability?* Journal
  of Finance 71(1), 5-32. [Post-publication decay of anomalies.]

## Going deeper

- [Operator guide](docs/engine/OPERATOR_GUIDE.md): attach a signal, write a Stage-0, read the output vector
- [Research registry](docs/RESEARCH_REGISTRY.md): every directive and its verdict
- [Architecture](docs/ARCHITECTURE.md) and [decision log](docs/DECISIONS.md)
- [ballast-bist](https://github.com/caganco/ballast-bist): the deployed smart-passive anchor

---

Solo research project. Every finding, including the null ones, is documented in full.

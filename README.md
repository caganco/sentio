# Sentio

Falsifiable signal research for Borsa Istanbul (BIST) — is the edge real, or am I fooling
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
- **Three validation modes, each splitting where overfit hides.** Name-split for
  cross-sectional factors, purged/embargoed CPCV for timing signals, intra-regime holdout for
  forward persistence. The statistics are Newey-West HAC IC, real CSCV-PBO, and a Deflated
  Sharpe bound tied to the pre-registered trial count.
- **It admits when it can't decide.** Every verdict carries a confidence flag, and CONFOUNDED
  fires automatically when the test window is single-regime. A bare pass with no qualifier is
  never emitted.

## Data

Daily BIST prices, 2019–2026, 681 symbols, survivorship-clean (delisted names stay in; they
aren't silently dropped). Seven years covers the modern post-2018 regime. It isn't deep
history, and that bounds the statistical power (see limits below).

## Two tracks

- **Anchor (the deployed idea):** a low-cost, fully-invested smart-passive strategy that beat
  the TL-deposit benchmark in real terms over 2019–2026. It lives in the companion repo
  [ballast-bist](https://github.com/caganco/ballast-bist). One rule governs the whole system:
  an idle signal means equal-weight invested, never cash. A post-mortem showed forgone beta,
  not bad stock selection, was the dominant damage channel.
- **Lab (this repo):** the infrastructure for testing whether any edge exists above that
  anchor. So far, none does.

## Scope & limits

Stated up front rather than left to be discovered:

- **Trial counting.** A Deflated Sharpe is only as honest as its trial count. N is bound per
  hypothesis-family from Stage-0; the program-level count across 200+ commits is deliberately
  not collapsed into one number. The [research registry](docs/RESEARCH_REGISTRY.md) is the
  audit ledger for that.
- **One market, one person, no live trading.** Solo work on BIST only. Nothing here places
  orders; there is no execution layer and no live-slippage realization. It's a research
  instrument by design, not a deployment.
- **Shallow history.** 2019–2026 is barely more than one regime. The ongoing disinflation
  gives a genuine prospective out-of-sample window, but today the power is whatever seven years
  buys.
- **Uneven type-checking.** The engine core (`src/engine/`) is mypy-strict; some older edge
  modules are still on a baseline ignore-list being paid down.

## Getting started

```bash
git clone https://github.com/caganco/sentio
cd sentio
pip install -r requirements.txt
cp .env.example .env          # keys all optional for offline runs

python -m pytest tests/ -q    # 2,088 tests, runs fully offline
python examples/rry1008/run_part1_known_answer.py   # red-team the engine, no data needed
```

API keys (EVDS macro, FMP, optional Anthropic narrative) only matter for live data pulls; the
engine and test suite run offline.

## Going deeper

- [Operator guide](docs/engine/OPERATOR_GUIDE.md): attach a signal, write a Stage-0, read the output vector
- [Research registry](docs/RESEARCH_REGISTRY.md): every directive and its verdict
- [Architecture](docs/ARCHITECTURE.md) and [decision log](docs/DECISIONS.md)
- Full reports in [docs/research/](docs/research/)

---

Solo research project. Every finding, including the null ones, is documented in full.

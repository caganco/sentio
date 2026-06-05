# BIST Algorithmic Trading Research System

[![CI](https://github.com/caganco/bist-trading-system/actions/workflows/ci.yml/badge.svg)](https://github.com/caganco/bist-trading-system/actions)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io)
[![ruff](https://img.shields.io/badge/ruff-clean-green)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)

A rigorous, production-grade research infrastructure for systematic strategy evaluation
on the Borsa Istanbul (BIST). Designed and implemented by a single researcher.

**This is not a trading bot.** It is a research discipline system — a framework for
rigorously asking whether a strategy idea is genuine signal or overfitting, with mechanically
enforced pre-registration, look-ahead-safe pipelines, survivorship-bias-clean data, and a
multi-mode conjugate test engine that splits evaluation in the dimension where overfit hides.

---

## What makes this different

**Pre-registration enforced mechanically.** Every backtest hypothesis is frozen in a
Stage-0 JSON before results are computed. The engine refuses to run without it.
Post-hoc interpretation is structurally prevented, not just discouraged.

**Negative knowledge is a first-class output.** Three discovery axes were systematically
tested — cross-sectional factors, orthogonal timing signals, and event-driven tilts. No
deployable persistent edge was found on the available data. This is the documented
finding. In efficient-ish markets, this is the *expected* outcome of rigorous research,
and it constitutes a high-quality map of what the data can and cannot support — including
the empirical demonstration of the regime-identifiability limit (the engine's own
validation surfaced it on real data, with the predicted confound named in advance).

**Survivorship-bias-clean data.** The dataset covers BIST daily prices back to 1987
including delisted tickers, acquired via the official BIST free dataset. Tests do not
silently exclude companies that went bankrupt.

**The validation engine has honest limits.** The conjugate test is powerful within one
regime; its regime-independence guarantees are bounded. These limits are documented,
tested against real data, and stated in the research reports. The engine surfaces
them — it does not hide them.

**Production-grade engineering discipline.** Strict mypy, ruff, full CI, zero-regression
policy, strangler pattern for infrastructure evolution, no magic constants, every
load-bearing parameter pre-registered before use.

---

## Architecture

The system is organized around two parallel tracks:

**Track 1 — Smart-passive anchor (deployed).** A systematic, low-cost strategy that
captures market risk premium while preventing the behavioral and transaction-cost leakage
that dominates retail performance drag. Over a 2019–2026 backtest (D-197) the anchor
delivered positive real (CPI-deflated) returns and beat the TL deposit-rate benchmark,
which lost value in real terms over the same period. The strategy, its backtest, and the
round-trip cost model live in the companion repository
[ballast-bist](https://github.com/caganco/ballast-bist).

**Track 2 — Alpha research lab.** A disciplined infrastructure for testing whether
systematic exploitable edge exists above the passive anchor. The conjugate validation
engine (see below) is the core tool. Research findings are accumulated in the
[research registry](#research-registry).

The invariant linking both tracks: **a signal is never expressed as a cash gate.**
An idle signal means a fully-invested equal-weight position, not cash. This is not
a preference — it is a law derived from a post-mortem attribution analysis that showed
forgone-beta, not selection, was the dominant damage channel in the system's pre-reform period.

---

## Validation engine (`src/engine/`)

The engine is a general-purpose, post-hoc-auditable strategy validation tool.
It enforces research discipline in code rather than in convention.

### Evaluation modes

| Mode | Question answered | Method |
|------|-------------------|--------|
| **Mod-A** (name-split) | Is this cross-sectional overfit to specific tickers? | Same time window, disjoint name halves; conjugate agreement across R=50 random splits |
| **Mod-B** (temporal CPCV) | Is this timing-signal overfit across time? | Embargoed combinatorial purged cross-validation (Bailey & López de Prado) |
| **Mod-C** (intra-regime holdout) | Does a cross-sectional factor persist forward within the same regime? | Train/holdout split within one regime, construction-window embargo |

The engine's mode-selection principle: **split in the dimension where overfit hides.**
Cross-sectional factors are evaluated with name-split (Mod-A); timing signals with temporal
CPCV (Mod-B); forward persistence with intra-regime holdout (Mod-C).

### Statistical methodology
- **Rank IC / IC-IR** with Newey-West HAC standard errors (pinned convention, rel=1e-12).
- **Real CSCV-PBO** (Bailey-López de Prado median-rank bucket transfer probability).
- **Deflated Sharpe Ratio** with honest trial-count binding from Stage-0 pre-registration.
- **Market-neutral residuals** via rolling-β neutralization (look-ahead-safe, W=126).
- **Benchmark floor:** real active return vs. max(CPI, policy-rate benchmark).

### Reliability hardening
- Verdict-confidence qualifier: every conjugate result carries `agreement_confidence`
  (HIGH / LOW / CONFOUNDED). CONFOUNDED fires when the eval window is single-regime or a
  shared common-factor is detected. A bare `agreement_pass=True` with no qualifier is not
  emitted.
- Iteration lockbox: a sealed held-out subset is registered with a content hash before
  any iteration begins. The engine enforces single-shot consumption. Tampering is visible
  in git history.

### Key interfaces

```python
# src/engine/harness.py — single entry point
def harness(
    panel: Panel,
    signal: Signal,
    split_spec: SplitSpec,
    dial_config: DialConfig,
    *,
    stage0_path: str | Path | None = None,
) -> EngineOutput:
    """Assemble the Section-7 EngineOutput for one prototype run.

    stage0_path (optional) enforces pre-registration: when given,
    require_stage0 refuses to proceed if the freeze file is absent or drifted.
    It is optional so synthetic panels stay runnable without a frozen Stage-0
    file; real pre-registered runs pass the path.
    """

# src/engine/contracts.py — SplitSpec (frozen=True)
@dataclass(frozen=True)
class SplitSpec:
    split_mode: SplitMode
    frequency: Frequency
    embargo_h: int = 1          # = signal construction-window; h >= 1
    R: int = 50                 # seed-fixed name-splits (Mod-A)
    seed: int = 0
    cpcv_n: int = 10            # Mod-B temporal CPCV blocks
    cpcv_k: int = 2
    split_arm_floor_tl: float = 1.0e7
    sort_depth: SortDepth = SortDepth.TERCILE
    min_names_per_arm: int = 50
    name_split_method: NameSplitMethod = NameSplitMethod.LIQUIDITY

# src/engine/contracts.py — EngineOutput (Section 7 output-vector, key fields)
@dataclass
class EngineOutput:
    gross_active_ann: float | None = None
    net_active_ann: float | None = None
    cost_ann: float | None = None
    tax_ann: float | None = None
    mean_rt_bps: float | None = None
    null_percentile: float | None = None
    mirror_active_ann: float | None = None
    real_active_ann: float | None = None
    benchmark_floor_ann: float | None = None
    beats_benchmark_floor: bool | None = None
    pbo: float | None = None
    deflated_oos_t: float | None = None
    dsr: float | None = None
    dsr_n_trials: int | None = None
    nw_t: float | None = None
    agreement_pass: bool | None = None
    agreement_t_cross_median: float | None = None
    sign_consistency: float | None = None
    residual_cross_sectional_corr: float | None = None
    residual_corr_flag: bool | None = None
    agreement_confidence: AgreementConfidence | None = None
    agreement_confidence_reasons: tuple[str, ...] = ()
    per_regime: dict[str, dict[str, float]] = field(default_factory=dict)
    plateau_map: dict[str, float] = field(default_factory=dict)
    pm1_guard_raised: bool = False
    guard_messages: tuple[str, ...] = ()
    n_obs: int | None = None
    n_names: int | None = None
    split_mode: str | None = None
    notes: tuple[str, ...] = ()
    # Mod-C (intra-regime holdout) fields — see src/engine/contracts.py for complete definition
    holdout_persistence_pass: bool | None = None
    holdout_confidence: HoldoutConfidence | None = None
    # ... (holdout_ic_t, holdout_ic_mean, train_ic_t, train_ic_mean, n_holdout_obs, etc.)
```

### Engine modules

| Module | Description |
|--------|-------------|
| `harness.py` | Top-level assembler: the single `harness()` entry point; dispatches Mod-A / Mod-B / Mod-C legs and assembles the full Section-7 output vector. |
| `contracts.py` | Typed dataclass contracts: `Panel`, `SplitSpec`, `DialConfig`, `EngineOutput`, and all related enums. |
| `config.py` | Frozen single source of truth for all engine structural constants and dial defaults (math-spec v1.1 §8). |
| `moda.py` | Mod-A conjugate (cross-sectional name-split): R seed-fixed liquidity-stratified splits; per-arm rank-IC series; conjugate agreement verdict + CSCV PBO. |
| `modb.py` | Mod-B temporal-CPCV: purged combinatorial cross-validation over the time axis; DSR-deflated OOS Sharpe; proxy PBO. |
| `modc.py` | Mod-C intra-regime holdout (`run_modc()`): train/holdout split with construction-window embargo; holdout rank-IC measurement; `holdout_persistence_pass` verdict. |
| `holdout_confidence.py` | Pure `assess_holdout_confidence()`: `HoldoutConfidence` enum (HIGH / LOW / CONFOUNDED); regime-semantics are the inverse of Mod-A — single-regime is the design here; REGIME_SPLIT-crossing is the confound. |
| `neutralizer.py` | Factor neutralization (§3.5): market-beta residualization of raw signal scores before IC measurement; mandatory for Mod-A. |
| `pbo.py` | Real CSCV median-rank PBO (López de Prado): decile-fixed bucket assignment over R name-splits. |
| `dsr.py` | DSR trial-count deflation benchmark (§4.2 / Faz-4b): Bailey–López de Prado E[max] order statistic deflation by N from Stage-0. |
| `stats.py` | Cross-sectional statistics core: rank-IC, ICIR, Newey-West HAC t-statistic with near-zero-variance guard. |
| `benchmark.py` | Real-return deflation + benchmark-floor: real active return vs max(TUFE, TLREF); raises PM-1 guard on floor failure. |
| `data_adapter.py` | Data adapter (§9): loads clean-universe parquet + snapshots into a typed `Panel`; computes forward total returns. |
| `confidence.py` | Verdict-confidence qualifier (RR-Y1-009): annotates Mod-A conjugate verdict with HIGH / LOW / CONFOUNDED; additive, does not replace `agreement_pass`. |
| `lockbox.py` | Held-out iteration lockbox (RR-Y1-009): single-shot enforcement — refuses to score a sealed held-out subset more than once. |
| `stage0_validator.py` | Stage-0 pre-registration validator (§6): reads and validates the frozen JSON; refuses to run if absent or drifted. |
| `signal_protocol.py` | Signal contract + PM-1 guard (§10): `Signal` ABC and PM-1 fully-invested long-only assertion. |

---

## Research outcomes

The following table summarizes completed research directives.
Full reports are in `docs/research/`.

*SERAP = illusory edge: signal appears significant in aggregate but collapses when the universe is restricted to the deployable (liquid) subset. Gates defined in the engine's 5-gate framework.*

| Report | Verdict |
|--------|---------|
| **D-203** — Value + EDGE-2 + hi52 (681 symbols, D-202 clean universe) | VALUE = SERAP (gate-2 fail, illiquid-biased). EDGE-2 = genuine edge, post-2022 narrowing. hi52 = strongest / most regime-resilient. |
| **D-204** — hi52 stress-test: realistic cost + OOS + liquidity paradox | TRADEABLE-NO. Round-trip ~340 bp > breakeven ~302 bp at ~88%/month turnover. Liquidity paradox confirmed: illiquid premium evaporates after cost. |
| **D-205** — hi52 liquid-first (ADV ≥ 10M TRY, final N≤3 measurement) | TRADEABLE-NO. Pool healthy (min 44, median 78) but cost ratio only modestly improved (~307 bp). EW_FULL_LIQUID bar remains uncleared. |
| **D-207** — Realistic-cost recalibration (Roll + Kyle, quoted-spread primary) | Bloated model corrected (~12–20× de-inflation). EOD quoted spread ~flat ~11 bp across spectrum; microcap cost wall = Kyle impact, not spread. Fidelity 8/8. |
| **D-208** — hi52 liquid re-test with corrected cost (D-205-revisited) | TRADEABLE-NO (significance wall). Cost-free NW-\|t\| = 1.70; with corrected cost +1.17. Gate-2 (NW-\|t\| ≥ 2) FAIL. Root cause: not cost, but absent significance. hi52 closes definitively. |
| **D-209** — H2b dividend run-up re-test with corrected cost | TRADEABLE-NO (N≤3 final). Detection reproduced (1,108 events). Liquid cost-free NW-t = 0.61 (signal absent in deployable universe). H2b closes definitively. |
| **D-211** — RR-Y1-002: foreign flow → forward BIST-index TL-real return | TRADEABLE-NO. Lag-0 co-movement strong (NW-t = 3.68) but non-deployable (contemporaneous). Knowable lag-2 form: signal vanishes (sign reversal). RR-038 "foreign flow leads index" claim refuted. |
| **D-213** — RR-Y1-003: ex-ante real rate → forward XU100 TL-real return | TRADEABLE-NO (significance). Correct sign (tight policy → equities hurt); lag-1 NW-t = −1.82 (sub-2). Deploy backtest net +85.5% TL-real vs buy-hold +47.5%, but relative NW-t = 0.16. AR(1) = 0.986 → Stambaugh bias further suppresses effective t. |
| **D-Y1-001** — Value-only regime-resilience test | FRAGILE / REGIME-DEPENDENT. P/B passes 4/4 periods mechanically; E/P fails; OOS collapses; no disinflation premium. Value is not a stable premium on available data. |
| **NRR-007** — lowvol63 isolated (EDGE-2 hidden component) | ELIMINATED (cost-free SERAP). Gate-4 liquidity collapse: illiquid +1.20% vs liquid −0.31%. lowvol63 isolated edge is a liquidity premium, not an anomaly. |
| **NRR-008** — Value regime-gated tilt (3rd and final value measurement) | ELIMINATED. Regime gating did not rescue value: cost-free NW-t = 0.759 ≈ static D-203 (0.76). Value thread closes definitively (3 measurements, N≤3 rule). |
| **D-206** — NAV discount Z-score mean reversion (time-series, new paradigm) | SERAP. Pooled FE-within beta = −0.0185 (wrong sign for MR). Driscoll-Kraay \|t\| = −0.81. Bootstrap p = 0.43. BIST holding NAV discount does not exhibit MR in the measured window. |
| **RR-Y1-008** — Validator-validation / red-team (engine's first real-data exam) | ENGINE WORKS (3 independent tests passed). Structural BIST constraint surfaced: liquid universe at 10M TRY ADV + 7-year continuity = ~38 names < min_names_per_arm → breadth guard fires correctly. Documented market property, not methodology limit. |
| **RR-Y1-009** — Verdict-confidence qualifier + iteration lockbox | ENGINE HARDENED (additive-only, zero regression). Qualifier prevents silent CONFOUNDED pass. Lockbox enforces single-shot held-out consumption with SHA-256 fingerprint. |
| **D-185 / D-186 / D-187** — Trend-motor and honest-benchmark tests | TREND DISCREDITED (DEC-044). D-185 gross DD ~99% artefact; D-186 corrected: entry-timing does not beat fair null at 95th pctile. D-187: active timing real −5.7%; random-null pctile 0.17. |
| **D-188** — Event-driven confluence test | Infrastructure + forward recorder live since 2026-06-01. All three event types in `data_pending`. Verdict deferred to forward sample. |

**Summary finding.** No deployable persistent edge was identified across the three
tested axes. Cross-sectional factors face a cost wall (~42 bp realistic round-trip)
and regime instability. Timing signals failed to clear the significance bar across
four independent measurement attempts. Event-driven tilts: forward measurement
infrastructure deployed; verdict pending (sample collection in progress since 2026-06-01).

The engine's first real-data exam (RR-Y1-008) additionally revealed a structural
BIST constraint: the survivorship-honest liquid universe (~38 names at 10M TRY ADV
floor) is too small for the name-split conjugate test at full history. This is a
documented property of the market, not a limitation of the methodology.

*Event-driven tilts (D-188): infrastructure and forward recorder live since 2026-06-01;
forward sample collection in progress. Verdict deferred pending sufficient sample.*

---

## Engineering quality

| Metric | Value |
|--------|-------|
| Total tests | **2,088** across 138 test files |
| Engine-specific tests | **~254** (14 `test_engine_*.py` files) |
| Regression baseline | Zero regressions enforced; CI blocks merge on any failure |
| Type checking | mypy strict configured; CI tracking (non-blocking in current phase) |
| Linting | ruff clean across `src/` and `tests/` |
| Look-ahead safety | Forward returns computed as `return[t+1]` on `weights[t]`; verified by C12 golden byte-repro gate (NW-t gross = 6.928414, net = −6.274774, n_pooled = 1,375) |
| Strangler pattern | Committed motors are never edited; engine re-implements via committed primitives (no circular dependency to lab code) |
| Architecture enforcement | `import-linter` contracts block cross-layer imports in CI |
| CI tiers | Tier 1 (architecture) → Tier 2 (integration) → lint → Tier 3 (full regression) → security audit; all must pass before merge |

---

## Repository structure

```
bist-trading-system/
├── .github/
│   └── workflows/
│       ├── ci.yml                   — Multi-tier CI (arch → integration → lint → regression → security)
│       ├── daily_production.yml     — Scheduled 18:30 IST weekday production run + IC history commit
│       └── keep_alive.yml           — Sunday healthcheck ping
├── src/
│   ├── engine/                      — RR-Y1-005 validation engine (harness, contracts, config, Mod-A/B/C)
│   ├── backtest/                    — Backtesting engine + López de Prado statistical validation stack
│   ├── signals/                     — 6-layer signal engine (L1–L6) + regime gate + strategist
│   ├── screening/                   — Factor measurement engines (D-2xx series, event/exposure/trend)
│   ├── analytics/                   — IC calculator, Brinson attribution, NAV tracker, XBRL scorer
│   ├── data/                        — All data fetchers, scrapers, parsers, DataHub router
│   ├── risk/                        — Position sizing, Kelly, drawdown, circuit breaker, stop calculator
│   ├── nlp/                         — FinBERT / VADER sentiment analyzers
│   ├── analysis/                    — Technical analysis primitives
│   └── utils/                       — Logger, weight validator, OS state manager, failure notifier
├── tests/                           — 2,088 tests: unit · integration · architecture invariants · hygiene
├── examples/
│   └── rry1008/                     — RR-Y1-008 red-team scripts: graveyard-factor + adversarial overfit probe
├── docs/
│   ├── research/                    — 65+ research reports (RR-xxx, D-xxx, NRR-xxx)
│   ├── RESEARCH_REGISTRY.md         — Master index of all research reports
│   ├── DECISIONS.md                 — Architecture Decision Log (DEC-001..DEC-046)
│   └── ARCHITECTURE.md              — System architecture (v3.0, Yol-2 canonical)
├── scripts/                         — daily_update.py, health_check.py, build_clean_universe.py
├── config.yaml                      — Runtime config (universe, scanner parameters)
├── requirements.txt                 — Pinned dependencies (pandas 2.2.2, numpy 2.4.6, …)
└── pyproject.toml                   — Tool config (mypy strict, ruff, import-linter contracts)
```

---

## Getting started

**Requirements:** Python 3.11+, dependencies in `requirements.txt`.

```bash
git clone https://github.com/caganco/bist-trading-system
cd bist-trading-system

pip install -r requirements.txt

# Copy the template and fill in keys (all optional for offline test runs)
cp .env.example .env

# Run the full test suite
python -m pytest tests/ -q --tb=short
# Expected: 2,088 passed, 4 skipped (C12 golden gate — requires local data snapshot)

# Run the red-team engine example (no external data required)
python examples/rry1008/run_part1_known_answer.py
```

**Environment variables** (see `.env.example`):
- `EVDS_API_KEY` — TCMB EVDS3 macro data (free registration at evds2.tcmb.gov.tr)
- `FMP_API_KEY` — supplementary market data
- `ANTHROPIC_API_KEY` — optional; enables the Strategist narrative layer

The engine and test suite run fully offline; API keys are only needed for live data
pulls and the optional LLM narrative.

Full usage documentation — how to attach a prototype signal, configure a Stage-0
pre-registration, and read the output vector — is in
[`docs/engine/OPERATOR_GUIDE.md`](docs/engine/OPERATOR_GUIDE.md).

---

## Research registry

> Full index: [`docs/RESEARCH_REGISTRY.md`](docs/RESEARCH_REGISTRY.md).
> Status: ✅ Applied · ⏳ Pending · 🔬 In progress · ⚠️ Inconclusive

| ID | Title | Date | Linked CB/SPEC | Status |
|----|-------|------|----------------|--------|
| [RR-001](docs/research/RR-001-fintables-takas-scraper.md) | Fintables settlement-data scraper feasibility | 21 May 2026 | D-116 | ✅ Applied |
| [RR-002](docs/research/RR-002-akd-terminalleri-python.md) | AKD terminal Python integration | 21 May 2026 | D-116 (Matriks rejected) | ✅ Applied |
| [RR-003](docs/research/RR-003-composite-mimari-alternatifleri.md) | Composite architecture alternatives | 21 May 2026 | CB-002, CB-010 | ⏳ Awaiting Phase 1 SPEC |
| [RR-005](docs/research/RR-005-fetcher-map.md) | BIST fetcher map (robots/auth/format/rate-limit/ToS) | 22 May 2026 | — | ⏳ Pending |
| [RR-008](docs/research/RR-008-evds-migration.md) | TCMB EVDS API migration: evds2→evds3, new base URL | 22 May 2026 | D-135/D-136 | ✅ Applied |
| [RR-010](docs/research/RR-010-bist-ic-measurement.md) | IC measurement methodology — Spearman IC, ICIR, Bayesian-shrinkage weight calibration | 23 May 2026 | CB-010 | ✅ Applied (D-139/D-140) |
| [RR-011](docs/research/RR-011-NLP-YAMA.md) | FinBERT-TR feasibility — Path 3 confirmed | 24 May 2026 | — | ⏳ Pending |
| [RR-012](docs/research/RR-012-EM-Spesifik-Faktor-Literaturu-Derinlestirmesi.md) | 14 EM/BIST-specific factor literature deep-dive | 24 May 2026 | — | ⏳ Pending |
| [RR-013](docs/research/RR-013_NAV_ISKONTO.md) | BIST holding NAV-discount and mean-reversion alpha strategy | 24 May 2026 | RR-012 §B8 | ✅ Tested → D-206 (mirage) |
| [RR-014](docs/research/RR-014-SLIPPAGE.md) | BIST slippage and market-impact modeling | 24 May 2026 | — | ✅ Applied → cost model (D-204/D-207) |
| [RR-015](docs/research/RR-015-TRANSACTION-COST.md) | Transaction-cost modeling — broker-tier comparison | 24 May 2026 | RR-014 §cont. | ✅ Applied → cost model (D-204/D-207) |
| [RR-016](docs/research/RR-016-DRAWDOWN-AND-VOLATILITY-TARGETING.md) | Drawdown & volatility targeting | 24 May 2026 | RR-012, RR-013, RR-014, RR-015 | ⏳ Pending |
| [RR-017](docs/research/RR-017-HMM.md) | HMM regime detection — BIST calibration and activation roadmap | 25 May 2026 | RR-003 §Phase 1 | ⏳ Pending (HMM weights disabled) |
| [RR-018](docs/research/RR-018-VERY-IMPORTANT.md) | López de Prado-based backtesting framework | 25 May 2026 | RR-014, RR-015, RR-016, RR-017 | ✅ Applied → validation engine (PBO/DSR) |
| [RR-019](docs/research/RR-019-MULTI-LLM.md) | Multi-LLM orchestration — AI-jury system for the BIST OS | 24 May 2026 | RR-010/011/012 | ⏳ Pending (Phase 6+) |
| [RR-020](docs/research/RR-020-BIST-VERISI-MAP.md) | BIST data-source atlas (Rosetta Stone) | 24 May 2026 | RR-005 §deep-dive | ⏳ Pending |
| [RR-021](docs/research/RR-021-TCMB.md) | TCMB EVDS3 API operational reference | 25 May 2026 | RR-008 §cont. | ✅ Applied (EVDS client) |
| [RR-022](docs/research/CRITIC-2605-STRATEJIK-MIMARI-DEGERLENDIRME.md) | Strategic architecture assessment | 26 May 2026 | RR-003, RR-017, CB-002 | ⏳ Pending review |
| [RR-031](docs/research/RR-031-KAP-NEXTJS-MIGRATION.md) | KAP Next.js migration — scraping infeasibility | 28 May 2026 | D-170 | ✅ Applied |
| [RR-032](docs/research/RR-032-FIZIBILITE.md) | BIST fundamental-data inventory for the Phase 0b value factor | 25 May 2026 | NRR-002, D-170/172/175 | ⏳ Decision pending |
| [RR-033](docs/research/RR-033-isyatirim-tms29-uyum-testi.md) | İş Yatırım TMS 29 compliance test | 25–30 May 2026 | RR-032 §6, NRR-002 | ⚠️ v2 inconclusive |
| [RR-034](docs/research/RR-034-isyatirim-usd-feasibility.md) | İş Yatırım USD-based value feasibility check | 30 May 2026 | RR-033, RR-032 §6 | ⚠️ Check done — not green |
| [RR-035](docs/research/RR-035-malitablo-cross-sectional-consistency.md) | MaliTablo cross-sectional consistency test | 30 May 2026 | RR-033 v2, NRR-002 | ✅ Green + 3rd-source confirmed |
| [RR-036](docs/research/RR-036-tms29-uygulama-tarihi.md) | TMS 29 BIST first-application date | 30 May 2026 | RR-035, NRR-002 | ✅ Clear — Phase 0b window starts ~2024-09 |
| [RR-037](docs/research/RR-037-smartmoney-veri-erisim.md) | Smart-money 4-channel data-access + quality validation | 30 May 2026 | RR-032-V3, RR-001/002 | ⏳ Decision pending |
| [RR-038](docs/research/RR-038-MODERN-BIST.md) | Modern BIST (2019–2026) behavioral-regime evidence map | 31 May 2026 | RR-001/002/020, D-185/D-186/D-187 | 🔬 D-187: active-timing fails |
| [RR-039](docs/research/RR-039-RULEBASED-TA.md) | Rule-based TA: turning visual intuition into machine-computable rules | 31 May 2026 | RR-038, RR-039, D-185/D-186 | 🔬 D-186 definitive: fails |
| [RR-040](docs/research/RR-040-SWING.md) | BIST algorithmic swing-trading — three-hypothesis base research | 31 May 2026 | RR-038, RR-039, D-188 | 🔬 D-188 verdict deferred |
| [RR-041](docs/research/RR-041-SINYAL.md) | Measuring entry-signal quality, exit-stripped | 31 May 2026 | RR-040, RR-038/039, D-188 | 🔬 D-188 awaiting data/token |
| [RR-042](docs/research/RR-042-corp-action-veri-kaynagi.md) | Corp-action data-source research | 2 Jun 2026 | D-200, RR-020 | ✅ Applied → D-202 four-layer hybrid |
| [RR-Y1](docs/research/RR-Y1.md) | Resolving the value-factor Phase-0 ↔ D-191 contradiction + regime instability | 2 Jun 2026 | D-183, D-191 | ✅ Applied → D-Y1-001 |
| [D-203](docs/research/D-203-rapor.md) | Definitive test: value + EDGE-2 + 52wk-high on the D-202 clean universe | 2 Jun 2026 | D-202, RR-038/Y1 | ✅ Applied |
| [D-204](docs/research/D-204-rapor.md) | hi52 stress-test: realistic cost + OOS + liquidity paradox | 3 Jun 2026 | D-203, RR-015 | ✅ Applied → not tradeable |
| [D-205](docs/research/D-205-rapor.md) | hi52 liquid-first (final measurement, N≤3) | 3 Jun 2026 | D-204, NRR-005/006 | ✅ Applied → not tradeable |
| [NRR-008](docs/research/NRR-008-rapor.md) | Value regime-arm (3rd and final round, N≤3) | 3 Jun 2026 | D-203, D-Y1-001, RR-Y1 | ✅ Applied → eliminated |
| [NRR-007](docs/research/NRR-007-rapor.md) | lowvol63 isolated (hidden EDGE-2 component) | 3 Jun 2026 | D-203, D-205 | ✅ Applied → eliminated |
| [D-206](docs/research/D-206-rapor.md) | NAV-discount-Z mean-reversion — new paradigm (time-series) | 3 Jun 2026 | RR-044, D-205/NRR-007/NRR-008 | ✅ Applied → mirage |
| [RR-045](docs/research/RR-045-fund-nav-veri.md) | Fund-NAV-arb data-acquisition feasibility | 3 Jun 2026 | D-206, Pontiff 1995 | ✅ Applied → triggered NRR-009 |
| [RR-046](docs/research/RR-046-veri-fizibilite.md) | PEAD + macro-event data-acquisition feasibility | 3 Jun 2026 | RR-040, D-206/RR-045 | ⏳ Phase-2a done |
| [D-207](docs/research/D-207-rapor.md) | realistic_cost re-calibration — inflated-model fix | 3 Jun 2026 | NRR-010, D-204/D-205 | ✅ Applied → inflated model corrected |
| [D-208](docs/research/D-208-rapor.md) | hi52 liquid re-test — D-205 revisited, corrected cost | 4 Jun 2026 | D-205, D-207 | ✅ Applied → not tradeable (significance) |
| [D-209](docs/research/D-209-rapor.md) | H2b dividend-runup re-test — corrected cost | 4 Jun 2026 | D-207 | ✅ Applied → not tradeable |
| [D-213](docs/research/D-213-rapor.md) | RR-Y1-003: ex-ante real-rate → forward XU100 TL-real return | 4 Jun 2026 | D-212/RR-Y1-003, D-211 | ✅ Applied → not tradeable |
| [D-211](docs/research/D-211-rapor.md) | RR-Y1-002: foreign-flow → forward BIST-index TL-real return | 4 Jun 2026 | D-210/RR-Y1-002, RR-038 | ✅ Applied → not tradeable |
| [RR-Y1-005](docs/research/RR-Y1-005-TEST-MOTORU-TASARIM-v-0-2.md) | Validation-engine DESIGN v0.2 — FROZEN | 4 Jun 2026 | DEC-045, RR-Y1 | ✅ Phase 0–4 applied (PR #195–#204) |
| [RR-Y1-005B](docs/research/RR-Y1-005B-MATEMATIKSEL-SPEC.md) | Mathematical spec v1.1 — FROZEN | 4 Jun 2026 | RR-Y1-005, López de Prado | ✅ Phase 1–4 applied |
| [RR-Y1-008](docs/research/RR-Y1-008-VALIDATOR-REDTEAM.md) | Validator-validation / red-team — engine's first real-data exam | 5 Jun 2026 | RR-Y1-005 §7, RR-Y1-005B | ✅ Applied → engine works |
| [RR-Y1-009](docs/research/RR-Y1-009-VERDICT-CONFIDENCE-LOCKBOX.md) | Verdict-confidence qualifier + iteration lockbox | 5 Jun 2026 | RR-Y1-008 §1/§2, DEC-049/050 | ✅ Applied → engine hardened |
| [RR-Y1-010](docs/research/RR-Y1-010-TASK-intra-regime-time-holdout.md) | Intra-regime time-holdout — Mode-C (`SplitMode.TIME_HOLDOUT`) | 5 Jun 2026 | RR-Y1-005 §3/§4.8, RR-Y1-009, DEC-046 | ✅ Applied → engine Mode-C added (PR #208) |
| [RR-Y1-005-FAZ4](docs/research/RR-Y1-005-FAZ4-HARDENING.md) | Phase-4 hardening — NW floor-guard + DSR trial-count binding | 5 Jun 2026 | RR-Y1-005 (Phase-3 backlog), RR-Y1-005B §5 | ✅ Applied → partial double-counting measured |

---

## Methodology references

- Harvey, Liu & Zhu (2016). *… and the Cross-Section of Expected Returns.*
  Review of Financial Studies 29(1), 5–68.
  [Multiple testing in factor research; t > 3 threshold.]
- Bailey & López de Prado (2014). *The Deflated Sharpe Ratio.*
  Journal of Portfolio Management.
  [Deflated Sharpe; CSCV / PBO framework.]
- McLean & Pontiff (2016). *Does Academic Research Destroy Stock Return Predictability?*
  Journal of Finance 71(1), 5–32.
  [Post-publication decay of anomalies.]

---

## Roadmap

- **2026–2027 disinflation OOS:** the ongoing Turkish disinflation cycle provides
  a genuine second regime for prospective out-of-sample evaluation. The engine is ready.
- **Within-regime time-holdout (Mod-C):** complete (PR #208) — landed as
  `SplitMode.TIME_HOLDOUT`; ready for use.

---

*Built and maintained as a solo research project. All research findings — including null results —
are documented in full.*

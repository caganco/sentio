# BIST OS — Architecture

**System:** BIST OS Algorithmic Trading System
**Version:** Phase 4.5 (Production)
**Last Updated:** 2026-05-19

---

## 1. Full Signal Pipeline

```mermaid
flowchart TD
    subgraph DS["Data Sources"]
        YF["yfinance\nOHLCV · RSI · Volume"]
        EVDS["TCMB EVDS\nPolicy rate · FX · CDS"]
        KAP["KAP API\nCorporate disclosures"]
        ISY["Is Yatirim Screener\nForeign ratio · Short interest"]
    end

    subgraph LS["Layer Scoring  ·  src/signals/layers/"]
        L1["L1 Technical\ntechnical_layer.py\nweight: 0.25"]
        L2["L2 Macro\nmacro_layer.py\nweight: 0.20"]
        L3["L3 KAP\nkap_layer.py\nweight: 0.30"]
        L4["L4 Sentiment\nsentiment_layer.py\nweight: 0.12 x conf\nSUSPENDED"]
        L5["L5 Smart Money\nsmart_money_layer.py\nweight: 0.10 x conf\nRAMP-UP"]
        L6["L6 Risk/Kelly\nrisk_layer.py\nweight: 0.03"]
    end

    CE["Composite Engine\nsrc/signals/engine.py\ncompute_signal()\nSum(score x weight) / Sum(weight)\nnormalizer in [0.78, 1.00]"]

    CV["Conviction Validator\nsrc/signals/conviction_validator.py\ncompute_conviction()\nscore = (composite/100) x macro_mult\n>=0.68 BUY-STRONG · 0.55-0.67 BUY-MEDIUM · <0.55 WATCH"]

    MG["Macro Regime Gate\nsrc/signals/macro_regime_gate.py\ncalculate_macro_regime_scaling()\nBULL 1.0x · NEUTRAL 0.8x · BEAR 0.0x"]

    PS["Position Sizer\nsrc/risk/position_sizer_v2.py\nsize_position()\nBUY-STRONG 32.5% · BUY-MEDIUM 17.5%\nmax 4 strong · max 2 medium · max 30% sector"]

    SE["Staged Exit Manager\nsrc/order_engine/staged_exit_manager.py\ncheck_exit_ladder()\nTP1 50% · TP2 30% · TP3 20% trailing\nstop-loss -8%"]

    subgraph OUT["Outputs"]
        RPT["Daily Report\nsrc/reports/daily_report.py"]
        STR["Strategist Narrative\nsrc/signals/strategist.py\nClaude API · read-only advisory\nDEC-010"]
        AUD["Audit Trail\nSignalResult · AuditTrail\nsrc/signals/models.py"]
    end

    YF --> L1
    EVDS --> L2
    KAP --> L3
    YF --> L4
    ISY --> L5
    YF --> L6
    EVDS --> L6

    L1 --> CE
    L2 --> CE
    L3 --> CE
    L4 --> CE
    L5 --> CE
    L6 --> CE

    CE --> CV
    CV --> MG
    MG --> PS
    PS --> SE

    SE --> RPT
    CE --> STR
    CE --> AUD

    classDef live    fill:#1a5c2a,color:#fff,stroke:#0d3318
    classDef susp    fill:#4a4a4a,color:#ccc,stroke:#333
    classDef ramp    fill:#1a3a5c,color:#fff,stroke:#0d2236
    classDef engine  fill:#2c2c6e,color:#fff,stroke:#1a1a4a
    classDef output  fill:#3d1a5c,color:#fff,stroke:#250d3a
    classDef source  fill:#333,color:#ddd,stroke:#555

    class L1,L2,L3,L6 live
    class L4 susp
    class L5 ramp
    class CE,CV,MG,PS,SE engine
    class RPT,STR,AUD output
    class YF,EVDS,KAP,ISY source
```

---

## 2. Druckenmiller Macro-First Hierarchy

```mermaid
flowchart TD
    MR["1. Macro Regime\nTCMB policy · CDS · USD/TRY · DXY\nForeign flows · VIX\n-----------------\nBEAR -> no new entries (0.0x)\nNEUTRAL -> reduced size (0.8x)\nBULL -> full size (1.0x)"]

    SA["2. Sector Alignment\nL3 KAP sector scoring\nL2 macro sector context\n-----------------\nSector cap: max 30% exposure\nmax 2 positions per sector"]

    SF["3. Stock Fitness\nL1 Technical (RSI · MA · Volume)\nL3 KAP disclosure events\nL5 Smart Money institutional flow\n-----------------\nComposite 0-100 · Conviction 0-1"]

    TE["4. Entry Timing\nConviction tier gate\n>= 0.68 -> BUY-STRONG entry\n0.55-0.67 -> BUY-MEDIUM entry\n< 0.55 -> WATCH only"]

    SZ["5. Position Sizing\nConviction x macro scaling\n+ sector exposure check\n+ portfolio drawdown guard\n-----------------\nMax 4 BUY-STRONG · Max 2 BUY-MEDIUM\nMax 6 total open positions"]

    MR --> SA
    SA --> SF
    SF --> TE
    TE --> SZ

    classDef macro   fill:#5c1a1a,color:#fff,stroke:#3a0d0d
    classDef sector  fill:#1a3a5c,color:#fff,stroke:#0d2236
    classDef stock   fill:#1a5c2a,color:#fff,stroke:#0d3318
    classDef timing  fill:#4a3a00,color:#fff,stroke:#2c2200
    classDef sizing  fill:#2c2c6e,color:#fff,stroke:#1a1a4a

    class MR macro
    class SA sector
    class SF stock
    class TE timing
    class SZ sizing
```

---

## 3. Layer Detail Reference

### L1 — Technical Layer (`src/signals/layers/technical_layer.py`)

Scores price action and momentum on a 0-100 scale. Inputs: OHLCV from yfinance.

Key signals: RSI (14), 20/50/200-day moving averages, volume surge ratio, Bollinger Band position. Outputs a single `LayerScore` with `source="computed"` when data is available, `source="missing"` on fetch failure.

### L2 — Macro Layer (`src/signals/layers/macro_layer.py`)

Scores the Turkish macro environment. Inputs from `src/signals/local/` client modules:

| Sub-signal | Source | Weight in L2 |
|-----------|--------|-------------|
| USD/TRY direction | yfinance | 0.25 |
| VIX level | yfinance | 0.20 |
| Brent crude | yfinance | 0.15 |
| S&P 500 | yfinance | 0.15 |
| BIST100 | yfinance | 0.15 |
| Foreign flows (weekly) | Is Yatirim | 0.20 |
| DXY | yfinance (Gap 3) | 0.25 |

L2 score also drives conviction macro multiplier (separate from the macro gate).

### L3 — KAP Layer (`src/signals/layers/kap_layer.py`)

Highest-weight layer (0.30) — reflects BIST's information asymmetry dynamic where corporate disclosures frequently precede price moves. Parses KAP events by category (dividends, capital increases, financial results, material events, insider transactions) and scores their directional impact within a configurable lookback window.

### L4 — Sentiment Layer (`src/signals/layers/sentiment_layer.py`) — SUSPENDED

FinBERT-based Turkish financial news sentiment. Suspended because no reliable Turkish-language financial news feed has been integrated. When active: confidence scales with article count and recency; at confidence=0 the effective weight is 0 and the composite is unaffected (DEC-009). Social media scope (X, Telegram, BIST forums) deferred to Phase 5.

### L5 — Smart Money Layer (`src/signals/layers/smart_money_layer.py`) — RAMP-UP

Institutional flow detection from Is Yatirim foreign ratio screener + short interest data. Two sub-signals:

- **Foreign ratio trend** (`L5_FOREIGN_WEIGHT = 0.70`) — weekly directional change
- **Short interest** (`L5_SHORT_INT_WEIGHT = 0.30`) — inverse relationship (high short = bearish)

Bull trap override: triggers confidence reduction when technical score is high but institutional flow is negative. Returns `confidence=0` until minimum data history is accumulated (~Day 10-20 of data collection).

### L6 — Risk/Kelly Layer (`src/signals/layers/risk_layer.py`)

Lowest-weight layer (0.03) — acts as a position guard, not a primary signal. Kelly fraction estimate based on historical hit rate and payoff ratio. Also drives `detect_regime()` which classifies macro environment as `BULL`, `NEUTRAL`, `BEAR`, or `RISK_OFF`.

`RISK_OFF` triggers an engine-level override: all BUY signals become HOLD regardless of composite score (`engine.py:_apply_regime_filter()`).

---

## 4. Conviction System Detail

```
composite (0-100)
    |
    |  / 100
    v
base_score (0-1.0)
    |
    |  x macro_multiplier
    |    L2 >= 65 -> 1.2
    |    L2 >= 50 -> 1.0
    |    L2 < 50 -> 0.85
    v
conviction_score (0-1.0, capped at 1.0)
    |
    +--> >= 0.68  --> BUY-STRONG  --> 32.5% base allocation
    +--> >= 0.55  --> BUY-MEDIUM  --> 17.5% base allocation
    +-->  < 0.55  --> WATCH        --> no entry
```

Position sizing then applies a second macro scaling pass (macro regime gate) and checks sector concentration caps before returning a final allocation percentage.

---

## 5. Constants Architecture

All numeric parameters are centralized in `src/signals/thresholds.py`. No hardcoded values are permitted in engine, layer, or risk modules. Architecture tests (`tests/test_architecture.py::TestThresholdsSingleSource`) enforce this invariant on every test run.

```
src/signals/thresholds.py
+-- MASTER_WEIGHTS          # L1-L6 base weights (sum = 1.00)
+-- SIGNAL_THRESHOLDS       # buy_strong/buy_weak/hold_lower/sell_weak
+-- CONVICTION_STRONG       # 0.68
+-- CONVICTION_MEDIUM       # 0.55
+-- MACRO_GATE_BULL_MIN     # 60.0
+-- MACRO_GATE_NEUTRAL_MIN  # 45.0
+-- POSITION_SIZE_STRONG    # 0.325
+-- POSITION_SIZE_MEDIUM    # 0.175
+-- EXIT_STOP_LOSS          # 0.92  (-8%)
+-- EXIT_PROFIT_TARGET      # 1.20  (+20%)
+-- TP1/TP2/TP3_PCT_EXIT    # 0.50 / 0.30 / 0.20
+-- RISK_OFF_CONDITIONS     # VIX, USD/TRY, BIST100 thresholds
```

---

## 6. Test Architecture

```
tests/
+-- test_architecture.py   # Tier 1 - design invariants (7 tests)
|   +-- TestThresholdsSingleSource   (no hardcoded values in engine.py)
|   +-- TestWeightSumValid           (MASTER_WEIGHTS sum in [0.85, 1.05])
|   +-- TestSingletonPattern         (LocalMacroSignals singleton)
|   +-- TestL5VerdaIndependence      (L5 core is vendor-free)
+-- test_signal_alert.py   # Tier 2 - integration (7 tests)
+-- test_backtest.py       # Tier 2 - integration (22 tests)
+-- test_*.py (39 files)   # Tier 3 - unit tests (~700 tests)
```

Total: **742 passing, 1 skipped** (as of Phase 4.5, commit 9c9bbcb).

---

*docs/ARCHITECTURE.md — BIST OS v4.5 — 2026-05-19*

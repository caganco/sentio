"""NRR-008 value-REJIM-KOLU -- frozen Stage-0 MEASUREMENT geometry. FAZ-1.

value-static was measured TWICE and failed both times: D-203 = SERAP (Gate-2 NW |t|=0.76,
illiquid-heavy) and D-Y1-001 = KIRILGAN/REJIM-BAGIMLI (P/B mechanical-PASS but E/P contradicts
+ out-of-sample collapse + disinflation carries no premium). RR-Y1 thesis: BIST-value is
macro-regime-driven (NOT publication-decay; Aras/Cam 2018 HML=-1.09%/mo NEGATIVE). The ONE
untested arm: "value-tilt active ONLY in the appropriate macro regime". NRR-008 tests whether
turning the value tilt OFF during disinflation rescues an otherwise-fragile factor.

HONEST EXPECTATION (BEFORE results): UNCERTAIN. Static value was SERAP/fragile twice, so the
prior is weak -- BUT the regime-gated arm is genuinely untested. Regime-gating MIGHT rescue
value, OR turning off disinflation alone MIGHT not be enough. Elimination is a clean, valuable
result (definitive closure of the value thread). NO celebration expected; value's 3rd and FINAL
round (N<=3 lock -- no 4th).

TWO-STAGE DISCIPLINE (post-hoc protection): the regime variable was chosen edge-UNSEEN at
Stage-1 (docs/yol1/NRR-008-rejim-onerisi.md, 3 candidates with economic/literature justification
only) and APPROVED by maintainer on 2026-06-03 in DIRECTION form (Aday-A inflation-direction).
Selecting among candidates by edge = p-hacking = FORBIDDEN. The frozen rule is in
docs/yol1/STAGE0_nrr008.json (the engine REFUSES to run without it).

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d203/d204/nrr007 config, this holds pre-
registered GEOMETRY frozen at Stage-0; DECISION/COST constants live in src/signals/thresholds.py
(reused D203_*/D204_*). The value signal is D-203-IDENTICAL (eng.value_factor_panel via
eng.score_panel_for("value", ...) is CALLED; the committed engine is NOT modified -- gates run
via an injected-score replica of run_gates, the NRR-007 precedent). The regime rule is
DIRECTION-based (only the sign of the 6-month YoY-TUFE change) -> NO new decision threshold;
the 6-month window + t-1 lag are STRUCTURAL constants frozen here, not tuned.

NRR-008 is the 3rd and FINAL value measurement (N<=3 lock).
"""
from __future__ import annotations

from src.screening import d203_config as _d203
from src.screening import d204_config as _d204
from src.signals import thresholds as _th

NRR008_CONFIG_VERSION = "nrr008-v1"

# ---------------------------------------------------------------------------
# Frozen snapshots + windows -- REUSE D-203/D-204 verbatim (same panel, same hashes).
# ---------------------------------------------------------------------------
NRR008_CLEAN_UNIVERSE_ROOT = _d204.D204_CLEAN_UNIVERSE_ROOT
NRR008_PRICE_CONTENT_HASH = _d204.D204_PRICE_CONTENT_HASH   # fd207550...
NRR008_FUND_CONTENT_HASH = _d204.D204_FUND_CONTENT_HASH     # d72a6977...

NRR008_COMMON_WINDOW_START = _d204.D204_COMMON_WINDOW_START   # 2019-07-01
NRR008_COMMON_WINDOW_END = _d204.D204_COMMON_WINDOW_END       # 2026-04-30

# ---------------------------------------------------------------------------
# value factor geometry -- REUSE D-203 (identical definition, no new factor).
# value_factor_panel = bm (book-to-market = equity/mktval = 1/PBV) PRIMARY; ey robustness.
# month-end fundamentals lagged D203_FUND_PUBLICATION_LAG_MONTHS (look-ahead safe).
# ---------------------------------------------------------------------------
NRR008_VALUE_PRIMARY = _d203.D203_VALUE_PRIMARY       # "bm"
NRR008_VALUE_ROBUST = _d203.D203_VALUE_ROBUST         # "ey"
NRR008_FUND_PUBLICATION_LAG_MONTHS = _d203.D203_FUND_PUBLICATION_LAG_MONTHS  # 1
NRR008_TOP_N = _d203.D203_TOP_N                       # 15
NRR008_MIN_POOL_N = _d203.D203_MIN_POOL_N             # 30 (healthy-pool reference)

# ---------------------------------------------------------------------------
# Regime-direction signal (Aday-A, APPROVED maintainer 2026-06-03; DIRECTION-not-LEVEL).
# At a monthly rebalance in month M: regime_recent = infl_yoy(M-1), regime_prior = infl_yoy(M-7).
# ON (value-tilt ACTIVE = D-203 value top-15)  if regime_recent >= regime_prior (flat/rising).
# OFF (value-tilt CLOSED = EW_FULL-neutral)     if regime_recent <  regime_prior (disinflation).
# infl_yoy(M) = TUFE_monthend(M) / TUFE_monthend(M-12) - 1.
# The 6-month comparison window (M-1 vs M-7) + the t-1 publication lag + the 12-month YoY span
# are STRUCTURAL constants FROZEN here (rationale: capture the direction-trend with low noise;
# a 3/6/12-month sweep = multiple-comparisons = FORBIDDEN). DIRECTION-not-LEVEL: no inflation
# level threshold is used -> NO new decision threshold is introduced.
# ---------------------------------------------------------------------------
NRR008_TUFE_SNAPSHOT = _d203.D203_TUFE_SNAPSHOT       # "exposure_d187_tufe" (TP.FG.J0, daily index)
NRR008_REGIME_YOY_MONTHS = 12      # trailing-12m YoY-TUFE
NRR008_REGIME_WINDOW_MONTHS = 6    # compare YoY(M-1) vs YoY(M-7) -> 6-month direction window (DONUK)
NRR008_REGIME_LAG_MONTHS = 1       # t-1 publication lag (TUFE for M-1 published ~day 3 of M)

# ---------------------------------------------------------------------------
# Cadence + realistic-cost geometry -- REUSE D-204 verbatim (same cost model).
# ---------------------------------------------------------------------------
NRR008_PRIMARY_CADENCE = _d204.D204_PRIMARY_CADENCE          # 1 (monthly, D-203/204-comparable)
NRR008_PORTFOLIO_TL = _d204.D204_PORTFOLIO_TL               # 300_000
NRR008_ORDER_VALUE_TL = _d204.D204_ORDER_VALUE_TL           # 20_000 / position
NRR008_ADV_WINDOW = _d204.D204_ADV_WINDOW                   # 63
NRR008_LAMBDA_KYLE = _d204.D204_LAMBDA_KYLE                 # FROZEN
NRR008_ROLL_WINDOW = _d204.D204_ROLL_WINDOW                 # 21
NRR008_BREAKEVEN_BPS_GRID = _d204.D204_BREAKEVEN_BPS_GRID   # 0..400bp, 5bp steps (VIEW)
NRR008_BREAKEVEN_SAFETY_MULT = _d204.D204_BREAKEVEN_SAFETY_MULT  # 2.0

# ---------------------------------------------------------------------------
# OOS / regime -- REUSE D-204 (honest in-sample walk-forward + disinflation proxy).
# ---------------------------------------------------------------------------
NRR008_WALKFWD_SPLIT = _d204.D204_WALKFWD_SPLIT             # 2023-01-01
NRR008_DISINFLATION_WINDOW = _d204.D204_DISINFLATION_WINDOW  # 2024-01..2026-04 weak proxy
NRR008_REGIME_PRIMARY = _d203.D203_REGIME_PRIMARY          # 2022-01-01 (gate-3 calendar split)

# ---------------------------------------------------------------------------
# Statistics knobs -- REUSE D-203/204 (matches the KESIN-TEST exactly).
# ---------------------------------------------------------------------------
NRR008_GATE_NW_T_MIN = _d203.D203_GATE_NW_T_MIN            # 2.0 (KEY gate: static value failed at 0.76)

# ---------------------------------------------------------------------------
# Candidate lock (N=1). value-regime only -- value's 3rd and FINAL round.
# ---------------------------------------------------------------------------
NRR008_CANDIDATE = "value-regime"
NRR008_VALUE_DISPATCH = "value"   # eng.score_panel_for dispatch key (D-203-IDENTICAL)
NRR008_CANDIDATE_LABEL = (
    "value-regime (D-203-IDENTICAL value top-15 [bm primary], gated ON/OFF by a look-ahead-safe "
    "trailing-12m YoY-TUFE 6-month DIRECTION rule) -- NRR-008 value 3rd and FINAL round (N<=3)")

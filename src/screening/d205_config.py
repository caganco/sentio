"""D-205 hi52 LIKIT-ONCE -- frozen Stage-0 MEASUREMENT geometry. FAZ-1.

D-204 found hi52 = GERCEK-ama-tradeable-DEGIL on the naive prototype (realized realistic
cost ~340bp > breakeven ~302bp; root cause ~88% turnover x ~98% microcap). NRR-005 showed
(a) the killer is the COST-RATE (microcap), not the turnover-LEVEL, and (b) the hi52 SIGNAL
lives in liquid names (liquid-pool rank-IC 0.048 ~ full-universe 0.047). D-205 attacks the
cost-rate directly: restrict the UNIVERSE to absolute-liquid names FIRST (signal UNCHANGED),
then apply hi52, and ask whether the edge survives REALISTIC cost. This does NOT relax the
D-204 verdict (the prototype stays tradeable-DEGIL); it attacks D-204's root cause.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d204_config, this holds pre-registered
GEOMETRY frozen at Stage-0; DECISION/COST constants live in src/signals/thresholds.py
(D205_* + reused D204_*/D203_*, single source). It REUSES the D-203 frozen panel verbatim
(same content hashes) and the D-204 cost/stat geometry, so the hi52 factor + cost model are
defined identically. The liquid-ADV threshold (D205_LIQUID_ADV_MIN_TL) was frozen on
NRR-006 POOL-FEASIBILITY + Cagan-deploy grounds, EDGE-unseen (post-hoc selection FORBIDDEN).

D-205 is the 3rd and FINAL hi52 measurement (N<=3: D-203 + D-204 + D-205). No 4th round.
"""
from __future__ import annotations

from src.screening import d203_config as _d203
from src.screening import d204_config as _d204
from src.signals import thresholds as _th

D205_CONFIG_VERSION = "d205-v1"

# ---------------------------------------------------------------------------
# Frozen snapshots + windows + hi52 geometry -- REUSE D-203/D-204 verbatim.
# ---------------------------------------------------------------------------
D205_CLEAN_UNIVERSE_ROOT = _d204.D204_CLEAN_UNIVERSE_ROOT
D205_PRICE_CONTENT_HASH = _d204.D204_PRICE_CONTENT_HASH   # fd207550...
D205_FUND_CONTENT_HASH = _d204.D204_FUND_CONTENT_HASH     # d72a6977...
D205_TLREF_SNAPSHOT = _d204.D204_TLREF_SNAPSHOT

D205_COMMON_WINDOW_START = _d204.D204_COMMON_WINDOW_START      # 2019-07-01
D205_COMMON_WINDOW_END = _d204.D204_COMMON_WINDOW_END          # 2026-04-30

D205_HI52_LOOKBACK = _d204.D204_HI52_LOOKBACK          # 252 (hi52 IDENTICAL to D-203)
D205_TOP_N = _d204.D204_TOP_N                          # 15
D205_MIN_POOL_N = _d203.D203_MIN_POOL_N                # 30 (healthy-pool reference)

# ---------------------------------------------------------------------------
# Liquid-universe definition (D-205 core). ADV floor FROZEN at Stage-0 on NRR-006
# pool-feasibility + Cagan-deploy grounds (edge-unseen). Threshold lives in thresholds.py.
# ---------------------------------------------------------------------------
D205_LIQUID_ADV_MIN_TL = _th.D205_LIQUID_ADV_MIN_TL            # 1.0e7 FROZEN
D205_LIQUID_ADV_TRAILING_DAYS = _th.D205_LIQUID_ADV_TRAILING_DAYS  # 63
D205_SUBTIER_SPLIT = _th.D205_SUBTIER_SPLIT                    # 0.5 (gate-4 ADV half-split)

# ---------------------------------------------------------------------------
# Cadence + realistic-cost geometry -- REUSE D-204 verbatim (same cost model).
# ---------------------------------------------------------------------------
D205_PRIMARY_CADENCE = _d204.D204_PRIMARY_CADENCE             # 1 (monthly, D-203/204-comparable)
D205_PORTFOLIO_TL = _d204.D204_PORTFOLIO_TL                  # 300_000
D205_ORDER_VALUE_TL = _d204.D204_ORDER_VALUE_TL              # 20_000 / position
D205_ADV_WINDOW = _d204.D204_ADV_WINDOW                      # 63
D205_LAMBDA_KYLE = _d204.D204_LAMBDA_KYLE                    # FROZEN
D205_ROLL_WINDOW = _d204.D204_ROLL_WINDOW                    # 21
D205_BREAKEVEN_BPS_GRID = _d204.D204_BREAKEVEN_BPS_GRID      # 0..400bp, 5bp steps (VIEW)

# ---------------------------------------------------------------------------
# STRES-3 OOS / regime -- REUSE D-204 (honest in-sample walk-forward + disinflation proxy).
# ---------------------------------------------------------------------------
D205_WALKFWD_SPLIT = _d204.D204_WALKFWD_SPLIT                # 2023-01-01
D205_DISINFLATION_WINDOW = _d204.D204_DISINFLATION_WINDOW    # 2024-01..2026-04 weak proxy
D205_REGIME_PRIMARY = _d204.D204_REGIME_PRIMARY              # 2022-01-01

# ---------------------------------------------------------------------------
# Deploy hurdle (EKLEME-B) -- REUSE D-204 (same TLREF deposit real-carry, same snapshots).
# ---------------------------------------------------------------------------
D205_DEPLOY_MIN_LIQUID_NET = _d204.D204_DEPLOY_MIN_LIQUID_NET  # +0.000222 frozen
D205_DEPLOY_HURDLE_TOL = _d204.D204_DEPLOY_HURDLE_TOL          # 5e-6
D205_BREAKEVEN_SAFETY_MULT = _d204.D204_BREAKEVEN_SAFETY_MULT  # 2.0

# ---------------------------------------------------------------------------
# Statistics knobs -- REUSE D-203/204 (matches KESIN-TEST + STRES-TEST exactly).
# ---------------------------------------------------------------------------
D205_GATE_NW_T_MIN = _d203.D203_GATE_NW_T_MIN                # 2.0

# ---------------------------------------------------------------------------
# Buffer VIEW (secondary; reported, NOT selected). enter-15 / exit-30 ratchet within the
# liquid universe -- a turnover-reduction VIEW, not a deploy choice.
# ---------------------------------------------------------------------------
D205_BUFFER_ENTER = 15
D205_BUFFER_EXIT = 30

# ---------------------------------------------------------------------------
# Candidate lock (N=1). hi52 LIKIT-ONCE only -- the single D-205 candidate.
# ---------------------------------------------------------------------------
D205_CANDIDATE = "hi52-liquid-first"
D205_CANDIDATE_LABEL = (
    "hi52 LIKIT-ONCE (52wk-high proximity within an absolute-ADV-liquid universe) -- "
    "D-205 SON hi52-olcumu (N<=3)")

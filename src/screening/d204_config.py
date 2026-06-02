"""D-204 hi52 STRES-TEST -- frozen Stage-0 MEASUREMENT geometry. FAZ-1.

D-203 found ADAY-C hi52 (52wk-high proximity) = GERCEK-EDGE, the strongest candidate
(NW |t|=3.19, post>=pre on the primary split, 5/5 gates) -- the system's first
asterisk-free edge. But "5-gate-passed" != "deployable": D-203 left four caveats
(flat-cost only, monthly cadence, one long high-inflation regime, mechanism unexplained)
and EKLEME-3 a fifth (the liquidity paradox: hi52 illiquid +1.77% > liquid +1.35%, the
OPPOSITE of RR-043). D-204 is the STRESS-TEST that closes the deploy gap.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d203_config, this holds pre-registered
GEOMETRY frozen at Stage-0; DECISION/COST constants live in src/signals/thresholds.py
(D204_* block, single source). It REUSES the D-203 frozen panel verbatim (same content
hashes -> same universe, no re-measurement of the data) and re-exports D-203 lookbacks so
the hi52 factor is defined identically to D-203.

The 1/2/3-month rebalance cadences and the 0..400bp breakeven grid are reporting VIEWS of
the same measurement (like D-203's two windows / two regime splits) -- NOT optimization
variants, no "best" is selected. Single candidate: hi52 ISOLATED (N=1, Yol-1 N<=3 ok).
"""
from __future__ import annotations

from src.screening import d203_config as _d203
from src.signals import thresholds as _th

D204_CONFIG_VERSION = "d204-v1"

# ---------------------------------------------------------------------------
# Frozen snapshots -- REUSE D-203 verbatim (same panel, same hashes). No re-freeze.
# ---------------------------------------------------------------------------
D204_CLEAN_UNIVERSE_ROOT = _d203.D203_CLEAN_UNIVERSE_ROOT
D204_PRICE_PARQUET = _d203.D203_PRICE_PARQUET
D204_FUND_PARQUET = _d203.D203_FUND_PARQUET
D204_PRICE_CONTENT_HASH = _d203.D203_PRICE_CONTENT_HASH   # fd207550...
D204_FUND_CONTENT_HASH = _d203.D203_FUND_CONTENT_HASH     # d72a6977...
D204_TUFE_SNAPSHOT = _d203.D203_TUFE_SNAPSHOT             # exposure_d187_tufe
D204_TLREF_SNAPSHOT = "exposure_d187_tlref"               # D-187 frozen TLREF return-index

# ---------------------------------------------------------------------------
# Windows -- REUSE D-203. hi52 is price-only -> reported on BOTH windows (like D-203).
# ---------------------------------------------------------------------------
D204_COMMON_WINDOW_START = _d203.D203_COMMON_WINDOW_START      # 2019-07-01
D204_COMMON_WINDOW_END = _d203.D203_COMMON_WINDOW_END          # 2026-04-30
D204_EXTENDED_WINDOW_START = _d203.D203_EXTENDED_WINDOW_START  # 2019-01-01
D204_EXTENDED_WINDOW_END = _d203.D203_EXTENDED_WINDOW_END      # 2026-04-30
D204_WINDOWS = ("common", "extended")

# ---------------------------------------------------------------------------
# hi52 factor geometry -- REUSE D-203 (identical definition).
# ---------------------------------------------------------------------------
D204_HI52_LOOKBACK = _d203.D203_HI52_LOOKBACK          # 252
D204_MOM_LOOKBACK = _d203.D203_MOM_LOOKBACK            # 120 (STRES-4 factor-overlap proxy)
D204_MOM_SKIP = _d203.D203_MOM_SKIP                    # 21
D204_TOP_N = _d203.D203_TOP_N                          # 15
D204_MIN_POOL_N = _d203.D203_MIN_POOL_N                # 30
D204_LIQUIDITY_TRAILING_DAYS = _d203.D203_LIQUIDITY_TRAILING_DAYS  # 63
D204_DAILY_RETURN_CLIP = _d203.D203_DAILY_RETURN_CLIP  # 0.10

# ---------------------------------------------------------------------------
# STRES-2 cadence VIEWS (months between rebalances). 1 = D-203 monthly baseline.
# Longer cadence -> lower turnover -> lower cost (does the edge survive?). All
# reported; NO "best" selected (measurement, not optimization).
# ---------------------------------------------------------------------------
D204_REBALANCE_CADENCES = (1, 2, 3)
D204_PRIMARY_CADENCE = 1   # the D-203-comparable baseline

# ---------------------------------------------------------------------------
# STRES-1 realistic cost geometry. order_value = 300K-TL portfolio / top-15 = 20K/position.
# ADV = trailing-63d value_tl. Breakeven grid (bps) -> flat round-trip cost that zeroes the
# edge (the MODEL-INDEPENDENT main verdict). Cost MECHANICS in realistic_cost.py.
# ---------------------------------------------------------------------------
D204_PORTFOLIO_TL = 300_000.0
D204_ORDER_VALUE_TL = D204_PORTFOLIO_TL / D204_TOP_N        # 20000
D204_ADV_WINDOW = 63                                        # trailing value_tl ADV window
D204_LAMBDA_KYLE = _th.D204_LAMBDA_KYLE                     # FROZEN
D204_ROLL_WINDOW = _th.D204_ROLL_WINDOW                     # 21
D204_COMMISSION_PCT = _th.D204_COMMISSION_PCT               # 0.0
D204_BREAKEVEN_BPS_GRID = tuple(float(b) for b in range(0, 401, 5))  # 0..400bp, 5bp steps

# ---------------------------------------------------------------------------
# STRES-3 OOS / regime. HONEST in-sample (walk-forward) + disinflation sub-window as a
# WEAK proxy. pre-2019 acquisition REJECTED (no corp-action -> dirty, D-185 risk). The
# explicit OOS-GAP statement is mandatory in the report (regime-change resilience
# CANNOT be proven; disinflation 2024-26 is only a weak proxy).
# ---------------------------------------------------------------------------
D204_WALKFWD_SPLIT = "2023-01-01"                          # 2019-22 train / 2023-26 holdout
D204_DISINFLATION_WINDOW = ("2024-01-01", "2026-04-30")    # weak regime-change proxy
D204_REGIME_PRIMARY = _d203.D203_REGIME_PRIMARY            # 2022-01-01 (reused)
D204_REGIME_SECONDARY = _d203.D203_REGIME_SECONDARY        # 2022-07-01 (TLREF-carry start)

# ---------------------------------------------------------------------------
# EKLEME-B deploy hurdle. The TLREF deposit-real-carry hurdle is DERIVED from the frozen
# TLREF + TUFE snapshots over the TLREF-available window and asserted == the frozen
# thresholds value (reproducibility guard). TLREF index begins 2022-07 -> the hurdle is
# computed on 2022-07..2026-04 (n=45 months); stated explicitly.
# ---------------------------------------------------------------------------
D204_DEPLOY_MIN_LIQUID_NET = _th.D204_DEPLOY_MIN_LIQUID_NET     # +0.000222 frozen
D204_TLREF_AVAILABLE_START = "2022-07-01"                       # TLREF return-index data start
D204_DEPLOY_HURDLE_TOL = 5e-6                                   # recompute-vs-frozen assert tol

# ---------------------------------------------------------------------------
# Reused statistics knobs (verbatim D-203 -> matches the KESIN-TEST exactly).
# ---------------------------------------------------------------------------
D204_NW_LAGS = _d203.D203_NW_LAGS                  # 3
D204_NULL_SEED = _d203.D203_NULL_SEED              # 12345
D204_NULL_N_RESAMPLES = _d203.D203_NULL_N_RESAMPLES  # 2000
D204_SIG_BLOCK = _d203.D203_SIG_BLOCK              # 1
D204_SIG_N_BOOT = _d203.D203_SIG_N_BOOT            # 2000
D204_SIG_SEED = _d203.D203_SIG_SEED                # 12345
D204_GATE_NW_T_MIN = _d203.D203_GATE_NW_T_MIN      # 2.0
D204_BREAKEVEN_SAFETY_MULT = _th.D204_BREAKEVEN_SAFETY_MULT  # 2.0 (DEPLOY needs breakeven >= 2x cost)

# ---------------------------------------------------------------------------
# Candidate lock (N=1). hi52 ISOLATED only -- the single D-203 deploy candidate.
# ---------------------------------------------------------------------------
D204_CANDIDATE = "hi52"
D204_CANDIDATE_LABEL = "ADAY-C 52WK-HIGH ISOLATED (George-Hwang proximity) -- D-203 GERCEK-EDGE"

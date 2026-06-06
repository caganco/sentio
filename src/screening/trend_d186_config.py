"""D-186 Trend-Motor Duzeltme Turu -- Stage 0 frozen parameters (pre-registration).

D-185 verdict was INCONCLUSIVE: edge promising but (1) nominal-drift contaminated,
(2) random-null asymmetric (no entry-timing isolation), (3) significance overstated
(cross-sectional clustering), and the max_dd gate was a full-capital-cumprod ARTIFACT.
D-186 fixes the MEASUREMENT (not the rules): same 3 variants, same frozen snapshot,
same trades -- only the metrics change. This is a validation round (like D-181/D-184),
NOT a new edge search (N<=3 preserved).

These are MEASUREMENT params, intentionally NOT in thresholds.py (same precedent as
faz0_config / trend_config). Frozen at Stage 0 via a dated commit; MUST NOT change
after results are seen. The NET DECISION RULE (DEC-044) below is frozen and will NOT
be relaxed post-hoc (no "disinflation -> full-period", no threshold lowering).

Reuses D-185 frozen core (trend_config) unchanged.
"""
from __future__ import annotations

from src.screening.trend_config import (  # D-185 frozen core (unchanged)
    A_TRAIL_DONCHIAN_N,
    BOOTSTRAP_BLOCK,
    COST_SCENARIOS_BPS,
    FILTER_MODES,
    INFLATION_REGIMES,
    PRIMARY_COST_BPS,
    VARIANTS,
)

D186_CONFIG_VERSION = "trend-d186-v1"

# Re-exported (the same frozen objects drive D-186; no new variant/rule/param).
VARIANTS = VARIANTS
FILTER_MODES = FILTER_MODES
COST_SCENARIOS_BPS = COST_SCENARIOS_BPS
PRIMARY_COST_BPS = PRIMARY_COST_BPS

# ---------------------------------------------------------------------------
# FIX 1 -- real portfolio drawdown (replaces the broken full-capital cumprod)
# ---------------------------------------------------------------------------
# Concurrency-capped, equal-weight, daily mark-to-market portfolio. maintainer-approved:
# max K simultaneous open positions; each slot = 1/K of current equity; daily MTM on
# open positions' close -> a REAL equity curve -> real max-drawdown (bounded 0..1).
PORTFOLIO_MAX_CONCURRENT = 10
PORTFOLIO_SLOT_FRACTION = 1.0 / 10.0     # 1/K
PORTFOLIO_INITIAL_EQUITY = 1.0
# Slot contention: when > K signals compete, admit earliest (entry_date, then ticker
# alphabetical); the rest are skipped and counted (no silent drop).
PORTFOLIO_TIE_BREAK = "entry_date,ticker"

# ---------------------------------------------------------------------------
# FIX 2 -- drift-free returns (decisive = XU100-relative; real-CPI confirmatory)
# ---------------------------------------------------------------------------
# XU100-relative (geometric): rel_net = (1+gross)/(1+xu_ret[entry..exit]) - 1 - cost.
# Uses XU100 already in the frozen snapshot -> no new dependency, inflation-neutral.
RETURN_BASIS_DECISIVE = "xu100_relative"
# Real-CPI (TUFE-deflate) is CONFIRMATORY and BEST-EFFORT: frozen only if EVDS_API_KEY
# is present; absent -> XU100-relative decides alone (directive "REEL veya RELATIVE").
REAL_CPI_CONFIRMATORY = True
EVDS_TUFE_SERIES = "TP.FG.J0"            # monthly CPI (RR-021 active)
# Per-inflation-slice random null isolates drift (D-185 used a single global null).

# ---------------------------------------------------------------------------
# FIX 3 -- entry-timing isolation (fair null) + cross-sectional significance
# ---------------------------------------------------------------------------
# Fair null: random entries get the SAME exit machinery as the strategy (initial
# ATR-stop + Donchian-20 trailing + MAX_HOLD) AND the SAME active pre-filter as the
# cell (ADV universe always; parabolic-eligibility mask when parabolic_on). So the
# edge isolates ENTRY TIMING (trigger/retest), not the exit rule or the parabolic filter.
FAIR_NULL_STOP_ATR_MULT = 1.5            # random initial stop = entry - 1.5*ATR(14)
FAIR_NULL_TRAIL_DONCHIAN_N = A_TRAIL_DONCHIAN_N   # 20, same as strategy
FAIR_NULL_SEED = 12345
FAIR_NULL_N_RESAMPLES = 1000
# Cross-sectional significance: aggregate trades into a DAILY portfolio-return series
# (same-day trades collapse to one daily return -> cross-sectional clustering resolved
# by aggregation) then block-bootstrap (reuse factor_ic_harness.block_bootstrap_ci).
# No Driscoll-Kraay needed.
SIG_BLOCK = BOOTSTRAP_BLOCK              # 21 (~1 month), config now USED (D-185 IID ignored it)
SIG_N_BOOT = 2000
SIG_SEED = 12345

# ---------------------------------------------------------------------------
# NET DECISION RULE (DEC-044) -- FROZEN, no post-hoc relaxation
# ---------------------------------------------------------------------------
# PASSES if at least one variant (C is the strongest candidate), in XU100-relative
# returns, vs the FAIR null (stop+trailing+pre-filter matched), in the DISINFLATION
# slice (lowest nominal drift), with cross-sectional-corrected significance, beats the
# random null at >= DECISION_RANDOM_PCTILE_MIN AND has a real portfolio max_dd <= DECISION_MAXDD_MAX.
DECISION_SLICE = "disinflation"          # see INFLATION_REGIMES (2024-07-01..2026-04-30)
DECISION_RANDOM_PCTILE_MIN = 0.95
DECISION_MAXDD_MAX = 0.35


def decision_slice_window() -> tuple[str, str]:
    """(start, end) of the frozen decision slice from trend_config.INFLATION_REGIMES."""
    for label, lo, hi in INFLATION_REGIMES:
        if label == DECISION_SLICE:
            return lo, hi
    raise ValueError(f"decision slice {DECISION_SLICE} not in INFLATION_REGIMES")


# N<=3 lock: same A/B/C variants, same parabolic on/off, same trend_config params.
# Only the measurement methodology changes (DD, relative/real returns, fair null,
# CS-significance). NO new variant/rule/parameter.
N_VARIANTS = 3

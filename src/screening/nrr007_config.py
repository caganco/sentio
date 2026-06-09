"""NRR-007 lowvol63-IZOLE -- frozen Stage-0 MEASUREMENT geometry. FAZ-1.

hi52 CLOSED (D-205, N<=3 final: real signal but not retail-tradeable even liquid-first).
Decision (maintainer): measure the remaining cross-sectional Yol-1 candidates ONE BY ONE.
lowvol63 FIRST -- it lived INSIDE the EDGE-2 composite (mom120 + hi52 + lowvol63, equal-weight
rank-avg) but was NEVER tested in ISOLATION through the 5 gates (the D-203 engine only
dispatched value/edge2/hi52). The hi52 lesson: a bundle can HIDE a distinct factor -> it
deserves an isolated test.

HONEST EXPECTATION (calibrated BEFORE results): edge-arastirma S1/H4 pre-measured lowvol63-isolated
= +0.56%/mo, t=0.94 (BELOW the Gate-2 t>=2 bar, insignificant) -> PROBABLY ELIMINATED. This
test is for DEFINITIVE CLOSURE (no celebration expected); it is cheap (engine ready, one run).
But the edge-arastirma pre-indicator was pre-cost + full-universe; the isolated full test (5 gates +
realistic cost) MAY differ -> it still deserves the run (hi52 lesson: pre-indicator != full test).

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d205_config, this holds pre-registered
GEOMETRY frozen at Stage-0; DECISION/COST constants live in src/signals/thresholds.py
(reused D203_*/D204_*, single source -- NO new threshold needed: the lowvol window + gate
thresholds + cost constants already exist). It REUSES the D-203 frozen panel verbatim (same
content hashes) and the D-204 cost/stat geometry, so the lowvol63 factor + cost model are
defined identically to D-203/D-204. The lowvol63 signal is D-203/EDGE-2-IDENTICAL (the engine
function lowvol_panel is CALLED, the engine is NOT modified -- gates run via an injected-score
replica of run_gates).

NRR-007 is the 1st ISOLATED lowvol63 measurement (N<=3 lock per factor).
"""
from __future__ import annotations

from src.screening import d203_config as _d203
from src.screening import d204_config as _d204
from src.signals import thresholds as _th

NRR007_CONFIG_VERSION = "nrr007-v1"

# ---------------------------------------------------------------------------
# Frozen snapshots + windows -- REUSE D-203/D-204 verbatim (same panel, same hashes).
# ---------------------------------------------------------------------------
NRR007_CLEAN_UNIVERSE_ROOT = _d204.D204_CLEAN_UNIVERSE_ROOT
NRR007_PRICE_CONTENT_HASH = _d204.D204_PRICE_CONTENT_HASH   # fd207550...
NRR007_FUND_CONTENT_HASH = _d204.D204_FUND_CONTENT_HASH     # d72a6977...
NRR007_TLREF_SNAPSHOT = _d204.D204_TLREF_SNAPSHOT

NRR007_COMMON_WINDOW_START = _d204.D204_COMMON_WINDOW_START   # 2019-07-01
NRR007_COMMON_WINDOW_END = _d204.D204_COMMON_WINDOW_END       # 2026-04-30

# ---------------------------------------------------------------------------
# lowvol63 factor geometry -- REUSE D-203 (identical definition, no new factor).
# lowvol_panel = -std of trailing-NRR007_LOWVOL_WINDOW-day clipped daily returns.
# ---------------------------------------------------------------------------
NRR007_LOWVOL_WINDOW = _d203.D203_LOWVOL_WINDOW       # 63 (BIREBIR D-203/EDGE-2)
NRR007_TOP_N = _d203.D203_TOP_N                       # 15
NRR007_MIN_POOL_N = _d203.D203_MIN_POOL_N             # 30 (healthy-pool reference)

# ---------------------------------------------------------------------------
# Cadence + realistic-cost geometry -- REUSE D-204 verbatim (same cost model).
# ---------------------------------------------------------------------------
NRR007_PRIMARY_CADENCE = _d204.D204_PRIMARY_CADENCE          # 1 (monthly, D-203/204-comparable)
NRR007_PORTFOLIO_TL = _d204.D204_PORTFOLIO_TL               # 300_000
NRR007_ORDER_VALUE_TL = _d204.D204_ORDER_VALUE_TL           # 20_000 / position
NRR007_ADV_WINDOW = _d204.D204_ADV_WINDOW                   # 63
NRR007_LAMBDA_KYLE = _d204.D204_LAMBDA_KYLE                 # FROZEN
NRR007_ROLL_WINDOW = _d204.D204_ROLL_WINDOW                 # 21
NRR007_BREAKEVEN_BPS_GRID = _d204.D204_BREAKEVEN_BPS_GRID   # 0..400bp, 5bp steps (VIEW)
NRR007_BREAKEVEN_SAFETY_MULT = _d204.D204_BREAKEVEN_SAFETY_MULT  # 2.0

# ---------------------------------------------------------------------------
# OOS / regime -- REUSE D-204 (honest in-sample walk-forward + disinflation proxy).
# ---------------------------------------------------------------------------
NRR007_WALKFWD_SPLIT = _d204.D204_WALKFWD_SPLIT             # 2023-01-01
NRR007_DISINFLATION_WINDOW = _d204.D204_DISINFLATION_WINDOW  # 2024-01..2026-04 weak proxy
NRR007_REGIME_PRIMARY = _d203.D203_REGIME_PRIMARY          # 2022-01-01

# ---------------------------------------------------------------------------
# Statistics knobs -- REUSE D-203/204 (matches the validation test exactly).
# ---------------------------------------------------------------------------
NRR007_GATE_NW_T_MIN = _d203.D203_GATE_NW_T_MIN            # 2.0

# ---------------------------------------------------------------------------
# Candidate lock (N=1). lowvol63 ISOLATED only -- the single NRR-007 candidate.
# ---------------------------------------------------------------------------
NRR007_CANDIDATE = "lowvol63-isolated"
NRR007_CANDIDATE_LABEL = (
    "lowvol63 ISOLATED (inverted trailing-63d realized-vol; EDGE-2 component, "
    "D-203-IDENTICAL) -- NRR-007 ilk-izole olcum (N<=3)")

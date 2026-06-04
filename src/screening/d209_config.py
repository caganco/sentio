"""D-209 H2b TEMETTU-RUNUP re-test -- frozen Stage-0 MEASUREMENT geometry.

H2b (the dividend pre-ex run-up basket) was the single t>=2 candidate left in the
demo-goal graveyard (0bp daily NW-t=2.57), but it was eliminated there under a FLAT
20/100bp-per-side cost and NEVER measured with the D-207 corrected per-stock realistic
cost. D-209 re-runs the FROZEN demo-goal H2 signal (NO new definition) under the corrected
quoted-primary cost and decides: still tradeable, or a significance wall like hi52 (D-208)?

HONEST EXPECTATION (declared BEFORE results): the frozen demo-goal h2b_runup_basket.json
already shows NW-t=0.86 (ALL) / 1.16 (liquid) at the 20bp/side column; 20bp/side ~= 40bp
round-trip ~= the D-207 corrected cost (~42bp, D-208). -> PROBABLY a significance wall
(hi52 twin). No celebration expected; valuable because it is cheap and closes a gap.

MEASUREMENT-ONLY (optimization FORBIDDEN, grid-sweep FORBIDDEN = p-hacking). Like
d205_config, this holds pre-registered GEOMETRY frozen at Stage-0; DECISION/COST constants
live in src/signals/thresholds.py (D209_* + reused D205_*/D204_*/D203_*, single source). It
REUSES the D-203 frozen panel + the D-204/D-207 cost harness verbatim, and PORTS the frozen
demo-goal H2/H2b signal (detection + book) bit-for-bit so the run-up factor cannot drift.

Two FROZEN demo-goal variants are reported (NO "best" selected):
  V1 daily-churn basket (demo-goal h2b_runup_basket.py BIREBIR): held on day t iff ex-date
     in [t+1, t+5] (window [-5,-1]); exit before ex -> no dividend, no 15% tax.
  V2 low-turnover discrete capture (demo-goal H2 "RUNUP_capture" leg BIREBIR): per (symbol,
     ex) event ONE round-trip, compound over [-10,-1] (10 trading days = "hold-10g"),
     EW-combined per ex-month, exit before ex (add_div=False, no tax).

D-209 is the H2b FIRST official measurement (N<=3: count=1). No 4th round.
"""
from __future__ import annotations

from src.screening import d203_config as _d203
from src.screening import d204_config as _d204
from src.screening import d205_config as _d205
from src.signals import thresholds as _th

D209_CONFIG_VERSION = "d209-v1"

# ---------------------------------------------------------------------------
# Frozen snapshot + clean-universe geometry -- REUSE D-203/D-204 verbatim.
# The price parquet (adjusted_prices_2019_2026.parquet) carries BOTH tr_index_gross and
# adjusted_close, so the frozen ex-date detection reproduces LOCALLY (no re-freeze).
# ---------------------------------------------------------------------------
D209_CLEAN_UNIVERSE_ROOT = _d204.D204_CLEAN_UNIVERSE_ROOT
D209_PRICE_PARQUET = _d203.D203_PRICE_PARQUET            # adjusted_prices_2019_2026.parquet
D209_PRICE_CONTENT_HASH = _d204.D204_PRICE_CONTENT_HASH  # fd207550...

D209_COMMON_WINDOW_START = _d204.D204_COMMON_WINDOW_START  # 2019-07-01
D209_COMMON_WINDOW_END = _d204.D204_COMMON_WINDOW_END      # 2026-04-30
D209_DAILY_RETURN_CLIP = _d203.D203_DAILY_RETURN_CLIP      # 0.10 (clip_clean_returns)

# ---------------------------------------------------------------------------
# Frozen H2b/H2 signal geometry -- PORTED from the demo-goal H2 lab (BIREBIR, NO drift).
# ---------------------------------------------------------------------------
D209_EX_GAP_MIN = _th.D209_EX_GAP_MIN          # 0.005 ex-date detection gap
D209_HOLD_LO = _th.D209_HOLD_LO                # -5  V1 run-up window low
D209_HOLD_HI = _th.D209_HOLD_HI                # -1  V1 run-up window high
D209_V2_HOLD_LO = _th.D209_V2_HOLD_LO          # -10 V2 discrete-capture window low (hold-10g)
D209_V2_HOLD_HI = _th.D209_V2_HOLD_HI          # -1  V2 discrete-capture window high
D209_NW_LAG = _th.D209_NW_LAG                  # 5  Newey-West HAC lag (V1 daily series)
D209_REGIME_SPLIT = _th.D209_REGIME_SPLIT      # 2022-01-01 pre/post sign-stability split
# Frozen-detection reproduction guard (demo-goal H2 lab: ~1108 events / 265 symbols on the
# local build parquet). A LOCAL-only assert (parquet is CI-absent); informational here.
D209_EXPECTED_EVENTS_APPROX = 1108
D209_EXPECTED_SYMBOLS_APPROX = 265

# ---------------------------------------------------------------------------
# Liquid universe -- REUSE D-205 (absolute trailing-63d-median ADV >= 1e7 TL, FROZEN).
# Per directive ">=1e7 ADV, D-205-esik": ABSOLUTE threshold, NOT a tercile.
# ---------------------------------------------------------------------------
D209_LIQUID_ADV_MIN_TL = _d205.D205_LIQUID_ADV_MIN_TL            # 1.0e7 FROZEN
D209_LIQUID_ADV_TRAILING_DAYS = _d205.D205_LIQUID_ADV_TRAILING_DAYS  # 63

# ---------------------------------------------------------------------------
# Realistic-cost geometry -- REUSE D-204/D-207 verbatim (per-stock Roll+Kyle, quoted-primary).
# FLAT cost is REPLACED by per-name round-trip; commission stays Midas = 0.
# ---------------------------------------------------------------------------
D209_ORDER_VALUE_TL = _d204.D204_ORDER_VALUE_TL    # 20000 / position (300K / top-15)
D209_ADV_WINDOW = _d204.D204_ADV_WINDOW            # 63 trailing value_tl ADV window
D209_LAMBDA_KYLE = _d204.D204_LAMBDA_KYLE          # FROZEN (impact)
D209_ROLL_WINDOW = _d204.D204_ROLL_WINDOW          # 21 (Roll serial-cov window)
D209_BREAKEVEN_BPS_GRID = _d204.D204_BREAKEVEN_BPS_GRID  # 0..400bp, 5bp steps (VIEW)
# Legacy FLAT cost columns kept ONLY for the demo-goal-comparable context table (NOT the
# decision). The decision is the D-207 per-name realistic cost.
D209_FLAT_COST_BP_PER_SIDE = (0, 20, 100)

# ---------------------------------------------------------------------------
# Statistics knob -- gate2 significance floor (reuse D-203/204/205 single value).
# ---------------------------------------------------------------------------
D209_GATE_NW_T_MIN = _d205.D205_GATE_NW_T_MIN      # 2.0

# ---------------------------------------------------------------------------
# Candidate lock (N=1). H2b dividend pre-ex run-up only -- the single D-209 candidate.
# ---------------------------------------------------------------------------
D209_CANDIDATE = "h2b-dividend-runup"
D209_CANDIDATE_LABEL = (
    "H2b TEMETTU-RUNUP (dividend pre-ex run-up, exit before ex -> no tax) -- D-209 "
    "ilk-resmi-olcum (N<=3), demo-goal-FLAT-eleme sonrasi D-207-duzeltilmis-maliyet re-test")

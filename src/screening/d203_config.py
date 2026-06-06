"""D-203 KESIN-TEST -- frozen Stage-0 MEASUREMENT geometry. FAZ-1.

Resolves the two-lab contradiction (edge-arastirma VALUE=mirage / 52wk-high=regime-tilt
vs edge-arastirma EDGE-2 composite "strongest, +12.9pp above EW") by re-measuring
THREE candidates on the SAME corrected D-202 clean universe (681 symbols x 1848 days,
price content-hash fd207550..., mode yol-3-hybrid) with the SAME 5-gate methodology.
The EDGE-6 +12.9pp claim used the BROKEN D-200 universe (392 names, 291 wrongly
excluded, rights/TERP unadjusted, +/-50% return clip) -> INVALID; D-203 corrects it.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like k2_tilt_config / value_only_regime_config,
this holds pre-registered measurement knobs frozen at Stage-0. The GATE DECISION
THRESHOLDS (pass/fail constants) live in src/signals/thresholds.py (D203_* block, per
the CLAUDE.md "tek kaynak" mandate + the CLEAN_UNIVERSE_* precedent); this module only
holds GEOMETRY (lookbacks, regime splits, windows, snapshot hashes) and re-exports the
gate constants so the engine has a single import surface.

Three candidates (N<=3 lock):
  ADAY-A  VALUE-ONLY   : book-to-market bm=equity/mktval (=1/PBV) PRIMARY; ey=E/P robustness.
  ADAY-B  EDGE-2 COMP  : equal-weight rank-avg of mom120 + hi52 + lowvol63 (the core claim).
  ADAY-C  52WK-HIGH    : George-Hwang proximity-to-252d-high, ISOLATED.

Two regime splits (maintainer correction-1): PRIMARY 2022-01-01 (calendar-year boundary;
inflation regime accelerated 2021->2022), SECONDARY 2022-07-01 (edge-arastirma/smart_money
continuity; TLREF-carry data start). Gate-3 decided on PRIMARY; SECONDARY reported.

Two windows (maintainer correction-2): PRIMARY common 2019-07..2026-04 (degoran+TUFE overlap;
all three apples-to-apples); B/C also reported EXTENDED 2019-01..2026-04 (price-only).
"""
from __future__ import annotations

from src.screening import k2_tilt_config as _k2
from src.signals import thresholds as _th

D203_CONFIG_VERSION = "d203-v1"

# ---------------------------------------------------------------------------
# Windows. PRIMARY common window is the degoran-fundamentals + TUFE overlap so the
# three candidates are compared apples-to-apples. B/C (price-only) ALSO reported on
# the EXTENDED window; the window difference is stated explicitly in the verdict.
# ---------------------------------------------------------------------------
D203_COMMON_WINDOW_START = "2019-07-01"     # degoran fundamentals start (covers ADAY-A)
D203_COMMON_WINDOW_END = "2026-04-30"       # degoran/TUFE coverage end
D203_EXTENDED_WINDOW_START = "2019-01-01"   # B/C price-only extended start
D203_EXTENDED_WINDOW_END = "2026-04-30"

# ---------------------------------------------------------------------------
# Rebalance: MONTHLY (last trading day of each month). edge-arastirma EDGE-2 is a
# monthly top-15 EW rotation -> we match its cadence (NOT the k2 semi-annual calendar).
# ---------------------------------------------------------------------------
D203_REBALANCE = "monthly_last_trading_day"

# ---------------------------------------------------------------------------
# Factor lookbacks (trading days). FROZEN; mirror the demo-lab definitions so the
# re-measurement is comparable. mom skips the most recent ~21d (1-month reversal).
# ---------------------------------------------------------------------------
D203_MOM_LOOKBACK = 120        # 120d price momentum (close[d-21]/close[d-120]-1)
D203_MOM_SKIP = 21             # skip most-recent month (reversal control)
D203_HI52_LOOKBACK = 252       # 52-week-high proximity window
D203_LOWVOL_WINDOW = 63        # 63d realized-vol (inverted -> low-vol = high rank)

# ADAY-A fundamentals are month-end snapshots known at end-of-month; consumers must
# lag >= 1 month (publication ~mid M+1) -> look-ahead safe. At a rebalance in month M
# we use the fundamentals row from month <= M-1.
D203_FUND_PUBLICATION_LAG_MONTHS = 1
D203_VALUE_PRIMARY = "bm"      # book-to-market = equity/mktval = 1/PBV (higher = cheaper)
D203_VALUE_ROBUST = "ey"       # earnings yield = net_profit/mktval (higher = cheaper)

# ---------------------------------------------------------------------------
# Composite (ADAY-B). EQUAL-WEIGHT cross-sectional rank average (invariant: NO weight
# optimization, no z-score scaling that could be tuned). A name needs all three
# factors present to receive a composite rank.
# ---------------------------------------------------------------------------
D203_COMPOSITE_RULE = "equal_weight_rank_average"
D203_EDGE2_FACTORS = ("mom120", "hi52", "lowvol63")
D203_REQUIRE_ALL_FACTORS = True

# ---------------------------------------------------------------------------
# Regime splits (maintainer correction-1). PRIMARY decides Gate-3; SECONDARY reported for
# robustness. A period is assigned to a side by its START date.
# ---------------------------------------------------------------------------
D203_REGIME_SPLITS = ("2022-01-01", "2022-07-01")
D203_REGIME_PRIMARY = "2022-01-01"
D203_REGIME_SECONDARY = "2022-07-01"
D203_REGIME_RATIONALE = (
    "PRIMARY 2022-01-01: calendar-year boundary matching the directive language "
    "'2019-21 vs 2022-26'; TR inflation regime accelerated end-2021 into 2022 (not "
    "arbitrary). SECONDARY 2022-07-01: edge-arastirma/edge-arastirma continuity + the "
    "date TLREF-carry data begins. Gate-3 decided on PRIMARY; SECONDARY robustness-only."
)

# ---------------------------------------------------------------------------
# Selection. Fixed top-15 EW basket (and bottom-15 for the long-short spread). NOT a
# fraction -> no fraction-sweep optimization path. Long-short = top15 - bottom15
# nets out beta + survivorship.
# ---------------------------------------------------------------------------
D203_TOP_N = _th.D203_TOP_N                          # 15
D203_MIN_POOL_N = 2 * D203_TOP_N                     # need >=30 names for top15/bottom15 disjoint
D203_LIQUIDITY_TERCILE = _th.D203_LIQUIDITY_TERCILE  # 1/3
D203_LIQUIDITY_TRAILING_DAYS = 63                    # trailing median value_tl window for tercile

# ---------------------------------------------------------------------------
# Gate decision thresholds -- re-exported from thresholds.py (single source).
# ---------------------------------------------------------------------------
D203_GATE_NULL_PCTILE = _th.D203_GATE_NULL_PCTILE        # 0.95
D203_GATE_NW_T_MIN = _th.D203_GATE_NW_T_MIN              # 2.0
D203_GATE_COST_LOW_BPS = _th.D203_GATE_COST_LOW_BPS      # 20.0
D203_GATE_COST_HIGH_BPS = _th.D203_GATE_COST_HIGH_BPS    # 100.0
D203_DAILY_RETURN_CLIP = _th.D203_DAILY_RETURN_CLIP      # 0.10
D203_NW_LAGS = 3   # HAC Bartlett bandwidth for monthly (non-overlapping) return series

# ---------------------------------------------------------------------------
# Fair null + significance + bootstrap -- REUSE the K2 frozen knobs verbatim so the
# armored backtest matches D-191/D-Y1-001 exactly.
# ---------------------------------------------------------------------------
D203_NULL_SEED = _k2.K2_NULL_SEED                # 12345
D203_NULL_N_RESAMPLES = _k2.K2_NULL_N_RESAMPLES  # 2000
D203_SIG_BLOCK = _k2.K2_SIG_BLOCK                # 1
D203_SIG_N_BOOT = _k2.K2_SIG_N_BOOT              # 2000
D203_SIG_SEED = _k2.K2_SIG_SEED                  # 12345

# Tax/dividend drag reused (BIST 0% capgains; 15% dividend withholding approx).
D203_DIV_WITHHOLDING = _k2.K2_DIV_WITHHOLDING            # 0.15
D203_ASSUMED_ANNUAL_DIV_YIELD = _k2.K2_ASSUMED_ANNUAL_DIV_YIELD  # 0.03

# ---------------------------------------------------------------------------
# Frozen snapshots (offline, content-hash reproducible). Price + membership come
# from the junctioned D-202 clean_universe; fundamentals from the D-203 FAZ-0 freeze;
# TUFE from the D-187 frozen daily index.
# ---------------------------------------------------------------------------
D203_CLEAN_UNIVERSE_ROOT = "data/clean_universe"
D203_PRICE_PARQUET = "adjusted_prices_2019_2026.parquet"
D203_MEMBERSHIP_PARQUET = "pit_membership_2019_2026.parquet"
D203_FUND_PARQUET = "fundamentals_2019_2026.parquet"
D203_PRICE_CONTENT_HASH = "fd207550da312b19"        # D-202 adjusted_prices (first 16)
D203_FUND_CONTENT_HASH = "d72a69774a1c9f03"         # D-203 FAZ-0 fundamentals (first 16)
D203_TUFE_SNAPSHOT = "exposure_d187_tufe"           # data/snapshots/<>.parquet (date,value)

# ---------------------------------------------------------------------------
# Candidate registry (N<=3 lock).
# ---------------------------------------------------------------------------
D203_CANDIDATES = ("value", "edge2", "hi52")
D203_CANDIDATE_LABELS = {
    "value": "ADAY-A VALUE-ONLY (bm=1/PBV primary, ey=E/P robustness)",
    "edge2": "ADAY-B EDGE-2 COMPOSITE (mom120 + hi52 + lowvol63, equal-weight rank-avg)",
    "hi52": "ADAY-C 52WK-HIGH ISOLATED (George-Hwang proximity)",
}
# ADAY-A needs fundamentals -> common window only. B/C reported on both windows.
D203_CANDIDATE_WINDOWS = {
    "value": ("common",),
    "edge2": ("common", "extended"),
    "hi52": ("common", "extended"),
}

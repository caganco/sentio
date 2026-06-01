"""Value-only REGIME-RESILIENCE test -- frozen Stage-0 parameters. D-Y1-001.

MEASUREMENT parameters (NOT thresholds.py): like faz0_config / k2_tilt_config /
trend_d186_config, these are pre-registered measurement knobs, frozen at Stage 0
via a dated commit and NOT changed after results are seen (pre-registration
discipline). thresholds.py is the SIGNAL-engine constant source; backtest/
measurement labs keep their own frozen config (architecture invariant: these
modules must NOT import signals.thresholds).

Resolves the Faz-0 (D-183) <-> D-191 conflict for the VALUE factor in isolation:
  Faz-0 value rank-IC WEAK (honest_t<2)   vs   D-191 value-only tilt STRONG
  (fair-null %99.6, TL-real CI>0). RR-Y1.md sec.SORU-1 shows this is not a bug
  but a known methodological signature (rank-IC spans the whole cross-section;
  tercile/decile tilt only the extreme deciles). RR-Y1 also warns BIST value is
  REGIME-UNSTABLE -> the decisive question is regime-resilience, not a single t>2.

Dayanak: RR-Y1.md sec.SORU-1 (conflict resolution) + Recommendations Soru-1 #1
(same-sample rank-IC + decile MR test) and #3 (single-subperiod t>2 INSUFFICIENT;
need >=2 independent subperiods consistent sign). D-191 k2_* infra reused read-only.

Decision owner: Orchestrator+Cagan (DEC-039); harness MEASURES + RECOMMENDS.
SINGLE-FACTOR (no composite); MEASURE-ONLY (Yol-2 overlay candidate at most, <=10-20%).
"""
from __future__ import annotations

from src.screening import k2_tilt_config as _k2
from src.screening import trend_config as _trend

VOR_CONFIG_VERSION = "vor-v1"

# ---------------------------------------------------------------------------
# Window + rebalance (REUSE the frozen K2 calendar -> identical sample, so the
# AYAK-1 rank-IC and the tercile tilt are measured on the SAME observations,
# which is the whole point of the conflict-resolution leg).
# ---------------------------------------------------------------------------
VOR_WINDOW_START = _k2.K2_WINDOW_START          # 2019-01-01
VOR_WINDOW_END = _k2.K2_WINDOW_END              # 2026-04-30
VOR_REBALANCE_ANCHORS = _k2.K2_REBALANCE_ANCHORS  # (6, 12) semi-annual
VOR_INSAMPLE_END = _k2.K2_INSAMPLE_END          # 2022-12-31

# ---------------------------------------------------------------------------
# Universe + survivorship (REUSE K2 frozen pool). Survivors-only -> the measured
# tilt is an OPTIMISTIC upper bound; the fair null shares the SAME pool so the
# comparison stays fair (only the absolute level is inflated).
# ---------------------------------------------------------------------------
VOR_SURVIVORSHIP_BIAS = _k2.K2_SURVIVORSHIP_BIAS
VOR_BANKS = _k2.K2_BANKS

# ---------------------------------------------------------------------------
# Value metric. PRIMARY = book-to-market = 1/(P/B) (Fama-French HML); low P/B
# (cheap) -> high rank (invert=True on P/B). ROBUSTNESS = E/P (earnings yield) =
# net_income / market_cap; high E/P (cheap) -> high rank (invert=False). Both are
# point-in-time (latest annual with pub_date <= signal date, +lag) -> look-ahead
# safe. NO composite (value isolated).
# ---------------------------------------------------------------------------
VOR_VALUE_PRIMARY = "pb"          # book-to-market = 1/(P/B)
VOR_VALUE_ROBUST = "ep"           # earnings yield = E/P
VOR_PAR_VALUE = _k2.K2_PAR_VALUE
VOR_ANNUAL_LAG_DAYS = _k2.K2_ANNUAL_LAG_DAYS

# ---------------------------------------------------------------------------
# Selection. tercile (primary tilt), quintile (robustness), decile (AYAK-2
# monotonicity). N<=3 selection budget: tercile + quintile only; deciles are a
# monotonicity DIAGNOSTIC (not a sweep variant), like K2 single-factor portfolios.
# ---------------------------------------------------------------------------
VOR_TERCILE = _k2.K2_TERCILE      # 1/3
VOR_QUINTILE = _k2.K2_QUINTILE    # 1/5
VOR_N_DECILES = 10                # AYAK-2 decile monotonicity buckets
VOR_PRIMARY_VARIANT = "tercile"   # the tilt gated by Gate-1/Gate-2
VOR_SELECTION_VARIANTS = ("tercile", "quintile")  # N<=3 (deciles are diagnostic)
VOR_MIN_BASKET_N = _k2.K2_MIN_BASKET_N

# ---------------------------------------------------------------------------
# AYAK-1 rank-IC. Spearman cross-sectional IC of the value rank vs forward return
# at holding-period horizons (semi-annual ~ 126 trading days). honest_t = Newey-
# West HAC bandwidth = horizon (D-178 overlap correction). Reported alongside the
# tilt to expose the conflict signature (weak IC + strong tilt on the SAME data).
# DIAGNOSTIC, not a gate.
# ---------------------------------------------------------------------------
VOR_IC_HORIZONS = (63, 126)       # trading days (~quarter, ~half-year holding)
VOR_IC_MIN_XSECTION = 5           # min names/day for a valid cross-sectional IC

# ---------------------------------------------------------------------------
# AYAK-3 regime resilience (Gate-3, MOST CRITICAL). TWO splits (Cagan decision):
#   PRIMARY (decision gate): 3-way frozen INFLATION_REGIMES (pre_surge /
#     high_inflation / disinflation). Gate-3: >=2 of 3 regimes with consistent
#     positive sign.
#   ROBUSTNESS (side-check): 2-way simple split at VOR_REGIME_SPLIT_DATE
#     (pre/post 2023-01-01); thicker periods -> stronger statistics.
# READING RULE: 3-way and 2-way ALIGNED (both >=2-positive or both not) ->
#   decision STRONG. DIVERGENT -> value is REGIME-DEFINITION-SENSITIVE = FRAGILE
#   (not a stable premium; honest-closure direction). Single split is never trusted.
# These are two cuts of the SAME value measurement -> NOT a sweep, no N<=3 cost.
# ---------------------------------------------------------------------------
VOR_INFLATION_REGIMES = _trend.INFLATION_REGIMES   # frozen 3-way (D-186)
VOR_REGIME_SPLIT_DATE = "2023-01-01"               # 2-way robustness cut
VOR_GATE3_MIN_POSITIVE_REGIMES = 2                 # >=2 independent subperiods (RR-Y1 #3)

# ---------------------------------------------------------------------------
# Cost / tax / slippage + return bases + fair null + significance:
# REUSE K2 frozen knobs verbatim (same broker tier, slippage, withholding, null
# seed/resamples, block-bootstrap settings) so the armored backtest is identical
# to D-191 and the value-only result is directly comparable.
# ---------------------------------------------------------------------------
VOR_BROKER_TIER = _k2.K2_BROKER_TIER
VOR_SLIPPAGE_BPS = _k2.K2_SLIPPAGE_BPS
VOR_DIV_WITHHOLDING = _k2.K2_DIV_WITHHOLDING
VOR_ASSUMED_ANNUAL_DIV_YIELD = _k2.K2_ASSUMED_ANNUAL_DIV_YIELD

VOR_NULL_SEED = _k2.K2_NULL_SEED                   # 12345
VOR_NULL_N_RESAMPLES = _k2.K2_NULL_N_RESAMPLES     # 2000
VOR_SIG_BLOCK = _k2.K2_SIG_BLOCK                   # 1 (non-overlapping semi-annual)
VOR_SIG_N_BOOT = _k2.K2_SIG_N_BOOT                 # 2000
VOR_SIG_SEED = _k2.K2_SIG_SEED                     # 12345
VOR_DECISION_RANDOM_PCTILE_MIN = _k2.K2_DECISION_RANDOM_PCTILE_MIN  # 0.95

# ---------------------------------------------------------------------------
# Frozen snapshots (REUSE D-191 / D-187 frozen parquet -> fully offline,
# content-hash reproducible; NO live network on a measurement run).
# ---------------------------------------------------------------------------
VOR_PRICE_SNAPSHOT = "faz0_k2_prices_2019-01-01_2026-04-30"  # close + XU100 (D-191)
VOR_FUND_SNAPSHOT = "k2_fundamentals"                        # book/net_income (D-191)
VOR_FX_SNAPSHOT = "k2_fx_usdtry"                             # USD/TRY (D-191; partial early coverage)
VOR_TUFE_SNAPSHOT = "exposure_d187_tufe"                     # daily TUFE index (D-187, frozen offline)
VOR_US_CPI_SERIES = None                                     # None -> USD-nominal (labeled)

# ---------------------------------------------------------------------------
# Decision rule DEC-Y1 (FROZEN at Stage-0; post-hoc relaxation FORBIDDEN). Four
# gates; USD-real / XU100-relative are REPORTED, never gates.
#   Gate-1: net TL-real tercile tilt mean>0 AND block-bootstrap 95% CI excludes 0.
#   Gate-2: beats fair random-selection null (random_pctile >= 0.95).
#   Gate-3 (AYAK-3): PRIMARY 3-way regimes -> >=2 consistent-positive (single-
#           subperiod t>2 INSUFFICIENT, RR-Y1 #3); 2-way robustness alignment read.
#   Gate-4 (AYAK-2): decile profile EXPLAINABLE (cheap-minus-expensive spread>0 AND
#           premium concentrated at the cheap end: Spearman(decile, return)>0).
# PASS -> Yol-2 overlay candidate (<=10-20%, O+Cagan). PARTIAL (Gate-1&2 pass,
# Gate-4 explains conflict, Gate-3 fails) -> "value regime-dependent, not stable".
# FAIL -> value-only eliminated ("tried-and-refuted" archive).
# ---------------------------------------------------------------------------
VOR_GATE4_MIN_DECILE_SPREAD = 0.0     # cheap-minus-expensive net TL-real spread must be > this
VOR_GATE4_MIN_MONOTONICITY = 0.0      # Spearman(decile_idx -> cheap, return) must be > this

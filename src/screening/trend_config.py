"""D-185 Trend-Motor Test -- Stage 0 frozen parameters (pre-registration).

These are MEASUREMENT parameters, intentionally NOT in thresholds.py (same
precedent as faz0_config.py: thresholds.py is immutable production signal
constants; these are trend-test measurement params). Frozen at Stage 0 via a
dated commit and MUST NOT change after results are seen (pre-registration
discipline -- RR-039 + Faz 0 lesson against data-snooping).

Dayanak: RR-039 sec.6 (three rule variants A/B/C); RR-038 (modern BIST regime,
cost model: BSMV on commission, round-trip >= 0.3-0.5%); ARCHITECTURE v2.0
sec.3 (Katman A funnel) / sec.7.1 (per-trade expectancy gating).

DEC-039: this config drives MEASUREMENT only. Which variant (if any) becomes
the Katman A motor is an the project decision.

N<=3 LOCK: exactly three variants. parabolic-filter on/off and regime slices
are WITHIN-variant comparisons, NOT new rules (no N violation). Post-hoc
parameter sweeping is FORBIDDEN; every parameter below is frozen now.
"""
from __future__ import annotations

from src.screening.faz0_config import (  # reuse frozen Faz 0 inventory
    FAZ0_ADV_FLOOR_TL,
    FAZ0_ADV_MIN_DAYS,
    FAZ0_BIST100_CONSTITUENTS,
    KNOWN_DELISTED,
)

CONFIG_VERSION = "trend-test-v1"

# ---------------------------------------------------------------------------
# Universe + window
# ---------------------------------------------------------------------------
# Reuse the frozen Faz 0 v2 mechanical universe (BIST 100, point-in-time
# ~2025-2026). Survivorship gap (KNOWN_DELISTED, yfinance 404) is recorded in
# the snapshot meta + reported as a bias DIRECTION (survivors-only -> expectancy
# reads OPTIMISTIC -> results are an UPPER BOUND; if a variant cannot beat the
# random benchmark post-cost here, it definitely cannot in reality).
TREND_UNIVERSE = FAZ0_BIST100_CONSTITUENTS
TREND_UNIVERSE_SOURCE = "faz0_config.FAZ0_BIST100_CONSTITUENTS (BIST 100 PIT ~2025-2026)"

# 2019-2026: spans TL crisis, covid crash, 2021-22 retail bubble, high-inflation
# regime, 2024-26 disinflation -> exercises regime decomposition (RR-038).
TREND_SNAPSHOT_START = "2019-01-01"
TREND_SNAPSHOT_END = "2026-04-30"

# Liquidity floor. ADV primitive = snapshot._compute_adv (median daily TL =
# Close x Volume). NOTE (D-185 flagged substitution, the maintainer-approved): the
# directive named is_adv_eligible, but that needs a USD volume_3m_mn_usd shape
# the OHLCV snapshot does not carry; _compute_adv (TL) is the fitting reuse.
TREND_ADV_FLOOR_TL = FAZ0_ADV_FLOOR_TL      # 50M TL/day median
TREND_ADV_MIN_DAYS = FAZ0_ADV_MIN_DAYS      # 60

# ---------------------------------------------------------------------------
# Common timing + indicators (all variants)
# ---------------------------------------------------------------------------
# Signal computed at t close; entry at t+1 open (look-ahead guard). Long-only,
# daily bars, week-to-month holding.
ATR_WINDOW = 14
VOLUME_MA_WINDOW = 20
VOLUME_CONFIRM_MULT = 1.2          # breakout-bar volume >= 1.2 x avg(20)
MAX_HOLD_DAYS = 126                # safety cap (~6 months); trailing usually earlier

# ---------------------------------------------------------------------------
# Parabolic-avoidance filter (entry block). Tested ON and OFF (RR-039 gap #2).
# ---------------------------------------------------------------------------
# Block a NEW BUY if ANY of: price > (1+dev) x 20-SMA, OR RSI(14) > rsi_max, OR
# distance from last swing low > swing_atr_mult x ATR. Used as an entry FILTER
# (not a reversal/short signal) -- RR-039 sec.2.5.
PARABOLIC_SMA_WINDOW = 20
PARABOLIC_SMA_DEV_PCT = 0.20       # 20% above 20-SMA = overextended (frozen pick)
PARABOLIC_RSI_WINDOW = 14
PARABOLIC_RSI_MAX = 75.0
PARABOLIC_SWING_LOW_ATR_MULT = 5.0

# ---------------------------------------------------------------------------
# Variant A -- S/R-Flip Retest (the maintainer core intuition; tested FIRST)
# ---------------------------------------------------------------------------
A_SWING_LOOKBACK_DAYS = 252        # trailing window for swing peaks (~12 months)
A_FIND_PEAKS_DISTANCE = 5          # min bars between peaks (scipy find_peaks)
A_FIND_PEAKS_PROMINENCE_ATR = 1.0  # peak prominence >= 1 x ATR (meaningful swing)
A_CLUSTER_MERGE_ATR_MULT = 1.0     # AgglomerativeClustering distance ~ 1 x ATR
A_MIN_TOUCHES = 2                  # >= 2 touches -> a resistance zone
A_BREAKOUT_BUFFER_PCT = 0.005      # close > resistance x (1 + 0.005)
A_RETEST_TOL_ATR_MULT = 0.5        # |price - level| <= 0.5 x ATR on retest
A_RETEST_WINDOW_BARS = 10          # retest must occur within 10 bars of breakout
A_STOP_ATR_MULT = 1.5              # stop = level - 1.5 x ATR
A_TRAIL_DONCHIAN_N = 20            # exit: 20-day Donchian-low trailing

# ---------------------------------------------------------------------------
# Variant B -- Consolidation Breakout (squeeze)
# ---------------------------------------------------------------------------
B_BBW_WINDOW = 20                  # Bollinger 20/2sigma for bandwidth
B_BBW_STD = 2.0
B_BBW_LOOKBACK_DAYS = 126          # trailing 6 months for BBW percentile
B_BBW_LOW_PCTILE = 0.25            # BBW in bottom quartile -> consolidation
B_USE_NR7 = True                   # OR: narrowest range of last 7 bars
B_BOX_WINDOW = 20                  # consolidation box = max/min over last 20 bars
B_ADX_WINDOW = 14
B_ADX_MIN = 20.0                   # ADX>20 or rising (trend filter)
B_TRAIL_DONCHIAN_N = 20            # exit: 20-day Donchian-low trailing
B_STOP_USES_BOX_LOW = True         # stop = consolidation lower bound

# ---------------------------------------------------------------------------
# Variant C -- Trend-start Donchian + retest
# ---------------------------------------------------------------------------
C_DONCHIAN_N = 20                  # Donchian-20 upper breakout trigger
C_ADX_WINDOW = 14
C_ADX_MIN = 20.0                   # ADX>20-25 filter (frozen at 20)
C_RETEST_EMA = 20                  # pullback hold at 20-EMA / old Donchian-upper
C_RETEST_TOL_ATR_MULT = 0.5
C_RETEST_WINDOW_BARS = 10
C_STOP_ATR_MULT = 1.5
C_TRAIL_DONCHIAN_N = 20
C_REQUIRE_HH_HL = True             # higher-high + higher-low structure required

# ---------------------------------------------------------------------------
# Cost model (RR-038: BSMV charged on commission, round-trip >= 0.3-0.5%)
# ---------------------------------------------------------------------------
COST_SCENARIOS_BPS = (30, 50, 80)  # round-trip basis points: 0.3% / 0.5% / 0.8%
PRIMARY_COST_BPS = 50              # headline scenario

# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------
# Random-entry: match each variant's trade COUNT and holding-duration
# distribution, draw random (ticker, entry-date) pairs, recompute post-cost
# expectancy. Repeat N_RESAMPLES times -> null distribution. Edge is real only
# if observed expectancy exceeds the RANDOM_PCTILE_MIN quantile of this null.
RANDOM_BENCHMARK_SEED = 12345
RANDOM_BENCHMARK_N_RESAMPLES = 1000
# Buy-and-hold: equal-weight universe, post-cost, same window (net-of-cost).

# ---------------------------------------------------------------------------
# Significance machinery (reuse factor_ic_harness: newey_west_se + bootstrap)
# ---------------------------------------------------------------------------
BOOTSTRAP_N = 2000
BOOTSTRAP_BLOCK = 21               # ~1 month block (calendar-overlapping trades)
BOOTSTRAP_SEED = 12345
NW_LAGS = 5                        # HAC lag for time-ordered daily PnL t-stat

# ---------------------------------------------------------------------------
# Regime decomposition (frozen boundaries)
# ---------------------------------------------------------------------------
# Market state: deterministic XU100 200-day MA. bull = close>MA & MA rising;
# bear = close<MA & MA falling; sideways = otherwise.
REGIME_MA_WINDOW = 200
# Inflation regime: fixed calendar slices (TR CPI history; frozen, not tuned).
INFLATION_REGIMES = (
    ("pre_surge", "2019-01-01", "2021-09-30"),
    ("high_inflation", "2021-10-01", "2024-06-30"),
    ("disinflation", "2024-07-01", "2026-04-30"),
)

# ---------------------------------------------------------------------------
# Gating (AND) + failure thresholds (RR-039 sec.5)
# ---------------------------------------------------------------------------
GATE_EXPECTANCY_MIN_R = 0.0        # post-cost per-trade expectancy must be > 0
GATE_EXPECTANCY_T_MIN = 2.0        # statistically significant (~95%, HAC t)
GATE_RANDOM_PCTILE_MIN = 0.95      # must beat 95th pctile of random-entry null
GATE_MAX_DD_FAIL = 0.35            # fail if max drawdown > 35%
GATE_MAX_DD_WARN = 0.25            # warn at 25%
GATE_SINGLE_REGIME_PNL_MAX = 0.80  # fail if >80% of net PnL from one regime slice
GATE_REGIME_MIN_POSITIVE_STATES = 2  # expectancy>0 in >=2 of {bull,bear,sideways}

# ---------------------------------------------------------------------------
# N<=3 lock
# ---------------------------------------------------------------------------
VARIANTS = ("A_sr_flip_retest", "B_consolidation_breakout", "C_donchian_retest")
FILTER_MODES = ("parabolic_on", "parabolic_off")
N_VARIANTS = 3

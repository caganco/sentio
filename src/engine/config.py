"""Frozen configuration for the RR-Y1-005 validation engine.

Single source of truth for the engine's structural constants and frozen-default
dial values (math-spec v1.1 Section 8). The *tunable* surface is passed per-run
via ``DialConfig`` / ``SplitSpec`` (contracts.py); the defaults there point here.

Paths are repo-relative -- ``Path(__file__).resolve().parents[2]`` is the repo
root (engine -> src -> root). No machine-specific absolute path appears here
(public-repo commit hygiene).
"""
from __future__ import annotations

from pathlib import Path

# --- repo-relative data layer (Section 9: clean_universe + snapshots, NOT DataHub) ---
REPO_ROOT = Path(__file__).resolve().parents[2]
CLEAN_UNIVERSE = REPO_ROOT / "data" / "clean_universe"
SNAPSHOTS = REPO_ROOT / "data" / "snapshots"

PRICES_FILENAME = "adjusted_prices_2019_2026.parquet"
FUNDAMENTALS_FILENAME = "fundamentals_2019_2026.parquet"
PRICES_PARQUET = CLEAN_UNIVERSE / PRICES_FILENAME
FUNDAMENTALS_PARQUET = CLEAN_UNIVERSE / FUNDAMENTALS_FILENAME

# snapshot series (long form: columns date, value)
MARKET_SERIES = "exposure_d187_xu100"  # market index -> beta neutralization (Section 3.5)
TUFE_SERIES = "exposure_d187_tufe"  # CPI -> real-deflate + benchmark floor (Section 7)
TLREF_SERIES = "exposure_d187_tlref"  # TLREF -> benchmark floor from 2022-07

# --- panel window (clib parity) ---
PANEL_START = "2019-01-01"
PANEL_END = "2026-05-26"
REGIME_SPLIT = "2022-01-01"  # manual regime label boundary (Section 4.3)

# --- liquidity floor (recon B7; clib parity) ---
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
TRADING_DAYS_YR = 252.0

# --- frozen statistical parameters (math-spec v1.1 Section 8) ---
IC_TYPE = "spearman"  # dial 1: cross-sectional rank-IC
MIN_NAMES_CROSS_SECTION = 30  # min names to compute IC_t for a date
FORWARD_RETURN_BASIS = "tr_index_gross"  # total-return (Section 3.5/C5); net is a dial
NW_LAG_DAILY = 5
NW_LAG_MONTHLY = 3
# FAZ-4 near-zero-variance floor for nw_tstat. A numerically-constant input has a
# tiny-but-POSITIVE HAC variance (inexact-float FP rounding leaves s ~ 1e-32) that
# slips past the s<=0 guard and yields an explosive spurious t. The guard returns NaN
# when s <= eps*mean^2, i.e. relative variance s/mean^2 <= eps. eps=1e-12 sits two
# decades below the smallest LEGITIMATE relative variance (test_perfect_signal ~1e-10)
# and far below the C12 golden's (~1e2), so it fires ONLY on degenerate input -- the
# golden byte-repro and the d211/d213 equivalence never trip it.
NW_VAR_FLOOR_EPS = 1e-12
WINSORIZE_LOWER = 0.01
WINSORIZE_UPPER = 0.99

# factor neutralization (gap c; Section 3.5) -- market-only is the Mod-A minimum
BETA_WINDOW_DAYS = 126
BETA_MIN_COVERAGE = 0.8  # require >= 0.8 * W observations in the trailing window
NEUTRALIZATION_FACTORS_DEFAULT: tuple[str, ...] = ("market",)
ALLOWED_FACTORS: frozenset[str] = frozenset({"market", "size", "value", "sector"})

# conjugate agreement (gap b; Section 4.1) -- 3-part PASS bar
SPLIT_R_MIN = 50  # seed-fixed name-splits (Mod-A)
MIN_NAMES_PER_ARM = 50  # Section 3.3: each arm >= 50 names
AGREEMENT_CROSS_IC_T_MIN = 2.0  # median_R(t_IC_cross) > 2.0 in BOTH directions
SIGN_CONSISTENCY_MIN = 0.90
PBO_THRESHOLD = 0.50  # REAL CSCV median-rank (Lopez de Prado) -- NOT the Mod-B proxy
# PBO median-rank axis: decile-fixed, DECOUPLED from the tilt's sort_depth dial. Coupling the
# overfit-measurement resolution to a strategy knob would open a post-hoc degree-of-freedom
# ("we tried tercile-PBO and it dropped"); a frozen constant (not a dial) closes that.
PBO_N_BUCKETS = 10
MIN_NAMES_PER_BUCKET = 3  # degenerate-bucket guard: a bucket below this -> NaN (bucket-analog of
#                           the NW near-zero-variance guard; stops a thin bucket faking a winner)

# residual cross-sectional correlation (Section 4.2) -- SEPARATE from agreement (4.3 mixing-ban)
RESIDUAL_CORR_NULL_PCTILE = 95
RESIDUAL_NULL_RESAMPLES = 200  # random re-splits that build the permutation rho_arms null

# CPCV (Mod-B temporal; daily). Monthly temporal-CPCV is forbidden -> Mod-A mandatory.
CPCV_DAILY_N = 10
CPCV_DAILY_K = 2
MONTHLY_TEMPORAL_CPCV_FORBIDDEN = True

# DSR (Section 4.2)
DSR_MIN = 0.95
# FAZ-4 (b): trial-count deflation. The honest tried-config count N (Stage-0
# denenen_konfig_sayisi) feeds the Bailey-LdP E[max] order statistic, which becomes
# compute_dsr's benchmark_sr -> the canonical deflated DSR. N=1 -> E[max]=0 -> no
# deflation -> DSR byte-identical to the pre-FAZ-4 call (zero regression). Multiple-test
# / search overfit is the DSR layer's job -- NOT bucket-PBO (single-prototype-internal).
EULER_MASCHERONI = 0.5772156649  # same constant as statistical_validation.min_btl_days
DSR_DEFAULT_N_TRIALS = 1  # no Stage-0 -> assume a single trial -> no deflation

# benchmark floor (Section 7): real return must beat max(TUFE, TLREF); TLREF from 2022-07
BENCHMARK_TLREF_FROM = "2022-07"

# --- C12 golden hard-gate (Faz-3, Section 8.1) ---
# Frozen reference the real-data determinism anchor reproduces: the C12 ALL-universe
# walk-forward conjugate-OOS pooled daily active-return series (committed as the ASCII
# fixture tests/fixtures/c12_golden_active.csv). The NW-t values are the c9._nw_t
# headline numbers (lab results JSON, frozen 2026-06-04); the engine's nw_tstat shares
# c9's population-variance convention, so it reproduces them on the same pooled series.
# This is ONE of three correctness layers (the anti-silent-error / off-by-one-purge-leak
# determinism anchor) -- NOT the proof the engine is methodologically correct (that stays
# on the 3 synthetic Mod-A fixtures + the synthetic-null). C12 is gross-only/cost-killed.
C12_GOLDEN_NW_LAG = 10  # HAC bandwidth for the daily pooled series (c12 NW_LAG)
C12_GOLDEN_GROSS_NWT = 6.928414  # nw_tstat(pooled gross active, lag=10) -- the daily dependency EXISTS
C12_GOLDEN_NET_NWT = -6.274774  # nw_tstat(pooled net active, lag=10) -- D-207 cost FLIPS it negative
C12_GOLDEN_N_POOLED = 1375  # pooled conjugate-validation days (ALL universe)
C12_GOLDEN_TRADING_DAYS_YR = 252.0  # annualization factor (c12 TRADING_DAYS_YR)
C12_GOLDEN_REGIME_CUT = "2022-01-01"  # pre/post regime mask on the pooled return-dates (c12 REGIME_CUT)
C12_GOLDEN_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "c12_golden_active.csv"
C12_GOLDEN_META = REPO_ROOT / "tests" / "fixtures" / "c12_golden_meta.json"

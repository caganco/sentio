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

# residual cross-sectional correlation (Section 4.2) -- SEPARATE from agreement (4.3 mixing-ban)
RESIDUAL_CORR_NULL_PCTILE = 95

# CPCV (Mod-B temporal; daily). Monthly temporal-CPCV is forbidden -> Mod-A mandatory.
CPCV_DAILY_N = 10
CPCV_DAILY_K = 2
MONTHLY_TEMPORAL_CPCV_FORBIDDEN = True

# DSR (Section 4.2)
DSR_MIN = 0.95

# benchmark floor (Section 7): real return must beat max(TUFE, TLREF); TLREF from 2022-07
BENCHMARK_TLREF_FROM = "2022-07"

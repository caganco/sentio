"""D-206 NAV-iskonto-Z mean-reversion -- frozen Stage-0 MEASUREMENT geometry. TIME-SERIES.

Cross-sectional factor selection is EXHAUSTED (hi52 KAPANDI D-205, lowvol63 ELENDI NRR-007,
value-regime ELENDI NRR-008 -- 3/3 closed). Cagan+O decision: a NEW paradigm -- per-holding
NAV-discount MEAN-REVERSION (time-series, low-turnover, retail-suited). This is NOT cross-
sectional: each holding has its OWN discount time-series and is standardized against its OWN
history. HYPOTHESIS (Pontiff 1995, CEF premia mean-revert, half-life 7.7-10.3mo): a HIGH
discount-Z (discount wide -> holding cheap) predicts a POSITIVE forward return.

HONEST EXPECTATION (BEFORE results): UNCERTAIN. Holding-discount MR is well-documented for US
CEFs but UNTESTED on BIST holdings; N is small (6-8 holdings). Elimination is a clean, valuable
result. NO celebration. This is the FIRST NAV-discount reading (N<=3 lock); if a signal appears,
the FULL RR-013 architecture is a SEPARATE next step (O+Cagan) -- this is measurement-ONLY.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d203/d204/nrr008, this holds the pre-registered
GEOMETRY frozen at Stage-0; DECISION constants live in src/signals/thresholds.py (D206_*) and
COST mechanics reuse D204_* (realistic_cost.py). The committed engine is NOT modified.

DATA (corp-action archive is EMPTY -> no adjusted prices pre-2019):
  * Signal: per-holding monthly NAV-discount from degoran market caps, 2009-01..2026-04 (the
    legacy 'degoranYYYYMM.zip' monthly files unlock 2009-2019; see clean_universe_fundamentals
    file_glob='degoran*.zip'). discount-Z standardizes per-holding -> insensitive to a constant
    share-% bias (DECLARED). NAV = sum(stake_i * subsidiary_market_cap_i), listed subsidiaries
    only; net-cash/unlisted omitted (a near-constant level absorbed by the Z-score, DECLARED).
  * Forward return: mktval-implied total return = mktval(t+h)/mktval(t)-1 + dividends (degoran
    net_div), UNIFORM across 2009-2026. Market cap is continuous through splits/bonus; rights
    issues are rare and DECLARED. A FIDELITY-GUARD validates this proxy against the frozen
    adjusted_close panel on the 2019-2026 overlap (engine RAISES if it fails).

The holding composition (universe + stakes + net-cash) is FROZEN in docs/yol1/STAGE0_d206.json
(committed; config/holdings.yaml is gitignored / CI-invisible, so Stage-0 carries the geometry).

D-206 is the FIRST NAV-discount measurement (N<=3 lock).
"""
from __future__ import annotations

from pathlib import Path

from src.screening import d203_config as _d203
from src.screening import d204_config as _d204
from src.signals import thresholds as _th

D206_CONFIG_VERSION = "d206-v1"

# ---------------------------------------------------------------------------
# Frozen price/fundamentals snapshots -- REUSE D-203/204 for the FIDELITY-GUARD overlap.
# ---------------------------------------------------------------------------
D206_CLEAN_UNIVERSE_ROOT = _d204.D204_CLEAN_UNIVERSE_ROOT
D206_PRICE_PARQUET = _d203.D203_PRICE_PARQUET            # adjusted_prices_2019_2026.parquet
D206_PRICE_CONTENT_HASH = _d204.D204_PRICE_CONTENT_HASH  # fd207550... (FIDELITY-GUARD overlap)
D206_TUFE_SNAPSHOT = _d203.D203_TUFE_SNAPSHOT            # exposure_d187_tufe (TUFE-deflation)
D206_TLREF_SNAPSHOT = "exposure_d187_tlref"              # real-TLREF carry-trap control (2022-07+)

# ---------------------------------------------------------------------------
# Extended degoran monthly fundamentals (2009-2026) -- the SIGNAL + return source.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent.parent
D206_ARCHIVE_FR_DIR = _REPO_ROOT / "data" / "bist_datastore_archive" / "fundamental_ratios"
D206_FUND_FILE_GLOB = "degoran*.zip"   # includes legacy 'degoranYYYYMM.zip' (2009-2019 monthly)
D206_FUND_START = "2009-01"            # monthly degoran begins 2009-01 (legacy files)
D206_FUND_END = "2026-12"              # loader clamps to the latest available month
D206_OVERLAP_START = _d204.D204_COMMON_WINDOW_START   # 2019-07-01 (FIDELITY-GUARD window start)
D206_OVERLAP_END = _d204.D204_COMMON_WINDOW_END       # 2026-04-30 (FIDELITY-GUARD window end)

# ---------------------------------------------------------------------------
# discount-Z geometry (FROZEN; structural constants, not tuned). thresholds.py owns the numbers.
# ---------------------------------------------------------------------------
D206_TRAILING_WINDOW_MONTHS = _th.D206_TRAILING_WINDOW_MONTHS   # 36
D206_TRAILING_MIN_PERIODS = _th.D206_TRAILING_MIN_PERIODS       # 24
D206_PRIMARY_HORIZON_MONTHS = _th.D206_PRIMARY_HORIZON_MONTHS   # 6 (PRIMARY, single, frozen)
D206_SECONDARY_HORIZONS = _th.D206_SECONDARY_HORIZONS           # (1, 3) context-only
D206_PUBLICATION_LAG_MONTHS = _th.D206_PUBLICATION_LAG_MONTHS   # 1 (subsidiary mktval t-1 lag)

# ---------------------------------------------------------------------------
# Gate decision constants -- REUSE thresholds.py D206_* (single source).
# ---------------------------------------------------------------------------
D206_GATE_NW_T_MIN = _th.D206_GATE_NW_T_MIN                # 2.0
D206_GATE_NULL_PCTILE = _th.D206_GATE_NULL_PCTILE          # 0.95
D206_GATE_SAME_SIGN_FRAC = _th.D206_GATE_SAME_SIGN_FRAC    # 0.80
D206_NULL_N_RESAMPLES = _th.D206_NULL_N_RESAMPLES          # 2000
D206_NULL_SEED = _th.D206_NULL_SEED                        # 12345
D206_WILD_BOOT_N = _th.D206_WILD_BOOT_N                    # 2000
D206_REGIME_PRIMARY = _th.D206_REGIME_PRIMARY              # 2022-01-01
D206_REGIME_LOWINFL_END = _th.D206_REGIME_LOWINFL_END      # 2017-01-01
D206_STRATEGY_ENTRY_Z = _th.D206_STRATEGY_ENTRY_Z          # 1.0
D206_STRATEGY_EXIT_Z = _th.D206_STRATEGY_EXIT_Z            # 0.0
D206_FIDELITY_MIN_CORR = _th.D206_FIDELITY_MIN_CORR        # 0.95
D206_FIDELITY_MAX_MAE = _th.D206_FIDELITY_MAX_MAE          # 0.03

# ---------------------------------------------------------------------------
# Realistic-cost geometry -- REUSE D-204 verbatim (gate-5; daily-price-based, 2019-2026 only).
# ---------------------------------------------------------------------------
D206_PORTFOLIO_TL = _d204.D204_PORTFOLIO_TL
D206_ORDER_VALUE_TL = _d204.D204_ORDER_VALUE_TL
D206_ADV_WINDOW = _d204.D204_ADV_WINDOW
D206_ROLL_WINDOW = _d204.D204_ROLL_WINDOW
D206_LAMBDA_KYLE = _d204.D204_LAMBDA_KYLE
D206_BREAKEVEN_BPS_GRID = _d204.D204_BREAKEVEN_BPS_GRID
D206_BREAKEVEN_SAFETY_MULT = _d204.D204_BREAKEVEN_SAFETY_MULT

# ---------------------------------------------------------------------------
# Candidate lock (N=1). NAV-discount MR -- the FIRST NAV-discount round (N<=3).
# ---------------------------------------------------------------------------
D206_CANDIDATE = "nav-discount-mr"
D206_CANDIDATE_LABEL = (
    "NAV-iskonto-Z mean-reversion (per-holding TIME-SERIES: NAV=sum(stake*listed-sub-market-cap), "
    "discount-Z = trailing-36m standardized per-holding, look-ahead-safe; HIGH discount-Z -> "
    "POSITIVE forward return) -- D-206 NAV-discount FIRST round (N<=3), measurement-only")

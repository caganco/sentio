"""D-213 (RR-Y1-003) -- frozen Stage-0 MEASUREMENT geometry. Yol-1-lab.

Cerceve-B continuous time-series forecast: does ex-ante real-rate (nominal funding
rate minus 12m-expected inflation, in the ~t+15g-knowable form r_ex_ante(t-1)) predict
next-month XU100 TL-REAL return? Single-asset timing (index-long vs cash). NOT stock
selection. PRICE-ORTHOGONAL axis.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d211_config, this holds pre-registered
measurement knobs frozen at Stage-0 (STAGE0_d213.json). The DECISION THRESHOLDS live in
src/signals/thresholds.py (D213_* block, per the PROJECT_GUIDE.md tek-kaynak mandate); this
module holds GEOMETRY (window, predictor/dependent/cash-leg definitions, snapshot hashes,
cost params) and re-exports the gate constants for a single import surface.

STRANGLER: committed motors (d203/204/205/209/211 + realistic_cost + thresholds existing
blocks + evds_client) are NOT modified. EVDS raw data does NOT enter CI; the real run is a
local artifact (d213_results.json). HTTP-free at run time (reads frozen snapshots).

Dayanak: STAGE0_d213.json (frozen 2026-06-04); docs/yol1/RR-Y1-003-asama0-veri.md (D-212
data facts); realistic_cost.py D-207 cost mechanics; NW stats ported from d211_foreign_flow.
"""
from __future__ import annotations

from pathlib import Path

from src.signals import thresholds as _th

D213_CONFIG_VERSION = "d213-v1"

# ---------------------------------------------------------------------------
# Window. Coverage-guard (STAGE0_d213) verified ALL legs clean from 2019-01
# (predictor APIFON4+ENFBEK, dependent XU100+TUFE, cash-leg APIFON4-carry).
# TLREF excluded (silent-NaN until 2022-07). Effective = 2019-01..2026-04.
# ---------------------------------------------------------------------------
D213_WINDOW_START = "2019-01-01"
D213_WINDOW_END = "2026-04-30"

# ---------------------------------------------------------------------------
# Predictor (LOCK -- alternative-definition mining FORBIDDEN).
#   r_ex_ante(t) = nominal(t) - expected_inf(t)      [annual pct points, LEVEL]
#   To predict return-month t, use r_ex_ante(t - LOOKAHEAD_LAG_MONTHS).  (~t+15g)
#   change/impulse form is SECONDARY-only and cannot rescue primary.
# ---------------------------------------------------------------------------
D213_LOOKAHEAD_LAG_MONTHS = _th.D213_LOOKAHEAD_LAG_MONTHS   # 1
D213_EXPOST_LAG_MONTHS = _th.D213_EXPOST_LAG_MONTHS         # 2 (ex-post control, secondary)
D213_SIGNAL_THRESHOLD = _th.D213_SIGNAL_THRESHOLD           # 0.0 (r_ex_ante<0 -> long)

# ---------------------------------------------------------------------------
# Dependent (LOCK). XU100 price-only nominal monthly return, TL-real via TUFE MoM.
#   real_ret(t) = r_nom(t) - infl(t)        (directive-literal subtraction). SAME as D-211.
# ---------------------------------------------------------------------------
D213_REAL_DEFLATE = "subtract_mom_tufe"

# ---------------------------------------------------------------------------
# Regime stability (LOCK). split + leave-one-regime-out concentration test.
# ---------------------------------------------------------------------------
D213_REGIME_SPLIT = _th.D213_REGIME_SPLIT                  # "2022-01-01"

# ---------------------------------------------------------------------------
# Statistics (LOCK). NW-HAC lags=6; series monthly non-overlapping.
# ---------------------------------------------------------------------------
D213_NW_LAG = _th.D213_NW_LAG                              # 6
D213_KEEP_NW_T_MIN = _th.D213_KEEP_NW_T_MIN               # 2.0

# ---------------------------------------------------------------------------
# Deployable-leg cost (LOCK). Single mega-liquid index instrument: one-way switch cost
# = D207 MEGA half-spread; Kyle impact = 0 (deepest book); commission = 0. Charged on
# each index ENTRY and each index EXIT (one-way each; in-out round trip = 2x).
# Cash leg = APIFON4-derived monthly real carry (NOT TLREF -- silent-NaN until 2022-07).
# ---------------------------------------------------------------------------
D213_INDEX_ONEWAY_COST = _th.D207_TIER_MEGA_HALF_SPREAD    # 0.000528 (5.28bp)
D213_COMMISSION_PCT = _th.D204_COMMISSION_PCT              # 0.0

# ---------------------------------------------------------------------------
# Frozen snapshots (content-hash reproducible; engine asserts on load).
# ---------------------------------------------------------------------------
D213_NOMINAL_SNAPSHOT = "exposure_d213_apifon4"           # TP.APIFON4 daily annual-pct (nominal + cash)
D213_EXPINF_SNAPSHOT = "exposure_d213_enfbek12"           # TP.ENFBEK.PKA12ENF monthly annual-pct
D213_XU100_SNAPSHOT = "exposure_d187_xu100"               # XU100.IS price-only 2019-2026
D213_TUFE_SNAPSHOT = "exposure_k3_d192_tufe"              # CPI index 2010-2026 (deflator + CPI_YoY)
D213_NOMINAL_HASH = "e279aba1829da9d3"
D213_EXPINF_HASH = "716c5dc2685f8f1a"
D213_XU100_HASH = "f909f79881ca8e2b"
D213_TUFE_HASH = "28052c6f46d08446"

# ---------------------------------------------------------------------------
# Paths. Resolve RELATIVE to this repo root (no absolute path).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
D213_SNAPSHOT_DIR = _REPO_ROOT / "data" / "snapshots"

D213_STAGE0 = _REPO_ROOT / "docs" / "yol1" / "STAGE0_d213.json"
D213_RESULTS = _REPO_ROOT / "docs" / "yol1" / "d213_results.json"

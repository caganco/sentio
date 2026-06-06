"""D-211 (RR-Y1-002) -- frozen Stage-0 MEASUREMENT geometry. Yol-1-lab.

Cerceve-B continuous time-series forecast: does aggregate foreign NET flow (in the
~6-week-lag-knowable form, NF_pct(t-2)) predict next-month BIST-index TL-REAL return?
Single-asset timing. NOT stock selection.

MEASUREMENT-ONLY (optimization FORBIDDEN). Like d203_config / d205_config, this holds
pre-registered measurement knobs frozen at Stage-0 (STAGE0_d211.json). The DECISION
THRESHOLDS live in src/signals/thresholds.py (D211_* block, per the CLAUDE.md tek-kaynak
mandate); this module holds GEOMETRY (window, predictor/dependent definitions, snapshot
hashes, cost params) and re-exports the gate constants for a single import surface.

STRANGLER: committed motors (d203/204/205/209 + realistic_cost + thresholds existing
blocks) are NOT modified. The foreign_flow archive does NOT enter CI; the real run is a
local artifact (d211_results.json). HTTP-free, offline.

Dayanak: STAGE0_d211.json (frozen 2026-06-04); D-210/RR-Y1-002-asama0-veri.md (data facts);
realistic_cost.py D-207 cost mechanics; ff parser geometry from edge-arastirma/lab/ff_data.py.
"""
from __future__ import annotations

from pathlib import Path

from src.signals import thresholds as _th

D211_CONFIG_VERSION = "d211-v1"

# ---------------------------------------------------------------------------
# Window (maintainer-approved Option-1, 2026-06-04). Directive named 2010-2026 but
# the only clean LOCAL XU100 (exposure_d187_xu100, price-only) covers 2019+ ONLY; a
# corporate-action-clean index pre-2019 is NOT locally constructible (prices_official
# BIST100-index column is NULL). So PRIMARY = 2019-01..2026-04, NO new pull.
# ---------------------------------------------------------------------------
D211_WINDOW_START = "2019-01-01"
D211_WINDOW_END = "2026-04-30"

# ---------------------------------------------------------------------------
# Predictor (LOCK -- alternative-definition mining FORBIDDEN).
#   NF_pct(m) = SUM_tickers(buy_usd - sell_usd) / SUM_tickers(buy_usd + sell_usd)
#   To predict return-month t, use NF_pct(t - LOOKAHEAD_LAG_MONTHS).  (~6wk pub lag)
# ---------------------------------------------------------------------------
D211_LOOKAHEAD_LAG_MONTHS = _th.D211_LOOKAHEAD_LAG_MONTHS   # 2
D211_SIGNAL_THRESHOLD = _th.D211_SIGNAL_THRESHOLD           # 0.0
D211_TICKER_REGEX = r"^[A-Z0-9]{2,6}\.E$"

# ---------------------------------------------------------------------------
# Dependent (LOCK). XU100 price-only nominal monthly return, TL-real via TUFE MoM.
#   real_ret(t) = r_nom(t) - infl(t)        (directive-literal subtraction)
# ---------------------------------------------------------------------------
D211_REAL_DEFLATE = "subtract_mom_tufe"

# ---------------------------------------------------------------------------
# Regime stability (LOCK). split + leave-one-regime-out concentration test.
# ---------------------------------------------------------------------------
D211_REGIME_SPLIT = _th.D211_REGIME_SPLIT                  # "2022-01-01"

# ---------------------------------------------------------------------------
# Statistics (LOCK). NW-HAC lags=6 (directive lag>=6); series monthly non-overlapping.
# ---------------------------------------------------------------------------
D211_NW_LAG = _th.D211_NW_LAG                              # 6
D211_KEEP_NW_T_MIN = _th.D211_KEEP_NW_T_MIN               # 2.0

# ---------------------------------------------------------------------------
# Deployable-leg cost (LOCK). Single mega-liquid index instrument: one-way switch cost
# = D207 MEGA half-spread; Kyle impact = 0 (deepest book); commission = 0. Charged on
# each index ENTRY and each index EXIT (one-way each; in-out round trip = 2x).
# ---------------------------------------------------------------------------
D211_INDEX_ONEWAY_COST = _th.D207_TIER_MEGA_HALF_SPREAD    # 0.000528 (5.28bp)
D211_COMMISSION_PCT = _th.D204_COMMISSION_PCT              # 0.0

# ---------------------------------------------------------------------------
# Frozen snapshots (content-hash reproducible; engine asserts on load).
# ---------------------------------------------------------------------------
D211_XU100_SNAPSHOT = "exposure_d187_xu100"               # XU100.IS price-only 2019-2026
D211_TUFE_SNAPSHOT = "exposure_k3_d192_tufe"              # CPI index 2010-2026
D211_TLREF_SNAPSHOT = "exposure_d187_tlref"               # TLREF return-index (cash leg)
D211_XU100_HASH = "f909f79881ca8e2b"
D211_TUFE_HASH = "28052c6f46d08446"
D211_TLREF_HASH = "85368181d60a4dce"

# ---------------------------------------------------------------------------
# Paths. The foreign_flow archive lives in the main repo, junctioned into each clone
# as data/bist_datastore_archive. Resolve RELATIVE to this repo root (no absolute path).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
D211_SNAPSHOT_DIR = _REPO_ROOT / "data" / "snapshots"
D211_FOREIGN_FLOW_DIR = _REPO_ROOT / "data" / "bist_datastore_archive" / "foreign_flow"

D211_STAGE0 = _REPO_ROOT / "docs" / "yol1" / "STAGE0_d211.json"
D211_RESULTS = _REPO_ROOT / "docs" / "yol1" / "d211_results.json"

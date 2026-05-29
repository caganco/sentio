"""Faz 0 frozen factor definitions -- Stage 0 pre-registration. D-177.

These are FAZ-0 MEASUREMENT parameters, intentionally NOT in thresholds.py
(thresholds.py is immutable per directive; these are not production signal
thresholds). Frozen at Stage 0 via dated commit; must not change after results
are seen (pre-registration discipline, SPEC sec.2).

Dayanak: SPEC_PIVOT_ARCHITECTURE_1 sec.4 Faz 0; ARCHITECTURE v1.2 sec.3.1 / 7.1.
"""
from __future__ import annotations

# Snapshot window (same ~24 months as D-176; aligned with ARCHITECTURE sec.7.1
# IC sample of ~24 months).
SNAPSHOT_START = "2024-01-01"
SNAPSHOT_END = "2026-04-30"

# RS-vs-XU100: relative strength (stock - index), skip-1-month.
# Absolute nominal RS is forbidden (invariant 5: inflation contamination).
RS_LOOKBACKS_DAYS = {"rs6": 126, "rs12": 252}   # ~6 months, ~12 months
RS_SKIP_DAYS = 21                               # skip ~1 month

# Low-vol: realized volatility of daily log returns over a trailing window.
VOL_WINDOWS_DAYS = {"lowvol20": 20, "lowvol60": 60}

# Forward-return IC horizons (trading days); Faz 0 measures decay across these.
IC_HORIZONS = (1, 5, 10, 21, 63)

# Composite (equal-weight rank average, invariant 4): one representative per
# factor family. RS uses 12mo (lower turnover, ARCHITECTURE-preferred); low-vol
# uses 60d. All four single factors are also measured standalone.
COMPOSITE_RS = "rs12"
COMPOSITE_VOL = "lowvol60"

# Cross-sectional minimum per day (mirrors ic_calculator daily >=5 rule).
MIN_XSECTION = 5

# Newey-West HAC lag for overlapping-horizon IC series (matches NW_LAGS=5).
NW_LAGS = 5

# Block-bootstrap for TEST 2 group-conditional skewness CI (block required for
# cross-sectional correlation + fat tails). Fixed seed -> determinism.
BOOTSTRAP_N = 2000
BOOTSTRAP_BLOCK = 21          # ~1 month block
BOOTSTRAP_SEED = 12345

# TEST 2 vol-group split: bottom/top third by realized vol.
VOL_GROUP_FRACTION = 1.0 / 3.0
# Realized vol window used to split groups + ex-ante realized skewness window.
TEST2_VOL_WINDOW = 60
TEST2_FWD_HORIZON = 21        # forward horizon for group-conditional skew

# Benchmark reference (recorded only; RS/low-vol IC need no deflation because
# cross-sectional ranking removes the common inflation drift).
BENCHMARK_REF = "max(TUFE TP.FG.J0, TLREF TP.BISTTLREF.KAPANIS)"

# Known delisted/halted names for survivorship-gap reporting (invariant 9).
# Not fetchable from yfinance (404) -> snapshot excludes them; the gap and its
# bias DIRECTION are reported explicitly (the maintainer condition).
KNOWN_DELISTED = ("KOZAA", "KOZAL", "IPEKE", "TRALT")

# Factor keep/drop gate (decision rests on standalone rank-IC, NOT on TEST 2).
KEEP_IC_MIN = 0.0      # IC must be > 0 (positive predictive)
KEEP_ICIR_MIN = 0.5    # ICIR >= 0.5 (ARCHITECTURE sec.7.1)

CONFIG_VERSION = "faz0-v1"

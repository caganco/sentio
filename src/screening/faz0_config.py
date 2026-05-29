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

# ===========================================================================
# D-178 v2: mechanical universe + overlap-corrected horizon decision
# ===========================================================================

# Candidate pool = BIST 100 (XU100) index constituents. SOURCE: public BIST 100
# index membership, point-in-time ~2025-2026; frozen here for reproducibility.
# ALL constituents are included -- NO judgmental drop for liquidity (the ADV
# floor below trims mechanically) and NO cherry-pick by expected IC. List
# accuracy is a documented DATA LIMIT, not selection bias: bogus/illiquid names
# are removed mechanically (yfinance 404 -> dropped+logged; ADV floor -> dropped).
# This replaces the config-driven 57-name curated subset used in v1 (D-177),
# whose hand-curation weakened cross-sectional power.
FAZ0_BIST100_CONSTITUENTS = (
    "AEFES", "AGHOL", "AKBNK", "AKCNS", "AKENR", "AKFGY", "AKFYE", "AKSA",
    "AKSEN", "ALARK", "ALBRK", "ALCTL", "ALFAS", "ALGYO", "ALKIM", "ANSGR",
    "ARCLK", "ASELS", "ASTOR", "AYDEM", "BAGFS", "BERA", "BIMAS", "BIOEN",
    "BIZIM", "BRISA", "BUCIM", "CCOLA", "CIMSA", "CLEBI", "CWENE", "DEVA",
    "DOAS", "DOHOL", "ECILC", "EGEEN", "EKGYO", "ENERY", "ENJSA", "ENKAI",
    "EREGL", "ESEN", "EUPWR", "EUREN", "FROTO", "GARAN", "GESAN", "GLYHO",
    "GSDHO", "GUBRF", "GWIND", "HALKB", "HEKTS", "INDES", "ISCTR", "ISDMR",
    "ISGYO", "IZENR", "KAPLM", "KAREL", "KARSN", "KARTN", "KCHOL", "KLGYO",
    "KLNMA", "KONTR", "KONYA", "KORDS", "KRDMD", "LOGO", "MAVI", "MGROS",
    "MPARK", "NETAS", "NTHOL", "NUHCM", "ODAS", "OTKAR", "OYAKC", "PETKM",
    "PGSUS", "PNSUT", "POLHO", "QUAGR", "REEDR", "SAHOL", "SASA", "SELEC",
    "SISE", "SKBNK", "SMRTG", "SOKM", "TATGD", "TAVHL", "TCELL", "THYAO",
    "TKFEN", "TMSN", "TOASO", "TRGYO", "TRKCM", "TSKB", "TTKOM", "TTRAK",
    "TUKAS", "TUPRS", "TURSG", "ULKER", "ULUUN", "VAKBN", "VESTL", "YKBNK",
    "ZOREN",
)
FAZ0_CONSTITUENTS_SOURCE = "BIST 100 (XU100) index membership, point-in-time ~2025-2026"

# ADV liquidity floor (mechanical universe trim). Frozen, result-independent:
# illiquid tail would be dropped by the Faz 1 ADV gate anyway, so measuring IC
# on names we would not trade is misleading. median daily TL volume over window.
FAZ0_ADV_FLOOR_TL = 50_000_000.0    # 50M TL/day median
FAZ0_ADV_MIN_DAYS = 60              # min trading days to compute median ADV

# Theory-justified primary horizons (3-12 month momentum literature), frozen
# BEFORE results -- the keep decision is evaluated on these, not a post-hoc pick.
PRIMARY_HORIZONS = (21, 63)
# Keep decision uses OVERLAP-CORRECTED stats (honest_t = Newey-West HAC lag=h;
# non-overlapping ICIR). Bars are RESULT-INDEPENDENT:
#   KEEP_HONEST_T_MIN = thresholds.IC_INVESTABLE_TSTAT_MIN (existed pre-D-177)
#                       + classic t~=2 (~95%) significance convention.
#   KEEP_ICIR_NONOVERLAP_MIN = ARCHITECTURE sec.7.1 ICIR threshold.
KEEP_HONEST_T_MIN = 2.0
KEEP_ICIR_NONOVERLAP_MIN = 0.5

# Minimum non-overlapping observations for a horizon to be ELIGIBLE for the keep
# decision. ICIR = mean/std is meaningless on a handful of points (e.g. h=63 over
# this window gives ~4 disjoint obs -> a 2-4 point std produces ICIR like 28.9
# that trivially clears 0.5). Require enough independent obs (~1yr of monthly-
# spaced points) for ICIR/std to be trustworthy. Result-independent; STRICTER
# (it EXCLUDES thin horizons, never rescues). Found in Stage 0 dry-run shakedown.
FAZ0_MIN_NONOVERLAP_N = 12

CONFIG_VERSION = "faz0-v2"

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
# bias DIRECTION are reported explicitly (Cagan condition).
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

# ===========================================================================
# D-183 Faz 0b: value factor (USD-based P/B + EV/EBITDA) via Is Yatirim MaliTablo
# ===========================================================================

# Window starts 2024-09 so all valuation points see PUBLIC TMS-29 restated
# financials on a uniform basis (RR-036: SPK 2023/81 -> FY2023 restated public
# ~mid-2024 + SPK +10wk extension). Price forward-returns reuse the frozen
# faz0_v2 price snapshot (2024-01..2026-04); IC sub-window starts 2024-09.
FAZ0B_WINDOW_START = "2024-09-01"
FAZ0B_WINDOW_END = "2026-04-30"

# Value is slower than momentum -> add a 6-month horizon. naive_t + honest_t
# (NW lag=h) + non-overlap ICIR + min-n eligibility -- same machinery as D-178.
FAZ0B_HORIZONS = (21, 63, 126)

# Point-in-time, look-ahead-safe (Cagan): conservative deterministic lag. An
# annual report for fiscal year-end Y is treated as PUBLIC only after
# period_end + this many days (covers the SPK +10wk extension). A valuation
# date t uses the latest annual whose (period_end + lag) <= t. Erring late is
# conservative (never look-ahead).
FAZ0B_ANNUAL_LAG_DAYS = 120

# shares = IssuedCapital(point-in-time annual) / par. BIST standard nominal = 1.0 TL.
# par!=1 GUARD (Cagan): a ticker whose latest-date computed P/B deviates
# materially from Is Yatirim "Cari PD/DD" (tanimid 30) is flagged par!=1 / data
# issue -> value set NULL + reported in coverage (no wrong market_cap into IC).
FAZ0B_PAR_VALUE = 1.0
FAZ0B_PB_CROSSCHECK_TOL = 0.20   # |computed/reported - 1| > tol -> NULL (par!=1 flag)

# MaliTablo itemCode map -- LIVE-DISCOVERED on THYAO (XI_29) + AKBNK (UFRS),
# D-183 Stage 0. Only 2O (EAOoP) was pre-confirmed (RR-035 rho=1.0); the rest
# were verified by Turkish itemName against the live 147/192-row response.
MALITABLO_ENDPOINT = (
    "https://www.isyatirim.com.tr/_Layouts/15/IsYatirim.Website/Common/"
    "Data.aspx/MaliTablo"
)
MALITABLO_GROUP_NONBANK = "XI_29"
MALITABLO_GROUP_BANK = "UFRS"
# field -> itemCode (non-bank, XI_29):
MALITABLO_ITEMCODES = {
    "book_eaoop":        "2O",    # Ana Ortakliga Ait Ozkaynaklar (book value)
    "issued_capital":    "2OA",   # Odenmis Sermaye (-> shares = value / par)
    "cash":              "1AA",   # Nakit ve Nakit Benzerleri
    "short_term_liab":   "2A",    # Kisa Vadeli Yukumlulukler
    "long_term_liab":    "2B",    # Uzun Vadeli Yukumlulukler (TotalLiab = 2A + 2B)
    "operating_profit":  "3DF",   # FAALIYET KARI (ZARARI)  (EBIT)
    "d_and_a":           "4CAB",  # Amortisman & Itfa Paylari (EBITDA add-back; more
                                  # complete than 4B depreciation-only; cross-check
                                  # vs Is Yatirim tanimid 388 TTM FAVOK)
}
# banks (UFRS): code 2O = total OZKAYNAKLAR (D-182: banks match on total equity,
# not EAOoP); F/DD only, EV/EBITDA = NULL. 2OA = issued capital.
MALITABLO_ITEMCODES_BANK = {
    "book_eaoop":     "2O",     # XVI. OZKAYNAKLAR (total equity for banks)
    "issued_capital": "2OA",
}
# banks within the frozen 97-name faz0_v2 universe
FAZ0B_BANKS = ("AKBNK", "ALBRK", "GARAN", "HALKB", "ISCTR", "SKBNK", "TSKB",
               "VAKBN", "YKBNK")

# Annual fiscal years to fetch (period=12). Covers the window + look-back so a
# point-in-time pick always has a public restated annual available.
FAZ0B_FISCAL_YEARS = (2025, 2024, 2023, 2022)   # 4-period MaliTablo call (mandatory)

# USD/TRY period-end for the USD-based ratios + TL-rank==USD-rank sanity. NOTE
# (D-180): F/DD and EV/EBITDA are dimensionless and FX(t) is common across all
# tickers on date t -> USD conversion does NOT change cross-sectional rank. IC is
# computed on TL ratios; USD is for NRR-002 compliance + level + the sanity test.
EVDS_USDTRY_SERIES = "TP.DK.USD.A"

# Is Yatirim current ratios (tanimid) for latest-date cross-checks only:
ISYATIRIM_CARI_PB_TANIMID = "30"      # Cari PD/DD
ISYATIRIM_CARI_EVEBITDA_TANIMID = "29"  # Cari FD/FAVOK
ISYATIRIM_TTM_EBITDA_TANIMID = "388"   # Yillik Cari FAVOK

FAZ0B_CONFIG_VERSION = "faz0b-v1"

# ===========================================================================
# D-184: lowvol60 validity audit (CB-017 4-test diagnostics)
# ===========================================================================

# Test 1: D-regime proxy -- XU100 200-MA (ARCHITECTURE sec.3.1 primary switch).
# L2 macro score (classify_regime) needs live TCMB/CDS data not frozen in the
# snapshot -> use the deterministic price-based proxy instead.
D184_REGIME_MA_WINDOW = 200   # trading days for XU100 MA warm-up

# Test 3: multiple testing correction uses all (factor x horizon) p-values from
# D-177 v1 + D-178 v2 eligible measurements (conservative: all attempted).

# Test 4 OOS window (pre-D-178 period, different regime: TL crisis + covid + TCMB
# shock). ADV floor NOT applied (2019 TL volumes << 50M TL in 2024 terms).
D184_OOS_START = "2019-01-01"
D184_OOS_END = "2023-08-31"

# USDTRY aux snapshot for Test 2 macro-residual IC (yfinance ticker).
D184_USDTRY_YF_TICKER = "USDTRY=X"

# Test 1 regime thresholds (frozen):
D184_REGIME_ON_PCT = 0.80   # >=80% IC from D=ON -> fail (same-bet hypothesis confirmed)

# Macro residual IC honest_t threshold (same bar as keep rule):
D184_RESIDUAL_T_MIN = 2.0

D184_CONFIG_VERSION = "d184-v1"

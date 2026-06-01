"""K2 factor-tilt PORTFOLIO backtest -- frozen Stage-0 parameters. D-191.

MEASUREMENT parameters (NOT thresholds.py): like faz0_config / trend_d186_config,
these are pre-registered measurement knobs, frozen at Stage 0 via a dated commit
and NOT changed after results are seen (pre-registration discipline).

Tests SPEC_YOL2 sec.1 KATMAN 2 (modest factor tilt) hypothesis:
  value + quality/profitability + low-vol, long-only, equal-weight, semi-annual
  rebalance, low turnover. NO momentum (BIST weak/negative). composite-optimize
  FORBIDDEN (invariant 4): equal-weight rank average only.

Dayanak: SPEC_YOL2 sec.1 K2 + sec.4 (degismez test-dersleri); ARCHITECTURE v3.0;
RR-OMEGA (value+quality+lowvol ~%55-65 prior, BIST-net-USD-real alpha untested).
Decision owner: Orchestrator+Cagan (DEC-039); harness MEASURES + RECOMMENDS.
"""
from __future__ import annotations

from src.screening import faz0_config as _f0

K2_CONFIG_VERSION = "k2-tilt-v1"

# ---------------------------------------------------------------------------
# Window + rebalance (Cagan decision: 2019-2026 semi-annual -> ~14 rebalances,
# credible in/out split; fundamental coverage back to ~2018 is the binding
# constraint -> thin in/out is a DATA limit, reported, not over-interpreted).
# ---------------------------------------------------------------------------
K2_WINDOW_START = "2019-01-01"
K2_WINDOW_END = "2026-04-30"
K2_REBALANCE_ANCHORS = (6, 12)          # last trading day on/before Jun-30 & Dec-31
K2_INSAMPLE_END = "2022-12-31"          # in-sample: rebalance date < this; out: >=

# ---------------------------------------------------------------------------
# Universe (reuse the frozen BIST100 constituent pool). Survivors-only:
# delisted names not fetchable (yfinance 404) -> measured edge is an OPTIMISTIC
# upper-bound; the fair null shares the SAME pool so the comparison stays fair
# (only the absolute level is inflated). NO ADV floor: 2019 TL volumes << 2024,
# a 2024-calibrated floor would wrongly trim the early window (D-184 precedent).
# ---------------------------------------------------------------------------
K2_SURVIVORSHIP_BIAS = "optimistic upper-bound (survivors-only; delisted unfetchable)"
K2_ADV_FLOOR_TL = None
K2_BANKS = _f0.FAZ0B_BANKS              # banks: GP/TA undefined -> profitability NULL

# ---------------------------------------------------------------------------
# Factors (literature-standard; see Stage-0 JSON for full references)
#   profitability PRIMARY = GP/TA (Novy-Marx 2013); robustness = ROE
#   value = book-to-market = 1 / (P/B)              (Fama-French HML)
#   low-vol = 252d realized volatility, inverted    (Blitz-van Vliet / Robeco)
# ---------------------------------------------------------------------------
K2_LOWVOL_WINDOW = 252
K2_PROFITABILITY_PRIMARY = "gpa"        # gross_profit / total_assets
K2_PROFITABILITY_ROBUST = "roe"         # net_income / book_eaoop
K2_NO_MOMENTUM = True
K2_SINGLE_FACTORS = ("profitability", "value", "lowvol")  # gate-4 diagnostics

# ---------------------------------------------------------------------------
# Composite + selection. composite = equal-weight average of per-factor
# cross-sectional ranks (invariant 4: NO weight optimization). N<=3 selection
# variants (no parameter sweep): tercile (primary), quintile, tercile-intersection.
# Single-factor portfolios (above) are REQUIRED significance diagnostics, not
# sweep variants -- they do not count against the N<=3 composite budget.
# ---------------------------------------------------------------------------
K2_COMPOSITE_RULE = "equal_weight_composite_rank"
K2_SELECTION_VARIANTS = ("composite_tercile", "composite_quintile", "tercile_intersection")
K2_PRIMARY_VARIANT = "composite_tercile"
K2_TERCILE = 1.0 / 3.0
K2_QUINTILE = 1.0 / 5.0
K2_REQUIRE_ALL_FACTORS = True           # a name needs value+profitability+lowvol all present
K2_MIN_BASKET_N = 5                     # skip a rebalance with fewer eligible names

# ---------------------------------------------------------------------------
# Fundamentals (MaliTablo annual). 8 fiscal years -> two 4-period calls merged
# (endpoint mandates exactly 4 periods/call). pub_date = period_end + lag
# (conservative point-in-time, reuse faz0b convention -> never look-ahead).
# ---------------------------------------------------------------------------
K2_FISCAL_YEARS = (2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018)
K2_ANNUAL_LAG_DAYS = _f0.FAZ0B_ANNUAL_LAG_DAYS    # 120
K2_PAR_VALUE = _f0.FAZ0B_PAR_VALUE                # 1.0
K2_MALITABLO_GROUP_NONBANK = _f0.MALITABLO_GROUP_NONBANK
K2_MALITABLO_GROUP_BANK = _f0.MALITABLO_GROUP_BANK

# Value-side itemcodes reused from the D-183 live-discovered map (book + capital).
K2_MALITABLO_ITEMCODES_VALUE = {
    "book_eaoop": _f0.MALITABLO_ITEMCODES["book_eaoop"],         # 2O
    "issued_capital": _f0.MALITABLO_ITEMCODES["issued_capital"], # 2OA
}

# Profitability itemcodes: FROZEN after the D-191 Stage-0 LIVE DISCOVERY (Faz B),
# verified by ascii-folded Turkish itemName against the live response (same method
# as D-183). Placeholders here are OVERWRITTEN by the discovery step BEFORE the
# Stage-0 commit (pre-results boundary); discovery is result-independent.
K2_MALITABLO_ITEMCODES_PROFIT = {
    "gross_profit": "3D",     # BRUT KAR (ZARAR) -- headline gross profit (Novy-Marx GP)
    "total_assets": "1BL",    # TOPLAM VARLIKLAR
    "net_income": "3Z",       # Ana Ortaklik Paylari (net income attributable to parent,
                              # consistent with book_eaoop=2O for ROE)
}
# Discovered+verified D-191 Stage-0 (Faz B) on EREGL via ascii-folded itemName match
# (3D headline gross profit, distinct from 3DF operating profit / faz0_config EBIT).
# ascii-folded itemName substrings used by --discover-itemcodes to match/verify:
K2_PROFIT_ITEMNAME_PATTERNS = {
    "gross_profit": ("brut kar", "brut esas faaliyet kar"),
    "total_assets": ("toplam varlik",),
    "net_income": ("donem kari (zarari)", "ana ortaklik paylari", "donem net kar"),
}

# ---------------------------------------------------------------------------
# Cost / tax / slippage (K0 model reuse; RR-014 slippage + RR-015 round-trip).
# Per rebalance: cost = one_way_turnover * (round_trip_cost_pct + slippage_rt),
# where one_way_turnover = 0.5 * sum|w_new - w_old| in [0,1]; round_trip_cost_pct
# (tier A) already embeds 2x commission + spread; slippage_rt adds RR-014 market
# impact (two legs). Slightly conservative on the very first entry (charged as a
# round trip). Tax: BIST equities 0% capital gains; 15% dividend withholding ->
# since yfinance auto_adjust embeds GROSS dividends in price, a frozen annual
# dividend-withholding DRAG approximates the tax (caveat: assumed yield).
# ---------------------------------------------------------------------------
K2_BROKER_TIER = "A"
K2_SLIPPAGE_BPS = 20.0                   # RR-014 market-impact, per side (bps of notional)
K2_CAPGAINS_TAX = 0.0                    # BIST equities: 0% (K0)
K2_DIV_WITHHOLDING = 0.15                # 15% dividend withholding (K0)
K2_ASSUMED_ANNUAL_DIV_YIELD = 0.03       # frozen approx for tax drag (caveat in report)

# ---------------------------------------------------------------------------
# Return bases. PRIMARY gate = TL-real (TUFE-deflated). XU100-relative + USD-real
# ALWAYS reported (never gate). USD-real: deflate USD equity by US CPI if a frozen
# series is supplied; else report USD-NOMINAL (labeled). No silent fallback.
# ---------------------------------------------------------------------------
K2_TUFE_SERIES = "TP.FG.J0"              # EVDS monthly CPI (matches thresholds.EVDS_TUFE_SERIES)
K2_FX_SERIES = _f0.EVDS_USDTRY_SERIES    # TP.DK.USD.A (USD/TRY)
K2_US_CPI_SERIES = None                  # None -> USD-nominal (labeled); set to deflate

# ---------------------------------------------------------------------------
# Fair portfolio null + significance.
#   null: at each rebalance draw the SAME N names uniformly from the SAME eligible
#   pool, equal-weight, SAME rebalance dates / holding / cost / tax -> randomizes
#   ONLY name selection (isolates factor-selection skill). Statistic = full-window
#   mean per-period net TL-real return. beats iff strategy >= 95th pctile.
#   significance: block-bootstrap CI of the per-period net-real series. Holding
#   periods are NON-overlapping (semi-annual) -> near-independent -> block=1.
# ---------------------------------------------------------------------------
K2_NULL_SEED = 12345
K2_NULL_N_RESAMPLES = 2000
K2_SIG_BLOCK = 1
K2_SIG_N_BOOT = 2000
K2_SIG_SEED = 12345
K2_DECISION_RANDOM_PCTILE_MIN = 0.95

"""D-188 Event-Triggered Confluence Test -- Stage 0 frozen parameters (pre-registration).

CONTEXT. D-185/D-186 eliminated PURE-technical short-term swing (S/R-flip,
consolidation breakout, Donchian) -- it failed the fair null; the apparent edge
was nominal drift + exit-mechanism, not entry timing. EVENT-TRIGGERED swing
(catalyst event + technical confirmation = confluence) was never tested, and the
final research flagged it as the most defensible, still-open area, with a critical
warning: unconditional cross-sectional / IC / random-null tests can STRUCTURALLY
MISS an event-driven, sparse, conditional edge -- so "eliminated" does not apply
to event-driven.

These are MEASUREMENT params, intentionally NOT in thresholds.py (same precedent
as faz0_config / trend_config / exposure_config). Frozen at Stage 0 via a dated
commit; they MUST NOT change after results are seen. The decision rule (DEC-046)
below is frozen and will NOT be relaxed post-hoc (no Holm->FDR, no >=0.95 -> >=0.90).

TWO COMPONENTS (this directive builds both):
1. BACKTEST engine -- clean, runs on history once MKK_VYK_TOKEN + data are provided;
   exercised now only on synthetic data.
2. FORWARD (paper) recorder -- starts today via the auth-free real-time KAP feed
   (src/data/kap_scraper.py:180 _fetch_kap_api, disclosureCategory filter, no token);
   records the pre-registered signal BEFORE the forward outcome is seen, then fills
   t+5/+20/+60 forward returns later -> look-ahead / overfit / survivorship are
   structurally impossible. Manual-trigger by default (cron deferred).

REALISTIC EXPECTATION (pre-registered honesty): even if an edge exists, the prior is
a few-points-of-XU100-relative edge, NOT a multiplier (Bessembinder: pre-selecting the
top names ex-ante is statistically very hard). "No edge" is also a valid, valuable result.

DEC-039: this config drives MEASUREMENT only. Whether event-confluence is promoted into
the Yol-1 lab (and how) is an maintainer decision. the analysis recommends; deployment is decided separately.
"""
from __future__ import annotations

# Reuse D-185/D-186 frozen objects (no new market-regime / cost convention invented).
from src.screening.trend_config import (
    INFLATION_REGIMES,
    PRIMARY_COST_BPS,
)

EVENT_CONFIG_VERSION = "event-confluence-v1"

# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------
# Backtest window (used ONLY when historical event data is provisioned; data_pending now).
EVENT_BACKTEST_START = "2019-01-01"
EVENT_BACKTEST_END = "2026-04-30"
# Forward recording start = the Stage 0 pre-registration date (frozen). The forward
# recorder accumulates clean, look-ahead-free samples from this date onward.
FORWARD_RECORDING_START = "2026-05-31"

# ---------------------------------------------------------------------------
# Event types (N-LOCKED = 3; no parameter sweeping, no new event type post-hoc)
# ---------------------------------------------------------------------------
# status: "active_design" = methodology specified; "data_pending" = no frozen source yet.
# Backtest data and forward data availability are SEPARATE (E1/E3 forward use the
# auth-free KAP feed today; backtest needs MKK_VYK_TOKEN + KAP-4.0 depth).
EVENT_TYPES: tuple[str, ...] = ("E1_earnings", "E2_index_inclusion", "E3_material_kap")
N_EVENT_TYPES = 3

EVENT_TYPE_STATUS: dict[str, dict] = {
    "E1_earnings": {
        "design": "active",
        "backtest_source": "kap_historical_fetcher.fetch_fundamentals_with_fallback (needs MKK_VYK_TOKEN)",
        "forward_source": "kap_scraper.fetch_kap_news (auth-free, real-time, recent-only)",
        "surprise_metric": "real_yoy",
    },
    "E2_index_inclusion": {
        "design": "active",
        "backtest_source": "data_pending (no frozen BIST index-membership-change source)",
        "forward_source": "kap_scraper.fetch_kap_news (index-announcement disclosures, if accessible)",
        "surprise_metric": "n/a (binary event)",
    },
    "E3_material_kap": {
        "design": "active",
        "backtest_source": "data_pending (KAP ODA pagination needs MKK_VYK_TOKEN)",
        "forward_source": "kap_scraper.fetch_kap_news (material-event disclosures, auth-free)",
        "surprise_metric": "n/a (category event)",
    },
}

# ---------------------------------------------------------------------------
# Surprise metric (E1) -- REAL YoY, TUFE-deflated (NOT nominal: D-186 drift lesson)
# ---------------------------------------------------------------------------
# Nominal YoY in a high-inflation regime selects the "most nominally-inflated" names,
# not a genuine operational surprise -> the surprise signal would be contaminated by
# drift. Real YoY (net_income primary, revenue corroborating, both TUFE-deflated)
# captures the true surprise. Justification for real-vs-nominal framing: NRR-001-SCREENING
# sec.3 (RS relative-to-index, not absolute nominal). NOTE: NRR-001-SCREENING.md is
# currently UNTRACKED in this clone -- a separate commit decision (maintainer).
SURPRISE_METRIC = "real_yoy"
SURPRISE_PRIMARY_FIELD = "net_income"
SURPRISE_CORROBORATING_FIELD = "revenue"
# High-surprise slice: real YoY growth above this fraction. Frozen.
SURPRISE_HIGH_THRESHOLD = 0.20
# YoY is computed only when the prior-year value is > 0 (sign flips make YoY meaningless);
# otherwise the event is recorded but its surprise is undefined -> excluded from high-surprise.
SURPRISE_REQUIRE_POSITIVE_BASE = True
EVDS_TUFE_SERIES = "TP.FG.J0"  # monthly CPI (RR-021 active), for real-deflation

# ---------------------------------------------------------------------------
# Technical confirmation (FROZEN, look-ahead safe: uses only data up to event_date)
# ---------------------------------------------------------------------------
VOLUME_SURGE_WINDOW = 20          # trailing volume MA window (bars), excludes the event bar
VOLUME_SURGE_MULT = 1.5           # event-day volume / trailing-MA must exceed this
BREAKOUT_RESISTANCE_N = 20        # event-day close must exceed prior N-bar high (excl. event bar)

# ---------------------------------------------------------------------------
# Event study (forward returns)
# ---------------------------------------------------------------------------
EVENT_HORIZONS: tuple[int, ...] = (5, 20, 60)   # trading days
# Look-ahead guard: event_day = published_at (disclosure date); ACTION at t+1
# (enter the bar AFTER the disclosure -> the speed disadvantage is modelled, not assumed away).
ENTRY_OFFSET_DAYS = 1
RETURN_BASIS_DECISIVE = "xu100_relative"   # geometric excess over index (D-186 lesson)
REAL_CPI_CONFIRMATORY = True

# ---------------------------------------------------------------------------
# Cost model (reuse RR-038 calibration) + event-day slippage
# ---------------------------------------------------------------------------
COST_BPS = PRIMARY_COST_BPS       # 50 bps round-trip (BSMV on commission, RR-038)
SLIPPAGE_BPS = 20                 # event-day volatility -> extra realistic slippage
TOTAL_COST_BPS = COST_BPS + SLIPPAGE_BPS

# ---------------------------------------------------------------------------
# Two nulls (CRITICAL -- the report's methodological correction)
# ---------------------------------------------------------------------------
# NULL-1 (event-conditional): on the SAME event days, the technical confirmation is
#   assigned at RANDOM -> "does technical confirmation add value to the event itself?"
# NULL-2 (no-event): on RANDOM non-event days, the SAME technical confirmation ->
#   "does the event add value to the technical signal?"
# Confluence is REAL only if it beats BOTH nulls (intersection > sum of parts).
NULL_SEED = 12345
NULL_N_RESAMPLES = 1000

# ---------------------------------------------------------------------------
# DECISION RULE (DEC-046) -- FROZEN, no post-hoc relaxation
# ---------------------------------------------------------------------------
# Confluence "carries edge" for an event type ONLY IF (when a sufficient sample exists,
# from backtest OR from the forward recorder):
#   (1) beats NULL-1 (event-conditional) at >= DECISION_NULL_PCTILE_MIN, AND
#   (2) beats NULL-2 (no-event) at >= DECISION_NULL_PCTILE_MIN, AND
#   (3) XU100-relative forward return is POSITIVE after cost+slippage, AND
#   (4) Holm-Bonferroni (applied SEPARATELY per event type, across horizons) is significant.
# Fails any -> event-confluence does not carry edge for that type; if all three types
# fail, the last subset of swing closes too (pure-technical + event-triggered both gone).
DECISION_NULL_PCTILE_MIN = 0.95
DECISION_HOLM_ALPHA = 0.05
# Minimum sample before ANY verdict is issued (forward accrual is slow; small-n is honest).
# Below this, the status is "undetermined, sample accruing" -- NOT a pass/fail.
MIN_EVENTS_PER_TYPE = 30

# ---------------------------------------------------------------------------
# Significance machinery (reuse factor_ic_harness)
# ---------------------------------------------------------------------------
SIG_BLOCK = 21      # ~1 month block-bootstrap (cross-sectional clustering via daily aggregation)
SIG_N_BOOT = 2000
SIG_SEED = 12345


def regime_label(date_str: str) -> str:
    """Inflation-regime label for a date, from the frozen trend_config.INFLATION_REGIMES."""
    for label, lo, hi in INFLATION_REGIMES:
        if lo <= date_str <= hi:
            return label
    return "unknown"

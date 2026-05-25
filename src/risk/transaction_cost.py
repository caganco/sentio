"""BIST round-trip transaction cost model (D-146, RR-015).

Commission + bid-ask spread estimates per broker tier and ticker type.
Sources: Garanti BBVA, Is Yatirim, Deniz Yatirim fee schedules (May 2026).
High-cost ticker override applies for micro-cap / narrow-float names.
All threshold constants imported from thresholds.py (single source of truth).
"""
from __future__ import annotations

from src.signals.thresholds import (
    BROKER_TIER,
    HIGH_COST_RT_PCT,
    HIGH_COST_TICKERS,
    ROUND_TRIP_COST_PCT_DEFAULT,
)

# Broker tier round-trip cost lookup (2x commission + bid-ask spread estimate).
# Tier A: Garanti BBVA    ~0.20%*2 + 0.65% spread = 1.05%
# Tier B: Is Yatirim       ~0.18%*2 + 0.59% spread = 0.95%
# Tier C: Discount broker  ~0.10%*2 + 0.40% spread = 0.60%
# Note: these are IMPLEMENTATION DETAILS of the cost model, not signal thresholds.
_TIER_COSTS: dict[str, float] = {
    "A": 0.0105,
    "B": 0.0095,
    "C": 0.0060,
}


def round_trip_cost_pct(ticker: str, broker_tier: str | None = None) -> float:
    """Return round-trip cost fraction for a BIST trade.

    Priority order:
    1. HIGH_COST_TICKERS override (micro-cap / narrow-float names).
    2. Broker tier lookup (_TIER_COSTS["A"/"B"/"C"]).
    3. Fallback: ROUND_TRIP_COST_PCT_DEFAULT (unknown tier).

    Args:
        ticker: BIST ticker (e.g. "ENERY", "KCHOL").
        broker_tier: "A", "B", "C", or None (uses BROKER_TIER constant as default).

    Returns:
        Round-trip cost as a fraction (e.g. 0.013 = 1.3%).
    """
    if ticker in HIGH_COST_TICKERS:
        return HIGH_COST_RT_PCT
    tier = broker_tier if broker_tier is not None else BROKER_TIER
    return _TIER_COSTS.get(tier, ROUND_TRIP_COST_PCT_DEFAULT)

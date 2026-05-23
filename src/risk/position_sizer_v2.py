"""Conviction-based position sizing (SPEC_POSITION_SIZING_2, D-052).

Ruthless-Alpha sizing. Replaces Kelly for Phase 4.5 entries (kelly.py left
intact for legacy/other callers). Position size is driven by:

    size = base_tier_allocation * macro_regime_scaling * conviction_score

with hard caps: max 4 BUY-STRONG, max 2 BUY-MEDIUM, max 6 total, single sector
<= 40%, portfolio drawdown hard stop at 15%. All constants from thresholds.py.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.signals.thresholds import (
    CONVICTION_COLLAPSE,
    CONVICTION_MEDIUM,
    CONVICTION_STRONG,
    CONVICTION_WEAK,
    MAX_DRAWDOWN_HARD_STOP,
    MAX_POSITIONS_MEDIUM,
    MAX_POSITIONS_STRONG,
    MAX_POSITIONS_TOTAL,
    MAX_SECTOR_CONCENTRATION,
    POSITION_SIZE_MEDIUM,
    POSITION_SIZE_STRONG,
)

TIER_STRONG = "BUY-STRONG"
TIER_MEDIUM = "BUY-MEDIUM"
TIER_WEAK = "BUY-WEAK"
TIER_HOLD = "HOLD"
TIER_SELL = "SELL-SIGNAL"

ACTION_ENTER = "ENTER"
ACTION_WATCH = "WATCH"
ACTION_WATCHLIST = "WATCHLIST"  # tier qualifies but a hard cap is full
ACTION_HOLD = "HOLD"
ACTION_EXIT = "EXIT"
ACTION_BLOCKED = "BLOCKED"  # drawdown hard stop / bear regime


@dataclass(frozen=True)
class SizingDecision:
    conviction_tier: str
    action: str
    allocation_pct: float          # final % of equity (post macro + conviction)
    position_size: float           # allocation_pct * portfolio_equity
    macro_scaling: float
    reason: str


def classify_sizing_tier(conviction_score: float) -> str:
    """Full position-sizing lifecycle tier (5 states, SPEC_POSITION_SIZING_2 1.2)."""
    if conviction_score >= CONVICTION_STRONG:
        return TIER_STRONG
    if conviction_score >= CONVICTION_MEDIUM:
        return TIER_MEDIUM
    if conviction_score >= CONVICTION_WEAK:
        return TIER_WEAK
    if conviction_score >= CONVICTION_COLLAPSE:
        return TIER_HOLD
    return TIER_SELL


def _base_allocation(tier: str) -> float:
    if tier == TIER_STRONG:
        return POSITION_SIZE_STRONG
    if tier == TIER_MEDIUM:
        return POSITION_SIZE_MEDIUM
    return 0.0


def size_position(
    conviction_score: float,
    macro_scaling: float,
    portfolio_equity: float,
    strong_positions_count: int = 0,
    medium_positions_count: int = 0,
    total_positions_count: int = 0,
    sector_exposure_pct: float = 0.0,
    portfolio_drawdown: float = 0.0,
    stop_result: "object | None" = None,   # D-110: optional StopResult risk-parity clip
) -> SizingDecision:
    """Compute a sizing decision from conviction + macro regime + portfolio state.

    Args:
        conviction_score: [0,1] from conviction_validator / engine.
        macro_scaling: 1.0 bull / 0.8 neutral / 0.0 bear (macro_regime_gate).
        portfolio_equity: current portfolio value.
        strong_positions_count / medium_positions_count / total_positions_count:
            currently open positions by tier.
        sector_exposure_pct: existing exposure to this position's sector [0,1];
            a new entry must not push it past MAX_SECTOR_CONCENTRATION.
        portfolio_drawdown: current drawdown as a positive fraction (0.12 = -12%).
        stop_result: optional StopResult (D-110). When provided AND the
            conviction-based allocation exceeds risk-parity allocation, the
            allocation is clipped to risk-parity (so the dollar loss at stop
            stays at RISK_PER_TRADE_PCT of equity).

    Returns:
        SizingDecision (frozen).
    """
    tier = classify_sizing_tier(conviction_score)

    def decide(action: str, alloc: float, reason: str) -> SizingDecision:
        return SizingDecision(
            conviction_tier=tier,
            action=action,
            allocation_pct=round(alloc, 6),
            position_size=round(alloc * portfolio_equity, 4),
            macro_scaling=macro_scaling,
            reason=reason,
        )

    # Tier 4 hard stop: portfolio drawdown breach blocks all new entries.
    if portfolio_drawdown >= MAX_DRAWDOWN_HARD_STOP:
        if tier in (TIER_STRONG, TIER_MEDIUM):
            return decide(
                ACTION_BLOCKED, 0.0,
                f"drawdown {portfolio_drawdown:.2%} >= hard stop "
                f"{MAX_DRAWDOWN_HARD_STOP:.0%}",
            )

    if tier == TIER_SELL:
        return decide(ACTION_EXIT, 0.0, "conviction collapse -> staged exit")
    if tier == TIER_HOLD:
        return decide(ACTION_HOLD, 0.0, "hold existing, no new sizing")
    if tier == TIER_WEAK:
        return decide(ACTION_WATCH, 0.0, "watchlist only")

    # Bear regime → no new entries regardless of conviction.
    if macro_scaling <= 0.0:
        return decide(ACTION_BLOCKED, 0.0, "bear regime, entries frozen")

    # Concurrent caps.
    if total_positions_count >= MAX_POSITIONS_TOTAL:
        return decide(ACTION_WATCHLIST, 0.0,
                      f"total positions cap {MAX_POSITIONS_TOTAL} reached")
    if tier == TIER_STRONG and strong_positions_count >= MAX_POSITIONS_STRONG:
        return decide(ACTION_WATCHLIST, 0.0,
                      f"BUY-STRONG cap {MAX_POSITIONS_STRONG} reached")
    if tier == TIER_MEDIUM and medium_positions_count >= MAX_POSITIONS_MEDIUM:
        return decide(ACTION_WATCHLIST, 0.0,
                      f"BUY-MEDIUM cap {MAX_POSITIONS_MEDIUM} reached")

    base = _base_allocation(tier)
    alloc = base * macro_scaling * conviction_score

    # Sector concentration: clip so post-entry sector exposure <= cap.
    headroom = MAX_SECTOR_CONCENTRATION - sector_exposure_pct
    if headroom <= 0.0:
        return decide(ACTION_WATCHLIST, 0.0,
                      f"sector cap {MAX_SECTOR_CONCENTRATION:.0%} reached")
    if alloc > headroom:
        alloc = headroom
        return decide(ACTION_ENTER, alloc,
                      f"clipped to sector cap {MAX_SECTOR_CONCENTRATION:.0%}")

    # D-110 risk parity clip: when a vol-aware stop is supplied, the position
    # may not exceed the risk-parity allocation (= RISK_PER_TRADE_PCT / stop_distance).
    if stop_result is not None and alloc > 0:
        rp_alloc = float(getattr(stop_result, "equity_used", 0.0))
        if 0 < rp_alloc < alloc:
            return decide(ACTION_ENTER, rp_alloc,
                          f"{tier} entry, clipped to risk-parity "
                          f"(vol_tier={getattr(stop_result, 'vol_tier', '?')})")

    return decide(ACTION_ENTER, alloc, f"{tier} entry")

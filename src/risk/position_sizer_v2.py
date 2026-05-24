"""Conviction-based position sizing (SPEC_POSITION_SIZING_2, D-052).

Ruthless-Alpha sizing. Replaces Kelly for Phase 4.5 entries (kelly.py left
intact for legacy/other callers). Position size is driven by:

    size = base_tier_allocation * macro_regime_scaling * conviction_score

with hard caps: max 4 BUY-STRONG, max 2 BUY-MEDIUM, max 6 total, single sector
<= 40%, portfolio drawdown hard stop at 15%. All constants from thresholds.py.

D-145 (RR-014): apply_adv_cap() post-processes size_position() output with a
5% ADV cap (Almgren 2005). size_position() signature is unchanged.
"""
from __future__ import annotations

import logging
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
    POSITION_MAX_ADV_PCT,
    POSITION_SIZE_MEDIUM,
    POSITION_SIZE_STRONG,
)

logger = logging.getLogger(__name__)

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


# =============================================================================
# D-145 / RR-014: ADV cap post-processing
# =============================================================================

def fetch_adv(ticker: str, lookback: int = 20) -> float | None:
    """Fetch Average Daily Volume in TL via yfinance (20-day default).

    Args:
        ticker: BIST ticker without suffix (e.g. "AKBNK") or with ".IS".
        lookback: Number of trading days for the rolling average.

    Returns:
        Mean(Close × Volume) over last ``lookback`` days in TL,
        or None if fetch fails (non-fatal).
    """
    try:
        import yfinance as yf  # lazy import — optional dependency

        yf_ticker = ticker if ticker.endswith(".IS") else f"{ticker}.IS"
        df = yf.download(yf_ticker, period="2mo", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < lookback:
            logger.warning(
                "fetch_adv(%s): insufficient data (%d rows) — ADV cap skipped",
                ticker,
                0 if df is None else len(df),
            )
            return None
        recent = df.tail(lookback)
        adv_tl = float((recent["Close"] * recent["Volume"]).mean())
        return adv_tl
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "fetch_adv(%s) failed: %s — ADV cap not applied", ticker, exc
        )
        return None


def apply_adv_cap(
    ticker: str,
    decision: SizingDecision,
    *,
    adv_lookback: int = 20,
) -> SizingDecision:
    """Apply POSITION_MAX_ADV_PCT cap to a SizingDecision (D-145, RR-014).

    Post-processes the result of size_position(): fetches 20-day ADV from
    yfinance and clips position_size to POSITION_MAX_ADV_PCT × ADV when the
    conviction-based size would exceed that limit.

    Non-fatal: if fetch_adv() returns None (yfinance unavailable, insufficient
    history, etc.), the original decision is returned unchanged and a warning
    is already logged inside fetch_adv().

    Args:
        ticker: BIST ticker (e.g. "AKBNK"); ".IS" suffix added if absent.
        decision: SizingDecision returned by size_position().
        adv_lookback: Trading-day window for ADV (default 20).

    Returns:
        New SizingDecision with position_size ≤ ADV cap, or the original
        decision when the cap is unavailable or not triggered.
    """
    if decision.position_size <= 0.0:
        return decision  # No active entry — cap irrelevant

    adv = fetch_adv(ticker, lookback=adv_lookback)
    if adv is None or adv <= 0.0:
        return decision  # Non-fatal: ADV unavailable, keep original

    max_by_adv = adv * POSITION_MAX_ADV_PCT
    if decision.position_size <= max_by_adv:
        return decision  # Within ADV limit — no clip needed

    # Derive portfolio equity so we can restate allocation_pct correctly.
    portfolio_equity = (
        decision.position_size / decision.allocation_pct
        if decision.allocation_pct > 0.0
        else 0.0
    )
    new_alloc_pct = (
        round(max_by_adv / portfolio_equity, 6) if portfolio_equity > 0.0 else 0.0
    )

    return SizingDecision(
        conviction_tier=decision.conviction_tier,
        action=decision.action,
        allocation_pct=new_alloc_pct,
        position_size=round(max_by_adv, 4),
        macro_scaling=decision.macro_scaling,
        reason=(
            f"{decision.reason}, clipped to ADV cap "
            f"({POSITION_MAX_ADV_PCT:.0%}×ADV={max_by_adv:,.0f} TL)"
        ),
    )

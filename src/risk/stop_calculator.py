"""Volatility-aware stop-loss calculation (SPEC_STOPLOSS_VOLATILITY_AWARE_1, D-110).

ATR/Price ratio drives stop width tier:
    ATR/P < 2%  -> -6%  (low vol; large-cap)
    ATR/P 2-4%  -> -8%  (mid vol; matches legacy EXIT_STOP_LOSS)
    ATR/P 4-6%  -> -12% (high vol; small-mid cap)
    ATR/P >= 6% -> -15% (extreme / microcap)
    hard floor  -> -20% (catastrophic loss cap)

Risk parity sizes the position so the dollar loss at stop equals
RISK_PER_TRADE_PCT (1%) of equity, regardless of vol tier.

ATR calculation is reused from technical_level_detector.calculate_atr
(D-109's TP detector). STOP_ATR_WINDOW = 20 is wider than the TP detector's
default period=14: stop calibration benefits from a longer-horizon estimate
of natural noise; TP detection cares more about recent reaction range.

All constants from src.signals.thresholds -- no magic numbers here.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.risk.technical_level_detector import calculate_atr
from src.signals.thresholds import (
    RISK_PER_TRADE_PCT,
    STOP_ATR_PCT_HIGH_MAX,
    STOP_ATR_PCT_LOW_MAX,
    STOP_ATR_PCT_MID_MAX,
    STOP_ATR_WINDOW,
    STOP_HARD_FLOOR,
    STOP_LOSS_EXTREME_VOL,
    STOP_LOSS_HIGH_VOL,
    STOP_LOSS_LOW_VOL,
    STOP_LOSS_MID_VOL,
)

VOL_TIER_LOW = "low"
VOL_TIER_MID = "mid"
VOL_TIER_HIGH = "high"
VOL_TIER_EXTREME = "extreme"


@dataclass(frozen=True)
class StopResult:
    """Full audit trail for volatility-aware stop calculation."""
    entry_price: float
    stop_price: float
    stop_distance_pct: float   # Fraction (0.06 -> 6%)
    atr: float
    atr_pct: float             # ATR / entry_price (fraction)
    vol_tier: str              # low | mid | high | extreme
    risk_parity_size: float    # Position size in TL for RISK_PER_TRADE_PCT risk
    equity_used: float         # risk_parity_size / portfolio_equity (fraction)


def classify_vol_tier(atr_pct: float) -> str:
    """Map ATR/Price ratio (fraction) to vol tier label.

    atr_pct is the fraction (e.g., 0.04 for 4%). Compared in percent (Ã100)
    against the thresholds for readability.
    """
    pct_100 = atr_pct * 100.0
    if pct_100 < STOP_ATR_PCT_LOW_MAX:
        return VOL_TIER_LOW
    if pct_100 < STOP_ATR_PCT_MID_MAX:
        return VOL_TIER_MID
    if pct_100 < STOP_ATR_PCT_HIGH_MAX:
        return VOL_TIER_HIGH
    return VOL_TIER_EXTREME


def _stop_distance_from_tier(tier: str) -> float:
    return {
        VOL_TIER_LOW: STOP_LOSS_LOW_VOL,
        VOL_TIER_MID: STOP_LOSS_MID_VOL,
        VOL_TIER_HIGH: STOP_LOSS_HIGH_VOL,
        VOL_TIER_EXTREME: STOP_LOSS_EXTREME_VOL,
    }[tier]


def calculate_stop(
    entry_price: float,
    atr: float,
    portfolio_equity: float = 100_000.0,
) -> StopResult:
    """Vol-aware stop + risk-parity sizing for a single entry.

    Args:
        entry_price: Trade entry price (TL). Must be > 0.
        atr: Pre-computed ATR (same unit as price). Use calculate_atr() or
             calculate_stop_from_ohlcv() when you have OHLCV history.
        portfolio_equity: Total portfolio value in TL for risk-parity sizing.
    """
    if entry_price <= 0:
        raise ValueError(f"entry_price must be positive, got {entry_price}")

    atr_pct = atr / entry_price if entry_price > 0 else 0.0
    tier = classify_vol_tier(atr_pct)
    raw_distance = _stop_distance_from_tier(tier)

    # Hard floor: cap at STOP_HARD_FLOOR even if a future tier breaches it.
    stop_distance = min(raw_distance, STOP_HARD_FLOOR)
    stop_price = round(entry_price * (1.0 - stop_distance), 4)

    # Risk parity: pos_size * stop_distance = equity * RISK_PER_TRADE_PCT
    risk_parity_size = round(
        portfolio_equity * RISK_PER_TRADE_PCT / stop_distance, 2,
    )
    equity_used = round(risk_parity_size / portfolio_equity, 4) if portfolio_equity > 0 else 0.0

    return StopResult(
        entry_price=entry_price,
        stop_price=stop_price,
        stop_distance_pct=stop_distance,
        atr=round(atr, 4),
        atr_pct=round(atr_pct, 4),
        vol_tier=tier,
        risk_parity_size=risk_parity_size,
        equity_used=equity_used,
    )


def calculate_stop_from_ohlcv(
    ohlcv: pd.DataFrame,
    portfolio_equity: float = 100_000.0,
) -> StopResult:
    """Compute ATR from OHLCV (window=STOP_ATR_WINDOW) then calculate stop."""
    entry_price = float(ohlcv["Close"].iloc[-1])
    atr = calculate_atr(ohlcv, period=STOP_ATR_WINDOW)
    return calculate_stop(entry_price, atr, portfolio_equity)

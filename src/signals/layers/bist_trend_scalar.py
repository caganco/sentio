"""BIST100 MA trend scalar for position sizing (D-163)."""
from __future__ import annotations

from src.signals.thresholds import (
    BIST_TREND_SCALAR_BEAR,
    BIST_TREND_SCALAR_BULL,
    BIST_TREND_SCALAR_NEUTRAL,
)


def compute_bist_trend_scalar(
    bist_close: float,
    bist_ma20: float | None,
    bist_ma50: float | None,
) -> float:
    """BIST100 MA trend durumuna gore position sizing scalar.

    Returns 0.75 / 1.00 / 1.25.
    Fallback: MA verisi yoksa 1.00 (no change).
    """
    if bist_ma20 is None or bist_ma50 is None:
        return BIST_TREND_SCALAR_NEUTRAL
    if bist_close > bist_ma20 > bist_ma50:
        return BIST_TREND_SCALAR_BULL
    if bist_close > bist_ma50:
        return BIST_TREND_SCALAR_NEUTRAL
    return BIST_TREND_SCALAR_BEAR

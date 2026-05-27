"""D-163: BIST100 MA Trend Scalar unit tests."""
from __future__ import annotations

from src.signals.layers.bist_trend_scalar import compute_bist_trend_scalar
from src.signals.thresholds import (
    BIST_TREND_SCALAR_BEAR,
    BIST_TREND_SCALAR_BULL,
    BIST_TREND_SCALAR_NEUTRAL,
)


class TestBISTTrendScalar:
    def test_bull_confirmed_uptrend(self):
        """price > MA20 > MA50 -> 1.25."""
        assert compute_bist_trend_scalar(100.0, 98.0, 95.0) == BIST_TREND_SCALAR_BULL

    def test_weak_uptrend_price_above_ma50_only(self):
        """price > MA50 but MA20 < MA50: not confirmed bull -> 1.00."""
        # price=100 > MA50=95, but MA20=94 < MA50=95 → chain 100>94>95 is False
        assert compute_bist_trend_scalar(100.0, 94.0, 95.0) == BIST_TREND_SCALAR_NEUTRAL

    def test_bear_price_below_ma50(self):
        """price < MA50 -> 0.75 regardless of MA20."""
        assert compute_bist_trend_scalar(100.0, 96.0, 102.0) == BIST_TREND_SCALAR_BEAR

    def test_fallback_when_ma20_none(self):
        """None MA20 -> 1.00 fallback."""
        assert compute_bist_trend_scalar(100.0, None, 95.0) == BIST_TREND_SCALAR_NEUTRAL

    def test_fallback_when_both_ma_none(self):
        """None MA20 and MA50 -> 1.00 fallback."""
        assert compute_bist_trend_scalar(100.0, None, None) == BIST_TREND_SCALAR_NEUTRAL

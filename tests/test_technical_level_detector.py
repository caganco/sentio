"""Tests for technical level detection (SPEC_STAGED_TP_1, D-052)."""
import pandas as pd
import pytest

from src.risk.technical_level_detector import (
    calculate_atr,
    calculate_fibonacci_levels,
    calculate_ma200,
    calculate_pivot_points,
    detect_levels,
)


def _ohlcv(closes, highs=None, lows=None):
    n = len(closes)
    highs = highs or [c * 1.02 for c in closes]
    lows = lows or [c * 0.98 for c in closes]
    return pd.DataFrame({"High": highs, "Low": lows, "Close": closes})


class TestPivotPoints:
    def test_standard_formula(self):
        p = calculate_pivot_points(110.0, 90.0, 100.0)
        assert p["pivot"] == pytest.approx(100.0)
        assert p["resistance_1"] == pytest.approx(110.0)  # 2*100 - 90
        assert p["support_1"] == pytest.approx(90.0)       # 2*100 - 110
        assert p["resistance_2"] == pytest.approx(120.0)   # 100 + (110-90)


class TestFibonacci:
    def test_levels_anchored_on_low(self):
        df = _ohlcv([100] * 10, highs=[200] * 10, lows=[100] * 10)
        fib = calculate_fibonacci_levels(df, 252)
        assert fib["fib_0.618"] == pytest.approx(100 + 0.618 * 100)
        assert fib["fib_1.618"] == pytest.approx(100 + 1.618 * 100)


class TestMA200AndATR:
    def test_ma200_handles_short_history(self):
        df = _ohlcv([10, 20, 30])
        assert calculate_ma200(df) == pytest.approx(20.0)

    def test_atr_non_negative(self):
        df = _ohlcv([100, 101, 99, 102, 98, 103])
        assert calculate_atr(df) >= 0.0


class TestDetectLevels:
    def test_detected_levels_nondecreasing_above_entry(self):
        # Rising series so real resistances exist above entry. SPEC sorts
        # ascending and picks the nearest 3; coincident prices are allowed.
        closes = list(range(50, 130))
        df = _ohlcv(closes)
        plan = detect_levels(df)
        assert plan.tp1 <= plan.tp2 <= plan.tp3
        assert plan.tp1 > plan.entry_price
        assert 0.6 <= plan.confidence <= 0.95

    def test_atr_fallback_on_degenerate_flat_series(self):
        # Zero-range bars → no candidate strictly above entry → ATR fallback
        # (ATR is 0 here, so the TP prices collapse onto the entry price).
        df = pd.DataFrame({"High": [100.0] * 60, "Low": [100.0] * 60,
                           "Close": [100.0] * 60})
        plan = detect_levels(df)
        assert plan.tp1_type.startswith("atr")
        assert plan.tp2_type.startswith("atr")
        assert plan.tp3_type.startswith("atr")
        assert plan.tp1 == pytest.approx(plan.entry_price)

    def test_confidence_rises_with_fib_structural_overlap(self):
        closes = list(range(50, 200))
        df = _ohlcv(closes)
        plan = detect_levels(df)
        # At least one fib/structural level in the TP set → above the floor.
        assert plan.confidence > 0.6

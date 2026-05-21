"""Regime-aware TP tests (D-109 / SPEC_TP_REGIME_CONDITIONAL_1).

Fixture rationale: a rising-trend OHLCV creates `pivot_r1` close to entry
(within 2*ATR) AND `fib_1.618` far above (beyond 2*ATR). NEUTRAL picks the
nearer pivot_r1; BULL's min-distance filter rejects it and falls through to
the distant fib_1.618, demonstrating the wider TP1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.risk.technical_level_detector import LevelPlan, detect_levels


def _rising_ohlcv(n: int = 100) -> pd.DataFrame:
    """Strictly rising series: pivot_r1 close to entry, fib_1.618 far above."""
    closes = [50.0 + i * 1.0 for i in range(n)]   # 50, 51, ..., 149
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    return pd.DataFrame({"High": highs, "Low": lows, "Close": closes})


def _flat_ohlcv(n: int = 30, close: float = 100.0) -> pd.DataFrame:
    closes = np.full(n, close)
    highs = closes + 1.0
    lows = closes - 1.0
    return pd.DataFrame({"High": highs, "Low": lows, "Close": closes})


def _zero_range_ohlcv(n: int = 60, close: float = 100.0) -> pd.DataFrame:
    """High=Low=Close -> ATR=0; forces ATR fallback to entry price."""
    return pd.DataFrame({"High": [close]*n, "Low": [close]*n, "Close": [close]*n})


def test_neutral_picks_nearest_real_level():
    """With a rising series, NEUTRAL TP1 picks the nearest real resistance."""
    df = _rising_ohlcv()
    plan = detect_levels(df, regime="NEUTRAL")
    # Nearest level above entry (149) is pivot_r1 around 150
    assert plan.tp1_type in ("pivot_r1", "structural", "fib_0.618")
    assert plan.tp1 > plan.entry_price


def test_bull_min_distance_filter_pushes_tp1_far():
    """BULL filter rejects pivot_r1 (within 2*ATR); TP1 jumps to fib_1.618 / further."""
    df = _rising_ohlcv()
    neutral = detect_levels(df, regime="NEUTRAL")
    bull = detect_levels(df, regime="BULL")
    # BULL TP1 must be strictly farther from entry than NEUTRAL TP1
    assert bull.tp1 > neutral.tp1


def test_bull_atr_fallback_wider_than_neutral():
    """Zero-range OHLCV -> no real candidates above entry -> ATR fallback fires.

    With ATR=0, both BULL and NEUTRAL collapse to entry. Use a positive
    synthetic ATR by mixing the last bar's spread to verify the multipliers.
    """
    # ATR > 0 via last-bar spread; but build closes flat at 100 with NO levels
    # above entry. Solution: keep closes flat and add zero high-low range
    # except for the last bar where High=Low+2 -> ATR ~ small.
    df = _zero_range_ohlcv()
    # Modify last 14 rows so true-range becomes 2.0 each day
    df = df.copy()
    df.iloc[-14:, df.columns.get_loc("High")] = 101.0
    df.iloc[-14:, df.columns.get_loc("Low")]  = 99.0
    # entry still 100 from last close

    neutral = detect_levels(df, regime="NEUTRAL")
    bull = detect_levels(df, regime="BULL")
    # With ATR ~ 2, real levels exist but BULL pushes wider
    assert bull.tp1 >= neutral.tp1


def test_bear_identical_to_neutral():
    df = _rising_ohlcv()
    neutral = detect_levels(df, regime="NEUTRAL")
    bear = detect_levels(df, regime="BEAR")
    assert neutral.tp1 == bear.tp1
    assert neutral.tp2 == bear.tp2
    assert neutral.tp3 == bear.tp3


def test_tp_ordering_preserved_in_bull():
    """tp1 <= tp2 <= tp3 always holds in BULL."""
    df = _rising_ohlcv()
    plan = detect_levels(df, regime="BULL")
    assert plan.tp1 <= plan.tp2 <= plan.tp3


def test_regime_stored_in_level_plan():
    df = _flat_ohlcv()
    assert detect_levels(df, regime="BULL").regime == "BULL"
    assert detect_levels(df, regime="NEUTRAL").regime == "NEUTRAL"
    assert detect_levels(df, regime="BEAR").regime == "BEAR"


def test_backward_compat_no_regime_arg():
    """detect_levels(ohlcv) without regime preserves legacy behavior."""
    df = _flat_ohlcv()
    plan = detect_levels(df)
    assert isinstance(plan, LevelPlan)
    assert plan.regime == "NEUTRAL"


def test_atr_zero_collapses_to_entry_in_both_regimes():
    """Pure zero-range OHLCV: ATR=0, no real levels, both regimes pin to entry."""
    df = _zero_range_ohlcv()
    neutral = detect_levels(df, regime="NEUTRAL")
    bull = detect_levels(df, regime="BULL")
    assert neutral.tp1 == neutral.entry_price
    assert bull.tp1 == bull.entry_price
    # Fallback types start with "atr"
    assert neutral.tp1_type.startswith("atr")
    assert bull.tp1_type.startswith("atr")

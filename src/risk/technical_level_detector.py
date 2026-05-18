"""Technical level detection for staged take-profit (SPEC_STAGED_TP_1, D-052).

Hierarchical detection: daily pivots, Fibonacci extensions (252d), structural
swing highs (60d), MA200, with an ATR-multiple fallback when too few real
levels exist above entry. Output feeds the staged exit manager (TP1/TP2/TP3).
All tunables come from src.signals.thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.signals.thresholds import (
    ATR_TP1_MULTIPLE,
    ATR_TP2_MULTIPLE,
    ATR_TP3_MULTIPLE,
    TP_CONFIDENCE_FLOOR,
    TP_CONFIDENCE_OVERLAP_BONUS,
    TP_FIB_LOOKBACK,
    TP_SWING_HIGH_LOOKBACK,
)


@dataclass(frozen=True)
class LevelPlan:
    entry_price: float
    tp1: float
    tp2: float
    tp3: float
    tp1_type: str
    tp2_type: str
    tp3_type: str
    support_1: float
    support_2: float
    confidence: float


def calculate_pivot_points(high: float, low: float, close: float) -> dict:
    """Standard daily pivot points."""
    pivot = (high + low + close) / 3.0
    return {
        "pivot": pivot,
        "resistance_1": 2.0 * pivot - low,
        "resistance_2": pivot + (high - low),
        "support_1": 2.0 * pivot - high,
        "support_2": pivot - (high - low),
    }


def calculate_fibonacci_levels(ohlcv: pd.DataFrame, lookback: int) -> dict:
    """Fib retracement/extension over the trailing window (low anchor)."""
    window = ohlcv.tail(lookback)
    hi = float(window["High"].max())
    lo = float(window["Low"].min())
    rng = hi - lo
    return {
        "fib_0.382": lo + 0.382 * rng,
        "fib_0.618": lo + 0.618 * rng,
        "fib_1.000": lo + 1.000 * rng,
        "fib_1.618": lo + 1.618 * rng,
    }


def identify_structural_resistance(ohlcv: pd.DataFrame, lookback: int) -> list[dict]:
    """Highest swing high over the trailing window."""
    window = ohlcv.tail(lookback)
    if window.empty:
        return []
    return [{"price": float(window["High"].max()), "type": "structural"}]


def calculate_ma200(ohlcv: pd.DataFrame) -> float | None:
    """MA200 trend reference (None if insufficient history)."""
    closes = ohlcv["Close"]
    if len(closes) < 1:
        return None
    window = min(len(closes), 200)
    return float(closes.tail(window).mean())


def calculate_atr(ohlcv: pd.DataFrame, period: int = 14) -> float:
    """Average True Range (Wilder-style simple mean of true range)."""
    high = ohlcv["High"]
    low = ohlcv["Low"]
    close = ohlcv["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    tr = tr.dropna()
    if tr.empty:
        return 0.0
    return float(tr.tail(period).mean())


def detect_levels(ohlcv: pd.DataFrame) -> LevelPlan:
    """Detect TP1/TP2/TP3 from OHLCV (columns: High, Low, Close)."""
    current = ohlcv.iloc[-1]
    entry = float(current["Close"])

    pivot = calculate_pivot_points(
        float(current["High"]), float(current["Low"]), entry
    )
    fib = calculate_fibonacci_levels(ohlcv, TP_FIB_LOOKBACK)
    structural = identify_structural_resistance(ohlcv, TP_SWING_HIGH_LOOKBACK)
    ma200 = calculate_ma200(ohlcv)
    atr = calculate_atr(ohlcv)

    candidates = [
        {"price": pivot["resistance_1"], "type": "pivot_r1"},
        {"price": pivot["resistance_2"], "type": "pivot_r2"},
        {"price": ma200, "type": "ma200"},
        {"price": fib["fib_0.618"], "type": "fib_0.618"},
        {"price": structural[0]["price"] if structural else None, "type": "structural"},
        {"price": fib["fib_1.618"], "type": "fib_1.618"},
    ]
    valid = [
        c for c in candidates
        if c["price"] is not None and entry < c["price"] < entry * 2.0
    ]
    valid.sort(key=lambda c: c["price"])

    tp1 = valid[0] if len(valid) > 0 else None
    tp2 = valid[1] if len(valid) > 1 else None
    tp3 = valid[2] if len(valid) > 2 else None

    if tp1 is None:
        tp1 = {"price": entry + ATR_TP1_MULTIPLE * atr, "type": "atr_1.5x"}
    if tp2 is None:
        tp2 = {"price": entry + ATR_TP2_MULTIPLE * atr, "type": "atr_3.0x"}
    if tp3 is None:
        tp3 = {"price": entry + ATR_TP3_MULTIPLE * atr, "type": "atr_5.0x"}

    overlap = sum(
        1 for lv in (tp1, tp2, tp3)
        if lv["type"].startswith("structural") or "fib" in lv["type"]
    )
    confidence = round(
        min(0.95, TP_CONFIDENCE_FLOOR + overlap * TP_CONFIDENCE_OVERLAP_BONUS), 4
    )

    return LevelPlan(
        entry_price=round(entry, 4),
        tp1=round(tp1["price"], 4),
        tp2=round(tp2["price"], 4),
        tp3=round(tp3["price"], 4),
        tp1_type=tp1["type"],
        tp2_type=tp2["type"],
        tp3_type=tp3["type"],
        support_1=round(pivot["support_1"], 4),
        support_2=round(pivot["support_2"], 4),
        confidence=confidence,
    )

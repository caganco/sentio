"""Technical level detection for staged take-profit (SPEC_STAGED_TP_1, D-052).

Hierarchical detection: daily pivots, Fibonacci extensions (252d), structural
swing highs (60d), MA200, with an ATR-multiple fallback when too few real
levels exist above entry. Output feeds the staged exit manager (TP1/TP2/TP3).

D-109 (SPEC_TP_REGIME_CONDITIONAL_1) adds regime-aware TP fallbacks. BULL uses
wider multiples (2.5/4.0/6.5xATR) + a minimum-distance filter on real TP1
candidates so winners can run. NEUTRAL/BEAR unchanged.

All tunables come from src.signals.thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.signals.thresholds import (
    ATR_TP1_MIN_DISTANCE_BULL,
    ATR_TP1_MULTIPLE,
    ATR_TP1_MULTIPLE_BULL,
    ATR_TP2_MULTIPLE,
    ATR_TP2_MULTIPLE_BULL,
    ATR_TP3_MULTIPLE,
    ATR_TP3_MULTIPLE_BULL,
    TP_CONFIDENCE_FLOOR,
    TP_CONFIDENCE_OVERLAP_BONUS,
    TP_FIB_LOOKBACK,
    TP_SWING_HIGH_LOOKBACK,
)

_REGIME_BULL = "BULL"


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
    regime: str = "NEUTRAL"   # D-109: audit trail (default preserves prior behavior)


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


def detect_levels(ohlcv: pd.DataFrame, regime: str = "NEUTRAL") -> LevelPlan:
    """Detect TP1/TP2/TP3 from OHLCV.

    Args:
        ohlcv: DataFrame with columns High, Low, Close (chronological).
        regime: Macro regime label. "BULL" activates wider TP targets
                (ATR_TP*_MULTIPLE_BULL) and a min-distance filter for TP1.
                "NEUTRAL"/"BEAR" preserve the legacy behavior.

    Returns:
        Frozen LevelPlan. `regime` field stored for audit.
    """
    is_bull = (regime == _REGIME_BULL)
    if is_bull:
        tp1_mult, tp2_mult, tp3_mult = (
            ATR_TP1_MULTIPLE_BULL, ATR_TP2_MULTIPLE_BULL, ATR_TP3_MULTIPLE_BULL,
        )
    else:
        tp1_mult, tp2_mult, tp3_mult = (
            ATR_TP1_MULTIPLE, ATR_TP2_MULTIPLE, ATR_TP3_MULTIPLE,
        )

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

    # D-109: BULL min-distance filter -- skip near-entry levels that will be
    # crossed quickly in a bull trend. Applied to TP1 candidate selection only.
    if is_bull and atr > 0:
        min_tp1_price = entry + ATR_TP1_MIN_DISTANCE_BULL * atr
        bull_filtered = [c for c in valid if c["price"] >= min_tp1_price]
        valid_for_tp1 = bull_filtered if bull_filtered else valid
    else:
        valid_for_tp1 = valid

    tp1 = valid_for_tp1[0] if valid_for_tp1 else None

    # TP2/TP3 picked from the full valid list, but must lie ABOVE TP1
    tp1_price = tp1["price"] if tp1 else entry
    above_tp1 = [c for c in valid if c["price"] > tp1_price]
    tp2 = above_tp1[0] if len(above_tp1) > 0 else None
    tp3 = above_tp1[1] if len(above_tp1) > 1 else None

    if tp1 is None:
        tp1 = {"price": entry + tp1_mult * atr, "type": f"atr_{tp1_mult}x"}
    if tp2 is None:
        tp2 = {"price": entry + tp2_mult * atr, "type": f"atr_{tp2_mult}x"}
    if tp3 is None:
        tp3 = {"price": entry + tp3_mult * atr, "type": f"atr_{tp3_mult}x"}

    # D-109: enforce tp1 <= tp2 <= tp3. When BULL min-distance pushes TP1 to
    # a far real level (e.g., fib_1.618), the entry-anchored ATR fallback for
    # TP2/TP3 can land below it. Bump TP2/TP3 to (tp1 + tp_step) in that case.
    if tp2["price"] < tp1["price"]:
        tp2 = {"price": tp1["price"] + max(atr, 1e-6) * (tp2_mult - tp1_mult),
               "type": f"atr_from_tp1_{tp2_mult - tp1_mult:.1f}x"}
    if tp3["price"] < tp2["price"]:
        tp3 = {"price": tp2["price"] + max(atr, 1e-6) * (tp3_mult - tp2_mult),
               "type": f"atr_from_tp2_{tp3_mult - tp2_mult:.1f}x"}

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
        regime=regime,
    )

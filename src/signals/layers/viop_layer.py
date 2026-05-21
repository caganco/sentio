"""VIOP derivatives signal layer (L5b) — D-099.

Produces a LayerScore from BIST VIOP Put/Call OI ratio and open-interest delta.
VERDA-independent: data comes directly from borsaistanbul.com CSV files.

Not yet wired into engine.py — weight=0.0 until DEC-014 wiring task.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import pandas as pd

from src.data.viop_fetcher import (
    _last_trading_day,
    compute_oi_delta,
    compute_pc_ratio,
    compute_ticker_oi,
    fetch_viop_csv,
)
from src.signals.models import LayerScore
from src.signals.thresholds import (
    MASTER_WEIGHTS,
    VIOP_MIN_OI,
    VIOP_OI_DELTA_BOOST,
    VIOP_OI_DELTA_THRESHOLD,
    VIOP_PC_SCORES,
    VIOP_PC_THRESHOLDS,
)

logger = logging.getLogger(__name__)

# weight=0.0 sentinel: layer computed but not yet included in composite formula
_VIOP_WEIGHT: float = MASTER_WEIGHTS.get("viop", 0.0)


# ---------------------------------------------------------------------------
# Score mapping
# ---------------------------------------------------------------------------

def _pc_to_score(pc_ratio: float) -> float:
    """Map a Put/Call ratio to a 0-100 signal score via VIOP_PC_THRESHOLDS."""
    if pc_ratio < VIOP_PC_THRESHOLDS["very_bullish"]:
        return VIOP_PC_SCORES["very_bullish"]
    if pc_ratio < VIOP_PC_THRESHOLDS["bullish"]:
        return VIOP_PC_SCORES["bullish"]
    if pc_ratio < VIOP_PC_THRESHOLDS["neutral_low"]:
        return VIOP_PC_SCORES["neutral_low"]
    if pc_ratio < VIOP_PC_THRESHOLDS["neutral_high"]:
        return VIOP_PC_SCORES["neutral_high"]
    if pc_ratio < VIOP_PC_THRESHOLDS["bearish"]:
        return VIOP_PC_SCORES["bearish"]
    return VIOP_PC_SCORES["very_bearish"]


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------

def score_viop(
    symbol: str,
    viop_df: Optional[pd.DataFrame] = None,
    yesterday_df: Optional[pd.DataFrame] = None,
    as_of_date: Optional[date] = None,
) -> LayerScore:
    """Compute the VIOP derivatives signal for *symbol*.

    Args:
        symbol: Ticker with or without '.IS' suffix (e.g. 'THYAO' or 'THYAO.IS').
        viop_df: Pre-loaded VIOP bulletin DataFrame. Auto-fetched (T-1) if None.
        yesterday_df: Previous day's DataFrame for OI delta. Optional.
        as_of_date: Signal date override. Defaults to T-1.

    Returns:
        LayerScore with layer="viop", score in [0, 100], confidence in [0, 1].
    """
    target_date = as_of_date or _last_trading_day()

    # Auto-fetch when not injected (live path)
    if viop_df is None:
        viop_df = fetch_viop_csv(target_date)

    # No data at all
    if viop_df is None or viop_df.empty:
        return LayerScore(
            layer="viop",
            score=50.0,
            confidence=0.0,
            weight=_VIOP_WEIGHT,
            detail={"symbol": symbol, "error": "no_data", "as_of_date": str(target_date)},
            source="missing",
        )

    ticker = symbol.replace(".IS", "").upper()
    today_oi = compute_ticker_oi(viop_df, ticker)

    # Insufficient OI → unreliable signal
    if today_oi["total_oi"] < VIOP_MIN_OI:
        return LayerScore(
            layer="viop",
            score=50.0,
            confidence=0.3,
            weight=_VIOP_WEIGHT,
            detail={
                "symbol": ticker,
                "total_oi": today_oi["total_oi"],
                "min_oi_required": VIOP_MIN_OI,
                "reason": "insufficient_oi",
                "as_of_date": str(target_date),
            },
            source="partial",
        )

    pc_ratio = compute_pc_ratio(today_oi)
    base_score = _pc_to_score(pc_ratio)

    # OI delta modifier — only when yesterday data is available
    oi_delta = 0.0
    if yesterday_df is not None and not yesterday_df.empty:
        yesterday_oi = compute_ticker_oi(yesterday_df, ticker)
        oi_delta = compute_oi_delta(today_oi, yesterday_oi)
        if abs(oi_delta) > VIOP_OI_DELTA_THRESHOLD:
            # Boost when OI growth confirms signal direction; dampen when it diverges
            if base_score > 50.0 and oi_delta > 0:
                direction = 1
            elif base_score < 50.0 and oi_delta < 0:
                direction = 1   # more puts + OI growing = more bearish conviction
            else:
                direction = -1  # OI direction contradicts score → reduce confidence via score pull
            base_score = max(0.0, min(100.0, base_score + direction * VIOP_OI_DELTA_BOOST))

    # Confidence scales with OI volume — caps at 1.0 when OI ≥ 10× VIOP_MIN_OI
    oi_volume_factor = min(1.0, today_oi["total_oi"] / (VIOP_MIN_OI * 10))
    confidence = round(0.5 + 0.5 * oi_volume_factor, 4)

    return LayerScore(
        layer="viop",
        score=base_score,
        confidence=confidence,
        weight=_VIOP_WEIGHT,
        detail={
            "symbol": ticker,
            "call_oi": today_oi["call_oi"],
            "put_oi": today_oi["put_oi"],
            "total_oi": today_oi["total_oi"],
            "pc_ratio": round(pc_ratio, 4),
            "oi_delta_pct": round(oi_delta * 100, 2),
            "as_of_date": str(target_date),
        },
        source="computed",
    )

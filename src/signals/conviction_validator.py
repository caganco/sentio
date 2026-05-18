"""Conviction score + tier derivation (SPEC_SIGNAL_CONVICTION_1, D-052).

The engine keeps its internal 0-100 scoring untouched. Conviction is a DERIVED
layer on top: the reweighted composite (0-100) is mapped to a [0,1] conviction
score, modulated by macro context, and classified into a fixed quality tier.

Frequency is an OUTCOME, not a target -- no frequency validation here (SPEC 1.3).
All constants come from src.signals.thresholds (no magic numbers).
"""
from __future__ import annotations

from src.signals.thresholds import (
    CONVICTION_MACRO_BULL_MIN,
    CONVICTION_MACRO_MULT_BEAR,
    CONVICTION_MACRO_MULT_BULL,
    CONVICTION_MACRO_MULT_NEUTRAL,
    CONVICTION_MACRO_NEUTRAL_MIN,
    CONVICTION_MEDIUM,
    CONVICTION_STRONG,
)

TIER_STRONG = "BUY-STRONG"
TIER_MEDIUM = "BUY-MEDIUM"
TIER_WATCH = "WATCH"


def macro_multiplier(l2_macro_score: float) -> float:
    """Macro modulation multiplier from the L2 macro score (0-100 engine scale).

    >=65 -> 1.2 (bullish strengthen), >=50 -> 1.0 (neutral), <50 -> 0.85.
    """
    if l2_macro_score >= CONVICTION_MACRO_BULL_MIN:
        return CONVICTION_MACRO_MULT_BULL
    if l2_macro_score >= CONVICTION_MACRO_NEUTRAL_MIN:
        return CONVICTION_MACRO_MULT_NEUTRAL
    return CONVICTION_MACRO_MULT_BEAR


def classify_tier(conviction_score: float) -> str:
    """Map a [0,1] conviction score to a fixed quality tier."""
    if conviction_score >= CONVICTION_STRONG:
        return TIER_STRONG
    if conviction_score >= CONVICTION_MEDIUM:
        return TIER_MEDIUM
    return TIER_WATCH


def compute_conviction(
    composite_0_100: float, l2_macro_score: float
) -> tuple[float, str]:
    """Derive (conviction_score, conviction_tier) from the reweighted composite.

    Args:
        composite_0_100: reweighted weighted-sum from the engine (0-100 scale).
        l2_macro_score: L2 macro layer score (0-100 engine scale).

    Returns:
        (conviction_score in [0,1], tier in {BUY-STRONG, BUY-MEDIUM, WATCH}).
    """
    base = max(0.0, min(1.0, composite_0_100 / 100.0))
    score = min(1.0, base * macro_multiplier(l2_macro_score))
    score = round(score, 4)
    return score, classify_tier(score)

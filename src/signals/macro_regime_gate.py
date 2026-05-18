"""Macro regime gate: L2 macro score -> position sizing multiplier (D-052).

SPEC_MACRO_REGIME_GATE_2 converts the binary macro veto into a position
SCALING factor. Task success criteria are authoritative and use a FLAT 0.8 in
the neutral band (no linear interpolation):

    L2 >= 60  -> BULL    -> 1.0x  (full sizing)
    45 <= L2  -> NEUTRAL -> 0.8x  (reduced sizing)
    L2 < 45   -> BEAR    -> 0.0x  (no new entries)

L2 score is on the engine's 0-100 scale. All constants from thresholds.py.
"""
from __future__ import annotations

from src.signals.thresholds import (
    MACRO_GATE_BULL_MIN,
    MACRO_GATE_NEUTRAL_MIN,
    MACRO_GATE_SCALING_BEAR,
    MACRO_GATE_SCALING_BULL,
    MACRO_GATE_SCALING_NEUTRAL,
)

REGIME_BULL = "BULL"
REGIME_NEUTRAL = "NEUTRAL"
REGIME_BEAR = "BEAR"


def classify_regime(l2_macro_score: float) -> str:
    """Classify the macro regime from the L2 macro score (0-100 scale)."""
    if l2_macro_score >= MACRO_GATE_BULL_MIN:
        return REGIME_BULL
    if l2_macro_score >= MACRO_GATE_NEUTRAL_MIN:
        return REGIME_NEUTRAL
    return REGIME_BEAR


def calculate_macro_regime_scaling(l2_macro_score: float) -> float:
    """Position sizing multiplier in {1.0, 0.8, 0.0} from the L2 macro score."""
    regime = classify_regime(l2_macro_score)
    if regime == REGIME_BULL:
        return MACRO_GATE_SCALING_BULL
    if regime == REGIME_NEUTRAL:
        return MACRO_GATE_SCALING_NEUTRAL
    return MACRO_GATE_SCALING_BEAR

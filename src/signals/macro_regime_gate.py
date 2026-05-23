"""Macro regime gate: L2 macro score -> position sizing multiplier.

v1 (D-052, SPEC_MACRO_REGIME_GATE_2): binary veto -> flat 0.8 neutral / 0.0 bear.
v2 (D-108, SPEC_MACRO_GATE_SOFTENING_1): CDS-percentile overlay softens BEAR.

    v1: calculate_macro_regime_scaling(l2)            -> float in {1.0, 0.8, 0.0}
    v2: calculate_macro_regime_scaling_v2(l2, cds_pct, hard_flags) -> MacroScalingResult

v1 callers untouched (backward compat). Hard exits (CDS > 600 bps, USDTRY +3sigma,
portfolio DD >= 15%) override the soft path in v2.

Ref: Longstaff, Pan, Pedersen, Singleton (2011) NBER 16563.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.signals.thresholds import (
    CDS_PERCENTILE_HIGH,
    CDS_PERCENTILE_LOW,
    CDS_SCALING_HIGH,
    MACRO_GATE_BULL_MIN,
    MACRO_GATE_HARD_EXIT_CDS_BPS,
    MACRO_GATE_HARD_EXIT_USDTRY_SIGMA,
    MACRO_GATE_NEUTRAL_MIN,
    MACRO_GATE_SCALING_BEAR,
    MACRO_GATE_SCALING_BULL,
    MACRO_GATE_SCALING_NEUTRAL,
    MACRO_GATE_THRESHOLDS,
    MAX_DRAWDOWN_HARD_STOP,
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
    """v1: position sizing multiplier in {1.0, 0.8, 0.0}. Backward compatible."""
    regime = classify_regime(l2_macro_score)
    if regime == REGIME_BULL:
        return MACRO_GATE_SCALING_BULL
    if regime == REGIME_NEUTRAL:
        return MACRO_GATE_SCALING_NEUTRAL
    return MACRO_GATE_SCALING_BEAR


# ---------------------------------------------------------------------------
# v2 (D-108): CDS-percentile-conditional soft BEAR gate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HardExitFlags:
    """Hard exit conditions; if any active, scaling is 0.0 regardless of regime/CDS.

    Phase 1: usdtry_zscore stays 0.0 (no z-score pipeline yet -- placeholder).
    portfolio_drawdown is mirrored here for symmetry but the active enforcement
    lives in position_sizer_v2 (MAX_DRAWDOWN_HARD_STOP).
    """
    cds_bps: float = 0.0
    usdtry_zscore: float = 0.0
    portfolio_drawdown: float = 0.0   # Positive fraction (0.12 = -12%)

    @property
    def is_active(self) -> bool:
        return (
            self.cds_bps >= MACRO_GATE_HARD_EXIT_CDS_BPS
            or self.usdtry_zscore >= MACRO_GATE_HARD_EXIT_USDTRY_SIGMA
            or self.portfolio_drawdown >= MAX_DRAWDOWN_HARD_STOP
        )

    @property
    def reason(self) -> str:
        if self.cds_bps >= MACRO_GATE_HARD_EXIT_CDS_BPS:
            return f"CDS {self.cds_bps:.0f} bps >= {MACRO_GATE_HARD_EXIT_CDS_BPS:.0f} hard exit threshold"
        if self.usdtry_zscore >= MACRO_GATE_HARD_EXIT_USDTRY_SIGMA:
            return f"USDTRY z-score {self.usdtry_zscore:.1f} >= +{MACRO_GATE_HARD_EXIT_USDTRY_SIGMA:.0f}sigma"
        if self.portfolio_drawdown >= MAX_DRAWDOWN_HARD_STOP:
            return f"portfolio DD {self.portfolio_drawdown:.1%} >= hard stop"
        return ""


@dataclass(frozen=True)
class MacroScalingResult:
    scaling: float          # Final position sizing multiplier in [0.0, 1.0]
    regime: str             # BULL | NEUTRAL | BEAR
    cds_overlay: float      # CDS dampening factor applied [CDS_SCALING_HIGH, 1.0]
    hard_exit: bool         # True if a hard exit triggered
    reason: str             # Audit explanation


def _cds_overlay(cds_percentile: float) -> float:
    """CDS percentile -> scaling multiplier in [CDS_SCALING_HIGH, 1.0]."""
    if cds_percentile <= CDS_PERCENTILE_LOW:
        return 1.0
    if cds_percentile >= CDS_PERCENTILE_HIGH:
        return CDS_SCALING_HIGH
    span = CDS_PERCENTILE_HIGH - CDS_PERCENTILE_LOW
    return round(
        1.0 - (1.0 - CDS_SCALING_HIGH) * (cds_percentile - CDS_PERCENTILE_LOW) / span,
        4,
    )


def _l2_base_scaling(l2_macro_score: float) -> float:
    """CB-002: L2 score -> base position-size multiplier (floor, no full block).

    First band whose threshold L2 does not reach wins; >= 60 -> 1.0:
        L2 < 30 -> 0.3 | 30-45 -> 0.5 | 45-60 -> 0.8 | >= 60 -> 1.0
    """
    for threshold, mult in MACRO_GATE_THRESHOLDS:
        if l2_macro_score < threshold:
            return mult
    return MACRO_GATE_SCALING_BULL


def calculate_macro_regime_scaling_v2(
    l2_macro_score: float,
    cds_percentile: float,
    hard_exit_flags: HardExitFlags | None = None,
) -> MacroScalingResult:
    """L2-step soft scaling x CDS overlay position-size multiplier (CB-002).

    Base scaling comes from the L2-step floor (no full block below L2=45), then
    the DEC-017 CDS-percentile overlay dampens it multiplicatively. Hard exits
    (CDS >= 600 bps, USDTRY z-score, portfolio DD) still force 0.0.

    Args:
        l2_macro_score: L2 engine score [0, 100].
        cds_percentile: Pre-computed rolling CDS percentile [0, 1].
                        Use 0.5 as a no-dampening fallback when history < 30d.
        hard_exit_flags: Optional. None -> no hard exit check.

    Returns:
        MacroScalingResult with final scaling, regime, and audit trail.
    """
    if hard_exit_flags is not None and hard_exit_flags.is_active:
        return MacroScalingResult(
            scaling=0.0, regime=REGIME_BEAR, cds_overlay=0.0,
            hard_exit=True, reason=hard_exit_flags.reason,
        )

    regime = classify_regime(l2_macro_score)
    overlay = _cds_overlay(cds_percentile)
    base = _l2_base_scaling(l2_macro_score)
    scaling = round(base * overlay, 4)

    return MacroScalingResult(
        scaling=scaling, regime=regime, cds_overlay=overlay, hard_exit=False,
        reason=(
            f"CB-002 {regime} L2={l2_macro_score:.1f} base={base:.2f} "
            f"CDS_pct={cds_percentile:.2f} overlay={overlay:.2f} -> {scaling:.3f}x"
        ),
    )

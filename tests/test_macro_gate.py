"""Tests for CB-002: macro gate hard block -> L2-step soft scaling.

v2 base scaling now comes from an L2 step function (floor 0.3, no full block
below L2=45); the DEC-017 CDS-percentile overlay still dampens multiplicatively,
and hard exits (CDS >= 600 bps, USDTRY z-score, DD) still force 0.0.

    L2 < 30 -> 0.3 | 30-45 -> 0.5 | 45-60 -> 0.8 | >= 60 -> 1.0   (overlay = 1.0)
"""
from __future__ import annotations

import pytest

from src.signals.macro_regime_gate import (
    HardExitFlags,
    MacroScalingResult,
    calculate_macro_regime_scaling_v2,
)

# CDS percentile 0.5 -> overlay 1.0 (no dampening); isolates the L2-step base.
_NEUTRAL_CDS = 0.5


def _scale(l2: float, cds: float = _NEUTRAL_CDS, flags=None) -> MacroScalingResult:
    return calculate_macro_regime_scaling_v2(l2, cds, hard_exit_flags=flags)


class TestL2StepScaling:

    @pytest.mark.parametrize("l2,expected", [
        (25.0, 0.3),   # success criterion: L2=25 -> 0.3 (not zero)
        (35.0, 0.5),   # success criterion: L2=35 -> 0.5 (not zero)
        (50.0, 0.8),   # NEUTRAL band unchanged
        (65.0, 1.0),   # success criterion: L2=65 -> 1.0
    ])
    def test_l2_step_base(self, l2: float, expected: float) -> None:
        assert _scale(l2).scaling == pytest.approx(expected)

    def test_low_l2_not_zero(self) -> None:
        """CB-002 core: BEAR no longer fully blocks entries."""
        assert _scale(25.0).scaling > 0.0
        assert _scale(35.0).scaling > 0.0

    @pytest.mark.parametrize("l2,expected", [
        (29.99, 0.3), (30.0, 0.5), (44.99, 0.5), (45.0, 0.8), (59.99, 0.8), (60.0, 1.0),
    ])
    def test_band_boundaries(self, l2: float, expected: float) -> None:
        assert _scale(l2).scaling == pytest.approx(expected)


class TestHardExitsPreserved:

    def test_cds_hard_exit_still_blocks(self) -> None:
        """RISK_OFF override stays a hard gate (CDS >= 600 bps)."""
        r = _scale(35.0, flags=HardExitFlags(cds_bps=650.0))
        assert r.scaling == 0.0
        assert r.hard_exit is True
        assert "CDS" in r.reason

    def test_cds_below_600_does_not_hard_block(self) -> None:
        """Threshold stays 600 (directive 400 overridden): CDS=500 bps -> floor, not 0."""
        r = _scale(35.0, flags=HardExitFlags(cds_bps=500.0))
        assert r.scaling == pytest.approx(0.5)
        assert r.hard_exit is False

    def test_usdtry_sigma_still_blocks(self) -> None:
        r = _scale(35.0, flags=HardExitFlags(usdtry_zscore=3.5))
        assert r.scaling == 0.0
        assert r.hard_exit is True


class TestCdsOverlayInteraction:

    def test_overlay_dampens_floor_but_not_zero(self) -> None:
        """High CDS percentile dampens the floor multiplicatively, never to 0."""
        r = _scale(35.0, cds=0.95)   # base 0.5 x overlay 0.25
        assert r.scaling == pytest.approx(0.125)
        assert 0.0 < r.scaling < 0.5

    def test_bull_unchanged_under_normal_cds(self) -> None:
        assert _scale(70.0).scaling == pytest.approx(1.0)

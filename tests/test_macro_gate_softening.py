"""Macro gate softening v2 tests (D-108 Phase B / SPEC_MACRO_GATE_SOFTENING_1)."""
from __future__ import annotations

import pytest

from src.signals.macro_regime_gate import (
    HardExitFlags,
    MacroScalingResult,
    _cds_overlay,
    calculate_macro_regime_scaling_v2,
)


# ---- _cds_overlay unit tests -----------------------------------------------

class TestCdsOverlay:

    def test_below_low_threshold_no_dampening(self) -> None:
        assert _cds_overlay(0.30) == 1.0
        assert _cds_overlay(0.50) == 1.0

    def test_above_high_threshold_max_dampening(self) -> None:
        assert _cds_overlay(0.90) == 0.25
        assert _cds_overlay(0.99) == 0.25

    def test_midpoint_linear(self) -> None:
        """0.70 is halfway between 0.50 and 0.90 -> 1.0 - 0.75*0.5 = 0.625."""
        assert abs(_cds_overlay(0.70) - 0.625) < 0.001


# ---- BULL regime -----------------------------------------------------------

class TestBullRegime:

    def test_cds_normal_full_size(self) -> None:
        r = calculate_macro_regime_scaling_v2(65.0, 0.40)
        assert r.regime == "BULL"
        assert r.scaling == 1.0
        assert r.hard_exit is False

    def test_cds_high_reduced(self) -> None:
        r = calculate_macro_regime_scaling_v2(65.0, 0.92)
        assert r.regime == "BULL"
        assert abs(r.scaling - 0.25) < 0.001


# ---- BEAR soft gate --------------------------------------------------------

class TestBearSoftGate:

    def test_cds_low_soft_entry(self) -> None:
        """CB-002: L2 in 30-45 + CDS normal -> base floor 0.5 (NOT hard 0.0x)."""
        r = calculate_macro_regime_scaling_v2(40.0, 0.30)
        assert r.regime == "BEAR"
        assert abs(r.scaling - 0.5) < 0.001    # base 0.5 x overlay 1.0
        assert r.hard_exit is False

    def test_cds_high_dampens_bear_floor(self) -> None:
        """CB-002: L2 < 45 + CDS >= 90th pct -> floor x overlay (dampened, not hard 0)."""
        r = calculate_macro_regime_scaling_v2(40.0, 0.92)
        assert r.regime == "BEAR"
        assert abs(r.scaling - 0.125) < 0.001  # base 0.5 x overlay 0.25
        assert r.hard_exit is False

    def test_cds_midband_partial(self) -> None:
        """CB-002: L2 in 30-45, CDS = 70th pct -> base 0.5 x overlay 0.625 = 0.3125."""
        r = calculate_macro_regime_scaling_v2(40.0, 0.70)
        assert r.regime == "BEAR"
        assert abs(r.scaling - 0.3125) < 0.001


# ---- Hard exits ------------------------------------------------------------

class TestHardExits:

    def test_cds_above_600bps_overrides(self) -> None:
        flags = HardExitFlags(cds_bps=650.0)
        r = calculate_macro_regime_scaling_v2(70.0, 0.20, hard_exit_flags=flags)
        assert r.scaling == 0.0
        assert r.hard_exit is True
        assert "CDS" in r.reason

    def test_usdtry_sigma_overrides(self) -> None:
        flags = HardExitFlags(usdtry_zscore=3.5)
        r = calculate_macro_regime_scaling_v2(65.0, 0.30, hard_exit_flags=flags)
        assert r.scaling == 0.0
        assert r.hard_exit is True

    def test_no_hard_exit_when_flags_none(self) -> None:
        r = calculate_macro_regime_scaling_v2(40.0, 0.40, hard_exit_flags=None)
        assert r.hard_exit is False
        assert r.scaling > 0.0

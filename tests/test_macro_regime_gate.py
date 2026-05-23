"""Tests for the macro regime gate (SPEC_MACRO_REGIME_GATE_2, D-052)."""
import pytest

from src.signals.macro_regime_gate import (
    REGIME_BEAR,
    REGIME_BULL,
    REGIME_NEUTRAL,
    calculate_macro_regime_scaling,
    classify_regime,
)
from src.signals.thresholds import (
    MACRO_GATE_SCALING_BEAR,
    MACRO_GATE_SCALING_BULL,
    MACRO_GATE_SCALING_NEUTRAL,
)


class TestClassifyRegime:
    @pytest.mark.parametrize(
        "l2,regime",
        [
            (60.0, REGIME_BULL),
            (100.0, REGIME_BULL),
            (59.99, REGIME_NEUTRAL),
            (45.0, REGIME_NEUTRAL),
            (44.99, REGIME_BEAR),
            (0.0, REGIME_BEAR),
        ],
    )
    def test_regime_boundaries(self, l2, regime):
        assert classify_regime(l2) == regime


class TestRegimeScaling:
    @pytest.mark.parametrize(
        "l2,scaling",
        [
            (75.0, MACRO_GATE_SCALING_BULL),
            (60.0, MACRO_GATE_SCALING_BULL),
            (55.0, MACRO_GATE_SCALING_NEUTRAL),
            (45.0, MACRO_GATE_SCALING_NEUTRAL),
            (44.99, MACRO_GATE_SCALING_BEAR),
            (10.0, MACRO_GATE_SCALING_BEAR),
        ],
    )
    def test_scaling_matrix(self, l2, scaling):
        assert calculate_macro_regime_scaling(l2) == scaling

    def test_neutral_is_flat_not_interpolated(self):
        # Task criteria: flat 0.8 across the whole neutral band (no interpolation)
        assert calculate_macro_regime_scaling(45.0) == calculate_macro_regime_scaling(
            59.99
        )
        assert calculate_macro_regime_scaling(50.0) == MACRO_GATE_SCALING_NEUTRAL

    def test_bear_blocks_entries(self):
        assert calculate_macro_regime_scaling(30.0) == 0.0

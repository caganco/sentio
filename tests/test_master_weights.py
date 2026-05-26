"""D-154: L6 composite removal + EM_RELSTRENGTH assertions.

Tests:
- risk key removed from MASTER_WEIGHTS
- 5-layer Sigma = 1.000
- ASSET_DIRECTIONS swap: BIST100 out, EM_RELSTRENGTH in
- RUNTIME_NORMALIZER_FLOOR consistent with weight_validator
- New threshold constants exist
"""
from __future__ import annotations

import pytest

from src.signals.thresholds import (
    ASSET_DIRECTIONS,
    EM_RELSTRENGTH_LOOKBACK,
    EM_RELSTRENGTH_SCALE,
    MASTER_WEIGHTS,
    RUNTIME_NORMALIZER_FLOOR,
)


class TestMasterWeightsSum:
    def test_risk_removed(self):
        """L6/risk must NOT be in MASTER_WEIGHTS after D-154."""
        assert "risk" not in MASTER_WEIGHTS

    def test_sum_is_one(self):
        """5-layer Sigma must equal 1.000 exactly (within floating-point tolerance)."""
        assert abs(sum(MASTER_WEIGHTS.values()) - 1.0) < 1e-9

    def test_five_layers(self):
        """Exactly 5 layers remain after L6 removal."""
        assert len(MASTER_WEIGHTS) == 5

    def test_expected_keys(self):
        """All expected layer keys present."""
        expected = {"technical", "macro", "kap", "sentiment", "smart_money"}
        assert set(MASTER_WEIGHTS.keys()) == expected


class TestAssetDirections:
    def test_em_relstrength_in_asset_directions(self):
        """EM_RELSTRENGTH must be in ASSET_DIRECTIONS after D-154 swap."""
        assert "EM_RELSTRENGTH" in ASSET_DIRECTIONS

    def test_bist100_not_in_asset_directions(self):
        """BIST100 must be removed from ASSET_DIRECTIONS (circular feedback fix)."""
        assert "BIST100" not in ASSET_DIRECTIONS

    def test_em_relstrength_direction_positive(self):
        """EM_RELSTRENGTH direction = +1.0 (BIST outperforming EM → bullish)."""
        assert ASSET_DIRECTIONS["EM_RELSTRENGTH"] == pytest.approx(1.0)


class TestRuntimeFloor:
    def test_runtime_floor_consistent_with_validator(self):
        """RUNTIME_NORMALIZER_FLOOR must match emergent_normalizer_floor()."""
        from src.utils.weight_validator import emergent_normalizer_floor
        assert abs(emergent_normalizer_floor() - RUNTIME_NORMALIZER_FLOOR) < 1e-9

    def test_runtime_floor_below_old_value(self):
        """D-154: new floor ~0.773 < old 0.78 (L6 weight redistributed)."""
        assert RUNTIME_NORMALIZER_FLOOR < 0.78


class TestNewConstants:
    def test_em_relstrength_lookback_positive_int(self):
        assert isinstance(EM_RELSTRENGTH_LOOKBACK, int)
        assert EM_RELSTRENGTH_LOOKBACK > 0

    def test_em_relstrength_scale_positive_float(self):
        assert isinstance(EM_RELSTRENGTH_SCALE, float)
        assert EM_RELSTRENGTH_SCALE > 0

"""Tests for conviction derivation (SPEC_SIGNAL_CONVICTION_1, D-052)."""
import pytest

from src.signals.conviction_validator import (
    TIER_MEDIUM,
    TIER_STRONG,
    TIER_WATCH,
    classify_tier,
    compute_conviction,
    macro_multiplier,
)
from src.signals.thresholds import (
    CONVICTION_MACRO_MULT_BEAR,
    CONVICTION_MACRO_MULT_BULL,
    CONVICTION_MACRO_MULT_NEUTRAL,
)


class TestMacroMultiplier:
    @pytest.mark.parametrize(
        "l2,expected",
        [
            (65.0, CONVICTION_MACRO_MULT_BULL),
            (80.0, CONVICTION_MACRO_MULT_BULL),
            (64.99, CONVICTION_MACRO_MULT_NEUTRAL),
            (50.0, CONVICTION_MACRO_MULT_NEUTRAL),
            (49.99, CONVICTION_MACRO_MULT_BEAR),
            (0.0, CONVICTION_MACRO_MULT_BEAR),
        ],
    )
    def test_boundaries(self, l2, expected):
        assert macro_multiplier(l2) == expected


class TestClassifyTier:
    @pytest.mark.parametrize(
        "score,tier",
        [
            (1.00, TIER_STRONG),
            (0.68, TIER_STRONG),
            (0.6799, TIER_MEDIUM),
            (0.55, TIER_MEDIUM),
            (0.5499, TIER_WATCH),
            (0.00, TIER_WATCH),
        ],
    )
    def test_tier_boundaries(self, score, tier):
        assert classify_tier(score) == tier


class TestComputeConviction:
    def test_neutral_macro_passthrough(self):
        score, tier = compute_conviction(78.0, 50.0)
        assert score == pytest.approx(0.78)
        assert tier == TIER_STRONG

    def test_bear_macro_weakens(self):
        # 60/100 = 0.60 base, * 0.85 = 0.51 -> WATCH
        score, tier = compute_conviction(60.0, 40.0)
        assert score == pytest.approx(0.51)
        assert tier == TIER_WATCH

    def test_bull_macro_strengthens_and_clamps(self):
        # 100/100 = 1.0 base, * 1.2 = 1.2 -> clamp 1.0
        score, tier = compute_conviction(100.0, 70.0)
        assert score == 1.0
        assert tier == TIER_STRONG

    def test_medium_band(self):
        # 65/100 = 0.65 * 1.0 = 0.65 -> BUY-MEDIUM
        score, tier = compute_conviction(65.0, 55.0)
        assert score == pytest.approx(0.65)
        assert tier == TIER_MEDIUM

    @pytest.mark.parametrize("bad", [-10.0, 150.0])
    def test_composite_clamped_to_unit_range(self, bad):
        score, _ = compute_conviction(bad, 50.0)
        assert 0.0 <= score <= 1.0

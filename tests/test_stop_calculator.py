"""Volatility-aware stop tests (D-110 / SPEC_STOPLOSS_VOLATILITY_AWARE_1)."""
from __future__ import annotations

import pytest

from src.risk.stop_calculator import (
    VOL_TIER_EXTREME,
    VOL_TIER_HIGH,
    VOL_TIER_LOW,
    VOL_TIER_MID,
    calculate_stop,
    classify_vol_tier,
)
from src.signals.thresholds import (
    RISK_PER_TRADE_PCT,
    STOP_HARD_FLOOR,
    STOP_LOSS_EXTREME_VOL,
    STOP_LOSS_HIGH_VOL,
    STOP_LOSS_LOW_VOL,
    STOP_LOSS_MID_VOL,
)


# ---- Vol tier classification ----------------------------------------------

class TestVolTierClassification:

    def test_low_vol(self):
        assert classify_vol_tier(0.015) == VOL_TIER_LOW

    def test_mid_vol(self):
        assert classify_vol_tier(0.03) == VOL_TIER_MID

    def test_high_vol(self):
        assert classify_vol_tier(0.05) == VOL_TIER_HIGH

    def test_extreme_vol(self):
        assert classify_vol_tier(0.07) == VOL_TIER_EXTREME

    def test_boundary_assignment(self):
        # Boundaries: exact 2% -> mid, 4% -> high, 6% -> extreme
        assert classify_vol_tier(0.02) == VOL_TIER_MID
        assert classify_vol_tier(0.04) == VOL_TIER_HIGH
        assert classify_vol_tier(0.06) == VOL_TIER_EXTREME


# ---- Stop calculation -----------------------------------------------------

class TestStopCalculation:

    def test_low_vol_ttkom_like(self):
        """TTKOM-like: entry=60.65, ATR/P~1.8% -> -6% stop."""
        entry = 60.65
        atr = entry * 0.018
        r = calculate_stop(entry, atr, 100_000)
        assert r.vol_tier == VOL_TIER_LOW
        assert abs(r.stop_distance_pct - STOP_LOSS_LOW_VOL) < 1e-6
        assert abs(r.stop_price - entry * (1 - STOP_LOSS_LOW_VOL)) < 0.01

    def test_high_vol_aksen_like(self):
        """AKSEN-like: entry=87.59, ATR/P~5% -> -12% stop."""
        entry = 87.59
        atr = entry * 0.05
        r = calculate_stop(entry, atr, 100_000)
        assert r.vol_tier == VOL_TIER_HIGH
        assert abs(r.stop_distance_pct - STOP_LOSS_HIGH_VOL) < 1e-6

    def test_extreme_vol_enery_like(self):
        """ENERY-like: entry=9.07, ATR/P~7% -> -15% stop."""
        entry = 9.07
        atr = entry * 0.07
        r = calculate_stop(entry, atr, 100_000)
        assert r.vol_tier == VOL_TIER_EXTREME
        assert abs(r.stop_distance_pct - STOP_LOSS_EXTREME_VOL) < 1e-6

    def test_hard_floor_caps_extreme(self):
        """ATR/P=25% case: tier=extreme, but cannot exceed STOP_HARD_FLOOR (=20%)."""
        # Even with an extreme tier giving 15%, we never go below STOP_HARD_FLOOR.
        # If we ever raised STOP_LOSS_EXTREME_VOL above STOP_HARD_FLOOR, this test
        # would catch the regression.
        entry = 10.0
        atr = entry * 0.25
        r = calculate_stop(entry, atr, 100_000)
        assert r.stop_distance_pct <= STOP_HARD_FLOOR

    def test_risk_parity_invariant_across_tiers(self):
        """Dollar risk at stop must equal equity * RISK_PER_TRADE_PCT regardless of vol."""
        equity = 100_000.0
        target_risk = equity * RISK_PER_TRADE_PCT     # 1000 TL
        for atr_ratio in (0.015, 0.030, 0.050, 0.070):
            entry = 100.0
            atr = entry * atr_ratio
            r = calculate_stop(entry, atr, equity)
            actual_risk = r.risk_parity_size * r.stop_distance_pct
            assert abs(actual_risk - target_risk) < 1.0, (
                f"atr_ratio={atr_ratio}: risk {actual_risk:.0f} != target {target_risk:.0f}"
            )

    def test_stop_price_below_entry(self):
        r = calculate_stop(100.0, 3.0, 100_000)
        assert r.stop_price < r.entry_price

    def test_negative_entry_raises(self):
        with pytest.raises(ValueError):
            calculate_stop(-10.0, 1.0)

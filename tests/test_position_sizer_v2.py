"""Tests for conviction-based position sizing (SPEC_POSITION_SIZING_2, D-052)."""
import pytest

from src.risk.position_sizer_v2 import (
    ACTION_BLOCKED,
    ACTION_ENTER,
    ACTION_EXIT,
    ACTION_HOLD,
    ACTION_WATCH,
    ACTION_WATCHLIST,
    TIER_MEDIUM,
    TIER_SELL,
    TIER_STRONG,
    TIER_WEAK,
    apply_adv_cap,
    classify_sizing_tier,
    size_position,
)
from src.signals.thresholds import (
    MAX_DRAWDOWN_HARD_STOP,
    POSITION_MAX_ADV_PCT,
    POSITION_SIZE_MEDIUM,
    POSITION_SIZE_STRONG,
)

EQUITY = 100_000.0


class TestTierMapping:
    @pytest.mark.parametrize(
        "score,tier",
        [
            (0.90, TIER_STRONG),
            (0.68, TIER_STRONG),
            (0.60, TIER_MEDIUM),
            (0.55, TIER_MEDIUM),
            (0.50, TIER_WEAK),
            (0.45, TIER_WEAK),
            (0.40, "HOLD"),
            (0.34, TIER_SELL),
        ],
    )
    def test_classify(self, score, tier):
        assert classify_sizing_tier(score) == tier


class TestSizing:
    def test_strong_bull_full_size(self):
        d = size_position(0.80, 1.0, EQUITY)
        assert d.action == ACTION_ENTER
        assert d.conviction_tier == TIER_STRONG
        # 0.325 * 1.0 * 0.80
        assert d.allocation_pct == pytest.approx(POSITION_SIZE_STRONG * 0.80)
        assert d.position_size == pytest.approx(POSITION_SIZE_STRONG * 0.80 * EQUITY)

    def test_medium_neutral_scaled(self):
        d = size_position(0.60, 0.8, EQUITY)
        assert d.action == ACTION_ENTER
        assert d.conviction_tier == TIER_MEDIUM
        assert d.allocation_pct == pytest.approx(POSITION_SIZE_MEDIUM * 0.8 * 0.60)

    def test_bear_regime_blocks_entry(self):
        d = size_position(0.80, 0.0, EQUITY)
        assert d.action == ACTION_BLOCKED
        assert d.position_size == 0.0

    def test_weak_is_watch(self):
        d = size_position(0.50, 1.0, EQUITY)
        assert d.action == ACTION_WATCH
        assert d.allocation_pct == 0.0

    def test_collapse_is_exit(self):
        d = size_position(0.20, 1.0, EQUITY)
        assert d.action == ACTION_EXIT
        assert d.conviction_tier == TIER_SELL

    def test_hold_band(self):
        d = size_position(0.40, 1.0, EQUITY)
        assert d.action == ACTION_HOLD


class TestPositionLimits:
    def test_strong_cap_reached(self):
        d = size_position(0.80, 1.0, EQUITY, strong_positions_count=4)
        assert d.action == ACTION_WATCHLIST
        assert d.position_size == 0.0

    def test_medium_cap_reached(self):
        d = size_position(0.60, 1.0, EQUITY, medium_positions_count=2)
        assert d.action == ACTION_WATCHLIST

    def test_total_cap_reached(self):
        d = size_position(0.80, 1.0, EQUITY, total_positions_count=6)
        assert d.action == ACTION_WATCHLIST


class TestEdgeCases:
    def test_drawdown_hard_stop_blocks(self):
        d = size_position(
            0.80, 1.0, EQUITY, portfolio_drawdown=MAX_DRAWDOWN_HARD_STOP
        )
        assert d.action == ACTION_BLOCKED
        assert "drawdown" in d.reason

    def test_sector_cap_clips_allocation(self):
        # Sector already at 38%, cap 40% -> headroom 2% clips a larger entry.
        d = size_position(0.95, 1.0, EQUITY, sector_exposure_pct=0.38)
        assert d.action == ACTION_ENTER
        assert d.allocation_pct == pytest.approx(0.02)

    def test_sector_cap_full_watchlists(self):
        d = size_position(0.95, 1.0, EQUITY, sector_exposure_pct=0.40)
        assert d.action == ACTION_WATCHLIST


class TestADVCap:
    """D-145 / RR-014: ADV cap post-processing — 4 test."""

    def test_adv_cap_applies_when_position_exceeds(self, monkeypatch):
        """position_size > adv_cap → final position capped at adv_cap."""
        decision = size_position(0.80, 1.0, EQUITY)
        assert decision.position_size > 0

        # ADV = 100k TL → cap = 100k × 0.05 = 5k TL  (position ~26k → exceeds)
        monkeypatch.setattr(
            "src.risk.position_sizer_v2.fetch_adv",
            lambda *a, **kw: 100_000.0,
        )
        result = apply_adv_cap("AKBNK", decision)
        assert result.position_size == pytest.approx(5_000.0, rel=1e-3)
        assert "ADV cap" in result.reason

    def test_adv_cap_not_applied_when_position_within(self, monkeypatch):
        """position_size < adv_cap → original decision returned unchanged."""
        decision = size_position(0.80, 1.0, EQUITY)

        # ADV = 100M TL → cap = 5M TL (far above ~26k position → no clip)
        monkeypatch.setattr(
            "src.risk.position_sizer_v2.fetch_adv",
            lambda *a, **kw: 100_000_000.0,
        )
        result = apply_adv_cap("AKBNK", decision)
        assert result.position_size == pytest.approx(decision.position_size, rel=1e-3)

    def test_adv_fetch_fail_nonfatal(self, monkeypatch):
        """fetch_adv returns None → non-fatal, original decision unchanged."""
        decision = size_position(0.80, 1.0, EQUITY)

        monkeypatch.setattr(
            "src.risk.position_sizer_v2.fetch_adv",
            lambda *a, **kw: None,
        )
        result = apply_adv_cap("AKBNK", decision)
        assert result.position_size == pytest.approx(decision.position_size, rel=1e-3)

    def test_adv_cap_constant_value(self):
        """POSITION_MAX_ADV_PCT == 0.05 invariant (Almgren 2005, D-145)."""
        assert POSITION_MAX_ADV_PCT == pytest.approx(0.05)

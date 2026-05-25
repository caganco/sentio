"""Tests for transaction cost model + net EV check (D-146, RR-015).

Test coverage:
  TestRoundTripCost (3): HIGH_COST ticker, Tier A standard, unknown fallback
  TestNetEVCheck    (5): threshold pass/fail + §8.3 scenarios S1-S5
Total: 8 tests
"""
import pytest

from src.risk.position_sizer_v2 import (
    ACTION_ENTER,
    ACTION_NO_TRADE,
    net_expected_value_check,
    size_position,
)
from src.risk.transaction_cost import round_trip_cost_pct
from src.signals.thresholds import (
    BROKER_TIER,
    HIGH_COST_RT_PCT,
    HIGH_COST_TICKERS,
    MIN_NET_EXPECTED_VALUE_PCT,
    ROUND_TRIP_COST_PCT_DEFAULT,
)

EQUITY = 100_000.0
_TIER_A_COST = 0.0105   # Garanti BBVA Tier A (from transaction_cost._TIER_COSTS)


class TestRoundTripCost:
    """round_trip_cost_pct() priority logic."""

    def test_high_cost_ticker_enery(self):
        """ENERY ∈ HIGH_COST_TICKERS → HIGH_COST_RT_PCT returned (micro-cap override)."""
        assert "ENERY" in HIGH_COST_TICKERS
        assert round_trip_cost_pct("ENERY") == pytest.approx(HIGH_COST_RT_PCT)

    def test_standard_ticker_kchol_broker_tier(self):
        """KCHOL ∉ HIGH_COST_TICKERS → Tier A (Garanti default) cost returned."""
        assert "KCHOL" not in HIGH_COST_TICKERS
        assert BROKER_TIER == "A"
        assert round_trip_cost_pct("KCHOL") == pytest.approx(_TIER_A_COST)

    def test_unknown_ticker_unknown_tier_fallback(self):
        """Unknown ticker + unknown broker tier → ROUND_TRIP_COST_PCT_DEFAULT."""
        assert round_trip_cost_pct("XYZAN", "Z") == pytest.approx(ROUND_TRIP_COST_PCT_DEFAULT)


class TestNetEVCheck:
    """net_expected_value_check() — threshold gate + §8.3 scenario table."""

    def test_net_ev_above_threshold_tradeable(self):
        """net EV > MIN_NET_EXPECTED_VALUE_PCT → original ENTER decision returned."""
        decision = size_position(0.80, 1.0, EQUITY)
        assert decision.action == ACTION_ENTER

        # gross = 5%, cost = 1.05%, net = 3.95% >> 0.5%
        result, audit = net_expected_value_check("KCHOL", 0.05, decision)
        assert result.action == ACTION_ENTER
        assert result.position_size == pytest.approx(decision.position_size, rel=1e-4)
        assert audit["net_ev"] == pytest.approx(0.05 - _TIER_A_COST, rel=1e-4)

    def test_net_ev_below_threshold_no_trade(self):
        """net EV < MIN_NET_EXPECTED_VALUE_PCT → NO-TRADE, position_size=0."""
        decision = size_position(0.80, 1.0, EQUITY)

        # gross = 1.1%, cost = 1.05%, net = 0.05% < 0.5% → NO-TRADE
        result, audit = net_expected_value_check("KCHOL", 0.011, decision)
        assert result.action == ACTION_NO_TRADE
        assert result.position_size == 0.0
        assert "net EV" in result.reason
        assert audit["net_ev"] == pytest.approx(0.011 - _TIER_A_COST, rel=1e-4)

    def test_scenario_s1_strong_signal_liquid_tradeable(self):
        """§8.3 S1: KCHOL, gross=5%, Tier A, net=3.95% → ENTER."""
        decision = size_position(0.80, 1.0, EQUITY)
        result, audit = net_expected_value_check("KCHOL", 0.05, decision)
        assert result.action == ACTION_ENTER
        assert audit["net_ev"] > MIN_NET_EXPECTED_VALUE_PCT

    def test_scenario_s2_marginal_profitable_tradeable(self):
        """§8.3 S2: KCHOL, gross=1.6%, net=0.55% > 0.5% → ENTER."""
        decision = size_position(0.80, 1.0, EQUITY)
        result, audit = net_expected_value_check("KCHOL", 0.016, decision)
        assert result.action == ACTION_ENTER
        assert audit["net_ev"] == pytest.approx(0.016 - _TIER_A_COST, rel=1e-4)
        assert audit["net_ev"] > MIN_NET_EXPECTED_VALUE_PCT

    def test_scenario_s3_insufficient_liquid_no_trade(self):
        """§8.3 S3: KCHOL, gross=1.1%, net=0.05% < 0.5% → NO-TRADE."""
        decision = size_position(0.80, 1.0, EQUITY)
        result, _ = net_expected_value_check("KCHOL", 0.011, decision)
        assert result.action == ACTION_NO_TRADE
        assert result.position_size == 0.0

    def test_scenario_s4_high_cost_strong_tradeable(self):
        """§8.3 S4: ENERY, gross=5%, cost=1.3%, net=3.7% → ENTER."""
        decision = size_position(0.80, 1.0, EQUITY)
        result, audit = net_expected_value_check("ENERY", 0.05, decision)
        assert result.action == ACTION_ENTER
        assert audit["rt_cost"] == pytest.approx(HIGH_COST_RT_PCT)
        assert audit["net_ev"] > MIN_NET_EXPECTED_VALUE_PCT

    def test_scenario_s5_high_cost_insufficient_no_trade(self):
        """§8.3 S5: ENERY, gross=1.5%, cost=1.3%, net=0.2% < 0.5% → NO-TRADE."""
        decision = size_position(0.80, 1.0, EQUITY)
        result, audit = net_expected_value_check("ENERY", 0.015, decision)
        assert result.action == ACTION_NO_TRADE
        assert audit["rt_cost"] == pytest.approx(HIGH_COST_RT_PCT)
        assert audit["net_ev"] < MIN_NET_EXPECTED_VALUE_PCT

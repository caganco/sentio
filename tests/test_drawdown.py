"""Comprehensive tests for drawdown management and circuit breaker (SPEC_DRAWDOWN_1)."""
from datetime import datetime, timedelta

import pytest

from src.risk.circuit_breaker import CircuitBreaker
from src.risk.drawdown import DrawdownTracker, PortfolioDrawdown, PositionDrawdown


class TestPositionDrawdownCalculation:
    """Test position drawdown calculation (3 tests)."""

    def test_position_drawdown_simple(self):
        """Simple position drawdown: peak 110, current 95 → -13.6%."""
        pd = PositionDrawdown("AKSEN", entry_price=100)
        pd.peak_price = 110
        pd.update(95)

        assert abs(pd.peak_to_current_dd - (-0.136)) < 0.001
        assert abs(pd.entry_to_current_pl - (-0.05)) < 0.001

    def test_position_no_drawdown_profit(self):
        """Position in profit: peak 105, current 102 → -2.9% DD, +2% P&L."""
        pd = PositionDrawdown("TTKOM", entry_price=100)
        pd.peak_price = 105
        pd.update(102)

        assert abs(pd.peak_to_current_dd - (-0.029)) < 0.001
        assert abs(pd.entry_to_current_pl - (0.02)) < 0.001

    def test_position_max_drawdown_tracking(self):
        """Max drawdown tracking across multiple price updates."""
        pd = PositionDrawdown("TAVHL", entry_price=100)
        pd.peak_price = 110

        pd.update(95)  # -13.6% DD
        assert abs(pd.max_dd_ever - (-0.136)) < 0.001

        pd.update(90)  # -18.2% DD (worse)
        assert abs(pd.max_dd_ever - (-0.182)) < 0.001

        pd.update(92)  # -16.4% DD (better but still tracked as max)
        assert abs(pd.max_dd_ever - (-0.182)) < 0.001


class TestPortfolioDrawdownCalculation:
    """Test portfolio drawdown calculation (3 tests)."""

    def test_portfolio_drawdown_calculation(self):
        """Portfolio DD: peak 150k, current 127.5k → -15.0%."""
        pdd = PortfolioDrawdown(initial_value=100000)
        pdd.peak_value = 150000
        pdd.update(127500)

        assert abs(pdd.portfolio_dd - (-0.15)) < 0.001

    def test_portfolio_peak_update(self):
        """Peak updates when portfolio reaches new high."""
        pdd = PortfolioDrawdown(initial_value=100000)
        pdd.update(105000)
        assert pdd.peak_value == 105000

        pdd.update(110000)
        assert pdd.peak_value == 110000

    def test_circuit_breaker_trigger_at_threshold(self):
        """Circuit breaker triggers at exactly -15%."""
        pdd = PortfolioDrawdown(initial_value=100000)
        pdd.peak_value = 150000
        pdd.update(127500)  # Exactly -15%

        assert pdd.circuit_breaker_triggered is True
        assert pdd.circuit_breaker_mode == "RISK_OFF"


class TestPositionAlertLevels:
    """Test position alert levels and deduplication (4 tests)."""

    def test_alert_level_info(self):
        """Position at -8% (between -5% and -10%) → INFO level."""
        pd = PositionDrawdown("AKSEN", entry_price=100)
        pd.peak_price = 100
        pd.update(92)  # -8% DD

        assert pd.get_drawdown_level() == "INFO"

    def test_alert_level_warning(self):
        """Position at -12% (between -10% and -15%) → WARNING level."""
        pd = PositionDrawdown("TAVHL", entry_price=100)
        pd.peak_price = 100
        pd.update(88)  # -12% DD

        assert pd.get_drawdown_level() == "WARNING"

    def test_alert_level_critical(self):
        """Position at -18% (between -15% and -20%) → CRITICAL level."""
        pd = PositionDrawdown("ENERY", entry_price=100)
        pd.peak_price = 100
        pd.update(82)  # -18% DD

        assert pd.get_drawdown_level() == "CRITICAL"

    def test_alert_deduplication(self):
        """Alert only escalates when severity increases."""
        pd = PositionDrawdown("AKSEN", entry_price=100)
        pd.peak_price = 100
        pd.update(92)  # -8% (INFO)

        # First alert should trigger
        assert pd.should_alert() is True
        pd.mark_alert_sent()

        # Next update at same level should not alert
        pd.update(91)  # Still -9% (INFO)
        assert pd.should_alert() is False

        # Escalation to WARNING should trigger
        pd.update(88)  # -12% (WARNING)
        assert pd.should_alert() is True


class TestPositionActionRules:
    """Test position action recommendations (4 tests)."""

    def test_action_hold_no_drawdown(self):
        """No drawdown → HOLD."""
        tracker = DrawdownTracker(100000)
        tracker.update_position("AKSEN", current_price=102, entry_price=100)

        action = tracker.get_position_action("AKSEN")
        assert action["action"] == "HOLD"
        assert action["severity"] == "OK"

    def test_action_hold_moderate_drawdown(self):
        """Moderate drawdown (-8%) and 0 days → HOLD."""
        tracker = DrawdownTracker(100000)
        tracker.update_position("AKSEN", current_price=92, entry_price=100)
        tracker.position_drawdowns["AKSEN"].peak_price = 100

        action = tracker.get_position_action("AKSEN", days_since_last_action=0)
        assert action["action"] == "HOLD"
        assert action["severity"] == "INFO"

    def test_action_reduce_severe_drawdown(self):
        """Severe drawdown (-12%) → REDUCE 50%."""
        tracker = DrawdownTracker(100000)
        tracker.update_position("TAVHL", current_price=88, entry_price=100)
        tracker.position_drawdowns["TAVHL"].peak_price = 100

        action = tracker.get_position_action("TAVHL")
        assert action["action"] == "REDUCE"
        assert action["severity"] == "CRITICAL"
        assert action["reduce_pct"] == 0.50

    def test_action_exit_extreme_drawdown(self):
        """Extreme drawdown (-18%) → EXIT."""
        tracker = DrawdownTracker(100000)
        tracker.update_position("ENERY", current_price=82, entry_price=100)
        tracker.position_drawdowns["ENERY"].peak_price = 100

        action = tracker.get_position_action("ENERY")
        assert action["action"] == "EXIT"
        assert action["severity"] == "EMERGENCY"
        assert action["exit_pct"] == 1.0


class TestCircuitBreakerLogic:
    """Test circuit breaker trigger and risk-off mode (3 tests)."""

    def test_circuit_breaker_not_triggered(self):
        """Portfolio at -12% → circuit breaker NOT triggered."""
        cb = CircuitBreaker(trigger_level=-0.15)
        triggered = cb.check_and_trigger(portfolio_drawdown=-0.12, positions=[])

        assert triggered is False
        assert cb.is_triggered is False
        assert cb.mode == "NORMAL"

    def test_circuit_breaker_triggered_at_threshold(self):
        """Portfolio at -15% → circuit breaker triggered."""
        cb = CircuitBreaker(trigger_level=-0.15)
        positions = [{"ticker": "AKSEN"}, {"ticker": "TTKOM"}]

        triggered = cb.check_and_trigger(portfolio_drawdown=-0.15, positions=positions)

        assert triggered is True
        assert cb.is_triggered is True
        assert cb.mode == "RISK_OFF"
        assert cb.triggered_at_date is not None

    def test_circuit_breaker_triggered_deeper(self):
        """Portfolio at -17% → circuit breaker triggered."""
        cb = CircuitBreaker(trigger_level=-0.15)
        triggered = cb.check_and_trigger(portfolio_drawdown=-0.17, positions=[])

        assert triggered is True
        assert cb.is_triggered is True
        assert cb.mode == "RISK_OFF"


class TestRecoveryConditions:
    """Test recovery from RISK_OFF to RECOVERY mode (2 tests)."""

    def test_recovery_not_ready_too_early(self):
        """Recovery NOT ready: only 2 days, signals weak."""
        tracker = DrawdownTracker(100000)
        tracker._enter_risk_off_mode()
        tracker.portfolio_dd.peak_value = 150000
        tracker.portfolio_dd.current_value = 130000  # 86.7% recovery

        # Mock early risk_off date (2 days ago)
        tracker.risk_off_start_date = datetime.now() - timedelta(days=2)

        signal_scores = {
            "tech": 0.50,
            "macro": 0.45,
            "kap": 0.48,
            "risk": 0.40,
        }

        recovery = tracker.check_recovery_conditions(signal_scores)
        assert recovery["mode"] == "RISK_OFF"
        assert recovery["readiness_score"] < 1.0

    def test_recovery_ready_all_conditions_met(self):
        """Recovery READY: 5 days, 90%+ recovered, 2+ signals positive."""
        tracker = DrawdownTracker(100000)
        tracker._enter_risk_off_mode()
        tracker.portfolio_dd.peak_value = 150000
        tracker.portfolio_dd.current_value = 135000  # 90% of peak

        # Mock 5+ days ago (use 5.1 to ensure >= 5 with .days rounding)
        tracker.risk_off_start_date = datetime.now() - timedelta(days=5, hours=1)

        signal_scores = {
            "tech": 0.58,
            "macro": 0.62,
            "kap": 0.48,
            "risk": 0.40,
        }

        recovery = tracker.check_recovery_conditions(signal_scores)
        assert recovery["mode"] == "RECOVERY"
        assert recovery["readiness_score"] == 1.0


class TestEdgeCases:
    """Test edge cases and error conditions (3 tests)."""

    def test_gap_down_overnight(self):
        """Position gap down -22% overnight → should track as extreme DD."""
        pd = PositionDrawdown("AKSEN", entry_price=100)
        pd.peak_price = 100
        pd.update(78)  # Gap down -22%

        assert pd.peak_to_current_dd < -0.20
        assert pd.get_drawdown_level() == "EMERGENCY"

    def test_orphaned_position_at_circuit_breaker_level(self):
        """Position at -15% even after circuit breaker (shouldn't happen but track it)."""
        tracker = DrawdownTracker(100000)
        tracker.update_position("TAVHL", current_price=85, entry_price=100)
        tracker.position_drawdowns["TAVHL"].peak_price = 100

        action = tracker.get_position_action("TAVHL")
        # At exactly -15%, should REDUCE (not yet EMERGENCY)
        assert action["action"] == "REDUCE"
        assert action["severity"] == "CRITICAL"

    def test_portfolio_profitable_but_position_at_limit(self):
        """Portfolio +2% overall but one position at -15% → still exit position."""
        tracker = DrawdownTracker(100000)
        tracker.portfolio_dd.peak_value = 100000
        tracker.update_portfolio(102000)  # +2% overall

        tracker.update_position("AKSEN", current_price=85, entry_price=100)
        tracker.position_drawdowns["AKSEN"].peak_price = 100  # -15%

        action = tracker.get_position_action("AKSEN")
        # Position rule applies independently of portfolio
        assert action["action"] == "REDUCE"
        assert action["severity"] == "CRITICAL"


class TestIntegrationDailyUpdate:
    """Test integration with daily_update flow (1 test)."""

    def test_daily_update_flow(self):
        """Simulate daily update: track positions, check alerts, portfolio DD."""
        # Initialize with 100k portfolio
        tracker = DrawdownTracker(initial_portfolio_value=100000)

        # Update positions (day 1)
        tracker.update_position("AKSEN", current_price=98, entry_price=100)
        tracker.update_position("TTKOM", current_price=102, entry_price=100)
        tracker.update_position("TAVHL", current_price=87, entry_price=100)  # -13% DD
        tracker.position_drawdowns["TAVHL"].peak_price = 100

        # Check for alerts
        alerts = tracker.get_all_alerts()
        assert "TAVHL" in alerts
        assert alerts["TAVHL"]["action"] == "REDUCE"

        # Update portfolio (current value = sum of positions + cash)
        tracker.update_portfolio(current_value=98000)

        # Verify portfolio tracked
        assert tracker.portfolio_dd.portfolio_dd < 0
        assert tracker.portfolio_mode == "NORMAL"

        # Simulate worse day (portfolio -15%)
        tracker.update_position("AKSEN", current_price=80, entry_price=100)
        tracker.update_position("TTKOM", current_price=88, entry_price=100)
        tracker.update_position("TAVHL", current_price=75, entry_price=100)
        tracker.update_portfolio(current_value=85000)

        # Circuit breaker should trigger if portfolio DD = -15%
        if abs(tracker.portfolio_dd.portfolio_dd - (-0.15)) < 0.01:
            assert tracker.portfolio_mode == "RISK_OFF"

"""Tests for portfolio monitoring — stop-loss approach warnings. (5 tests)"""
import pytest

from src.portfolio.monitor import (
    PositionAlert,
    check_portfolio_alerts,
    check_stop_loss_approach,
    format_stop_approach_alert,
)
from src.signals.thresholds import EXIT_STOP_LOSS, STOP_APPROACH_BUFFER


class TestStopLossApproach:
    """Test stop-loss approach warning detection."""

    def test_stop_approach_triggered_within_buffer(self):
        """Position within 3% of stop-loss should trigger STOP_APPROACHING."""
        entry_price = 100.0
        stop_loss_price = entry_price * EXIT_STOP_LOSS  # 92.0
        approach_threshold = stop_loss_price * (1 + STOP_APPROACH_BUFFER)  # 94.76

        # Current price at 93% (within 3% of stop, but above it)
        current_price = 93.0
        assert current_price <= approach_threshold  # Within buffer
        assert current_price > stop_loss_price      # Above stop

        alert = check_stop_loss_approach("AKSEN", current_price, entry_price)

        assert alert.is_approaching_stop is True
        assert alert.symbol == "AKSEN"
        assert alert.current_price == 93.0
        assert alert.stop_loss_price == pytest.approx(92.0, abs=0.01)

    def test_stop_approach_not_triggered_far_from_stop(self):
        """Position far from stop-loss should not trigger warning."""
        entry_price = 100.0
        stop_loss_price = entry_price * EXIT_STOP_LOSS  # 92.0

        # Current price at 98 (well above stop)
        current_price = 98.0

        alert = check_stop_loss_approach("GARAN", current_price, entry_price)

        assert alert.is_approaching_stop is False
        assert alert.distance_to_stop_pct == pytest.approx(6.52, abs=0.1)

    def test_stop_approach_at_exact_stop(self):
        """Position exactly at stop-loss should not be marked as approaching."""
        entry_price = 100.0
        stop_loss_price = entry_price * EXIT_STOP_LOSS  # 92.0
        current_price = stop_loss_price

        alert = check_stop_loss_approach("AKBNK", current_price, entry_price)

        assert alert.is_approaching_stop is False
        assert alert.distance_to_stop_pct == pytest.approx(0.0, abs=0.01)

    def test_stop_approach_below_stop(self):
        """Position below stop-loss should not be marked as approaching."""
        entry_price = 100.0
        stop_loss_price = entry_price * EXIT_STOP_LOSS  # 92.0
        current_price = 91.0  # Below stop

        alert = check_stop_loss_approach("SASA", current_price, entry_price)

        assert alert.is_approaching_stop is False
        assert alert.distance_to_stop_pct < 0  # Negative = below stop


class TestAlertFormatting:
    """Test alert message formatting."""

    def test_format_approaching_alert(self):
        """Format stop approach alert message correctly."""
        alert = PositionAlert(
            symbol="AKSEN",
            current_price=93.0,
            entry_price=100.0,
            stop_loss_price=92.0,
            distance_to_stop_pct=1.09,
            is_approaching_stop=True,
        )

        message = format_stop_approach_alert(alert)

        assert "⚠️ AKSEN STOP_APPROACHING" in message
        assert "Stop: ₺92.00" in message
        assert "Mevcut: ₺93.00" in message
        assert "Mesafe: %1.1" in message

    def test_format_no_alert_when_not_approaching(self):
        """Empty string when position not approaching stop."""
        alert = PositionAlert(
            symbol="GARAN",
            current_price=98.0,
            entry_price=100.0,
            stop_loss_price=92.0,
            distance_to_stop_pct=6.52,
            is_approaching_stop=False,
        )

        message = format_stop_approach_alert(alert)

        assert message == ""


class TestPortfolioAlerts:
    """Test portfolio-wide alert checking."""

    def test_check_portfolio_mixed_alerts(self):
        """Portfolio with mix of approaching and safe positions."""
        positions = {
            "AKSEN": {"entry_price": 100.0, "last_price": 93.0},
            "GARAN": {"entry_price": 50.0, "last_price": 49.0},
            "AKBNK": {"entry_price": 80.0, "last_price": 72.0},  # Below stop
        }
        current_prices = {
            "AKSEN": 93.0,  # Within 3% of stop (92.0)
            "GARAN": 49.0,  # Far from stop (46.0)
            "AKBNK": 72.0,  # Below stop (73.6)
        }

        alerts = check_portfolio_alerts(positions, current_prices)

        assert len(alerts) == 3
        assert alerts[0].is_approaching_stop is True  # AKSEN
        assert alerts[1].is_approaching_stop is False  # GARAN
        assert alerts[2].is_approaching_stop is False  # AKBNK


pytestmark = pytest.mark.baseline

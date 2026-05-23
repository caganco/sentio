"""Drawdown tracking and management for positions and portfolio."""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class PositionDrawdown:
    """Track drawdown for a single position."""

    def __init__(self, ticker: str, entry_price: float):
        """
        Initialize position drawdown tracker.

        Args:
            ticker: Stock ticker (e.g., "AKSEN")
            entry_price: Entry price in TRY
        """
        self.ticker = ticker
        self.entry_price = entry_price
        self.peak_price = entry_price
        self.peak_date = datetime.now()
        self.current_price = entry_price

        self.peak_to_current_dd = 0.0
        self.entry_to_current_pl = 0.0
        self.max_dd_ever = 0.0
        self.last_dd_alert_level = None

    def update(self, current_price: float) -> "PositionDrawdown":
        """
        Update position with latest price.

        Args:
            current_price: Current price in TRY

        Returns:
            self for chaining
        """
        self.current_price = current_price

        if current_price > self.peak_price:
            self.peak_price = current_price
            self.peak_date = datetime.now()

        if self.peak_price > 0:
            self.peak_to_current_dd = -(self.peak_price - current_price) / self.peak_price
            self.entry_to_current_pl = (current_price - self.entry_price) / self.entry_price
            self.max_dd_ever = min(self.max_dd_ever, self.peak_to_current_dd)

        return self

    def get_drawdown_level(self) -> str:
        """
        Map drawdown to alert level.

        Returns:
            "OK", "INFO", "WARNING", "CRITICAL", "EMERGENCY"
        """
        dd = self.peak_to_current_dd
        if dd >= -0.05:
            return "OK"
        elif dd >= -0.10:
            return "INFO"
        elif dd >= -0.15:
            return "WARNING"
        elif dd >= -0.20:
            return "CRITICAL"
        else:
            return "EMERGENCY"

    def should_alert(self) -> bool:
        """
        Check if new alert should be triggered.

        Returns:
            True if drawdown level has escalated or is first alert
        """
        severity_order = ["OK", "INFO", "WARNING", "CRITICAL", "EMERGENCY"]
        current_level = self.get_drawdown_level()
        current_severity = severity_order.index(current_level)

        if self.last_dd_alert_level is None:
            return current_level != "OK"

        last_severity = severity_order.index(self.last_dd_alert_level)
        return current_severity > last_severity

    def mark_alert_sent(self) -> None:
        """Mark that alert has been sent for current level."""
        self.last_dd_alert_level = self.get_drawdown_level()


class PortfolioDrawdown:
    """Track overall portfolio drawdown."""

    def __init__(self, initial_value: float):
        """
        Initialize portfolio drawdown tracker.

        Args:
            initial_value: Initial portfolio value in TRY
        """
        self.initial_value = initial_value
        self.peak_value = initial_value
        self.peak_date = datetime.now()
        self.current_value = initial_value
        self.portfolio_dd = 0.0

        self.circuit_breaker_triggered = False
        self.circuit_breaker_trigger_date: datetime | None = None
        self.circuit_breaker_mode = "NORMAL"

    def update(self, current_value: float) -> "PortfolioDrawdown":
        """
        Update portfolio with latest value.

        Args:
            current_value: Current total portfolio value in TRY

        Returns:
            self for chaining
        """
        self.current_value = current_value

        if current_value > self.peak_value:
            self.peak_value = current_value
            self.peak_date = datetime.now()

        if self.peak_value > 0:
            self.portfolio_dd = -(self.peak_value - current_value) / self.peak_value

        # Check circuit breaker trigger
        if self.portfolio_dd <= -0.15:
            if not self.circuit_breaker_triggered:
                self.circuit_breaker_triggered = True
                self.circuit_breaker_trigger_date = datetime.now()
                self.circuit_breaker_mode = "RISK_OFF"
                logger.critical(
                    f"CIRCUIT BREAKER: Portfolio DD {self.portfolio_dd:.2%} <= -15%"
                )

        return self

    def get_recovery_pct(self, trough_value: float) -> float:
        """
        Calculate recovery percentage from trough.

        Args:
            trough_value: Lowest portfolio value during drawdown

        Returns:
            Recovery percentage (e.g., 0.05 for 5% recovered from trough)
        """
        if trough_value <= 0:
            return 0.0
        return (self.current_value - trough_value) / trough_value


class DrawdownTracker:
    """Central drawdown tracking for positions and portfolio."""

    def __init__(self, initial_portfolio_value: float):
        """
        Initialize drawdown tracker.

        Args:
            initial_portfolio_value: Initial portfolio value in TRY
        """
        self.portfolio_dd = PortfolioDrawdown(initial_portfolio_value)
        self.position_drawdowns: dict[str, PositionDrawdown] = {}
        self.portfolio_mode = "NORMAL"
        self.risk_off_start_date: datetime | None = None
        self.trough_value: float | None = None

    def update_position(self, ticker: str, current_price: float, entry_price: float | None = None) -> None:
        """
        Update or create position drawdown tracking.

        Args:
            ticker: Stock ticker
            current_price: Current price in TRY
            entry_price: Entry price (required if creating new position)
        """
        if ticker not in self.position_drawdowns:
            if entry_price is None:
                raise ValueError(f"entry_price required to create new position {ticker}")
            self.position_drawdowns[ticker] = PositionDrawdown(ticker, entry_price)

        self.position_drawdowns[ticker].update(current_price)

    def update_portfolio(self, current_value: float) -> None:
        """
        Update portfolio drawdown and check circuit breaker.

        Args:
            current_value: Current total portfolio value in TRY
        """
        was_triggered = self.portfolio_dd.circuit_breaker_triggered
        self.portfolio_dd.update(current_value)

        # Transition to RISK_OFF if circuit breaker just triggered
        if self.portfolio_dd.circuit_breaker_triggered and not was_triggered:
            self._enter_risk_off_mode()

    def _enter_risk_off_mode(self) -> None:
        """Handle transition to RISK_OFF mode."""
        self.portfolio_mode = "RISK_OFF"
        self.risk_off_start_date = datetime.now()
        self.trough_value = self.portfolio_dd.current_value
        logger.critical(f"Entered RISK_OFF mode at portfolio value {self.trough_value:.2f}")

    def get_position_action(self, ticker: str, days_since_last_action: int = 0) -> dict[str, Any]:
        """
        Get recommended action for a position based on drawdown.

        Args:
            ticker: Stock ticker
            days_since_last_action: Days since last action was taken

        Returns:
            Dict with action, reason, severity, and optional reduce_pct
        """
        if ticker not in self.position_drawdowns:
            return {"action": "NONE", "reason": "Position not tracked", "severity": "OK"}

        pd = self.position_drawdowns[ticker]
        dd = pd.peak_to_current_dd

        if dd >= -0.05:
            return {"action": "HOLD", "reason": "Position near entry or in profit", "severity": "OK"}

        elif dd >= -0.10:
            if days_since_last_action >= 2:
                return {
                    "action": "REDUCE",
                    "reason": "Drawdown persists beyond 2 days",
                    "severity": "WARNING",
                    "reduce_pct": 0.30,
                }
            else:
                return {
                    "action": "HOLD",
                    "reason": "Moderate drawdown, wait for recovery",
                    "severity": "INFO",
                }

        elif dd >= -0.15:
            return {
                "action": "REDUCE",
                "reason": "Severe drawdown, cut position size",
                "severity": "CRITICAL",
                "reduce_pct": 0.50,
            }

        elif dd >= -0.20:
            return {
                "action": "EXIT",
                "reason": "Extreme drawdown, exit full position",
                "severity": "EMERGENCY",
                "exit_pct": 1.0,
            }

        else:
            return {
                "action": "EXIT",
                "reason": "Catastrophic drawdown beyond -20%",
                "severity": "CRITICAL_FAILURE",
                "exit_pct": 1.0,
            }

    def get_all_alerts(self) -> dict[str, dict[str, Any]]:
        """
        Get all positions with new alerts.

        Returns:
            Dict mapping ticker → alert info (action, severity, etc.)
        """
        alerts = {}
        for ticker, pd in self.position_drawdowns.items():
            if pd.should_alert():
                action = self.get_position_action(ticker)
                alerts[ticker] = {
                    "drawdown": pd.peak_to_current_dd,
                    "level": pd.get_drawdown_level(),
                    **action,
                }
                pd.mark_alert_sent()

        return alerts

    def check_recovery_conditions(self, signal_scores: dict[str, float]) -> dict[str, Any]:
        """
        Check if portfolio can transition from RISK_OFF to RECOVERY.

        Args:
            signal_scores: Dict of signal scores {tech, macro, kap, risk}

        Returns:
            Dict with mode, conditions_met, readiness_score
        """
        if self.portfolio_mode != "RISK_OFF":
            return {"mode": self.portfolio_mode, "readiness_score": 1.0}

        conditions_met = {
            "price_recovery": False,
            "signal_reset": False,
            "minimum_duration": False,
            "confirmation_day": False,
        }

        # Condition A: Price recovery to 90% of peak
        recovery_90_level = self.portfolio_dd.peak_value * 0.90
        if self.portfolio_dd.current_value >= recovery_90_level:
            conditions_met["price_recovery"] = True

        # Condition B: Signal reset (2+ signals positive)
        if signal_scores:
            positive_signals = sum(1 for s in signal_scores.values() if s > 0.55)
            if positive_signals >= 2:
                conditions_met["signal_reset"] = True

        # Condition C: Minimum 5 days in RISK_OFF
        if self.risk_off_start_date:
            days_elapsed = (datetime.now() - self.risk_off_start_date).days
            if days_elapsed >= 5:
                conditions_met["minimum_duration"] = True

        # Condition D: Confirmation (all above 3 conditions met)
        first_three_met = (
            conditions_met["price_recovery"]
            and conditions_met["signal_reset"]
            and conditions_met["minimum_duration"]
        )
        if first_three_met:
            conditions_met["confirmation_day"] = True

        # Transition if all met
        if first_three_met:
            self.portfolio_mode = "RECOVERY"
            logger.warning("Transitioning from RISK_OFF to RECOVERY mode")

        readiness_score = sum(conditions_met.values()) / len(conditions_met)
        return {
            "mode": self.portfolio_mode,
            "conditions_met": conditions_met,
            "readiness_score": readiness_score,
        }

    def reset_after_recovery(self) -> None:
        """Reset drawdown trackers after recovery (return to NORMAL mode)."""
        self.portfolio_mode = "NORMAL"
        self.portfolio_dd.circuit_breaker_triggered = False
        self.portfolio_dd.circuit_breaker_trigger_date = None
        self.portfolio_dd.circuit_breaker_mode = "NORMAL"
        self.risk_off_start_date = None
        self.trough_value = None
        logger.info("Reset drawdown system to NORMAL mode")

"""Circuit breaker for portfolio-level risk control."""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Portfolio-level kill switch triggered at -15% drawdown."""

    def __init__(self, trigger_level: float = -0.15):
        """
        Initialize circuit breaker.

        Args:
            trigger_level: Drawdown threshold for trigger (default -15%)
        """
        self.trigger_level = trigger_level
        self.is_triggered = False
        self.triggered_at_date: datetime | None = None
        self.mode = "NORMAL"

    def check_and_trigger(
        self, portfolio_drawdown: float, positions: list[dict[str, Any]]
    ) -> bool:
        """
        Check if circuit breaker should trigger and execute risk-off if needed.

        Args:
            portfolio_drawdown: Current portfolio drawdown (e.g., -0.15)
            positions: List of open positions

        Returns:
            True if circuit breaker was just triggered in this call
        """
        if portfolio_drawdown <= self.trigger_level:
            if not self.is_triggered:
                self.is_triggered = True
                self.triggered_at_date = datetime.now()
                self.mode = "RISK_OFF"
                self._execute_risk_off(positions)
                return True

        return False

    def _execute_risk_off(self, positions: list[dict[str, Any]]) -> None:
        """
        Execute full risk-off sequence.

        Args:
            positions: List of open positions to exit
        """
        logger.critical(f"CIRCUIT BREAKER TRIGGERED at {self.triggered_at_date}")
        logger.critical(f"Executing risk-off sequence for {len(positions)} positions")

        for position in positions:
            ticker = position.get("ticker", "UNKNOWN")
            logger.critical(f"CB: Exit {ticker} @ market")

        logger.critical("CB: Move all proceeds to cash")
        logger.critical("CB: Halt new entries, tighten all stops")
        logger.critical("CB: Risk-off mode active, halt trading")

    def can_exit_risk_off(self, recovery_ready: bool) -> bool:
        """
        Check if circuit breaker allows exit from RISK_OFF.

        Args:
            recovery_ready: True if all recovery conditions met

        Returns:
            True if circuit breaker cleared and recovery mode can start
        """
        if recovery_ready:
            self.mode = "RECOVERY"
            logger.warning("Circuit breaker cleared, transitioning to RECOVERY mode")
            return True

        return False

    def reset(self) -> None:
        """Reset circuit breaker to normal state."""
        self.is_triggered = False
        self.triggered_at_date = None
        self.mode = "NORMAL"
        logger.info("Circuit breaker reset to NORMAL mode")

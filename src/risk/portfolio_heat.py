"""Portfolio heat tracking and rebalancing."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PortfolioHeat:
    """Track and manage portfolio heat (sum of position_size × stop_loss)."""

    def __init__(self, max_heat_pct: float = 0.10):
        """
        Initialize portfolio heat tracker.

        Args:
            max_heat_pct: Maximum allowed portfolio heat as decimal (0.10 = 10%)
        """
        self.max_heat = max_heat_pct
        self.positions: dict[str, dict[str, float]] = {}

    def add_position(
        self, ticker: str, size_pct: float, stop_loss_pct: float, conviction: str = "MEDIUM"
    ) -> None:
        """
        Add or update a position in heat tracking.

        Args:
            ticker: Stock ticker
            size_pct: Position size as decimal (0.04 = 4%)
            stop_loss_pct: Stop loss as decimal (0.05 = 5%)
            conviction: Conviction level for reference (HIGH/MEDIUM/LOW)
        """
        self.positions[ticker] = {
            "size": size_pct,
            "stop_loss": stop_loss_pct,
            "heat": size_pct * stop_loss_pct,
            "conviction": conviction,
        }
        logger.debug(f"Added {ticker}: size={size_pct:.2%}, stop={stop_loss_pct:.2%}, heat={size_pct*stop_loss_pct:.4f}")

    def remove_position(self, ticker: str) -> None:
        """Remove position from heat tracking."""
        if ticker in self.positions:
            del self.positions[ticker]
            logger.debug(f"Removed {ticker} from heat tracking")

    def get_current_heat(self) -> float:
        """Get total current heat as decimal."""
        return sum(pos["heat"] for pos in self.positions.values())

    def check_heat(self) -> dict[str, Any]:
        """
        Check current heat vs limit.

        Returns:
            Dict with current_heat, max_heat, status, positions_count
        """
        current_heat = self.get_current_heat()
        status = "OK"

        if current_heat > self.max_heat:
            status = "CRITICAL"
        elif current_heat > self.max_heat * 0.8:
            status = "WARNING"

        return {
            "current_heat_pct": current_heat * 100,
            "max_heat_pct": self.max_heat * 100,
            "positions_count": len(self.positions),
            "status": status,
            "exceeded": current_heat > self.max_heat,
        }

    def rebalance(self, action: str = "scale") -> dict[str, Any]:
        """
        Rebalance portfolio to meet heat limit.

        Args:
            action: "scale" (proportional), "exit_lowest" (lowest conviction), "exit_oldest" (first position)

        Returns:
            Dict with recommended_actions, new_heat, scale_factor
        """
        current_heat = self.get_current_heat()

        if current_heat <= self.max_heat:
            return {
                "status": "OK",
                "current_heat": current_heat,
                "actions": [],
            }

        actions = []
        scale_factor = self.max_heat / current_heat if current_heat > 0 else 1.0

        if action == "scale":
            # Proportional scaling
            for ticker in self.positions:
                old_size = self.positions[ticker]["size"]
                new_size = old_size * scale_factor
                actions.append(
                    {
                        "ticker": ticker,
                        "action": "SCALE",
                        "old_size_pct": old_size * 100,
                        "new_size_pct": new_size * 100,
                    }
                )

        elif action == "exit_lowest":
            # Sort by conviction (LOW, MEDIUM, HIGH) and exit the lowest
            sorted_positions = sorted(
                self.positions.items(),
                key=lambda x: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(x[1]["conviction"], 1),
            )
            if sorted_positions:
                ticker_to_exit = sorted_positions[0][0]
                size = self.positions[ticker_to_exit]["size"]
                actions.append(
                    {
                        "ticker": ticker_to_exit,
                        "action": "EXIT",
                        "conviction": self.positions[ticker_to_exit]["conviction"],
                        "size_pct": size * 100,
                    }
                )

        elif action == "exit_oldest":
            # Exit first position (oldest)
            if self.positions:
                ticker_to_exit = next(iter(self.positions))
                size = self.positions[ticker_to_exit]["size"]
                actions.append(
                    {
                        "ticker": ticker_to_exit,
                        "action": "EXIT",
                        "size_pct": size * 100,
                    }
                )

        return {
            "status": "REBALANCE_NEEDED",
            "current_heat_pct": current_heat * 100,
            "max_heat_pct": self.max_heat * 100,
            "scale_factor": scale_factor,
            "actions": actions,
        }

    def get_position_summary(self) -> list[dict[str, Any]]:
        """Get summary of all positions."""
        return [
            {
                "ticker": ticker,
                "size_pct": pos["size"] * 100,
                "stop_loss_pct": pos["stop_loss"] * 100,
                "heat_pct": pos["heat"] * 100,
                "conviction": pos["conviction"],
            }
            for ticker, pos in self.positions.items()
        ]

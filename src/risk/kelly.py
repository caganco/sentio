"""Kelly Criterion position sizing with conviction mapping."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class KellySizer:
    """Size positions using Kelly Criterion with signal-driven conviction."""

    def __init__(
        self,
        portfolio_value_pct: float = 100.0,
        kelly_fraction: float = 0.25,
        max_position_pct: float = 0.03,
        max_portfolio_heat_pct: float = 0.10,
    ):
        """
        Initialize Kelly position sizer.

        Args:
            portfolio_value_pct: Portfolio size reference (for normalization)
            kelly_fraction: Fractional Kelly multiplier (0.25 = conservative)
            max_position_pct: Maximum single position size (3% default)
            max_portfolio_heat_pct: Maximum portfolio heat (10% default)
        """
        self.portfolio_value_pct = portfolio_value_pct
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct

    def size_position(
        self,
        ticker: str,
        signal_data: dict[str, Any],
        current_positions: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        """
        Size a position based on signal conviction and Kelly Criterion.

        Args:
            ticker: Stock ticker (e.g., "AKSEN")
            signal_data: Signal data with overall_score, signals dict, stop_loss_pct
            current_positions: Existing positions (to check for losses)

        Returns:
            Dict with conviction, Kelly %, fractional size, recommendation
        """
        if current_positions is None:
            current_positions = {}

        # Get conviction level
        conviction = self._map_conviction(signal_data)

        # Derive win probability from conviction
        win_prob = self._conviction_to_win_rate(conviction)

        # Get reward/risk ratio (typically 1.0 for stop-loss defined)
        reward_risk = self._calculate_reward_risk(signal_data)

        # Calculate Kelly percentage
        kelly_pct = self._calculate_kelly(win_prob, reward_risk)

        # Apply fractional Kelly (conservative)
        fractional_kelly_pct = kelly_pct * self.kelly_fraction

        # Apply stress market adjustment if VIX elevated
        vix = signal_data.get("vix", 17)
        if vix > 25:
            fractional_kelly_pct *= 0.75  # 25% reduction in stress
            logger.debug(f"{ticker}: VIX={vix}, reduced Kelly to {fractional_kelly_pct:.2f}%")

        # Get current position info
        current_pos = current_positions.get(ticker, {})
        current_size_pct = current_pos.get("size", 0.0)
        current_pnl_pct = current_pos.get("pnl_pct", 0.0)

        # Apply position limits
        recommended_size_pct = min(fractional_kelly_pct / 100.0, self.max_position_pct)

        # Determine action
        action = self._determine_action(
            ticker,
            conviction,
            kelly_pct,
            recommended_size_pct,
            current_size_pct,
            current_pnl_pct,
        )

        # Skip sizing if no edge
        if kelly_pct <= 0:
            recommended_size_pct = 0
            action = "SKIP"

        return {
            "ticker": ticker,
            "conviction": conviction,
            "current_size_pct": current_size_pct,
            "recommended_size_pct": recommended_size_pct,
            "kelly_pct": kelly_pct,
            "kelly_fractional_pct": fractional_kelly_pct,
            "win_probability": win_prob,
            "reward_risk_ratio": reward_risk,
            "action": action,
        }

    def calculate_portfolio_heat(
        self, positions: dict[str, dict]
    ) -> dict[str, Any]:
        """
        Calculate total portfolio heat (sum of position size × stop loss).

        Args:
            positions: {
                "AKSEN": {"size": 0.04, "stop_loss": 0.05},
                ...
            }

        Returns:
            Dict with total heat, status, recommendation
        """
        total_heat_pct = 0.0

        for ticker, pos_data in positions.items():
            size = pos_data.get("size", 0.0)
            stop_loss = pos_data.get("stop_loss", 0.0)
            heat = size * stop_loss
            total_heat_pct += heat

        total_heat_pct *= 100  # Convert to percentage

        status = "OK"
        if total_heat_pct > self.max_portfolio_heat_pct * 100:
            status = "CRITICAL"
        elif total_heat_pct > self.max_portfolio_heat_pct * 100 * 0.8:
            status = "WARNING"

        recommendation = f"Portfolio heat {total_heat_pct:.2f}% "
        if status == "OK":
            recommendation += f"is well within limit of {self.max_portfolio_heat_pct*100:.1f}%"
        elif status == "WARNING":
            scale_factor = (self.max_portfolio_heat_pct * 100) / total_heat_pct
            recommendation += f"is approaching limit. Consider scaling positions to {scale_factor*100:.0f}%"
        else:
            scale_factor = (self.max_portfolio_heat_pct * 100) / total_heat_pct
            recommendation += (
                f"exceeds limit of {self.max_portfolio_heat_pct*100:.1f}%. "
                f"SCALE positions to {scale_factor*100:.0f}%"
            )

        return {
            "total_heat_pct": total_heat_pct,
            "max_heat_pct": self.max_portfolio_heat_pct * 100,
            "status": status,
            "recommendation": recommendation,
        }

    def _map_conviction(self, signal_data: dict[str, Any]) -> str:
        """Map signal score to conviction level (HIGH/MEDIUM/LOW)."""
        score = signal_data.get("overall_score", 0.5)
        distance = abs(score - 0.5)
        agreement = self._calculate_agreement(signal_data.get("signals", {}))
        macro_strength = signal_data.get("signals", {}).get("macro", {}).get("score", 0.5)

        # LOW: close to 0.5 or poor agreement
        if distance < 0.15 or agreement < 0.5:
            return "LOW"

        # HIGH: far from 0.5 AND strong macro AND high agreement
        if distance >= 0.30 and macro_strength >= 0.50 and agreement >= 0.75:
            return "HIGH"

        # MEDIUM: everything else
        return "MEDIUM"

    def _calculate_agreement(self, signals: dict[str, Any]) -> float:
        """Calculate signal agreement: ratio of bullish signals."""
        if not signals:
            return 0.5

        layers = [k for k in signals.keys() if k in ["tech", "macro", "kap", "risk"]]
        if not layers:
            return 0.5

        bullish = sum(1 for l in layers if signals[l].get("score", 0.5) > 0.5)
        return bullish / len(layers)

    def _conviction_to_win_rate(self, conviction: str) -> float:
        """Map conviction to win probability estimate."""
        return {
            "HIGH": 0.58,
            "MEDIUM": 0.52,
            "LOW": 0.50,
        }.get(conviction, 0.50)

    def _calculate_reward_risk(self, signal_data: dict[str, Any]) -> float:
        """Calculate reward/risk ratio (b in Kelly formula)."""
        # For stop-loss defined positions, typically b = 1.0
        # Could be enhanced later with actual target/stop ratio
        return 1.0

    def _calculate_kelly(self, win_prob: float, reward_risk: float) -> float:
        """
        Calculate Kelly percentage.

        Formula: K = (p × b - q) / b
        where p = win_prob, q = 1-p, b = reward_risk
        """
        loss_prob = 1.0 - win_prob
        kelly = (win_prob * reward_risk - loss_prob) / reward_risk
        return max(0, kelly * 100)  # Return as percentage, minimum 0

    def _determine_action(
        self,
        ticker: str,
        conviction: str,
        kelly_pct: float,
        recommended_size_pct: float,
        current_size_pct: float,
        current_pnl_pct: float,
    ) -> str:
        """Determine sizing action (HOLD, ADD, REDUCE, SCALE, SKIP, EXIT)."""
        # Skip if no edge
        if kelly_pct <= 0:
            return "SKIP"

        # Skip if position is losing and new recommendation is to add
        if current_pnl_pct < -3.0 and recommended_size_pct > current_size_pct:
            return "HOLD"

        # If currently in position
        if current_size_pct > 0:
            if recommended_size_pct > current_size_pct + 0.001:
                return "ADD"
            elif recommended_size_pct < current_size_pct - 0.001:
                return "REDUCE"
            else:
                return "HOLD"
        else:
            # New position
            if recommended_size_pct >= 0.005:  # Min 0.5%
                return "ADD"
            else:
                return "SKIP"

"""Portfolio monitoring — position alerts, stop-loss approach warnings."""
from __future__ import annotations

from dataclasses import dataclass

from src.signals.thresholds import EXIT_STOP_LOSS, STOP_APPROACH_BUFFER


@dataclass
class PositionAlert:
    """Alert for a single position."""

    symbol: str
    current_price: float
    entry_price: float
    stop_loss_price: float
    distance_to_stop_pct: float  # Positive: above stop, Negative: below stop
    is_approaching_stop: bool


def check_stop_loss_approach(
    symbol: str,
    current_price: float,
    entry_price: float,
) -> PositionAlert:
    """Check if position is approaching stop-loss.

    Stop-loss is at entry_price * EXIT_STOP_LOSS (0.92 = -8%).
    Warning triggers when price is within STOP_APPROACH_BUFFER (3%) of stop.

    Example:
    - entry_price = 100.0
    - stop_loss_price = 92.0
    - current_price = 94.8 → within 3% of stop (94.8 <= 92.0 * 1.03)
    - distance_to_stop_pct = ((94.8 - 92.0) / 92.0) * 100 = 3.0%
    - is_approaching_stop = True
    """
    stop_loss_price = entry_price * EXIT_STOP_LOSS

    if current_price <= 0 or entry_price <= 0:
        return PositionAlert(
            symbol=symbol,
            current_price=current_price,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            distance_to_stop_pct=0.0,
            is_approaching_stop=False,
        )

    # Calculate % distance from current price to stop-loss
    distance_to_stop_pct = ((current_price - stop_loss_price) / stop_loss_price) * 100

    # Trigger alert if within STOP_APPROACH_BUFFER of stop
    approach_threshold = stop_loss_price * (1 + STOP_APPROACH_BUFFER)
    is_approaching = current_price <= approach_threshold and current_price > stop_loss_price

    return PositionAlert(
        symbol=symbol,
        current_price=current_price,
        entry_price=entry_price,
        stop_loss_price=stop_loss_price,
        distance_to_stop_pct=distance_to_stop_pct,
        is_approaching_stop=is_approaching,
    )


def format_stop_approach_alert(alert: PositionAlert) -> str:
    """Format alert message for reporting.

    Format: "⚠️ SYMBOL STOP_APPROACHING — Stop: ₺X.XX, Mevcut: ₺Y.YY, Mesafe: %Z.Z"
    """
    if not alert.is_approaching_stop:
        return ""

    return (
        f"⚠️ {alert.symbol} STOP_APPROACHING — "
        f"Stop: ₺{alert.stop_loss_price:.2f}, "
        f"Mevcut: ₺{alert.current_price:.2f}, "
        f"Mesafe: %{alert.distance_to_stop_pct:.1f}"
    )


def check_portfolio_alerts(
    positions: dict[str, dict],
    current_prices: dict[str, float],
) -> list[PositionAlert]:
    """Check all positions for stop-loss approach warnings.

    Args:
        positions: {symbol: {entry_price, ...}, ...}
        current_prices: {symbol: price, ...}

    Returns:
        List of PositionAlert objects for all positions.
    """
    alerts = []
    for symbol, pos in positions.items():
        current_price = current_prices.get(symbol, pos.get("last_price", 0.0))
        alert = check_stop_loss_approach(
            symbol=symbol,
            current_price=current_price,
            entry_price=pos["entry_price"],
        )
        alerts.append(alert)
    return alerts

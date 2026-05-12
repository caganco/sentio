from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from src.analysis.technicals import get_indicator_snapshot
from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class PositionAlert:
    ticker: str
    alert_type: str   # "STOP_LOSS" | "PROFIT_TARGET" | "OVERSOLD" | "OVERBOUGHT"
    message: str
    severity: str     # "HIGH" | "MEDIUM" | "LOW"


@dataclass
class PositionAnalysis:
    ticker: str
    quantity: int
    avg_cost: float
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss_price: float
    profit_target_price: float
    rsi: Optional[float]
    ma20: Optional[float]
    ma50: Optional[float]
    alerts: list[PositionAlert] = field(default_factory=list)


def analyze_portfolio(
    all_data: dict[str, pd.DataFrame],
    stop_loss_pct: float = 0.08,
    profit_target_pct: float = 0.20,
    rsi_period: int = 14,
) -> list[PositionAnalysis]:
    """Analyze all portfolio positions against live price data."""
    config = load_config()
    positions = config.get("portfolio", {}).get("positions", [])

    results: list[PositionAnalysis] = []

    for pos in positions:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        avg_cost = pos["avg_cost"]

        df = all_data.get(ticker)
        if df is None or df.empty:
            logger.warning("No price data for portfolio ticker %s", ticker)
            continue

        current_price = float(df["Close"].iloc[-1])
        cost_basis = avg_cost * qty
        market_value = current_price * qty
        pnl = market_value - cost_basis
        pnl_pct = pnl / cost_basis * 100

        stop_loss_price = avg_cost * (1 - stop_loss_pct)
        profit_target_price = avg_cost * (1 + profit_target_pct)

        snap = get_indicator_snapshot(df, rsi_period=rsi_period, ma_periods=[20, 50])

        alerts: list[PositionAlert] = []

        # Stop-loss alert
        if current_price <= stop_loss_price:
            alerts.append(PositionAlert(
                ticker=ticker,
                alert_type="STOP_LOSS",
                message=f"Price {current_price:.2f} breached stop-loss {stop_loss_price:.2f} ({-stop_loss_pct*100:.0f}% from avg cost)",
                severity="HIGH",
            ))

        # Profit-target alert
        if current_price >= profit_target_price:
            alerts.append(PositionAlert(
                ticker=ticker,
                alert_type="PROFIT_TARGET",
                message=f"Price {current_price:.2f} reached profit target {profit_target_price:.2f} (+{profit_target_pct*100:.0f}% from avg cost)",
                severity="MEDIUM",
            ))

        # RSI-based alerts
        if snap["rsi"] is not None:
            if snap["rsi"] >= 75:
                alerts.append(PositionAlert(
                    ticker=ticker,
                    alert_type="OVERBOUGHT",
                    message=f"RSI {snap['rsi']} — consider trimming position",
                    severity="LOW",
                ))
            elif snap["rsi"] <= 30:
                alerts.append(PositionAlert(
                    ticker=ticker,
                    alert_type="OVERSOLD",
                    message=f"RSI {snap['rsi']} — potential accumulation opportunity",
                    severity="LOW",
                ))

        results.append(PositionAnalysis(
            ticker=ticker,
            quantity=qty,
            avg_cost=avg_cost,
            current_price=current_price,
            cost_basis=cost_basis,
            market_value=market_value,
            unrealized_pnl=pnl,
            unrealized_pnl_pct=pnl_pct,
            stop_loss_price=stop_loss_price,
            profit_target_price=profit_target_price,
            rsi=snap["rsi"],
            ma20=snap.get("ma20"),
            ma50=snap.get("ma50"),
            alerts=alerts,
        ))

    return results


def portfolio_summary(analyses: list[PositionAnalysis]) -> dict:
    """Aggregate totals and collect all alerts."""
    total_cost = sum(a.cost_basis for a in analyses)
    total_value = sum(a.market_value for a in analyses)
    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost * 100 if total_cost else 0

    all_alerts = [alert for a in analyses for alert in a.alerts]
    high_alerts = [al for al in all_alerts if al.severity == "HIGH"]

    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "position_count": len(analyses),
        "alerts": all_alerts,
        "high_alerts": high_alerts,
    }

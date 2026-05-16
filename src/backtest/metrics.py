"""Backtest metrics: win rate, Sharpe, alpha, max drawdown, sensitivity."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.backtest.engine import BacktestEngine

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.42  # Turkish risk-free rate = TCMB policy rate ~42% annual (2026)


def calculate_win_rate(trades: list[dict]) -> float:
    """Win rate over completed (SELL) trades. Returns 0.0 if no trades."""
    sell_trades = [t for t in trades if t.get("type") == "SELL"]
    if not sell_trades:
        return 0.0
    wins = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
    return wins / len(sell_trades)


def calculate_sharpe(
    equity_curve: list[float],
    rf_rate: float = RISK_FREE_RATE,
) -> float:
    """Sharpe ratio = (annual_return - rf) / annual_vol. Returns 0.0 if insufficient data."""
    if len(equity_curve) < 2:
        return 0.0
    arr = np.array(equity_curve, dtype=float)
    daily_returns = np.diff(arr) / arr[:-1]
    annual_vol = float(np.std(daily_returns)) * np.sqrt(252)
    if annual_vol == 0:
        return 0.0
    annual_return = (arr[-1] - arr[0]) / arr[0]
    return (annual_return - rf_rate) / annual_vol


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    """Max drawdown as negative fraction (e.g., -0.18 for -18%). Returns 0.0 if empty."""
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (val - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    return max_dd


def calculate_alpha(
    equity_curve: list[float],
    benchmark_series: pd.Series,
    initial_capital: float,
) -> dict[str, float]:
    """Alpha vs. benchmark (BIST100). Returns dict with system_return, benchmark_return, alpha."""
    if not equity_curve or benchmark_series.empty:
        return {"system_return": 0.0, "benchmark_return": 0.0, "alpha": 0.0}

    system_return = (equity_curve[-1] - initial_capital) / initial_capital

    bmark_start = float(benchmark_series.iloc[0])
    bmark_end = float(benchmark_series.iloc[-1])
    if bmark_start == 0:
        benchmark_return = 0.0
    else:
        benchmark_return = (bmark_end - bmark_start) / bmark_start

    return {
        "system_return": system_return,
        "benchmark_return": benchmark_return,
        "alpha": system_return - benchmark_return,
    }


def summarize(
    engine: "BacktestEngine",
    benchmark_series: Optional[pd.Series] = None,
) -> dict[str, Any]:
    """Aggregate all backtest metrics into a summary dict with pass/fail evaluation."""
    trades = engine.trades
    sell_trades = [t for t in trades if t.get("type") == "SELL"]

    win_rate = calculate_win_rate(trades)
    sharpe = calculate_sharpe(engine.equity_curve)
    max_dd = engine.max_dd

    wins = [t["pnl_pct"] for t in sell_trades if t.get("pnl", 0) > 0]
    losses = [abs(t["pnl_pct"]) for t in sell_trades if t.get("pnl", 0) < 0]
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    profit_factor = sum(wins) / sum(losses) if losses else 0.0

    total_commission = sum(t.get("commission", 0) for t in trades)
    system_return = (engine.portfolio_value - engine.initial_capital) / engine.initial_capital

    alpha_data = {"system_return": system_return, "benchmark_return": 0.0, "alpha": system_return}
    if benchmark_series is not None and not benchmark_series.empty:
        alpha_data = calculate_alpha(engine.equity_curve, benchmark_series, engine.initial_capital)

    circuit_breaker_triggers = sum(
        1 for d in engine.drawdown_curve if d <= -0.15
    )

    pass_fail = {
        "win_rate": f"{win_rate:.1%} {'PASS' if win_rate >= 0.52 else 'FAIL'} (threshold: >=52%)",
        "sharpe": f"{sharpe:.2f} {'PASS' if sharpe >= 1.0 else 'FAIL'} (threshold: >=1.0)",
        "max_drawdown": f"{max_dd:.1%} {'PASS' if max_dd >= -0.25 else 'FAIL'} (threshold: >=-25%)",
        "alpha": f"{alpha_data['alpha']:.1%} {'PASS' if alpha_data['alpha'] > 0 else 'FAIL'} (threshold: >0%)",
        "circuit_breaker": f"{circuit_breaker_triggers} triggers {'PASS' if circuit_breaker_triggers <= 2 else 'FAIL'} (threshold: <=2)",
    }
    overall_pass = all("PASS" in v for v in pass_fail.values())

    return {
        "period": f"{engine.start_date} to {engine.end_date}",
        "trading_days": len(engine.daily_dates),
        "initial_capital_tl": engine.initial_capital,
        "final_portfolio_tl": round(engine.portfolio_value, 2),
        "total_return_pct": round(system_return * 100, 2),
        "total_trades": len(engine.trades),
        "completed_trades": len(sell_trades),
        "win_rate_pct": round(win_rate * 100, 2),
        "avg_win_pct": round(avg_win * 100, 4),
        "avg_loss_pct": round(avg_loss * 100, 4),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "system_return_pct": round(alpha_data["system_return"] * 100, 2),
        "benchmark_return_pct": round(alpha_data["benchmark_return"] * 100, 2),
        "alpha_pct": round(alpha_data["alpha"] * 100, 2),
        "total_commission_tl": round(total_commission, 2),
        "circuit_breaker_trigger_days": circuit_breaker_triggers,
        "pass_fail_evaluation": pass_fail,
        "overall_status": "PASS -- System ready for live test" if overall_pass else "FAIL -- Refine before live",
    }


def run_kelly_sensitivity(
    price_data: dict,
    macro_ts: pd.DataFrame,
    benchmark_series: Optional[pd.Series],
    base_kwargs: dict,
    kelly_fractions: tuple = (0.1, 0.25, 0.5, 1.0),
) -> dict[str, Any]:
    """Run backtest with different Kelly fractions. Returns {fraction: metrics}."""
    from src.backtest.engine import BacktestEngine

    results: dict[str, Any] = {}
    for frac in kelly_fractions:
        kwargs = dict(base_kwargs)
        kwargs["kelly_fraction"] = frac
        eng = BacktestEngine(**kwargs)
        eng.run(price_data, macro_ts, benchmark_series)
        m = summarize(eng, benchmark_series)
        results[str(frac)] = {
            "kelly_fraction": frac,
            "final_portfolio_tl": m["final_portfolio_tl"],
            "total_return_pct": m["total_return_pct"],
            "max_drawdown_pct": m["max_drawdown_pct"],
            "sharpe_ratio": m["sharpe_ratio"],
            "win_rate_pct": m["win_rate_pct"],
            "overall_status": m["overall_status"],
        }
        logger.info(
            f"Kelly {frac}x: return={m['total_return_pct']:.1f}%, "
            f"max_dd={m['max_drawdown_pct']:.1f}%, sharpe={m['sharpe_ratio']:.2f}"
        )
    return results

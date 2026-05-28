"""Backtest metrics: win rate, Sharpe, alpha, max drawdown, sensitivity."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from src.backtest.validation_constants import (
    CALMAR_PASS_THRESHOLD,
    CALMAR_STRONG_THRESHOLD,
    IR_PASS_THRESHOLD,
    SHARPE_PASS_THRESHOLD,
    SHARPE_STRONG_THRESHOLD,
)

if TYPE_CHECKING:
    from src.backtest.engine import BacktestEngine

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.37  # Turkish risk-free rate = TCMB Mayis 2026 MPK — OS_STATE
TUFE_UNAVAILABLE: str = "TÜFE_UNAVAILABLE"


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
    """Period-adjusted Sharpe ratio. D-161: period mismatch duzeltildi.

    Formula: (excess_period / annual_vol) * sqrt(252 / holding_days)
    excess_period = total_return - rf_rate * (holding_days / 252)

    Onceki formul yillik RF ile donem getirisini karsilastiriyordu (hata).
    Returns 0.0 if insufficient data or zero volatility.
    """
    if len(equity_curve) < 2:
        return 0.0
    arr = np.array(equity_curve, dtype=float)
    daily_returns = np.diff(arr) / arr[:-1]
    annual_vol = float(np.std(daily_returns)) * np.sqrt(252)
    if annual_vol == 0:
        return 0.0
    holding_days = len(daily_returns)
    total_return = (arr[-1] - arr[0]) / arr[0]
    rf_period = rf_rate * (holding_days / 252)
    excess = total_return - rf_period
    return float((excess / annual_vol) * np.sqrt(252 / holding_days))


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


def calculate_ir(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> float:
    """Information Ratio = annualized(mean active return / std active return). D-161.

    active_return = portfolio_daily - benchmark_daily (per day).
    IR > IR_PASS_THRESHOLD (0.3) anlamli alpha olarak kabul edilir.
    Returns 0.0 if insufficient data or zero tracking error.
    """
    if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
        return 0.0
    n = min(len(portfolio_returns), len(benchmark_returns))
    active = np.array(portfolio_returns[:n]) - np.array(benchmark_returns[:n])
    std_active = float(np.std(active))
    if std_active == 0:
        return 0.0
    return float(np.mean(active) / std_active * np.sqrt(252))


def calculate_alpha(
    equity_curve: list[float],
    benchmark_series: pd.Series,
    initial_capital: float,
) -> dict[str, float]:
    """Alpha vs. benchmark (BIST100). Returns dict with system_return, benchmark_return, alpha."""
    if not equity_curve or benchmark_series.empty:
        return {"system_return": 0.0, "benchmark_return": 0.0, "alpha": 0.0}

    system_return = (equity_curve[-1] - initial_capital) / initial_capital

    valid = benchmark_series.dropna()
    if valid.empty:
        return {"system_return": system_return, "benchmark_return": float("nan"), "alpha": float("nan")}
    bmark_start = float(valid.iloc[0])
    bmark_end = float(valid.iloc[-1])
    if bmark_start == 0:
        benchmark_return = 0.0
    else:
        benchmark_return = (bmark_end - bmark_start) / bmark_start

    return {
        "system_return": system_return,
        "benchmark_return": benchmark_return,
        "alpha": system_return - benchmark_return,
    }


def calculate_real_returns(
    nominal_return: float,
    benchmark_return: float,
    tufe_series: pd.Series | None,
    start_date: str,
    end_date: str,
    holding_days: int,
) -> dict[str, float | str]:
    """Nominal getirileri TÜFE CPI ile deflate eder. D-169.

    Formula: real = (1 + nominal) / (1 + cumulative_inflation) - 1
    Fallback: None/bos seri veya NaN degerler → TUFE_UNAVAILABLE sentinel.

    Returns keys: real_return_pct, benchmark_real_return_pct, real_alpha_pct,
                  avg_annual_tufe_pct.
    """
    import math

    sentinel = TUFE_UNAVAILABLE
    _na = {
        "real_return_pct":           sentinel,
        "benchmark_real_return_pct": sentinel,
        "real_alpha_pct":            sentinel,
        "avg_annual_tufe_pct":       sentinel,
    }

    if tufe_series is None or tufe_series.empty:
        return _na
    try:
        t_start = float(tufe_series.asof(pd.Timestamp(start_date)))
        t_end   = float(tufe_series.asof(pd.Timestamp(end_date)))
        if math.isnan(t_start) or math.isnan(t_end) or t_start == 0:
            return _na

        cum_inf = t_end / t_start - 1.0
        real_ret = (1.0 + nominal_return) / (1.0 + cum_inf) - 1.0

        if math.isnan(benchmark_return):
            real_bench_pct: float | str = sentinel
            real_alpha_pct: float | str = sentinel
        else:
            real_bench_pct = round(float((1.0 + benchmark_return) / (1.0 + cum_inf) - 1.0) * 100, 2)
            real_alpha_pct = round(float(real_ret) * 100 - float(real_bench_pct), 2)

        ann_tufe = (1.0 + cum_inf) ** (252.0 / max(holding_days, 1)) - 1.0

        return {
            "real_return_pct":           round(real_ret * 100, 2),
            "benchmark_real_return_pct": real_bench_pct,
            "real_alpha_pct":            real_alpha_pct,
            "avg_annual_tufe_pct":       round(ann_tufe * 100, 2),
        }
    except Exception:
        return _na


def summarize(
    engine: "BacktestEngine",
    benchmark_series: pd.Series | None = None,
    tufe_series: pd.Series | None = None,
) -> dict[str, Any]:
    """Aggregate all backtest metrics into a summary dict with pass/fail evaluation."""
    trades = engine.trades
    sell_trades = [t for t in trades if t.get("type") == "SELL"]

    win_rate = calculate_win_rate(trades)
    sharpe = calculate_sharpe(engine.equity_curve)

    # IR hesabi: benchmark ile gunluk hizalanmis aktif getiri (D-161)
    ir = 0.0
    if (
        benchmark_series is not None
        and not benchmark_series.empty
        and len(engine.daily_dates) >= 2
    ):
        dates = pd.DatetimeIndex(engine.daily_dates)
        bench_aligned = benchmark_series.reindex(dates, method="ffill").ffill()
        bench_daily = bench_aligned.pct_change().fillna(0)
        arr_eq = np.array(engine.equity_curve, dtype=float)
        port_daily = np.diff(arr_eq) / arr_eq[:-1]
        bench_vals = bench_daily.values[1:]  # pct_change ilk deger NaN -> [1:]
        min_len = min(len(port_daily), len(bench_vals))
        if min_len >= 2:
            ir = calculate_ir(
                list(port_daily[:min_len]),
                list(bench_vals[:min_len]),
            )

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

    # D-168: Calmar = toplam_getiri / abs(max_dd); Turkiye borsasinda ana risk metrik.
    calmar: float | None = abs(system_return / max_dd) if max_dd < 0 else None

    pass_fail = {
        "win_rate": f"{win_rate:.1%} {'PASS' if win_rate >= 0.52 else 'FAIL'} (threshold: >=52%)",
        # D-168: Sharpe artik pass/fail kriteri degil — TRY RF=%37 nedeniyle yapisal negatif.
        "sharpe": f"{sharpe:.3f} INFO (Turkiye RF=%37 nedeniyle kriter disinda; calmar bakınız)",
        "calmar": (
            f"{calmar:.2f} "
            f"{'PASS' if calmar >= CALMAR_PASS_THRESHOLD else 'FAIL'} "
            f"(threshold: >={CALMAR_PASS_THRESHOLD:.1f}; strong: >={CALMAR_STRONG_THRESHOLD:.1f})"
            if calmar is not None else "N/A PASS (max_dd=0)"
        ),
        "ir": (
            f"{ir:.3f} "
            f"{'PASS' if ir >= IR_PASS_THRESHOLD else 'FAIL'} "
            f"(threshold: >={IR_PASS_THRESHOLD})"
        ),
        "max_drawdown": f"{max_dd:.1%} {'PASS' if max_dd >= -0.25 else 'FAIL'} (threshold: >=-25%)",
        "alpha": f"{alpha_data['alpha']:.1%} {'PASS' if alpha_data['alpha'] > 0 else 'FAIL'} (threshold: >0%)",
        "circuit_breaker": f"{circuit_breaker_triggers} triggers {'PASS' if circuit_breaker_triggers <= 2 else 'FAIL'} (threshold: <=2)",
    }
    # Sharpe kriter disinda — overall_pass hesabina dahil edilmez (D-168).
    overall_pass = all("PASS" in v for k, v in pass_fail.items() if k != "sharpe")

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
        "calmar_ratio": round(calmar, 3) if calmar is not None else None,
        "information_ratio": round(ir, 3),
        "system_return_pct": round(alpha_data["system_return"] * 100, 2),
        "benchmark_return_pct": round(alpha_data["benchmark_return"] * 100, 2),
        "alpha_pct": round(alpha_data["alpha"] * 100, 2),
        "total_commission_tl": round(total_commission, 2),
        "circuit_breaker_trigger_days": circuit_breaker_triggers,
        "pass_fail_evaluation": pass_fail,
        "overall_status": "PASS -- System ready for live test" if overall_pass else "FAIL -- Refine before live",
        # D-169: TÜFE-deflate reel getiriler (TÜFE_UNAVAILABLE if EVDS unavailable)
        **calculate_real_returns(
            nominal_return=system_return,
            benchmark_return=alpha_data["benchmark_return"],
            tufe_series=tufe_series,
            start_date=engine.start_date,
            end_date=engine.end_date,
            holding_days=len(engine.daily_dates),
        ),
    }


def run_kelly_sensitivity(
    price_data: dict,
    macro_ts: pd.DataFrame,
    benchmark_series: pd.Series | None,
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

"""Calculate real alpha: strategy return - BIST100 benchmark return."""
import sys
from pathlib import Path
import json
import yfinance as yf
import numpy as np
from datetime import datetime


def calculate_returns_and_alpha(
    start_date: str,
    end_date: str,
    strategy_metrics: dict,
) -> dict:
    """Calculate BIST100 benchmark return and real alpha.

    Args:
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"
        strategy_metrics: dict with 'initial_capital_tl', 'final_portfolio_tl', 'equity_curve'

    Returns:
        dict with benchmark_return, real_alpha, sharpe_strategy, sharpe_benchmark
    """
    # Download BIST100 data
    print(f"  Downloading BIST100 ({start_date} to {end_date})...")
    bist100_data = yf.download("XU100.IS", start=start_date, end=end_date, progress=False)

    if bist100_data.empty:
        print(f"  ERROR: Could not download BIST100 data")
        return None

    # Extract closing prices
    if isinstance(bist100_data.columns, pd.MultiIndex):
        bist100_data = bist100_data.droplevel(level=1, axis=1)

    close_prices = bist100_data["Close"]

    # Calculate BIST100 return
    start_price = close_prices.iloc[0]
    end_price = close_prices.iloc[-1]
    bist100_return = (end_price - start_price) / start_price

    # Calculate strategy return
    initial_capital = strategy_metrics["initial_capital_tl"]
    final_portfolio = strategy_metrics["final_portfolio_tl"]
    strategy_return = (final_portfolio - initial_capital) / initial_capital

    # Real alpha
    real_alpha = strategy_return - bist100_return

    # Calculate daily returns for Sharpe
    bist100_daily_returns = close_prices.pct_change().dropna()

    # Strategy daily returns from equity curve (if available)
    equity_curve = strategy_metrics.get("equity_curve", [])
    if equity_curve and len(equity_curve) > 1:
        equity_array = np.array(equity_curve)
        strategy_daily_returns = np.diff(equity_array) / equity_array[:-1]
    else:
        # Use pre-calculated Sharpe if available (from backtest engine)
        strategy_daily_returns = np.array([])

    # Sharpe ratios (assuming risk-free rate = 0 for simplicity)
    sharpe_benchmark = (
        np.mean(bist100_daily_returns) / np.std(bist100_daily_returns) * np.sqrt(252)
        if len(bist100_daily_returns) > 1 and np.std(bist100_daily_returns) > 0
        else 0.0
    )

    if len(strategy_daily_returns) > 1 and np.std(strategy_daily_returns) > 0:
        sharpe_strategy = (
            np.mean(strategy_daily_returns) / np.std(strategy_daily_returns) * np.sqrt(252)
        )
    else:
        # Use pre-calculated Sharpe from backtest engine if equity curve unavailable
        sharpe_strategy = strategy_metrics.get("sharpe_ratio", 0.0)

    return {
        "period": f"{start_date} to {end_date}",
        "bist100_start_price": round(float(start_price), 4),
        "bist100_end_price": round(float(end_price), 4),
        "bist100_return_pct": round(bist100_return * 100, 2),
        "strategy_return_pct": round(strategy_return * 100, 2),
        "real_alpha_pct": round(real_alpha * 100, 2),
        "sharpe_benchmark": round(sharpe_benchmark, 4),
        "sharpe_strategy": round(sharpe_strategy, 4),
        "sharpe_difference": round(sharpe_strategy - sharpe_benchmark, 4),
    }


def main():
    import pandas as pd

    # Load D-046 backtest metrics
    d046_summary_path = Path("reports/d046_backtest_gated/summary.json")
    if not d046_summary_path.exists():
        print(f"ERROR: {d046_summary_path} not found")
        sys.exit(1)

    with open(d046_summary_path, "r") as f:
        d046_metrics = json.load(f)

    print("\n" + "="*70)
    print("  D-048: REAL ALPHA CALCULATION")
    print("="*70 + "\n")

    # Period 1: Full backtest (2025-11-01 to 2026-05-31)
    print("Period 1: 2025-11-01 to 2026-05-31 (D-046 backtest window)")
    print("-" * 70)
    period1 = calculate_returns_and_alpha(
        "2025-11-01",
        "2026-05-31",
        {
            "initial_capital_tl": d046_metrics["initial_capital_tl"],
            "final_portfolio_tl": d046_metrics["final_portfolio_tl"],
            "equity_curve": d046_metrics.get("equity_curve", []),
            "sharpe_ratio": d046_metrics.get("sharpe_ratio", 0.0),
        }
    )

    if period1:
        for key, val in period1.items():
            print(f"  {key:30} {val}")

    # Period 2: Historical (2024-01-01 to 2026-05-31)
    print("\nPeriod 2: 2024-01-01 to 2026-05-31 (Historical context)")
    print("-" * 70)

    # For historical period, we need to estimate strategy return
    # Assuming same daily return profile as backtest period
    if period1 and d046_metrics.get("system_return_pct"):
        # Use backtest system return as proxy
        historical_estimate = {
            "period": "2024-01-01 to 2026-05-31 (estimated)",
            "note": "Strategy return estimated from backtest profile",
        }
        print("  (No historical strategy data; using backtest return as reference)")

        # Just get BIST100 return for comparison
        bist100_2024_2026 = yf.download("XU100.IS", start="2024-01-01", end="2026-05-31", progress=False)
        if not bist100_2024_2026.empty:
            if isinstance(bist100_2024_2026.columns, pd.MultiIndex):
                bist100_2024_2026 = bist100_2024_2026.droplevel(level=1, axis=1)

            close = bist100_2024_2026["Close"]
            bist_return_2024_2026 = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
            print(f"  BIST100 return (2024-2026): {bist_return_2024_2026*100:.2f}%")
            print(f"  Start price: {close.iloc[0]:.4f}")
            print(f"  End price: {close.iloc[-1]:.4f}")

    # Summary table
    print("\n" + "="*70)
    print("  SUMMARY TABLE")
    print("="*70)
    print(f"\n  Period: 2025-11-01 to 2026-05-31")
    if period1:
        print(f"    BIST100 return:        {period1['bist100_return_pct']:>8}%")
        print(f"    Strategy return:       {period1['strategy_return_pct']:>8}%")
        print(f"    REAL ALPHA:            {period1['real_alpha_pct']:>8}% [ALERT]")
        print(f"    ")
        print(f"    BIST100 Sharpe:        {period1['sharpe_benchmark']:>8.4f}")
        print(f"    Strategy Sharpe:       {period1['sharpe_strategy']:>8.4f}")
        print(f"    Sharpe difference:     {period1['sharpe_difference']:>8.4f}")

    print("\n" + "="*70 + "\n")

    # Save results
    output_path = Path("reports/D-048_REAL_ALPHA.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = {
        "period_2025_11_2026_05": period1,
        "metadata": {
            "strategy": "BIST Trading System (D-046 macro-gated backtest)",
            "benchmark": "BIST100 (XU100.IS)",
            "rf_rate": 0.0,
            "note": "Alpha = Strategy Return - BIST100 Return (no risk-free adjustment)",
        }
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {output_path}\n")


if __name__ == "__main__":
    import pandas as pd
    main()

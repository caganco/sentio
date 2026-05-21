"""Run two baseline backtests: Naive buy-and-hold and Tech-only composite."""
import json
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.data_loader import load_price_data, load_macro_series
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import summarize
from src.signals.layers.technical_layer import score_technical
from src.backtest.data_loader import build_technical_data

logger_setup = None
def setup_logger(name):
    import logging
    return logging.getLogger(name)

logger = setup_logger("run_baseline_backtests")


class NaiveBaseline:
    """Baseline A: Equal-weight buy-and-hold of 10 BIST tickers."""

    def __init__(self, tickers=None, start_date="2025-11-01", end_date="2026-05-31"):
        self.tickers = tickers or [
            "AKSEN", "ASELS", "TUPRS", "BIMAS", "FROTO",
            "KCHOL", "GARAN", "EREGL", "SISE", "AKBNK"
        ]
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = 120_000.0
        self.results = {}

    def run(self, price_data: dict[str, pd.DataFrame]) -> dict:
        """Buy equal weights on start_date, hold until end_date."""
        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)

        # Find first and last trading dates
        all_dates = set()
        for ticker in self.tickers:
            if ticker in price_data:
                all_dates.update(price_data[ticker].index.tolist())

        all_dates = sorted(all_dates)
        start_date_actual = next((d for d in all_dates if d >= start), None)
        end_date_actual = next((d for d in reversed(all_dates) if d <= end), None)

        if not start_date_actual or not end_date_actual:
            return {"error": "Insufficient data for baseline period"}

        # Entry: Equal weight on start date
        entry_prices = {}
        entry_value_per_ticker = self.initial_capital / len(self.tickers)
        shares = {}

        for ticker in self.tickers:
            if ticker in price_data:
                df = price_data[ticker]
                if start_date_actual in df.index:
                    entry_price = df.loc[start_date_actual, "Close"]
                else:
                    # Find next available date
                    available = df[df.index >= start_date_actual]
                    if len(available) > 0:
                        entry_price = available.iloc[0]["Close"]
                    else:
                        entry_price = None

                if entry_price:
                    entry_prices[ticker] = entry_price
                    shares[ticker] = entry_value_per_ticker / entry_price

        # Exit: Sell all on end date
        exit_prices = {}
        final_value = 0.0

        for ticker in self.tickers:
            if ticker in price_data and ticker in entry_prices:
                df = price_data[ticker]
                if end_date_actual in df.index:
                    exit_price = df.loc[end_date_actual, "Close"]
                else:
                    # Find last available date before end
                    available = df[df.index <= end_date_actual]
                    if len(available) > 0:
                        exit_price = available.iloc[-1]["Close"]
                    else:
                        exit_price = entry_prices[ticker]

                exit_prices[ticker] = exit_price
                final_value += shares[ticker] * exit_price

        # Calculate metrics
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # Calculate Sharpe: daily returns from closing prices
        daily_returns_list = []
        for ticker in self.tickers:
            if ticker in price_data:
                df = price_data[ticker]
                mask = (df.index >= start_date_actual) & (df.index <= end_date_actual)
                ticker_data = df[mask].copy()
                ticker_data["pct_change"] = ticker_data["Close"].pct_change()
                daily_returns_list.extend(ticker_data["pct_change"].dropna().values)

        if len(daily_returns_list) > 1:
            daily_returns = np.array(daily_returns_list) / len(self.tickers)
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "strategy": "Naive Buy-and-Hold (10 tickers)",
            "start_date": start_date_actual.strftime("%Y-%m-%d"),
            "end_date": end_date_actual.strftime("%Y-%m-%d"),
            "tickers": self.tickers,
            "initial_capital_tl": self.initial_capital,
            "final_portfolio_tl": final_value,
            "total_return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "entry_prices": {k: round(v, 2) for k, v in entry_prices.items()},
            "exit_prices": {k: round(v, 2) for k, v in exit_prices.items()},
            "shares": {k: round(v, 2) for k, v in shares.items()},
        }


class TechOnlyBacktest:
    """Baseline B: Backtest with Tech layer only (macro/risk/sentiment disabled)."""

    def __init__(self, start_date="2025-11-01", end_date="2026-05-31"):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = 120_000.0

    def run(self, price_data: dict[str, pd.DataFrame], macro_ts: pd.DataFrame) -> dict:
        """Run modified BacktestEngine with only tech composite (weight=1.0)."""
        from src.signals.layers.technical_layer import score_technical
        from src.signals.layers.risk_layer import score_risk

        # Use unmodified BacktestEngine but override _compute_composite
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            start_date=self.start_date,
            end_date=self.end_date,
            quiet_warnings=True,
        )

        # Monkey-patch to use tech-only composite
        original_compute = engine._compute_composite

        def tech_only_composite(technical_data: dict, macro_data: dict, symbol: str) -> tuple[float, float]:
            # Return tech score only (weight=1.0), with macro_score for audit trail
            try:
                tech_score = score_technical(technical_data).score
            except Exception:
                tech_score = 50.0
            try:
                macro_score = engine._global_macro_score(macro_data)
            except Exception:
                macro_score = 50.0
            # Tech-only: composite = tech_score * 1.0, no macro/risk weighting
            return (tech_score * 1.0, macro_score)

        engine._compute_composite = tech_only_composite
        engine.run(price_data, macro_ts)

        # Benchmark series
        benchmark_series = macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None
        metrics = summarize(engine, benchmark_series)

        return {
            "strategy": "Tech-only Composite (weight=1.0)",
            **metrics
        }


def main(start_date=None, end_date=None, test_name=None):
    if start_date is None:
        start_date = "2025-11-01"
    if end_date is None:
        end_date = "2026-05-31"
    if test_name is None:
        test_name = "BASELINE BACKTESTS"

    print(f"\n{'='*70}")
    print(f"  {test_name}")
    print(f"{'='*70}\n")

    # Load data
    print("  Loading BIST price data (58 tickers)...")
    from src.utils.config import load_config
    config = load_config()
    tickers = config.get("portfolio", {}).get("tickers", [])
    price_data = load_price_data(tickers, start_date, end_date)
    print(f"  Price data loaded: {len(price_data)}/{len(tickers)} tickers")

    print("  Loading macro data...")
    macro_ts = load_macro_series(start_date, end_date)
    print(f"  Macro data loaded: {len(macro_ts)} days\n")

    # Baseline A: Naive buy-and-hold
    print("  Running Baseline A: Naive buy-and-hold (10 tickers)...")
    print("  Tickers: AKSEN, ASELS, TUPRS, BIMAS, FROTO, KCHOL, GARAN, EREGL, SISE, AKBNK")
    naive = NaiveBaseline(start_date=start_date, end_date=end_date)
    baseline_a = naive.run(price_data)

    print(f"    Result: {baseline_a['total_return_pct']:+.2f}% return, Sharpe {baseline_a['sharpe_ratio']:.4f}\n")

    # Baseline B: Tech-only
    print("  Running Baseline B: Tech-only composite...")
    tech_only = TechOnlyBacktest(start_date=start_date, end_date=end_date)
    baseline_b = tech_only.run(price_data, macro_ts)

    print(f"    Result: {baseline_b['total_return_pct']:+.2f}% return, Sharpe {baseline_b['sharpe_ratio']:.4f}")
    print(f"    Trades: {baseline_b['total_trades']} total, {baseline_b['completed_trades']} closed, {baseline_b['win_rate_pct']:.1f}% win rate\n")

    # Load D-046 results for comparison
    print("  Loading D-046 macro-gated results...")
    d046_path = Path("reports/d046_backtest_gated/summary.json")
    if d046_path.exists():
        with open(d046_path) as f:
            d046_results = json.load(f)
        print(f"    Result: {d046_results['total_return_pct']:+.2f}% return, Sharpe {d046_results['sharpe_ratio']:.4f}")
        print(f"    Trades: {d046_results['total_trades']} total, {d046_results['completed_trades']} closed, {d046_results['win_rate_pct']:.1f}% win rate\n")
    else:
        d046_results = None
        print("    ERROR: D-046 results not found\n")

    # Save baseline results
    output_dir = Path("reports/d049_baselines")
    output_dir.mkdir(parents=True, exist_ok=True)

    baselines = {
        "baseline_a_naive": baseline_a,
        "baseline_b_tech_only": baseline_b,
    }

    with open(output_dir / "baselines.json", "w") as f:
        json.dump(baselines, f, indent=2)

    print(f"  Saved baseline results to {output_dir}/baselines.json\n")

    # Create comparison table
    print("="*70)
    print("  COMPARISON TABLE: NAIVE vs TECH-ONLY vs MACRO-GATED")
    print("="*70 + "\n")

    print(f"{'Strategy':<25} {'Return':>12} {'Sharpe':>10} {'Win Rate':>10} {'Trades':>8}")
    print("-"*70)
    print(f"{'Naive Buy-and-Hold':<25} {baseline_a['total_return_pct']:>11.2f}% {baseline_a['sharpe_ratio']:>9.4f} {'N/A':>10} {'1':>8}")
    print(f"{'Tech-only':<25} {baseline_b['total_return_pct']:>11.2f}% {baseline_b['sharpe_ratio']:>9.4f} {baseline_b['win_rate_pct']:>9.1f}% {baseline_b['completed_trades']:>8}")

    if d046_results:
        print(f"{'Macro-gated (D-046)':<25} {d046_results['total_return_pct']:>11.2f}% {d046_results['sharpe_ratio']:>9.4f} {d046_results['win_rate_pct']:>9.1f}% {d046_results['completed_trades']:>8}")

    print("\n" + "="*70)
    print("  ANALYSIS")
    print("="*70 + "\n")

    tech_return = baseline_b['total_return_pct']
    naive_return = baseline_a['total_return_pct']

    print(f"1. Naive vs Tech-only:")
    print(f"   Return delta: {tech_return - naive_return:+.2f}% (tech {'outperforms' if tech_return > naive_return else 'underperforms'} naive)")
    print(f"   Sharpe delta: {baseline_b['sharpe_ratio'] - baseline_a['sharpe_ratio']:+.4f}")

    if d046_results:
        d046_return = d046_results['total_return_pct']
        print(f"\n2. Macro-gated (D-046) vs Baselines:")
        print(f"   vs Naive: {d046_return - naive_return:+.2f}%")
        print(f"   vs Tech-only: {d046_return - tech_return:+.2f}%")
        print(f"\n3. Insights:")
        print(f"   - Naive baseline return: {naive_return:+.2f}%")
        print(f"   - Tech-only return: {tech_return:+.2f}% (signal quality: {'+' if tech_return > 0 else '-'} impact)")
        print(f"   - Macro gates impact: {d046_return - tech_return:+.2f}% vs tech-only")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    import sys
    start = sys.argv[1] if len(sys.argv) > 1 else None
    end = sys.argv[2] if len(sys.argv) > 2 else None
    name = sys.argv[3] if len(sys.argv) > 3 else None
    main(start_date=start, end_date=end, test_name=name)

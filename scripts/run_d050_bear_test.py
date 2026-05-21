"""D-050: Bear market test — Compare three strategies on negative BIST period."""
import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.data_loader import load_price_data, load_macro_series
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import summarize
from src.utils.config import load_config


class BearMarketTest:
    """Run three strategies on bearish BIST period (2024-08-01 to 2024-10-31)."""

    def __init__(self, start_date="2024-08-01", end_date="2024-10-31"):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = 120_000.0
        self.results = {}

    def run_all_strategies(self, price_data, macro_ts):
        """Run three backtest strategies on same period."""
        benchmark_series = macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None

        # Strategy 1: Naive buy-and-hold
        print("\n  Running Baseline A: Naive buy-and-hold...")
        naive_result = self._run_naive(price_data)
        self.results["naive"] = naive_result

        # Strategy 2: Tech-only
        print("  Running Baseline B: Tech-only composite...")
        tech_result = self._run_tech_only(price_data, macro_ts, benchmark_series)
        self.results["tech_only"] = tech_result

        # Strategy 3: Macro-gated
        print("  Running Baseline C: Macro-gated (standard D-046)...")
        macro_result = self._run_macro_gated(price_data, macro_ts, benchmark_series)
        self.results["macro_gated"] = macro_result

        return self.results

    def _run_naive(self, price_data):
        """Equal-weight buy-and-hold of 10 tickers."""
        tickers = ["AKSEN", "ASELS", "TUPRS", "BIMAS", "FROTO", "KCHOL", "GARAN", "EREGL", "SISE", "AKBNK"]
        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)

        all_dates = set()
        for ticker in tickers:
            if ticker in price_data:
                all_dates.update(price_data[ticker].index.tolist())

        all_dates = sorted(all_dates)
        start_date_actual = next((d for d in all_dates if d >= start), None)
        end_date_actual = next((d for d in reversed(all_dates) if d <= end), None)

        if not start_date_actual or not end_date_actual:
            return {"error": "Insufficient data"}

        entry_prices = {}
        entry_value_per_ticker = self.initial_capital / len(tickers)
        shares = {}

        for ticker in tickers:
            if ticker in price_data:
                df = price_data[ticker]
                if start_date_actual in df.index:
                    entry_price = df.loc[start_date_actual, "Close"]
                else:
                    available = df[df.index >= start_date_actual]
                    if len(available) > 0:
                        entry_price = available.iloc[0]["Close"]
                    else:
                        entry_price = None

                if entry_price:
                    entry_prices[ticker] = entry_price
                    shares[ticker] = entry_value_per_ticker / entry_price

        exit_prices = {}
        final_value = 0.0

        for ticker in tickers:
            if ticker in price_data and ticker in entry_prices:
                df = price_data[ticker]
                if end_date_actual in df.index:
                    exit_price = df.loc[end_date_actual, "Close"]
                else:
                    available = df[df.index <= end_date_actual]
                    if len(available) > 0:
                        exit_price = available.iloc[-1]["Close"]
                    else:
                        exit_price = entry_prices[ticker]

                exit_prices[ticker] = exit_price
                final_value += shares[ticker] * exit_price

        total_return = (final_value - self.initial_capital) / self.initial_capital

        # Calculate Sharpe
        daily_returns_list = []
        for ticker in tickers:
            if ticker in price_data:
                df = price_data[ticker]
                mask = (df.index >= start_date_actual) & (df.index <= end_date_actual)
                ticker_data = df[mask].copy()
                ticker_data["pct_change"] = ticker_data["Close"].pct_change()
                daily_returns_list.extend(ticker_data["pct_change"].dropna().values)

        if len(daily_returns_list) > 1:
            daily_returns = np.array(daily_returns_list) / len(tickers)
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "strategy": "Naive Buy-and-Hold",
            "return_pct": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 4),
            "total_trades": 1,
            "completed_trades": 1,
            "win_rate_pct": 0.0,
        }

    def _run_tech_only(self, price_data, macro_ts, benchmark_series):
        """Tech-only composite."""
        from src.signals.layers.technical_layer import score_technical

        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            start_date=self.start_date,
            end_date=self.end_date,
            quiet_warnings=True,
        )

        # Monkey-patch for tech-only
        def tech_only_composite(technical_data, macro_data, symbol):
            try:
                tech_score = score_technical(technical_data).score
            except Exception:
                tech_score = 50.0
            try:
                macro_score = engine._global_macro_score(macro_data)
            except Exception:
                macro_score = 50.0
            return (tech_score * 1.0, macro_score)

        engine._compute_composite = tech_only_composite
        engine.run(price_data, macro_ts)
        metrics = summarize(engine, benchmark_series)

        return {
            "strategy": "Tech-only Composite",
            "return_pct": metrics["total_return_pct"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "total_trades": metrics["total_trades"],
            "completed_trades": metrics["completed_trades"],
            "win_rate_pct": metrics["win_rate_pct"],
        }

    def _run_macro_gated(self, price_data, macro_ts, benchmark_series):
        """Standard macro-gated strategy (D-046 thresholds)."""
        engine = BacktestEngine(
            initial_capital=self.initial_capital,
            start_date=self.start_date,
            end_date=self.end_date,
            quiet_warnings=True,
        )

        engine.run(price_data, macro_ts)
        metrics = summarize(engine, benchmark_series)

        return {
            "strategy": "Macro-gated (D-046)",
            "return_pct": metrics["total_return_pct"],
            "sharpe_ratio": metrics["sharpe_ratio"],
            "total_trades": metrics["total_trades"],
            "completed_trades": metrics["completed_trades"],
            "win_rate_pct": metrics["win_rate_pct"],
        }


def main():
    print(f"\n{'='*70}")
    print("  D-050: BEAR MARKET TEST (2024-08-01 to 2024-10-31)")
    print(f"{'='*70}\n")

    start_date = "2024-08-01"
    end_date = "2024-10-31"

    print("  Loading BIST price data (58 tickers)...")
    config = load_config()
    tickers = config.get("portfolio", {}).get("tickers", [])
    price_data = load_price_data(tickers, start_date, end_date)
    print(f"  Price data loaded: {len(price_data)}/{len(tickers)} tickers")

    print("  Loading macro data...")
    macro_ts = load_macro_series(start_date, end_date)
    print(f"  Macro data loaded: {len(macro_ts)} days\n")

    # Run all three strategies
    tester = BearMarketTest(start_date=start_date, end_date=end_date)
    results = tester.run_all_strategies(price_data, macro_ts)

    # Print comparison
    print("\n" + "="*70)
    print("  BEAR MARKET COMPARISON TABLE")
    print("="*70 + "\n")

    print(f"{'Strategy':<25} {'Return':>12} {'Sharpe':>10} {'Win Rate':>10} {'Trades':>8}")
    print("-"*70)

    for key in ["naive", "tech_only", "macro_gated"]:
        r = results[key]
        print(f"{r['strategy']:<25} {r['return_pct']:>11.2f}% {r['sharpe_ratio']:>9.4f} {r['win_rate_pct']:>9.1f}% {r['completed_trades']:>8}")

    # Analysis
    print("\n" + "="*70)
    print("  KEY FINDINGS")
    print("="*70 + "\n")

    naive = results["naive"]["return_pct"]
    tech = results["tech_only"]["return_pct"]
    macro = results["macro_gated"]["return_pct"]

    print(f"1. Market Regime:")
    print(f"   BIST100 return (benchmark): -17.91%")
    print(f"   Period: Aug 1 - Oct 31, 2024 (Q3 bearish)")

    print(f"\n2. Strategy Performance:")
    print(f"   Naive B&H:      {naive:>7.2f}% (buy-and-hold in down market)")
    print(f"   Tech-only:      {tech:>7.2f}% (signal quality in bear market)")
    print(f"   Macro-gated:    {macro:>7.2f}% (drawdown protection test)")

    print(f"\n3. Macro Gates Effectiveness:")
    if macro > naive:
        improvement = macro - naive
        print(f"   [PASS] OUTPERFORMED naive by {improvement:.2f}%")
        print(f"   [PASS] Gates provided drawdown protection in bear market")
    elif macro == naive:
        print(f"   [NEUTRAL] MATCHED naive return at {macro:.2f}%")
        print(f"   [NEUTRAL] Gates did not add value but avoided extra damage")
    else:
        underperformance = naive - macro
        print(f"   [FAIL] UNDERPERFORMED naive by {underperformance:.2f}%")
        print(f"   [FAIL] Gates blocked profitable trades or added overhead")

    if tech > macro:
        print(f"\n4. Tech vs Macro gates:")
        print(f"   Tech-only beat macro-gated by {tech - macro:.2f}%")
    else:
        print(f"\n4. Tech vs Macro gates:")
        print(f"   Macro-gated beat tech-only by {macro - tech:.2f}%")

    # Save results
    output_dir = Path("reports/d050_bear_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "results.json", "w") as f:
        json.dump({
            "period": f"{start_date} to {end_date}",
            "benchmark_return_pct": -17.91,
            "results": results
        }, f, indent=2)

    print(f"\n  Results saved to {output_dir}/results.json")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()

"""CLI entry point for SPEC_BACKTEST_1 historical simulation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.data_loader import load_macro_series, load_price_data
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import run_kelly_sensitivity, summarize
from src.backtest.reporter import (
    save_equity_curve_png,
    save_sensitivity_json,
    save_summary_json,
    save_trades_csv,
)
from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger("run_backtest")


def main() -> None:
    parser = argparse.ArgumentParser(description="SPEC_BACKTEST_1 — BIST signal validation")
    parser.add_argument("--start", default="2025-11-01", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-05-31", help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument("--tickers", default=None, help="Comma-separated ticker subset (e.g., AKSEN,GARAN)")
    parser.add_argument("--kelly-sensitivity", action="store_true", help="Run 4x Kelly fraction comparison")
    parser.add_argument("--no-chart", action="store_true", help="Skip equity curve PNG generation")
    parser.add_argument("--verbose", action="store_true", help="Enable all log levels (disables quiet_warnings)")
    parser.add_argument("--output-dir", default="reports/backtest", help="Output directory")
    args = parser.parse_args()

    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    print(f"\n{'='*60}")
    print("  SPEC_BACKTEST_1 — BIST Trading System Validation")
    print(f"  Period: {args.start} to {args.end}")
    print(f"{'='*60}\n")

    # Load tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        config = load_config()
        tickers = config.get("portfolio", {}).get("tickers", [])
    print(f"  Tickers: {len(tickers)} loaded")

    # Download data
    print("  Downloading BIST price data...")
    price_data = load_price_data(tickers, args.start, args.end)
    print(f"  Price data: {len(price_data)}/{len(tickers)} tickers loaded")

    print("  Downloading macro data (USDTRY, VIX, Brent, SP500, BIST100)...")
    macro_ts = load_macro_series(args.start, args.end)
    print(f"  Macro data: {len(macro_ts)} days, {list(macro_ts.columns)}")

    # Benchmark series (XU100.IS)
    benchmark_series = macro_ts["BIST100"] if "BIST100" in macro_ts.columns else None

    if not price_data:
        print("\n  ERROR: No price data loaded. Check network connection or ticker list.")
        sys.exit(1)

    # Run main backtest
    print("\n  Running backtest simulation...")
    base_kwargs = {
        "start_date": args.start,
        "end_date": args.end,
        "quiet_warnings": not args.verbose,
    }
    engine = BacktestEngine(**base_kwargs)
    engine.run(price_data, macro_ts, benchmark_series)

    # Compute metrics
    metrics = summarize(engine, benchmark_series)

    # Save outputs
    print("\n  Saving results...")
    save_summary_json(metrics, args.output_dir)
    save_trades_csv(engine.trades, args.output_dir)
    engine.export_audit_trail_csv(f"{args.output_dir}/audit_trail.csv")
    if not args.no_chart:
        save_equity_curve_png(
            engine.equity_curve,
            engine.daily_dates,
            benchmark_series,
            engine.initial_capital,
            args.output_dir,
        )

    # Kelly sensitivity
    if args.kelly_sensitivity:
        print("\n  Running Kelly sensitivity analysis (4x fractions)...")
        sensitivity = run_kelly_sensitivity(
            price_data, macro_ts, benchmark_series, base_kwargs
        )
        save_sensitivity_json(sensitivity, args.output_dir)

    # Print pass/fail summary
    print(f"\n{'='*60}")
    print("  BACKTEST RESULTS — PASS/FAIL EVALUATION")
    print(f"{'='*60}")
    print(f"  Period  : {metrics['period']}")
    print(f"  Days    : {metrics['trading_days']}")
    print(f"  Trades  : {metrics['total_trades']} total ({metrics['completed_trades']} closed)")
    print(f"  Capital : {metrics['initial_capital_tl']:,.0f} TL -> {metrics['final_portfolio_tl']:,.0f} TL")
    print(f"  Return  : {metrics['total_return_pct']:+.2f}%  (system) vs {metrics['benchmark_return_pct']:+.2f}% (BIST100)")
    print(f"  Alpha   : {metrics['alpha_pct']:+.2f}%")
    print()
    for criterion, verdict in metrics["pass_fail_evaluation"].items():
        print(f"  {criterion:<22}: {verdict}")
    print()
    print(f"  {metrics['overall_status']}")
    print(f"{'='*60}\n")
    print(f"  Output  : {args.output_dir}/")
    print(f"    summary.json")
    print(f"    trades.csv")
    if not args.no_chart:
        print(f"    equity_curve.png")
    if args.kelly_sensitivity:
        print(f"    sensitivity_analysis.json")
    print()


if __name__ == "__main__":
    main()

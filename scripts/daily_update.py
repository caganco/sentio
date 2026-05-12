"""Main entry point for the daily BIST data update."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.momentum import scan_momentum_stocks
from src.analysis.portfolio import analyze_portfolio, portfolio_summary
from src.data.database import get_prices, initialize_db, sync_portfolio, upsert_prices
from src.data.fetcher import fetch_multiple_stocks, get_bist100_tickers
from src.reports.daily_report import generate_html_report, generate_markdown_report
from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger("daily_update")

SEP = "=" * 65
DASH = "-" * 65


def run_update(scan: bool = False, generate_report: bool = False) -> None:
    logger.info("=== BIST Daily Update Started ===")

    initialize_db()

    config = load_config()
    positions = config.get("portfolio", {}).get("positions", [])
    sync_portfolio(positions)

    tickers = get_bist100_tickers()
    logger.info("Fetching data for %d tickers...", len(tickers))

    lookback_days = config.get("data", {}).get("lookback_days", 365)
    period = _days_to_period(lookback_days)
    all_data = fetch_multiple_stocks(tickers, period=period)

    total_rows = 0
    for ticker, df in all_data.items():
        total_rows += upsert_prices(df, ticker)
    logger.info("Stored %d price rows across %d tickers", total_rows, len(all_data))

    # Load from DB so analysis always uses canonical data
    db_data = {t: get_prices(t) for t in all_data}

    # --- Portfolio analysis ---
    risk_cfg = config.get("risk", {})
    analyses = analyze_portfolio(
        db_data,
        stop_loss_pct=risk_cfg.get("stop_loss_pct", 0.08),
        profit_target_pct=risk_cfg.get("profit_target_pct", 0.20),
    )
    summary = portfolio_summary(analyses)
    _print_portfolio(analyses, summary)

    # --- Momentum scan ---
    momentum_df = None
    if scan:
        scanner_cfg = config.get("scanner", {})
        momentum_df = scan_momentum_stocks(
            db_data,
            vol_threshold=scanner_cfg.get("volume_threshold", 1.5),
            proximity_threshold=scanner_cfg.get("high_52w_proximity", 0.05),
            min_price=scanner_cfg.get("min_price", 1.0),
            top_n=scanner_cfg.get("top_n_results", 10),
        )
        _print_momentum(momentum_df)

    if generate_report:
        md_path = generate_markdown_report(analyses, momentum_df if scan else None)
        html_path = generate_html_report(analyses, momentum_df if scan else None)
        print(f"\nRaporlar olusturuldu:")
        print(f"  Markdown : {md_path}")
        print(f"  HTML     : {html_path}\n")

    logger.info("=== BIST Daily Update Complete ===")


# ── Printers ────────────────────────────────────────────────────────────────

def _print_portfolio(analyses, summary) -> None:
    print("\n" + SEP)
    print("  PORTFOLIO SNAPSHOT")
    print(SEP)
    print(f"  {'Ticker':<12} {'Qty':>5} {'Avg':>8} {'Last':>8} {'P&L%':>7} {'P&L TL':>10} {'RSI':>5} {'vs MA20':>8}")
    print(DASH)

    for a in analyses:
        sign = "+" if a.unrealized_pnl_pct >= 0 else ""
        rsi_str = f"{a.rsi:.0f}" if a.rsi is not None else "N/A"
        ma20_str = ""
        if a.ma20 is not None:
            diff = (a.current_price - a.ma20) / a.ma20 * 100
            ma20_str = f"{diff:+.1f}%"
        alert_flag = " (!)" if any(al.severity == "HIGH" for al in a.alerts) else ""
        print(
            f"  {a.ticker:<12} {a.quantity:>5} {a.avg_cost:>8.2f} {a.current_price:>8.2f} "
            f"{sign}{a.unrealized_pnl_pct:>5.1f}% {a.unrealized_pnl:>+10.0f} {rsi_str:>5} {ma20_str:>8}{alert_flag}"
        )

    print(DASH)
    s = summary
    sign = "+" if s["total_pnl_pct"] >= 0 else ""
    print(
        f"  {'TOPLAM':<12} {'':>5} {s['total_cost']:>8.0f} {s['total_value']:>8.0f} "
        f"{sign}{s['total_pnl_pct']:>5.1f}% {s['total_pnl']:>+10.0f}"
    )
    print(SEP)

    if summary["alerts"]:
        print("\n  ALERTS")
        print(DASH)
        for al in sorted(summary["alerts"], key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x.severity]):
            icon = "[!]" if al.severity == "HIGH" else "[~]" if al.severity == "MEDIUM" else "[-]"
            print(f"  {icon} {al.ticker}: {al.message}")
        print(DASH)


def _print_momentum(df) -> None:
    print("\n" + SEP)
    print("  MOMENTUM SCAN — TOP CANDIDATES")
    print(SEP)

    if df.empty:
        print("  No candidates found.")
        print(SEP)
        return

    print(f"  {'#':<3} {'Ticker':<12} {'Close':>8} {'Day%':>6} {'1M%':>6} {'VolSurge':>9} {'52w%':>6} {'RSI':>5} {'Score':>7}")
    print(DASH)

    for i, row in df.iterrows():
        vol = f"{row['vol_surge']:.1f}x" if row["vol_surge"] is not None else "N/A"
        prox = f"{row['proximity_52w_high_pct']:.1f}%" if row["proximity_52w_high_pct"] is not None else "N/A"
        ret1m = f"{row['ret_1m_pct']:+.1f}%" if row["ret_1m_pct"] is not None else "N/A"
        rsi = f"{row['rsi']:.0f}" if row["rsi"] is not None else "N/A"
        score = f"{row['momentum_score']:.4f}" if row["momentum_score"] is not None else "N/A"
        day = f"{row['daily_chg_pct']:+.1f}%"
        print(
            f"  {i+1:<3} {row['ticker']:<12} {row['close']:>8.2f} {day:>6} {ret1m:>6} "
            f"{vol:>9} {prox:>6} {rsi:>5} {score:>7}"
        )

    print(SEP + "\n")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _days_to_period(days: int) -> str:
    if days <= 30:
        return "1mo"
    elif days <= 90:
        return "3mo"
    elif days <= 180:
        return "6mo"
    elif days <= 365:
        return "1y"
    return "2y"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BIST Daily Update")
    parser.add_argument("--scan", action="store_true", help="Run momentum scanner")
    parser.add_argument("--generate-report", action="store_true", help="Generate daily report (Phase 3)")
    args = parser.parse_args()
    run_update(scan=args.scan, generate_report=args.generate_report)

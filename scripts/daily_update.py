"""Main entry point for the daily BIST data update."""
import argparse
import json
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.momentum import scan_momentum_stocks
from src.analysis.portfolio import analyze_portfolio, portfolio_summary
from src.data.database import get_prices, initialize_db, sync_portfolio, upsert_prices, get_sector, get_sector_context
from src.data.fetcher import fetch_all_bist_batch, fetch_multiple_stocks, get_bist100_tickers
from src.data.kap_scraper import fetch_kap_news
from src.data.macro import fetch_macro_data
from src.data.macro_feed import fetch_macro_snapshot, save_to_db, get_latest_snapshot
from src.data.macro_scheduler import run_daily_update as run_macro_update
from src.signals.local import LocalMacroCache, TCMBClient, BistForeignOwnershipClient
from src.signals.local.cds_fallback import CDSFallbackClient
from src.signals.macro_signals import generate_macro_signal, save_signal_json
from src.signals.macro_alignment import MacroAlignmentCalculator
from src.signals.strategist import StrategistAgent, StrategistError
from src.reports.daily_report import generate_html_report, generate_markdown_report
from src.risk.kelly import KellySizer
from src.signals.sentiment.sentiment_signal import SentimentSignal
from src.utils.config import load_config
from src.utils.logger import setup_logger
from src.utils.os_state_manager import OSStateManager

logger = setup_logger("daily_update")

SEP = "=" * 65
DASH = "-" * 65


def pre_filter_tickers(
    all_signals: list[dict],
    portfolio_tickers: set[str],
    max_results: int = 10,
) -> list[dict]:
    """
    Filter momentum scan results down to the most actionable candidates.

    Portfolio tickers are always included. Others must have momentum_score >= 60
    (normalised 0-100 scale) OR at least 2 of the trigger conditions below.

    Returns a list of dicts (same schema as scan rows) sorted by priority score,
    capped at max_results.
    """
    config = load_config()
    agent_cfg = config.get("agent", {}).get("analyst", {})
    min_score = agent_cfg.get("pre_filter_min_score", 60)
    use_filter = agent_cfg.get("pre_filter", True)

    if not use_filter:
        return all_signals[:max_results]

    scanner_cfg = config.get("scanner", {})
    rsi_buy_min = scanner_cfg.get("rsi_buy_min", 50)
    rsi_buy_max = scanner_cfg.get("rsi_buy_max", 65)
    rsi_overbought = scanner_cfg.get("rsi_overbought", 80)
    rsi_oversold = scanner_cfg.get("rsi_oversold", 35)
    vol_threshold = scanner_cfg.get("volume_surge_threshold", 1.5)

    flagged: list[tuple[float, dict]] = []

    for s in all_signals:
        ticker = s.get("ticker", "")
        score = s.get("momentum_score") or 0.0
        rsi = s.get("rsi")
        vol = s.get("vol_surge")
        prox = s.get("proximity_52w_high_pct")

        # Portfolio positions — always include
        if ticker in portfolio_tickers:
            flagged.append((200.0 + score, s))
            continue

        reasons = 0

        # Momentum score above threshold
        if score >= min_score:
            reasons += 1

        # RSI in buy zone or extreme
        if rsi is not None:
            if rsi_buy_min <= rsi <= rsi_buy_max:
                reasons += 1
            elif rsi > rsi_overbought:
                reasons += 1
            elif rsi < rsi_oversold:
                reasons += 1

        # Volume surge
        if vol is not None and vol > vol_threshold:
            reasons += 1

        # Near 52-week high (proximity_52w_high_pct is % below high, so <5 = near)
        if prox is not None and prox > -5:
            reasons += 1

        if reasons >= 2:
            priority = score + (reasons * 5)
            flagged.append((priority, s))

    flagged.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in flagged[:max_results]]


def run_update(scan: bool = False, generate_report: bool = False) -> None:
    logger.info("=== BIST Daily Update Started ===")

    initialize_db()

    # Pre-market: fetch local macro signals (TCMB, CDS, BIST foreign)
    logger.info("Fetching local macro signals...")
    cache = LocalMacroCache()
    # Load YAML fallback data if cache is empty
    cache.load_from_yaml_fallback()

    tcmb_client = TCMBClient(cache)
    cds_client = CDSFallbackClient(cache)  # Fallback: primary → iShares proxy → cache
    bist_client = BistForeignOwnershipClient(cache)

    tcmb_ok = tcmb_client.fetch_and_store()
    cds_ok = cds_client.fetch_and_store()
    bist_ok = bist_client.fetch_and_store()

    logger.info(
        "Daily macro fetch: TCMB=%s, CDS=%s, BIST=%s",
        tcmb_ok,
        cds_ok,
        bist_ok,
    )

    config = load_config()
    positions = config.get("portfolio", {}).get("positions", [])
    sync_portfolio(positions)

    tickers = get_bist100_tickers()
    logger.info("Fetching data for %d tickers (batch mode)...", len(tickers))

    lookback_days = config.get("data", {}).get("lookback_days", 365)
    period = _days_to_period(lookback_days)
    all_data = fetch_all_bist_batch(tickers, period=period)

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
    filtered_signals: list[dict] = []
    if scan:
        scanner_cfg = config.get("scanner", {})
        momentum_df = scan_momentum_stocks(
            db_data,
            vol_threshold=scanner_cfg.get("volume_threshold", 1.5),
            proximity_threshold=scanner_cfg.get("high_52w_proximity", 0.05),
            min_price=scanner_cfg.get("min_price", 1.0),
            top_n=len(all_data),  # get all, pre_filter will cap
        )
        _print_momentum(momentum_df)

        # Pre-filter: keep only actionable signals for the agent pipeline
        portfolio_tickers = set(positions) if isinstance(positions, dict) else {p["ticker"] for p in positions}
        all_signals_list = momentum_df.to_dict(orient="records") if momentum_df is not None and not momentum_df.empty else []
        filtered_signals = pre_filter_tickers(all_signals_list, portfolio_tickers)
        logger.info(
            "Pre-filter: %d/%d tickers flagged for agent pipeline",
            len(filtered_signals), len(all_signals_list),
        )

    if generate_report:
        # Build daily briefing JSON for the agent pipeline
        logger.info("Updating macro feed...")
        macro_snapshot = fetch_macro_snapshot()
        if not macro_snapshot.empty:
            save_to_db(macro_snapshot)
            logger.info(f"Macro feed updated: {len(macro_snapshot)} records")
        else:
            logger.warning("No macro snapshot data")

        logger.info("Fetching macro data (legacy)...")
        macro_data = fetch_macro_data()

        logger.info("Generating macro signal...")
        macro_signal = None
        try:
            macro_signal = generate_macro_signal()
            macro_signal_path = save_signal_json(macro_signal)
            logger.info(f"Macro signal saved: {macro_signal_path}")
        except Exception as e:
            logger.error(f"Failed to generate macro signal: {e}")

        # --- Macro Snapshot Display ---
        if macro_signal:
            print("\n" + SEP)
            print("  MACRO SNAPSHOT")
            print(SEP)
            print(f"  Regime: {macro_signal.regime}")
            print(f"  Environment Score: {macro_signal.macro_environment_score:+.3f} ([-1, +1])")
            print(f"  " + DASH)
            print(f"  {'Symbol':<12} {'Price':>12} {'Score':>8}")
            print(f"  {DASH}")
            symbols_scores = [
                ("USDTRY", macro_signal.symbols.get("USDTRY"), macro_signal.usdtry_score),
                ("BRENT", macro_signal.symbols.get("BRENT"), macro_signal.brent_score),
                ("VIX", macro_signal.symbols.get("VIX"), macro_signal.vix_score),
                ("BIST100", macro_signal.symbols.get("BIST100"), macro_signal.bist100_score),
            ]
            for symbol, price, score in symbols_scores:
                price_str = f"{price:.2f}" if price else "N/A"
                print(f"  {symbol:<12} {price_str:>12} {score:+7.3f}")
            print(SEP)

        md_path = generate_markdown_report(analyses, momentum_df if scan else None)
        html_path = generate_html_report(analyses, momentum_df if scan else None)
        print(f"\nRaporlar olusturuldu:")
        print(f"  Markdown : {md_path}")
        print(f"  HTML     : {html_path}")

        logger.info("Fetching KAP disclosures...")
        _pos_tickers = list(positions.keys()) if isinstance(positions, dict) else [p["ticker"] for p in positions]
        kap_news = fetch_kap_news(
            portfolio_tickers=_pos_tickers,
        )

        # Calculate macro alignment scores for portfolio positions
        calculator = MacroAlignmentCalculator()
        macro_state = {
            "brent": macro_data.get("brent") if macro_data else None,
            "usd_try": macro_data.get("usd_try") if macro_data else None,
            "vix": macro_data.get("vix") if macro_data else None,
            "cds": macro_data.get("cds") if macro_data else None,
        }

        # --- Sentiment batch for portfolio positions ---
        _pos_ticker_list = list(positions.keys()) if isinstance(positions, dict) else [p["ticker"] for p in positions]
        sentiment_scores: dict = {}
        try:
            _sentiment_signal = SentimentSignal()
            sentiment_scores = _sentiment_signal.batch_calculate(_pos_ticker_list, days=7)
            logger.info("Sentiment batch calculated for %d tickers", len(sentiment_scores))
        except Exception as e:
            logger.warning("Sentiment batch failed: %s", e)

        portfolio_data = []
        kelly_sizer = KellySizer(portfolio_value_pct=100.0, kelly_fraction=0.25)
        current_positions = {}

        for a in analyses:
            position = {
                "ticker": a.ticker,
                "sector": get_sector(a.ticker),
                "sector_context": get_sector_context(a.ticker),
                "quantity": a.quantity,
                "avg_cost": round(a.avg_cost, 2),
                "current_price": round(a.current_price, 2) if a.current_price is not None else None,
                "unrealized_pnl_pct": round(a.unrealized_pnl_pct, 2) if a.unrealized_pnl_pct is not None else None,
                "unrealized_pnl": round(a.unrealized_pnl, 2) if a.unrealized_pnl is not None else None,
                "rsi": round(a.rsi, 1) if a.rsi is not None else None,
                "ma20": round(a.ma20, 2) if a.ma20 is not None else None,
                "stop_loss": round(a.stop_loss_price, 2) if a.stop_loss_price is not None else None,
                "profit_target": round(a.profit_target_price, 2) if a.profit_target_price is not None else None,
                "alerts": [{"severity": al.severity, "message": al.message} for al in a.alerts],
            }

            # Add sentiment data if available
            if a.ticker in sentiment_scores:
                sent = sentiment_scores[a.ticker]
                position["sentiment"] = {
                    "score": sent.get("score"),
                    "normalized": sent.get("normalized"),
                    "confidence": sent.get("confidence"),
                    "bullish_count": sent.get("bullish_count", 0),
                    "bearish_count": sent.get("bearish_count", 0),
                    "article_count": sent.get("article_count", 0),
                    "source": sent.get("source"),
                }

            # Add macro alignment if all macro data available
            if all(macro_state.values()):
                alignment = calculator.calculate_alignment(a.ticker, macro_state)
                position["macro_alignment"] = {
                    "score": alignment["alignment_score"],
                    "direction": alignment["alignment_direction"],
                    "narrative": alignment["narrative"],
                }

            # Track current position for Kelly sizing
            if a.current_price is not None and a.current_price > 0:
                position_pct = (a.quantity * a.current_price) / summary["total_value"] if summary["total_value"] > 0 else 0
                current_positions[a.ticker] = {
                    "size": position_pct,
                    "pnl_pct": a.unrealized_pnl_pct if a.unrealized_pnl_pct is not None else 0,
                }

            portfolio_data.append(position)

        momentum_top5 = []
        momentum_top10 = []
        if momentum_df is not None and not momentum_df.empty:
            for _, row in momentum_df.head(5).iterrows():
                momentum_top5.append({
                    "ticker": row["ticker"],
                    "close": round(float(row["close"]), 2),
                    "daily_chg_pct": round(float(row["daily_chg_pct"]), 2) if row["daily_chg_pct"] is not None else None,
                    "ret_1m_pct": round(float(row["ret_1m_pct"]), 2) if row["ret_1m_pct"] is not None else None,
                    "vol_surge": round(float(row["vol_surge"]), 2) if row["vol_surge"] is not None else None,
                    "proximity_52w_high_pct": round(float(row["proximity_52w_high_pct"]), 2) if row["proximity_52w_high_pct"] is not None else None,
                    "rsi": round(float(row["rsi"]), 1) if row["rsi"] is not None else None,
                    "momentum_score": round(float(row["momentum_score"]), 4) if row["momentum_score"] is not None else None,
                })
            for _, row in momentum_df.head(10).iterrows():
                momentum_top10.append({
                    "ticker": row["ticker"],
                    "score": round(float(row["momentum_score"]), 4) if row["momentum_score"] is not None else None,
                    "rsi": round(float(row["rsi"]), 1) if row["rsi"] is not None else None,
                    "1m_pct": round(float(row["ret_1m_pct"]), 2) if row["ret_1m_pct"] is not None else None,
                    "vol_surge": round(float(row["vol_surge"]), 2) if row["vol_surge"] is not None else None,
                })

        all_alerts = summary.get("alerts", [])

        # Get CDS source (R=real/primary, P=proxy/estimated)
        cds_data = cds_client.get_latest_cds()
        cds_src = "R" if cds_data and cds_data.get("source", "").startswith("worldgovernmentbonds") else "P"

        # Build macro snapshot section
        macro_snapshot_section = {}
        if 'macro_signal' in locals() and macro_signal:
            macro_snapshot_section = {
                "timestamp": macro_signal.timestamp,
                "regime": macro_signal.regime,
                "macro_environment_score": round(macro_signal.macro_environment_score, 3),
                "components": {
                    "vix": round(macro_signal.vix_score, 3),
                    "usdtry": round(macro_signal.usdtry_score, 3),
                    "brent": round(macro_signal.brent_score, 3),
                    "bist100": round(macro_signal.bist100_score, 3),
                },
                "prices": {
                    "usdtry": macro_signal.symbols.get("USDTRY"),
                    "brent": macro_signal.symbols.get("BRENT"),
                    "vix": macro_signal.symbols.get("VIX"),
                    "bist100": macro_signal.symbols.get("BIST100"),
                },
                "data_date": macro_signal.data_date,
                "cds_src": cds_src,  # R=real (primary scraping), P=proxy (iShares estimated)
            }

        # Build portfolio-level sentiment summary
        sentiment_summary: dict = {}
        if sentiment_scores:
            bullish_tickers = [t for t, s in sentiment_scores.items() if s.get("score", 50) > 60]
            bearish_tickers = [t for t, s in sentiment_scores.items() if s.get("score", 50) < 40]
            avg_sentiment = (
                sum(s.get("score", 50) for s in sentiment_scores.values()) / len(sentiment_scores)
                if sentiment_scores else 50.0
            )
            sentiment_summary = {
                "avg_score": round(avg_sentiment, 1),
                "bullish_tickers": bullish_tickers,
                "bearish_tickers": bearish_tickers,
                "neutral_tickers": [
                    t for t in sentiment_scores
                    if t not in bullish_tickers and t not in bearish_tickers
                ],
                "total_tickers": len(sentiment_scores),
            }

        briefing = {
            "date": str(_date.today()),
            "bist100": 0,
            "risk_limits": {
                "max_sector_concentration": risk_cfg.get("max_sector_concentration", 0.30),
                "max_position_size": risk_cfg.get("max_position_size", 0.15),
            },
            "portfolio": portfolio_data,
            "momentum_top5": momentum_top5,
            "filtered_signals": filtered_signals,  # pre-filtered for agent pipeline
            "macro_data": macro_data,
            "macro_snapshot": macro_snapshot_section,
            "kap_news": kap_news,
            "sentiment_summary": sentiment_summary,
            "sector_performance": {},
            "alerts": [{"severity": al.severity, "ticker": al.ticker, "message": al.message} for al in all_alerts],
        }

        briefing_path = Path(__file__).parent.parent / "agents" / "intelligence" / "daily_briefing.json"
        briefing_path.parent.mkdir(parents=True, exist_ok=True)
        briefing_path.write_text(json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8")
        kap_src = kap_news.get("source_used", "none")
        kap_total = kap_news.get("total", 0)
        print(f"  Briefing  : {briefing_path}")
        print(f"  KAP News  : {kap_total} item(s) via {kap_src}\n")

        # --- Kelly Criterion Position Sizing ---
        kelly_sizing = {}
        vix_val = macro_data.get("vix") if isinstance(macro_data, dict) else None
        for a in analyses:
            try:
                # Build minimal signal data for Kelly sizing
                overall_score = (briefing["macro_snapshot"].get("macro_environment_score", 0) + 1) * 0.5
                signal_data = {
                    "overall_score": overall_score,
                    "signals": {
                        "tech": {"score": 0.5 + (a.rsi - 50) / 100 if a.rsi else 0.5, "weight": 0.20},
                        "macro": {"score": briefing["macro_snapshot"].get("macro_environment_score", 0) * 0.5 + 0.5, "weight": 0.333},
                        "kap": {"score": 0.5, "weight": 0.267},
                        "risk": {"score": 0.5, "weight": 0.067},
                    },
                    "stop_loss_pct": 0.05,
                    "vix": vix_val or 17,
                }
                kelly_result = kelly_sizer.size_position(a.ticker, signal_data, current_positions)
                kelly_sizing[a.ticker] = {
                    "conviction": kelly_result["conviction"],
                    "current_size_pct": round(kelly_result["current_size_pct"] * 100, 2),
                    "recommended_size_pct": round(kelly_result["recommended_size_pct"] * 100, 2),
                    "kelly_pct": round(kelly_result["kelly_pct"], 2),
                    "kelly_fractional_pct": round(kelly_result["kelly_fractional_pct"], 2),
                    "win_probability": round(kelly_result["win_probability"], 3),
                    "action": kelly_result["action"],
                }
            except Exception as e:
                logger.debug(f"Kelly sizing failed for {a.ticker}: {e}")
                kelly_sizing[a.ticker] = {"error": str(e)}

        # --- Strategist Agent ---
        strategist_notes = "(Strategist analysis unavailable)"
        _brent_price = macro_snapshot_section.get("prices", {}).get("brent") if macro_snapshot_section else None
        report_data_for_strategist = {
            "timestamp": briefing["date"],
            "macro_data": {
                "tcmb_decision": macro_data.get("tcmb_decision") if isinstance(macro_data, dict) else "N/A",
                "cds_bps": macro_data.get("cds_bps") if isinstance(macro_data, dict) else "N/A",
                "bist_foreign": macro_data.get("bist_foreign") if isinstance(macro_data, dict) else "N/A",
                "brent_usd": round(_brent_price, 2) if _brent_price is not None else "N/A",
            },
            "signals": {
                "rsi_5d": briefing["macro_snapshot"].get("components", {}).get("bist100", "N/A"),
                "ma_cross": "N/A",
                "breadth_score": briefing["macro_snapshot"].get("macro_environment_score", "N/A"),
                "volume_trend": "N/A",
            },
            "scores": {
                "overall_score": round(
                    (briefing["macro_snapshot"].get("macro_environment_score", 0) + 1) * 50, 1
                ) if briefing["macro_snapshot"] else "N/A",
                "sector_ratings": "N/A",
            },
            "portfolio_positions": portfolio_data,
            "momentum_top5": briefing.get("momentum_top5", []),
            "momentum_top10": momentum_top10,
            "kelly_sizing": kelly_sizing,
            "sentiment_scores": sentiment_scores,
            "sentiment_summary": sentiment_summary,
        }
        try:
            strategist = StrategistAgent(timeout=60)
            strategist_notes = strategist.analyze_report(report_data_for_strategist)
            logger.info("Strategist notes generated successfully")
        except StrategistError as exc:
            logger.warning("Strategist analysis failed: %s; proceeding with empty notes", exc)

        # --- Write daily report markdown ---
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"report_{briefing['date']}.md"
        _write_daily_report(report_path, briefing, strategist_notes)
        print(f"  Strategist: {report_path}\n")

    # --- Auto-update OS_STATE.md ---
    try:
        os_state = OSStateManager()
        os_state.update_metadata()
        logger.info("OS_STATE.md updated successfully")
    except Exception as e:
        logger.warning(f"OS_STATE.md update failed: {e}")

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

def _write_daily_report(report_path: Path, briefing: dict, strategist_notes: str) -> None:
    """Write combined daily report markdown file."""
    date_str = briefing.get("date", "unknown")
    macro_snap = briefing.get("macro_snapshot", {})
    portfolio = briefing.get("portfolio", [])

    lines = [
        f"# Daily Market Report — {date_str}",
        "",
        "## Macro Snapshot",
        "",
    ]

    if macro_snap:
        lines += [
            f"- **Regime:** {macro_snap.get('regime', 'N/A')}",
            f"- **Environment Score:** {macro_snap.get('macro_environment_score', 'N/A')}",
            f"- **USD/TRY:** {macro_snap.get('prices', {}).get('usdtry', 'N/A')}",
            f"- **BRENT:** {macro_snap.get('prices', {}).get('brent', 'N/A')}",
            f"- **VIX:** {macro_snap.get('prices', {}).get('vix', 'N/A')}",
            f"- **BIST100:** {macro_snap.get('prices', {}).get('bist100', 'N/A')}",
        ]
    else:
        lines.append("_No macro snapshot available._")

    lines += ["", "## Portfolio", ""]
    if portfolio:
        lines.append("| Ticker | Sector | P&L% | RSI | Alerts |")
        lines.append("|--------|--------|------|-----|--------|")
        for pos in portfolio:
            alerts = "; ".join(a.get("message", "") for a in pos.get("alerts", [])) or "—"
            lines.append(
                f"| {pos.get('ticker','?')} | {pos.get('sector','?')} "
                f"| {pos.get('unrealized_pnl_pct','N/A')} "
                f"| {pos.get('rsi','N/A')} | {alerts} |"
            )
    else:
        lines.append("_No portfolio data._")

    lines += [
        "",
        "---",
        "",
        "## STRATEGIST NOTES",
        "",
        strategist_notes,
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")


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

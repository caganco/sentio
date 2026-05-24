"""Main entry point for the daily BIST data update."""
import argparse
import json
import sys
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.momentum import scan_momentum_stocks
from src.analysis.portfolio import analyze_portfolio, portfolio_summary
from src.data.database import get_prices, initialize_db, sync_portfolio, upsert_prices, get_sector, get_sector_context
from src.data.fetcher import fetch_all_bist_batch, fetch_multiple_stocks, get_bist100_tickers
from src.data.kap_scraper import fetch_kap_news_full
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
from src.risk.drawdown import DrawdownTracker
from src.risk.technical_level_detector import detect_levels
from src.signals.macro_regime_gate import classify_regime
from src.signals.layers.smart_money_layer import get_l5_layer
from src.signals.layers.connectors.smart_money_connector import IsYatirimScreenerConnector
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

    # L5 Smart Money screener fetch (D-056)
    logger.info("Fetching L5 Smart Money screener data (İş Yatırım)...")
    # BIST trading-day label: explicit Europe/Istanbul date so the parquet
    # `date` field stays consistent with the UTC `written_at` stamp regardless
    # of run hour or local clock (D-074 fix B).
    _today_str = datetime.now(ZoneInfo("Europe/Istanbul")).date().isoformat()
    try:
        _l5_connector = IsYatirimScreenerConnector()
        _l5_ok = get_l5_layer().write_daily_snapshot(_l5_connector, _today_str)
        logger.info(
            "SmartMoneyL5 screener: %s (%s)",
            "written" if _l5_ok else "FAILED — check ALERT logs",
            _today_str,
        )
    except Exception as _exc:
        logger.error("SmartMoneyL5 screener fetch error (graceful): %s", _exc)

    # --- D-123 HMM Regime Detection ---
    _hmm_regime_label: str | None = None
    from src.signals.thresholds import ENABLE_HMM_WEIGHTS as _HMM_ENABLED_DU
    if _HMM_ENABLED_DU:
        logger.info("HMM regime detection (D-123)...")
        try:
            from src.signals.regime_hmm import BISTRegimeHMM
            _hmm_model = BISTRegimeHMM.load_or_retrain()
            _hmm_regime_label = _hmm_model.predict_current_regime()
            logger.info("HMM regime: %s", _hmm_regime_label)
        except Exception as _exc:
            logger.warning("HMM regime detection failed (non-fatal): %s", _exc)

    # --- Fintables Takas / MKK Custody fetch (D-116) ---
    # custody DB yolu: hem buradaki fetch hem aşağıdaki L5 skor okuması kullanır.
    from src.signals.thresholds import CUSTODY_DB_PATH as _CUSTODY_DB_PATH
    _custody_db_path = Path(__file__).parent.parent / _CUSTODY_DB_PATH
    logger.info("Fetching Fintables takas/custody data (BIST50)...")
    try:
        from src.data.fintables_scraper import FintablesScraperConnector
        _db_existed = _custody_db_path.exists()  # connector __init__ DB oluşturur — önce yakala
        _takas_conn = FintablesScraperConnector(db_path=_custody_db_path)
        if not _db_existed:
            logger.info("Custody DB yok → backfill başlatılıyor...")
            _takas_conn.backfill()
        else:
            from src.data.fintables_scraper import FintablesClient as _FintablesClient
            from src.signals.thresholds import CUSTODY_SCRAPE_RATE_LIMIT_SEC as _RATE_SEC
            import time as _time_local
            _takas_results: dict[str, bool] = {}
            _takas_blocked = False
            with _FintablesClient(session_file=_takas_conn.session_file) as _client:
                for _tidx, _tticker in enumerate(_takas_conn.tickers):
                    _tres = _takas_conn.scrape_ticker(_tticker, _today_str, _client)
                    _takas_results[_tticker] = _tres
                    if _tidx == 0 and not _tres:
                        logger.warning(
                            "Fintables takas devre disi — bot engeli aktif, skip"
                        )
                        _takas_blocked = True
                        break
                    _time_local.sleep(_RATE_SEC)
            _takas_ok = sum(1 for v in _takas_results.values() if v)
            if not _takas_blocked:
                logger.info(
                    "Fintables takas: %d/%d ticker basarili (%s)",
                    _takas_ok, len(_takas_results), _today_str,
                )
    except ImportError:
        logger.debug("playwright/fintables_scraper bulunamadı → takas fetch atlanıyor")
    except Exception as _exc:
        logger.error("Fintables takas fetch error (graceful): %s", _exc)

    # --- Is Yatirim Foreign Flow fetch (D-128; D-126 bridge kullanir) ---
    # Robots-guvenli screener; custody DB bos/yoksa L5'in change_30d sinyalini doldurur.
    from src.signals.thresholds import FOREIGN_FLOW_DB_PATH as _FOREIGN_FLOW_DB_PATH
    _foreign_flow_db_path = Path(__file__).parent.parent / _FOREIGN_FLOW_DB_PATH
    _foreign_flow_freshness = None
    logger.info("Fetching Is Yatirim foreign-flow data (screener bridge)...")
    try:
        from src.data.isyatirim_scraper import ForeignFlowConnector
        _ff_conn = ForeignFlowConnector(db_path=_foreign_flow_db_path)
        _ff_results = _ff_conn.fetch_and_store(date_str=_today_str)
        _ff_ok = sum(1 for v in _ff_results.values() if v)
        # freshness = DB'deki gercek en son tarih (AKBNK temsilci; bugun yazildiysa = bugun)
        _foreign_flow_freshness = _ff_conn.writer.get_latest_date("AKBNK")
        logger.info("Foreign flow: %d ticker yazildi (%s)", _ff_ok, _today_str)
    except Exception as _exc:
        logger.error("Foreign flow fetch error (graceful): %s", _exc)

    # --- Is Yatirim Aciga Satis PDF fetch (D-132) ---
    # Robots-guvenli PDF raporu; short_ratio L5 short_interest sinyaline beslenir.
    # SPK yasagi doneminde sinyal agirligi 0'a yakin; veri toplanmaya devam eder.
    _short_interest_ratios: dict[str, float] = {}
    logger.info("Fetching Is Yatirim short interest PDF...")
    try:
        from src.data.isyatirim_short_interest_parser import IsyatirimShortInterestConnector
        _si_conn = IsyatirimShortInterestConnector()
        _short_interest_ratios = _si_conn.get_short_ratios()
        logger.info("Short interest: %d ticker yuklendi", len(_short_interest_ratios))
        for _si_ticker, _si_ratio in list(_short_interest_ratios.items())[:5]:
            logger.debug("  %s: short_ratio=%.2f%%", _si_ticker, _si_ratio)
    except Exception as _exc:
        logger.error("Short interest fetch error (graceful): %s", _exc)

    # --- VIOP Takasbank market-wide put/call ratio (CB-008) ---
    _viop_score: float = 50.0
    _viop_conf: float = 0.0
    try:
        from src.data.viop_takasbank_parser import fetch_viop_pcr
        from src.signals.thresholds import VIOP_PCR_BEARISH, VIOP_PCR_BULLISH
        _viop_pcr_data = fetch_viop_pcr()
        if _viop_pcr_data:
            _pcr = _viop_pcr_data["put_call_ratio"]
            if _pcr >= VIOP_PCR_BEARISH:
                _viop_score = 35.0
            elif _pcr <= VIOP_PCR_BULLISH:
                _viop_score = 65.0
            else:
                _viop_score = 50.0
            _viop_conf = 0.6
            logger.info(
                "VIOP PCR: %.4f (put=%d, call=%d) -> score=%.1f",
                _pcr, _viop_pcr_data["put_oi"], _viop_pcr_data["call_oi"], _viop_score,
            )
    except Exception as _exc:
        logger.warning("VIOP Takasbank hook hatasi (graceful): %s", _exc)

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
        # fetch_kap_news_full() returns the dict shape {source_used, total, items, ...}
        # that the briefing + downstream kap_src/kap_total readers expect. A KAP
        # failure must NEVER kill the report (Macro Snapshot + Strategist live AFTER
        # this point) — graceful fallback to an empty result. (D-113 signature fix)
        try:
            kap_news = fetch_kap_news_full(_pos_tickers)
        except Exception as _kap_exc:
            logger.warning("KAP fetch failed (non-fatal): %s", _kap_exc)
            kap_news = {"source_used": "none", "total": 0, "items": []}

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

        # L5 Smart Money scores are read from parquet (written in pre-market step above).
        # Per-ticker lookup happens inline below during portfolio position assembly.

        portfolio_data = []
        kelly_sizer = KellySizer(portfolio_value_pct=100.0, kelly_fraction=0.25)
        current_positions = {}

        # Regime for TP level computation — derived once from macro_signal (D-112).
        # Falls back to NEUTRAL when macro_signal is unavailable.
        _tp_regime = "NEUTRAL"
        if macro_signal is not None:
            try:
                _l2_for_tp = (macro_signal.macro_environment_score + 1) * 50.0
                _tp_regime = classify_regime(_l2_for_tp)
            except Exception:
                pass

        # Initialize drawdown tracker with portfolio total value
        portfolio_total_value = summary.get("total_value", 0)
        drawdown_tracker = DrawdownTracker(initial_portfolio_value=portfolio_total_value if portfolio_total_value > 0 else 100000)

        for a in analyses:
            # Update drawdown tracking
            if a.current_price is not None and a.current_price > 0:
                drawdown_tracker.update_position(
                    ticker=a.ticker,
                    current_price=a.current_price,
                    entry_price=a.avg_cost
                )

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

            # Add drawdown data if available
            if a.ticker in drawdown_tracker.position_drawdowns:
                pd = drawdown_tracker.position_drawdowns[a.ticker]
                position["drawdown"] = {
                    "drawdown_pct": round(pd.peak_to_current_dd * 100, 2),
                    "peak_price": round(pd.peak_price, 2),
                    "alert_level": pd.get_drawdown_level(),
                    "max_dd_ever_pct": round(pd.max_dd_ever * 100, 2),
                }

            # Add sentiment data if available
            if a.ticker in sentiment_scores:
                sent = sentiment_scores[a.ticker]
                position["sentiment"] = {
                    "score": round(sent.get("score"), 2) if sent.get("score") is not None else None,
                    "normalized": round(sent.get("normalized"), 2) if sent.get("normalized") is not None else None,
                    "confidence": round(sent.get("confidence"), 2) if sent.get("confidence") is not None else None,
                    "bullish_count": sent.get("bullish_count", 0),
                    "bearish_count": sent.get("bearish_count", 0),
                    "article_count": sent.get("article_count", 0),
                    "source": sent.get("source"),
                }

            # L5 Smart Money score (D-116: custody DB öncelikli, yoksa İş Yatırım parquet)
            # D-132: short_ratio PDF verisini short_interest_score normalize ederek pass et
            _ticker_short_ratio = _short_interest_ratios.get(a.ticker)
            _short_interest_score: float | None = None
            if _ticker_short_ratio is not None:
                from src.data.short_interest_normalizer import score_short_interest
                _short_interest_score = score_short_interest(_ticker_short_ratio, 0.5)
                logger.debug(
                    "short_interest_pct %s: ratio=%.2f%% score=%.3f",
                    a.ticker, _ticker_short_ratio, _short_interest_score,
                )
            _l5_pos_score = get_l5_layer().compute_l5_score(
                a.ticker,
                custody_db_path=_custody_db_path if _custody_db_path.exists() else None,
                foreign_flow_db_path=_foreign_flow_db_path if _foreign_flow_db_path.exists() else None,
                short_interest_score=_short_interest_score,
                short_ratio=_ticker_short_ratio,
            )
            if _l5_pos_score is not None:
                position["smart_money"] = {
                    "l5_score": round(_l5_pos_score, 2),
                    "confidence": 0.8,
                    "source": "isyatirim_screener_l5",
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

            # TP levels — detect_levels() per ticker (D-112).
            # OHLCV unavailable or any exception → tp1/tp2/tp3 = null (silent skip).
            try:
                _ohlcv = db_data.get(a.ticker)
                if _ohlcv is not None and not _ohlcv.empty:
                    _plan = detect_levels(_ohlcv, _tp_regime)
                    position["tp1"] = round(_plan.tp1, 2)
                    position["tp2"] = round(_plan.tp2, 2)
                    position["tp3"] = round(_plan.tp3, 2)
                    position["tp_regime"] = _plan.regime
                    position["tp_confidence"] = _plan.confidence
                else:
                    position.update({"tp1": None, "tp2": None, "tp3": None})
            except Exception:
                position.update({"tp1": None, "tp2": None, "tp3": None})

            portfolio_data.append(position)

        # Update portfolio drawdown and check circuit breaker
        drawdown_tracker.update_portfolio(current_value=portfolio_total_value)
        portfolio_drawdown_alerts = drawdown_tracker.get_all_alerts()
        if portfolio_drawdown_alerts:
            logger.warning(f"Drawdown alerts: {portfolio_drawdown_alerts}")

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
            "portfolio_drawdown": {
                "drawdown_pct": round(drawdown_tracker.portfolio_dd.portfolio_dd * 100, 2),
                "peak_value": round(drawdown_tracker.portfolio_dd.peak_value, 2),
                "current_value": round(drawdown_tracker.portfolio_dd.current_value, 2),
                "mode": drawdown_tracker.portfolio_mode,
                "circuit_breaker_triggered": drawdown_tracker.portfolio_dd.circuit_breaker_triggered,
            },
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

        # --- D-108 Macro Gate v2 (CDS-percentile-conditional soft BEAR) ---
        # Computes the v2 scaling once per run and stashes in briefing for audit /
        # future position_sizer_v2 callers. Failure path: try/except -> v1 fallback.
        macro_gate_v2 = None
        try:
            from src.signals.local.cache_store import LocalMacroCache as _LMC
            from src.signals.layers.macro_layer import _compute_cds_percentile
            from src.signals.macro_regime_gate import (
                HardExitFlags as _HardExitFlags,
                calculate_macro_regime_scaling_v2 as _gate_v2,
            )
            from src.signals.thresholds import CDS_PERCENTILE_WINDOW as _CPW

            _cds_hist = _LMC().get_cds_history(days=_CPW)
            _cds_pct = _compute_cds_percentile(_cds_hist)
            _cds_pct_used = _cds_pct if _cds_pct is not None else 0.5
            _l2_score = (briefing["macro_snapshot"].get("macro_environment_score", 0) + 1) * 50.0
            _cds_latest = _cds_hist[-1].get("cds_bps", 0.0) if _cds_hist else 0.0
            _portfolio_dd = briefing.get("portfolio_drawdown", {}).get("drawdown_pct", 0.0) / 100.0
            _hard = _HardExitFlags(
                cds_bps=float(_cds_latest),
                usdtry_zscore=0.0,                # Phase 1 placeholder (DEC-017)
                portfolio_drawdown=float(_portfolio_dd),
            )
            _v2 = _gate_v2(_l2_score, _cds_pct_used, hard_exit_flags=_hard)
            macro_gate_v2 = {
                "scaling": _v2.scaling,
                "regime": _v2.regime,
                "cds_percentile": _cds_pct,        # None if history < 30d
                "cds_overlay": _v2.cds_overlay,
                "hard_exit": _v2.hard_exit,
                "reason": _v2.reason,
            }
            logger.info("Macro gate v2: %s", _v2.reason)
            briefing["macro_gate_v2"] = macro_gate_v2
        except Exception as exc:
            logger.warning("D-108 macro gate v2 compute failed (non-fatal): %s", exc)

        briefing["hmm_regime"] = _hmm_regime_label   # D-123 audit field (None when disabled)
        briefing["foreign_flow_freshness"] = _foreign_flow_freshness   # D-128 son foreign_flow tarihi
        briefing["short_interest_ticker_count"] = len(_short_interest_ratios)  # D-132 PDF ticker sayisi

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
            "portfolio_drawdown": briefing.get("portfolio_drawdown", {}),
            "portfolio_mode": drawdown_tracker.portfolio_mode,
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

        # --- D-107 Alpha Attribution: signal log writes + return fill ---
        try:
            _write_signal_logs_d107(
                tickers=tickers,
                db_data=db_data,
                macro_data=macro_data,
                macro_signal=macro_signal if 'macro_signal' in locals() else None,
                kelly_sizing=kelly_sizing,
                hmm_regime=_hmm_regime_label,   # D-123
            )
        except Exception as exc:
            logger.warning("D-107 signal log writes failed (non-fatal): %s", exc)

    # --- Forward Test Log (for live validation against backtest) ---
    if scan:
        _write_forward_test_log(briefing, drawdown_tracker)

    # --- Auto-update OS_STATE.md ---
    try:
        os_state = OSStateManager()
        os_state.update_metadata()
        logger.info("OS_STATE.md updated successfully")
    except Exception as e:
        logger.warning(f"OS_STATE.md update failed: {e}")

    logger.info("=== BIST Daily Update Complete ===")


# ── Forward Test Log ────────────────────────────────────────────────────────

def _write_forward_test_log(briefing: dict, drawdown_tracker) -> None:
    """Write daily forward test snapshot to reports/forward_test/YYYY-MM-DD.json.

    Captures portfolio state and signal environment for live-vs-backtest comparison.
    """
    try:
        today_str = briefing.get("date", str(_date.today()))
        log_dir = Path(__file__).parent.parent / "reports" / "forward_test"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{today_str}.json"

        portfolio_value = briefing.get("portfolio_drawdown", {}).get("current_value", 0)
        initial_value = briefing.get("portfolio_drawdown", {}).get("peak_value", portfolio_value)
        return_pct = (portfolio_value - initial_value) / initial_value if initial_value > 0 else 0.0

        forward_log = {
            "date": today_str,
            "portfolio_value": round(portfolio_value, 2),
            "return_pct": round(return_pct * 100, 2),
            "max_dd_pct": round(briefing.get("portfolio_drawdown", {}).get("drawdown_pct", 0.0), 2),
            "circuit_breaker": briefing.get("portfolio_drawdown", {}).get("circuit_breaker_triggered", False),
            "portfolio_mode": briefing.get("portfolio_drawdown", {}).get("mode", "NORMAL"),
            "positions": {
                p["ticker"]: {
                    "qty": p.get("quantity"),
                    "avg_cost": p.get("avg_cost"),
                    "current_price": p.get("current_price"),
                    "unrealized_pnl_pct": p.get("unrealized_pnl_pct"),
                }
                for p in briefing.get("portfolio", [])
            },
            "macro_regime": briefing.get("macro_snapshot", {}).get("regime", "N/A"),
            "macro_score": briefing.get("macro_snapshot", {}).get("macro_environment_score", None),
        }

        log_path.write_text(json.dumps(forward_log, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Forward test log: {log_path}")
    except Exception as exc:
        logger.warning(f"Forward test log write failed: {exc}")


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


# ── D-107 Alpha Attribution Hook (SPEC_ALPHA_INFRASTRUCTURE_1 Phase 3) ──────

def _compute_position_weights_d107(kelly_sizing: dict) -> dict[str, float]:
    """Aggregate Kelly results into {symbol: weight_pct_of_portfolio}."""
    out: dict[str, float] = {}
    for ticker, info in (kelly_sizing or {}).items():
        if not isinstance(info, dict) or "error" in info:
            continue
        rec_pct = info.get("recommended_size_pct")
        if rec_pct is None:
            continue
        out[ticker] = float(rec_pct) / 100.0
    return out


def _write_signal_logs_d107(
    tickers: list[str],
    db_data: dict,
    macro_data: dict,
    macro_signal,
    kelly_sizing: dict,
    hmm_regime: str | None = None,   # D-123
) -> None:
    """Per-symbol compute_signal() loop + flat parquet write + return fill (D-107).

    Writes flat data/signal_logs/YYYY-MM-DD.parquet via alpha_attribution.
    Pure additive — failure here must NEVER break the briefing pipeline.
    Each ticker computed in its own try/except so one bad ticker can't kill the rest.
    """
    from datetime import date as _d
    from src.signals.engine import compute_signal
    from src.signals.macro_regime_gate import classify_regime
    from src.backtest.data_loader import build_technical_data
    from src.data.signal_logger import SignalLogger, ReturnFiller
    from src.data.universe_snapshot import UniverseSnapshot
    from src.reporting.alpha_attribution import write_daily_snapshot
    import pandas as _pd

    today = _d.today()
    universe = UniverseSnapshot()
    universe.fetch_and_save_current()  # idempotent — refresh current snapshot

    # Regime label from L2 macro score on 0-100 scale.
    regime_label = "NEUTRAL"
    try:
        if macro_signal is not None:
            env_score = float(macro_signal.macro_environment_score)
            l2_score = (env_score + 1.0) * 50.0   # [-1,+1] -> [0,100]
            regime_label = classify_regime(l2_score)
    except Exception as exc:
        logger.info("D-107 regime classify failed: %s", exc)

    position_weights = _compute_position_weights_d107(kelly_sizing)
    sig_logger = SignalLogger()
    n_logged = 0
    records: list[dict] = []

    for symbol in tickers:
        try:
            df = db_data.get(symbol)
            if df is None or df.empty:
                continue
            tech = build_technical_data(df, _pd.Timestamp(today))
            if tech is None:
                continue
            macro_dict = macro_data if isinstance(macro_data, dict) else {}
            result = compute_signal(
                symbol=symbol,
                technical_data=tech,
                macro_data=macro_dict,
                kap_events=[],  # Faz 1: KAP routing into engine deferred
                as_of_date=today,
                hmm_regime=hmm_regime,   # D-123
            )
            tier = universe.get_liquidity_tier(symbol, today.year, today.month)
            record = sig_logger.build_record(
                symbol=symbol,
                result=result,
                liquidity_tier=tier,
                position_weight=position_weights.get(symbol, 0.0),
                regime_label=regime_label,
                viop_score=_viop_score,
                viop_conf=_viop_conf,
            )
            records.append(record.model_dump())
            n_logged += 1
        except Exception as exc:
            logger.info("D-107 signal log skip %s: %s", symbol, exc)

    logger.info("D-107 signal log: %d symbols computed (regime=%s)", n_logged, regime_label)

    # Write flat daily parquet — always runs, even when n_logged == 0
    write_daily_snapshot(records, today)

    # Forward-return fill: reads flat YYYY-MM-DD.parquet from past trading days
    try:
        from src.data.database import get_prices as _get_prices

        def _price_on(symbol: str, d) -> float | None:
            try:
                prices = _get_prices(symbol, limit_days=120)
                if prices is None or prices.empty:
                    return None
                d_ts = _pd.Timestamp(d)
                idx = prices.index
                idx_at_or_before = idx[idx <= d_ts]
                if len(idx_at_or_before) == 0:
                    return None
                return float(prices.loc[idx_at_or_before[-1], "Close"])
            except Exception:
                return None

        def _reader(d) -> "_pd.DataFrame | None":
            path = Path(__file__).parent.parent / "data" / "signal_logs" / f"{d}.parquet"
            if not path.exists():
                return None
            return _pd.read_parquet(path)

        filler = ReturnFiller()
        n_filled = filler.fill(today, _price_on, _reader)
        logger.info("D-107 return filler: %d rows backfilled", n_filled)
    except Exception as exc:
        logger.warning("D-107 return filler failed (non-fatal): %s", exc)

    # --- Daily IC computation (D-139) ---
    try:
        from src.analytics.ic_history import ICHistoryWriter

        n_ic = ICHistoryWriter().run_daily(today)
        logger.info("D-139 IC history: %d rows appended", n_ic)
    except Exception as exc:
        logger.warning("D-139 IC daily compute failed (non-fatal): %s", exc)

    # --- NAV Discount Tracker (D-143, RR-013) ---
    try:
        from src.analytics.nav_calculator import NAVCalculator
        from src.analytics.nav_zscore import NAVZScoreTracker
        from src.signals.thresholds import (
            NAV_DISCOUNT_KADEME1_KAPATMA,
            NAV_DISCOUNT_KADEME2_ALIM,
        )

        nav_result = NAVCalculator().compute_tier1_nav("KCHOL")
        zscore_result = NAVZScoreTracker().update(nav_result, as_of_date=today)

        disc = nav_result["discount_pct"]
        z = zscore_result["z_score"]
        signal = zscore_result["signal"]
        logger.info(
            "D-143 NAV KCHOL: iskonto=%.1f%% z=%.2f sinyal=%s",
            disc * 100,
            z if z == z else float("nan"),  # nan-safe
            signal,
        )

        # Alert trigger: append NAV section to today's daily report markdown
        nav_alert_line = ""
        if disc < NAV_DISCOUNT_KADEME1_KAPATMA:
            nav_alert_line = (
                f"[NAV-ALERT] KCHOL iskonto {disc:.1%} < Kademe-1 siniri "
                f"({NAV_DISCOUNT_KADEME1_KAPATMA:.0%}) -- TRIM/KAPATMA sinyali"
            )
        elif disc > NAV_DISCOUNT_KADEME2_ALIM:
            nav_alert_line = (
                f"[NAV-ALERT] KCHOL iskonto {disc:.1%} > Kademe-2 siniri "
                f"({NAV_DISCOUNT_KADEME2_ALIM:.0%}) -- EK ALIM sinyali"
            )

        import glob as _glob
        report_files = sorted(_glob.glob("reports/daily_*.md"), reverse=True)
        if report_files:
            z_str = f"{z:.2f}" if z == z else "N/A"
            nav_section = (
                f"\n\n## NAV Tracker -- KCHOL\n"
                f"- iskonto: {disc:.1%}  |  z-skor: {z_str}  |  sinyal: {signal}\n"
            )
            if nav_alert_line:
                nav_section += f"- WARNING: {nav_alert_line}\n"
            with open(report_files[0], "a", encoding="utf-8") as _f:
                _f.write(nav_section)

    except Exception as exc:
        logger.warning("D-143 NAV tracker failed (non-fatal): %s", exc)


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
    try:
        run_update(scan=args.scan, generate_report=args.generate_report)
    except Exception as _exc:
        # D-120: pipeline tümüyle düşerse failure dosyası yaz (+opsiyonel email), sonra raise.
        from src.utils.failure_notifier import notify_failure
        _fpath = notify_failure(
            _exc,
            context=f"daily_update scan={args.scan} generate_report={args.generate_report}",
        )
        logger.error("daily_update FAILED — failure logged to %s", _fpath)
        raise

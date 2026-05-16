"""Backtest with VADER sentiment layer integrated (2024-2026)."""
import json
import logging
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest.data_loader import build_macro_data, build_technical_data
from src.backtest.metrics import calculate_sharpe, summarize
from src.signals.layers.risk_layer import score_risk
from src.signals.layers.sentiment_layer import score_sentiment
from src.signals.layers.technical_layer import score_technical
from src.signals.thresholds import MASTER_WEIGHTS, SIGNAL_THRESHOLDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy loggers during backtest
_NOISY_LOGGERS = [
    "src.signals.layers.macro_layer",
    "src.signals.local_macro_signals",
    "src.signals.local",
    "src.data.tcmb_client",
    "src.data.cds_client",
]


class BacktestEngineWithSentiment:
    """Backtest with VADER sentiment layer integrated."""

    def __init__(
        self,
        initial_capital: float = 120_000.0,
        commission_pct: float = 0.001,
        kelly_fraction: float = 0.25,
        start_date: str = "2024-01-01",
        end_date: str = "2026-05-31",
        quiet_warnings: bool = True,
    ):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.kelly_fraction = kelly_fraction
        self.start_date = start_date
        self.end_date = end_date
        self.quiet_warnings = quiet_warnings

        self.cash = initial_capital
        self.portfolio_value = initial_capital
        self.positions: dict[str, dict] = {}
        self.trades: list[dict] = []
        self.equity_curve: list[float] = []
        self.daily_dates: list[pd.Timestamp] = []
        self.drawdown_curve: list[float] = []
        self.audit_trail: list[dict] = []
        self.peak_equity = initial_capital
        self.max_dd = 0.0
        self.circuit_breaker_active = False
        self.sentiment_scores: dict[str, list[float]] = {}  # Track sentiment scores

    def _reset_state(self) -> None:
        self.cash = self.initial_capital
        self.portfolio_value = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_dates = []
        self.drawdown_curve = []
        self.audit_trail = []
        self.peak_equity = self.initial_capital
        self.max_dd = 0.0
        self.circuit_breaker_active = False
        self.sentiment_scores = {}

    def run(
        self,
        price_data: dict[str, pd.DataFrame],
        macro_ts: pd.DataFrame,
        benchmark_series = None,
    ):
        """Run backtest with sentiment layer."""
        self._reset_state()
        if self.quiet_warnings:
            saved = {n: logging.getLogger(n).level for n in _NOISY_LOGGERS}
            for n in _NOISY_LOGGERS:
                logging.getLogger(n).setLevel(logging.ERROR)
        try:
            self._run_loop(price_data, macro_ts)
        finally:
            if self.quiet_warnings:
                for n, lvl in saved.items():
                    logging.getLogger(n).setLevel(lvl)
        return self

    def _run_loop(
        self,
        price_data: dict[str, pd.DataFrame],
        macro_ts: pd.DataFrame,
    ) -> None:
        all_dates: set[pd.Timestamp] = set()
        for df in price_data.values():
            all_dates.update(df.index.tolist())

        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)
        trading_dates = sorted(d for d in all_dates if start <= d <= end)

        logger.info(
            f"Backtest WITH SENTIMENT: {len(trading_dates)} days, "
            f"{self.start_date} → {self.end_date}, {len(price_data)} tickers"
        )

        for i, current_date in enumerate(trading_dates):
            macro_snap = self._safe_macro(macro_ts, current_date)

            for symbol, df in price_data.items():
                if current_date not in df.index:
                    continue
                close_price = float(df.loc[current_date, "Close"])
                volume = float(df.loc[current_date, "Volume"])
                if volume == 0 or pd.isna(close_price) or close_price <= 0:
                    continue

                tech_data = build_technical_data(df, current_date)
                if tech_data is None:
                    continue

                # Compute composite with sentiment
                composite = self._compute_composite_with_sentiment(
                    tech_data, macro_snap, symbol
                )
                signal = self._composite_to_signal(composite)
                vix_level = macro_snap.get("vix_level", 17.0)
                already_holding = symbol in self.positions

                if signal in ("BUY-STRONG", "BUY-WEAK") and not already_holding and not self.circuit_breaker_active:
                    self._execute_buy(symbol, current_date, close_price, composite, vix_level)
                elif signal in ("SELL-WEAK", "SELL-STRONG") and already_holding:
                    self._execute_sell(symbol, current_date, close_price)

            self._update_portfolio(price_data, current_date)

            if (i + 1) % 50 == 0:
                logger.info(
                    f"  Day {i+1}: portfolio={self.portfolio_value:,.0f} TL, "
                    f"DD={self.max_dd:.1%}, open={len(self.positions)}"
                )

        logger.info(
            f"Backtest complete: {len(self.trades)} trades, "
            f"final={self.portfolio_value:,.0f} TL, max_dd={self.max_dd:.1%}"
        )

    def _compute_composite_with_sentiment(
        self,
        technical_data: dict,
        macro_data: dict,
        symbol: str,
    ) -> float:
        """Composite = tech*0.20 + macro*0.35 + risk*0.05 + sentiment*0.05 + 19.2

        The +19.2 = 50*(kap_w=0.15 + sm_w=0.20) for unimplemented layers.
        Sentiment NOW INTEGRATED (was hardcoded to 50 before).
        """
        try:
            tech_score = score_technical(technical_data).score
        except Exception:
            tech_score = 50.0

        try:
            macro_score = self._global_macro_score(macro_data)
        except Exception:
            macro_score = 50.0

        try:
            risk_score = score_risk(symbol, technical_data, macro_data).score
        except Exception:
            risk_score = 50.0

        # NEW: Sentiment score (was missing before)
        try:
            sentiment_score = score_sentiment(symbol).score
            if symbol not in self.sentiment_scores:
                self.sentiment_scores[symbol] = []
            self.sentiment_scores[symbol].append(sentiment_score)
        except Exception as e:
            logger.debug(f"Sentiment error for {symbol}: {e}")
            sentiment_score = 50.0

        # Composite formula updated to include sentiment weight (0.05)
        composite = (
            tech_score * 0.20
            + macro_score * 0.35
            + risk_score * 0.05
            + sentiment_score * 0.05
            + 19.2  # 50*(0.15 + 0.20) for KAP + SmartMoney
        )
        return max(0.0, min(100.0, composite))

    @staticmethod
    def _global_macro_score(macro_data: dict) -> float:
        """Global macro score without TCMB/CDS local adjustment."""
        from src.signals.thresholds import ASSET_DIRECTIONS

        weighted_sum = 0.0
        total_weight = 0.0

        for asset, direction in ASSET_DIRECTIONS.items():
            raw = macro_data.get(asset, macro_data.get(asset.lower()))
            if raw is None:
                continue
            raw_f = max(-1.0, min(1.0, float(raw)))
            adjusted = raw_f * direction
            weight = abs(direction)
            weighted_sum += adjusted * weight
            total_weight += weight

        if total_weight == 0:
            return 50.0

        normalized = weighted_sum / total_weight
        return max(0.0, min(100.0, (normalized + 1.0) / 2.0 * 100.0))

    def _composite_to_signal(self, score: float) -> str:
        if score >= SIGNAL_THRESHOLDS["buy_strong"]:
            return "BUY-STRONG"
        if score >= SIGNAL_THRESHOLDS["buy_weak"]:
            return "BUY-WEAK"
        if score >= SIGNAL_THRESHOLDS["hold_lower"]:
            return "HOLD"
        if score >= SIGNAL_THRESHOLDS["sell_weak"]:
            return "SELL-WEAK"
        return "SELL-STRONG"

    def _get_kelly_allocation_tl(self, composite: float, vix_level: float) -> float:
        win_prob = 0.50 + (composite - 50.0) / 200.0
        kelly_raw = max(0.0, 2.0 * win_prob - 1.0)
        position_frac = min(kelly_raw * self.kelly_fraction, 0.05)
        if vix_level and vix_level > 25.0:
            position_frac *= 0.75
        return position_frac * self.portfolio_value

    def _execute_buy(
        self,
        symbol: str,
        current_date: pd.Timestamp,
        close_price: float,
        composite: float,
        vix_level: float,
    ) -> bool:
        allocation_tl = self._get_kelly_allocation_tl(composite, vix_level)
        shares = int(allocation_tl / close_price)
        if shares <= 0:
            return False

        cost = shares * close_price
        commission = cost * self.commission_pct
        total_cost = cost + commission

        if total_cost > self.cash:
            return False

        self.cash -= total_cost
        self.positions[symbol] = {
            "shares": shares,
            "entry_price": close_price,
            "last_price": close_price,
            "entry_date": current_date,
            "composite": composite,
        }
        self.trades.append({
            "symbol": symbol,
            "type": "BUY",
            "date": current_date,
            "price": close_price,
            "shares": shares,
            "composite": composite,
            "commission": commission,
        })
        return True

    def _execute_sell(
        self,
        symbol: str,
        current_date: pd.Timestamp,
        close_price: float,
        reason: str = "signal",
    ) -> bool:
        pos = self.positions.get(symbol)
        if pos is None:
            return False

        proceeds = pos["shares"] * close_price
        commission = proceeds * self.commission_pct
        net_proceeds = proceeds - commission

        entry_cost = pos["shares"] * pos["entry_price"]
        pnl = net_proceeds - entry_cost
        pnl_pct = pnl / entry_cost if entry_cost > 0 else 0.0

        self.cash += net_proceeds
        del self.positions[symbol]

        self.trades.append({
            "symbol": symbol,
            "type": "SELL",
            "date": current_date,
            "price": close_price,
            "shares": pos["shares"],
            "entry_price": pos["entry_price"],
            "entry_date": pos["entry_date"],
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "commission": commission,
            "reason": reason,
        })
        return True

    def _update_portfolio(
        self,
        price_data: dict[str, pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> None:
        position_value = 0.0
        for sym, pos in self.positions.items():
            if sym in price_data and current_date in price_data[sym].index:
                price = float(price_data[sym].loc[current_date, "Close"])
                if price > 0:
                    pos["last_price"] = price
                    position_value += pos["shares"] * price
            else:
                position_value += pos["shares"] * pos.get("last_price", pos["entry_price"])

        self.portfolio_value = self.cash + position_value
        self.equity_curve.append(self.portfolio_value)
        self.daily_dates.append(current_date)

        if self.portfolio_value > self.peak_equity:
            self.peak_equity = self.portfolio_value

        dd = (self.portfolio_value - self.peak_equity) / self.peak_equity
        self.drawdown_curve.append(dd)
        if dd < self.max_dd:
            self.max_dd = dd

        self.circuit_breaker_active = dd <= -0.15

        # Stop-loss and profit-target
        symbols_to_exit = []
        for sym in list(self.positions.keys()):
            pos = self.positions[sym]
            entry_price = pos["entry_price"]
            current_price = pos.get("last_price", entry_price)

            stop_loss_price = entry_price * 0.92
            if current_price <= stop_loss_price:
                symbols_to_exit.append((sym, current_price, "stop_loss"))
                continue

            profit_target_price = entry_price * 1.20
            if current_price >= profit_target_price:
                symbols_to_exit.append((sym, current_price, "profit_target"))

        for sym, exit_price, reason in symbols_to_exit:
            self._execute_sell(sym, current_date, exit_price, reason=reason)

    @staticmethod
    def _safe_macro(macro_ts: pd.DataFrame, as_of: pd.Timestamp) -> dict:
        try:
            return build_macro_data(macro_ts, as_of)
        except Exception:
            return {}


def load_macro_timeseries(start: str = "2024-01-01", end: str = "2026-05-31") -> pd.DataFrame:
    """Load macro timeseries from yfinance."""
    import yfinance as yf

    instruments = {
        "USDTRY": "USDTRY=X",
        "VIX": "^VIX",
        "BRENT": "BZ=F",
        "SP500": "^GSPC",
        "BIST100": "XU100.IS",
    }

    data = {}
    for key, ticker in instruments.items():
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(level=1, axis=1)
            data[key] = df["Close"]
            logger.info(f"{key}: {len(df)} rows loaded")
        except Exception as e:
            logger.warning(f"{key}: failed — {e}")

    return pd.DataFrame(data)


def load_price_data_for_backtest(
    tickers: list[str],
    start: str = "2024-01-01",
    end: str = "2026-05-31",
) -> dict[str, pd.DataFrame]:
    """Load BIST price data."""
    import yfinance as yf

    result = {}
    for ticker in tickers:
        symbol = f"{ticker}.IS" if not ticker.endswith(".IS") else ticker
        try:
            df = yf.download(symbol, start=start, end=end, progress=False)
            if df.empty or len(df) < 20:
                logger.warning(f"{ticker}: insufficient data")
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(level=1, axis=1)
            result[ticker] = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            logger.info(f"{ticker}: {len(df)} rows loaded")
        except Exception as e:
            logger.warning(f"{ticker}: download failed — {e}")

    return result


if __name__ == "__main__":
    logger.info("=== Backtest WITH VADER Sentiment ===")

    # Load data
    tickers = ["AKSEN", "TTKOM", "TAVHL", "KCHOL", "ENERY", "GARAN"]
    logger.info(f"Loading price data for {tickers}...")
    price_data = load_price_data_for_backtest(tickers)

    logger.info("Loading macro timeseries...")
    macro_ts = load_macro_timeseries()

    if not price_data or macro_ts.empty:
        logger.error("Failed to load data — check yfinance connectivity")
        exit(1)

    # Run backtest
    engine = BacktestEngineWithSentiment(
        initial_capital=120_000.0,
        start_date="2024-01-01",
        end_date="2026-05-31",
    )
    engine.run(price_data, macro_ts)

    # Calculate metrics
    metrics = summarize(engine)
    sharpe = calculate_sharpe(engine.equity_curve)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "backtest_period": f"2024-01-01 to 2026-05-31",
        "sentiment_layer": "VADER (integrated)",
        "sharpe_ratio": round(sharpe, 4),
        "metrics": metrics,
        "sentiment_scores_sample": {
            ticker: sentiment_scores[:5] if sentiment_scores else []
            for ticker, sentiment_scores in engine.sentiment_scores.items()
        },
    }

    report_path = Path("reports/backtest/backtest_with_sentiment_2024_2026.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Report saved to {report_path}")
    logger.info(f"\n=== BACKTEST RESULTS ===")
    logger.info(f"Sharpe Ratio: {sharpe:.4f}")
    logger.info(f"Total Return: {metrics['total_return_pct']:.2f}%")
    logger.info(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
    logger.info(f"Win Rate: {metrics['win_rate_pct']:.2f}%")
    logger.info(f"Trades: {metrics['completed_trades']} completed")

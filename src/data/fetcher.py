import time
from typing import Optional

import pandas as pd
import yfinance as yf

from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0


def fetch_bist_stock(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a single BIST stock with retry logic."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t = yf.Ticker(ticker)
            data = t.history(period=period, auto_adjust=True)
            if data.empty:
                logger.warning("No data returned for %s", ticker)
                return None
            # Keep only OHLCV columns, rename to standard names
            data = data[["Open", "High", "Low", "Close", "Volume"]].copy()
            # Strip timezone from index so downstream code stays simple
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            logger.debug("Fetched %d rows for %s", len(data), ticker)
            return data
        except Exception as exc:
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "Attempt %d/%d failed for %s: %s. Retrying in %.0fs…",
                attempt, _MAX_RETRIES, ticker, exc, wait,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)
            else:
                logger.error("All retries exhausted for %s: %s", ticker, exc)
                return None


def fetch_multiple_stocks(tickers: list[str], period: str = "1y", delay: float = 0.3) -> dict[str, pd.DataFrame]:
    """Fetch data for multiple tickers sequentially with a small delay."""
    results: dict[str, pd.DataFrame] = {}
    total = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        logger.info("[%d/%d] Fetching %s…", i, total, ticker)
        df = fetch_bist_stock(ticker, period=period)
        if df is not None and not df.empty:
            results[ticker] = df
        if i < total:
            time.sleep(delay)
    logger.info("Successfully fetched %d/%d tickers", len(results), total)
    return results


def get_bist100_tickers() -> list[str]:
    """Load BIST ticker list from config.yaml."""
    config = load_config()
    return config.get("data", {}).get("bist100_tickers", [])


def get_portfolio_tickers() -> list[str]:
    """Return tickers that appear in the portfolio config."""
    config = load_config()
    positions = config.get("portfolio", {}).get("positions", [])
    return [p["ticker"] for p in positions]

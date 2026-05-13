import time
from typing import Optional

import pandas as pd
import yfinance as yf

from src.utils.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_BATCH_SIZE = 60  # yfinance handles up to ~100 symbols reliably in one call


def fetch_bist_stock(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a single BIST stock with retry logic."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t = yf.Ticker(ticker)
            data = t.history(period=period, auto_adjust=True)
            if data.empty:
                logger.warning("No data returned for %s", ticker)
                return None
            # Keep only OHLCV columns
            data = data[["Open", "High", "Low", "Close", "Volume"]].copy()
            # Drop rows where Close is NaN (yfinance returns a partial intraday row
            # with NaN OHLC + filled Volume for the current trading day)
            before = len(data)
            data = data.dropna(subset=["Close"])
            dropped = before - len(data)
            if dropped:
                logger.debug("Dropped %d NaN-close row(s) for %s", dropped, ticker)
            if data.empty:
                logger.warning("All rows had NaN Close for %s", ticker)
                return None
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


def fetch_all_bist_batch(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV for all tickers in a single yfinance batch call.

    Much faster than fetch_multiple_stocks for large lists (60+ tickers).
    Falls back to sequential fetch if the batch returns no data.

    Returns: dict keyed by bare ticker (e.g. "THYAO"), not "THYAO.IS".
    """
    if not tickers:
        return {}

    symbols = [f"{t}.IS" for t in tickers]
    logger.info("Batch-fetching %d tickers via yfinance…", len(symbols))

    try:
        raw = yf.download(
            symbols,
            period=period,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as exc:
        logger.error("Batch download failed: %s — falling back to sequential", exc)
        return fetch_multiple_stocks(
            [f"{t}.IS" for t in tickers], period=period
        )

    if raw is None or raw.empty:
        logger.warning("Batch download returned empty — falling back to sequential")
        return fetch_multiple_stocks(
            [f"{t}.IS" for t in tickers], period=period
        )

    results: dict[str, pd.DataFrame] = {}
    failed: list[str] = []

    for ticker, symbol in zip(tickers, symbols):
        try:
            # Multi-ticker download nests columns under ticker symbol
            if len(tickers) == 1:
                df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
            else:
                df = raw[symbol][["Open", "High", "Low", "Close", "Volume"]].copy()

            before = len(df)
            df = df.dropna(subset=["Close"])
            dropped = before - len(df)
            if dropped:
                logger.debug("Dropped %d NaN-close row(s) for %s", dropped, ticker)

            if df.empty:
                logger.warning("No usable data for %s in batch result", ticker)
                failed.append(ticker)
                continue

            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            results[ticker] = df
        except (KeyError, TypeError):
            logger.warning("Could not extract data for %s from batch result", ticker)
            failed.append(ticker)

    logger.info(
        "Batch fetch complete: %d/%d succeeded, %d failed",
        len(results), len(tickers), len(failed),
    )

    # Retry failed tickers sequentially
    if failed:
        logger.info("Retrying %d failed tickers sequentially…", len(failed))
        retry_symbols = [f"{t}.IS" for t in failed]
        fallback = fetch_multiple_stocks(retry_symbols, period=period)
        for sym, df in fallback.items():
            bare = sym.replace(".IS", "")
            results[bare] = df

    return results


def get_bist100_tickers() -> list[str]:
    """Load BIST ticker list from config.yaml (portfolio.tickers)."""
    config = load_config()
    return config.get("portfolio", {}).get("tickers", [])


def get_portfolio_tickers() -> list[str]:
    """Return tickers that appear in the portfolio positions config."""
    config = load_config()
    positions = config.get("portfolio", {}).get("positions", {})
    if isinstance(positions, dict):
        return list(positions.keys())
    return [p["ticker"] for p in positions]

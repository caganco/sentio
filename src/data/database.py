import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pandas as pd

from src.utils.config import get_db_path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prices (
    date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (date, ticker)
);

CREATE TABLE IF NOT EXISTS portfolio (
    ticker TEXT PRIMARY KEY,
    quantity INTEGER NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT NOT NULL,
    reason TEXT,
    date_added TEXT NOT NULL,
    PRIMARY KEY (ticker)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
"""


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
    logger.info("Database initialized at %s", get_db_path())


def upsert_prices(df: pd.DataFrame, ticker: str) -> int:
    """Insert or replace price rows for a ticker. Returns row count written.
    Rows with NaN Close are skipped (partial intraday rows from yfinance)."""
    if df.empty:
        return 0

    # Drop NaN-Close rows defensively (fetcher already does this, but
    # `float(nan or 0) == nan` so we must filter, not coerce).
    df = df.dropna(subset=["Close"])
    if df.empty:
        return 0

    def _num(v):
        return float(v) if pd.notna(v) else 0.0

    rows = []
    for date, row in df.iterrows():
        date_str = str(date)[:10]
        rows.append((
            date_str,
            ticker,
            _num(row.get("Open")),
            _num(row.get("High")),
            _num(row.get("Low")),
            _num(row.get("Close")),
            int(_num(row.get("Volume"))),
        ))

    with get_connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO prices (date, ticker, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )

    return len(rows)


def sync_portfolio(positions: list[dict]) -> None:
    """Sync portfolio positions from config into DB."""
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        for pos in positions:
            conn.execute(
                "INSERT OR REPLACE INTO portfolio (ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?)",
                (pos["ticker"], pos["quantity"], pos["avg_cost"], now),
            )
    logger.info("Portfolio synced: %d positions", len(positions))


def get_prices(ticker: str, limit_days: int = 365) -> pd.DataFrame:
    """Fetch price history for a ticker from DB."""
    query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(ticker, limit_days))
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df.columns = [c.capitalize() for c in df.columns]
    return df


def get_all_prices_latest() -> pd.DataFrame:
    """Fetch the most recent close price for every ticker."""
    query = """
        SELECT p.ticker, p.date, p.close, p.volume
        FROM prices p
        INNER JOIN (
            SELECT ticker, MAX(date) AS max_date FROM prices GROUP BY ticker
        ) latest ON p.ticker = latest.ticker AND p.date = latest.max_date
        ORDER BY p.ticker
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def get_portfolio_with_prices() -> pd.DataFrame:
    """Join portfolio positions with latest prices."""
    query = """
        SELECT
            pf.ticker,
            pf.quantity,
            pf.avg_cost,
            pr.close AS current_price,
            pr.date AS price_date
        FROM portfolio pf
        LEFT JOIN (
            SELECT p.ticker, p.close, p.date
            FROM prices p
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date FROM prices GROUP BY ticker
            ) latest ON p.ticker = latest.ticker AND p.date = latest.max_date
        ) pr ON pf.ticker = pr.ticker
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pandas as pd

from src.utils.config import get_db_path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

KAP_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS kap_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_index  TEXT NOT NULL UNIQUE,
    symbol            TEXT NOT NULL,
    published_at      TEXT NOT NULL,
    fetched_at        TEXT NOT NULL,
    subject           TEXT NOT NULL,
    category          TEXT NOT NULL,
    summary           TEXT,
    url               TEXT NOT NULL,
    source_type       TEXT NOT NULL DEFAULT 'kap_official',
    structured_data   TEXT,
    has_attachment    INTEGER DEFAULT 0,
    attachment_urls   TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_kap_symbol_date
    ON kap_events(symbol, published_at);
CREATE INDEX IF NOT EXISTS idx_kap_category
    ON kap_events(category);
"""

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
        conn.executescript(KAP_SCHEMA_SQL)
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


def sync_portfolio(positions: dict | list) -> None:
    """Sync portfolio positions from config into DB."""
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")

    # Handle both dict format (ticker: {lots, avg_cost}) and list format
    pos_list = []
    if isinstance(positions, dict):
        pos_list = [
            {"ticker": ticker, "quantity": data.get("lots", 0), "avg_cost": data.get("avg_cost", 0)}
            for ticker, data in positions.items()
        ]
    else:
        pos_list = positions

    with get_connection() as conn:
        for pos in pos_list:
            conn.execute(
                "INSERT OR REPLACE INTO portfolio (ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?)",
                (pos["ticker"], pos["quantity"], pos["avg_cost"], now),
            )
    logger.info("Portfolio synced: %d positions", len(pos_list))


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


def upsert_kap_events(events: list) -> int:
    """Insert KapEvent list into kap_events table (INSERT OR IGNORE on duplicate index).

    Returns: number of newly inserted rows.
    """
    import json

    if not events:
        return 0

    rows = []
    for ev in events:
        rows.append((
            ev.disclosure_index,
            ev.symbol,
            ev.published_at.isoformat(),
            ev.fetched_at.isoformat(),
            ev.subject,
            ev.category,
            ev.summary,
            ev.url,
            ev.source_type,
            json.dumps(ev.structured_data) if ev.structured_data else None,
            1 if ev.has_attachment else 0,
            json.dumps(ev.attachment_urls) if ev.attachment_urls else None,
        ))

    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM kap_events").fetchone()[0]
        conn.executemany(
            """INSERT OR IGNORE INTO kap_events
               (disclosure_index, symbol, published_at, fetched_at, subject, category,
                summary, url, source_type, structured_data, has_attachment, attachment_urls)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        after = conn.execute("SELECT COUNT(*) FROM kap_events").fetchone()[0]

    inserted = after - before
    logger.info("kap_events: inserted %d new rows (skipped %d duplicates)", inserted, len(rows) - inserted)
    return inserted


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

import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.logger import setup_logger
from src.utils.config import get_db_path

logger = setup_logger(__name__)

MACRO_TICKERS = {
    "USDTRY": "TRY=X",
    "BRENT": "BZ=F",
    "VIX": "^VIX",
    "BIST100": "XU100.IS",
}

SCHEMA_PATH = Path(__file__).parent / "db" / "schema.sql"


def _init_macro_db(db_path: str) -> None:
    """Initialize macro_data table if not exists."""
    if not SCHEMA_PATH.exists():
        logger.warning(f"Schema file not found: {SCHEMA_PATH}")
        return

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
        conn.commit()
    logger.debug(f"Macro data schema initialized: {db_path}")


def fetch_macro_snapshot(
    tickers: dict[str, str] = None,
    period: str = "1d"
) -> pd.DataFrame:
    """
    Fetch latest macro data snapshot from Yahoo Finance.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """
    if tickers is None:
        tickers = MACRO_TICKERS

    results = []

    for name, ticker in tickers.items():
        try:
            logger.debug(f"Fetching {name} ({ticker}) snapshot...")
            data = yf.Ticker(ticker).history(period=period, auto_adjust=True)

            if data.empty:
                logger.warning(f"No data for {name}")
                continue

            latest = data.iloc[-1]
            date_str = str(data.index[-1].date())

            results.append({
                "date": date_str,
                "symbol": name,
                "open": float(latest.get("Open", 0.0)) if pd.notna(latest.get("Open")) else None,
                "high": float(latest.get("High", 0.0)) if pd.notna(latest.get("High")) else None,
                "low": float(latest.get("Low", 0.0)) if pd.notna(latest.get("Low")) else None,
                "close": float(latest.get("Close", 0.0)) if pd.notna(latest.get("Close")) else 0.0,
                "volume": int(latest.get("Volume", 0)) if pd.notna(latest.get("Volume")) else 0,
            })
            logger.debug(f"  ✓ {name}: {latest.get('Close', 'N/A')}")

        except Exception as e:
            logger.error(f"Failed to fetch {name}: {e}")
            continue

    if not results:
        logger.warning("No macro data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df


def fetch_macro_history(
    tickers: dict[str, str] = None,
    start: str = "2020-01-01",
    end: str | None = None
) -> pd.DataFrame:
    """
    Fetch historical macro data for specified date range.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """
    if tickers is None:
        tickers = MACRO_TICKERS

    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    results = []

    for name, ticker in tickers.items():
        try:
            logger.debug(f"Fetching {name} ({ticker}) history {start}–{end}...")
            data = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)

            if data.empty:
                logger.warning(f"No history for {name}")
                continue

            for date_idx, row in data.iterrows():
                date_str = str(date_idx.date())
                results.append({
                    "date": date_str,
                    "symbol": name,
                    "open": float(row.get("Open")) if pd.notna(row.get("Open")) else None,
                    "high": float(row.get("High")) if pd.notna(row.get("High")) else None,
                    "low": float(row.get("Low")) if pd.notna(row.get("Low")) else None,
                    "close": float(row.get("Close")) if pd.notna(row.get("Close")) else 0.0,
                    "volume": int(row.get("Volume")) if pd.notna(row.get("Volume")) else 0,
                })

            logger.debug(f"  ✓ {name}: {len(data)} rows")

        except Exception as e:
            logger.error(f"Failed to fetch history for {name}: {e}")
            continue

    if not results:
        logger.warning("No historical data fetched")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df


def save_to_db(
    df: pd.DataFrame,
    db_path: str = None,
    table: str = "macro_data"
) -> int:
    """
    Save/upsert macro data to SQLite.
    Returns: number of rows inserted/updated
    """
    if df.empty:
        logger.warning("Empty DataFrame, nothing to save")
        return 0

    if db_path is None:
        db_path = get_db_path()

    _init_macro_db(db_path)

    saved_count = 0

    with sqlite3.connect(db_path) as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(
                    f"""
                    INSERT OR REPLACE INTO {table}
                    (date, symbol, open, high, low, close, volume, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        row["date"],
                        row["symbol"],
                        row.get("open"),
                        row.get("high"),
                        row.get("low"),
                        row["close"],
                        row.get("volume", 0),
                    ),
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save row {row['symbol']} {row['date']}: {e}")
                continue

        conn.commit()

    logger.info(f"Saved {saved_count} macro data rows to {db_path}")
    return saved_count


def load_from_db(
    symbols: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    db_path: str = None,
) -> pd.DataFrame:
    """
    Load macro data from SQLite with optional filters.
    Returns: DataFrame [date, symbol, open, high, low, close, volume]
    """
    if db_path is None:
        db_path = get_db_path()

    if not Path(db_path).exists():
        logger.warning(f"Database not found: {db_path}")
        return pd.DataFrame()

    query = "SELECT date, symbol, open, high, low, close, volume FROM macro_data WHERE 1=1"
    params = []

    if symbols:
        placeholders = ",".join("?" * len(symbols))
        query += f" AND symbol IN ({placeholders})"
        params.extend(symbols)

    if start:
        query += " AND date >= ?"
        params.append(start)

    if end:
        query += " AND date <= ?"
        params.append(end)

    query += " ORDER BY date DESC, symbol ASC"

    try:
        df = pd.read_sql_query(query, sqlite3.connect(db_path), params=params)
        logger.debug(f"Loaded {len(df)} rows from macro_data")
        return df
    except Exception as e:
        logger.error(f"Failed to load from database: {e}")
        return pd.DataFrame()


def get_latest_snapshot(db_path: str = None) -> pd.DataFrame:
    """
    Get latest price snapshot for each symbol with 1-day % change.
    Returns: DataFrame [symbol, date, close, pct_change_1d]
    """
    if db_path is None:
        db_path = get_db_path()

    if not Path(db_path).exists():
        logger.warning(f"Database not found: {db_path}")
        return pd.DataFrame()

    query = """
    SELECT
        symbol,
        date,
        close,
        (SELECT close FROM macro_data m2
         WHERE m2.symbol = m1.symbol
         AND m2.date < m1.date
         ORDER BY m2.date DESC
         LIMIT 1) as prev_close
    FROM macro_data m1
    WHERE (symbol, date) IN (
        SELECT symbol, MAX(date) FROM macro_data GROUP BY symbol
    )
    ORDER BY symbol
    """

    try:
        df = pd.read_sql_query(query, sqlite3.connect(db_path))

        if df.empty:
            return pd.DataFrame()

        df["pct_change_1d"] = 0.0
        for idx, row in df.iterrows():
            if row["prev_close"] and row["prev_close"] != 0:
                pct = ((row["close"] - row["prev_close"]) / row["prev_close"]) * 100
                df.at[idx, "pct_change_1d"] = round(pct, 2)

        return df[["symbol", "date", "close", "pct_change_1d"]]

    except Exception as e:
        logger.error(f"Failed to get latest snapshot: {e}")
        return pd.DataFrame()

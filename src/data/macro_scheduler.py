import schedule
import time
from datetime import datetime
from pathlib import Path

from src.utils.logger import setup_logger
from src.utils.config import get_db_path
from src.data.macro_feed import fetch_macro_snapshot, save_to_db

logger = setup_logger(__name__)


def run_daily_update(
    db_path: str = None,
    log_path: str = "logs/macro_feed.log",
) -> dict:
    """
    Daily update job: fetch macro snapshot and save to DB.
    Returns: {"updated_rows": int, "symbols": list, "timestamp": str, "errors": list}
    """
    if db_path is None:
        db_path = get_db_path()

    timestamp = datetime.now().isoformat(timespec="seconds")
    errors = []
    symbols = []

    logger.info(f"Starting daily macro data update ({timestamp})")

    try:
        df = fetch_macro_snapshot()

        if df.empty:
            errors.append("No macro data fetched")
            logger.warning("Fetch returned empty DataFrame")
        else:
            symbols = df["symbol"].tolist()
            updated_rows = save_to_db(df, db_path=db_path)
            logger.info(f"Updated {updated_rows} rows for {len(symbols)} symbols")

    except Exception as e:
        errors.append(f"Fetch error: {str(e)}")
        logger.error(f"Daily update failed: {e}")

    result = {
        "updated_rows": len(df) if not df.empty else 0,
        "symbols": symbols,
        "timestamp": timestamp,
        "errors": errors,
    }

    # Log result
    log_line = f"[{timestamp}] rows={result['updated_rows']} symbols={','.join(symbols)} errors={len(errors)}\n"
    try:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        logger.error(f"Failed to write log: {e}")

    return result


def schedule_daily(
    run_time: str = "18:30",
    db_path: str = None,
) -> None:
    """
    Schedule daily macro data update using schedule library.
    Blocks: runs event loop until cancelled.
    """
    if db_path is None:
        db_path = get_db_path()

    logger.info(f"Scheduling daily macro update at {run_time}")

    schedule.every().day.at(run_time).do(run_daily_update, db_path=db_path)

    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


def backfill_missing(
    db_path: str = None,
    start: str = "2020-01-01",
) -> int:
    """
    Detect and fill missing dates in macro data.
    Returns: number of rows added
    """
    if db_path is None:
        db_path = get_db_path()

    from src.data.macro_feed import fetch_macro_history, load_from_db, save_to_db

    logger.info(f"Backfilling macro data from {start}")

    # Fetch historical data
    df_hist = fetch_macro_history(start=start)

    if df_hist.empty:
        logger.warning("No historical data to backfill")
        return 0

    # Load existing data
    df_existing = load_from_db(db_path=db_path)

    if df_existing.empty:
        # All data is new
        saved = save_to_db(df_hist, db_path=db_path)
        logger.info(f"Backfilled {saved} new rows")
        return saved

    # Find missing (date, symbol) pairs
    existing_keys = set(zip(df_existing["date"], df_existing["symbol"]))
    hist_keys = set(zip(df_hist["date"], df_hist["symbol"]))
    missing_keys = hist_keys - existing_keys

    if not missing_keys:
        logger.info("No missing data to backfill")
        return 0

    # Filter historical data to only missing rows
    df_missing = df_hist[
        df_hist.apply(lambda r: (r["date"], r["symbol"]) in missing_keys, axis=1)
    ]

    saved = save_to_db(df_missing, db_path=db_path)
    logger.info(f"Backfilled {saved} missing rows")
    return saved

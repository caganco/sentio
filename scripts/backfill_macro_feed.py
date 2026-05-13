"""Backfill macro feed with 30 days of historical data."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.macro_feed import fetch_macro_history, save_to_db
from src.utils.logger import setup_logger

logger = setup_logger("backfill_macro_feed")

if __name__ == "__main__":
    logger.info("=== Backfill Macro Feed (30 Days) ===")

    # Calculate date range: last 30 days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    logger.info(f"Fetching historical data: {start_date} to {end_date}")

    # Fetch all symbols for last 30 days
    df = fetch_macro_history(start=start_date, end=end_date)

    if df.empty:
        logger.error("No data fetched")
        sys.exit(1)

    logger.info(f"Fetched {len(df)} rows")
    print(f"\nData preview (first 10 rows):")
    print(df.head(10).to_string())
    print(f"\nDate range in data:")
    print(f"  Start: {df['date'].min()}")
    print(f"  End:   {df['date'].max()}")
    print(f"  Symbols: {', '.join(df['symbol'].unique())}")

    # Save to database
    saved = save_to_db(df)
    logger.info(f"Saved {saved} rows to database")

    print(f"\n[OK] Backfill complete: {saved} rows saved")

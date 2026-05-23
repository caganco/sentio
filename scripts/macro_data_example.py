"""Example: Fetch and manage macro data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.macro_feed import (
    fetch_macro_snapshot,
    fetch_macro_history,
    save_to_db,
    load_from_db,
    get_latest_snapshot,
)
from src.data.macro_scheduler import run_daily_update
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("Macro Data Feed Example")
    logger.info("=" * 70)

    # 1. Fetch latest snapshot
    logger.info("\n[1] Fetching latest macro data snapshot...")
    snapshot = fetch_macro_snapshot()
    print(snapshot)

    # 2. Save to database
    logger.info("\n[2] Saving snapshot to database...")
    rows = save_to_db(snapshot)
    print(f"Saved {rows} rows")

    # 3. Load and display latest prices
    logger.info("\n[3] Getting latest snapshot from database...")
    latest = get_latest_snapshot()
    print(latest)

    # 4. Fetch historical data
    logger.info("\n[4] Fetching historical data (2024-01-01 to 2024-01-31)...")
    history = fetch_macro_history(start="2024-01-01", end="2024-01-31")
    print(f"Fetched {len(history)} historical data points")

    # 5. Load data with filters
    logger.info("\n[5] Loading USD/TRY data from database...")
    usdtry = load_from_db(symbols=["USDTRY"])
    print(f"Found {len(usdtry)} USD/TRY records")

    # 6. Run daily update job
    logger.info("\n[6] Running daily update job...")
    result = run_daily_update()
    print(f"Update result: {result}")

    logger.info("\n" + "=" * 70)
    logger.info("Example complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

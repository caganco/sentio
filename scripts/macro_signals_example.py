"""Example: Generate and save macro signals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.signals.macro_signals import (
    generate_macro_signal,
    save_signal_json,
)
from src.data.macro_feed import fetch_macro_snapshot, save_to_db
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("=" * 70)
    logger.info("Macro Signals Example")
    logger.info("=" * 70)

    # 1. Fetch latest macro data
    logger.info("\n[1] Fetching latest macro data...")
    snapshot = fetch_macro_snapshot()
    print(snapshot)

    if snapshot.empty:
        logger.warning("No macro data available")
        return

    # 2. Save to database
    logger.info("\n[2] Saving to database...")
    rows = save_to_db(snapshot)
    print(f"Saved {rows} rows")

    # 3. Generate macro signal
    logger.info("\n[3] Generating macro signal...")
    signal = generate_macro_signal()
    print(f"Regime: {signal.regime}")
    print(f"Macro Environment Score: {signal.macro_environment_score:.3f}")
    print(f"Component Scores:")
    print(f"  VIX:     {signal.vix_score:.3f}")
    print(f"  USDTRY:  {signal.usdtry_score:.3f}")
    print(f"  BRENT:   {signal.brent_score:.3f}")
    print(f"  BIST100: {signal.bist100_score:.3f}")
    print(f"Latest Prices:")
    for symbol, price in signal.symbols.items():
        print(f"  {symbol}: {price:.2f}")

    # 4. Save signal to JSON
    logger.info("\n[4] Saving signal to JSON...")
    filepath = save_signal_json(signal)
    print(f"Saved: {filepath}")

    logger.info("\n" + "=" * 70)
    logger.info("Example complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

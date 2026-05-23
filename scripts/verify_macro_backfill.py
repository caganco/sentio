"""Verify backfilled macro data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.macro_feed import load_from_db
from src.utils.config import get_db_path
from src.utils.logger import setup_logger

logger = setup_logger("verify_macro_backfill")

if __name__ == "__main__":
    df = load_from_db(db_path=get_db_path())

    print(f"\n{'='*60}")
    print(f"  MACRO FEED BACKFILL VERIFICATION")
    print(f"{'='*60}")
    print(f"\nTotal rows in database: {len(df)}")
    print(f"\nRows per symbol:")
    for symbol in sorted(df['symbol'].unique()):
        count = len(df[df['symbol'] == symbol])
        print(f"  {symbol:<10} {count:>3} rows")

    print(f"\nDate range: {df['date'].min()} to {df['date'].max()}")

    print(f"\nLatest data by symbol:")
    latest = df.sort_values('date', ascending=False).drop_duplicates('symbol')[['symbol', 'date', 'close']].sort_values('symbol')
    for _, row in latest.iterrows():
        print(f"  {row['symbol']:<10} {row['date']}  {row['close']:>10.2f}")

    print(f"\n{'='*60}\n")

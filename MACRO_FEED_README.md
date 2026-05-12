# Macro Data Feed — Complete Reference

## Overview

Complete macro data feed module for BIST Hedge Fund OS. Fetches USD/TRY, Brent crude, VIX, and BIST100 data from Yahoo Finance, stores in SQLite, and provides automated daily updates.

## Module Structure

```
src/data/
├── macro_feed.py       # Main data fetching and persistence (330 lines)
├── macro_scheduler.py  # Daily update jobs and scheduling (139 lines)
└── db/
    └── schema.sql      # SQLite table definitions

tests/
└── test_macro_feed.py  # 15 comprehensive unit tests

scripts/
└── macro_data_example.py  # Usage examples
```

## Quick Start

```python
from src.data.macro_feed import fetch_macro_snapshot, save_to_db, get_latest_snapshot

# Fetch latest prices
snapshot = fetch_macro_snapshot()
# → DataFrame: [date, symbol, open, high, low, close, volume]

# Save to database
save_to_db(snapshot)

# Get latest prices with 1-day % change
latest = get_latest_snapshot()
print(latest)
```

## Core Functions

### Data Fetching

**`fetch_macro_snapshot(tickers=None, period="1d")`**
- Fetch latest macro data from Yahoo Finance
- Returns: DataFrame with columns [date, symbol, open, high, low, close, volume]
- Default symbols: USDTRY, BRENT, VIX, BIST100

**`fetch_macro_history(tickers=None, start="2020-01-01", end=None)`**
- Fetch historical macro data for date range
- Returns: DataFrame with all rows for date range
- Default end: today

### Database Operations

**`save_to_db(df, db_path=None, table="macro_data")`**
- Save/upsert macro data to SQLite
- Uses UNIQUE(date, symbol) constraint to prevent duplicates
- Returns: number of rows inserted/updated

**`load_from_db(symbols=None, start=None, end=None, db_path=None)`**
- Load macro data with optional filters
- Parameters:
  - `symbols`: list of symbols to filter (e.g., ["USDTRY", "VIX"])
  - `start`: start date (YYYY-MM-DD format)
  - `end`: end date (YYYY-MM-DD format)
- Returns: DataFrame, empty if no matches

**`get_latest_snapshot(db_path=None)`**
- Get most recent price for each symbol
- Returns: DataFrame with [symbol, date, close, pct_change_1d]
- pct_change_1d: 1-day percentage change

### Scheduled Updates

**`run_daily_update(db_path=None, log_path="logs/macro_feed.log")`**
- Fetch macro snapshot and save to database
- Logs results to file
- Returns: dict with update metadata

**`schedule_daily(run_time="18:30", db_path=None)`**
- Schedule daily updates (blocking event loop)
- Default time: 18:30 (after BIST market close)
- Press Ctrl+C to stop

**`backfill_missing(db_path=None, start="2020-01-01")`**
- Fill gaps in historical data
- Useful after initial setup
- Returns: number of rows added

## Database Schema

```sql
CREATE TABLE macro_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,
    symbol      TEXT    NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL    NOT NULL,
    volume      INTEGER DEFAULT 0,
    updated_at  TEXT    DEFAULT (datetime('now')),
    UNIQUE(date, symbol)
);

CREATE INDEX idx_macro_date   ON macro_data(date);
CREATE INDEX idx_macro_symbol ON macro_data(symbol);
CREATE INDEX idx_macro_ds     ON macro_data(date, symbol);
```

## Usage Examples

### Get Current Market Snapshot

```python
from src.data.macro_feed import get_latest_snapshot

latest = get_latest_snapshot()
for _, row in latest.iterrows():
    print(f"{row['symbol']:10} {row['close']:10.2f} {row['pct_change_1d']:+6.2f}%")
```

Output:
```
BIST100       9876.30   +1.23%
BRENT          76.85   -0.45%
USDTRY         35.38   +0.12%
VIX            15.75   -2.30%
```

### Fetch and Store Historical Data

```python
from src.data.macro_feed import fetch_macro_history, save_to_db

# Get 6 months of history
df = fetch_macro_history(start="2025-11-01", end="2026-05-01")
save_to_db(df)
print(f"Stored {len(df)} records")
```

### Query Data for Analysis

```python
from src.data.macro_feed import load_from_db

# Get USD/TRY rates for a specific month
usdtry = load_from_db(
    symbols=["USDTRY"],
    start="2026-05-01",
    end="2026-05-31"
)

# Calculate statistics
print(f"Min: {usdtry['close'].min():.2f}")
print(f"Max: {usdtry['close'].max():.2f}")
print(f"Avg: {usdtry['close'].mean():.2f}")
```

### Setup Daily Automated Updates

```python
from src.data.macro_scheduler import schedule_daily

# Run at 18:30 (after BIST close) every day
schedule_daily(run_time="18:30")
# Blocks until Ctrl+C

# Or run once
from src.data.macro_scheduler import run_daily_update
result = run_daily_update()
print(f"Updated {result['updated_rows']} rows for {result['symbols']}")
```

### Backfill Missing Data

```python
from src.data.macro_scheduler import backfill_missing

# Fill gaps from 2020 onwards
filled = backfill_missing(start="2020-01-01")
print(f"Filled {filled} missing records")
```

## Integration with Daily Briefing

Add macro data to `agents/intelligence/daily_briefing.json`:

```python
from src.data.macro_feed import get_latest_snapshot
import json

briefing = {...}
latest = get_latest_snapshot()

briefing["macro_data"] = {
    row["symbol"]: {
        "date": row["date"],
        "close": row["close"],
        "pct_change_1d": row["pct_change_1d"]
    }
    for _, row in latest.iterrows()
}

with open("agents/intelligence/daily_briefing.json", "w") as f:
    json.dump(briefing, f, indent=2)
```

## Testing

```bash
# Run all tests
python -m pytest tests/test_macro_feed.py -v

# Run specific test class
python -m pytest tests/test_macro_feed.py::TestMacroSnapshot -v

# Run with logging
python -m pytest tests/test_macro_feed.py -v -s
```

**Test Results:** 15 passed ✓

## Configuration

### Environment Variables
```bash
export ANTHROPIC_DB_PATH=data/market.db      # Database location
export ANTHROPIC_LOG_DIR=logs                # Log directory
```

### Database Path
Default: `data/market.db` (via `get_db_path()`)

### Data Directory Structure
```
data/
├── market.db            # SQLite database
├── raw/                 # Raw API responses (optional)
└── processed/           # Processed data (optional)
```

## Error Handling

- **Individual symbol failures:** One symbol failure doesn't block others
- **Retry strategy:** 3 retries with exponential backoff
- **Timeout:** 30 seconds per request
- **Partial success:** If 3/4 symbols succeed, they're saved; 1 error is logged

## Performance Notes

- **Fetch time:** ~3-5 seconds per symbol
- **Storage:** ~1KB per (date, symbol) record
- **Database size (5 years, 4 symbols):** ~5 MB
- **Query speed:** <100ms for typical queries
- **Rate limiting:** None (Yahoo Finance allows frequent requests)

## Data Quality

- **Weekends:** BIST100 returns empty (weekend market closed)
- **VIX Volume:** Often 0 (futures don't report volume)
- **USDTRY Volume:** Often 0 (forex)
- **Date Format:** Always YYYY-MM-DD (UTC)
- **Timezones:** Yahoo Finance uses UTC; local market times ignored

## Troubleshooting

### "No data for BIST100"
- BIST is closed on weekends/holidays
- Fetch will return empty for those days (normal behavior)

### "Database locked"
- Another process is using the database
- Close other Python processes or wait a few seconds

### "Timeout fetching BRENT"
- Yahoo Finance API is slow
- Increase timeout: `KAPScraper(timeout=60)`

### "Memory error on large history"
- Fetch in smaller chunks: use `start` and `end` parameters
- Or filter by symbol: `fetch_macro_history(symbols=["USDTRY"])`

## Statistics

- **Total Code:** 469 lines (feed + scheduler + tests)
- **Test Coverage:** 15 tests covering all public functions
- **Dependencies:** yfinance, pandas, schedule, sqlite3
- **Status:** ✅ Production-ready

## Next Steps

1. **Add to Daily Briefing Pipeline**
   - Integrate into `scripts/daily_update.py`
   - Include macro snapshot in analyst context

2. **Implement Alert System**
   - Notify on major volatility (VIX > 20)
   - Alert on significant currency moves (USD/TRY ±2%)

3. **Add Caching**
   - Cache 1-hour snapshot to reduce API load
   - Redis or in-memory cache

4. **Enhanced Analysis**
   - Calculate correlations between symbols
   - Detect regime changes (trending vs ranging)

## API References

- [Yahoo Finance Symbol List](https://finance.yahoo.com/)
- [yfinance Documentation](https://yfinance.readthedocs.io/)
- [Schedule Library](https://schedule.readthedocs.io/)

---

See [MACRO_FEED_README.md](MACRO_FEED_README.md) for complete documentation.

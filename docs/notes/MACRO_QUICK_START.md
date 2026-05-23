# Macro Data Feed — Quick Start

## Installation

Dependencies already installed. Database is auto-created on first use.

## Basic Usage (Copy & Paste)

```python
from src.data.macro_feed import fetch_macro_snapshot, save_to_db, get_latest_snapshot

# 1. Fetch latest prices (USDTRY, BRENT, VIX, BIST100)
snapshot = fetch_macro_snapshot()
print(snapshot)

# 2. Save to database
save_to_db(snapshot)

# 3. Get latest with % change
latest = get_latest_snapshot()
for _, row in latest.iterrows():
    print(f"{row['symbol']:10} {row['close']:10.2f} {row['pct_change_1d']:+6.2f}%")
```

## Common Operations

### Get Latest Prices
```python
from src.data.macro_feed import get_latest_snapshot

latest = get_latest_snapshot()
# → DataFrame: [symbol, date, close, pct_change_1d]
```

### Fetch Historical Data
```python
from src.data.macro_feed import fetch_macro_history, save_to_db

# Get 2024 data
df = fetch_macro_history(start="2024-01-01", end="2024-12-31")
save_to_db(df)
```

### Query Database
```python
from src.data.macro_feed import load_from_db

# Get USD/TRY for last 30 days
usdtry = load_from_db(
    symbols=["USDTRY"],
    start="2026-04-13",
    end="2026-05-13"
)

# Statistics
print(f"Min:  {usdtry['close'].min():.2f}")
print(f"Max:  {usdtry['close'].max():.2f}")
print(f"Avg:  {usdtry['close'].mean():.2f}")
```

### Run Daily Update
```python
from src.data.macro_scheduler import run_daily_update

result = run_daily_update()
print(f"Updated {result['updated_rows']} rows")
print(f"Symbols: {result['symbols']}")
print(f"Errors: {result['errors']}")
```

### Schedule Daily Job
```python
from src.data.macro_scheduler import schedule_daily

# Run every day at 18:30 (after BIST close)
schedule_daily(run_time="18:30")  # Blocks until Ctrl+C
```

### Backfill Historical Data
```python
from src.data.macro_scheduler import backfill_missing

# Fill gaps from 2020 onwards
filled = backfill_missing(start="2020-01-01")
print(f"Filled {filled} missing records")
```

## Available Symbols

| Symbol | Description | Volume | Weekends |
|--------|-------------|--------|----------|
| USDTRY | US Dollar / Turkish Lira | 0 | No |
| BRENT | Brent Crude Oil | Yes | Sometimes |
| VIX | Volatility Index | 0 | No |
| BIST100 | Istanbul Stock Exchange | Yes | No |

## Integration with Analyst

```python
# In daily_briefing.json:
from src.data.macro_feed import get_latest_snapshot

briefing["macro_snapshot"] = {}
latest = get_latest_snapshot()
for _, row in latest.iterrows():
    briefing["macro_snapshot"][row["symbol"]] = {
        "date": row["date"],
        "close": row["close"],
        "change": row["pct_change_1d"]
    }
```

Then in analyst prompt:
```
Makro Veri (En son):
- USDTRY: 45.39 (+0.12%)
- BRENT: 107.41 (-0.45%)
- VIX: 17.99 (-2.30%)
- BIST100: 14780 (+1.23%)
```

## Testing

```bash
# All tests
python -m pytest tests/test_macro_feed.py -v

# Specific test
python -m pytest tests/test_macro_feed.py::TestMacroSnapshot -v

# Example script
python scripts/macro_data_example.py
```

**Status:** 15/15 tests passing ✅

## Database

- **Location:** `data/bist_data.db` (auto-created)
- **Size:** ~1KB per record
- **5 years, 4 symbols:** ~5MB
- **Auto-indexed:** date, symbol, (date, symbol)

## Troubleshooting

### "No data for BIST100"
- BIST is closed on weekends/holidays
- This is normal — fetch returns empty for those dates

### "Timeout"
- Yahoo Finance is slow
- Run later or increase timeout

### "Database locked"
- Another process is using the database
- Close other Python sessions

### "Connection refused"
- Check internet connection
- Yahoo Finance API might be down

## Notes

- Dates always stored as `YYYY-MM-DD` (UTC)
- Upsert prevents duplicates (same date + symbol)
- 3 retries with exponential backoff on failure
- Logs to file with timestamp

## Files

- `src/data/macro_feed.py` — Main module (330 lines)
- `src/data/macro_scheduler.py` — Scheduling (139 lines)
- `src/data/db/schema.sql` — Database schema
- `tests/test_macro_feed.py` — 15 unit tests
- `scripts/macro_data_example.py` — Usage examples

---

See [MACRO_FEED_README.md](MACRO_FEED_README.md) for full documentation.

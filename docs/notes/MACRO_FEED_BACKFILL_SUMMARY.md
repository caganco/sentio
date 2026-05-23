# Macro Feed Backfill Summary — May 13, 2026

## Overview

Successfully backfilled macro feed with 30 days of historical data using `fetch_macro_history()` function. All 4 symbols now have trading history from April 13 to May 13, 2026.

## Backfill Process

**Script:** `scripts/backfill_macro_feed.py`

**Method:**
1. Calculated 30-day lookback: 2026-04-13 to 2026-05-13
2. Called `fetch_macro_history(start="2026-04-13", end="2026-05-13")`
3. Saved all rows to SQLite database via `save_to_db()`

**Execution:**
```bash
python scripts/backfill_macro_feed.py
```

## Results

### Data Summary

| Metric | Value |
|--------|-------|
| **Total rows** | 87 |
| **Date range** | 2026-04-13 to 2026-05-13 |
| **Symbols** | USDTRY, BRENT, VIX, BIST100 |
| **Time to fetch** | ~1 second |
| **Time to save** | <100ms |

### Rows Per Symbol

| Symbol  | Rows |
|---------|------|
| USDTRY  | 23   |
| BRENT   | 22   |
| VIX     | 22   |
| BIST100 | 20   |
| **TOTAL** | **87** |

### Latest Values (2026-05-13)

```
Symbol      Date        Price      
------      ----        -----      
USDTRY      2026-05-13  45.39      
BRENT       2026-05-12  107.48     
VIX         2026-05-12  17.99      
BIST100     2026-05-12  14779.93   
```

## Macro Signals Generated

With backfilled data, `daily_update.py --generate-report` now generates **meaningful signals** based on historical context:

### Generated Signal (2026-05-13)

**File:** `agents/intelligence/macro_signal_2026-05-13.json`

```json
{
  "timestamp": "2026-05-13T00:04:11.310320Z",
  "regime": "TRANSITION",
  "macro_environment_score": -0.169,
  "components": {
    "usdtry": -0.010,
    "brent": +0.628,
    "vix": -0.424,
    "bist100": -0.467
  },
  "prices": {
    "usdtry": 45.41,
    "brent": 107.48,
    "vix": 17.99,
    "bist100": 14779.93
  },
  "data_date": "2026-05-13"
}
```

### Signal Interpretation

**Regime:** TRANSITION (macro_score: -0.169)
- Mixed market signals
- Conflicting sentiment across components

**Component Analysis:**
- **BRENT +0.628** — Strong energy demand signal (oil up)
- **USDTRY -0.010** — Neutral currency (TRY stable)
- **VIX -0.424** — Volatility elevated (risk aversion)
- **BIST100 -0.467** — Equity weakness (market decline)

**Interpretation:**
- Energy demand remains strong (BRENT up)
- But equities and volatility show risk-off sentiment
- TRY stable, suggesting balanced currency flows
- Overall: Risk-off bias, requires caution

## Database State

**Location:** `data/bist_data.db`

**Tables:**
- `macro_data` — 87 rows with 30 days of OHLCV data
- `portfolio_prices` — Historical stock prices (5797 rows)
- `portfolio` — 5 positions

**Query for latest macro snapshot:**
```python
from src.data.macro_feed import get_latest_snapshot
df = get_latest_snapshot()  # Returns latest price + 1d % change for each symbol
```

## Daily Update Integration

Running `daily_update.py --generate-report` now:

1. **Fetches today's macro data** (USDTRY, BRENT, VIX, BIST100)
2. **Saves to database** alongside historical data
3. **Generates macro signal** comparing to previous day
4. **Displays MACRO SNAPSHOT** section in console:
   ```
   Regime: TRANSITION
   Environment Score: -0.169 ([-1, +1])
   Symbol              Price    Score
   USDTRY              45.41  -0.010
   BRENT              107.48  +0.628
   VIX                 17.99  -0.424
   BIST100          14779.93  -0.467
   ```
5. **Saves to daily_briefing.json** with macro_snapshot section
6. **Creates macro_signal_YYYY-MM-DD.json** for archival

## Next Steps

### Optional Enhancements

1. **Signal History Analysis**
   - Keep daily macro_signal_*.json files
   - Analyze regime persistence (days in RISK_ON vs RISK_OFF)
   - Track macro environment score over time

2. **Alerts**
   - Alert on regime changes (RISK_ON → RISK_OFF)
   - Notify on extreme scores (|macro_score| > 0.7)
   - Track 5-day moving average of signal

3. **Correlation Analysis**
   - Compare portfolio returns vs macro regime
   - Identify which stocks perform best in RISK_ON
   - Which defend best in RISK_OFF

4. **Analyst Integration**
   - Pass macro_snapshot to analyst system prompt
   - Condition recommendations on regime
   - Adjust risk levels based on macro environment

## Files Modified/Created

**Created:**
- `scripts/backfill_macro_feed.py` — Backfill script
- `scripts/verify_macro_backfill.py` — Verification script
- `MACRO_FEED_BACKFILL_SUMMARY.md` — This document

**Modified:**
- `data/bist_data.db` — Now contains 87 macro data rows (was 4)

**Generated:**
- `agents/intelligence/macro_signal_2026-05-13.json` — Daily signal (with backfilled history)
- `agents/intelligence/daily_briefing.json` — Updated with macro_snapshot

## Performance

| Operation | Time |
|-----------|------|
| Fetch 30d × 4 symbols | ~1s |
| Save 87 rows to DB | ~100ms |
| Generate signal | ~200ms |
| Save JSON | <10ms |
| **Total macro operations** | **~1.3s** |

Daily update total time: ~10-15 seconds (unchanged)

## Verification

Run verification at any time:
```bash
python scripts/verify_macro_backfill.py
```

Expected output:
```
Total rows in database: 87
Rows per symbol:
  BIST100     20 rows
  BRENT       22 rows
  USDTRY      23 rows
  VIX         22 rows
Date range: 2026-04-13 to 2026-05-13
```

## Status

✅ **Complete**
- 30-day historical data backfilled
- 87 rows saved to database
- Macro signals generated with historical context
- Daily update integrated and working
- Verification scripts provided

---

**Date:** 2026-05-13  
**Backfill Period:** 2026-04-13 to 2026-05-13 (30 days)  
**Status:** ✅ Complete  
**Rows Saved:** 87  
**All Symbols Covered:** USDTRY, BRENT, VIX, BIST100  

# KAP Scraper — Quick Start

## Basic Usage (Copy & Paste)

```python
from src.scrapers.kap_scraper import KAPScraper

# Initialize scraper (rate-limited, auto-retry)
scraper = KAPScraper(delay=1.5, timeout=30)

# Get all BIST companies (cached)
companies = scraper.get_company_list()
# → [{"ticker": "THYAO", "name": "...", "kap_id": "..."}, ...]

# Financial reports for a ticker
disclosures = scraper.get_financial_disclosures("THYAO", year=2024, limit=5)
# → [FinancialDisclosure(...), ...]

# Material events/announcements
specials = scraper.get_special_disclosures("THYAO", limit=10)
# → [SpecialDisclosure(...), ...]

# Get detailed financial statements (balance sheet, income, cash flow)
if disclosures:
    tables = scraper.get_financial_tables(disclosures[0].disclosure_id)
    # → FinancialTables(balance_sheet={...}, income_statement={...}, ...)
```

## Common Patterns

### Fetch Latest Financial Data for All Portfolio Tickers
```python
from src.scrapers.kap_scraper import KAPScraper
from src.utils.config import load_config

config = load_config()
portfolio_tickers = [p["ticker"] for p in config["portfolio"]["positions"]]

scraper = KAPScraper()
latest_reports = {}

for ticker in portfolio_tickers:
    disclosures = scraper.get_financial_disclosures(ticker, limit=1)
    if disclosures:
        latest_reports[ticker] = disclosures[0]
        print(f"{ticker}: {disclosures[0].period}")
```

### Find Material Events (Last 30 Days)
```python
from datetime import datetime, timedelta

start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
specials = scraper.get_special_disclosures("THYAO", start_date=start)

for s in specials:
    if s.is_material:
        print(f"[MATERIAL] {s.title} on {s.disclosure_date.date()}")
```

### Extract Financial Metrics
```python
tables = scraper.get_financial_tables(disclosure_id)

# Get total assets (first balance sheet item usually)
assets = tables.balance_sheet.get("Toplam Varlıklar", {})
print(f"Total Assets: {assets.get(tables.period)}")

# Get revenue
revenue = tables.income_statement.get("Hasılat", {})
print(f"Revenue: {revenue.get(tables.period)}")
```

## Customization

### Adjust Rate Limiting
```python
# Faster (less polite, may get rate-limited)
scraper = KAPScraper(delay=0.5)

# Slower (more polite, safer)
scraper = KAPScraper(delay=3.0)
```

### Adjust Timeout
```python
# For slow networks
scraper = KAPScraper(timeout=60)

# For fast networks
scraper = KAPScraper(timeout=10)
```

### Adjust Retries
```python
# More retries for unstable connections
scraper = KAPScraper(max_retries=5)

# Fewer retries for testing
scraper = KAPScraper(max_retries=1)
```

## Testing Locally

```bash
# Run unit tests
python -m pytest tests/test_kap_scraper.py -v

# Run example script
python scripts/scrape_kap_data.py

# Test in interactive Python
python -i -c "from src.scrapers.kap_scraper import KAPScraper; scraper = KAPScraper()"
# Then: companies = scraper.get_company_list()
```

## Troubleshooting

### "API returned invalid JSON"
- KAP API is temporarily down (maintenance)
- Scraper automatically falls back to hardcoded company list
- Wait a few hours and try again

### "Rate limited (429)"
- Increase delay: `KAPScraper(delay=3.0)`
- Wait 30 minutes before retrying

### "Timeout"
- Increase timeout: `KAPScraper(timeout=60)`
- Check your internet connection

### "No disclosures found"
- Ticker might not exist or have no recent reports
- Try a major ticker: THYAO, AKBNK, GARAN
- Check company_list: `scraper.get_company_list()`

## Data Storage

Raw data is automatically saved:
```
data/raw/
├── financials/THYAO_1234567.json      # Financial table responses
└── disclosures/THYAO_special_20240101.json  # Announcement responses
```

Use for debugging, replay, or further analysis.

## Integration with Analyst

**Possible enhancement:** Add to daily_briefing.json

```python
# In scripts/daily_update.py
scraper = KAPScraper()
for ticker in portfolio_tickers:
    latest = scraper.get_financial_disclosures(ticker, limit=1)
    briefing["kap_disclosures"][ticker] = latest[0].model_dump()
```

Then analyst can reference: "Latest financial report for THYAO (2024/9): ..."

## Status

- ✅ Production-ready code
- ✅ 16 unit tests passing
- ✅ Comprehensive documentation
- ⏳ Waiting for KAP API to return valid JSON (currently down)
- ✅ Falls back gracefully with hardcoded company list

See [KAP_SCRAPER_README.md](KAP_SCRAPER_README.md) for full documentation.

# KAP Scraper Implementation

## Overview

Complete KAP (Kamuoyu Aydınlatma Platformu) scraper module for fetching BIST financial disclosures and special announcements.

## Modules

### `src/scrapers/kap_scraper.py`
Main scraper class with rate limiting, retry logic, and fallback support.

**Key features:**
- Rate-limited requests (configurable delay, default 1.5s)
- Automatic retry with exponential backoff (Retry Strategy)
- Fallback company list when API unavailable
- Request caching for company list
- Session pooling with Connection Adapter

**Main methods:**
- `get_company_list()` — List all BIST companies (with cache)
- `get_financial_disclosures(ticker, year=None, period=None, limit=10)` — Financial reports
- `get_special_disclosures(ticker, start_date=None, end_date=None, limit=50)` — Material events
- `get_financial_tables(disclosure_id)` — Detailed financial statements

### `src/scrapers/kap_models.py`
Pydantic data models for type safety and validation.

**Models:**
- `FinancialDisclosure` — Financial report metadata
- `SpecialDisclosure` — Material event announcement
- `FinancialTables` — Balance sheet, income statement, cash flow

### `src/scrapers/kap_parser.py`
HTML/JSON parsing and data normalization.

**Functions:**
- `normalize_value(val)` — Turkish format "1.234.567,89" → 1234567.89
- `parse_balance_sheet(raw)` — Extract balance sheet items
- `parse_income_statement(raw)` — Extract income statement items
- `parse_cash_flow(raw)` — Extract cash flow statement
- `parse_special_disclosure(raw)` — Extract announcement fields
- `detect_currency_unit(raw)` — Currency and multiplier detection

## Usage

### Basic Example
```python
from src.scrapers.kap_scraper import KAPScraper

scraper = KAPScraper(delay=1.5, timeout=30)

# List companies
companies = scraper.get_company_list()

# Financial disclosures
disclosures = scraper.get_financial_disclosures("THYAO", limit=5)
for d in disclosures:
    print(f"{d.ticker} {d.period} — {d.disclosure_date}")

# Special announcements
specials = scraper.get_special_disclosures(
    "THYAO",
    start_date="2024-01-01",
    limit=10
)

# Financial tables
if disclosures:
    tables = scraper.get_financial_tables(disclosures[0].disclosure_id)
    if tables:
        print(f"Balance sheet: {len(tables.balance_sheet)} accounts")
        print(f"Income statement: {len(tables.income_statement)} accounts")
```

### Production Script
See `scripts/scrape_kap_data.py` for example usage.

## Data Storage

Raw and processed data are saved to:
- `data/raw/financials/` — Raw JSON responses
- `data/raw/disclosures/` — Raw announcement JSON
- `data/processed/financials/` — Parsed financial tables
- `data/processed/disclosures/` — Parsed announcements

## Testing

```bash
# Unit tests (value parsing, company list, caching)
python -m pytest tests/test_kap_scraper.py::TestNormalizeValue -v
python -m pytest tests/test_kap_scraper.py::TestKAPScraperCompanyList -v

# Integration tests (requires API access)
python -m pytest tests/test_kap_scraper.py::TestKAPScraperIntegration -v
```

## Current Status

- **API Status:** KAP API currently returns invalid JSON (likely maintenance or blocking)
- **Fallback:** Hardcoded company list (8 major BIST stocks) for testing
- **Parser:** Ready for real API responses once KAP returns valid JSON
- **Tests:** 14/14 unit tests passing; API-dependent tests skip gracefully

## Dependencies

```
requests>=2.31        # HTTP client
pydantic>=2.0         # Data validation
beautifulsoup4>=4.12  # HTML parsing (when needed)
lxml>=5.0             # XML parsing
tenacity>=8.2         # Retry decorators
pandas>=2.0           # Data transformation
python-dateutil>=2.8  # Date parsing
ratelimit>=2.2        # Rate limiting
fake-useragent>=1.4   # User-Agent rotation
```

## Architecture Notes

**Why Fallback?**
- KAP API occasionally returns HTML error pages instead of JSON
- Fallback prevents complete failure during development/testing
- Production should monitor API status and alert on fallback usage

**Why Rate Limiting?**
- KAP throttles high-frequency requests
- Default 1.5s delay between requests
- Configurable per instance

**Why Pydantic?**
- Type safety for downstream analysis
- Automatic validation of date formats
- IDE autocompletion support
- Clear contract for API consumers

## Future Enhancements

- [ ] HTML-based scraper fallback (BeautifulSoup)
- [ ] Quarterly report aggregation
- [ ] Financial ratio calculations (ROE, Debt/Equity, etc.)
- [ ] Material event impact analysis
- [ ] Integration with daily_briefing.json
- [ ] Caching layer with expiry (Redis, SQLite)

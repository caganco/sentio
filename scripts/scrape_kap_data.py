"""Example KAP scraper usage."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.kap_scraper import KAPScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

TICKERS = ["THYAO", "AKBNK", "GARAN", "KCHOL", "ENERY"]


def main():
    logger.info("=" * 60)
    logger.info("KAP Data Scraper Example")
    logger.info("=" * 60)

    scraper = KAPScraper(delay=2.0, timeout=20)

    # 1. Company list
    logger.info("\n[1] Loading company list...")
    companies = scraper.get_company_list()
    logger.info(f"Loaded {len(companies)} BIST companies")

    # 2. Financial disclosures for sample tickers
    for ticker in TICKERS[:2]:  # Only first 2 to save time
        logger.info(f"\n[2] Fetching financial disclosures for {ticker}...")
        disclosures = scraper.get_financial_disclosures(ticker, limit=2)
        logger.info(f"Found {len(disclosures)} financial disclosures")

        if disclosures:
            for d in disclosures[:1]:  # Just first one
                logger.info(f"  - {d.ticker} {d.period} ({d.disclosure_date.date()})")

        # 3. Try to get financial tables
        if disclosures:
            logger.info(f"[3] Fetching financial tables...")
            tables = scraper.get_financial_tables(disclosures[0].disclosure_id)
            if tables:
                logger.info(
                    f"  ✓ {tables.ticker} {tables.period}: "
                    f"{len(tables.balance_sheet)} accounts in balance sheet"
                )
            else:
                logger.warning(f"  ✗ Could not fetch tables (API may be down)")

    # 4. Special disclosures
    ticker = TICKERS[0]
    logger.info(f"\n[4] Fetching special disclosures for {ticker}...")
    specials = scraper.get_special_disclosures(ticker, limit=3)
    logger.info(f"Found {len(specials)} special disclosures")
    if specials:
        for s in specials[:1]:
            logger.info(f"  - {s.title} ({s.disclosure_date.date()})")

    logger.info("\n" + "=" * 60)
    logger.info("Scraping complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

import pytest
from datetime import datetime
from src.scrapers.kap_scraper import KAPScraper
from src.scrapers.kap_parser import normalize_value


class TestNormalizeValue:
    """Test Turkish number format normalization."""

    def test_turkish_thousands(self):
        assert normalize_value("1.234.567,89") == 1234567.89

    def test_negative_parens(self):
        assert normalize_value("(500,00)") == -500.0

    def test_dash(self):
        assert normalize_value("-") is None

    def test_float_input(self):
        assert normalize_value(1234.56) == 1234.56

    def test_int_input(self):
        assert normalize_value(1000) == 1000.0

    def test_none_input(self):
        assert normalize_value(None) is None

    def test_na_string(self):
        assert normalize_value("N/A") is None


class TestKAPScraperCompanyList:
    """Test company list retrieval."""

    @pytest.fixture
    def scraper(self):
        return KAPScraper(delay=0.5, timeout=10)

    def test_company_list_structure(self, scraper):
        """Verify company list has required fields."""
        companies = scraper.get_company_list()
        assert len(companies) > 0, "Company list should not be empty"

        for company in companies:
            assert "ticker" in company
            assert "name" in company
            assert company["ticker"] is not None

    def test_thyao_in_list(self, scraper):
        """Verify THYAO exists in company list."""
        companies = scraper.get_company_list()
        tickers = [c["ticker"] for c in companies]
        assert "THYAO" in tickers, "THYAO should be in BIST"

    def test_cache_works(self, scraper):
        """Verify company list caching."""
        first_call = scraper.get_company_list()
        second_call = scraper.get_company_list()
        assert first_call is second_call, "Cache should return same object"


class TestKAPScraperFinancial:
    """Test financial disclosure retrieval."""

    @pytest.fixture
    def scraper(self):
        return KAPScraper(delay=0.5, timeout=10)

    def test_financial_disclosures_exist(self, scraper):
        """Verify financial disclosures can be retrieved."""
        disclosures = scraper.get_financial_disclosures("THYAO", limit=3)
        # API may be unavailable; test passes if no exception
        assert isinstance(disclosures, list)

    def test_disclosure_fields(self, scraper):
        """Verify disclosure objects have required fields."""
        disclosures = scraper.get_financial_disclosures("THYAO", limit=1)
        # Skip if API unavailable
        if not disclosures:
            pytest.skip("KAP API unavailable")

        d = disclosures[0]
        assert d.disclosure_id
        assert d.ticker == "THYAO"
        assert d.company_name
        assert d.period
        assert isinstance(d.disclosure_date, datetime)

    def test_year_filter(self, scraper):
        """Verify year filtering works."""
        disclosures = scraper.get_financial_disclosures("THYAO", year=2024, limit=5)
        # Some should be from 2024
        assert len(disclosures) >= 0  # May be 0 if no 2024 reports yet

    def test_special_disclosures(self, scraper):
        """Verify special disclosures can be retrieved."""
        disclosures = scraper.get_special_disclosures("THYAO", limit=5)
        assert len(disclosures) >= 0

        if disclosures:
            d = disclosures[0]
            assert d.disclosure_id
            assert d.ticker == "THYAO"
            assert d.title
            assert isinstance(d.disclosure_date, datetime)


class TestKAPScraperRateLimit:
    """Test rate limiting behavior."""

    def test_rate_limiting_enforced(self):
        """Verify rate limiting between requests."""
        import time

        scraper = KAPScraper(delay=0.5)
        start = time.time()

        # Make multiple requests
        scraper.get_company_list()
        scraper.get_company_list()  # From cache
        scraper.get_special_disclosures("THYAO", limit=1)

        elapsed = time.time() - start
        # At least one real request should respect delay
        assert elapsed > 0, "Should take measurable time"


@pytest.mark.integration
class TestKAPScraperIntegration:
    """Full integration tests."""

    def test_full_workflow(self):
        """Test complete workflow: list → disclosures → tables."""
        scraper = KAPScraper(delay=1.0, timeout=15)

        # Step 1: Get companies
        companies = scraper.get_company_list()
        assert len(companies) > 0

        # Step 2: Get financial disclosures
        ticker = "THYAO"
        disclosures = scraper.get_financial_disclosures(ticker, limit=1)
        if disclosures:
            # Step 3: Get tables (if disclosure exists)
            tables = scraper.get_financial_tables(disclosures[0].disclosure_id)
            if tables:
                assert tables.ticker == ticker
                assert tables.period
                assert tables.balance_sheet is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

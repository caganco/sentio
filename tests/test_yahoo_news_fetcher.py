"""Tests for YahooNewsFetcher and ticker validation."""

import pytest

from src.nlp.sentiment_data import YahooNewsFetcher, validate_ticker_format


class TestTickerValidation:
    """Test ticker format validation."""

    def test_valid_ticker_no_suffix(self):
        """Valid ticker without .IS suffix."""
        assert validate_ticker_format("AKSEN") is True
        assert validate_ticker_format("GARAN") is True

    def test_valid_ticker_with_suffix(self):
        """Valid ticker with .IS suffix."""
        assert validate_ticker_format("AKSEN.IS") is True
        assert validate_ticker_format("GARAN.IS") is True

    def test_valid_ticker_sise_bug(self):
        """Test the SISE.IS edge case (originally broken by rstrip bug)."""
        # This was the bug case: rstrip(".IS") would incorrectly strip "SISE.IS" → "SIS"
        # Now with removesuffix(), it should correctly validate to "SISE"
        assert validate_ticker_format("SISE.IS") is True
        assert validate_ticker_format("SISE") is True

    def test_valid_tickers_ending_in_problematic_chars(self):
        """Test tickers ending in S, I, or E (chars that rstrip would incorrectly strip)."""
        # These could be broken by rstrip(".IS") but should work with removesuffix()
        assert validate_ticker_format("TTKOM.IS") is True
        assert validate_ticker_format("ENERY.IS") is True
        assert validate_ticker_format("ASELS.IS") is True
        assert validate_ticker_format("ARCLK.IS") is True

    def test_invalid_ticker_too_short(self):
        """Ticker with empty base."""
        assert validate_ticker_format(".IS") is False
        assert validate_ticker_format("") is False

    def test_invalid_ticker_too_long(self):
        """Ticker exceeding 5 character limit."""
        assert validate_ticker_format("VERYLONGTICKER") is False
        assert validate_ticker_format("VERYLONGTICKER.IS") is False

    def test_invalid_ticker_lowercase(self):
        """Ticker with lowercase letters."""
        assert validate_ticker_format("aksen") is False
        assert validate_ticker_format("Aksen") is False
        assert validate_ticker_format("AkSen") is False

    def test_invalid_ticker_special_chars(self):
        """Ticker with special characters."""
        assert validate_ticker_format("AKSE@") is False
        assert validate_ticker_format("AKSE-N") is False
        assert validate_ticker_format("AKSE_N") is False

    def test_invalid_ticker_numbers(self):
        """Ticker with numbers."""
        assert validate_ticker_format("AKS3N") is False
        assert validate_ticker_format("AKSEN2") is False

    def test_valid_single_letter(self):
        """Single letter ticker."""
        assert validate_ticker_format("A") is True
        assert validate_ticker_format("A.IS") is True

    def test_valid_five_letter(self):
        """Five letter ticker (maximum length)."""
        assert validate_ticker_format("ABCDE") is True
        assert validate_ticker_format("ABCDE.IS") is True

    def test_invalid_six_letter(self):
        """Six letter ticker (exceeds maximum)."""
        assert validate_ticker_format("ABCDEF") is False
        assert validate_ticker_format("ABCDEF.IS") is False

    def test_ticker_with_multiple_suffixes(self):
        """Ticker with incorrect suffix format."""
        assert validate_ticker_format("AKSEN.IO") is False
        assert validate_ticker_format("AKSEN.IS.IS") is False


class TestYahooNewsFetcher:
    """Test YahooNewsFetcher initialization and basic functionality."""

    def test_fetcher_initialization(self):
        """Test that fetcher initializes correctly."""
        fetcher = YahooNewsFetcher()
        assert fetcher.base_url == "https://query1.finance.yahoo.com"
        assert fetcher.timeout == 10.0
        assert fetcher.fetch_success == 0
        assert fetcher.fetch_failure == 0

    def test_success_rate_initial(self):
        """Test initial success rate is 0 when no fetches attempted."""
        fetcher = YahooNewsFetcher()
        assert fetcher.get_success_rate() == 0.0

    def test_stats_initial(self):
        """Test initial stats show zero attempts."""
        fetcher = YahooNewsFetcher()
        stats = fetcher.get_stats()
        assert stats["total_attempts"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate_pct"] == 0.0

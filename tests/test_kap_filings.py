"""Tests for KapScraper.get_filings() — D-114."""
from unittest.mock import patch

import pytest

from src.data.kap_scraper import KapScraper


def _sample_news(ticker: str = "AKSEN") -> list[dict]:
    return [
        {
            "source": "gnews:Haberturk",
            "ticker": ticker,
            "title": f"{ticker} ozel durum aciklamasi",
            "published": "2026-05-21T10:00:00+00:00",
            "category": "IMPORTANT",
            "url": "https://example.com/news/1",
        },
        {
            "source": "gnews:Milliyet",
            "ticker": ticker,
            "title": f"{ticker} temettü bildirimi",
            "published": "2026-05-20T08:30:00+00:00",
            "category": "CRITICAL",
            "url": "https://example.com/news/2",
        },
    ]


class TestKapScraperGetFilings:

    def test_returns_list(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news()):
            result = scraper.get_filings("AKSEN")
        assert isinstance(result, list)

    def test_returns_empty_when_no_news(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=[]):
            result = scraper.get_filings("AKSEN")
        assert result == []

    def test_result_has_required_fields(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news()):
            result = scraper.get_filings("AKSEN")
        assert len(result) == 2
        for item in result:
            assert "symbol" in item
            assert "published_at" in item
            assert "category" in item
            assert "title" in item
            assert "url" in item
            assert "source" in item

    def test_symbol_field_matches_input(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news("TTKOM")):
            result = scraper.get_filings("TTKOM")
        assert all(item["symbol"] == "TTKOM" for item in result)

    def test_published_at_maps_from_published(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news()):
            result = scraper.get_filings("AKSEN")
        assert result[0]["published_at"] == "2026-05-21T10:00:00+00:00"
        assert result[1]["published_at"] == "2026-05-20T08:30:00+00:00"

    def test_category_preserved(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news()):
            result = scraper.get_filings("AKSEN")
        assert result[0]["category"] == "IMPORTANT"
        assert result[1]["category"] == "CRITICAL"

    def test_never_raises_on_fetch_exception(self):
        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", side_effect=RuntimeError("network")):
            result = scraper.get_filings("AKSEN")
        assert result == []

    def test_category_defaults_to_diger_when_missing(self):
        scraper = KapScraper()
        raw = [{"source": "gnews:Test", "ticker": "AKSEN",
                "title": "haber", "published": "2026-05-21T10:00:00+00:00", "url": ""}]
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=raw):
            result = scraper.get_filings("AKSEN")
        assert result[0]["category"] == "diger"

    def test_published_at_empty_when_published_missing(self):
        scraper = KapScraper()
        raw = [{"source": "gnews:Test", "ticker": "AKSEN",
                "title": "haber", "category": "NOISE", "url": ""}]
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=raw):
            result = scraper.get_filings("AKSEN")
        assert result[0]["published_at"] == ""

    def test_compatible_with_score_kap_symbol_filter(self):
        """score_kap() checks ev.get('symbol') against the requested symbol."""
        from src.signals.layers.kap_layer import score_kap
        from datetime import date

        scraper = KapScraper()
        with patch("src.data.kap_scraper.fetch_kap_news", return_value=_sample_news("AKSEN")):
            filings = scraper.get_filings("AKSEN")

        # score_kap should accept get_filings() output without raising
        result = score_kap("AKSEN", filings, date(2026, 5, 21))
        assert result.layer == "kap"
        assert isinstance(result.score, float)

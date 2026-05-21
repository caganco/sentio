"""Tests for src/data/news_fetcher.py (D-094 / SPEC_L4_NEWS_1)."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.data.news_fetcher import (
    MatchedArticle,
    MynetDirectFetcher,
    MynetNewsFetcher,
    NewsArticle,
    TickerMatcher,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_article(title: str, body: str = "", tags: list[str] | None = None) -> NewsArticle:
    return NewsArticle(
        title=title,
        body=body,
        published_at=datetime.now(timezone.utc),
        url="http://example.com",
        tags=tags or [],
    )


def _mock_direct_fetcher(raw_articles: list[dict]) -> MynetDirectFetcher:
    """Return a MynetDirectFetcher mock whose fetch_raw returns given articles."""
    mock = MagicMock(spec=MynetDirectFetcher)
    mock.fetch_raw.return_value = raw_articles
    return mock


# ---------------------------------------------------------------------------
# TestMynetNewsFetcher
# ---------------------------------------------------------------------------

class TestMynetNewsFetcher:

    def test_returns_empty_on_scraper_unavailable(self, tmp_path):
        """Scraper failure → [] returned, no exception propagated."""
        mock = MagicMock(spec=MynetDirectFetcher)
        mock.fetch_raw.side_effect = RuntimeError("Mynet unreachable")
        fetcher = MynetNewsFetcher(cache_file=tmp_path / "cache.json", direct_fetcher=mock)
        result = fetcher.fetch("AKBNK", days=7)
        assert result == []

    def test_cache_ttl_prevents_redundant_calls(self, tmp_path):
        """Second fetch() for same key must not call scraper (cache hit)."""
        raw = [{
            "baslik": "Test", "metin": "body",
            "tarih": "2026-05-19T10:00:00+03:00",
            "url": "http://x.com",
        }]
        mock = _mock_direct_fetcher(raw)
        fetcher = MynetNewsFetcher(cache_file=tmp_path / "cache.json", direct_fetcher=mock)
        fetcher.fetch("AKBNK", days=7)
        fetcher.fetch("AKBNK", days=7)
        assert mock.fetch_raw.call_count == 1

    def test_deserialization_from_raw_json(self, tmp_path):
        """Raw dict → NewsArticle fields parsed correctly."""
        raw = [{
            "baslik": "Akbank kâr açıkladı",
            "metin": "Akbank güçlü büyüme...",
            "tarih": "2026-05-18T14:00:00+03:00",
            "url": "http://mynet.com/akbnk",
            "source": "mynet_finans",
            "tags": ["AKBNK", "bankacılık"],
        }]
        fetcher = MynetNewsFetcher(cache_file=tmp_path / "c.json", direct_fetcher=_mock_direct_fetcher(raw))
        articles = fetcher.fetch("AKBNK")
        assert len(articles) == 1
        assert articles[0].title == "Akbank kâr açıkladı"
        assert articles[0].source == "mynet_finans"
        assert "bankacılık" in articles[0].tags

    def test_deserialization_tolerates_missing_fields(self, tmp_path):
        """Articles with missing optional fields don't crash deserialization."""
        raw = [{"baslik": "Minimum article"}]  # no body, url, tags, tarih
        fetcher = MynetNewsFetcher(cache_file=tmp_path / "c.json", direct_fetcher=_mock_direct_fetcher(raw))
        articles = fetcher.fetch("THYAO")
        assert len(articles) == 1
        assert articles[0].title == "Minimum article"
        assert articles[0].body == ""
        assert articles[0].tags == []

    def test_stale_cache_returned_on_scraper_failure(self, tmp_path):
        """When scraper fails after a prior successful fetch, stale cache is returned."""
        raw = [{"baslik": "Cached article", "tarih": "2026-05-01T10:00:00+03:00"}]
        mock = _mock_direct_fetcher(raw)
        fetcher = MynetNewsFetcher(cache_file=tmp_path / "c.json", direct_fetcher=mock)

        # Populate stale cache
        fetcher._cache["GARAN:7"] = {"articles": raw, "fetched_at": 0}
        fetcher._persist()

        # Scraper fails
        mock.fetch_raw.side_effect = RuntimeError("timeout")
        result = fetcher.fetch("GARAN", days=7)
        assert len(result) == 1
        assert result[0].title == "Cached article"


# ---------------------------------------------------------------------------
# TestTickerMatcher
# ---------------------------------------------------------------------------

class TestTickerMatcher:

    def test_exact_ticker_match(self):
        """'AKBNK' in article text → exact_ticker (weight 1.00)."""
        art = _make_article("AKBNK güçlü kâr açıkladı")
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "exact_ticker"
        assert m.relevance_weight == pytest.approx(1.00)

    def test_exact_ticker_via_tags(self):
        """Ticker in tags → exact_ticker."""
        art = _make_article("Bankacılık sektörü haberleri", tags=["AKBNK"])
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "exact_ticker"

    def test_company_alias_match(self):
        """Alias 'akbank' → company_name (weight 0.85)."""
        art = _make_article("Akbank büyüme hedefini açıkladı")
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "company_name"
        assert m.relevance_weight == pytest.approx(0.85)

    def test_sector_theme_match(self):
        """Sector keyword 'bankacılık' → sector_theme (weight 0.30)."""
        art = _make_article("Bankacılık sektöründe faiz baskısı artıyor")
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "sector_theme"
        assert m.relevance_weight == pytest.approx(0.30)

    def test_no_match(self):
        """Unrelated article → no_match (weight 0.10)."""
        art = _make_article("Altın fiyatları yükseliyor, ons başına 2000 dolar")
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "no_match"
        assert m.relevance_weight == pytest.approx(0.10)

    def test_exact_ticker_priority_over_alias(self):
        """Ticker string wins over alias when both present."""
        art = _make_article("AKBNK (Akbank) rekor kâr")
        m = TickerMatcher().match(art, "AKBNK")
        assert m.match_type == "exact_ticker"

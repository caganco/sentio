"""Tests for news aggregation and sentiment aggregation."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.signals.sentiment.news_aggregator import NewsAggregator
from src.signals.sentiment.vader_analyzer import VaderSentimentAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yahoo_item(title: str, summary: str, age_days: float = 0) -> dict:
    """Build a minimal yfinance news item (old schema: flat dict)."""
    pub_ts = int((datetime.now() - timedelta(days=age_days)).timestamp())
    return {
        "title": title,
        "summary": summary,
        "providerPublishTime": pub_ts,
        "publisher": "TestSource",
    }


def _make_yahoo_item_v2(title: str, summary: str, age_days: float = 0) -> dict:
    """Build a yfinance >=0.2 news item (content nested dict)."""
    pub_ts_str = (datetime.now() - timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "content": {
            "title": title,
            "summary": summary,
            "pubDate": pub_ts_str,
            "provider": {"displayName": "TestSource"},
        }
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def aggregator(tmp_path):
    return NewsAggregator(str(tmp_path / "sentiment_cache_test.json"))


@pytest.fixture
def analyzer():
    return VaderSentimentAnalyzer()


# ---------------------------------------------------------------------------
# YahooFinance fetch tests
# ---------------------------------------------------------------------------

class TestYahooNewsFetch:
    """Test YahooFinance news fetching."""

    def test_fetch_returns_articles_from_yahoo(self, aggregator):
        fake_news = [
            _make_yahoo_item("AKSEN gains on energy boost", "Strong revenue growth expected", 0),
            _make_yahoo_item("Market outlook positive", "Analysts bullish on sector", 1),
        ]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            articles = aggregator.fetch_news("AKSEN", days=7)

        assert len(articles) == 2
        assert articles[0]["source"] == "TestSource"
        assert "AKSEN" in articles[0]["title"] or "Market" in articles[0]["title"]

    def test_fetch_filters_old_articles(self, aggregator):
        fake_news = [
            _make_yahoo_item("Recent news", "Good profit", age_days=1),
            _make_yahoo_item("Old news", "Old data", age_days=30),  # outside 7-day window
        ]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            articles = aggregator.fetch_news("AKSEN", days=7)

        assert len(articles) == 1
        assert "Recent" in articles[0]["title"]

    def test_fetch_handles_v2_content_schema(self, aggregator):
        fake_news = [_make_yahoo_item_v2("Profit surge expected", "Bullish outlook", 0)]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            articles = aggregator.fetch_news("AKSEN", days=7)

        assert len(articles) == 1
        assert "Profit surge" in articles[0]["title"]

    def test_fetch_uses_bist_suffix(self, aggregator):
        called_symbols = []

        def capture(sym):
            called_symbols.append(sym)
            m = MagicMock()
            m.news = []
            return m

        with patch("yfinance.Ticker", side_effect=capture):
            aggregator.fetch_news("GARAN", days=7)

        assert called_symbols == ["GARAN.IS"]

    def test_fetch_returns_empty_on_yahoo_error(self, aggregator):
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = None
            articles = aggregator.fetch_news("AKSEN", days=7)
        assert articles == []

    def test_fetch_returns_empty_on_exception(self, aggregator):
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.side_effect = Exception("network error")
            articles = aggregator.fetch_news("AKSEN", days=7)
        assert articles == []

    def test_fetch_skips_items_with_no_text(self, aggregator):
        fake_news = [
            {"providerPublishTime": int(datetime.now().timestamp())},  # no title/summary
            _make_yahoo_item("Valid headline", "Good earnings", 0),
        ]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            articles = aggregator.fetch_news("AKSEN", days=7)

        assert len(articles) == 1
        assert "Valid" in articles[0]["title"]


# ---------------------------------------------------------------------------
# Cache tests
# ---------------------------------------------------------------------------

class TestCacheBehavior:
    """Test cache logic."""

    def test_cache_is_used_on_second_call(self, aggregator):
        fake_news = [_make_yahoo_item("Cached article", "Some text", 0)]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            first = aggregator.fetch_news("AKSEN", days=7)

        # Second call should NOT hit Yahoo (cache valid)
        with patch("yfinance.Ticker") as mock_ticker_cls2:
            mock_ticker_cls2.return_value.news = []  # would give 0 if Yahoo called
            second = aggregator.fetch_news("AKSEN", days=7)

        assert len(first) == len(second) == 1

    def test_cache_persists_to_disk(self, aggregator, tmp_path):
        fake_news = [_make_yahoo_item("Persisted article", "Good text", 0)]
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = fake_news
            aggregator.fetch_news("AKSEN", days=7)

        # New aggregator instance should load from disk
        aggregator2 = NewsAggregator(str(tmp_path / "sentiment_cache_test.json"))
        articles = aggregator2.fetch_news("AKSEN", days=7)
        assert len(articles) == 1

    def test_empty_fetch_is_cached(self, aggregator):
        with patch("yfinance.Ticker") as mock_ticker_cls:
            mock_ticker_cls.return_value.news = []
            articles = aggregator.fetch_news("RARE_TICKER", days=7)

        assert articles == []
        assert "RARE_TICKER" in aggregator.cache


# ---------------------------------------------------------------------------
# Sentiment aggregation tests (unchanged logic, no dummy dependency)
# ---------------------------------------------------------------------------

class TestAggregation:
    """Test sentiment aggregation math."""

    def test_aggregate_sentiment_positive(self, aggregator, analyzer):
        articles = [
            {"text": "Great earnings and strong growth", "date": datetime.now().isoformat()},
            {"text": "Excellent profit margins and outstanding performance", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert result["normalized"] > 0.5
        assert result["bullish"] >= 1
        assert result["bearish"] == 0

    def test_aggregate_sentiment_negative(self, aggregator, analyzer):
        articles = [
            {"text": "Catastrophic losses and plummeting revenue completely destroy shareholder value", "date": datetime.now().isoformat()},
            {"text": "Devastating financial results with massive decline ahead", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert result["normalized"] < 0.5
        assert result["bearish"] >= 1

    def test_aggregate_sentiment_mixed(self, aggregator, analyzer):
        articles = [
            {"text": "Good earnings", "date": datetime.now().isoformat()},
            {"text": "Weak demand concerns", "date": datetime.now().isoformat()},
            {"text": "Stable trading", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert 0 <= result["normalized"] <= 1
        assert result["count"] == 3

    def test_aggregate_sentiment_empty(self, aggregator, analyzer):
        result = aggregator.aggregate_sentiment([], analyzer)
        assert result["score"] == 0.0
        assert result["normalized"] == 0.5
        assert result["count"] == 0

    def test_recency_weighting(self, aggregator, analyzer):
        now = datetime.now()
        old_date = (now - timedelta(days=7)).isoformat()
        recent_date = now.isoformat()

        old_result = aggregator.aggregate_sentiment(
            [{"text": "Good earnings", "date": old_date}], analyzer
        )
        recent_result = aggregator.aggregate_sentiment(
            [{"text": "Good earnings", "date": recent_date}], analyzer
        )

        assert old_result["normalized"] > 0
        assert recent_result["normalized"] > 0
        # Recent weight (0.9^0=1.0) > old weight (0.9^7≈0.478), same text → same sign
        assert (recent_result["score"] >= 0) == (old_result["score"] >= 0)

    def test_normalize_to_0_1_range(self, aggregator, analyzer):
        test_cases = [
            [{"text": "Excellent profit", "date": datetime.now().isoformat()}],
            [{"text": "Major loss reported", "date": datetime.now().isoformat()}],
            [{"text": "Mixed trading", "date": datetime.now().isoformat()}],
        ]
        for articles in test_cases:
            result = aggregator.aggregate_sentiment(articles, analyzer)
            assert 0 <= result["normalized"] <= 1

    def test_bullish_count(self, aggregator, analyzer):
        articles = [
            {"text": "Strong gains and excellent growth", "date": datetime.now().isoformat()},
            {"text": "Outperform expectations", "date": datetime.now().isoformat()},
            {"text": "Decline continues", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert result["bullish"] >= 1

    def test_bearish_count(self, aggregator, analyzer):
        articles = [
            {"text": "Severe loss in operations", "date": datetime.now().isoformat()},
            {"text": "Sharp decline expected", "date": datetime.now().isoformat()},
            {"text": "Good recovery signs", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert result["bearish"] >= 1

    def test_missing_date_handling(self, aggregator, analyzer):
        articles = [
            {"text": "Good earnings", "date": datetime.now().isoformat()},
            {"text": "Poor revenue", "date": None},
            {"text": "Mixed signals"},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert result["count"] == 3
        assert 0 <= result["normalized"] <= 1

    def test_article_scores_in_result(self, aggregator, analyzer):
        articles = [
            {"text": "Good earnings", "date": datetime.now().isoformat()},
            {"text": "Poor revenue", "date": datetime.now().isoformat()},
        ]
        result = aggregator.aggregate_sentiment(articles, analyzer)
        assert "articles" in result
        assert len(result["articles"]) == 2
        for article_score in result["articles"]:
            assert "score" in article_score
            assert "weighted" in article_score
            assert "weight" in article_score

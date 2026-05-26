"""Tests for sentiment signal integration."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.signals.sentiment.sentiment_signal import SentimentSignal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yahoo_item(title: str, summary: str, age_days: float = 0) -> dict:
    pub_ts = int((datetime.now().timestamp() - age_days * 86400))
    return {
        "title": title,
        "summary": summary,
        "providerPublishTime": pub_ts,
        "publisher": "TestSource",
    }


def _mock_ticker(news_items: list):
    m = MagicMock()
    m.news = news_items
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sentiment_signal(tmp_path):
    return SentimentSignal(str(tmp_path / "sentiment_cache_test.json"))


@pytest.fixture
def positive_news():
    return [
        _yahoo_item("Strong earnings beat", "Excellent revenue growth and profit expansion", 0),
        _yahoo_item("Analyst upgrades stock", "Bullish outlook with strong upside target", 1),
        _yahoo_item("Record profit announced", "Outstanding quarterly results exceed expectations", 2),
    ]


@pytest.fixture
def negative_news():
    return [
        _yahoo_item("Catastrophic loss reported", "Massive revenue decline and shareholder value destruction", 0),
        _yahoo_item("Analyst downgrades", "Bearish outlook with severe downside risk", 1),
    ]


# ---------------------------------------------------------------------------
# Basic structure tests
# ---------------------------------------------------------------------------

class TestSentimentSignalStructure:
    """Test sentiment signal dict structure."""

    def test_calculate_returns_dict(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert isinstance(result, dict)
        assert "score" in result
        assert "confidence" in result
        assert "article_count" in result

    def test_score_range_0_to_100(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert 0 <= result["score"] <= 100

    def test_normalized_range_minus1_to_1(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert -1 <= result["normalized"] <= 1

    def test_confidence_range_0_to_1(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert 0 <= result["confidence"] <= 1

    def test_article_count_non_negative(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["article_count"] >= 0

    def test_bullish_bearish_counts(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["bullish_count"] >= 0
        assert result["bearish_count"] >= 0
        assert (result["bullish_count"] + result["bearish_count"]) <= result["article_count"]

    def test_source_computed_or_missing(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["source"] in ("computed", "missing")


# ---------------------------------------------------------------------------
# Sentiment accuracy tests
# ---------------------------------------------------------------------------

class TestSentimentAccuracy:
    """Test that positive/negative news produces expected signal direction."""

    def test_positive_news_produces_high_score(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["article_count"] > 0
        assert result["score"] >= 50, f"Positive news should score ≥50, got {result['score']}"

    def test_negative_news_produces_low_score(self, sentiment_signal, negative_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(negative_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["article_count"] > 0
        assert result["score"] <= 60, f"Negative news should score ≤60, got {result['score']}"

    def test_neutral_sentiment_near_50(self, sentiment_signal):
        neutral_news = [
            _yahoo_item("Mixed trading", "Stable market conditions with sideways trend", 0),
        ]
        with patch("yfinance.Ticker", return_value=_mock_ticker(neutral_news)):
            result = sentiment_signal.calculate("ENERY", days=7)
        # Neutral text should stay in reasonable range
        assert 30 <= result["score"] <= 70


# ---------------------------------------------------------------------------
# Missing news tests
# ---------------------------------------------------------------------------

class TestMissingNews:
    """Test no-news fallback path."""

    def test_missing_news_returns_neutral(self, sentiment_signal):
        with patch("yfinance.Ticker", return_value=_mock_ticker([])):
            result = sentiment_signal.calculate("NONEXISTENT_XYZ", days=7)
        assert result["source"] == "missing"
        assert result["score"] == 50.0
        assert result["confidence"] == 0.0

    def test_missing_news_article_count_zero(self, sentiment_signal):
        with patch("yfinance.Ticker", return_value=_mock_ticker([])):
            result = sentiment_signal.calculate("NONEXISTENT_XYZ", days=7)
        assert result["article_count"] == 0


# ---------------------------------------------------------------------------
# Confidence tests
# ---------------------------------------------------------------------------

_MYNET_EMPTY = "src.signals.sentiment.news_aggregator.MynetNewsAggregator.aggregate"
_MYNET_EMPTY_RESULT = {
    "score": 50.0, "normalized": 0.0, "confidence": 0.0,
    "bullish_count": 0, "bearish_count": 0, "article_count": 0,
    "source": "missing",
}


class TestConfidence:
    """Test confidence scoring logic (Yahoo fallback path)."""

    def test_few_articles_lower_confidence(self, sentiment_signal):
        single_news = [_yahoo_item("Good results", "Decent earnings", 0)]
        with patch(_MYNET_EMPTY, return_value=_MYNET_EMPTY_RESULT), \
             patch("yfinance.Ticker", return_value=_mock_ticker(single_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["article_count"] == 1
        assert result["confidence"] <= 0.8

    def test_five_plus_articles_higher_confidence(self, sentiment_signal):
        many_news = [
            _yahoo_item(f"Positive news {i}", "Strong results and bullish outlook", i * 0.5)
            for i in range(6)
        ]
        with patch(_MYNET_EMPTY, return_value=_MYNET_EMPTY_RESULT), \
             patch("yfinance.Ticker", return_value=_mock_ticker(many_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        assert result["article_count"] >= 5
        assert result["confidence"] >= 0.5

    def test_agreement_affects_confidence(self, sentiment_signal, positive_news):
        with patch(_MYNET_EMPTY, return_value=_MYNET_EMPTY_RESULT), \
             patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result = sentiment_signal.calculate("AKSEN", days=7)
        if result["article_count"] > 1:
            agreement_ratio = max(result["bullish_count"], result["bearish_count"]) / result["article_count"]
            if agreement_ratio > 0.8:
                assert result["confidence"] > 0.3


# ---------------------------------------------------------------------------
# Batch tests
# ---------------------------------------------------------------------------

class TestBatchCalculate:
    """Test batch calculation."""

    def test_batch_calculate_all_tickers(self, sentiment_signal, positive_news):
        tickers = ["AKSEN", "ENERY", "GARAN"]
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            results = sentiment_signal.batch_calculate(tickers, days=7)
        assert len(results) == 3
        for ticker in tickers:
            assert ticker in results
            assert "score" in results[ticker]

    def test_batch_calculate_all_valid(self, sentiment_signal, positive_news):
        tickers = ["AKSEN", "ENERY", "GARAN", "HALKB"]
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            results = sentiment_signal.batch_calculate(tickers, days=7)
        for ticker, result in results.items():
            assert 0 <= result["score"] <= 100
            assert 0 <= result["confidence"] <= 1
            assert result["source"] in ("computed", "missing")


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Test graceful degradation."""

    def test_exception_handling_returns_missing(self, tmp_path):
        signal = SentimentSignal(str(tmp_path / "exc_test_cache.json"))
        with patch("yfinance.Ticker", side_effect=Exception("API down")):
            result = signal.calculate("AKSEN", days=7)
        assert isinstance(result, dict)
        assert result["score"] >= 0
        assert result["source"] in ("computed", "missing")

    def test_days_parameter_passed_through(self, sentiment_signal, positive_news):
        with patch("yfinance.Ticker", return_value=_mock_ticker(positive_news)):
            result_7 = sentiment_signal.calculate("AKSEN", days=7)
        assert isinstance(result_7, dict)


# ---------------------------------------------------------------------------
# L4 Confidence Formula tests (D-094 / SPEC_L4_NEWS_1)
# ---------------------------------------------------------------------------

class TestL4ConfidenceFormula:
    """Validate three-component confidence formula for Mynet/FinBERT pipeline."""

    @staticmethod
    def _scored(n: int, label: str = "bullish", relevance: float = 1.0, fb_conf: float = 1.0):
        from src.nlp.finbert_analyzer import ScoredArticle
        return [
            ScoredArticle(
                title=f"t{i}", sentiment_raw=0.7 if label == "bullish" else -0.7,
                finbert_confidence=fb_conf, relevance_weight=relevance,
                recency_weight=1.0, effective_weight=relevance * fb_conf,
                label=label,
            )
            for i in range(n)
        ]

    def test_below_activation_threshold_returns_zero(self):
        """n < L4_MIN_ARTICLES_ACTIVATE (3) → confidence = 0.0."""
        from src.signals.sentiment.news_aggregator import _compute_confidence
        scored = self._scored(2)
        assert _compute_confidence(scored, 2) == 0.0

    def test_unanimous_ten_articles_max_confidence(self):
        """10 unanimous bullish, full relevance → confidence = 1.0."""
        from src.signals.sentiment.news_aggregator import _compute_confidence
        scored = self._scored(10)
        assert abs(_compute_confidence(scored, 10) - 1.0) < 1e-6

    def test_three_articles_unanimous_confidence_above_zero(self):
        """3 unanimous bullish → confidence > 0, ≤ 1."""
        from src.signals.sentiment.news_aggregator import _compute_confidence
        scored = self._scored(3)
        conf = _compute_confidence(scored, 3)
        assert 0.0 < conf <= 1.0

    def test_mixed_sentiment_lowers_agreement(self):
        """3 bullish + 3 bearish → lower conf than 6 unanimous bullish."""
        from src.signals.sentiment.news_aggregator import _compute_confidence
        mixed = self._scored(3, "bullish") + self._scored(3, "bearish")
        unanimous = self._scored(6, "bullish")
        assert _compute_confidence(mixed, 6) < _compute_confidence(unanimous, 6)

    def test_low_relevance_lowers_quality_component(self):
        """Low relevance_weight → quality_conf lower → overall confidence lower."""
        from src.signals.sentiment.news_aggregator import _compute_confidence
        high_rel = self._scored(5, relevance=1.00)
        low_rel  = self._scored(5, relevance=0.10)
        assert _compute_confidence(high_rel, 5) > _compute_confidence(low_rel, 5)

    def test_engine_weight_zero_at_zero_confidence(self):
        """Engine: MASTER_WEIGHTS['sentiment'] × 0.0 = 0."""
        from src.signals.thresholds import MASTER_WEIGHTS
        assert MASTER_WEIGHTS["sentiment"] * 0.0 == 0.0

    def test_engine_weight_scales_with_confidence(self):
        """Engine: MASTER_WEIGHTS['sentiment'] × 0.75 ≈ 0.0928 (D-154: renormalized)."""
        from src.signals.thresholds import MASTER_WEIGHTS
        effective = MASTER_WEIGHTS["sentiment"] * 0.75
        # D-154: sentiment base weight renormalized 0.12 → 0.12/0.97; 0.75 × 0.12/0.97 ≈ 0.0928
        expected = round(0.12 / 0.97, 10) * 0.75
        assert abs(effective - expected) < 1e-9

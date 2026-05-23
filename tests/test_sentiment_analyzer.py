"""Tests for VADER sentiment analyzer."""

import pytest

from src.signals.sentiment.vader_analyzer import VaderSentimentAnalyzer


class TestVaderSentimentAnalyzer:
    """Test VADER sentiment analysis."""

    @pytest.fixture
    def analyzer(self):
        return VaderSentimentAnalyzer()

    def test_positive_sentiment(self, analyzer):
        """Test detection of positive sentiment."""
        text = "Stock rises sharply with strong profit growth and bullish outlook"
        score = analyzer.analyze_article(text)
        assert score > 0.5, f"Expected positive sentiment, got {score}"

    def test_negative_sentiment(self, analyzer):
        """Test detection of negative sentiment."""
        text = "Stock plummets catastrophically with massive losses and extremely bearish outlook"
        score = analyzer.analyze_article(text)
        assert score < -0.3, f"Expected negative sentiment, got {score}"

    def test_neutral_sentiment(self, analyzer):
        """Test detection of neutral sentiment."""
        text = "Stock trading in sideways range with mixed indicators"
        score = analyzer.analyze_article(text)
        assert -0.5 <= score <= 0.5, f"Expected neutral sentiment, got {score}"

    def test_empty_text(self, analyzer):
        """Test handling of empty text."""
        score = analyzer.analyze_article("")
        assert score == 0.0

    def test_none_text(self, analyzer):
        """Test handling of None input."""
        score = analyzer.analyze_article(None)
        assert score == 0.0

    def test_categorize_bullish(self, analyzer):
        """Test categorization of bullish sentiment."""
        assert analyzer.categorize_sentiment(0.7) == "bullish"
        assert analyzer.categorize_sentiment(0.51) == "bullish"

    def test_categorize_bearish(self, analyzer):
        """Test categorization of bearish sentiment."""
        assert analyzer.categorize_sentiment(-0.7) == "bearish"
        assert analyzer.categorize_sentiment(-0.51) == "bearish"

    def test_categorize_neutral(self, analyzer):
        """Test categorization of neutral sentiment."""
        assert analyzer.categorize_sentiment(0.0) == "neutral"
        assert analyzer.categorize_sentiment(0.3) == "neutral"
        assert analyzer.categorize_sentiment(-0.3) == "neutral"

    def test_batch_analyze_mixed(self, analyzer):
        """Test batch analysis with mixed sentiments."""
        articles = [
            {"text": "Great earnings and strong growth"},
            {"text": "Poor results and declining revenue"},
            {"text": "Stable trading with mixed signals"},
        ]
        result = analyzer.batch_analyze(articles)
        assert result["count"] == 3
        assert len(result["scores"]) == 3
        assert -1 <= result["avg"] <= 1

    def test_batch_analyze_empty(self, analyzer):
        """Test batch analysis with empty list."""
        result = analyzer.batch_analyze([])
        assert result["count"] == 0
        assert result["avg"] == 0.0
        assert result["scores"] == []

    def test_financial_language(self, analyzer):
        """Test with financial domain language."""
        bullish_terms = "profit, revenue growth, expansion, outperform, upgrade"
        score = analyzer.analyze_article(bullish_terms)
        assert score > 0, f"Expected positive for bullish terms, got {score}"

        bearish_terms = "loss, decline, downgrade, underperform, contraction"
        score = analyzer.analyze_article(bearish_terms)
        assert score < 0, f"Expected negative for bearish terms, got {score}"

    def test_length_independence(self, analyzer):
        """Test that sentiment is independent of text length."""
        short = "Good profit growth"
        long = "Our company achieved good profit growth across all business segments this quarter with strong margins"

        short_score = analyzer.analyze_article(short)
        long_score = analyzer.analyze_article(long)

        # Both should be positive, magnitude may differ but direction same
        assert short_score > 0 and long_score > 0, "Both should have positive sentiment"

    def test_score_range(self, analyzer):
        """Test that all scores are in [-1, 1] range."""
        test_texts = [
            "Excellent results",
            "Poor performance",
            "Mixed trading",
            "Outstanding profit growth",
            "Massive losses",
        ]
        for text in test_texts:
            score = analyzer.analyze_article(text)
            assert -1 <= score <= 1, f"Score out of range: {score}"

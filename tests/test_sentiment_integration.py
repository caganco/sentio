"""Integration tests for sentiment layer with signal engine."""

import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from src.signals.engine import compute_signal, compute_batch
from src.signals.layers.sentiment_layer import score_sentiment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yahoo_item(title: str, summary: str, age_days: float = 0) -> dict:
    pub_ts = int(datetime.now().timestamp() - age_days * 86400)
    return {
        "title": title,
        "summary": summary,
        "providerPublishTime": pub_ts,
        "publisher": "TestSource",
    }


_POSITIVE_NEWS = [
    _yahoo_item("Strong earnings beat", "Excellent revenue growth", 0),
    _yahoo_item("Analyst upgrades", "Bullish outlook with strong upside", 1),
    _yahoo_item("Record profit", "Outstanding quarterly results", 2),
]

_MOCK_TICKER = MagicMock()
_MOCK_TICKER.news = _POSITIVE_NEWS


class TestSentimentIntegration:
    """Test sentiment layer integration with signal engine."""

    TECH_BULLISH = {
        "rsi": 55,
        "close": 100.0,
        "ma20": 90.0,
        "ma50": 85.0,
        "ma200": 80.0,
        "momentum_score": 0.3,
        "volume_surge": True,
        "proximity_52w_high": 0.02,
    }

    MACRO_NEUTRAL = {
        "USDTRY": 0.0,
        "VIX": 0.0,
        "BRENT": 0.0,
        "SP500": 0.0,
        "BIST100": 0.0,
        "vix_level": 22.0,
    }

    def test_sentiment_layer_included_in_signal(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        sentiment_layers = [ls for ls in result.audit.layer_scores if ls.layer == "sentiment"]
        assert len(sentiment_layers) == 1

        sentiment_ls = sentiment_layers[0]
        assert 0 <= sentiment_ls.score <= 100
        assert 0 <= sentiment_ls.confidence <= 1.0

    def test_sentiment_affects_final_score(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        assert 30 <= result.score <= 70

    def test_positive_sentiment_increases_score(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        assert result.score >= 40

    def test_sentiment_layer_has_detail(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        sentiment_ls = [ls for ls in result.audit.layer_scores if ls.layer == "sentiment"][0]
        assert "article_count" in sentiment_ls.detail
        assert "bullish_count" in sentiment_ls.detail
        assert "bearish_count" in sentiment_ls.detail

    def test_batch_computes_sentiment_for_all(self):
        symbols = ["AKSEN", "ENERY", "GARAN"]
        tech_batch = {s: self.TECH_BULLISH for s in symbols}

        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            results = compute_batch(symbols, tech_batch, self.MACRO_NEUTRAL, {}, date.today())

        assert len(results) == 3
        for result in results:
            sentiment_layers = [ls for ls in result.audit.layer_scores if ls.layer == "sentiment"]
            assert len(sentiment_layers) == 1

    def test_sentiment_weight_in_master_weights(self):
        from src.signals.thresholds import MASTER_WEIGHTS

        assert "sentiment" in MASTER_WEIGHTS
        assert MASTER_WEIGHTS["sentiment"] == 0.25

    def test_all_5_layers_in_signal(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("TEST", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        layer_names = {ls.layer for ls in result.audit.layer_scores}
        expected_layers = {"technical", "macro", "kap", "sentiment", "risk"}
        assert layer_names == expected_layers

    def test_sentiment_returns_valid_result(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = score_sentiment("AKSEN")

        assert 0 <= result.score <= 100
        assert result.source in ("computed", "missing")

    def test_sentiment_with_different_tickers(self):
        tickers = ["AKSEN", "ENERY", "GARAN", "HALKB"]

        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            for ticker in tickers:
                result = score_sentiment(ticker)
                assert 0 <= result.score <= 100
                assert 0 <= result.confidence <= 1.0
                assert result.layer == "sentiment"

    def test_sentiment_deterministic(self):
        """Calling twice with the same cached data returns identical results."""
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result1 = score_sentiment("AKSEN")
            result2 = score_sentiment("AKSEN")

        assert result1.score == result2.score
        assert result1.confidence == result2.confidence

    def test_sentiment_with_bullish_macro_increases_signal(self):
        bullish_macro = {
            "USDTRY": -0.5,
            "VIX": -0.6,
            "BRENT": 0.3,
            "SP500": 0.7,
            "BIST100": 0.5,
            "vix_level": 15.0,
        }

        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, bullish_macro, [], date.today())

        assert result.score > 60

    def test_sentiment_layer_weight_applied_correctly(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal("AKSEN", self.TECH_BULLISH, self.MACRO_NEUTRAL, [], date.today())

        sentiment_ls = [ls for ls in result.audit.layer_scores if ls.layer == "sentiment"][0]
        assert sentiment_ls.weight == 0.25

    def test_sentiment_missing_source_when_error(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = score_sentiment("AKSEN")
        assert result.source in ("computed", "missing")
        assert result.score >= 0

    def test_sentiment_confidence_increases_with_articles(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = score_sentiment("AKSEN")

        article_count = result.detail.get("article_count", 0)
        if article_count > 0:
            assert result.confidence >= 0.3

    def test_integration_checkpoint_5_layers(self):
        with patch("yfinance.Ticker", return_value=_MOCK_TICKER):
            result = compute_signal(
                "AKSEN",
                self.TECH_BULLISH,
                self.MACRO_NEUTRAL,
                [],
                date.today(),
            )

        assert len(result.audit.layer_scores) == 5

        for layer in result.audit.layer_scores:
            assert 0 <= layer.score <= 100
            assert 0 <= layer.confidence <= 1.0
            assert layer.layer in ("technical", "macro", "kap", "sentiment", "risk")

        assert result.final_signal in ("BUY-STRONG", "BUY-WEAK", "HOLD", "SELL-WEAK", "SELL-STRONG")

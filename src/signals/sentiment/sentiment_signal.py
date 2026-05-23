"""Sentiment signal layer for signal engine.

Source priority (D-094 / SPEC_L4_NEWS_1):
  1. borsa-mcp → Mynet Finans → FinBERT  (primary)
  2. Yahoo Finance → VADER               (fallback when Mynet returns 0 articles)
"""

import logging

from src.signals.sentiment.news_aggregator import MynetNewsAggregator, NewsAggregator
from src.signals.sentiment.vader_analyzer import VaderSentimentAnalyzer

logger = logging.getLogger(__name__)


class SentimentSignal:
    """Calculate sentiment signal from news articles."""

    def __init__(self, cache_file: str = "data/sentiment_cache.json"):
        self.analyzer = VaderSentimentAnalyzer()
        self.aggregator = NewsAggregator(cache_file)

    def calculate(self, ticker: str, days: int = 7) -> dict:
        """Calculate sentiment signal for ticker.

        Returns dict with:
          score [0,100], normalized [-1,1], confidence [0,1],
          bullish_count, bearish_count, article_count,
          source ("computed"|"missing")
        """
        try:
            mynet_agg = MynetNewsAggregator()
            result = mynet_agg.aggregate(ticker, days)

            if result["article_count"] == 0:
                logger.info("%s: Mynet returned 0 articles, falling back to Yahoo", ticker)
                result = self._yahoo_fallback(ticker, days)
            else:
                # Preserve actual source in news_source; normalize top-level source
                # for backward compat (tests assert source in "computed"|"missing")
                result["news_source"] = result.get("source", "mynet_finans")
                result["source"] = "computed"

            logger.debug(
                "%s: sentiment score=%.1f conf=%.3f articles=%d source=%s",
                ticker, result["score"], result["confidence"],
                result["article_count"], result.get("source", "?"),
            )
            return result

        except Exception as exc:
            logger.exception("%s: sentiment calculation failed: %s", ticker, exc)
            return {
                "score": 50.0,
                "normalized": 0.0,
                "confidence": 0.0,
                "bullish_count": 0,
                "bearish_count": 0,
                "article_count": 0,
                "source": "missing",
            }

    def _yahoo_fallback(self, ticker: str, days: int) -> dict:
        """Legacy Yahoo Finance + VADER path (unchanged logic)."""
        articles = self.aggregator.fetch_news(ticker, days)

        if not articles:
            logger.warning("%s: no news articles available (Yahoo fallback)", ticker)
            return {
                "score": 50.0,
                "normalized": 0.0,
                "confidence": 0.0,
                "bullish_count": 0,
                "bearish_count": 0,
                "article_count": 0,
                "source": "missing",
            }

        agg = self.aggregator.aggregate_sentiment(articles, self.analyzer)
        signal_score = agg["normalized"] * 100

        bullish_ratio = agg["bullish"] / agg["count"] if agg["count"] > 0 else 0
        bearish_ratio = agg["bearish"] / agg["count"] if agg["count"] > 0 else 0
        agreement = max(bullish_ratio, bearish_ratio, 1 - bullish_ratio - bearish_ratio)
        article_confidence = min(agg["count"] / 5, 1.0)
        confidence = (article_confidence + agreement) / 2

        logger.info(
            "%s: Yahoo sentiment %.3f (bullish=%d bearish=%d conf=%.3f)",
            ticker, agg["score"], agg["bullish"], agg["bearish"], confidence,
        )

        return {
            "score": round(signal_score, 4),
            "normalized": round(agg["score"], 4),
            "confidence": round(confidence, 4),
            "bullish_count": agg["bullish"],
            "bearish_count": agg["bearish"],
            "article_count": agg["count"],
            "source": "computed",
        }

    def batch_calculate(self, tickers: list, days: int = 7) -> dict[str, dict]:
        """
        Calculate sentiment for multiple tickers.

        Args:
            tickers: List of stock tickers
            days: Days lookback

        Returns:
            Dict mapping ticker -> sentiment signal dict
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.calculate(ticker, days)
        return results

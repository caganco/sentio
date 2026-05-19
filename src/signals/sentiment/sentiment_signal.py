"""Sentiment signal layer for signal engine."""

import logging

from src.signals.sentiment.news_aggregator import NewsAggregator
from src.signals.sentiment.vader_analyzer import VaderSentimentAnalyzer

logger = logging.getLogger(__name__)


class SentimentSignal:
    """Calculate sentiment signal from news articles."""

    def __init__(self, cache_file: str = "data/sentiment_cache.json"):
        """
        Initialize sentiment signal.

        Args:
            cache_file: Path to sentiment cache
        """
        self.analyzer = VaderSentimentAnalyzer()
        self.aggregator = NewsAggregator(cache_file)

    def calculate(self, ticker: str, days: int = 7) -> dict:
        """
        Calculate sentiment signal for ticker.

        Args:
            ticker: Stock ticker
            days: Days lookback for news

        Returns:
            Dict with:
            - score: signal score [0, 100] (50=neutral)
            - normalized: original sentiment [-1, 1]
            - confidence: signal confidence [0, 1]
            - bullish_count: number of bullish articles
            - bearish_count: number of bearish articles
            - article_count: total articles analyzed
            - source: "computed" or "missing"
        """
        try:
            # Fetch news articles
            articles = self.aggregator.fetch_news(ticker, days)

            if not articles:
                logger.warning(f"{ticker}: no news articles available")
                return {
                    "score": 50.0,  # neutral
                    "normalized": 0.0,
                    "confidence": 0.0,
                    "bullish_count": 0,
                    "bearish_count": 0,
                    "article_count": 0,
                    "source": "missing",
                }

            # Aggregate sentiment
            agg = self.aggregator.aggregate_sentiment(articles, self.analyzer)

            # Convert normalized [0, 1] to signal score [0, 100]
            signal_score = agg["normalized"] * 100

            # Confidence based on article count and agreement
            bullish_ratio = (
                agg["bullish"] / agg["count"] if agg["count"] > 0 else 0
            )
            bearish_ratio = (
                agg["bearish"] / agg["count"] if agg["count"] > 0 else 0
            )
            agreement = max(bullish_ratio, bearish_ratio, 1 - bullish_ratio - bearish_ratio)

            # Confidence = f(article_count, agreement)
            # More articles + stronger agreement = higher confidence
            article_confidence = min(agg["count"] / 5, 1.0)  # Max at 5+ articles
            agreement_confidence = agreement
            confidence = (article_confidence + agreement_confidence) / 2

            logger.info(
                f"{ticker}: sentiment {agg['score']:.3f} (bullish={agg['bullish']}, "
                f"bearish={agg['bearish']}, neutral={agg['count']-agg['bullish']-agg['bearish']}, "
                f"confidence={confidence:.3f})"
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

        except Exception as e:
            logger.exception(f"{ticker}: sentiment calculation failed: {e}")
            return {
                "score": 50.0,
                "normalized": 0.0,
                "confidence": 0.0,
                "bullish_count": 0,
                "bearish_count": 0,
                "article_count": 0,
                "source": "missing",
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

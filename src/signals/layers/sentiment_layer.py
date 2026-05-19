"""Sentiment signal layer for signal engine."""

import logging

from src.signals.models import LayerScore
from src.signals.sentiment.sentiment_signal import SentimentSignal
from src.signals.thresholds import MASTER_WEIGHTS

logger = logging.getLogger(__name__)


def score_sentiment(symbol: str, days: int = 7) -> LayerScore:
    """
    Calculate sentiment signal layer.

    Args:
        symbol: Stock ticker
        days: Days lookback for news

    Returns:
        LayerScore with sentiment analysis
    """
    try:
        sentiment = SentimentSignal()
        result = sentiment.calculate(symbol, days)

        # Convert from [0, 100] signal score to LayerScore
        score = result["score"]
        confidence = result["confidence"]
        source = result["source"]

        detail = {
            "normalized_sentiment": result["normalized"],
            "article_count": result["article_count"],
            "bullish_count": result["bullish_count"],
            "bearish_count": result["bearish_count"],
        }

        logger.debug(
            f"{symbol}: sentiment score={score:.1f}, confidence={confidence:.3f}, "
            f"articles={result['article_count']} (bullish={result['bullish_count']}, "
            f"bearish={result['bearish_count']})"
        )

        return LayerScore(
            layer="sentiment",
            score=score,
            confidence=confidence,
            weight=MASTER_WEIGHTS["sentiment"],  # base; engine confidence-scales
            detail=detail,
            source=source,
        )

    except Exception as e:
        logger.exception(f"{symbol}: sentiment layer failed: {e}")
        return LayerScore(
            layer="sentiment",
            score=50.0,  # neutral
            confidence=0.0,
            weight=MASTER_WEIGHTS["sentiment"],
            detail={"error": str(e)},
            source="missing",
        )

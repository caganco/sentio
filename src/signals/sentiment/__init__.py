"""Sentiment analysis layer for 7-layer intelligence stack."""

from .news_aggregator import NewsAggregator
from .sentiment_signal import SentimentSignal
from .vader_analyzer import VaderSentimentAnalyzer

__all__ = ["VaderSentimentAnalyzer", "NewsAggregator", "SentimentSignal"]

"""VADER sentiment analysis for financial news articles."""

import logging

from nltk.sentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


class VaderSentimentAnalyzer:
    """VADER sentiment analyzer optimized for financial news."""

    def __init__(self):
        """Initialize VADER sentiment analyzer."""
        try:
            self.sia = SentimentIntensityAnalyzer()
        except LookupError:
            import nltk
            nltk.download("vader_lexicon", quiet=True)
            self.sia = SentimentIntensityAnalyzer()

    def analyze_article(self, text: str) -> float:
        """
        Analyze sentiment of article text.

        Args:
            text: Article text (title + body preferred)

        Returns:
            Compound sentiment score [-1, 1] where:
            - < -0.5: Negative (bearish)
            - -0.5 to 0.5: Neutral (mixed)
            - > 0.5: Positive (bullish)
        """
        if not text or not isinstance(text, str):
            return 0.0

        scores = self.sia.polarity_scores(text)
        compound = scores.get("compound", 0.0)

        logger.debug(f"Sentiment: {compound:.3f} (pos={scores['pos']:.3f}, neg={scores['neg']:.3f}, neu={scores['neu']:.3f})")
        return compound

    def categorize_sentiment(self, score: float) -> str:
        """Categorize sentiment score into label."""
        if score < -0.5:
            return "bearish"
        elif score > 0.5:
            return "bullish"
        else:
            return "neutral"

    def batch_analyze(self, articles: list) -> dict:
        """
        Analyze multiple articles.

        Args:
            articles: List of dicts with 'text' key

        Returns:
            Dict with:
            - scores: list of sentiment scores
            - avg: average sentiment
            - count: total articles
        """
        if not articles:
            return {"scores": [], "avg": 0.0, "count": 0}

        scores = [self.analyze_article(article.get("text", "")) for article in articles]
        avg = sum(scores) / len(scores) if scores else 0.0

        return {"scores": scores, "avg": avg, "count": len(scores)}

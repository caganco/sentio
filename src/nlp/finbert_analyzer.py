"""FinBERT analyzer for L4 News pipeline (D-094 / SPEC_L4_NEWS_1).

Wraps FinBERTSentimentModel (src/nlp/sentiment_model.py) to produce
ScoredArticle objects with relevance weighting and recency decay.

Phase 1 language note: ProsusAI/finbert is English-trained; Mynet Finans
articles are Turkish. Accuracy ~55-65%. L4 confidence formula dampens
weak/mixed signals via agreement and quality components, making Phase 1
acceptable. Turkish BERT integration is a separate micro-SPEC.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.nlp.sentiment_model import DummyDistilBERTAnalyzer, get_sentiment_model
from src.signals.thresholds import (
    L4_BEARISH_THRESHOLD,
    L4_BULLISH_THRESHOLD,
    L4_FINBERT_MAX_TOKENS,
    L4_NEWS_RECENCY_DECAY,
)

logger = logging.getLogger(__name__)


@dataclass
class ScoredArticle:
    """Article with FinBERT score, relevance, and recency weight."""
    title: str
    sentiment_raw: float        # normalized [-1, 1]
    finbert_confidence: float   # FinBERT model confidence [0, 1]
    relevance_weight: float     # from TickerMatcher [0.10, 1.00]
    recency_weight: float       # L4_NEWS_RECENCY_DECAY ^ age_days
    effective_weight: float     # relevance × recency × finbert_confidence
    label: str                  # "bullish" | "bearish" | "neutral"
    source: str = "finbert"


class FinBERTAnalyzer:
    """Score matched articles with FinBERT and compute weighted sentiment.

    Falls back to DummyDistilBERTAnalyzer when transformers unavailable —
    dummy mode halves finbert_confidence output (×0.5 penalty).
    """

    def __init__(self) -> None:
        self._model = get_sentiment_model(model_type="finbert", fallback_to_dummy=True)
        self._is_dummy = isinstance(self._model, DummyDistilBERTAnalyzer)
        if self._is_dummy:
            logger.warning(
                "FinBERTAnalyzer: using DummyDistilBERT fallback — "
                "confidence output penalized (×0.5)"
            )

    def score_articles(self, matched_articles: list) -> list[ScoredArticle]:
        """Batch-score MatchedArticle list. Returns ScoredArticle list."""
        if not matched_articles:
            return []

        texts = [
            ma.article.full_text[:L4_FINBERT_MAX_TOKENS]
            for ma in matched_articles
        ]
        raw_results = self._model.analyze_batch(texts)

        scored = []
        for ma, result in zip(matched_articles, raw_results):
            label_raw = result["label"]   # "POSITIVE" | "NEGATIVE" | "NEUTRAL"
            fb_score = result["score"]    # [0, 1] — class probability

            # Map to normalized [-1, 1]:
            # POSITIVE: fb_score=1.0 → +1.0, fb_score=0.5 → 0.0
            # NEGATIVE: fb_score=1.0 → -1.0, fb_score=0.5 → 0.0
            # NEUTRAL:  0.0
            if label_raw == "POSITIVE":
                sentiment_norm = fb_score * 2.0 - 1.0
            elif label_raw == "NEGATIVE":
                sentiment_norm = -(fb_score * 2.0 - 1.0)
            else:
                sentiment_norm = 0.0

            sentiment_norm = max(-1.0, min(1.0, sentiment_norm))

            effective_fb_conf = fb_score * (0.5 if self._is_dummy else 1.0)

            recency = L4_NEWS_RECENCY_DECAY ** ma.article.age_days
            eff_weight = ma.relevance_weight * recency * effective_fb_conf

            if sentiment_norm > L4_BULLISH_THRESHOLD:
                label = "bullish"
            elif sentiment_norm < L4_BEARISH_THRESHOLD:
                label = "bearish"
            else:
                label = "neutral"

            scored.append(ScoredArticle(
                title=ma.article.title,
                sentiment_raw=round(sentiment_norm, 4),
                finbert_confidence=round(effective_fb_conf, 4),
                relevance_weight=ma.relevance_weight,
                recency_weight=round(recency, 4),
                effective_weight=round(eff_weight, 4),
                label=label,
                source="dummy_distilbert" if self._is_dummy else "finbert",
            ))

        return scored

    def compute_weighted_sentiment(self, scored: list[ScoredArticle]) -> float:
        """Σ(sentiment × effective_weight) / Σ(effective_weight). Returns 0.0 if empty."""
        total_w = sum(s.effective_weight for s in scored)
        if total_w == 0.0:
            return 0.0
        return sum(s.sentiment_raw * s.effective_weight for s in scored) / total_w

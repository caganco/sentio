"""Tests for TurkishHybridAnalyzer (D-124) — Tier-1 + Tier-2 orchestration."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.nlp.finbert_analyzer import ScoredArticle, TurkishHybridAnalyzer


# ---------------------------------------------------------------------------
# Helpers — MatchedArticle mock (mirrors src.data.news_fetcher structure)
# ---------------------------------------------------------------------------

def _make_article(title: str, body: str = "", age_days: float = 0.0) -> SimpleNamespace:
    article = SimpleNamespace(
        title=title,
        body=body,
        full_text=f"{title}. {body}".strip(". ") if body else title,
        age_days=age_days,
    )
    return article


def _make_matched(title: str, body: str = "", age_days: float = 0.0,
                  relevance_weight: float = 1.0, match_type: str = "exact_ticker"):
    return SimpleNamespace(
        article=_make_article(title, body, age_days),
        match_type=match_type,
        relevance_weight=relevance_weight,
    )


@pytest.fixture
def analyzer():
    return TurkishHybridAnalyzer()


# ---------------------------------------------------------------------------
# score_articles() — basic correctness
# ---------------------------------------------------------------------------

class TestScoreArticles:
    def test_empty_list_returns_empty(self, analyzer):
        assert analyzer.score_articles([]) == []

    def test_returns_list_of_scored_articles(self, analyzer):
        ma = _make_matched("GARAN rekor kar açıkladı")
        result = analyzer.score_articles([ma])
        assert len(result) == 1
        assert isinstance(result[0], ScoredArticle)

    def test_definite_bullish_label(self, analyzer):
        ma = _make_matched("GARAN rekor kar artışı beklenti üzeri")
        result = analyzer.score_articles([ma])
        assert result[0].label == "bullish"
        assert result[0].finbert_confidence == 0.85
        assert result[0].source == "lexicon_tier1"

    def test_definite_bearish_label(self, analyzer):
        ma = _make_matched("EKGYO konkordato ilan etti iflas tehlikesi")
        result = analyzer.score_articles([ma])
        assert result[0].label == "bearish"
        assert result[0].finbert_confidence == 0.85
        assert result[0].source == "lexicon_tier1"

    def test_neutral_article_confidence(self, analyzer):
        ma = _make_matched("Toplantı tarihi belirsiz kaldı")
        result = analyzer.score_articles([ma])
        # May be neutral or ambiguous depending on term match
        assert isinstance(result[0].finbert_confidence, float)
        assert 0.0 <= result[0].finbert_confidence <= 1.0

    def test_scored_article_fields_present(self, analyzer):
        ma = _make_matched("AKBNK kar artışı", relevance_weight=0.85, age_days=1.0)
        result = analyzer.score_articles([ma])
        s = result[0]
        assert hasattr(s, "title")
        assert hasattr(s, "sentiment_raw")
        assert hasattr(s, "finbert_confidence")
        assert hasattr(s, "relevance_weight")
        assert hasattr(s, "recency_weight")
        assert hasattr(s, "effective_weight")
        assert hasattr(s, "label")
        assert hasattr(s, "source")

    def test_relevance_weight_propagated(self, analyzer):
        ma = _make_matched("GARAN rekor kar artışı beklenti üzeri",
                           relevance_weight=0.5)
        result = analyzer.score_articles([ma])
        assert result[0].relevance_weight == 0.5

    def test_recency_decay_applied(self, analyzer):
        ma_fresh = _make_matched("GARAN rekor kar artışı beklenti üzeri", age_days=0.0)
        ma_old = _make_matched("GARAN rekor kar artışı beklenti üzeri", age_days=3.0)
        r_fresh = analyzer.score_articles([ma_fresh])[0]
        r_old = analyzer.score_articles([ma_old])[0]
        assert r_fresh.recency_weight > r_old.recency_weight
        assert r_fresh.effective_weight > r_old.effective_weight

    def test_sentiment_raw_clamped_to_minus1_plus1(self, analyzer):
        ma = _make_matched("rekor kar rekor kar rekor kar rekor kar rekor")
        result = analyzer.score_articles([ma])
        assert -1.0 <= result[0].sentiment_raw <= 1.0


# ---------------------------------------------------------------------------
# Tier routing — definite/neutral bypass Tier-2
# ---------------------------------------------------------------------------

class TestTierRouting:
    def test_definite_does_not_call_tier2(self, analyzer):
        ma = _make_matched("GARAN rekor kar artışı beklenti üzeri")
        with patch.object(analyzer._tier2, "analyze") as mock_analyze:
            analyzer.score_articles([ma])
            mock_analyze.assert_not_called()

    def test_neutral_does_not_call_tier2(self, analyzer):
        ma = _make_matched("Toplantı tarihi belirsiz kaldı")
        # Force neutral by checking score
        raw = analyzer._tier1.score(ma.article.full_text)
        tier = analyzer._tier1.tier(raw)
        if tier == "neutral":
            with patch.object(analyzer._tier2, "analyze") as mock_analyze:
                analyzer.score_articles([ma])
                mock_analyze.assert_not_called()

    def test_ambiguous_calls_tier2(self, analyzer):
        # Build an article guaranteed to be ambiguous
        from src.signals.thresholds import LEXICON_TIER1_HIGH, LEXICON_TIER1_LOW

        ma = _make_matched("güçlü")  # score=1.2, might be ambiguous or definite
        raw = analyzer._tier1.score(ma.article.full_text)
        tier = analyzer._tier1.tier(raw)

        if tier == "ambiguous":
            mock_result = {"label": "POSITIVE", "score": 0.75, "reason": "test"}
            with patch.object(analyzer._tier2, "analyze", return_value=mock_result) as mock_an:
                analyzer.score_articles([ma])
                mock_an.assert_called_once()

    def test_ambiguous_tier2_result_used(self, analyzer):
        # Create a mock tier1 that returns ambiguous tier
        ma = _make_matched("some text")
        mock_tier1 = MagicMock()
        mock_tier1.score.return_value = 0.5   # ambiguous
        mock_tier1.tier.return_value = "ambiguous"
        analyzer._tier1 = mock_tier1

        mock_result = {"label": "POSITIVE", "score": 0.80, "reason": "test"}
        with patch.object(analyzer._tier2, "analyze", return_value=mock_result):
            result = analyzer.score_articles([ma])

        assert result[0].source == "claude_haiku"
        assert result[0].label == "bullish"  # POSITIVE → bullish

    def test_tier2_neutral_result_gives_neutral_label(self, analyzer):
        ma = _make_matched("some text")
        mock_tier1 = MagicMock()
        mock_tier1.score.return_value = 0.5
        mock_tier1.tier.return_value = "ambiguous"
        analyzer._tier1 = mock_tier1

        mock_result = {"label": "NEUTRAL", "score": 0.50, "reason": "neutral"}
        with patch.object(analyzer._tier2, "analyze", return_value=mock_result):
            result = analyzer.score_articles([ma])

        assert result[0].label == "neutral"
        assert result[0].finbert_confidence == 0.50


# ---------------------------------------------------------------------------
# compute_weighted_sentiment()
# ---------------------------------------------------------------------------

class TestComputeWeightedSentiment:
    def _make_scored(self, sentiment: float, weight: float) -> ScoredArticle:
        return ScoredArticle(
            title="test",
            sentiment_raw=sentiment,
            finbert_confidence=0.8,
            relevance_weight=1.0,
            recency_weight=1.0,
            effective_weight=weight,
            label="bullish" if sentiment > 0 else "bearish",
            source="lexicon_tier1",
        )

    def test_empty_returns_zero(self, analyzer):
        assert analyzer.compute_weighted_sentiment([]) == 0.0

    def test_zero_total_weight_returns_zero(self, analyzer):
        s = self._make_scored(0.8, 0.0)
        assert analyzer.compute_weighted_sentiment([s]) == 0.0

    def test_single_article(self, analyzer):
        s = self._make_scored(0.6, 1.0)
        result = analyzer.compute_weighted_sentiment([s])
        assert abs(result - 0.6) < 1e-6

    def test_weighted_average(self, analyzer):
        s1 = self._make_scored(0.8, 2.0)  # weight 2
        s2 = self._make_scored(0.2, 1.0)  # weight 1
        # Expected: (0.8*2 + 0.2*1) / (2+1) = 1.8/3 = 0.6
        result = analyzer.compute_weighted_sentiment([s1, s2])
        assert abs(result - 0.6) < 1e-6

    def test_end_to_end_with_score_articles(self, analyzer):
        articles = [
            _make_matched("GARAN rekor kar artışı beklenti üzeri"),
            _make_matched("GARAN güçlü büyüme olumlu"),
        ]
        scored = analyzer.score_articles(articles)
        result = analyzer.compute_weighted_sentiment(scored)
        # Both strongly bullish → weighted sentiment > 0
        assert result > 0.0

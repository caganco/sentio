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


# =============================================================================
# D-124 — Hybrid Turkish NLP (Tier-1 lexicon + Tier-2 Claude Haiku 4.5)
# =============================================================================

class TurkishLexiconScorer:
    """Tier-1: Loughran-McDonald Turkish financial lexicon scorer (D-124).

    Scores article text using a weighted term dictionary.
    Negation window: flips weight when negation appears within 60 chars before term.
    """

    def __init__(self) -> None:
        from src.data.lexicon.turkish_financial_lexicon import (
            BEARISH_TERMS,
            BULLISH_TERMS,
            NEGATION_PATTERN,
            NEGATION_WINDOW,
        )
        from src.signals.thresholds import LEXICON_TIER1_HIGH, LEXICON_TIER1_LOW

        self._terms: dict[str, float] = {**BULLISH_TERMS, **BEARISH_TERMS}
        self._negation_re = NEGATION_PATTERN
        self._neg_window = NEGATION_WINDOW
        self._tier1_high = LEXICON_TIER1_HIGH
        self._tier1_low = LEXICON_TIER1_LOW

    def score(self, text: str) -> float:
        """Raw lexicon score: positive=bullish, negative=bearish."""
        text_lower = text.lower()
        total = 0.0
        for term, weight in self._terms.items():
            idx = text_lower.find(term)
            if idx == -1:
                continue
            # Turkish negation follows the term ("kar değil") — check after-window.
            # Also check pre-window for compound forms ("sona erdi", "iptal").
            after_start = idx + len(term)
            window_after = text_lower[after_start:after_start + self._neg_window]
            window_before = text_lower[max(0, idx - self._neg_window):idx]
            negated = bool(
                self._negation_re.search(window_after)
                or self._negation_re.search(window_before)
            )
            total += (-weight if negated else weight)
        return total

    def tier(self, raw_score: float) -> str:
        """Classify score: 'definite' | 'neutral' | 'ambiguous'."""
        abs_s = abs(raw_score)
        if abs_s > self._tier1_high:
            return "definite"
        if abs_s <= self._tier1_low:
            return "neutral"
        return "ambiguous"


class ClaudeHaikuAnalyzer:
    """Tier-2: Claude Haiku 4.5 for ambiguous sentiment (D-124).

    temperature=0.0, structured JSON output, prompt caching on system prompt.
    Model: claude-haiku-4-5-20251001. Falls back to NEUTRAL on any error.
    """

    _SYSTEM = (
        "Türk finansal haberleri için duygu analizi yapıyorsun. "
        "Sadece JSON formatında yanıt ver: "
        '{"label": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": 0.0-1.0, "reason": "kısa açıklama"}\n\n'
        "Örnekler:\n"
        '- "GARAN 3. çeyrekte %23 kâr artışı açıkladı" → {"label": "POSITIVE", "score": 0.82, "reason": "kar artisi"}\n'
        '- "ASELS hakkında SPK soruşturması başlatıldı" → {"label": "NEGATIVE", "score": 0.78, "reason": "duzenleyici sorusturma"}\n'
        '- "BIMAS yönetim kurulu toplantı tarihini açıkladı" → {"label": "NEUTRAL", "score": 0.50, "reason": "bilgilendirme"}'
    )

    def __init__(self) -> None:
        from src.signals.thresholds import HAIKU_MAX_RETRIES, HAIKU_TIMEOUT_S

        self._model = "claude-haiku-4-5-20251001"
        self._timeout = HAIKU_TIMEOUT_S
        self._retries = HAIKU_MAX_RETRIES

    def analyze(self, text: str) -> dict:
        """Returns {"label": str, "score": float, "reason": str}. Fallback: NEUTRAL 0.5."""
        import json

        try:
            import anthropic

            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=self._model,
                max_tokens=120,
                temperature=0.0,
                system=[
                    {
                        "type": "text",
                        "text": self._SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": text[:512]}],
            )
            return json.loads(resp.content[0].text)
        except Exception:
            return {"label": "NEUTRAL", "score": 0.5, "reason": "error"}


class TurkishHybridAnalyzer:
    """Hybrid Tier-1 (Turkish lexicon) + Tier-2 (Claude Haiku 4.5) analyzer (D-124).

    Drop-in replacement for FinBERTAnalyzer — identical score_articles() /
    compute_weighted_sentiment() interface. Tier-1 handles definite/neutral cases
    offline; Tier-2 is called only for ambiguous cases.
    """

    def __init__(self) -> None:
        self._tier1 = TurkishLexiconScorer()
        self._tier2 = ClaudeHaikuAnalyzer()

    def score_articles(self, matched_articles: list) -> list[ScoredArticle]:
        """Hybrid-score MatchedArticle list. Returns ScoredArticle list."""
        if not matched_articles:
            return []

        from src.signals.thresholds import (
            L4_BEARISH_THRESHOLD,
            L4_BULLISH_THRESHOLD,
            L4_NEWS_RECENCY_DECAY,
        )

        scored: list[ScoredArticle] = []
        for ma in matched_articles:
            text = ma.article.full_text[:512] if ma.article.full_text else ma.article.title

            raw = self._tier1.score(text)
            tier = self._tier1.tier(raw)

            if tier == "definite":
                norm = max(-1.0, min(1.0, raw / 2.0))
                conf = 0.85
                source_tag = "lexicon_tier1"
            elif tier == "neutral":
                norm = 0.0
                conf = 0.60
                source_tag = "lexicon_tier1"
            else:  # ambiguous → Tier-2
                h = self._tier2.analyze(text)
                h_label = h.get("label", "NEUTRAL")
                h_score = float(h.get("score", 0.5))
                if h_label == "POSITIVE":
                    norm = max(-1.0, min(1.0, h_score * 2.0 - 1.0))
                elif h_label == "NEGATIVE":
                    norm = max(-1.0, min(1.0, -(h_score * 2.0 - 1.0)))
                else:
                    norm = 0.0
                conf = h_score if h_label != "NEUTRAL" else 0.50
                source_tag = "claude_haiku"

            recency = L4_NEWS_RECENCY_DECAY ** ma.article.age_days
            eff_weight = ma.relevance_weight * recency * conf

            if norm > L4_BULLISH_THRESHOLD:
                label = "bullish"
            elif norm < L4_BEARISH_THRESHOLD:
                label = "bearish"
            else:
                label = "neutral"

            scored.append(ScoredArticle(
                title=ma.article.title,
                sentiment_raw=round(norm, 4),
                finbert_confidence=round(conf, 4),
                relevance_weight=ma.relevance_weight,
                recency_weight=round(recency, 4),
                effective_weight=round(eff_weight, 4),
                label=label,
                source=source_tag,
            ))

        return scored

    def compute_weighted_sentiment(self, scored: list[ScoredArticle]) -> float:
        """Σ(sentiment × effective_weight) / Σ(effective_weight). Returns 0.0 if empty."""
        total_w = sum(s.effective_weight for s in scored)
        if total_w == 0.0:
            return 0.0
        return sum(s.sentiment_raw * s.effective_weight for s in scored) / total_w

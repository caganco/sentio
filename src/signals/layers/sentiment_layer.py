"""Sentiment layer — STUB. Returns NEUTRAL pass-through until implemented."""
from src.signals.models import LayerScore
from src.signals.thresholds import MASTER_WEIGHTS


def score_sentiment(sentiment_data: dict | None = None) -> LayerScore:
    return LayerScore(layer="sentiment", score=50.0, confidence=0.0,
                      weight=MASTER_WEIGHTS["sentiment"],
                      detail={"status": "not_implemented", "planned": "social_media_scraper"},
                      source="missing")

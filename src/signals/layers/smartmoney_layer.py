"""Smart money layer — STUB. Returns NEUTRAL pass-through until implemented."""
from src.signals.models import LayerScore
from src.signals.thresholds import MASTER_WEIGHTS


def score_smartmoney(smartmoney_data: dict | None = None) -> LayerScore:
    return LayerScore(layer="smart_money", score=50.0, confidence=0.0,
                      weight=MASTER_WEIGHTS["smart_money"],
                      detail={"status": "not_implemented", "planned": "bist_takas_scraper"},
                      source="missing")

"""Shared signal computation utilities (D-149c, RR-018 §8.2(b)).

Pure, stateless, side-effect yok.
K-08: Bu modül src.signals.engine'den IMPORT EDEMEZ (circular bagimlılık onlemi).
Her iki engine (production + backtest) bu modulu paylasir.

Dayanak: SPEC_BACKTEST_FRAMEWORK_1 §B1-S3; RR-018 §8.2(b)
"""
from __future__ import annotations

from src.signals.thresholds import (
    KELLY_WIN_PROB_BASE,
    KELLY_WIN_PROB_SLOPE,
    MASTER_WEIGHTS,
    SIGNAL_THRESHOLDS,
)

__all__ = [
    "compute_composite_score",
    "validate_weights",
    "signal_from_composite",
    "kelly_win_prob",
]


def compute_composite_score(
    layer_scores: dict[str, float],
    weights: dict[str, float] | None = None,
    confidence_scaling: dict[str, float] | None = None,
) -> float:
    """Agirlikli ortalama composite skor hesaplar (0-100).

    Sigma(score_i x weight_i x conf_i) / Sigma(weight_i x conf_i)
    Sifir agirlik -> 50.0 (neutral fallback).

    Args:
        layer_scores: {layer_key: score_0_100}
        weights:      {layer_key: weight} — None -> MASTER_WEIGHTS kullanilir
        confidence_scaling: {layer_key: conf_0_1} — None -> tumu 1.0
    """
    w = weights if weights is not None else MASTER_WEIGHTS
    conf = confidence_scaling or {}
    total_weight = 0.0
    weighted = 0.0
    for layer, score in layer_scores.items():
        if layer not in w:
            continue
        effective_weight = w[layer] * conf.get(layer, 1.0)
        total_weight += effective_weight
        weighted += score * effective_weight
    if total_weight == 0.0:
        return 50.0
    return round(max(0.0, min(100.0, weighted / total_weight)), 4)


def validate_weights(weights: dict[str, float]) -> bool:
    """Toplam agirlik [0.85, 1.05] araliginda mi kontrol eder.

    DEC-009: efektif Sigma in [0.78, 1.00] (conf scaling sonrasi).
    Statik MASTER_WEIGHTS toplami = 1.00 -> her zaman True doner.
    """
    total = sum(weights.values())
    return 0.85 <= total <= 1.05


def signal_from_composite(composite: float) -> str:
    """Composite skoru -> sinyal stringine gevirir.

    SIGNAL_THRESHOLDS tablosu kullanilir (thresholds.py tek kaynak).
    Returns: "BUY-STRONG" | "BUY-WEAK" | "HOLD" | "SELL-WEAK" | "SELL-STRONG"
    """
    if composite >= SIGNAL_THRESHOLDS["buy_strong"]:
        return "BUY-STRONG"
    if composite >= SIGNAL_THRESHOLDS["buy_weak"]:
        return "BUY-WEAK"
    if composite >= SIGNAL_THRESHOLDS["hold_lower"]:
        return "HOLD"
    if composite >= SIGNAL_THRESHOLDS["sell_weak"]:
        return "SELL-WEAK"
    return "SELL-STRONG"


def kelly_win_prob(composite: float) -> float:
    """Composite skora dayali linear Kelly kazanma olasiligi (0.0-1.0).

    p = KELLY_WIN_PROB_BASE + (composite - 50) x KELLY_WIN_PROB_SLOPE
    composite=50  -> p=0.50 (neutral)
    composite=100 -> p=0.75 (max)
    composite=0   -> p=0.25 (min)
    """
    p = KELLY_WIN_PROB_BASE + (composite - 50.0) * KELLY_WIN_PROB_SLOPE
    return max(0.0, min(1.0, p))

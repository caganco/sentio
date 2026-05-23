"""Technical layer: RSI, MA, momentum → LayerScore 0-100."""
from __future__ import annotations

from src.signals.models import LayerScore
from src.signals.thresholds import (
    MA_SCORES,
    MASTER_WEIGHTS,
    PROXIMITY_HIGH_SCORE,
    PROXIMITY_HIGH_THRESHOLD,
    PROXIMITY_LOW_SCORE,
    PROXIMITY_LOW_THRESHOLD,
    PROXIMITY_NEUTRAL_SCORE,
    RSI_SCORES,
    RSI_THRESHOLDS,
    VOLUME_NO_SURGE_SCORE,
    VOLUME_SURGE_SCORE,
)


def _rsi_sub_score(rsi: float) -> float:
    if rsi > RSI_THRESHOLDS["overbought"]:
        return RSI_SCORES["extreme_overbought"]
    if rsi > RSI_THRESHOLDS["mild_overbought"]:
        return RSI_SCORES["overbought"]
    if rsi > RSI_THRESHOLDS["neutral_upper"]:
        return RSI_SCORES["mild_bullish"]
    if rsi > RSI_THRESHOLDS["weak_bearish"]:
        return RSI_SCORES["neutral"]
    if rsi > RSI_THRESHOLDS["oversold"]:
        return RSI_SCORES["weak_bearish"]
    return RSI_SCORES["oversold"]


def _ma_sub_score(close: float, ma20: float | None, ma50: float | None, ma200: float | None) -> float:
    above = sum(
        1 for ma in (ma20, ma50, ma200)
        if ma is not None and close > ma
    )
    return MA_SCORES[above]


def _momentum_sub_score(momentum_score: float | None) -> float:
    """momentum_score from momentum.py is already 0-based; map to 0-100 range."""
    if momentum_score is None:
        return 50.0
    # momentum_score is typically -0.3 to +0.3; map linearly to 0-100
    clamped = max(-1.0, min(1.0, momentum_score))
    return round((clamped + 1.0) / 2.0 * 100.0, 4)


def _volume_sub_score(volume_surge: bool | None) -> float:
    return VOLUME_SURGE_SCORE if volume_surge else VOLUME_NO_SURGE_SCORE


def _proximity_sub_score(proximity_below_52w_high: float | None) -> float:
    """proximity_below_52w_high: 0 = at 52w high, 0.10 = 10% below."""
    if proximity_below_52w_high is None:
        return PROXIMITY_NEUTRAL_SCORE
    price_ratio = 1.0 - proximity_below_52w_high
    if price_ratio > PROXIMITY_HIGH_THRESHOLD:
        return PROXIMITY_HIGH_SCORE
    if proximity_below_52w_high < PROXIMITY_LOW_THRESHOLD:
        return PROXIMITY_LOW_SCORE
    return PROXIMITY_NEUTRAL_SCORE


def score_technical(technical_data: dict) -> LayerScore:
    """Produce 0-100 LayerScore from technical_data dict (src/analysis/ output)."""
    detail: dict = {}
    sub_scores: list[float] = []
    partial = False

    rsi = technical_data.get("rsi")
    if rsi is not None:
        rsi_sub = _rsi_sub_score(float(rsi))
        detail["rsi"] = rsi
        detail["rsi_sub"] = rsi_sub
        sub_scores.append(rsi_sub)
    else:
        partial = True
        detail["rsi"] = None

    close = technical_data.get("close")
    ma20 = technical_data.get("ma20")
    ma50 = technical_data.get("ma50")
    ma200 = technical_data.get("ma200")
    if close is not None:
        ma_sub = _ma_sub_score(float(close), ma20, ma50, ma200)
        detail["ma_sub"] = ma_sub
        detail["ma20_above"] = ma20 is not None and close > ma20
        detail["ma50_above"] = ma50 is not None and close > ma50
        detail["ma200_above"] = ma200 is not None and close > ma200
        sub_scores.append(ma_sub)
    else:
        partial = True

    momentum_score = technical_data.get("momentum_score")
    mom_sub = _momentum_sub_score(momentum_score)
    detail["momentum_score"] = momentum_score
    detail["momentum_sub"] = mom_sub
    sub_scores.append(mom_sub)

    volume_surge = technical_data.get("volume_surge")
    vol_sub = _volume_sub_score(volume_surge)
    detail["volume_surge"] = volume_surge
    detail["volume_sub"] = vol_sub
    sub_scores.append(vol_sub)

    proximity = technical_data.get("proximity_52w_high")
    prox_sub = _proximity_sub_score(proximity)
    detail["proximity_52w_high"] = proximity
    detail["proximity_sub"] = prox_sub
    sub_scores.append(prox_sub)

    if not sub_scores:
        final_score = 50.0
        confidence = 0.3
    else:
        final_score = round(sum(sub_scores) / len(sub_scores), 4)
        confidence = 0.5 if partial else 1.0

    return LayerScore(
        layer="technical",
        score=final_score,
        confidence=confidence,
        weight=MASTER_WEIGHTS["technical"],
        detail=detail,
        source="computed" if not partial else "partial",
    )

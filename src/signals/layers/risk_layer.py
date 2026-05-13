"""Risk layer: score risk and detect macro regime."""
from __future__ import annotations

from src.signals.models import LayerScore, MacroRegime
from src.signals.thresholds import (
    MASTER_WEIGHTS,
    RISK_BASE_SCORE,
    RISK_OFF_CONDITIONS,
    RISK_RSI_OVERBOUGHT_PENALTY,
    RISK_USDTRY_SPIKE_PENALTY,
    RISK_USDTRY_SPIKE_THRESHOLD,
    RISK_VOLUME_ANOMALY_PENALTY,
    RISK_VIX_EXTREME_PENALTY,
    RISK_VIX_HIGH_PENALTY,
    RISK_VIX_HIGH_THRESHOLD,
    REGIME_RISK_ON_VIX_MAX,
    REGIME_NEUTRAL_VIX_MAX,
)


def score_risk(
    symbol: str,
    technical_data: dict,
    macro_data: dict,
) -> LayerScore:
    """Risk score: high = low risk = bullish. Base=70, penalties subtracted."""
    score = RISK_BASE_SCORE
    detail: dict = {}
    penalties_applied: list[str] = []

    rsi = technical_data.get("rsi")
    if rsi is not None and rsi > 80:
        score -= RISK_RSI_OVERBOUGHT_PENALTY
        detail["rsi_overbought"] = True
        detail["rsi"] = rsi
        penalties_applied.append(f"rsi_overbought(-{RISK_RSI_OVERBOUGHT_PENALTY})")
    else:
        detail["rsi_overbought"] = False
        if rsi is not None:
            detail["rsi"] = rsi

    volume_surge = technical_data.get("volume_surge", False)
    close = technical_data.get("close")
    prev_close = technical_data.get("prev_close")
    price_down = (
        close is not None and prev_close is not None and prev_close > 0
        and close < prev_close
    )
    if volume_surge and price_down:
        score -= RISK_VOLUME_ANOMALY_PENALTY
        detail["volume_anomaly"] = True
        penalties_applied.append(f"volume_anomaly(-{RISK_VOLUME_ANOMALY_PENALTY})")
    else:
        detail["volume_anomaly"] = False

    usdtry_change = macro_data.get("USDTRY_1d_change", macro_data.get("usdtry_1d_change"))
    if usdtry_change is not None and abs(usdtry_change) > RISK_USDTRY_SPIKE_THRESHOLD:
        score -= RISK_USDTRY_SPIKE_PENALTY
        detail["usdtry_spike"] = True
        detail["usdtry_change"] = round(usdtry_change, 4)
        penalties_applied.append(f"usdtry_spike(-{RISK_USDTRY_SPIKE_PENALTY})")
    else:
        detail["usdtry_spike"] = False

    # vix_level = raw VIX index value; "VIX" key may be a normalized score
    vix = macro_data.get("vix_level", macro_data.get("VIX_level"))
    if vix is None:
        # Fall back: if value > 1 it's a raw level not a normalized score
        _vix_raw = macro_data.get("VIX", macro_data.get("vix"))
        if _vix_raw is not None and abs(float(_vix_raw)) > 1.0:
            vix = float(_vix_raw)
    if vix is not None:
        detail["vix_level"] = round(float(vix), 2)
        if vix > RISK_OFF_CONDITIONS["vix_threshold"]:
            score -= RISK_VIX_EXTREME_PENALTY
            penalties_applied.append(f"vix_extreme(-{RISK_VIX_EXTREME_PENALTY})")
        elif vix > RISK_VIX_HIGH_THRESHOLD:
            score -= RISK_VIX_HIGH_PENALTY
            penalties_applied.append(f"vix_high(-{RISK_VIX_HIGH_PENALTY})")

    detail["penalties"] = penalties_applied
    final_score = round(max(0.0, min(100.0, score)), 4)

    return LayerScore(
        layer="risk",
        score=final_score,
        confidence=1.0,
        weight=MASTER_WEIGHTS["risk"],
        detail=detail,
        source="computed",
    )


def detect_regime(macro_data: dict) -> MacroRegime:
    """Detect RISK_ON / RISK_OFF / NEUTRAL from macro data.

    RISK_OFF if any RISK_OFF_CONDITIONS threshold is triggered.
    RISK_ON if VIX < 20 and USDTRY stable.
    NEUTRAL otherwise.
    """
    # vix_level = raw VIX index value (>1 means raw); "VIX" may be normalized score
    vix = macro_data.get("vix_level", macro_data.get("VIX_level"))
    if vix is None:
        _vix_raw = macro_data.get("VIX", macro_data.get("vix"))
        if _vix_raw is not None and abs(float(_vix_raw)) > 1.0:
            vix = float(_vix_raw)
    usdtry_change = macro_data.get("USDTRY_1d_change", macro_data.get("usdtry_1d_change", 0.0))
    bist100_change = macro_data.get("BIST100_1d_change", macro_data.get("bist100_1d_change", 0.0))

    if usdtry_change is None:
        usdtry_change = 0.0
    if bist100_change is None:
        bist100_change = 0.0

    risk_off = False
    if vix is not None and vix > RISK_OFF_CONDITIONS["vix_threshold"]:
        risk_off = True
    if usdtry_change > RISK_OFF_CONDITIONS["usdtry_1d_change"]:
        risk_off = True
    if bist100_change < RISK_OFF_CONDITIONS["bist100_1d_change"]:
        risk_off = True

    if risk_off:
        return "RISK_OFF"

    if vix is not None and vix < REGIME_RISK_ON_VIX_MAX and abs(usdtry_change) <= RISK_USDTRY_SPIKE_THRESHOLD:
        return "RISK_ON"

    return "NEUTRAL"

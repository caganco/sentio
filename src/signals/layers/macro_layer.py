"""Macro layer: global + local macro signals → LayerScore 0-100."""
from __future__ import annotations

from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.models import LayerScore
from src.signals.thresholds import ASSET_DIRECTIONS, LOCAL_MACRO_ENABLED, MACRO_WEIGHTS_COMPOSITE, MASTER_WEIGHTS


def score_macro(macro_data: dict) -> LayerScore:
    """Convert macro_signals.py output (scores in [-1, +1]) to LayerScore 0-100.

    Accepts two key formats:
    - ASSET_DIRECTIONS keys directly: {"USDTRY": -0.3, "VIX": -0.5, ...}
    - MacroSignal-style score keys:   {"vix_score": -0.5, "usdtry_score": -0.3, ...}

    ASSET_DIRECTIONS apply sign so BIST-bullish = positive contribution.

    If LOCAL_MACRO_ENABLED: composite with TCMB + CDS signals (50% global, 25% TCMB, 25% CDS).
    """
    # Normalise MacroSignal-style keys to ASSET_DIRECTIONS format
    score_key_map = {
        "vix_score": "VIX",
        "usdtry_score": "USDTRY",
        "brent_score": "BRENT",
        "bist100_score": "BIST100",
    }
    normalised: dict = dict(macro_data)
    for score_key, asset_key in score_key_map.items():
        if score_key in macro_data and asset_key not in macro_data:
            normalised[asset_key] = macro_data[score_key]

    detail: dict = {}
    weighted_sum = 0.0
    total_weight = 0.0
    missing_assets: list[str] = []

    for asset, direction in ASSET_DIRECTIONS.items():
        raw = normalised.get(asset, normalised.get(asset.lower()))
        if raw is None:
            missing_assets.append(asset)
            continue
        raw_f = float(raw)
        raw_f = max(-1.0, min(1.0, raw_f))
        adjusted = raw_f * direction
        weight = abs(direction)
        weighted_sum += adjusted * weight
        total_weight += weight
        detail[asset] = round(raw_f, 4)

    if total_weight == 0:
        return LayerScore(
            layer="macro",
            score=50.0,
            confidence=0.0,
            weight=MASTER_WEIGHTS["macro"],
            detail={"missing": list(ASSET_DIRECTIONS.keys())},
            source="missing",
        )

    normalized_signal = weighted_sum / total_weight
    global_score = round((normalized_signal + 1.0) / 2.0 * 100.0, 4)
    global_score = max(0.0, min(100.0, global_score))

    confidence = 1.0 if not missing_assets else 0.6
    if missing_assets:
        detail["missing_assets"] = missing_assets

    # Apply local macro signals if enabled
    if LOCAL_MACRO_ENABLED:
        local_signals = LocalMacroSignals()
        local_result = local_signals.score()

        # Composite: 50% global + 25% TCMB + 25% CDS + 0% foreign (stub)
        tcmb_contrib = (
            local_result.tcmb.score
            * local_result.tcmb.confidence
            * MACRO_WEIGHTS_COMPOSITE["tcmb"]
        )
        cds_contrib = (
            local_result.cds.score
            * local_result.cds.confidence
            * MACRO_WEIGHTS_COMPOSITE["cds"]
        )
        global_contrib = global_score * MACRO_WEIGHTS_COMPOSITE["global_signals"]

        final_score = global_contrib + tcmb_contrib + cds_contrib
        final_score = max(0.0, min(100.0, final_score))

        # Confidence: min of components
        min_conf = min(
            confidence,
            local_result.tcmb.confidence,
            local_result.cds.confidence,
        )

        detail["local_macro"] = {
            "tcmb": {
                "score": round(local_result.tcmb.score, 4),
                "conf": round(local_result.tcmb.confidence, 4),
                "msg": local_result.tcmb.audit_msg,
            },
            "cds": {
                "score": round(local_result.cds.score, 4),
                "conf": round(local_result.cds.confidence, 4),
                "msg": local_result.cds.audit_msg,
            },
        }
        detail["global_score"] = round(global_score, 4)
        detail["composite_score"] = round(final_score, 4)

        return LayerScore(
            layer="macro",
            score=final_score,
            confidence=min_conf,
            weight=MASTER_WEIGHTS["macro"],
            detail=detail,
            source="computed",
        )
    else:
        # Global signals only
        return LayerScore(
            layer="macro",
            score=global_score,
            confidence=confidence,
            weight=MASTER_WEIGHTS["macro"],
            detail=detail,
            source="computed",
        )

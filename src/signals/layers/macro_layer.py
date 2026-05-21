"""Macro layer: global + local macro signals → LayerScore 0-100."""
from __future__ import annotations

import logging

from src.signals.local_macro_signals import LocalMacroSignals
from src.signals.models import LayerScore
from src.signals.thresholds import (
    ASSET_DIRECTIONS,
    CDS_PERCENTILE_WINDOW,
    LOCAL_MACRO_ENABLED,
    MACRO_WEIGHTS_COMPOSITE,
    MASTER_WEIGHTS,
)

logger = logging.getLogger(__name__)


def _compute_cds_percentile(cds_history: list[dict] | None) -> float | None:
    """Percentile rank of the latest CDS value within trailing-window history.

    D-108 / SPEC_MACRO_GATE_SOFTENING_1. Returns None when len(history) < 30
    (insufficient data); callers should fall back to 0.5 (no dampening).

    history rows are cache dicts with key `cds_bps` (ascending by data_date).
    """
    if not cds_history or len(cds_history) < 30:
        return None
    values = [row.get("cds_bps") for row in cds_history if row.get("cds_bps") is not None]
    if len(values) < 30:
        return None
    latest = values[-1]
    rank = sum(1 for v in values if v <= latest) / len(values)
    return round(rank, 4)


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

        # D-108: CDS percentile from rolling window for audit + gate v2 callers.
        cds_percentile: float | None = None
        try:
            from src.signals.local.cache_store import LocalMacroCache
            history = LocalMacroCache().get_cds_history(days=CDS_PERCENTILE_WINDOW)
            cds_percentile = _compute_cds_percentile(history)
        except Exception as exc:
            logger.debug("CDS percentile compute failed (non-fatal): %s", exc)

        # Gap 3: DXY weight is redistributed to global_signals when DXY data
        # is absent (confidence=0) so the total effective weight stays at 1.0.
        dxy_conf = local_result.dxy.confidence
        global_w = MACRO_WEIGHTS_COMPOSITE["global_signals"]
        if dxy_conf == 0.0:
            global_w += MACRO_WEIGHTS_COMPOSITE["dxy"]

        global_contrib = global_score * global_w
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
        dxy_contrib = (
            local_result.dxy.score
            * dxy_conf
            * MACRO_WEIGHTS_COMPOSITE["dxy"]
        )

        final_score = global_contrib + tcmb_contrib + cds_contrib + dxy_contrib
        final_score = max(0.0, min(100.0, final_score))

        # Confidence: min of components with data (exclude absent DXY)
        conf_components = [confidence, local_result.tcmb.confidence, local_result.cds.confidence]
        if dxy_conf > 0.0:
            conf_components.append(dxy_conf)
        min_conf = min(conf_components)

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
                "percentile": cds_percentile,   # D-108: None when history < 30d
            },
            "dxy": {
                "score": round(local_result.dxy.score, 4),
                "conf": round(dxy_conf, 4),
                "msg": local_result.dxy.audit_msg,
            },
            "tl_bond_proxy": {
                "score": round(local_result.tl_bond_proxy.score, 4),
                "implied_yield": local_result.tl_bond_proxy.raw_value,
                "msg": local_result.tl_bond_proxy.audit_msg,
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

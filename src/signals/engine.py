"""Signal Engine: compute_signal() and compute_batch()."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from src.signals.layers.kap_layer import score_kap
from src.signals.layers.macro_layer import score_macro
from src.signals.layers.risk_layer import detect_regime, score_risk
from src.signals.layers.sentiment_layer import score_sentiment
from src.signals.layers.smart_money_layer import get_l5_layer
from src.signals.layers.technical_layer import score_technical
from src.signals.models import (
    AuditTrail,
    ConflictInfo,
    FinalSignal,
    LayerScore,
    MacroRegime,
    SIGNAL_ORDER,
    SignalResult,
)
from src.signals.conviction_validator import compute_conviction
from src.signals.thresholds import (
    CONFLICT_THRESHOLD,
    MASTER_WEIGHTS,
    SIGNAL_THRESHOLDS,
)

logger = logging.getLogger(__name__)


def _compute_weighted_sum(layer_scores: list[LayerScore]) -> float:
    """WeightedSum = Σ(score_i × weight_i) / Σ(weight_i). Returns 0-100."""
    total_weight = sum(ls.weight for ls in layer_scores)
    if total_weight == 0:
        return 50.0
    weighted = sum(ls.score * ls.weight for ls in layer_scores)
    return round(weighted / total_weight, 4)


def _score_to_signal(weighted_sum: float) -> FinalSignal:
    """Map weighted_sum (0-100) to FinalSignal using SIGNAL_THRESHOLDS."""
    if weighted_sum >= SIGNAL_THRESHOLDS["buy_strong"]:
        return "BUY-STRONG"
    if weighted_sum >= SIGNAL_THRESHOLDS["buy_weak"]:
        return "BUY-WEAK"
    if weighted_sum >= SIGNAL_THRESHOLDS["hold_lower"]:
        return "HOLD"
    if weighted_sum >= SIGNAL_THRESHOLDS["sell_weak"]:
        return "SELL-WEAK"
    return "SELL-STRONG"


def _apply_conflict_resolution(
    signal: FinalSignal,
    layer_scores: list[LayerScore],
) -> tuple[FinalSignal, ConflictInfo]:
    """Detect conflict: max-score computed layer vs min-score computed layer gap > 40.

    Only compares layers with source='computed' or 'partial' (ignores stubs/missing).
    """
    no_conflict = ConflictInfo(
        detected=False, layer_a="", layer_b="", score_gap=0.0, resolution="none"
    )

    active = [ls for ls in layer_scores if ls.source in ("computed", "partial")]
    if len(active) < 2:
        return signal, no_conflict

    highest = max(active, key=lambda ls: ls.score)
    lowest = min(active, key=lambda ls: ls.score)
    score_gap = round(highest.score - lowest.score, 4)

    if score_gap <= CONFLICT_THRESHOLD:
        return signal, no_conflict

    conflict = ConflictInfo(
        detected=True,
        layer_a=highest.layer,
        layer_b=lowest.layer,
        score_gap=score_gap,
        resolution="downgrade_one_level",
    )

    idx = SIGNAL_ORDER.index(signal)
    if idx < len(SIGNAL_ORDER) - 1:
        new_signal = SIGNAL_ORDER[idx + 1]
    else:
        new_signal = signal

    return new_signal, conflict


def _apply_regime_filter(
    signal: FinalSignal,
    regime: MacroRegime,
    macro_data: dict,
) -> tuple[FinalSignal, bool, str | None]:
    """RISK_OFF → all BUY signals become HOLD. Returns (filtered_signal, override_applied, trigger)."""
    if regime != "RISK_OFF":
        return signal, False, None

    if signal in ("BUY-STRONG", "BUY-WEAK"):
        from src.signals.thresholds import RISK_OFF_CONDITIONS
        trigger = None
        vix = macro_data.get("vix_level", macro_data.get("VIX_level"))
        if vix is None:
            _v = macro_data.get("VIX", macro_data.get("vix"))
            if _v is not None and abs(float(_v)) > 1.0:
                vix = float(_v)
        usdtry = macro_data.get("USDTRY_1d_change", macro_data.get("usdtry_1d_change", 0.0))
        bist100 = macro_data.get("BIST100_1d_change", macro_data.get("bist100_1d_change", 0.0))
        if vix is not None and vix > RISK_OFF_CONDITIONS["vix_threshold"]:
            trigger = f"VIX={vix:.1f}"
        elif usdtry is not None and usdtry > RISK_OFF_CONDITIONS["usdtry_1d_change"]:
            trigger = f"USDTRY_1d={usdtry:.2%}"
        elif bist100 is not None and bist100 < RISK_OFF_CONDITIONS["bist100_1d_change"]:
            trigger = f"BIST100_1d={bist100:.2%}"
        return "HOLD", True, trigger

    return signal, False, None


def _build_signal_summary(
    symbol: str,
    final_signal: FinalSignal,
    score: float,
    conflict: ConflictInfo,
    regime: MacroRegime,
    layer_scores: list[LayerScore],
    risk_off_override: bool,
) -> str:
    parts = [f"{symbol} {final_signal} | Score:{score:.1f}"]
    if conflict.detected:
        parts.append(
            f"⚠ Conflict: {conflict.layer_a}({next(ls.score for ls in layer_scores if ls.layer == conflict.layer_a):.0f})"
            f" vs {conflict.layer_b}({next(ls.score for ls in layer_scores if ls.layer == conflict.layer_b):.0f})"
        )
    if risk_off_override:
        parts.append("RISK_OFF override")
    kap_ls = next((ls for ls in layer_scores if ls.layer == "kap"), None)
    tech_ls = next((ls for ls in layer_scores if ls.layer == "technical"), None)
    if kap_ls and kap_ls.source != "no_events":
        parts.append(f"KAP:{kap_ls.score:.0f}")
    if tech_ls:
        rsi = tech_ls.detail.get("rsi")
        if rsi is not None:
            parts.append(f"RSI:{rsi:.0f}")
    parts.append(f"Macro:{regime}")
    return " | ".join(parts)


def compute_signal(
    symbol: str,
    technical_data: dict,
    macro_data: dict,
    kap_events: list[dict],
    as_of_date: date | None = None,
    weight_override: dict[str, float] | None = None,
) -> SignalResult:
    """Compute signal for a single symbol. Stateless — safe for backtesting."""
    if as_of_date is None:
        as_of_date = date.today()
    elif as_of_date > date.today():
        raise ValueError(f"as_of_date {as_of_date} is in the future")

    weights = dict(MASTER_WEIGHTS)
    if weight_override:
        unknown_keys = set(weight_override) - set(weights)
        if unknown_keys:
            raise ValueError(
                f"weight_override içinde bilinmeyen key'ler: {unknown_keys}. "
                f"Geçerli key'ler: {set(weights)}"
            )
        total = sum(weight_override.values())
        if total == 0:
            raise ValueError("weight_override values sum to 0")
        if abs(total - 1.0) > 1e-9:
            logger.warning("weight_override sum=%.4f ≠ 1.0 — normalizing", total)
            weight_override = {k: v / total for k, v in weight_override.items()}
        weights.update(weight_override)

    def _w(key: str) -> float:
        return weights.get(key, MASTER_WEIGHTS[key])

    tech_ls = score_technical(technical_data)
    object.__setattr__(tech_ls, "__class__", LayerScore)
    tech_ls = LayerScore(
        layer=tech_ls.layer, score=tech_ls.score, confidence=tech_ls.confidence,
        weight=_w("technical"), detail=tech_ls.detail, source=tech_ls.source,
    )

    macro_ls = score_macro(macro_data)
    macro_ls = LayerScore(
        layer=macro_ls.layer, score=macro_ls.score, confidence=macro_ls.confidence,
        weight=_w("macro"), detail=macro_ls.detail, source=macro_ls.source,
    )

    kap_ls = score_kap(symbol, kap_events, as_of_date)
    kap_ls = LayerScore(
        layer=kap_ls.layer, score=kap_ls.score, confidence=kap_ls.confidence,
        weight=_w("kap"), detail=kap_ls.detail, source=kap_ls.source,
    )

    risk_ls = score_risk(symbol, technical_data, macro_data)
    risk_ls = LayerScore(
        layer=risk_ls.layer, score=risk_ls.score, confidence=risk_ls.confidence,
        weight=_w("risk"), detail=risk_ls.detail, source=risk_ls.source,
    )

    # L4 Sentiment — confidence-scaled at LayerScore creation (D-052, DEC-009).
    # Effective weight = MASTER_WEIGHTS["sentiment"] (0.12) x layer confidence.
    # SUSPENDED in production (no Turkish news source) → confidence=0.0 →
    # effective weight 0.0 → zero contribution (emergent normalizer floor 0.78).
    sentiment_ls = score_sentiment(symbol)
    sentiment_ls = LayerScore(
        layer=sentiment_ls.layer, score=sentiment_ls.score, confidence=sentiment_ls.confidence,
        weight=_w("sentiment") * sentiment_ls.confidence,
        detail=sentiment_ls.detail, source=sentiment_ls.source,
    )

    # L5 Smart Money (D-055 — Phase 4.5 progressive build), confidence-scaled
    # at LayerScore creation (D-052, DEC-009): effective weight =
    # MASTER_WEIGHTS["smart_money"] (0.10) x layer confidence.
    # compute_l5_score() returns None when: no history, stale >48h, ADV
    # ineligible, or <10 days → confidence=0 → effective weight 0 (fully
    # excluded; not a 50.0 neutral contribution). Data-collection until ~Gün 10.
    _l5_score = get_l5_layer().compute_l5_score(symbol)
    if _l5_score is None:
        smart_money_ls = LayerScore(
            layer="smart_money",
            score=50.0,
            confidence=0.0,
            weight=0.0,
            detail={"status": "no_data_or_stale"},
            source="stub",
        )
    else:
        _l5_conf = 0.8
        smart_money_ls = LayerScore(
            layer="smart_money",
            score=round(_l5_score, 2),
            confidence=_l5_conf,
            weight=_w("smart_money") * _l5_conf,
            detail={"l5_score": _l5_score},
            source="computed",
        )

    layer_scores: list[LayerScore] = [
        tech_ls, macro_ls, kap_ls, risk_ls, smart_money_ls, sentiment_ls
    ]

    weighted_sum = _compute_weighted_sum(layer_scores)

    # Phase 4.5 (D-052) — derived conviction layer (SPEC_SIGNAL_CONVICTION_1).
    # Engine's 0-100 scoring + L1/L2/L3 logic untouched; conviction is derived
    # on top from the reweighted composite, modulated by L2 macro score.
    conviction_score, conviction_tier = compute_conviction(
        weighted_sum, macro_ls.score
    )

    pre_conflict_signal = _score_to_signal(weighted_sum)

    final_signal, conflict = _apply_conflict_resolution(pre_conflict_signal, layer_scores)

    regime = detect_regime(macro_data)
    final_signal, risk_off_override, risk_off_trigger = _apply_regime_filter(
        final_signal, regime, macro_data
    )

    score = round(weighted_sum, 4)
    summary = _build_signal_summary(
        symbol, final_signal, score, conflict, regime, layer_scores, risk_off_override
    )

    audit = AuditTrail(
        symbol=symbol,
        as_of_date=as_of_date,
        computed_at=datetime.now(timezone.utc),
        layer_scores=layer_scores,
        weighted_sum=weighted_sum,
        pre_conflict_signal=pre_conflict_signal,
        conflict=conflict,
        regime=regime,
        risk_off_override=risk_off_override,
        risk_off_trigger=risk_off_trigger,
        final_signal=final_signal,
        signal_summary=summary,
        conviction_score=conviction_score,
        conviction_tier=conviction_tier,
    )

    return SignalResult(
        symbol=symbol,
        final_signal=final_signal,
        score=score,
        audit=audit,
        conviction_score=conviction_score,
        conviction_tier=conviction_tier,
    )


def compute_batch(
    symbols: list[str],
    technical_batch: dict[str, dict],
    macro_data: dict,
    kap_batch: dict[str, list[dict]],
    as_of_date: date | None = None,
) -> list[SignalResult]:
    """Compute signals for multiple symbols. macro_data shared. Sorted by score desc."""
    results: list[SignalResult] = []
    for symbol in symbols:
        try:
            tech = technical_batch.get(symbol, {})
            kap = kap_batch.get(symbol, [])
            result = compute_signal(symbol, tech, macro_data, kap, as_of_date)
            results.append(result)
        except Exception as exc:
            logger.error("compute_batch: skipping %s — %s", symbol, exc)
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def build_signal_context_for_orchestrator(results: list[SignalResult]) -> dict:
    """Format compute_batch() output for orchestrator pre_filter."""
    if not results:
        return {
            "date": date.today().isoformat(),
            "regime": "NEUTRAL",
            "risk_off": False,
            "strong_signals": [],
            "weak_signals": [],
            "holds": [],
            "sell_signals": [],
            "conflict_symbols": [],
            "missing_layers": [],
        }

    first_audit = results[0].audit
    regime = first_audit.regime
    risk_off = first_audit.risk_off_override

    strong, weak, holds, sells = [], [], [], []
    conflicts = []

    for r in results:
        entry = {"symbol": r.symbol, "signal": r.final_signal, "score": round(r.score, 2)}
        if r.audit.conflict.detected:
            conflicts.append(r.symbol)
        if r.final_signal == "BUY-STRONG":
            strong.append(entry)
        elif r.final_signal == "BUY-WEAK":
            weak.append(entry)
        elif r.final_signal == "HOLD":
            holds.append(entry)
        else:
            sells.append(entry)

    return {
        "date": first_audit.as_of_date.isoformat(),
        "regime": regime,
        "risk_off": risk_off,
        "strong_signals": strong,
        "weak_signals": weak,
        "holds": holds,
        "sell_signals": sells,
        "conflict_symbols": conflicts,
        "missing_layers": [],
    }

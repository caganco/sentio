"""KAP layer: KAP disclosure events → LayerScore 0-100."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from src.signals.layers.kap_earnings_parser import parse_earnings_surprise  # D-158
from src.signals.models import LayerScore
from src.signals.thresholds import (
    KAP_BASE_SCORE,
    KAP_CATEGORY_IMPACT,
    KAP_DUPLICATE_MULTIPLIER,
    KAP_EARNINGS_IMPACT_SCALE,  # D-158
    KAP_EVENT_WINDOW_DAYS,
    KAP_HIGH_PRIORITY_MULTIPLIER,
    MASTER_WEIGHTS,
)


def _parse_date(val: str | date | datetime | None) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except Exception:
        return None


def score_kap(
    symbol: str,
    kap_events: list[dict],
    as_of_date: date,
) -> LayerScore:
    """Score KAP disclosures for a symbol within a 3-day window."""
    cutoff = as_of_date - timedelta(days=KAP_EVENT_WINDOW_DAYS)

    relevant = []
    for ev in kap_events:
        ev_symbol = ev.get("symbol", "")
        if ev_symbol and ev_symbol != symbol:
            continue
        pub = _parse_date(ev.get("published_at") or ev.get("publish_datetime"))
        if pub is None or pub < cutoff or pub > as_of_date:
            continue
        relevant.append(ev)

    if not relevant:
        return LayerScore(
            layer="kap",
            score=KAP_BASE_SCORE,
            confidence=0.0,
            weight=MASTER_WEIGHTS["kap"],
            detail={"events_count": 0},
            source="no_events",
        )

    score = KAP_BASE_SCORE
    category_seen: dict[str, int] = {}
    event_details: list[str] = []
    high_priority = any(ev.get("high_priority_flag") or ev.get("is_high_priority") for ev in relevant)

    for ev in relevant:
        category = ev.get("category", "diger")

        # D-158: finansal_rapor → numeric surprise score (Faz 1, regex-only, LLM yok)
        if category == "finansal_rapor":
            kap_text = ev.get("kap_text") or ev.get("text") or ""
            if kap_text:
                surprise = parse_earnings_surprise(kap_text)
                if surprise.confidence > 0.0:
                    impact = surprise.score * KAP_EARNINGS_IMPACT_SCALE
                else:
                    impact = KAP_CATEGORY_IMPACT.get(category, 0.0)  # 0.0 fallback
            else:
                impact = KAP_CATEGORY_IMPACT.get(category, 0.0)  # kap_text yok → 0.0 fallback
        else:
            impact = KAP_CATEGORY_IMPACT.get(category, 0.0)

        seen_count = category_seen.get(category, 0)
        multiplier = KAP_DUPLICATE_MULTIPLIER if seen_count > 0 else 1.0
        if high_priority:
            multiplier *= KAP_HIGH_PRIORITY_MULTIPLIER

        actual_impact = round(impact * multiplier, 4)
        score += actual_impact
        category_seen[category] = seen_count + 1
        event_details.append(f"{category} {'+' if actual_impact >= 0 else ''}{actual_impact}")

    score = round(max(0.0, min(100.0, score)), 4)

    return LayerScore(
        layer="kap",
        score=score,
        confidence=1.0,
        weight=MASTER_WEIGHTS["kap"],
        detail={
            "events_count": len(relevant),
            "high_priority": high_priority,
            "events": event_details,
            "categories": category_seen,
        },
        source="computed",
    )

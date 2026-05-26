"""KAP finansal rapor metni → numerik sürpriz skoru (D-158, Faz 1, LLM yok).

Stage 1 (bu modül): pure regex/heuristic ile net kâr/hasılat/FAVÖK çift değeri
yakalanır; önceki dönemle karşılaştırılır; normalize edilmiş sürpriz skoru üretilir.

Stage 2 (Faz 2, ~Eylül-Kasım 2026): düşük-güven durumları için LLM çağrısı eklenecek.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.signals.thresholds import (
    KAP_EARNINGS_NEUTRAL_BAND,
    KAP_EARNINGS_STRONG_THRESHOLD,
)


@dataclass
class EarningsSurprise:
    """Numerik sürpriz skoru parse sonucu."""

    score: float           # ∈ [-1.0, +1.0]; 0.0 = nötr / parse başarısız
    confidence: float      # 0.0 = fallback, 0.5 = 1 metrik, 0.75 = 2, 1.0 = 3
    metrics_found: list[str] = field(default_factory=list)  # ["net_kar", "hasilat", "favok"]
    parse_method: str = "fallback"  # "regex" | "fallback"


_FALLBACK = EarningsSurprise(
    score=0.0, confidence=0.0, metrics_found=[], parse_method="fallback"
)

# Birim çarpanları
_MULT_MAP: dict[str, float] = {"milyon": 1e6, "milyar": 1e9, "bin": 1e3}

# Önceki dönem etiketleri (non-capturing)
_PREV = r"(?:geçen\s+yıl|önceki\s+dönem|\d{4})"

# Sayı + birim grubu — 2 capture group: (value, multiplier?)
_NUM = r"([\d.,]+)\s*(milyon|milyar|bin)?\s*(?:tl)?"

# Metrik adı → regex pattern mapping
# Her pattern: curr_val, curr_mult, prev_val, prev_mult → 4 capture groups
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "net_kar",
        re.compile(
            r"net\s+k[aâ]r[ı]?\s+" + _NUM + r"\s+\(" + _PREV + r"[:\s]+" + _NUM + r"\)",
            re.IGNORECASE,
        ),
    ),
    (
        "hasilat",
        re.compile(
            r"(?:hasılat|net\s+satış[lar]*)\s+" + _NUM + r"\s+\(" + _PREV + r"[:\s]+" + _NUM + r"\)",
            re.IGNORECASE,
        ),
    ),
    (
        "favok",
        re.compile(
            r"favök\s+" + _NUM + r"\s+\(" + _PREV + r"[:\s]+" + _NUM + r"\)",
            re.IGNORECASE,
        ),
    ),
]

# Metriklerin bulunma sayısı → confidence mapping
_CONFIDENCE_MAP: dict[int, float] = {1: 0.5, 2: 0.75, 3: 1.0}


def _parse_number(value_str: str, mult_str: str | None) -> float:
    """Türkçe format sayıyı float'a dönüştür.

    Türkçe: nokta = binlik ayracı, virgül = ondalık.
    Örnekler: "1.100" → 1100.0, "1,5" → 1.5, "450" → 450.0.
    """
    cleaned = value_str.strip().replace(".", "").replace(",", ".")
    val = float(cleaned)
    mult = _MULT_MAP.get((mult_str or "").lower().strip(), 1.0)
    return val * mult


def _normalize_delta(delta: float) -> float:
    """delta% → [-1.0, +1.0] sürpriz skoru.

    Normalizasyon (thresholds.py sabitlerine göre):
    - |delta| ≤ NEUTRAL_BAND (0.05): 0.0
    - delta > STRONG_THRESHOLD (0.20): +1.0
    - delta ∈ (NEUTRAL_BAND, STRONG_THRESHOLD): lineer [+0.25, +1.0]
    - Negatif taraf simetrik.
    """
    band = KAP_EARNINGS_NEUTRAL_BAND
    strong = KAP_EARNINGS_STRONG_THRESHOLD

    if abs(delta) <= band:
        return 0.0
    if delta > 0:
        if delta >= strong:
            return 1.0
        return 0.25 + 0.75 * (delta - band) / (strong - band)
    else:
        if delta <= -strong:
            return -1.0
        return -0.25 - 0.75 * (-delta - band) / (strong - band)


def parse_earnings_surprise(kap_text: str) -> EarningsSurprise:
    """KAP finansal rapor metninden sayısal sürpriz skoru çıkarır (D-158 Faz 1).

    Hedef metrikler: net kâr, hasılat/net satışlar, FAVÖK.
    Bulunan metriklerin eşit ağırlıklı ortalaması alınır.

    Fail-safe: herhangi bir exception → score=0.0, confidence=0.0 (fallback).
    LLM çağrısı yok (Faz 2'de eklenecek).
    """
    try:
        if not kap_text or not kap_text.strip():
            return _FALLBACK

        scores: list[float] = []
        metrics: list[str] = []

        for metric_name, pattern in _PATTERNS:
            m = pattern.search(kap_text)
            if not m:
                continue
            g = m.groups()
            # g[0]: curr_val, g[1]: curr_mult, g[2]: prev_val, g[3]: prev_mult
            curr = _parse_number(g[0], g[1])
            prev = _parse_number(g[2], g[3])
            if prev == 0:
                continue
            delta = (curr - prev) / abs(prev)
            scores.append(_normalize_delta(delta))
            metrics.append(metric_name)

        if not scores:
            return _FALLBACK

        final_score = round(sum(scores) / len(scores), 6)
        confidence = _CONFIDENCE_MAP.get(len(scores), 1.0)

        return EarningsSurprise(
            score=final_score,
            confidence=confidence,
            metrics_found=metrics,
            parse_method="regex",
        )

    except Exception:  # noqa: BLE001 — fail-safe: tüm hatalar fallback
        return _FALLBACK

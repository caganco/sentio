"""KAP disclosure parser: raw dict → KapEvent dataclass.

Handles category classification, structured data extraction (dividend/
capital increase), and attachment URL fetching.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import src.data.kap_client  # noqa: F401 — applies Company.from_row field-name patch
from kap_client import Kap

from src.data.kap_fetcher import fetch_attachments_for_disclosure

logger = logging.getLogger(__name__)

EventCategory = Literal[
    "ozel_durum",
    "finansal_rapor",
    "insider",
    "temettu",
    "sermaye_artirimi",
    "genel_kurul",
    "diger",
]

# ---------------------------------------------------------------------------
# Keyword → category map (Turkish, lowercase matching)
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: list[tuple[str, EventCategory]] = [
    # longer / more-specific phrases first to avoid false matches
    ("finansal rapor", "finansal_rapor"),
    ("finansal tablo", "finansal_rapor"),
    ("mali tablo", "finansal_rapor"),
    # ozel durum — both Turkish unicode and ASCII-fallback
    ("özel durum", "ozel_durum"),
    ("ozel durum", "ozel_durum"),
    # insider — match both unicode and ASCII-fallback forms
    ("içeriden", "insider"),
    ("iceriden", "insider"),
    ("yönetici işlem", "insider"),
    ("yonetici islem", "insider"),
    # temettu
    ("temettü", "temettu"),
    ("temettu", "temettu"),
    ("kâr payı", "temettu"),
    ("kar payi", "temettu"),
    # sermaye
    ("sermaye artırım", "sermaye_artirimi"),
    ("sermaye artirimi", "sermaye_artirimi"),
    ("bedelsiz", "sermaye_artirimi"),
    ("bedelli", "sermaye_artirimi"),
    # genel kurul
    ("genel kurul", "genel_kurul"),
]


def classify_category(subject: str) -> EventCategory:
    """Classify a KAP disclosure subject string into an EventCategory.

    Uses keyword matching on lowercase subject. Returns "diger" on no match.
    """
    if not subject:
        return "diger"
    lower = subject.lower()
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in lower:
            return category
    return "diger"


def extract_structured_data(
    subject: str,
    category: EventCategory,
    attachment_urls: list[str],
) -> dict:
    """Extract structured fields for dividend/capital-increase disclosures.

    For other categories returns {}. Parse failures return {} with a WARNING.
    """
    if category == "temettu":
        return _parse_dividend(subject)
    if category == "sermaye_artirimi":
        return _parse_capital_increase(subject)
    return {}


def parse_disclosure(
    raw: dict,
    symbol: str,
    fetched_at: datetime,
    kap_client: Kap,
) -> "KapEvent":
    """Convert a raw kap_fetcher disclosure dict into a KapEvent.

    Steps:
    1. classify_category(subject)
    2. If dividend/capital: extract_structured_data()
    3. If has_attachment: fetch attachment URLs
    4. Build frozen KapEvent

    published_at is stored as-is (kap-client returns naive datetime, UTC+3 local).
    """
    subject = raw.get("subject") or ""
    category = classify_category(subject)

    has_att = bool(raw.get("has_attachment"))
    attachment_urls: list[str] = []
    if has_att:
        attachment_urls = fetch_attachments_for_disclosure(raw["index"], kap_client)

    structured_data = extract_structured_data(subject, category, attachment_urls)

    pub_str = raw.get("publish_datetime", "")
    try:
        published_at = datetime.fromisoformat(pub_str)
    except (ValueError, TypeError):
        logger.warning("KAP parser: cannot parse publish_datetime %r for %s, using epoch", pub_str, symbol)
        published_at = datetime.min

    return KapEvent(
        disclosure_index=str(raw["index"]),
        symbol=symbol,
        published_at=published_at,
        fetched_at=fetched_at,
        subject=subject,
        category=category,
        summary=(raw.get("summary") or "")[:500] or None,
        url=raw.get("url") or "",
        structured_data=structured_data,
        has_attachment=has_att,
        attachment_urls=attachment_urls,
    )


def parse_all(
    raw_by_symbol: dict[str, list[dict]],
    fetched_at: datetime,
    kap_client: Kap,
) -> list["KapEvent"]:
    """Parse all raw disclosure dicts from fetch_all_symbols() output.

    Returns KapEvent list sorted by published_at descending.
    """
    events: list[KapEvent] = []
    for symbol, raws in raw_by_symbol.items():
        for raw in raws:
            try:
                events.append(parse_disclosure(raw, symbol, fetched_at, kap_client))
            except Exception as exc:
                logger.warning("KAP parser: failed to parse disclosure %s for %s: %s", raw.get("index"), symbol, exc)
    return sorted(events, key=lambda e: e.published_at, reverse=True)


# ---------------------------------------------------------------------------
# Structured data extractors
# ---------------------------------------------------------------------------

def _parse_dividend(subject: str) -> dict:
    result = {}
    try:
        # Match patterns like "2,50 TL" or "2.50 TL"
        brut_match = re.search(r"br[üu]t\s*[:\-]?\s*([\d.,]+)\s*tl", subject, re.IGNORECASE)
        net_match = re.search(r"net\s*[:\-]?\s*([\d.,]+)\s*tl", subject, re.IGNORECASE)
        pay_match = re.search(r"pay\s+ba[şs][ıi]na\s*[:\-]?\s*([\d.,]+)", subject, re.IGNORECASE)

        if brut_match:
            result["temettu_brut_tl"] = _parse_number(brut_match.group(1))
        if net_match:
            result["temettu_net_tl"] = _parse_number(net_match.group(1))
        if pay_match:
            result["pay_basi"] = _parse_number(pay_match.group(1))
    except Exception as exc:
        logger.warning("KAP parser: dividend parse failed for %r: %s", subject, exc)
    return result


def _parse_capital_increase(subject: str) -> dict:
    result = {}
    try:
        oran_match = re.search(r"([\d.,]+)\s*%", subject)
        bedelsiz_match = re.search(r"bedelsiz\s*[:\-]?\s*([\d.,]+)\s*%", subject, re.IGNORECASE)
        bedelli_match = re.search(r"bedelli\s*[:\-]?\s*([\d.,]+)\s*%", subject, re.IGNORECASE)

        if oran_match:
            result["artis_oran"] = _parse_number(oran_match.group(1)) / 100
        if bedelsiz_match:
            result["bedelsiz_miktar"] = _parse_number(bedelsiz_match.group(1)) / 100
        if bedelli_match:
            result["bedelli_miktar"] = _parse_number(bedelli_match.group(1)) / 100
    except Exception as exc:
        logger.warning("KAP parser: capital-increase parse failed for %r: %s", subject, exc)
    return result


def _parse_number(s: str) -> float:
    """Parse a Turkish-formatted number string (e.g. "2,50" or "2.50")."""
    # Turkish decimal: comma as separator → replace last comma with dot
    s = s.strip()
    if "," in s and "." in s:
        # e.g. "1.234,56" → "1234.56"
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    return float(s)


# ---------------------------------------------------------------------------
# KapEvent dataclass (defined after helpers it depends on)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KapEvent:
    disclosure_index: str
    symbol: str
    published_at: datetime
    fetched_at: datetime
    subject: str
    category: EventCategory
    summary: str | None
    url: str
    source_type: Literal["kap_official"] = "kap_official"
    source_domain: str = "kap.org.tr"
    structured_data: dict = field(default_factory=dict)
    has_attachment: bool = False
    attachment_urls: list[str] = field(default_factory=list)

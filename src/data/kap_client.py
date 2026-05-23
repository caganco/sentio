"""kap_client library field-name monkey-patch.

KAP API field names mismatches in kap_client >= 0.x:

  API response field  │ CompanyRow model field  │ Used for
  ─────────────────── │ ─────────────────────── │ ──────────────────────────
  mkkMemberOid        │ memberOid (None)         │ mkkMemberOidList in query
  kapMemberTitle      │ memberTitle (None)       │ company name display
  stockCode (sing.)   │ stockCodes (plural,None) │ ticker → company lookup

All three are stored in CompanyRow.model_extra (pydantic extra="allow").
This module patches Company.from_row() to read from model_extra so that
kap_client.Kap().find_company("AKBNK") works for YK/PYS/BDK/DCS/DDK/DK
member-type companies.

NOTE: HT (BIST listed companies, e.g. THYAO) endpoint returns [] since
~May 2026 — a KAP API infrastructure change. THYAO and other listed stocks
must be fetched via kap_scraper.fetch_kap_news() (Google News RSS fallback).

Usage — import BEFORE using kap_client.Kap():
    import src.data.kap_client  # side-effect: applies patch
    from kap_client import Kap
    with Kap() as kap:
        co = kap.find_company("AKBNK")
"""

from __future__ import annotations

import logging

import kap_client._models as _models
import kap_client._endpoints as _endpoints

logger = logging.getLogger(__name__)

_PATCH_APPLIED = False


def _patched_company_from_row(cls, row: _endpoints.CompanyRow) -> _models.Company:
    """Read KAP API's actual field names from pydantic model_extra."""
    extra: dict = row.model_extra or {}

    # mkkMemberOid goes into mkkMemberOidList for disclosure queries
    oid = (
        extra.get("mkkMemberOid")
        or extra.get("kapMemberOid")
        or row.memberOid
        or ""
    )
    name = (
        extra.get("kapMemberTitle")
        or row.memberTitle
        or ""
    )
    # API returns singular "stockCode"; model has plural "stockCodes"
    ticker = (
        extra.get("stockCode")
        or extra.get("stockCodes")
        or row.stockCodes
        or ""
    )
    return cls(oid=oid, name=name, ticker=ticker)


def apply_patch() -> None:
    """Monkey-patch Company.from_row to handle KAP API field name mismatches.

    Idempotent — safe to call multiple times.
    """
    global _PATCH_APPLIED
    if _PATCH_APPLIED:
        return

    _models.Company.from_row = classmethod(_patched_company_from_row)
    _PATCH_APPLIED = True
    logger.debug("kap_client patch applied: Company.from_row reads model_extra")


# Auto-apply on import so callers don't need to call apply_patch() explicitly.
apply_patch()

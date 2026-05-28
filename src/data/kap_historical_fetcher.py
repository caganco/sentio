"""MKK VYK FR tarihsel veri fetcher + parquet cache. D-170 / D-172.

Sadece backtest icin — production kap_scraper.py akisina dokunmaz.

D-172: gercek MKK VYK API semasina uyarlandi (canli test API teyitli):
  - companyId↔ticker haritasi /api/vyk/members'tan (build_company_map).
  - get_disclosures companyId filtresi ile o sirketin FR'lerini dogrudan ceker.
  - Bir filing'de 3 FR-class bildirim olur; yalniz subject.en=="Financial Report"
    finansal tasir → subject filtresi.
  - disclosureIndex < 538004 → KAP 4.0 oncesi (html-only) → atlanir.
  - disclosureDetail(fileType="data"): year, period{tr,en}, time, subject, presentation.
  - XBRL: presentation[i].content.ReportItem.ReportItem (recursive); leaf name ∈ _XBRL_MAP,
    Values.Value[contextId] — CURR = contextId.startswith(year).

Kullanim:
    from src.data.kap_historical_fetcher import build_company_map, fetch_fr_history
    df = fetch_fr_history("THYAO", 2022, 2025)

Cache: data/cache/kap_fr_{ticker}_{year}.parquet (yil bazli),
       data/cache/kap_company_map.json (companyId→ticker, 24h TTL).
XBRL alan eslemesi:
    Revenue       → revenue
    GrossProfit   → gross_profit
    ProfitLoss    → net_income
    Assets        → total_assets
    IssuedCapital → equity
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.kap_api_client import KapApiClient, KapApiError

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_COMPANY_MAP_PATH = _CACHE_DIR / "kap_company_map.json"
_COMPANY_MAP_TTL = 24 * 3600  # 24 saat

# KAP 4.0 oncesi bildirimler yalniz html (XBRL yok) — bu indeksin altini atla.
_MIN_DISCLOSURE_INDEX = 538004
_FINANCIAL_SUBJECT_EN = "Financial Report"

_COLS = [
    "date", "ticker", "year", "period",
    "revenue", "gross_profit", "net_income", "total_assets", "equity",
    "publication_date",
]

_XBRL_MAP: dict[str, str] = {
    "Revenue":      "revenue",
    "GrossProfit":  "gross_profit",
    "ProfitLoss":   "net_income",
    "Assets":       "total_assets",
    "IssuedCapital": "equity",
}


def _make_client() -> "KapApiClient | None":
    """Env'den kimlik okur, KapApiClient kurar. Kimlik yoksa None."""
    base_url = os.getenv("MKK_VYK_BASE_URL", "")
    token = os.getenv("MKK_VYK_TOKEN", "")
    if not base_url or not token:
        return None
    auth_type = "basic" if "apigwdev" in base_url.lower() else "bearer"
    return KapApiClient(base_url, token, auth_type=auth_type)


def build_company_map() -> dict[str, str]:
    """companyId (str) → stockCode (ticker) haritasi. 24h JSON cache.

    Returns:
        {"1107": "THYAO", "1383": "FENER", ...}. Kimlik yoksa veya hata → bos dict.
    """
    client = _make_client()
    if client is None:
        return {}

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _COMPANY_MAP_PATH.exists():
        age = time.time() - _COMPANY_MAP_PATH.stat().st_mtime
        if age < _COMPANY_MAP_TTL:
            try:
                with open(_COMPANY_MAP_PATH, encoding="utf-8") as fh:
                    return json.load(fh)
            except (json.JSONDecodeError, OSError):
                pass  # bozuk cache → yeniden cek

    try:
        members = client.get_members()
    except KapApiError as exc:
        logger.warning("build_company_map: %s", exc)
        return {}

    cmap = {
        str(m.get("id")): m.get("stockCode")
        for m in members
        if m.get("id") and m.get("stockCode")
    }
    try:
        with open(_COMPANY_MAP_PATH, "w", encoding="utf-8") as fh:
            json.dump(cmap, fh, ensure_ascii=False)
    except OSError as exc:
        logger.warning("build_company_map cache yazilamadi: %s", exc)
    return cmap


def fetch_fr_history(ticker: str, start_year: int, end_year: int) -> pd.DataFrame:
    """FR (Financial Report) bildirimlerini yil yil ceker; parquet cache kullanir.

    Args:
        ticker:     BIST ticker (orn. "THYAO").
        start_year: Baslangic yili (inclusive).
        end_year:   Bitis yili (inclusive).

    Returns:
        DataFrame kolonlari: date, ticker, year, period, revenue, gross_profit,
        net_income, total_assets, equity, publication_date.
        Kimlik eksikse veya veri yoksa: bos DataFrame.
    """
    client = _make_client()
    if client is None:
        logger.warning("fetch_fr_history: MKK_VYK_BASE_URL/MKK_VYK_TOKEN tanimli degil")
        return pd.DataFrame(columns=_COLS)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    company_map = build_company_map()
    ticker_to_id = {v.upper(): k for k, v in company_map.items() if v}

    frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        cache_path = _CACHE_DIR / f"kap_fr_{ticker}_{year}.parquet"
        if cache_path.exists():
            frames.append(pd.read_parquet(cache_path))
            logger.debug("kap_fr cache hit: %s", cache_path.name)
            continue

        rows = _fetch_year(client, ticker, year, ticker_to_id)
        if rows:
            df_year = pd.DataFrame(rows, columns=_COLS)
            df_year.to_parquet(cache_path, index=False)
            frames.append(df_year)
            logger.info(
                "kap_fr fetched: ticker=%s year=%d rows=%d", ticker, year, len(rows)
            )

    if not frames:
        return pd.DataFrame(columns=_COLS)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_year(
    client: KapApiClient,
    ticker: str,
    year: int,
    ticker_to_id: dict[str, str],
) -> list[dict[str, Any]]:
    """Bir yil icin ticker'in Financial Report bildirimlerini ceker."""
    rows: list[dict[str, Any]] = []
    cid = ticker_to_id.get(ticker.upper())
    if cid is None:
        logger.debug("_fetch_year: companyId bulunamadi ticker=%s", ticker)
        return rows

    try:
        discs = client.get_disclosures(
            start_index=0, disclosure_class="FR", company_id=int(cid)
        )
        for disc in discs:
            idx = disc.get("disclosureIndex")
            if idx is None:
                continue
            try:
                idx_int = int(idx)
            except (ValueError, TypeError):
                continue
            if idx_int < _MIN_DISCLOSURE_INDEX:  # KAP 4.0 oncesi → XBRL yok
                continue
            detail = client.get_disclosure_detail(idx_int, file_type="data")
            if not _is_financial_report(detail):
                continue
            if str(detail.get("year")) != str(year):
                continue
            rows.append(_parse_xbrl(detail, ticker, year))
    except KapApiError as exc:
        logger.warning("_fetch_year: ticker=%s year=%d — %s", ticker, year, exc)
    return rows


def _is_financial_report(detail: dict[str, Any]) -> bool:
    """subject.en == 'Financial Report' mi? (Operating Review / Representation Letter degil)."""
    subject = detail.get("subject") or {}
    return isinstance(subject, dict) and subject.get("en") == _FINANCIAL_SUBJECT_EN


def _parse_xbrl(detail: dict[str, Any], ticker: str, year: int) -> dict[str, Any]:
    """disclosureDetail (fileType=data) yanitindan CURR finansal alanlari ayiklar."""
    row: dict[str, Any] = {col: None for col in _COLS}
    row["ticker"] = ticker
    row["year"] = year
    period = detail.get("period") or {}
    row["period"] = period.get("tr") if isinstance(period, dict) else period
    pub = _parse_tr_date(detail.get("time"))
    row["publication_date"] = pub
    row["date"] = pub

    yr = str(year)
    for entry in detail.get("presentation") or []:
        content = entry.get("content") if isinstance(entry, dict) else None
        if not isinstance(content, dict):
            continue
        for node in _iter_report_items(content.get("ReportItem")):
            name = node.get("name")
            if name in _XBRL_MAP and node.get("Values") is not None:
                col = _XBRL_MAP[name]
                if row[col] is None:  # ilk eslesme kazanir
                    val = _curr_value(node["Values"], yr)
                    if val is not None:
                        row[col] = val
    return row


def _iter_report_items(node: Any) -> Iterator[dict[str, Any]]:
    """ReportItem agacini recursive gezer; her dict node'u yield eder."""
    if isinstance(node, list):
        for child in node:
            yield from _iter_report_items(child)
    elif isinstance(node, dict):
        yield node
        child = node.get("ReportItem")
        if child is not None:
            yield from _iter_report_items(child)


def _curr_value(values: dict[str, Any], year: str) -> "float | None":
    """Values.Value listesinden contextId yili eslesen (CURR) degeri float dondurur."""
    value = values.get("Value") if isinstance(values, dict) else None
    if value is None:
        return None
    entries = value if isinstance(value, list) else [value]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("contextId", "")).startswith(year):
            try:
                return float(entry.get("value"))
            except (ValueError, TypeError):
                return None
    return None


def _parse_tr_date(raw: Any) -> "str | None":
    """'29.10.2023 14:05:18' (TR gun.ay.yil) → '2023-10-29'. Gecersizse None."""
    s = str(raw or "").strip()
    if not s:
        return None
    date_part = s.split(" ")[0]
    parts = date_part.split(".")
    if len(parts) != 3 or len(parts[2]) != 4:
        return None
    day, month, year = parts
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def fetch_fundamentals_with_fallback(
    ticker: str,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """MKK XBRL once, bossan yfinance fallback. D-175.

    1. fetch_fr_history(ticker, start_year, end_year)
    2. Bossan -> fetch_yf_fundamentals(ticker, start_year, end_year)
    3. Ikisi de bossan -> bos DataFrame
    """
    df = fetch_fr_history(ticker, start_year, end_year)
    if not df.empty:
        return df
    # Lazy import: circular dep yok (yfinance_fundamentals_fetcher bu module bagimli degil)
    from src.data.yfinance_fundamentals_fetcher import fetch_yf_fundamentals
    logger.debug("D-175 fallback: MKK bos, yfinance deneniyor. ticker=%s", ticker)
    return fetch_yf_fundamentals(ticker, start_year, end_year)

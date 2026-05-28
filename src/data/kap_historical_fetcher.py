"""MKK VYK FR tarihsel veri fetcher + parquet cache. D-170.

Sadece backtest icin — production kap_scraper.py akisina dokunmaz.

Kullanim:
    from src.data.kap_historical_fetcher import fetch_fr_history
    df = fetch_fr_history("THYAO", 2022, 2025)

Cache: data/cache/kap_fr_{ticker}_{year}.parquet (yil bazli)
XBRL alan eslemesi:
    Revenue       → revenue
    GrossProfit   → gross_profit
    ProfitLoss    → net_income
    Assets        → total_assets
    IssuedCapital → equity
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.kap_api_client import KapApiClient, KapApiError

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"

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


def fetch_fr_history(ticker: str, start_year: int, end_year: int) -> pd.DataFrame:
    """FR bildirimlerini yil yil ceker; parquet cache'den okur, eksikleri API'den doldurur.

    Args:
        ticker:     BIST ticker (orn. "THYAO").
        start_year: Baslangic yili (inclusive).
        end_year:   Bitis yili (inclusive).

    Returns:
        DataFrame kolonlari: date, ticker, year, period, revenue, gross_profit,
        net_income, total_assets, equity, publication_date.
        Alan bulunamazsa: None. Credentials eksikse: bos DataFrame.
    """
    base_url = os.getenv("MKK_VYK_BASE_URL", "")
    token = os.getenv("MKK_VYK_TOKEN", "")
    if not base_url or not token:
        logger.warning("fetch_fr_history: MKK_VYK_BASE_URL/MKK_VYK_TOKEN tanimli degil")
        return pd.DataFrame(columns=_COLS)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    auth_type = "basic" if "apigwdev" in base_url.lower() else "bearer"
    client = KapApiClient(base_url, token, auth_type=auth_type)

    frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        cache_path = _CACHE_DIR / f"kap_fr_{ticker}_{year}.parquet"
        if cache_path.exists():
            frames.append(pd.read_parquet(cache_path))
            logger.debug("kap_fr cache hit: %s", cache_path.name)
            continue

        rows = _fetch_year(client, ticker, year)
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

def _fetch_year(client: KapApiClient, ticker: str, year: int) -> list[dict[str, Any]]:
    """Bir yil icin tum FR bildirimlerini API'den ceker."""
    rows: list[dict[str, Any]] = []
    try:
        disclosures = client.get_disclosures(start_index=0, disclosure_class="FR")
        for disc in disclosures:
            if not _matches(disc, ticker, year):
                continue
            idx = disc.get("index") or disc.get("id")
            if idx is None:
                continue
            detail = client.get_disclosure_detail(int(idx))
            rows.append(_parse_xbrl(detail, ticker, year, disc))
    except KapApiError as exc:
        logger.warning("_fetch_year: ticker=%s year=%d — %s", ticker, year, exc)
    return rows


def _matches(disc: dict[str, Any], ticker: str, year: int) -> bool:
    """Bildirimin ticker ve yil ile eslesmesini kontrol eder."""
    disc_year = str(disc.get("year", str(disc.get("publishDate", ""))[:4]))
    member = str(disc.get("member", disc.get("ticker", ""))).upper()
    return disc_year == str(year) and ticker.upper() in member


def _parse_xbrl(
    detail: dict[str, Any],
    ticker: str,
    year: int,
    disc: dict[str, Any],
) -> dict[str, Any]:
    """XBRL detay yanitindan finansal alanlari ayiklar."""
    items = detail.get("items", detail.get("data", []))
    row: dict[str, Any] = {col: None for col in _COLS}
    row["ticker"] = ticker
    row["year"] = year
    row["date"] = str(disc.get("publishDate", ""))[:10] or None
    row["period"] = disc.get("period", disc.get("term", None))
    # D-171: ayri look-ahead alani — "time" oncelikli, publishDate fallback.
    row["publication_date"] = str(disc.get("time", disc.get("publishDate", "")))[:10] or None

    for item in items:
        name = item.get("name", "")
        if name in _XBRL_MAP:
            raw = item.get("value", item.get("val", None))
            try:
                row[_XBRL_MAP[name]] = float(raw) if raw is not None else None
            except (ValueError, TypeError):
                row[_XBRL_MAP[name]] = None
    return row

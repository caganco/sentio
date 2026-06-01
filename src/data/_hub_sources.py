"""
DataHub kaynak kayitlari — mevcut fetcher'larin hub registration'i.

Her _make_* fonksiyonu bir DataSource dondurur veya hata durumunda None.
Tum modul importlari fonksiyon govdelerinde lazy yapilir; modul-seviyesinde
import yok, dolayisiyla circular import ve optional-dependency sorunu olmaz.

Mevcut modüller DEGISMEZ — hub bunlari sadece wrapper olarak bilir.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.data.data_hub import DataHub, DataSource

log = logging.getLogger(__name__)


def register_all(hub: type[DataHub]) -> None:
    """Tum kaynaklari hub'a kaydet. Basarisiz kayit warn + skip."""
    from src.data.data_hub import DataSource

    makers = [
        _make_yfinance,
        _make_evds,
        _make_evds_snapshot,
        _make_kap,
        _make_isyatirim,
        _make_news,
        _make_viop,
        _make_bist_datastore,
        _make_fintables,
        _make_cds,
        _make_cds_fallback,
    ]
    for fn in makers:
        try:
            src = fn(DataSource)
            if src is not None:
                hub.register(src)
        except Exception as exc:
            log.warning("DataHub kayit hatasi [%s]: %s", fn.__name__, exc)


# ------------------------------------------------------------------
# KAYNAK TANIMLARI
# ------------------------------------------------------------------


def _make_yfinance(DataSource: type) -> DataSource:
    def fetch(ticker: str, lookback: str = "1y", interval: str = "1d", **_: Any):
        import yfinance as yf

        return yf.download(
            ticker,
            period=lookback,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

    return DataSource(
        name="yfinance",
        description="Yahoo Finance OHLCV + makro endeksler (USDTRY, VIX, BRENT, SP500)",
        data_type="price",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["price", "ohlcv", "macro", "index"],
    )


def _make_evds(DataSource: type) -> DataSource:
    def fetch(series: str, lookback: str = "1y", **_: Any):
        from src.data.evds_client import fetch_series

        rows = fetch_series(series, lookback=lookback)
        import pandas as pd

        return pd.DataFrame(rows) if rows else pd.DataFrame()

    return DataSource(
        name="evds",
        description="TCMB EVDS — TLREF, TUFE, doviz, yabanci sahiplik serisi",
        data_type="macro",
        fetcher=fetch,
        fallback="evds_snapshot",
        auth_required=True,
        tags=["macro", "tcmb", "fx", "cpi", "tlref"],
    )


def _make_evds_snapshot(DataSource: type) -> DataSource:
    def fetch(series: str, **_: Any):
        import pathlib

        import pandas as pd

        snap = (
            pathlib.Path("data/snapshots")
            / f"{series.lower().replace('.', '_')}_series.parquet"
        )
        if snap.exists():
            return pd.read_parquet(snap)
        raise FileNotFoundError(f"EVDS snapshot yok: {snap}")

    return DataSource(
        name="evds_snapshot",
        description="EVDS frozen parquet snapshot (offline fallback)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "offline", "snapshot"],
    )


def _make_kap(DataSource: type) -> DataSource:
    def fetch(ticker: str, days: int = 90, **_: Any):
        import datetime

        from kap_client import Kap

        from src.data.kap_fetcher import fetch_disclosures_for_symbol

        kap = Kap()
        target_date = datetime.date.today()
        return fetch_disclosures_for_symbol(ticker, target_date, kap)

    return DataSource(
        name="kap",
        description="KAP API bildiri endeksi (son N gun) — MKK auth gerekli",
        data_type="kap",
        fetcher=fetch,
        fallback="kap_scraper",
        auth_required=True,
        tags=["kap", "disclosure", "mkk"],
    )


def _make_isyatirim(DataSource: type) -> DataSource:
    def fetch(ticker: Optional[str] = None, **_: Any):
        from src.signals.layers.connectors.smart_money_connector import (
            IsYatirimScreenerConnector,
        )

        conn = IsYatirimScreenerConnector()
        data = conn.fetch_all_tickers()
        if ticker and isinstance(data, dict):
            return data.get(ticker, {})
        return data

    return DataSource(
        name="isyatirim",
        description="Is Yatirim screener — yabanci saklama orani, 1w/1m degisim (bps)",
        data_type="foreign",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["foreign", "custody", "screener", "smart_money"],
    )


def _make_news(DataSource: type) -> DataSource:
    def fetch(ticker: str, days: int = 7, **_: Any):
        from src.data.news_fetcher import MynetNewsFetcher

        articles = MynetNewsFetcher().fetch(ticker, days=days)
        return [
            {
                "title": a.title,
                "date": a.date,
                "source": a.source,
            }
            for a in articles
        ]

    return DataSource(
        name="news",
        description="Finansal haberler — Mynet Finans (ticker bazli)",
        data_type="news",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["news", "sentiment", "mynet"],
    )


def _make_viop(DataSource: type) -> DataSource:
    def fetch(target_date: Optional[Any] = None, **_: Any):
        from src.data.viop_fetcher import fetch_viop_csv

        return fetch_viop_csv(target_date=target_date)

    return DataSource(
        name="viop",
        description="BIST VIOP CSV — Put/Call orani, Open Interest (gunluk)",
        data_type="viop",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["viop", "derivatives", "pcr", "oi"],
    )


def _make_bist_datastore(DataSource: type) -> DataSource:
    def fetch(ticker: Optional[str] = None, **_: Any):
        import pathlib
        import sqlite3

        import pandas as pd

        db_path = pathlib.Path("data/bist_datastore/foreign_monthly.db")
        if not db_path.exists():
            return pd.DataFrame()
        conn = sqlite3.connect(db_path)
        if ticker:
            df = pd.read_sql(
                "SELECT * FROM foreign_monthly WHERE ticker = ?",
                conn,
                params=(ticker,),
            )
        else:
            df = pd.read_sql("SELECT * FROM foreign_monthly", conn)
        conn.close()
        return df

    return DataSource(
        name="bist_datastore",
        description="BIST Datastore — yabanci islem (aylik, USD), foreign_monthly.db",
        data_type="foreign",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["foreign", "monthly", "bist", "usd"],
    )


def _make_fintables(DataSource: type) -> DataSource:
    def fetch(**_: Any):
        from src.data.fintables_scraper import FintablesScraperConnector

        conn = FintablesScraperConnector()
        return conn.scrape_all()

    return DataSource(
        name="fintables",
        description="Fintables custody scraper (Playwright, BIST50) — email/sifre gerekli",
        data_type="foreign",
        fetcher=fetch,
        fallback=None,
        auth_required=True,
        tags=["foreign", "custody", "fintables", "playwright"],
    )


def _make_cds(DataSource: type) -> DataSource:
    def fetch(**_: Any):
        from src.signals.local.cds_client import CDSClient
        from src.signals.local.local_macro_cache import LocalMacroCache

        cache = LocalMacroCache()
        client = CDSClient(cache=cache)
        client.fetch_and_store()
        return cache.get_cds()

    return DataSource(
        name="cds",
        description="Turkiye 5Y CDS (World Gov Bonds API)",
        data_type="macro",
        fetcher=fetch,
        fallback="cds_fallback",
        auth_required=False,
        tags=["macro", "cds", "risk"],
    )


def _make_cds_fallback(DataSource: type) -> DataSource:
    def fetch(**_: Any):
        from src.signals.local.cds_fallback import CDSFallbackClient
        from src.signals.local.local_macro_cache import LocalMacroCache

        cache = LocalMacroCache()
        client = CDSFallbackClient(cache=cache)
        client.fetch_and_store()
        return cache.get_cds()

    return DataSource(
        name="cds_fallback",
        description="CDS fallback — yfinance proxy hesabi",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "cds", "fallback"],
    )

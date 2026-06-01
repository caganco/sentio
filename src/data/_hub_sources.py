"""
DataHub kaynak kayitlari — mevcut fetcher'larin hub registration'i.

Her _make_* fonksiyonu bir DataSource dondurur veya hata durumunda None.
Tum modul importlari fonksiyon govdelerinde lazy yapilir; modul-seviyesinde
import yok, dolayisiyla circular import ve optional-dependency sorunu olmaz.

Mevcut moduller DEGISMEZ — hub bunlari sadece wrapper olarak bilir.

Duzeltmeler (v2):
  - LocalMacroCache import yolu: local_macro_cache -> cache_store (dogrusu)
  - cache.get_cds() -> cache.get_latest_cds() (metod adi duzeltildi)
  - kap_scraper kaydi eklendi (kap fallback olarak referans ediliyordu ama yoktu)
  - tcmb, bist_foreign, dxy, macro_global, event_signals, event_returns,
    em_relative_strength kaynaklari eklendi
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
        # --- Dis kaynaklar (canli API / scrape) ---
        _make_yfinance,
        _make_macro_global,
        _make_evds,
        _make_evds_snapshot,
        _make_kap,
        _make_kap_scraper,
        _make_isyatirim,
        _make_news,
        _make_viop,
        _make_fintables,
        # --- Yerel makro cache (SQLite: data/local_macro.db) ---
        _make_cds,
        _make_cds_fallback,
        _make_tcmb,
        _make_bist_foreign,
        _make_dxy,
        _make_em_relative_strength,
        # --- Disk uzerindeki veri magazalari ---
        _make_bist_datastore,
        _make_event_signals,
        _make_event_returns,
    ]
    for fn in makers:
        try:
            src = fn(DataSource)
            if src is not None:
                hub.register(src)
        except Exception as exc:
            log.warning("DataHub kayit hatasi [%s]: %s", fn.__name__, exc)


# ---------------------------------------------------------------------------
# DIS KAYNAKLAR
# ---------------------------------------------------------------------------


def _make_yfinance(DataSource: type) -> DataSource:
    """Yahoo Finance OHLCV + makro endeksler.

    Parametreler:
        ticker   : str   — ornek: "AKBNK.IS", "USDTRY=X", "^VIX", "GC=F"
        lookback : str   — yfinance period: "1d","5d","1mo","3mo","6mo","1y","2y","5y","max"
        interval : str   — "1d" (varsayilan), "1wk", "1mo"

    Donus: pd.DataFrame  columns=[Open,High,Low,Close,Volume], DatetimeIndex
    Forward-only: HAYIR — tarihsel veri mevcuttur
    """
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
        description="Yahoo Finance OHLCV + makro endeksler (USDTRY, VIX, BRENT, SP500, Gold)",
        data_type="price",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["price", "ohlcv", "macro", "index"],
    )


def _make_macro_global(DataSource: type) -> DataSource:
    """Global makro verilerin tek cagriyla cekilmesi.

    Parametreler: yok

    Donus: dict  {usdtry, usdtry_change_pct, vix, vix_change_pct,
                   oil_brent, oil_brent_change_pct, sp500, sp500_change_pct,
                   gold, gold_change_pct}
    Forward-only: HAYIR
    Notlar: Her deger son kapanis veya None (indir basarisiz oldugunda)
    """
    def fetch(**_: Any):
        from src.data.macro import fetch_macro_data

        return fetch_macro_data()

    return DataSource(
        name="macro_global",
        description="Global makro bundle: USDTRY, VIX, Brent, SP500, Gold (son kapanis + degisim%)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "global", "fx", "vix", "oil", "gold"],
    )


def _make_evds(DataSource: type) -> DataSource:
    """TCMB EVDS — TLREF, TUFE, doviz, yabanci sahiplik serisi.

    Parametreler:
        series   : str  — EVDS seri kodu, ornek:
                          "TP.BISTTLREF.KAPANIS"   TLREF kapanis endeksi
                          "TP.BISTTLREF.ORAN"      TLREF faiz orani
                          "TP.MKBRGN.A"            BIST yabanci pay orani (haftalik)
                          "TP.TUFE"                TUFE enflasyon endeksi
                          "TP.APIFON4"             TCMB agirlikli ort. fonlama orani
        lookback : str  — "1y" (varsayilan), "2y", "5y" vb.

    Donus: pd.DataFrame  columns=[date, value], tarih azalan sirali
    Auth: EVDS_API_KEY (env degiskeni) — eksikse evds_snapshot'a duser
    Forward-only: HAYIR
    """
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
    """EVDS frozen parquet snapshot — EVDS API yokken offline fallback.

    Parametreler:
        series : str  — seri kodu (dosya adi: data/snapshots/{seri_kucuk}_series.parquet)

    Donus: pd.DataFrame — snapshot tarihi itibarilye veri
    Forward-only: HAYIR — dondurulmus tarihsel veri
    """
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
    """KAP bildiri endeksi — MKK auth gerektiren resmi API.

    Parametreler:
        ticker : str   — ornek: "THYAO", "AKBNK"
        days   : int   — kac gun geriye bakilacak (varsayilan 90)

    Donus: list[dict]  her eleman:
           {index, publish_datetime, company_name, subject, summary, ...}
    Auth: kap-client ic auth (otomatik)
    Forward-only: HAYIR
    Notlar: HT endpoint ~May 2026 itibarilye bozuk; bos liste donebilir.
            Basarisiz olursa kap_scraper fallback'e gecer.
    """
    def fetch(ticker: str, days: int = 90, **_: Any):
        import datetime

        from kap_client import Kap

        from src.data.kap_fetcher import fetch_disclosures_for_symbol

        kap = Kap()
        target_date = datetime.date.today()
        return fetch_disclosures_for_symbol(ticker, target_date, kap)

    return DataSource(
        name="kap",
        description="KAP resmi API bildiri endeksi — MKK auth",
        data_type="kap",
        fetcher=fetch,
        fallback="kap_scraper",
        auth_required=True,
        tags=["kap", "disclosure", "mkk"],
    )


def _make_kap_scraper(DataSource: type) -> DataSource:
    """KAP bildirimleri — Google News RSS + Mynet scraper (auth-free fallback).

    Parametreler:
        ticker           : str | list[str] | None
                           tek ticker: "THYAO"
                           liste: ["THYAO","AKBNK"]
                           None: config'deki PORTFOLIO_TICKERS kullanilir
        watchlist_tickers: list[str] | None  — ek ticker listesi
        company_names    : dict[str,str] | None  — {ticker: sirket_adi}

    Donus: list[dict]  her eleman:
           {source, ticker, title, published, category, url}
           category: "CRITICAL" | "IMPORTANT" | "NOISE"
    Auth: gerekmiyor
    Forward-only: HAYIR — son ~24 saat haberi
    """
    def fetch(
        ticker: Optional[Any] = None,
        watchlist_tickers: Optional[Any] = None,
        company_names: Optional[Any] = None,
        **_: Any,
    ):
        from src.data.kap_scraper import fetch_kap_news

        return fetch_kap_news(
            ticker_or_tickers=ticker,
            watchlist_tickers=watchlist_tickers,
            company_names=company_names,
        )

    return DataSource(
        name="kap_scraper",
        description="KAP bildirimleri — Google News RSS + Mynet (auth-free fallback)",
        data_type="kap",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["kap", "disclosure", "rss", "scraper"],
    )


def _make_isyatirim(DataSource: type) -> DataSource:
    """Is Yatirim screener — yabanci saklama orani (custody) ve degisim.

    Parametreler:
        ticker : str | None
                 "AKBNK" -> sadece o ticker'in verisini dondurur (dict)
                 None    -> tum BIST tickers (dict[str, dict])

    Donus:
        ticker verilirse  : dict  {foreign_ratio, delta_1w_bps, delta_1m_bps}
        ticker verilmezse : dict[str, dict]  {TICKER: {...}}
    Auth: gerekmiyor (robots.txt onaylı endpoint)
    Forward-only: HAYIR — anlik oran
    Staleness: SMART_MONEY_STALE_HOURS (24h)
    """
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
    """Finansal haberler — Mynet Finans (ticker bazli, 24h cache).

    Parametreler:
        ticker : str  — ornek: "EREGL", "THYAO"
        days   : int  — kac gun geriye haberler cekilsin (varsayilan 7)

    Donus: list[dict]  her eleman: {title, date, source}
    Auth: gerekmiyor
    Forward-only: HAYIR
    Cache: data/news_cache.json (24h TTL)
    """
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
    """BIST VIOP CSV — Put/Call orani ve Open Interest (gunluk).

    Parametreler:
        target_date : date | str | None  — None ise bugunun verisi

    Donus: pd.DataFrame | None  — VIOP kontratlari
           Sutunlar: ticker, type (call/put/future), expiry, strike, open_interest, ...
    Auth: gerekmiyor
    Forward-only: HAYIR
    Encoding: windows-1254, ayirici=";", ondalik=","
    """
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


def _make_fintables(DataSource: type) -> DataSource:
    """Fintables custody scraper — BIST50 yabanci saklama (Playwright).

    Parametreler: yok (tum BIST50'yi toplu ceker)

    Donus: dict[str, bool]  — {ticker: scrape_basarili}
    Auth: FINTABLES_EMAIL + FINTABLES_PASSWORD (env) — ZORUNLU
    Forward-only: HAYIR
    Notlar: Playwright gerektirir; ~30sn; sadece BIST50 kapsami
    """
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


# ---------------------------------------------------------------------------
# YEREL MAKRO CACHE (SQLite: data/local_macro.db)
# ---------------------------------------------------------------------------


def _make_cds(DataSource: type) -> DataSource:
    """Turkiye 5Y CDS — World Gov Bonds API (baz puan).

    Parametreler: yok

    Donus: dict | None  — {data_date, cds_bps, source, confidence, fetched_at}
    Auth: gerekmiyor
    Forward-only: HAYIR
    Staleness: CDS_STALE_DAYS
    Fallback: cds_fallback (yfinance iShares TUR proxy modeli)
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.cds_client import CDSClient

        cache = LocalMacroCache()
        client = CDSClient(cache=cache)
        client.fetch_and_store()
        return cache.get_latest_cds()

    return DataSource(
        name="cds",
        description="Turkiye 5Y CDS (World Gov Bonds API) — baz puan",
        data_type="macro",
        fetcher=fetch,
        fallback="cds_fallback",
        auth_required=False,
        tags=["macro", "cds", "risk"],
    )


def _make_cds_fallback(DataSource: type) -> DataSource:
    """CDS fallback — yfinance proxy hesabi (iShares TUR + USDTRY + VIX).

    Parametreler: yok

    Donus: dict | None  — {data_date, cds_bps, source, confidence, fetched_at}
    Auth: gerekmiyor
    Model: CDS_est = base + a*(USDTRY-baseline) + b*VIX + c*TUR_return
    Sinirlar: [100, 800] bps
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.cds_fallback import CDSFallbackClient

        cache = LocalMacroCache()
        client = CDSFallbackClient(cache=cache)
        client.fetch_and_store()
        return cache.get_latest_cds()

    return DataSource(
        name="cds_fallback",
        description="CDS fallback — yfinance proxy hesabi (iShares TUR + USDTRY + VIX)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "cds", "fallback"],
    )


def _make_tcmb(DataSource: type) -> DataSource:
    """TCMB para politikasi kararlari — politika faizi gecmisi.

    Parametreler: yok

    Donus: dict | None  — {decision_date, decision_type, rate_before, rate_after,
                            source, confidence, fetched_at}
    Auth: gerekmiyor (tcmb.gov.tr + EVDS ikili kaynak)
    Forward-only: HAYIR
    Staleness: TCMB_STALE_DAYS (tipik 7-30 gun)
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.tcmb_client import TCMBClient

        cache = LocalMacroCache()
        client = TCMBClient(cache=cache)
        client.fetch_and_store()
        return cache.get_latest_tcmb()

    return DataSource(
        name="tcmb",
        description="TCMB para politikasi — son faiz karari (karar_tipi, onceki_oran, sonraki_oran)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "tcmb", "policy_rate"],
    )


def _make_bist_foreign(DataSource: type) -> DataSource:
    """BIST haftalik yabanci pay orani — EVDS makro context (L2).

    Parametreler: yok

    Donus: dict | None  — {week_ending_date, foreign_ownership_pct,
                            pct_change_weekly, source, confidence, fetched_at}
    Auth: EVDS_API_KEY (env) — eksikse YAML fallback
    Forward-only: HAYIR
    Staleness: BIST_FOREIGN_STALE_DAYS (tipik 7 gun)
    Not: Bu L2 makro context'i; L5 smart money icin bkz. isyatirim / bist_datastore
    """
    def fetch(**_: Any):
        from src.signals.local.bist_foreign_client import BistForeignOwnershipClient
        from src.signals.local.cache_store import LocalMacroCache

        cache = LocalMacroCache()
        client = BistForeignOwnershipClient(cache=cache)
        client.fetch_and_store()
        return cache.get_latest_bist_foreign()

    return DataSource(
        name="bist_foreign",
        description="BIST haftalik yabanci pay orani — EVDS makro context (L2)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=True,
        tags=["macro", "foreign", "bist", "evds"],
    )


def _make_dxy(DataSource: type) -> DataSource:
    """DXY US Dollar Index — haftalik kapanis ve degisim orani.

    Parametreler: yok

    Donus: dict | None  — {data_date, close, weekly_change_pct, fetched_at}
    Auth: gerekmiyor (yfinance DX-Y.NYB)
    Forward-only: HAYIR
    Staleness: DXY_STALE_DAYS (tipik 3-5 gun)
    Yorum: Yuksek DXY -> USD guclu -> EM sermaye cikisi -> BIST icin negatif
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.dxy_client import DXYClient

        cache = LocalMacroCache()
        client = DXYClient(cache=cache)
        client.fetch_and_store()
        return cache.get_latest_dxy()

    return DataSource(
        name="dxy",
        description="DXY US Dollar Index — haftalik degisim (DX-Y.NYB via yfinance)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "dxy", "fx", "usd"],
    )


def _make_em_relative_strength(DataSource: type) -> DataSource:
    """BIST100/EEM relative strength — normalize edilmis fark skoru.

    Parametreler:
        lookback_days : int | None  — varsayilan EM_RELSTRENGTH_LOOKBACK

    Donus: float | None  — [-1.0, +1.0] araliginda
           +1.0 = BIST EM'i guclu geciyor
           -1.0 = BIST EM'in gerisinde
           None = veri indirilemiyor
    Auth: gerekmiyor
    Forward-only: HAYIR
    """
    def fetch(lookback_days: Optional[int] = None, **_: Any):
        from src.data.macro_sources import fetch_em_relative_strength

        if lookback_days is not None:
            return fetch_em_relative_strength(lookback_days=lookback_days)
        return fetch_em_relative_strength()

    return DataSource(
        name="em_relative_strength",
        description="BIST100/EEM relative strength (normalize [-1,+1]; +1 = BIST EM'i geciyor)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "em", "relative_strength", "bist"],
    )


# ---------------------------------------------------------------------------
# DISK UZERINDEKI VERI MAGAZALARI
# ---------------------------------------------------------------------------


def _make_bist_datastore(DataSource: type) -> DataSource:
    """BIST DataStore — yabanci islemler (aylik, USD), foreign_monthly.db.

    Parametreler:
        ticker : str | None  — "AKBNK" -> sadece o ticker; None -> tum tablo

    Donus: pd.DataFrame  columns=[date, ticker, usd_net_trades, ...]
    Auth: datastore_session.json (JWT + cookie) — aylik manuel yenileme
    FORWARD-ONLY: EVET — 2024-12'den itibaren birikimli; oncesi yok
    Kapsam: sadece ZIP olarak indirilen aylar mevcuttur (data/bist_datastore/)
    """
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
        description="BIST DataStore yabanci islem (aylik USD) — FORWARD-ONLY 2024-12'den",
        data_type="foreign",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["foreign", "monthly", "bist", "usd", "forward_only"],
    )


def _make_event_signals(DataSource: type) -> DataSource:
    """Olay sinyalleri on-kayit (degistirilemez) — FORWARD-ONLY.

    Parametreler:
        ticker : str | None  — belirli ticker filtreleme (None = tumu)
        after  : str | None  — "YYYY-MM-DD" formatinda baslangic filtresi

    Donus: pd.DataFrame  columns=[natural_key, event_date, ticker, event_type,
                                   surprise_real, technical_confirm, signal_fired,
                                   as_of_timestamp]
    Auth: gerekmiyor (yerel dosya)
    FORWARD-ONLY: EVET — 2026-06-01'den itibaren birikimli
    Immutable: natural_key uzerinde idempotent; uzerine yazma yoktur.
    Neden forward-only: on-kayit garantisi — sinyal gelecek donus bilinmeden kaydedilir.
    Task Scheduler: clone3/data/event_logs/, 19:00 gunluk
    """
    def fetch(ticker: Optional[str] = None, after: Optional[str] = None, **_: Any):
        import pathlib

        import pandas as pd

        signals_path = pathlib.Path("data/event_logs/event_signals.parquet")
        if not signals_path.exists():
            return pd.DataFrame()
        df = pd.read_parquet(signals_path)
        if ticker:
            df = df[df["ticker"] == ticker]
        if after:
            df = df[df["event_date"] >= after]
        return df

    return DataSource(
        name="event_signals",
        description="Olay sinyalleri on-kayit (immutable) — FORWARD-ONLY 2026-06-01'den",
        data_type="kap",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["event", "forward_only", "kap", "immutable"],
    )


def _make_event_returns(DataSource: type) -> DataSource:
    """Olay geriye-donuk getirileri — FORWARD-ONLY (horizon olgunlastikca dolar).

    Parametreler:
        ticker  : str | None  — belirli ticker filtreleme
        horizon : int | None  — 1, 5, 20, 60 (gun olarak ufuk filtresi)

    Donus: pd.DataFrame  columns=[natural_key, ticker, event_date, event_type,
                                   horizon, entry_date, exit_date,
                                   gross_return, rel_net_return, filled_at]
    Auth: gerekmiyor
    FORWARD-ONLY: EVET — 2026-06-01 on-kayitlari olgunlasinca dolmaya baslar
                  t+1 = min 1 is gunu; t+60 = yaklasik Agustos 2026'dan itibaren
    Not: event_signals.parquet dolmadan bu tablo bos kalabilir (normal durum).
    """
    def fetch(ticker: Optional[str] = None, horizon: Optional[int] = None, **_: Any):
        import pathlib

        import pandas as pd

        returns_path = pathlib.Path("data/event_logs/event_returns.parquet")
        if not returns_path.exists():
            return pd.DataFrame()
        df = pd.read_parquet(returns_path)
        if ticker:
            df = df[df["ticker"] == ticker]
        if horizon is not None:
            df = df[df["horizon"] == horizon]
        return df

    return DataSource(
        name="event_returns",
        description="Olay geriye-donuk getirileri (t+1/5/20/60) — FORWARD-ONLY 2026-06-01'den",
        data_type="kap",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["event", "forward_only", "returns", "horizon"],
    )

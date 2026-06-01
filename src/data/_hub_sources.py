"""
DataHub kaynak kayitlari — mevcut fetcher'larin hub registration'i.

Her _make_* fonksiyonu bir DataSource dondurur.
Tum modul importlari fonksiyon govdelerinde lazy yapilir — circular import yok.
Mevcut moduller DEGISMEZ; hub onlari wrapper olarak bilir.

v2: LocalMacroCache import yolu duzeltildi, get_cds() -> get_latest_cds(),
    kap_scraper kaydi eklendi, 8 yeni kaynak eklendi.

v3: _RateLimiter eklendi (yfinance/evds/kap/isyatirim/fintables),
    paylasimli ham fetcher fonksiyonlari (raw + clean icin ortak),
    clean/typed kaynaklar: yfinance_clean, macro_global_clean, kap_clean, evds_clean,
    _hub_types.py: MacroSnapshot + KAPItem dataclass'lari.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.data.data_hub import DataHub, DataSource

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RATE LIMITER
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Thread-safe sabit-aralik bekleme (token bucket basitlesmis)."""

    def __init__(self, calls_per_second: float) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call: float = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_call
            gap = self._min_interval - elapsed
            if gap > 0:
                time.sleep(gap)
            self._last_call = time.monotonic()


# Modul-seviyesi limiter'lar — tum cagrilar arasinda paylasimli state
_rl_yfinance = _RateLimiter(1.0)     # 1 istek/sn   — Yahoo Finance soft limit
_rl_macro = _RateLimiter(0.2)        # 1 istek/5 sn  — macro_global 5 yf cagrisi
_rl_evds = _RateLimiter(0.33)        # 1 istek/3 sn  — TCMB devlet API'si
_rl_kap = _RateLimiter(0.5)          # 1 istek/2 sn  — RSS/scraping
_rl_isyatirim = _RateLimiter(0.5)    # 1 istek/2 sn  — Is Yatirim screener
_rl_fintables = _RateLimiter(0.2)    # 1 istek/5 sn  — Playwright oturumu


# ---------------------------------------------------------------------------
# PAYLASIMLI HAM FETCHER FONKSIYONLARI
# Raw source ile clean source ayni fonksiyonu kullanir — limiter bir kez uygulanir.
# ---------------------------------------------------------------------------


def _fetch_yfinance_raw(
    ticker: str, lookback: str = "1y", interval: str = "1d", **_: Any
) -> Any:
    _rl_yfinance.wait()
    import yfinance as yf

    return yf.download(
        ticker,
        period=lookback,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )


def _fetch_macro_global_raw(**_: Any) -> Any:
    _rl_macro.wait()
    from src.data.macro import fetch_macro_data

    return fetch_macro_data()


def _fetch_kap_scraper_raw(
    ticker: Optional[Any] = None,
    watchlist_tickers: Optional[Any] = None,
    company_names: Optional[Any] = None,
    **_: Any,
) -> Any:
    _rl_kap.wait()
    from src.data.kap_scraper import fetch_kap_news

    return fetch_kap_news(
        ticker_or_tickers=ticker,
        watchlist_tickers=watchlist_tickers,
        company_names=company_names,
    )


def _fetch_evds_raw(series: str, lookback: str = "1y", **_: Any) -> list:
    _rl_evds.wait()
    from src.data.evds_client import fetch_series

    return fetch_series(series, lookback=lookback)


# ---------------------------------------------------------------------------
# NORMALIZASYON YARDIMCILARI
# ---------------------------------------------------------------------------


def _normalize_ohlcv(df: Any, ticker: Optional[str]) -> Any:
    """yfinance DataFrame -> standart OHLCV.

    Cikti: lowercase sutunlar, DatetimeIndex(date), tz-naive, ticker sutunu.
    """
    import pandas as pd

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return df
    df = df.copy()
    # Yeni yfinance surumlerinde MultiIndex donebilir
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    if "adj close" in df.columns:
        df = df.rename(columns={"adj close": "adj_close"})
    keep = [c for c in ["open", "high", "low", "close", "volume", "adj_close"] if c in df.columns]
    df = df[keep]
    if ticker:
        df.insert(0, "ticker", ticker)
    df.index.name = "date"
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df.sort_index()


def _normalize_evds(rows: list, series: str) -> Any:
    """EVDS list[{date, value}] -> DataFrame(DatetimeIndex, sutun = seri_kodu)."""
    import pandas as pd

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    col = series.lower().replace(".", "_")
    df = df.rename(columns={"value": col})
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()


# ---------------------------------------------------------------------------
# KAYIT FONKSIYONU
# ---------------------------------------------------------------------------


def register_all(hub: type) -> None:
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
        # --- Clean/typed kaynaklar (normalize edilmis sema, _hub_types.py) ---
        _make_yfinance_clean,
        _make_macro_global_clean,
        _make_kap_clean,
        _make_evds_clean,
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
        lookback : str   — "1d","5d","1mo","3mo","6mo","1y","2y","5y","max"
        interval : str   — "1d" (varsayilan), "1wk", "1mo"

    Donus: pd.DataFrame  columns=[Open,High,Low,Close,Volume], DatetimeIndex
    Rate limit: 1 istek/sn
    Forward-only: HAYIR
    """
    def fetch(ticker: str, lookback: str = "1y", interval: str = "1d", **_: Any):
        return _fetch_yfinance_raw(ticker=ticker, lookback=lookback, interval=interval)

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
    Rate limit: 1 istek/5 sn (ic yfinance cagrisi x5)
    Forward-only: HAYIR
    """
    def fetch(**_: Any):
        return _fetch_macro_global_raw()

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
        series   : str  — EVDS seri kodu
        lookback : str  — "1y" (varsayilan), "2y", "5y" vb.

    Donus: pd.DataFrame  columns=[date, value], tarih azalan sirali
    Rate limit: 1 istek/3 sn
    Auth: EVDS_API_KEY (env degiskeni) — eksikse evds_snapshot'a duser
    Forward-only: HAYIR
    """
    def fetch(series: str, lookback: str = "1y", **_: Any):
        import pandas as pd

        rows = _fetch_evds_raw(series=series, lookback=lookback)
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
        series : str  — seri kodu (data/snapshots/{seri_kucuk}_series.parquet)

    Donus: pd.DataFrame — snapshot tarihi itibarilye veri
    Forward-only: HAYIR
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

    Donus: list[dict]  {index, publish_datetime, company_name, subject, summary, ...}
    Auth: kap-client ic auth
    Forward-only: HAYIR
    Not: HT endpoint ~May 2026 bozuk; bos liste donebilir -> kap_scraper fallback
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
        ticker            : str | list[str] | None
        watchlist_tickers : list[str] | None
        company_names     : dict[str,str] | None

    Donus: list[dict]  {source, ticker, title, published, category, url}
           category: "CRITICAL" | "IMPORTANT" | "NOISE"
    Rate limit: 1 istek/2 sn
    Forward-only: HAYIR
    """
    def fetch(
        ticker: Optional[Any] = None,
        watchlist_tickers: Optional[Any] = None,
        company_names: Optional[Any] = None,
        **_: Any,
    ):
        return _fetch_kap_scraper_raw(
            ticker=ticker,
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
    """Is Yatirim screener — yabanci saklama orani ve degisim.

    Parametreler:
        ticker : str | None
                 "AKBNK" -> tek ticker dict
                 None    -> tum BIST dict[str, dict]

    Donus:
        ticker verilirse  : dict  {foreign_ratio, delta_1w_bps, delta_1m_bps}
        ticker verilmezse : dict[str, dict]
    Rate limit: 1 istek/2 sn
    Forward-only: HAYIR
    """
    def fetch(ticker: Optional[str] = None, **_: Any):
        _rl_isyatirim.wait()
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
        days   : int  — kac gun geriye (varsayilan 7)

    Donus: list[dict]  [{title, date, source}, ...]
    Forward-only: HAYIR
    """
    def fetch(ticker: str, days: int = 7, **_: Any):
        from src.data.news_fetcher import MynetNewsFetcher

        articles = MynetNewsFetcher().fetch(ticker, days=days)
        return [{"title": a.title, "date": a.date, "source": a.source} for a in articles]

    return DataSource(
        name="news",
        description="Finansal haberler — Mynet Finans (ticker bazli, 24h cache)",
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

    Donus: pd.DataFrame | None
           Sutunlar: ticker, type (call/put/future), expiry, strike, open_interest, ...
    Forward-only: HAYIR
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

    Parametreler: yok (tum BIST50 toplu cekilir)

    Donus: dict[str, bool]  {ticker: scrape_basarili}
    Rate limit: 1 istek/5 sn (Playwright oturumu)
    Auth: FINTABLES_EMAIL + FINTABLES_PASSWORD (env) — ZORUNLU
    Forward-only: HAYIR
    """
    def fetch(**_: Any):
        _rl_fintables.wait()
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

    Donus: dict | None  {data_date, cds_bps, source, confidence, fetched_at}
    Forward-only: HAYIR
    Fallback: cds_fallback (yfinance iShares TUR proxy modeli)
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.cds_client import CDSClient

        cache = LocalMacroCache()
        CDSClient(cache=cache).fetch_and_store()
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

    Donus: dict | None  {data_date, cds_bps, source, confidence, fetched_at}
    Model: CDS_est = base + a*(USDTRY-baseline) + b*VIX + c*TUR_return
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.cds_fallback import CDSFallbackClient

        cache = LocalMacroCache()
        CDSFallbackClient(cache=cache).fetch_and_store()
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

    Donus: dict | None  {decision_date, decision_type, rate_before, rate_after,
                          source, confidence, fetched_at}
    Forward-only: HAYIR
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.tcmb_client import TCMBClient

        cache = LocalMacroCache()
        TCMBClient(cache=cache).fetch_and_store()
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

    Donus: dict | None  {week_ending_date, foreign_ownership_pct,
                          pct_change_weekly, source, confidence, fetched_at}
    Forward-only: HAYIR
    """
    def fetch(**_: Any):
        from src.signals.local.bist_foreign_client import BistForeignOwnershipClient
        from src.signals.local.cache_store import LocalMacroCache

        cache = LocalMacroCache()
        BistForeignOwnershipClient(cache=cache).fetch_and_store()
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

    Donus: dict | None  {data_date, close, weekly_change_pct, fetched_at}
    Forward-only: HAYIR
    """
    def fetch(**_: Any):
        from src.signals.local.cache_store import LocalMacroCache
        from src.signals.local.dxy_client import DXYClient

        cache = LocalMacroCache()
        DXYClient(cache=cache).fetch_and_store()
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

    Donus: float | None  [-1.0, +1.0]
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
    FORWARD-ONLY: EVET — 2024-12'den itibaren birikimli
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
        ticker : str | None  — belirli ticker filtreleme
        after  : str | None  — "YYYY-MM-DD" baslangic filtresi

    Donus: pd.DataFrame  columns=[natural_key, event_date, ticker, event_type,
                                   surprise_real, technical_confirm, signal_fired,
                                   as_of_timestamp]
    FORWARD-ONLY: EVET — 2026-06-01'den itibaren birikimli
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
    """Olay geriye-donuk getirileri — FORWARD-ONLY (horizon olgunlasinca dolar).

    Parametreler:
        ticker  : str | None  — belirli ticker filtreleme
        horizon : int | None  — 1 | 5 | 20 | 60 (gun)

    Donus: pd.DataFrame  columns=[natural_key, ticker, event_date, event_type,
                                   horizon, entry_date, exit_date,
                                   gross_return, rel_net_return, filled_at]
    FORWARD-ONLY: EVET — 2026-06-01 on-kayitlari olgunlasinca dolar
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


# ---------------------------------------------------------------------------
# CLEAN / TYPED KAYNAKLAR
# Ham kaynak ile ayni rate limiter'i kullanir (paylasimli fonksiyon).
# Fallback yok: clean kaynak hata verirse exception — degrade edilmis tip yok.
# ---------------------------------------------------------------------------


def _make_yfinance_clean(DataSource: type) -> DataSource:
    """Yahoo Finance OHLCV — normalize edilmis format.

    Parametreler: yfinance ile ayni (ticker, lookback, interval)

    Donus: pd.DataFrame
      index  : DatetimeIndex(date), tz-naive, artan sirali
      sutunlar: [ticker, open, high, low, close, volume, adj_close]  (lowercase)
    Rate limit: yfinance ile paylasimli (_rl_yfinance)
    Ham karsıligi: "yfinance"
    """
    def fetch(ticker: str, lookback: str = "1y", interval: str = "1d", **_: Any):
        raw = _fetch_yfinance_raw(ticker=ticker, lookback=lookback, interval=interval)
        return _normalize_ohlcv(raw, ticker)

    return DataSource(
        name="yfinance_clean",
        description="Yahoo Finance OHLCV — lowercase/DatetimeIndex/ticker sutunu (normalize)",
        data_type="price",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["price", "ohlcv", "clean", "typed"],
    )


def _make_macro_global_clean(DataSource: type) -> DataSource:
    """Global makro bundle — MacroSnapshot dataclass.

    Parametreler: yok

    Donus: MacroSnapshot | None
      .usdtry, .usdtry_change_pct
      .vix, .vix_change_pct
      .oil_brent, .oil_brent_change_pct
      .sp500, .sp500_change_pct
      .gold, .gold_change_pct
      Tum alanlar Optional[float] — indirilemeyen kaynak None doner.
    Rate limit: macro_global ile paylasimli (_rl_macro)
    Ham karsıligi: "macro_global"
    """
    def fetch(**_: Any):
        from src.data._hub_types import MacroSnapshot

        raw = _fetch_macro_global_raw()
        if raw is None:
            return None
        return MacroSnapshot.from_dict(raw)

    return DataSource(
        name="macro_global_clean",
        description="Global makro bundle — MacroSnapshot dataclass (typed, None-safe)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["macro", "global", "clean", "typed"],
    )


def _make_kap_clean(DataSource: type) -> DataSource:
    """KAP bildirimleri — list[KAPItem] typed.

    Parametreler: kap_scraper ile ayni (ticker, watchlist_tickers, company_names)

    Donus: list[KAPItem]
      .source, .ticker, .title, .published, .category, .url
      .is_critical -> bool  (category == "CRITICAL")
    Rate limit: kap_scraper ile paylasimli (_rl_kap)
    Ham karsıligi: "kap_scraper"
    """
    def fetch(
        ticker: Optional[Any] = None,
        watchlist_tickers: Optional[Any] = None,
        company_names: Optional[Any] = None,
        **_: Any,
    ):
        from src.data._hub_types import KAPItem

        raw = _fetch_kap_scraper_raw(
            ticker=ticker,
            watchlist_tickers=watchlist_tickers,
            company_names=company_names,
        )
        return [KAPItem.from_dict(d) for d in (raw or [])]

    return DataSource(
        name="kap_clean",
        description="KAP bildirimleri — list[KAPItem] (source, ticker, title, category, url)",
        data_type="kap",
        fetcher=fetch,
        fallback=None,
        auth_required=False,
        tags=["kap", "disclosure", "clean", "typed"],
    )


def _make_evds_clean(DataSource: type) -> DataSource:
    """TCMB EVDS — normalize edilmis DataFrame.

    Parametreler: evds ile ayni (series, lookback)

    Donus: pd.DataFrame
      index  : DatetimeIndex(date), artan sirali
      sutunlar: [<seri_kodu_lowercase>]  ornk "tp_bisttlref_kapanis"
    Rate limit: evds ile paylasimli (_rl_evds)
    Auth: EVDS_API_KEY (env degiskeni) — eksikse exception (snapshot fallback yok)
    Ham karsıligi: "evds"
    """
    def fetch(series: str, lookback: str = "1y", **_: Any):
        rows = _fetch_evds_raw(series=series, lookback=lookback)
        return _normalize_evds(rows, series)

    return DataSource(
        name="evds_clean",
        description="TCMB EVDS — DatetimeIndex(date), sutun = seri_kodu_lowercase (normalize)",
        data_type="macro",
        fetcher=fetch,
        fallback=None,
        auth_required=True,
        tags=["macro", "tcmb", "clean", "typed"],
    )

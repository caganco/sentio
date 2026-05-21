"""Fintables MKK takas scraper (D-116, SPEC_FINTABLES_TAKAS_SCRAPER_1).

Playwright sync API ile fintables.com/sirketler/{TICKER}/takas-analizi sayfasını
ayrıştırır. Sonuçları data/custody/custody_snapshots.db içine yazar.

Kullanım:
    from src.data.fintables_scraper import FintablesScraperConnector
    conn = FintablesScraperConnector()
    conn.scrape_all(date_str="2026-05-21")   # BIST50 döngüsü

Önemli: playwright OPSİYONEL bir bağımlılıktır ve yalnızca FintablesClient
metotları içinde lazy import edilir. CustodyDBWriter / dataclass'lar / connector
playwright kurulu OLMADAN da import edilebilir (testler buna güvenir).

Canlı-site bağımlı satırlar `# VERIFY AGAINST LIVE SITE` ile işaretlidir: bu
ortamda doğrulanamadı (Fintables 403 + login gerektiriyor). Credential ve canlı
erişimle CSS selector/login akışı/tarih navigasyonu doğrulanmalıdır.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pandas as pd

from src.signals.thresholds import (
    CUSTODY_BACKFILL_DAYS,
    CUSTODY_BIST50_TICKERS,
    CUSTODY_DB_PATH,
    CUSTODY_MAX_RETRIES,
    CUSTODY_RETRY_BACKOFF_SEC,
    CUSTODY_SCRAPE_RATE_LIMIT_SEC,
    CUSTODY_SCRAPE_TIMEOUT_SEC,
    CUSTODY_SESSION_FILE,
    CUSTODY_SESSION_MAX_AGE_HOURS,
    CUSTODY_STALE_HOURS,
)

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime playwright import
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_ISTANBUL = ZoneInfo("Europe/Istanbul")


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------

class CustodyScraperError(Exception):
    """Base scraper error."""


class TickerNotFoundError(CustodyScraperError):
    """Hisse Fintables'ta bulunamadı (404 veya boş tablo)."""


class LoginExpiredError(CustodyScraperError):
    """Cookie süresi dolmuş; yeniden login gerekli."""


class RateLimitError(CustodyScraperError):
    """HTTP 429 veya Fintables soft-block."""


# ---------------------------------------------------------------------------
# Turkish number parsing helpers (pure, unit-testable)
# ---------------------------------------------------------------------------

def parse_tr_float(text: str | None) -> float | None:
    """TR sayı formatını float'a çevir: "1.234,56" → 1234.56, "%12,3" → 12.3.

    Binlik ayraç '.', ondalık ayraç ','. '%', boşluk ve diğer semboller temizlenir.
    Ayrıştırılamazsa None döner.
    """
    if text is None:
        return None
    cleaned = re.sub(r"[^0-9,\.\-]", "", str(text))
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_tr_int(text: str | None) -> int | None:
    """TR lot/adet formatını int'e çevir: "1.234.567" → 1234567."""
    val = parse_tr_float(text)
    if val is None:
        return None
    return int(round(val))


# ---------------------------------------------------------------------------
# Dataclasses (DB row shapes)
# ---------------------------------------------------------------------------

@dataclass
class CustodySnapshot:
    """Tek kurum satırı (custody_snapshots tablosuna karşılık gelir)."""
    date: str          # YYYY-MM-DD
    ticker: str
    kurum_adi: str
    lot: int | None
    pct: float | None
    gunluk_delta: float | None
    haftalik_delta: float | None
    aylik_delta: float | None
    ucaylik_delta: float | None
    scraped_at: str    # ISO UTC


@dataclass
class CustodyDailySummary:
    """Hisse özeti satırı (custody_daily_summary tablosuna karşılık gelir)."""
    date: str
    ticker: str
    yabanci_toplam_pct: float | None
    kurumsal_pct: float | None
    bireysel_pct: float | None
    toplam_yatirimci_sayisi: int | None
    scraped_at: str


# ---------------------------------------------------------------------------
# CustodyDBWriter — SQLite upsert (playwright'sız, tam test edilebilir)
# ---------------------------------------------------------------------------

class CustodyDBWriter:
    """SQLite yazar. DB yoksa __init__ içinde şema oluşturulur (idempotent)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _init_db(self) -> None:
        """Tablolar ve indexler oluşturulur (idempotent)."""
        con = self._connect()
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS custody_snapshots (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    date          TEXT    NOT NULL,
                    ticker        TEXT    NOT NULL,
                    kurum_adi     TEXT    NOT NULL,
                    lot           INTEGER,
                    pct           REAL,
                    gunluk_delta  REAL,
                    haftalik_delta REAL,
                    aylik_delta   REAL,
                    ucaylik_delta REAL,
                    scraped_at    TEXT    NOT NULL,
                    UNIQUE(date, ticker, kurum_adi)
                );

                CREATE TABLE IF NOT EXISTS custody_daily_summary (
                    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                    date                     TEXT    NOT NULL,
                    ticker                   TEXT    NOT NULL,
                    yabanci_toplam_pct       REAL,
                    kurumsal_pct             REAL,
                    bireysel_pct             REAL,
                    toplam_yatirimci_sayisi  INTEGER,
                    scraped_at               TEXT    NOT NULL,
                    UNIQUE(date, ticker)
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_date_ticker
                    ON custody_snapshots(date, ticker);
                CREATE INDEX IF NOT EXISTS idx_summary_ticker_date
                    ON custody_daily_summary(ticker, date);
                CREATE INDEX IF NOT EXISTS idx_summary_date_ticker
                    ON custody_daily_summary(date, ticker);
                """
            )
            con.commit()
        finally:
            con.close()

    def upsert_snapshot(self, rows: list[CustodySnapshot]) -> int:
        """INSERT OR REPLACE kurum satırları. Döner: yazılan satır sayısı."""
        if not rows:
            return 0
        con = self._connect()
        try:
            con.executemany(
                """
                INSERT OR REPLACE INTO custody_snapshots
                    (date, ticker, kurum_adi, lot, pct, gunluk_delta,
                     haftalik_delta, aylik_delta, ucaylik_delta, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.date, r.ticker, r.kurum_adi, r.lot, r.pct,
                        r.gunluk_delta, r.haftalik_delta, r.aylik_delta,
                        r.ucaylik_delta, r.scraped_at,
                    )
                    for r in rows
                ],
            )
            con.commit()
        finally:
            con.close()
        return len(rows)

    def upsert_summary(self, row: CustodyDailySummary) -> None:
        """INSERT OR REPLACE hisse özet satırı."""
        con = self._connect()
        try:
            con.execute(
                """
                INSERT OR REPLACE INTO custody_daily_summary
                    (date, ticker, yabanci_toplam_pct, kurumsal_pct,
                     bireysel_pct, toplam_yatirimci_sayisi, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.date, row.ticker, row.yabanci_toplam_pct,
                    row.kurumsal_pct, row.bireysel_pct,
                    row.toplam_yatirimci_sayisi, row.scraped_at,
                ),
            )
            con.commit()
        finally:
            con.close()

    def get_history(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """custody_daily_summary'den (date, ticker, yabanci_toplam_pct) döner.

        date'e göre artan sıralı. Stale check: en son scraped_at
        > CUSTODY_STALE_HOURS ise boş DataFrame döner.
        """
        con = self._connect()
        try:
            df = pd.read_sql_query(
                """
                SELECT date, ticker, yabanci_toplam_pct, scraped_at
                FROM custody_daily_summary
                WHERE ticker = ?
                ORDER BY date ASC
                """,
                con,
                params=(ticker,),
            )
        finally:
            con.close()

        empty = pd.DataFrame(columns=["date", "ticker", "yabanci_toplam_pct"])
        if df.empty:
            return empty

        latest_scraped = df["scraped_at"].max()
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(latest_scraped)
            if age > timedelta(hours=CUSTODY_STALE_HOURS):
                logger.warning(
                    "CustodyDBWriter.get_history %s: stale (%.1fh > %dh) → empty",
                    ticker, age.total_seconds() / 3600, CUSTODY_STALE_HOURS,
                )
                return empty
        except (TypeError, ValueError):
            pass

        out = df[["date", "ticker", "yabanci_toplam_pct"]].tail(days)
        return out.reset_index(drop=True)

    def get_latest_date(self, ticker: str) -> str | None:
        """custody_daily_summary'deki en son date (YYYY-MM-DD). Backfill için."""
        con = self._connect()
        try:
            cur = con.execute(
                "SELECT MAX(date) FROM custody_daily_summary WHERE ticker = ?",
                (ticker,),
            )
            row = cur.fetchone()
        finally:
            con.close()
        return row[0] if row and row[0] else None

    def ticker_counts(self) -> dict[str, int]:
        """--check için: ticker başına distinct gün sayısı."""
        con = self._connect()
        try:
            cur = con.execute(
                """
                SELECT ticker, COUNT(DISTINCT date) AS n
                FROM custody_daily_summary
                GROUP BY ticker ORDER BY ticker
                """
            )
            rows = cur.fetchall()
        finally:
            con.close()
        return {t: int(n) for t, n in rows}


# ---------------------------------------------------------------------------
# FintablesClient — Playwright session yönetimi
# ---------------------------------------------------------------------------
# NOT: playwright bu sınıfın metotları İÇİNDE lazy import edilir; modül
# seviyesinde import YOK (testler playwright olmadan import edebilmeli).

class FintablesClient:
    """Playwright sync context + session cookie yönetimi.

    Login credentials ortam değişkenlerinden okunur:
        FINTABLES_EMAIL    (zorunlu)
        FINTABLES_PASSWORD (zorunlu)
    """

    BASE_URL = "https://fintables.com"
    LOGIN_URL = "https://fintables.com/giris"
    # VERIFY AGAINST LIVE SITE: ticker formatı (AKSEN vs AKSEN.IS) ve URL path.
    TAKAS_URL = "https://fintables.com/sirketler/{ticker}/takas-analizi"

    def __init__(self, session_file: str | Path | None = None) -> None:
        self.session_file = Path(session_file or CUSTODY_SESSION_FILE)
        self._pw = None
        self._browser = None
        self._context = None

    def __enter__(self) -> "FintablesClient":
        self._start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop()

    def _start(self) -> None:
        """Playwright başlat, mevcut session yükle veya yeniden login yap."""
        from playwright.sync_api import sync_playwright  # lazy import

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=(
                # VERIFY AGAINST LIVE SITE: gerçekçi UA bot-block'u azaltabilir.
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        if not self._load_session():
            self._login()

    def _stop(self) -> None:
        """Cookie kaydet, browser kapat, playwright durdur."""
        try:
            if self._context is not None:
                self._save_session()
        finally:
            if self._browser is not None:
                self._browser.close()
            if self._pw is not None:
                self._pw.stop()
            self._context = None
            self._browser = None
            self._pw = None

    def _load_session(self) -> bool:
        """.fintables_session.json varsa ve taze ise cookie'leri yükle."""
        if not self.session_file.exists():
            return False
        try:
            import json
            data = json.loads(self.session_file.read_text(encoding="utf-8"))
            saved_at = datetime.fromisoformat(data["saved_at"])
            age = datetime.now(timezone.utc) - saved_at
            if age > timedelta(hours=CUSTODY_SESSION_MAX_AGE_HOURS):
                logger.info("Fintables session expired (%.1fh) → re-login", age.total_seconds() / 3600)
                return False
            self._context.add_cookies(data["cookies"])  # type: ignore[union-attr]
            logger.debug("Fintables session loaded from %s", self.session_file)
            return True
        except Exception as exc:  # noqa: BLE001 - corrupt session → re-login
            logger.warning("Fintables session load failed (%s) → re-login", exc)
            return False

    def _save_session(self) -> None:
        """Cookie'leri .fintables_session.json'a kaydet."""
        try:
            import json
            cookies = self._context.cookies()  # type: ignore[union-attr]
            payload = {
                "cookies": cookies,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            self.session_file.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fintables session save failed: %s", exc)

    def _login(self) -> None:
        """FINTABLES_EMAIL + FINTABLES_PASSWORD ile login. Cookie kaydet."""
        email = os.getenv("FINTABLES_EMAIL")
        password = os.getenv("FINTABLES_PASSWORD")
        if not email or not password:
            raise ValueError(
                "FINTABLES_EMAIL / FINTABLES_PASSWORD ortam değişkenleri tanımlı değil"
            )

        page = self._context.new_page()  # type: ignore[union-attr]
        page.goto(self.LOGIN_URL, timeout=CUSTODY_SCRAPE_TIMEOUT_SEC * 1000)
        # VERIFY AGAINST LIVE SITE: login form input selector'ları.
        page.fill("input[name='email']", email)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        # VERIFY AGAINST LIVE SITE: login sonrası yönlendirme/başarı sinyali.
        try:
            page.wait_for_url(lambda u: "/giris" not in u, timeout=CUSTODY_SCRAPE_TIMEOUT_SEC * 1000)
        except Exception as exc:  # noqa: BLE001
            page.close()
            raise ValueError(f"Fintables login başarısız (captcha veya selector?): {exc}") from exc
        page.close()
        self._save_session()
        logger.info("Fintables login OK (%s)", email)

    def get_page(self, ticker: str, date_str: str | None = None) -> "Page":
        """{ticker}/takas-analizi sayfasını yükle, hazır Page döndür.

        date_str verilirse VERIFY: Senaryo A (?date= URL parametresi) denenir.
        Login redirect algılanırsa bir kez _login() + yeniden dene.
        """
        url = self.TAKAS_URL.format(ticker=ticker)
        # VERIFY AGAINST LIVE SITE (open Q1): geçmiş tarih ?date= parametresi
        # gerçekten destekleniyor mu? Desteklenmiyorsa backfill Senaryo B'ye düşer.
        if date_str:
            url = f"{url}?date={date_str}"

        page = self._context.new_page()  # type: ignore[union-attr]
        page.goto(url, timeout=CUSTODY_SCRAPE_TIMEOUT_SEC * 1000)

        if "/giris" in page.url:
            page.close()
            self._login()
            page = self._context.new_page()  # type: ignore[union-attr]
            page.goto(url, timeout=CUSTODY_SCRAPE_TIMEOUT_SEC * 1000)
            if "/giris" in page.url:
                page.close()
                raise LoginExpiredError(f"Login redirect persists for {ticker}")
        return page


# ---------------------------------------------------------------------------
# TakasPageParser — HTML ayrıştırıcı
# ---------------------------------------------------------------------------

class TakasPageParser:
    """Fintables takas sayfasını ayrıştırır (JS render sonrası DOM).

    VERIFY AGAINST LIVE SITE (open Q2): selector'lar canlı sayfada doğrulanmalı.
    Frontend deploy'ları kırabilir → mümkünse text/role tabanlı selector tercih et.
    """

    # VERIFY AGAINST LIVE SITE: gerçek DOM yapısına göre güncellenecek.
    TABLE_SELECTOR = "table.takas-table"
    SUMMARY_SELECTOR = "div.takas-summary-card"
    ROW_SELECTOR = "tbody tr"

    def parse_summary(self, page: "Page") -> CustodyDailySummary | None:
        """Özet kartından yabancı/kurumsal/bireysel % ve yatırımcı sayısı."""
        # VERIFY AGAINST LIVE SITE: özet kartının gerçek selector'ı/etiketleri.
        card = page.query_selector(self.SUMMARY_SELECTOR)
        if card is None:
            return None
        text = card.inner_text()

        def _grab(label: str) -> str | None:
            m = re.search(rf"{label}[^0-9%\-]*([0-9\.,]+)", text, re.IGNORECASE)
            return m.group(1) if m else None

        return CustodyDailySummary(
            date="",            # connector tarafından doldurulur
            ticker="",
            yabanci_toplam_pct=parse_tr_float(_grab("Yabancı")),
            kurumsal_pct=parse_tr_float(_grab("Kurumsal")),
            bireysel_pct=parse_tr_float(_grab("Bireysel")),
            toplam_yatirimci_sayisi=parse_tr_int(_grab("Yatırımcı")),
            scraped_at="",
        )

    def parse_institution_rows(
        self, page: "Page", ticker: str, date_str: str, scraped_at: str
    ) -> list[CustodySnapshot]:
        """Kurum tablosunu satır satır okur. Boş tablo → TickerNotFoundError."""
        # VERIFY AGAINST LIVE SITE: tablo + satır + hücre sırası.
        try:
            page.wait_for_selector(self.TABLE_SELECTOR, timeout=CUSTODY_SCRAPE_TIMEOUT_SEC * 1000)
        except Exception as exc:  # noqa: BLE001
            raise TickerNotFoundError(f"{ticker}: takas tablosu bulunamadı") from exc

        rows = page.query_selector_all(f"{self.TABLE_SELECTOR} {self.ROW_SELECTOR}")
        if not rows:
            raise TickerNotFoundError(f"{ticker}: boş takas tablosu")

        snapshots: list[CustodySnapshot] = []
        for r in rows:
            cells = [c.inner_text() for c in r.query_selector_all("td")]
            if len(cells) < 2:
                continue
            # VERIFY AGAINST LIVE SITE: hücre sırası
            # [kurum, lot, %, günlük Δ, haftalık Δ, aylık Δ, 3 aylık Δ]
            snapshots.append(
                CustodySnapshot(
                    date=date_str,
                    ticker=ticker,
                    kurum_adi=(cells[0] or "").strip(),
                    lot=parse_tr_int(cells[1]) if len(cells) > 1 else None,
                    pct=parse_tr_float(cells[2]) if len(cells) > 2 else None,
                    gunluk_delta=parse_tr_float(cells[3]) if len(cells) > 3 else None,
                    haftalik_delta=parse_tr_float(cells[4]) if len(cells) > 4 else None,
                    aylik_delta=parse_tr_float(cells[5]) if len(cells) > 5 else None,
                    ucaylik_delta=parse_tr_float(cells[6]) if len(cells) > 6 else None,
                    scraped_at=scraped_at,
                )
            )
        if not snapshots:
            raise TickerNotFoundError(f"{ticker}: ayrıştırılabilir kurum satırı yok")
        return snapshots


# ---------------------------------------------------------------------------
# FintablesScraperConnector — orchestrator
# ---------------------------------------------------------------------------

class FintablesScraperConnector:
    """FintablesClient + TakasPageParser + CustodyDBWriter birleşimi.

    BIST50 döngüsünü yönetir, rate limiting uygular, hataları loglar.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        session_file: str | Path | None = None,
        tickers: tuple[str, ...] | None = None,
    ) -> None:
        self.db_path = Path(db_path or CUSTODY_DB_PATH)
        self.session_file = Path(session_file or CUSTODY_SESSION_FILE)
        self.tickers = tickers or CUSTODY_BIST50_TICKERS
        self.writer = CustodyDBWriter(self.db_path)
        self.parser = TakasPageParser()

    def scrape_ticker(
        self,
        ticker: str,
        date_str: str,
        client: "FintablesClient",
    ) -> bool:
        """Tek ticker için sayfayı ayrıştır ve yaz.

        TickerNotFoundError → WARNING + False (sessiz skip).
        RateLimitError → exponential backoff (max CUSTODY_MAX_RETRIES).
        LoginExpiredError → yukarı fırlat (batch durur).
        Diğer exception → WARNING + False.
        """
        backoff = CUSTODY_RETRY_BACKOFF_SEC
        for attempt in range(1, CUSTODY_MAX_RETRIES + 1):
            try:
                page = client.get_page(ticker, date_str=date_str)
                try:
                    scraped_at = datetime.now(timezone.utc).isoformat()
                    snaps = self.parser.parse_institution_rows(
                        page, ticker, date_str, scraped_at
                    )
                    summary = self.parser.parse_summary(page)
                finally:
                    page.close()

                self.writer.upsert_snapshot(snaps)
                if summary is not None:
                    summary.date = date_str
                    summary.ticker = ticker
                    summary.scraped_at = scraped_at
                    self.writer.upsert_summary(summary)
                logger.info("Takas %s @ %s: %d kurum satırı yazıldı", ticker, date_str, len(snaps))
                return True

            except TickerNotFoundError as exc:
                logger.warning("Takas skip %s: %s", ticker, exc)
                return False
            except LoginExpiredError:
                raise
            except RateLimitError as exc:
                logger.warning(
                    "Takas %s rate-limit (deneme %d/%d): %s — %.0fs backoff",
                    ticker, attempt, CUSTODY_MAX_RETRIES, exc, backoff,
                )
                if attempt >= CUSTODY_MAX_RETRIES:
                    return False
                time.sleep(backoff)
                backoff *= 2
            except Exception as exc:  # noqa: BLE001 - graceful per-ticker skip
                logger.warning("Takas %s beklenmedik hata: %s", ticker, exc)
                return False
        return False

    def scrape_all(self, date_str: str | None = None) -> dict[str, bool]:
        """BIST50 döngüsü. date_str=None → Europe/Istanbul bugünü."""
        if date_str is None:
            date_str = datetime.now(_ISTANBUL).date().isoformat()

        results: dict[str, bool] = {}
        with FintablesClient(session_file=self.session_file) as client:
            for ticker in self.tickers:
                results[ticker] = self.scrape_ticker(ticker, date_str, client)
                time.sleep(CUSTODY_SCRAPE_RATE_LIMIT_SEC)
        ok = sum(1 for v in results.values() if v)
        logger.info("Takas scrape_all: %d/%d başarılı (%s)", ok, len(results), date_str)
        return results

    def backfill(self, days: int | None = None, force: bool = False) -> None:
        """İlk çalışma backfill: CUSTODY_BACKFILL_DAYS geriye git.

        VERIFY AGAINST LIVE SITE (open Q1): Senaryo A (?date= URL) destekleniyorsa
        gün gün döngü; desteklenmiyorsa parser tarihsel tab'ı tek seferde çekmeli.
        """
        days = days or CUSTODY_BACKFILL_DAYS
        today = datetime.now(_ISTANBUL).date()
        start = today - timedelta(days=days)

        with FintablesClient(session_file=self.session_file) as client:
            for ticker in self.tickers:
                latest = self.writer.get_latest_date(ticker)
                if not force and latest and latest >= start.isoformat():
                    logger.debug("Backfill skip %s: zaten %s itibaren veri var", ticker, latest)
                    continue

                current = start
                while current <= today:
                    try:
                        self.scrape_ticker(ticker, current.isoformat(), client)
                    except TickerNotFoundError:
                        break  # ticker listede değil, tüm tarihleri atla
                    time.sleep(CUSTODY_SCRAPE_RATE_LIMIT_SEC)
                    current += timedelta(days=1)
                time.sleep(CUSTODY_SCRAPE_RATE_LIMIT_SEC * 2)

"""İş Yatırım foreign-flow bridge (D-126, SPEC_FOREIGN_FLOW_ISYATIRIM_1, §17).

MKK/Fintables custody yolu abonelik duvarına takıldığı için (D-116), yabancı
saklama oranı sinyali İş Yatırım üzerinden köprülenir. Doğrudan foreign-flow
endpoint'i (arastirma / _layouts/Data.aspx) robots.txt ile YASAKLI + 401 + ToS
gri zon olduğundan (Q-4 eskalasyonu) KULLANILMAZ. Bunun yerine ZATEN entegre,
robots-güvenli `IsYatirimScreenerConnector` (getScreenerDataNEW, login yok)
kullanılır.

Akış:
    IsYatirimScreenerConnector.fetch_all_tickers()  →  {sym: {foreign_ratio, ...}}
    ForeignFlowConnector.fetch_and_store()          →  isyatirim.db (günlük snapshot)
    SmartMoneyL5.compute_l5_score(foreign_flow_db_path=...)  →  change_30d/level/persistence

isyatirim.db şeması custody DB'nin ikizidir (date, ticker, yabanci_toplam_pct,
scraped_at) — böylece L5'te `_compute_from_custody` aynen yeniden kullanılır.

Gün-1 sentetik seed: bir ticker'ın geçmişi yoksa ilk yazımda İKİ satır eklenir
(bugün + bugün-30g); 30g-önce değeri = foreign_ratio - change_1m_pp. Bu sayede
change_30d_score ilk günden çalışır; gerçek günlük snapshot'lar biriktikçe
sentetik nokta 30g penceresinden doğal olarak çıkar.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.signals.thresholds import (
    FOREIGN_FLOW_CHANGE_UNIT_DIVISOR,
    FOREIGN_FLOW_DB_PATH,
    FOREIGN_FLOW_STALE_HOURS,
)

logger = logging.getLogger(__name__)

_ISTANBUL = ZoneInfo("Europe/Istanbul")
_SEED_LOOKBACK_DAYS = 30  # sentetik "30g-önce" noktası


@dataclass
class ForeignFlowSummary:
    """Tek hisse-gün satırı (foreign_flow_summary tablosuna karşılık gelir)."""
    date: str          # YYYY-MM-DD
    ticker: str
    yabanci_toplam_pct: float | None
    scraped_at: str    # ISO UTC


# ---------------------------------------------------------------------------
# ForeignFlowDBWriter — SQLite (custody şemasının ikizi, network'süz test edilebilir)
# ---------------------------------------------------------------------------

class ForeignFlowDBWriter:
    """SQLite yazar. DB yoksa __init__ içinde şema oluşturulur (idempotent).

    CustodyDBWriter API'sini aynalar; tablo `foreign_flow_summary`.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS foreign_flow_summary (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    date               TEXT    NOT NULL,
                    ticker             TEXT    NOT NULL,
                    yabanci_toplam_pct REAL,
                    scraped_at         TEXT    NOT NULL,
                    UNIQUE(date, ticker)
                );

                CREATE INDEX IF NOT EXISTS idx_ff_ticker_date
                    ON foreign_flow_summary(ticker, date);
                CREATE INDEX IF NOT EXISTS idx_ff_date_ticker
                    ON foreign_flow_summary(date, ticker);
                """
            )
            con.commit()
        finally:
            con.close()

    def upsert_summary(self, rows: list[ForeignFlowSummary]) -> int:
        """INSERT OR REPLACE satırlar. Döner: yazılan satır sayısı."""
        if not rows:
            return 0
        con = self._connect()
        try:
            con.executemany(
                """
                INSERT OR REPLACE INTO foreign_flow_summary
                    (date, ticker, yabanci_toplam_pct, scraped_at)
                VALUES (?, ?, ?, ?)
                """,
                [(r.date, r.ticker, r.yabanci_toplam_pct, r.scraped_at) for r in rows],
            )
            con.commit()
        finally:
            con.close()
        return len(rows)

    def get_history(self, ticker: str, days: int = 252) -> pd.DataFrame:
        """(date, ticker, yabanci_toplam_pct) — date artan sıralı.

        Stale check: en son scraped_at > FOREIGN_FLOW_STALE_HOURS ise boş DF.
        """
        con = self._connect()
        try:
            df = pd.read_sql_query(
                """
                SELECT date, ticker, yabanci_toplam_pct, scraped_at
                FROM foreign_flow_summary
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
            if age > timedelta(hours=FOREIGN_FLOW_STALE_HOURS):
                logger.warning(
                    "ForeignFlowDBWriter.get_history %s: stale (%.1fh > %dh) → empty",
                    ticker, age.total_seconds() / 3600, FOREIGN_FLOW_STALE_HOURS,
                )
                return empty
        except (TypeError, ValueError):
            pass

        out = df[["date", "ticker", "yabanci_toplam_pct"]].tail(days)
        return out.reset_index(drop=True)

    def get_latest_date(self, ticker: str) -> str | None:
        """En son date (YYYY-MM-DD) veya None (geçmiş yok → seed tetikleyici)."""
        con = self._connect()
        try:
            cur = con.execute(
                "SELECT MAX(date) FROM foreign_flow_summary WHERE ticker = ?",
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
                FROM foreign_flow_summary
                GROUP BY ticker ORDER BY ticker
                """
            )
            rows = cur.fetchall()
        finally:
            con.close()
        return {t: int(n) for t, n in rows}


# ---------------------------------------------------------------------------
# ForeignFlowConnector — screener → DB orchestrator
# ---------------------------------------------------------------------------

class ForeignFlowConnector:
    """IsYatirimScreenerConnector + ForeignFlowDBWriter köprüsü.

    `connector` enjekte edilebilir (test için mock); verilmezse gerçek
    `IsYatirimScreenerConnector` lazy import edilir (requests bağımlılığı orada).
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        connector=None,
        tickers: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.db_path = Path(db_path or FOREIGN_FLOW_DB_PATH)
        self.writer = ForeignFlowDBWriter(self.db_path)
        self.tickers = tuple(tickers) if tickers else None  # None → screener'ın tüm ticker'ları
        self._connector = connector  # None → fetch_and_store içinde lazy oluşturulur

    def _get_connector(self):
        if self._connector is None:
            # Lazy: requests yalnızca gerçek connector kullanılırken gerekli
            from src.signals.layers.connectors.smart_money_connector import (
                IsYatirimScreenerConnector,
            )
            self._connector = IsYatirimScreenerConnector()
        return self._connector

    def fetch_and_store(self, date_str: str | None = None) -> dict[str, bool]:
        """Screener'dan çek, istenen ticker'lar için bugünün snapshot'ını yaz.

        Geçmişi olmayan ticker → gün-1 sentetik seed (bugün + bugün-30g).
        Döner: {ticker: yazıldı_mı}. Screener boş/soft-block → ALERT + {} (raise yok).
        """
        if date_str is None:
            date_str = datetime.now(_ISTANBUL).date().isoformat()

        data = self._get_connector().fetch_all_tickers()
        if not data:
            logger.error(
                "ALERT ForeignFlowConnector.fetch_and_store: screener boş döndü "
                "(soft-block veya network) — %s için veri yazılmadı.", date_str,
            )
            return {}

        targets = self.tickers if self.tickers is not None else tuple(data.keys())
        scraped_at = datetime.now(timezone.utc).isoformat()
        try:
            today = date.fromisoformat(date_str)
        except ValueError:
            today = datetime.now(_ISTANBUL).date()
        seed_date = (today - timedelta(days=_SEED_LOOKBACK_DAYS)).isoformat()

        results: dict[str, bool] = {}
        for ticker in targets:
            vals = data.get(ticker)
            if vals is None:
                results[ticker] = False
                continue

            foreign_ratio = vals.get("foreign_ratio")
            if foreign_ratio is None:
                results[ticker] = False
                continue

            rows = [ForeignFlowSummary(date_str, ticker, float(foreign_ratio), scraped_at)]

            # Gün-1 seed: geçmiş yoksa sentetik 30g-önce noktası
            if self.writer.get_latest_date(ticker) is None:
                change_pp = float(vals.get("change_1m_bps") or 0.0) / FOREIGN_FLOW_CHANGE_UNIT_DIVISOR
                seed_value = float(foreign_ratio) - change_pp
                rows.append(ForeignFlowSummary(seed_date, ticker, seed_value, scraped_at))

            self.writer.upsert_summary(rows)
            results[ticker] = True

        ok = sum(1 for v in results.values() if v)
        logger.info(
            "ForeignFlowConnector.fetch_and_store: %d/%d ticker yazıldı (%s)",
            ok, len(results), date_str,
        )
        return results

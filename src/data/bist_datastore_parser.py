"""BIST Datastore aylik yabanci islem .xls parser (D-129).

BIST Datastore "Foreign Investor Transactions" aylik .xls dosyalarini
ayristirir. Sonuclari data/bist_datastore/foreign_monthly.db icine yazar.
L5 (smart_money_layer) son aylarin net_usd trendini fallback tier olarak kullanir.

Tasarim:
- IO (_read_xls) saf transform'dan (_transform) ayrildigi icin testler .xls IO'suz
  sentetik DataFrame ile calisir. .xls okuma engine='xlrd' (xlrd 2.0 .xls okur).
- year/month XLS header hucresinden cikarilir (_extract_period): ilk satirlarda
  TR ay adi + 4 haneli yil aranir.
- skiprows YOK: satirlar Pay kolonunun ticker.E regex'i ile filtrelenir; header,
  donem ve pazar-grup (Yildiz/Ana/Alt Pazar) satirlari dogal olarak elenir.

VERIFY (gercek .xls ile): header period hucresi yeri/format, 8 kolonun pozisyonu,
sheet adi "TURKCE". Ornek dosya repo'da yok; canli dogrulama execution'da.
"""
from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.signals.thresholds import FOREIGN_MONTHLY_DB_PATH

logger = logging.getLogger(__name__)

SHEET_NAME = "TURKCE"

# Kolon pozisyonlari (verified format; VERIFY canli .xls ile)
_COL_PAY = 0
_COL_ALIS_USD = 4
_COL_SATIS_USD = 7

_TICKER_RE = re.compile(r"^([A-Z0-9]+)\.E$")

_TR_MONTHS: dict[str, int] = {
    "ocak": 1, "subat": 2, "şubat": 2, "mart": 3, "nisan": 4,
    "mayis": 5, "mayıs": 5, "haziran": 6, "temmuz": 7,
    "agustos": 8, "ağustos": 8, "eylul": 9, "eylül": 9,
    "ekim": 10, "kasim": 11, "kasım": 11, "aralik": 12, "aralık": 12,
}
_MONTH_ALT = "|".join(sorted(_TR_MONTHS.keys(), key=len, reverse=True))
_PERIOD_RE = re.compile(rf"({_MONTH_ALT})\s+(\d{{4}})", re.IGNORECASE)


def _to_usd_float(val) -> float | None:
    """Numeric ya da TR-format ('1.234.567,89') -> float. Ayristirilamazsa None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        return None if pd.isna(f) else f
    s = str(val).strip()
    if not s:
        return None
    cleaned = re.sub(r"[^0-9,\.\-]", "", s)
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


@dataclass
class ForeignMonthlyRow:
    year: int
    month: int
    ticker: str
    alis_usd: float | None
    satis_usd: float | None
    net_usd: float | None


# ---------------------------------------------------------------------------
# Pure transform helpers (network/IO yok, tam test edilebilir)
# ---------------------------------------------------------------------------

def _extract_period(raw_df: pd.DataFrame, max_rows: int = 6) -> tuple[int, int]:
    """Ilk max_rows satirin string hucrelerinde TR ay + yil ara -> (year, month).

    Bulunamazsa ValueError.
    """
    head = raw_df.head(max_rows)
    for _, row in head.iterrows():
        for cell in row:
            if not isinstance(cell, str):
                continue
            m = _PERIOD_RE.search(cell)
            if m:
                month = _TR_MONTHS[m.group(1).lower()]
                year = int(m.group(2))
                return year, month
    raise ValueError("XLS header'da donem (TR ay + yil) bulunamadi")


def _transform(raw_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Ham (header=None) DataFrame -> [ticker, year, month, alis_usd, satis_usd, net_usd].

    Pay kolonu ticker.E formatinda olan satirlar tutulur; header/donem/pazar-grup
    satirlari elenir. .E suffix strip edilir.
    """
    rows: list[ForeignMonthlyRow] = []
    for _, r in raw_df.iterrows():
        pay = r.iloc[_COL_PAY] if len(r) > _COL_PAY else None
        if not isinstance(pay, str):
            continue
        m = _TICKER_RE.match(pay.strip())
        if not m:
            continue  # header / pazar grup / non-ticker satir
        ticker = m.group(1)
        alis = _to_usd_float(r.iloc[_COL_ALIS_USD]) if len(r) > _COL_ALIS_USD else None
        satis = _to_usd_float(r.iloc[_COL_SATIS_USD]) if len(r) > _COL_SATIS_USD else None
        net = None
        if alis is not None and satis is not None:
            net = alis - satis
        rows.append(ForeignMonthlyRow(year, month, ticker, alis, satis, net))

    return pd.DataFrame(
        [
            {
                "ticker": x.ticker, "year": x.year, "month": x.month,
                "alis_usd": x.alis_usd, "satis_usd": x.satis_usd, "net_usd": x.net_usd,
            }
            for x in rows
        ],
        columns=["ticker", "year", "month", "alis_usd", "satis_usd", "net_usd"],
    )


def _read_xls(xls_path: str | Path) -> pd.DataFrame:
    """TURKCE sheet'i ham (header=None) oku. IO siniri."""
    return pd.read_excel(xls_path, sheet_name=SHEET_NAME, header=None, engine="xlrd")


def parse_foreign_monthly(xls_path: str | Path) -> pd.DataFrame:
    """xls -> [ticker, year, month, alis_usd, satis_usd, net_usd]."""
    raw = _read_xls(xls_path)
    year, month = _extract_period(raw)
    return _transform(raw, year, month)


# ---------------------------------------------------------------------------
# ForeignMonthlyDBWriter — SQLite (network'suz, tam test edilebilir)
# ---------------------------------------------------------------------------

class ForeignMonthlyDBWriter:
    """SQLite yazar. DB yoksa __init__ icinde sema olusturulur (idempotent)."""

    def __init__(self, db_path: str | Path = FOREIGN_MONTHLY_DB_PATH) -> None:
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
                CREATE TABLE IF NOT EXISTS foreign_monthly (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    year       INTEGER NOT NULL,
                    month      INTEGER NOT NULL,
                    ticker     TEXT    NOT NULL,
                    alis_usd   REAL,
                    satis_usd  REAL,
                    net_usd    REAL,
                    loaded_at  TEXT    NOT NULL,
                    UNIQUE(year, month, ticker)
                );
                CREATE INDEX IF NOT EXISTS idx_fm_ticker_period
                    ON foreign_monthly(ticker, year, month);
                """
            )
            con.commit()
        finally:
            con.close()

    def upsert(self, df: pd.DataFrame) -> int:
        """INSERT OR REPLACE DataFrame satirlari. Doner: yazilan satir sayisi."""
        if df is None or df.empty:
            return 0
        loaded_at = datetime.now(timezone.utc).isoformat()
        payload = [
            (
                int(row["year"]), int(row["month"]), str(row["ticker"]),
                row.get("alis_usd"), row.get("satis_usd"), row.get("net_usd"),
                loaded_at,
            )
            for _, row in df.iterrows()
        ]
        con = self._connect()
        try:
            con.executemany(
                """
                INSERT OR REPLACE INTO foreign_monthly
                    (year, month, ticker, alis_usd, satis_usd, net_usd, loaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            con.commit()
        finally:
            con.close()
        return len(payload)

    def get_net_history(self, ticker: str, months: int = 3) -> list[float]:
        """Son `months` ayin net_usd'si, (year, month) artan sirali. None'lar atlanir."""
        con = self._connect()
        try:
            cur = con.execute(
                """
                SELECT net_usd FROM foreign_monthly
                WHERE ticker = ? AND net_usd IS NOT NULL
                ORDER BY year ASC, month ASC
                """,
                (ticker,),
            )
            vals = [float(r[0]) for r in cur.fetchall()]
        finally:
            con.close()
        return vals[-months:]

    def ticker_counts(self) -> dict[str, int]:
        """--check icin: ticker basina distinct ay sayisi."""
        con = self._connect()
        try:
            cur = con.execute(
                """
                SELECT ticker, COUNT(*) AS n FROM foreign_monthly
                GROUP BY ticker ORDER BY ticker
                """
            )
            rows = cur.fetchall()
        finally:
            con.close()
        return {t: int(n) for t, n in rows}

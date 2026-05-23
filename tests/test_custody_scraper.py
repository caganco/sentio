"""Tests for D-116 Fintables Takas Scraper (SPEC_FINTABLES_TAKAS_SCRAPER_1).

Tüm testler temp SQLite + sentetik veri kullanır — canlı Fintables sitesi
GEREKMEZ. playwright kurulu olmadan çalışır (lazy import sözleşmesi).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.data.fintables_scraper import (
    CustodyDailySummary,
    CustodyDBWriter,
    CustodySnapshot,
    FintablesScraperConnector,
    TickerNotFoundError,
    parse_tr_float,
    parse_tr_int,
)
from src.signals.layers.smart_money_layer import SmartMoneyL5
from src.signals.thresholds import CUSTODY_MIN_HISTORY_DAYS, CUSTODY_STALE_HOURS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh(hours_ago: float = 0.0) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _make_custody_db(
    tmp_path: Path,
    ticker: str = "AKSEN",
    n_days: int = 20,
    start_pct: float = 30.0,
    delta: float = 0.2,
    scraped_offset_hours: float = 0.0,
    db_name: str = "custody_snapshots.db",
) -> tuple[Path, CustodyDBWriter]:
    """Sentetik custody_daily_summary verisi yaz, (db_path, writer) döndür."""
    db_path = tmp_path / db_name
    writer = CustodyDBWriter(db_path)
    scraped_at = _fresh(scraped_offset_hours)
    for i in range(n_days):
        day = (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d")
        writer.upsert_summary(
            CustodyDailySummary(
                date=day,
                ticker=ticker,
                yabanci_toplam_pct=start_pct + i * delta,
                kurumsal_pct=None,
                bireysel_pct=None,
                toplam_yatirimci_sayisi=None,
                scraped_at=scraped_at,
            )
        )
    return db_path, writer


def _make_parquet(tmp_path: Path, symbol: str = "AKBNK", n_days: int = 20) -> Path:
    """Minimal screener parquet (parquet fallback testi için)."""
    p = tmp_path / "daily_screener.parquet"
    written_at = _fresh(0.0)
    rows = [
        {
            "date": (datetime(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d"),
            "symbol": symbol,
            "foreign_ratio": 30.0 + i * 0.1,
            "change_1w_bps": 0.0,
            "change_1m_bps": 0.0,
            "volume_3m_mn_usd": 100.0,
            "written_at": written_at,
        }
        for i in range(n_days)
    ]
    pd.DataFrame(rows).to_parquet(p, index=False)
    return p


# ---------------------------------------------------------------------------
# TR number parsing (pure helpers)
# ---------------------------------------------------------------------------

def test_parse_tr_float_and_int():
    assert parse_tr_float("1.234,56") == 1234.56
    assert parse_tr_float("%12,3") == 12.3
    assert parse_tr_float("-0,5") == -0.5
    assert parse_tr_float(None) is None
    assert parse_tr_float("-") is None
    assert parse_tr_int("1.234.567") == 1234567


# ---------------------------------------------------------------------------
# CustodyDBWriter — schema & upsert
# ---------------------------------------------------------------------------

def test_custody_schema_init(tmp_path):
    """DB oluşur; tablolar ve indexler sqlite_master'da var."""
    db_path = tmp_path / "c.db"
    CustodyDBWriter(db_path)
    assert db_path.exists()

    con = sqlite3.connect(str(db_path))
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    con.close()
    assert {"custody_snapshots", "custody_daily_summary"} <= names
    assert {
        "idx_snapshots_date_ticker",
        "idx_summary_ticker_date",
        "idx_summary_date_ticker",
    } <= names


def test_custody_snapshot_upsert_idempotent(tmp_path):
    """Aynı (date, ticker, kurum_adi) iki kez → 1 satır."""
    writer = CustodyDBWriter(tmp_path / "c.db")
    snap = CustodySnapshot(
        date="2026-05-20", ticker="AKSEN", kurum_adi="İş Yatırım",
        lot=1000, pct=12.3, gunluk_delta=0.1, haftalik_delta=0.2,
        aylik_delta=0.3, ucaylik_delta=0.4, scraped_at=_fresh(),
    )
    writer.upsert_snapshot([snap])
    writer.upsert_snapshot([snap])

    con = sqlite3.connect(str(tmp_path / "c.db"))
    n = con.execute("SELECT COUNT(*) FROM custody_snapshots").fetchone()[0]
    con.close()
    assert n == 1


def test_custody_summary_upsert_idempotent(tmp_path):
    """Aynı (date, ticker) iki kez → 1 satır, pct güncellenir."""
    writer = CustodyDBWriter(tmp_path / "c.db")
    base = dict(
        date="2026-05-20", ticker="AKSEN", kurumsal_pct=None,
        bireysel_pct=None, toplam_yatirimci_sayisi=None, scraped_at=_fresh(),
    )
    writer.upsert_summary(CustodyDailySummary(yabanci_toplam_pct=40.0, **base))
    writer.upsert_summary(CustodyDailySummary(yabanci_toplam_pct=45.5, **base))

    con = sqlite3.connect(str(tmp_path / "c.db"))
    rows = con.execute(
        "SELECT yabanci_toplam_pct FROM custody_daily_summary"
    ).fetchall()
    con.close()
    assert len(rows) == 1
    assert rows[0][0] == 45.5


def test_custody_get_history_returns_sorted_df(tmp_path):
    """3 farklı tarih → get_history date'e göre artan sıralı DF."""
    db_path, writer = _make_custody_db(tmp_path, n_days=3, start_pct=10.0, delta=5.0)
    df = writer.get_history("AKSEN")
    assert list(df["date"]) == sorted(df["date"])
    assert len(df) == 3
    assert df["yabanci_toplam_pct"].iloc[0] == 10.0


def test_custody_get_history_stale_returns_empty(tmp_path):
    """scraped_at 72h önce → get_history boş DF."""
    db_path, writer = _make_custody_db(
        tmp_path, n_days=3, scraped_offset_hours=CUSTODY_STALE_HOURS + 24
    )
    df = writer.get_history("AKSEN")
    assert df.empty


def test_custody_get_latest_date(tmp_path):
    """get_latest_date en son date'i döner."""
    db_path, writer = _make_custody_db(tmp_path, n_days=5)
    # 2026-01-01 + 4 gün = 2026-01-05
    assert writer.get_latest_date("AKSEN") == "2026-01-05"
    assert writer.get_latest_date("YOKKK") is None


# ---------------------------------------------------------------------------
# SmartMoneyL5 — custody history loader
# ---------------------------------------------------------------------------

def test_l5_load_custody_history_missing_file(tmp_path):
    """custody_db_path yok → None, exception yok."""
    layer = SmartMoneyL5()
    assert layer._load_custody_history("AKSEN", tmp_path / "yok.db") is None


def test_l5_load_custody_history_insufficient_days(tmp_path):
    """< CUSTODY_MIN_HISTORY_DAYS gün → None."""
    db_path, _ = _make_custody_db(tmp_path, n_days=CUSTODY_MIN_HISTORY_DAYS - 1)
    layer = SmartMoneyL5()
    assert layer._load_custody_history("AKSEN", db_path) is None


def test_l5_load_custody_history_stale_returns_none(tmp_path):
    """Son scraped_at > CUSTODY_STALE_HOURS → None (parquet fallback)."""
    db_path, _ = _make_custody_db(
        tmp_path, n_days=20, scraped_offset_hours=CUSTODY_STALE_HOURS + 1
    )
    layer = SmartMoneyL5()
    assert layer._load_custody_history("AKSEN", db_path) is None


# ---------------------------------------------------------------------------
# SmartMoneyL5 — compute_l5_score routing
# ---------------------------------------------------------------------------

def test_l5_compute_l5_score_uses_custody_when_available(tmp_path):
    """Custody DB taze + yeterli → custody'den skor; parquet okunmaz."""
    db_path, _ = _make_custody_db(tmp_path, ticker="AKSEN", n_days=25)
    layer = SmartMoneyL5()
    # parquet_path bilinçli olarak yok bir dosya: custody kullanılırsa skor gelir,
    # parquet'e düşülürse None olurdu (dosya yok).
    result = layer.compute_l5_score(
        "AKSEN",
        parquet_path=tmp_path / "nonexistent.parquet",
        custody_db_path=db_path,
    )
    assert result is not None
    assert 0.0 <= result <= 100.0


def test_l5_parquet_fallback_when_custody_db_path_none(tmp_path):
    """custody_db_path=None → eski parquet path davranışı (backward compat)."""
    p = _make_parquet(tmp_path, symbol="AKBNK", n_days=20)
    layer = SmartMoneyL5()
    result = layer.compute_l5_score("AKBNK", parquet_path=p, custody_db_path=None)
    assert result is not None
    assert 0.0 <= result <= 100.0


def test_l5_custody_empty_falls_back_to_parquet(tmp_path):
    """Custody DB var ama symbol kaydı yok → parquet fallback çalışır."""
    db_path, _ = _make_custody_db(tmp_path, ticker="AKSEN", n_days=20)
    p = _make_parquet(tmp_path, symbol="AKBNK", n_days=20)
    layer = SmartMoneyL5()
    # AKBNK custody'de yok → custody None → parquet'ten okur
    result = layer.compute_l5_score("AKBNK", parquet_path=p, custody_db_path=db_path)
    assert result is not None


# ---------------------------------------------------------------------------
# Custody sub-score math
# ---------------------------------------------------------------------------

def test_compute_persistence_score_buying_streak():
    """7 gün ard arda artış → > 80."""
    layer = SmartMoneyL5()
    s = pd.Series([10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5])
    assert layer.compute_persistence_score(s) > 80


def test_compute_persistence_score_selling_streak():
    """7 gün ard arda azalış → < 20."""
    layer = SmartMoneyL5()
    s = pd.Series([20, 19, 18, 17, 16, 15, 14, 13])
    assert layer.compute_persistence_score(s) < 20


def test_compute_30d_change_score():
    """+5pp → ~75, -5pp → ~25, 0 → 50."""
    layer = SmartMoneyL5()
    assert layer.compute_30d_change_score(pd.Series([10.0, 15.0])) == pytest.approx(75.0)
    assert layer.compute_30d_change_score(pd.Series([15.0, 10.0])) == pytest.approx(25.0)
    assert layer.compute_30d_change_score(pd.Series([12.0, 12.0])) == pytest.approx(50.0)


def test_compute_level_score_extremes():
    """Tarihin en yükseği → ~100, en düşüğü → ~0."""
    layer = SmartMoneyL5()
    assert layer.compute_level_score(pd.Series(list(range(30)))) > 90      # current = max
    assert layer.compute_level_score(pd.Series(list(range(30, 0, -1)))) < 10  # current = min


# ---------------------------------------------------------------------------
# Connector wiring (playwright'sız — DB tarafı)
# ---------------------------------------------------------------------------

def test_connector_init_creates_db(tmp_path):
    """FintablesScraperConnector __init__ → DB + writer hazır (playwright gerekmez)."""
    db_path = tmp_path / "custody_snapshots.db"
    conn = FintablesScraperConnector(db_path=db_path, tickers=("AKSEN", "THYAO"))
    assert db_path.exists()
    assert conn.tickers == ("AKSEN", "THYAO")
    assert isinstance(conn.writer, CustodyDBWriter)

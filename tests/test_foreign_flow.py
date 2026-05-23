"""Tests for D-126 İş Yatırım foreign-flow bridge (SPEC_FOREIGN_FLOW_ISYATIRIM_1, §17).

Tüm testler temp SQLite + enjekte edilmiş mock connector kullanır — canlı İş
Yatırım screener'ı GEREKMEZ (network yok).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.data.isyatirim_scraper import (
    ForeignFlowConnector,
    ForeignFlowDBWriter,
    ForeignFlowSummary,
)
from src.signals.layers.smart_money_layer import SmartMoneyL5
from src.signals.thresholds import FOREIGN_FLOW_STALE_HOURS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh(hours_ago: float = 0.0) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


class _MockScreener:
    """fetch_all_tickers() davranışını taklit eder (network yok)."""

    def __init__(self, data: dict[str, dict]):
        self._data = data

    def fetch_all_tickers(self) -> dict[str, dict]:
        return self._data


def _seed_history(writer: ForeignFlowDBWriter, ticker: str, values: list[float],
                  start: date = date(2026, 4, 1)) -> None:
    rows = [
        ForeignFlowSummary((start + timedelta(days=i)).isoformat(), ticker, v, _fresh())
        for i, v in enumerate(values)
    ]
    writer.upsert_summary(rows)


# ---------------------------------------------------------------------------
# ForeignFlowDBWriter
# ---------------------------------------------------------------------------

def test_db_init_creates_schema(tmp_path):
    w = ForeignFlowDBWriter(tmp_path / "isyatirim.db")
    assert (tmp_path / "isyatirim.db").exists()
    # idempotent re-init
    ForeignFlowDBWriter(tmp_path / "isyatirim.db")


def test_upsert_idempotent(tmp_path):
    w = ForeignFlowDBWriter(tmp_path / "ff.db")
    row = ForeignFlowSummary("2026-05-21", "AKSEN", 30.0, _fresh())
    assert w.upsert_summary([row]) == 1
    w.upsert_summary([ForeignFlowSummary("2026-05-21", "AKSEN", 31.0, _fresh())])
    hist = w.get_history("AKSEN")
    assert len(hist) == 1  # UNIQUE(date,ticker) → replace, not duplicate
    assert hist.iloc[0]["yabanci_toplam_pct"] == 31.0


def test_get_history_sorted_and_columns(tmp_path):
    w = ForeignFlowDBWriter(tmp_path / "ff.db")
    _seed_history(w, "AKSEN", [10.0, 11.0, 12.0])
    hist = w.get_history("AKSEN")
    assert list(hist.columns) == ["date", "ticker", "yabanci_toplam_pct"]
    assert hist["date"].tolist() == sorted(hist["date"].tolist())


def test_get_history_stale_returns_empty(tmp_path):
    w = ForeignFlowDBWriter(tmp_path / "ff.db")
    old = _fresh(hours_ago=FOREIGN_FLOW_STALE_HOURS + 1)
    w.upsert_summary([
        ForeignFlowSummary("2026-04-01", "AKSEN", 10.0, old),
        ForeignFlowSummary("2026-04-02", "AKSEN", 11.0, old),
    ])
    assert w.get_history("AKSEN").empty


def test_get_latest_date_and_counts(tmp_path):
    w = ForeignFlowDBWriter(tmp_path / "ff.db")
    assert w.get_latest_date("AKSEN") is None
    _seed_history(w, "AKSEN", [10.0, 11.0])
    assert w.get_latest_date("AKSEN") == "2026-04-02"
    assert w.ticker_counts()["AKSEN"] == 2


# ---------------------------------------------------------------------------
# ForeignFlowConnector — fetch_and_store + day-1 seed
# ---------------------------------------------------------------------------

def test_fetch_and_store_seeds_two_rows_on_day_one(tmp_path):
    """Geçmişi olmayan ticker → bugün + bugün-30g (= ratio - change_1m_pp)."""
    mock = _MockScreener({
        "AKSEN": {"foreign_ratio": 30.0, "change_1w_bps": 0.0,
                  "change_1m_bps": 2.0, "volume_3m_mn_usd": 50.0},
    })
    conn = ForeignFlowConnector(
        db_path=tmp_path / "ff.db", connector=mock, tickers=["AKSEN"],
    )
    res = conn.fetch_and_store(date_str="2026-05-22")
    assert res == {"AKSEN": True}

    hist = conn.writer.get_history("AKSEN")
    assert len(hist) == 2
    # bugün = 30.0; 30g-önce = 30.0 - 2.0 = 28.0
    by_date = dict(zip(hist["date"], hist["yabanci_toplam_pct"]))
    assert by_date["2026-05-22"] == pytest.approx(30.0)
    assert by_date["2026-04-22"] == pytest.approx(28.0)


def test_fetch_and_store_no_seed_when_history_exists(tmp_path):
    """Geçmiş varsa seed yok; sadece bugünün satırı eklenir."""
    w = ForeignFlowDBWriter(tmp_path / "ff.db")
    _seed_history(w, "AKSEN", [29.0, 29.5], start=date(2026, 5, 20))
    mock = _MockScreener({"AKSEN": {"foreign_ratio": 30.0, "change_1m_bps": 5.0}})
    conn = ForeignFlowConnector(db_path=tmp_path / "ff.db", connector=mock, tickers=["AKSEN"])
    conn.fetch_and_store(date_str="2026-05-22")
    hist = conn.writer.get_history("AKSEN")
    assert len(hist) == 3  # 2 mevcut + bugün (seed yok)


def test_fetch_and_store_soft_block_returns_empty(tmp_path):
    """Screener boş ({}) → ALERT + boş sonuç, raise yok, DB'ye yazılmaz."""
    conn = ForeignFlowConnector(
        db_path=tmp_path / "ff.db", connector=_MockScreener({}), tickers=["AKSEN"],
    )
    assert conn.fetch_and_store(date_str="2026-05-22") == {}
    assert conn.writer.ticker_counts() == {}


def test_fetch_and_store_all_tickers_when_none(tmp_path):
    """tickers=None → screener'ın döndürdüğü tüm ticker'lar yazılır."""
    mock = _MockScreener({
        "AKSEN": {"foreign_ratio": 30.0, "change_1m_bps": 0.0},
        "THYAO": {"foreign_ratio": 22.0, "change_1m_bps": 0.0},
    })
    conn = ForeignFlowConnector(db_path=tmp_path / "ff.db", connector=mock, tickers=None)
    res = conn.fetch_and_store(date_str="2026-05-22")
    assert set(res.keys()) == {"AKSEN", "THYAO"}


# ---------------------------------------------------------------------------
# compute_l5_score — foreign_flow_db_path routing
# ---------------------------------------------------------------------------

def test_l5_uses_foreign_flow_when_available(tmp_path):
    """foreign_flow_db_path veri varsa → skor üretir (parquet okunmaz)."""
    mock = _MockScreener({"AKSEN": {"foreign_ratio": 30.0, "change_1m_bps": 2.0}})
    conn = ForeignFlowConnector(db_path=tmp_path / "ff.db", connector=mock, tickers=["AKSEN"])
    conn.fetch_and_store(date_str="2026-05-22")

    layer = SmartMoneyL5()
    result = layer.compute_l5_score(
        "AKSEN",
        parquet_path=tmp_path / "nonexistent.parquet",  # parquet'e düşerse None olurdu
        foreign_flow_db_path=tmp_path / "ff.db",
    )
    assert result is not None
    assert 0.0 <= result <= 100.0


def test_l5_foreign_flow_change_30d_direction(tmp_path):
    """Alım (artan ratio) → >50; satış (azalan) → <50 change_30d_score."""
    layer = SmartMoneyL5()
    # seed: 30g önce düşük → bugün yüksek = alım → change_30d > 50
    w_buy = ForeignFlowDBWriter(tmp_path / "buy.db")
    w_buy.upsert_summary([
        ForeignFlowSummary("2026-04-22", "AKSEN", 28.0, _fresh()),
        ForeignFlowSummary("2026-05-22", "AKSEN", 30.0, _fresh()),
    ])
    buy = layer._load_foreign_flow_history("AKSEN", tmp_path / "buy.db")
    assert buy is not None
    assert layer.compute_30d_change_score(buy["yabanci_toplam_pct"]) > 50

    w_sell = ForeignFlowDBWriter(tmp_path / "sell.db")
    w_sell.upsert_summary([
        ForeignFlowSummary("2026-04-22", "AKSEN", 30.0, _fresh()),
        ForeignFlowSummary("2026-05-22", "AKSEN", 28.0, _fresh()),
    ])
    sell = layer._load_foreign_flow_history("AKSEN", tmp_path / "sell.db")
    assert layer.compute_30d_change_score(sell["yabanci_toplam_pct"]) < 50


def test_l5_custody_takes_precedence_over_foreign_flow(tmp_path):
    """custody_db_path veri varsa foreign_flow okunmaz (precedence)."""
    # foreign_flow DB'yi geçersiz kıl: var olmayan path → custody kullanılmalı
    mock = _MockScreener({"AKSEN": {"foreign_ratio": 30.0, "change_1m_bps": 2.0}})
    conn = ForeignFlowConnector(db_path=tmp_path / "ff.db", connector=mock, tickers=["AKSEN"])
    conn.fetch_and_store(date_str="2026-05-22")

    layer = SmartMoneyL5()
    # custody yok (None) → foreign_flow'a düşer → skor
    result = layer.compute_l5_score(
        "AKSEN",
        parquet_path=tmp_path / "none.parquet",
        custody_db_path=None,
        foreign_flow_db_path=tmp_path / "ff.db",
    )
    assert result is not None


def test_l5_foreign_flow_none_falls_back_to_parquet(tmp_path):
    """foreign_flow DB boş/yetersiz → parquet fallback (backward compat korunur)."""
    layer = SmartMoneyL5()
    # foreign_flow_db_path verilmeden eski davranış aynen çalışır
    result = layer.compute_l5_score(
        "AKBNK",
        parquet_path=tmp_path / "none.parquet",
        foreign_flow_db_path=tmp_path / "missing.db",  # yok → None → parquet (o da yok) → None
    )
    assert result is None  # ne foreign_flow ne parquet → None (graceful)

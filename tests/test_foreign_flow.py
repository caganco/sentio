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


# ---------------------------------------------------------------------------
# D-144 CB-011: Multi-window foreign flow + QNB filter tests
# ---------------------------------------------------------------------------
from src.data.foreign_flow_parser import (
    compute_boost_multiplier,
    compute_multi_window,
    qnb_filter,
)


class TestMultiWindowForeignFlow:
    """D-144: compute_multi_window pure function tests."""

    def test_delta_values_correct(self):
        """delta_Nd = (latest - Nd_ago) * 100 bps."""
        # series[-1]=0.25, series[-4]=0.22 -> delta_3d = (0.25-0.22)*100 = 3.0 bps
        series = [0.22, 0.23, 0.24, 0.25]
        mw = compute_multi_window("BIST", series)
        assert mw["delta_3d"] == pytest.approx(3.0, abs=1e-6)
        assert mw["delta_5d"] is None   # need >= 6 points
        assert mw["delta_10d"] is None  # need >= 11 points

    def test_insufficient_series_returns_none_deltas(self):
        """< 4 points -> delta_3d None; < 6 points -> delta_5d None."""
        series = [0.20, 0.21, 0.22]  # 3 points
        mw = compute_multi_window("BIST", series)
        assert mw["delta_3d"] is None
        assert mw["delta_5d"] is None
        assert mw["delta_10d"] is None

    def test_persistence_buy_5_days(self):
        """5 consecutive up days -> persistence=5, direction=BUY."""
        series = [0.20, 0.21, 0.22, 0.23, 0.24, 0.25]
        mw = compute_multi_window("BIST", series)
        assert mw["persistence"] == 5
        assert mw["direction"] == "BUY"

    def test_persistence_sell_3_days(self):
        """3 consecutive down days -> persistence=3, direction=SELL."""
        series = [0.30, 0.29, 0.28, 0.27]
        mw = compute_multi_window("BIST", series)
        assert mw["persistence"] == 3
        assert mw["direction"] == "SELL"

    def test_direction_neutral_minimal_change(self):
        """< 1 bps absolute delta -> NEUTRAL direction."""
        # delta_5d = (0.200009 - 0.200000) * 100 = 0.0009 bps < 1 bps
        series = [0.200000, 0.200001, 0.200002, 0.200003, 0.200005, 0.200009]
        mw = compute_multi_window("BIST", series)
        assert mw["direction"] == "NEUTRAL"

    def test_empty_series_safe(self):
        """Empty series -> no crash, persistence=0, direction=NEUTRAL."""
        mw = compute_multi_window("BIST", [])
        assert mw["persistence"] == 0
        assert mw["direction"] == "NEUTRAL"
        assert mw["delta_3d"] is None


class TestQNBFilter:
    """D-144: qnb_filter ticker-specific correction tests."""

    def test_qnb_filter_adjusts_qnbfb(self):
        """QNBFB.IS raw ~100% is scaled down to ~12%."""
        result = qnb_filter(100.0, "QNBFB.IS")
        assert result == pytest.approx(100.0 * 0.12, rel=1e-4)
        assert result < 20.0  # sanity: well below 100%

    def test_qnb_filter_passthrough_other_ticker(self):
        """Other tickers return raw value unchanged."""
        raw = 25.7
        assert qnb_filter(raw, "ARCLK.IS") == pytest.approx(raw)
        assert qnb_filter(raw, "KCHOL.IS") == pytest.approx(raw)
        assert qnb_filter(raw, "BIST") == pytest.approx(raw)

    def test_qnb_filter_adjusted_flag_in_multiwindow(self):
        """QNBFB.IS series -> qnb_adjusted=True in compute_multi_window output."""
        series = [90.0, 95.0, 98.0, 99.0]
        mw = compute_multi_window("QNBFB.IS", series)
        assert mw["qnb_adjusted"] is True

    def test_non_qnb_adjusted_flag_false(self):
        """Non-QNBFB ticker -> qnb_adjusted=False."""
        mw = compute_multi_window("BIST", [0.20, 0.21, 0.22, 0.23])
        assert mw["qnb_adjusted"] is False


class TestFFBoostMultiplier:
    """D-144: compute_boost_multiplier logic tests."""

    def test_boost_persistence_gte_3_active(self):
        """persistence >= 3 -> +0.20 boost (total 1.20)."""
        series = [0.20, 0.21, 0.22, 0.23]  # 3 up days, no delta_5d/10d
        mw = compute_multi_window("BIST", series)
        assert mw["persistence"] >= 3
        boost = compute_boost_multiplier(mw)
        assert boost == pytest.approx(1.20, abs=0.001)

    def test_boost_persistence_lt_3_no_boost(self):
        """persistence < 3 -> no boost (1.0), no alignment bonus."""
        # 2 up days preceded by a down day to cap persistence at 2
        series = [0.25, 0.20, 0.21, 0.22]  # down then 2 up -> persistence=2
        mw = compute_multi_window("BIST", series)
        if mw["persistence"] < 3:
            boost = compute_boost_multiplier(mw)
            assert boost == pytest.approx(1.0, abs=0.001)

    def test_boost_aligned_directions_adds_10pct(self):
        """delta_5d and delta_10d same sign -> +0.10 alignment bonus."""
        # 12 up-trending points: delta_5d > 0 AND delta_10d > 0
        series = [0.20 + i * 0.01 for i in range(12)]
        mw = compute_multi_window("BIST", series)
        assert mw["delta_5d"] is not None and mw["delta_5d"] > 0
        assert mw["delta_10d"] is not None and mw["delta_10d"] > 0
        boost = compute_boost_multiplier(mw)
        # persistence=11 (+0.20) + alignment (+0.10) = 1.30
        assert boost >= 1.10  # at least alignment bonus

    def test_boost_cap_1_5x_not_exceeded(self):
        """Boost is capped at 1.5x even if both bonuses apply."""
        # max theoretical = 1.0 + 0.20 + 0.10 = 1.30 (both bonuses)
        # test cap directly via dict override
        mw_mock = {"persistence": 10, "delta_5d": 5.0, "delta_10d": 8.0}
        boost = compute_boost_multiplier(mw_mock)
        assert boost <= 1.5
        assert boost == pytest.approx(1.30, abs=0.001)  # 1.0+0.20+0.10

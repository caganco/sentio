"""Tests for D-129 BIST Datastore aylik yabanci islem parser + L5 entegrasyonu.

Tum testler sentetik DataFrame + temp SQLite kullanir — gercek .xls IO GEREKMEZ
(xlrd 2.0 .xls yazamaz). Parser IO'dan ayrik (_transform/_extract_period saf).
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.data.bist_datastore_parser import (
    ForeignMonthlyDBWriter,
    _extract_period,
    _transform,
    _to_usd_float,
)
from src.signals.layers.smart_money_layer import SmartMoneyL5


# ---------------------------------------------------------------------------
# Helpers — ham (header=None) DataFrame'i taklit et
# ---------------------------------------------------------------------------

def _raw_with_header(period_text: str, data_rows: list[list]) -> pd.DataFrame:
    """Ilk satir donem metni, sonra 8-kolonlu data satirlari (pozisyonel)."""
    header = [
        ["Borsa Istanbul - Yabanci Islemler", None, None, None, None, None, None, None],
        [period_text, None, None, None, None, None, None, None],
        ["Pay", "Sirket", "Alis Nominal", "Alis TL", "Alis USD",
         "Satis Nominal", "Satis TL", "Satis USD"],
    ]
    return pd.DataFrame(header + data_rows)


# ---------------------------------------------------------------------------
# _to_usd_float
# ---------------------------------------------------------------------------

def test_to_usd_float_numeric_and_tr_format():
    assert _to_usd_float(1234.5) == pytest.approx(1234.5)
    assert _to_usd_float("1.234.567,89") == pytest.approx(1234567.89)
    assert _to_usd_float("") is None
    assert _to_usd_float(None) is None


# ---------------------------------------------------------------------------
# _extract_period
# ---------------------------------------------------------------------------

def test_extract_period_basic():
    raw = _raw_with_header("Yabanci Islemler - Mayis 2026", [])
    assert _extract_period(raw) == (2026, 5)


def test_extract_period_various_months():
    assert _extract_period(_raw_with_header("Ocak 2025", [])) == (2025, 1)
    assert _extract_period(_raw_with_header("Donem: Aralik 2024", [])) == (2024, 12)
    assert _extract_period(_raw_with_header("Agustos 2026 raporu", [])) == (2026, 8)


def test_extract_period_not_found_raises():
    raw = _raw_with_header("hicbir donem yok", [])
    with pytest.raises(ValueError):
        _extract_period(raw)


# ---------------------------------------------------------------------------
# _transform
# ---------------------------------------------------------------------------

def test_transform_strips_ticker_e_suffix():
    raw = _raw_with_header("Mayis 2026", [
        ["AKBNK.E", "Akbank", 100, 200, 5000.0, 50, 100, 3000.0],
    ])
    out = _transform(raw, 2026, 5)
    assert list(out["ticker"]) == ["AKBNK"]
    assert out.iloc[0]["year"] == 2026 and out.iloc[0]["month"] == 5


def test_transform_net_usd_computation():
    raw = _raw_with_header("Mayis 2026", [
        ["THYAO.E", "THY", 0, 0, 8000.0, 0, 0, 3000.0],
    ])
    out = _transform(raw, 2026, 5)
    assert out.iloc[0]["alis_usd"] == pytest.approx(8000.0)
    assert out.iloc[0]["satis_usd"] == pytest.approx(3000.0)
    assert out.iloc[0]["net_usd"] == pytest.approx(5000.0)


def test_transform_skips_market_group_and_header_rows():
    raw = _raw_with_header("Mayis 2026", [
        ["Yildiz Pazar", None, None, None, None, None, None, None],
        ["AKBNK.E", "Akbank", 1, 1, 5000.0, 1, 1, 3000.0],
        ["Ana Pazar", None, None, None, None, None, None, None],
        ["GARAN.E", "Garanti", 1, 1, 2000.0, 1, 1, 2500.0],
        [None, None, None, None, None, None, None, None],
    ])
    out = _transform(raw, 2026, 5)
    assert set(out["ticker"]) == {"AKBNK", "GARAN"}
    assert len(out) == 2
    # net direction: AKBNK net +2000 (alim), GARAN net -500 (satim)
    net = dict(zip(out["ticker"], out["net_usd"]))
    assert net["AKBNK"] == pytest.approx(2000.0)
    assert net["GARAN"] == pytest.approx(-500.0)


def test_transform_tr_formatted_numbers():
    raw = _raw_with_header("Mayis 2026", [
        ["SISE.E", "Sise", "1.000", "2.000", "1.234.567,50", "500", "900", "234.567,50"],
    ])
    out = _transform(raw, 2026, 5)
    assert out.iloc[0]["net_usd"] == pytest.approx(1000000.0)


# ---------------------------------------------------------------------------
# ForeignMonthlyDBWriter
# ---------------------------------------------------------------------------

def _df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["ticker", "year", "month", "alis_usd", "satis_usd", "net_usd"])


def test_db_init_and_upsert(tmp_path):
    w = ForeignMonthlyDBWriter(tmp_path / "fm.db")
    n = w.upsert(_df([
        {"ticker": "AKBNK", "year": 2026, "month": 3, "alis_usd": 5000, "satis_usd": 3000, "net_usd": 2000},
    ]))
    assert n == 1
    assert (tmp_path / "fm.db").exists()


def test_db_upsert_idempotent_unique(tmp_path):
    w = ForeignMonthlyDBWriter(tmp_path / "fm.db")
    w.upsert(_df([{"ticker": "AKBNK", "year": 2026, "month": 3, "alis_usd": 1, "satis_usd": 1, "net_usd": 100}]))
    w.upsert(_df([{"ticker": "AKBNK", "year": 2026, "month": 3, "alis_usd": 1, "satis_usd": 1, "net_usd": 999}]))
    hist = w.get_net_history("AKBNK", months=12)
    assert hist == [999.0]  # UNIQUE(year,month,ticker) -> replace


def test_get_net_history_ordered_and_capped(tmp_path):
    w = ForeignMonthlyDBWriter(tmp_path / "fm.db")
    w.upsert(_df([
        {"ticker": "X", "year": 2026, "month": 1, "alis_usd": 0, "satis_usd": 0, "net_usd": 10},
        {"ticker": "X", "year": 2026, "month": 3, "alis_usd": 0, "satis_usd": 0, "net_usd": 30},
        {"ticker": "X", "year": 2026, "month": 2, "alis_usd": 0, "satis_usd": 0, "net_usd": 20},
    ]))
    assert w.get_net_history("X", months=3) == [10.0, 20.0, 30.0]
    assert w.get_net_history("X", months=2) == [20.0, 30.0]


# ---------------------------------------------------------------------------
# compute_l5_score — foreign_monthly tier
# ---------------------------------------------------------------------------

def _seed(tmp_path, ticker: str, monthly_nets: list[tuple[int, int, float]]):
    db = tmp_path / "fm.db"
    w = ForeignMonthlyDBWriter(db)
    w.upsert(_df([
        {"ticker": ticker, "year": y, "month": m, "alis_usd": 0, "satis_usd": 0, "net_usd": net}
        for (y, m, net) in monthly_nets
    ]))
    return db


def test_l5_foreign_monthly_uptrend_entry(tmp_path):
    db = _seed(tmp_path, "AKBNK", [(2026, 1, 100.0), (2026, 2, 200.0), (2026, 3, 500.0)])
    layer = SmartMoneyL5()
    score = layer.compute_l5_score(
        "AKBNK", parquet_path=tmp_path / "none.parquet", foreign_monthly_db_path=db,
    )
    assert score == pytest.approx(70.0)  # FOREIGN_MONTHLY_ENTRY_SCORE


def test_l5_foreign_monthly_downtrend_exit(tmp_path):
    db = _seed(tmp_path, "AKBNK", [(2026, 1, 500.0), (2026, 2, 300.0), (2026, 3, 100.0)])
    layer = SmartMoneyL5()
    score = layer.compute_l5_score(
        "AKBNK", parquet_path=tmp_path / "none.parquet", foreign_monthly_db_path=db,
    )
    assert score == pytest.approx(30.0)  # FOREIGN_MONTHLY_EXIT_SCORE


def test_l5_foreign_monthly_flat_neutral(tmp_path):
    db = _seed(tmp_path, "AKBNK", [(2026, 1, 100.0), (2026, 2, 250.0), (2026, 3, 100.0)])
    layer = SmartMoneyL5()
    score = layer.compute_l5_score(
        "AKBNK", parquet_path=tmp_path / "none.parquet", foreign_monthly_db_path=db,
    )
    assert score == pytest.approx(50.0)  # delta (last-first) == 0


def test_l5_foreign_monthly_insufficient_history_falls_back(tmp_path):
    db = _seed(tmp_path, "AKBNK", [(2026, 3, 100.0)])  # tek ay -> <2 -> None
    layer = SmartMoneyL5()
    score = layer.compute_l5_score(
        "AKBNK", parquet_path=tmp_path / "none.parquet", foreign_monthly_db_path=db,
    )
    assert score is None  # foreign_monthly None + parquet yok -> None (graceful)


def test_l5_foreign_flow_precedence_over_monthly(tmp_path):
    """foreign_flow veri varsa foreign_monthly okunmaz."""
    from src.data.isyatirim_scraper import ForeignFlowDBWriter, ForeignFlowSummary
    from datetime import datetime, timezone
    fresh = datetime.now(timezone.utc).isoformat()
    ff_db = tmp_path / "ff.db"
    ffw = ForeignFlowDBWriter(ff_db)
    ffw.upsert_summary([
        ForeignFlowSummary("2026-04-22", "AKBNK", 28.0, fresh),
        ForeignFlowSummary("2026-05-22", "AKBNK", 30.0, fresh),
    ])
    # monthly DB downtrend (30) olsa da foreign_flow oncelikli
    fm_db = _seed(tmp_path, "AKBNK", [(2026, 1, 500.0), (2026, 2, 300.0), (2026, 3, 100.0)])
    layer = SmartMoneyL5()
    score = layer.compute_l5_score(
        "AKBNK",
        parquet_path=tmp_path / "none.parquet",
        foreign_flow_db_path=ff_db,
        foreign_monthly_db_path=fm_db,
    )
    # foreign_flow custody-makinesi skoru (30 EXIT degil) -> monthly EXIT'ten farkli
    assert score is not None
    assert score != pytest.approx(30.0)

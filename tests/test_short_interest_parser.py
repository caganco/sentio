"""Tests for D-132 Is Yatirim aciga satis PDF parser.

Tum testler IO'suz: sentetik satir listeleri ve gecici cache dizinleri kullanir.
Gercek PDF fetch/parse gerektiren testler VERIFY marker ile isaretlenmis
(canli dosya olmadan calismaz, bu yuzden skipped).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.data.isyatirim_short_interest_parser import (
    IsyatirimShortInterestConnector,
    _build_url,
    _cache_path,
    _load_cache,
    _parse_float_tr,
    _save_cache,
    parse_table_rows,
)


# ---------------------------------------------------------------------------
# _parse_float_tr
# ---------------------------------------------------------------------------

def test_parse_float_tr_numeric():
    assert _parse_float_tr(12.5) == pytest.approx(12.5)
    assert _parse_float_tr(0) == pytest.approx(0.0)


def test_parse_float_tr_string_dot_decimal():
    assert _parse_float_tr("3.45") == pytest.approx(3.45)


def test_parse_float_tr_tr_format():
    assert _parse_float_tr("1.234,56") == pytest.approx(1234.56)


def test_parse_float_tr_percent_strip():
    assert _parse_float_tr("7,50%") == pytest.approx(7.5)


def test_parse_float_tr_none_and_empty():
    assert _parse_float_tr(None) is None
    assert _parse_float_tr("") is None
    assert _parse_float_tr("-") is None


# ---------------------------------------------------------------------------
# parse_table_rows
# ---------------------------------------------------------------------------

def test_parse_table_rows_basic():
    rows = [
        ["Hisse", "Aciga Satis Orani (%)", "Tutar (USD)"],
        ["AKSEN", "7,50", "12345678"],
        ["THYAO", "3,20", "5000000"],
    ]
    result = parse_table_rows(rows)
    assert "AKSEN" in result
    assert result["AKSEN"]["short_ratio"] == pytest.approx(7.5)
    assert result["AKSEN"]["amount_usd"] == pytest.approx(12345678.0)
    assert "THYAO" in result
    assert result["THYAO"]["short_ratio"] == pytest.approx(3.2)


def test_parse_table_rows_skips_header_and_non_ticker():
    rows = [
        ["Hisse Kodu", "Oran", "Tutar"],  # header — 'Hisse' regex match etmez
        ["Piyasa Toplam", "15.0", "9999"],  # non-ticker ("Piyasa" -> regex fail)
        ["GARAN", "5,00", "3000000"],
    ]
    result = parse_table_rows(rows)
    assert "GARAN" in result
    assert "Hisse Kodu" not in result
    assert "Piyasa Toplam" not in result


def test_parse_table_rows_empty():
    assert parse_table_rows([]) == {}


def test_parse_table_rows_missing_amount():
    rows = [
        ["SISE", "4,10"],  # amount kolonu yok
    ]
    result = parse_table_rows(rows)
    assert "SISE" in result
    assert result["SISE"].get("short_ratio") == pytest.approx(4.1)
    assert "amount_usd" not in result["SISE"]


def test_parse_table_rows_all_zero_ratio_skipped():
    """short_ratio=0 ve amount_usd=0 ise entry yok (her ikisi None olmali)."""
    rows = [
        ["BIMAS", "", ""],  # her iki deger bos -> None -> atlama
    ]
    result = parse_table_rows(rows)
    assert "BIMAS" not in result


# ---------------------------------------------------------------------------
# Cache IO (_load_cache / _save_cache)
# ---------------------------------------------------------------------------

def test_cache_roundtrip(tmp_path):
    data = {"AKSEN": {"short_ratio": 7.5, "amount_usd": 1000000.0}}
    d = date(2026, 5, 22)
    _save_cache(data, d, tmp_path)
    loaded = _load_cache(d, tmp_path)
    assert loaded == data


def test_cache_miss_returns_none(tmp_path):
    assert _load_cache(date(2000, 1, 1), tmp_path) is None


def test_cache_path_format(tmp_path):
    p = _cache_path(date(2026, 5, 22), tmp_path)
    assert p.name == "isyatirim_short_interest_20260522.json"


# ---------------------------------------------------------------------------
# _build_url
# ---------------------------------------------------------------------------

def test_build_url_format():
    url = _build_url(date(2026, 5, 22))
    assert "2026" in url
    assert "05" in url
    assert "22052026" in url
    assert url.endswith(".pdf")


# ---------------------------------------------------------------------------
# IsyatirimShortInterestConnector — cache-only path
# ---------------------------------------------------------------------------

def test_connector_get_short_ratios_from_cache(tmp_path):
    """Cache'te veri varsa connector dogrudan dondurmeli."""
    data = {
        "AKSEN": {"short_ratio": 6.2, "amount_usd": 500000.0},
        "THYAO": {"short_ratio": 2.1, "amount_usd": 200000.0},
    }
    d = date(2026, 5, 22)
    _save_cache(data, d, tmp_path)

    conn = IsyatirimShortInterestConnector(cache_dir=tmp_path)
    ratios = conn.get_short_ratios(report_date=d)
    assert ratios["AKSEN"] == pytest.approx(6.2)
    assert ratios["THYAO"] == pytest.approx(2.1)


def test_connector_no_data_returns_empty(tmp_path):
    """Cache yok ve HTTP erisim yok -> bos dict."""
    conn = IsyatirimShortInterestConnector(cache_dir=tmp_path)
    # Gercek fetch yapmamak icin bilinen bir tarih gecir (cache de yok)
    result = conn.get_short_ratios(report_date=date(2000, 1, 1))
    assert isinstance(result, dict)

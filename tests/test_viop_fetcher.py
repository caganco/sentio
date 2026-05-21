"""Tests for VIOP fetcher and layer (D-099).

All HTTP calls are mocked — no live network required.
"""
from __future__ import annotations

import io
import math
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.viop_fetcher import (
    _last_trading_day,
    compute_oi_delta,
    compute_pc_ratio,
    compute_ticker_oi,
    fetch_viop_csv,
    fetch_viopgs_csv,
    parse_contract_symbol,
)
from src.signals.layers.viop_layer import _pc_to_score, score_viop
from src.signals.models import LayerScore
from src.signals.thresholds import (
    VIOP_MIN_OI,
    VIOP_PC_SCORES,
    VIOP_PC_THRESHOLDS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_CSV = (
    "Sözleşme Adı;Toplam Açık Pozisyon (Lot)\n"
    "THYAOE0626C110;1000\n"
    "THYAOE0626C115;500\n"
    "THYAOE0626P100;800\n"
    "THYAOE0626P095;400\n"
    "EREGLE0626C50;300\n"
    "EREGLE0626P45;600\n"
)

_YESTERDAY_CSV = (
    "Sözleşme Adı;Toplam Açık Pozisyon (Lot)\n"
    "THYAOE0626C110;900\n"
    "THYAOE0626C115;450\n"
    "THYAOE0626P100;700\n"
    "THYAOE0626P095;350\n"
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(_SAMPLE_CSV), sep=";")


@pytest.fixture
def yesterday_df() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(_YESTERDAY_CSV), sep=";")


# ---------------------------------------------------------------------------
# _last_trading_day
# ---------------------------------------------------------------------------

def test_last_trading_day_is_weekday():
    d = _last_trading_day()
    assert d.weekday() < 5, f"Expected weekday, got {d} ({d.strftime('%A')})"


def test_last_trading_day_before_today():
    assert _last_trading_day() < date.today()


def test_last_trading_day_skips_weekend():
    # Monday 2026-05-18 → last trading day should be Friday 2026-05-15
    monday = date(2026, 5, 18)
    result = _last_trading_day(ref=monday)
    assert result == date(2026, 5, 15)


# ---------------------------------------------------------------------------
# parse_contract_symbol
# ---------------------------------------------------------------------------

def test_parse_call_contract():
    result = parse_contract_symbol("THYAOE0626C110")
    assert result is not None
    assert result["ticker"] == "THYAO"
    assert result["type"] == "C"
    assert result["expiry"] == "0626"


def test_parse_put_contract():
    result = parse_contract_symbol("THYAOE0626P100")
    assert result is not None
    assert result["ticker"] == "THYAO"
    assert result["type"] == "P"


def test_parse_futures_contract():
    result = parse_contract_symbol("XU030F0626")
    assert result is not None
    assert result["type"] == "F"


def test_parse_is_suffix_stripped_in_symbol():
    # parse_contract_symbol works on raw contract names (no .IS suffix)
    result = parse_contract_symbol("EREGLE0626C50")
    assert result is not None
    assert result["ticker"] == "EREGL"


def test_parse_unrecognized_returns_none():
    assert parse_contract_symbol("XYZ123") is None
    assert parse_contract_symbol("") is None
    assert parse_contract_symbol("THYAO") is None


# ---------------------------------------------------------------------------
# compute_ticker_oi
# ---------------------------------------------------------------------------

def test_compute_oi_thyao(sample_df):
    oi = compute_ticker_oi(sample_df, "THYAO")
    assert oi["call_oi"] == pytest.approx(1500.0)
    assert oi["put_oi"] == pytest.approx(1200.0)
    assert oi["total_oi"] == pytest.approx(2700.0)


def test_compute_oi_strips_is_suffix(sample_df):
    oi_with = compute_ticker_oi(sample_df, "THYAO.IS")
    oi_without = compute_ticker_oi(sample_df, "THYAO")
    assert oi_with == oi_without


def test_compute_oi_missing_ticker(sample_df):
    oi = compute_ticker_oi(sample_df, "ARCLK")
    assert oi["call_oi"] == 0.0
    assert oi["put_oi"] == 0.0
    assert oi["total_oi"] == 0.0


def test_compute_oi_empty_df():
    oi = compute_ticker_oi(pd.DataFrame(), "THYAO")
    assert oi["total_oi"] == 0.0


# ---------------------------------------------------------------------------
# compute_pc_ratio
# ---------------------------------------------------------------------------

def test_pc_ratio_bullish():
    oi = {"call_oi": 1500.0, "put_oi": 600.0, "total_oi": 2100.0}
    assert compute_pc_ratio(oi) == pytest.approx(0.4)


def test_pc_ratio_bearish():
    oi = {"call_oi": 500.0, "put_oi": 1500.0, "total_oi": 2000.0}
    assert compute_pc_ratio(oi) == pytest.approx(3.0)


def test_pc_ratio_neutral():
    oi = {"call_oi": 1000.0, "put_oi": 1000.0, "total_oi": 2000.0}
    assert compute_pc_ratio(oi) == pytest.approx(1.0)


def test_pc_ratio_no_calls_returns_inf():
    oi = {"call_oi": 0.0, "put_oi": 1000.0, "total_oi": 1000.0}
    assert math.isinf(compute_pc_ratio(oi))


def test_pc_ratio_both_zero_returns_one():
    oi = {"call_oi": 0.0, "put_oi": 0.0, "total_oi": 0.0}
    assert compute_pc_ratio(oi) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# compute_oi_delta
# ---------------------------------------------------------------------------

def test_oi_delta_increase():
    today = {"total_oi": 3000.0}
    yesterday = {"total_oi": 2500.0}
    assert compute_oi_delta(today, yesterday) == pytest.approx(0.20)


def test_oi_delta_decrease():
    today = {"total_oi": 1800.0}
    yesterday = {"total_oi": 2000.0}
    assert compute_oi_delta(today, yesterday) == pytest.approx(-0.10)


def test_oi_delta_zero_yesterday():
    today = {"total_oi": 1000.0}
    yesterday = {"total_oi": 0.0}
    assert compute_oi_delta(today, yesterday) == 0.0


def test_oi_delta_no_change():
    oi = {"total_oi": 2000.0}
    assert compute_oi_delta(oi, oi) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# HTTP fetch mocking
# ---------------------------------------------------------------------------

@patch("src.data.viop_fetcher.requests.get")
def test_fetch_viop_csv_http_404(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp
    result = fetch_viop_csv(date(2026, 5, 19))
    assert result is None


@patch("src.data.viop_fetcher.requests.get")
def test_fetch_viop_csv_network_error(mock_get):
    mock_get.side_effect = ConnectionError("network failure")
    result = fetch_viop_csv(date(2026, 5, 19))
    assert result is None


@patch("src.data.viop_fetcher.requests.get")
def test_fetch_viopgs_csv_http_404(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp
    result = fetch_viopgs_csv(date(2026, 5, 19))
    assert result is None


# ---------------------------------------------------------------------------
# _pc_to_score
# ---------------------------------------------------------------------------

def test_pc_to_score_very_bullish():
    score = _pc_to_score(0.3)  # < very_bullish threshold (0.50)
    assert score == VIOP_PC_SCORES["very_bullish"]


def test_pc_to_score_bullish():
    score = _pc_to_score(0.65)  # 0.50–0.80
    assert score == VIOP_PC_SCORES["bullish"]


def test_pc_to_score_neutral_low():
    score = _pc_to_score(0.90)  # 0.80–1.00
    assert score == VIOP_PC_SCORES["neutral_low"]


def test_pc_to_score_neutral_high():
    score = _pc_to_score(1.10)  # 1.00–1.20
    assert score == VIOP_PC_SCORES["neutral_high"]


def test_pc_to_score_bearish():
    score = _pc_to_score(1.50)  # 1.20–2.00
    assert score == VIOP_PC_SCORES["bearish"]


def test_pc_to_score_very_bearish():
    score = _pc_to_score(3.0)  # >= 2.00
    assert score == VIOP_PC_SCORES["very_bearish"]


# ---------------------------------------------------------------------------
# score_viop integration
# ---------------------------------------------------------------------------

def test_score_viop_missing_df_returns_missing():
    result = score_viop("THYAO", viop_df=pd.DataFrame())
    assert isinstance(result, LayerScore)
    assert result.score == 50.0
    assert result.confidence == 0.0
    assert result.source == "missing"
    assert result.layer == "viop"


def test_score_viop_returns_layer_score(sample_df):
    result = score_viop("THYAO", viop_df=sample_df)
    assert isinstance(result, LayerScore)
    assert result.layer == "viop"
    assert 0.0 <= result.score <= 100.0
    assert 0.0 <= result.confidence <= 1.0


def test_score_viop_insufficient_oi_returns_partial(sample_df):
    # ARCLK has no contracts in sample_df → total_oi=0 < VIOP_MIN_OI
    result = score_viop("ARCLK", viop_df=sample_df)
    assert result.source == "partial"
    assert result.score == 50.0
    assert result.confidence == pytest.approx(0.3)


def test_score_viop_thyao_pc_ratio_in_detail(sample_df):
    result = score_viop("THYAO", viop_df=sample_df)
    # THYAO: call_oi=1500, put_oi=1200 → PC = 0.8 → neutral_low (55.0)
    assert result.detail["pc_ratio"] == pytest.approx(0.8)
    assert result.detail["call_oi"] == pytest.approx(1500.0)
    assert result.detail["put_oi"] == pytest.approx(1200.0)


def test_score_viop_thyao_neutral_low_score(sample_df):
    result = score_viop("THYAO", viop_df=sample_df)
    assert result.score == pytest.approx(VIOP_PC_SCORES["neutral_low"])


def test_score_viop_weight_zero(sample_df):
    result = score_viop("THYAO", viop_df=sample_df)
    assert result.weight == pytest.approx(0.0)


def test_score_viop_detail_keys(sample_df):
    result = score_viop("THYAO", viop_df=sample_df)
    for key in ("symbol", "call_oi", "put_oi", "total_oi", "pc_ratio", "oi_delta_pct", "as_of_date"):
        assert key in result.detail, f"Missing detail key: {key}"


def test_score_viop_with_yesterday_oi_delta(sample_df, yesterday_df):
    # Today THYAO total_oi=2700, yesterday=2400 → delta=+12.5% > 10% threshold
    # base_score=55 (neutral_low), bullish direction → score boosted by 5
    result = score_viop("THYAO", viop_df=sample_df, yesterday_df=yesterday_df)
    assert result.source == "computed"
    assert result.detail["oi_delta_pct"] > 0


def test_score_viop_is_suffix_handled(sample_df):
    with_suffix = score_viop("THYAO.IS", viop_df=sample_df)
    without_suffix = score_viop("THYAO", viop_df=sample_df)
    assert with_suffix.score == without_suffix.score
    assert with_suffix.detail["symbol"] == "THYAO"


def test_score_viop_none_viop_df_calls_fetcher():
    with patch("src.signals.layers.viop_layer.fetch_viop_csv") as mock_fetch:
        mock_fetch.return_value = None
        result = score_viop("THYAO")
        mock_fetch.assert_called_once()
        assert result.source == "missing"

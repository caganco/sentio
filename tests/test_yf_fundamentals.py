"""Tests for yfinance fundamentals fetcher + fallback logic (D-175).

Tum testler mock — gercek yfinance / MKK API cagrisi yok.
"""
from __future__ import annotations

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

import src.data.yfinance_fundamentals_fetcher as _yf_mod
from src.data.yfinance_fundamentals_fetcher import fetch_yf_fundamentals
from src.data.kap_historical_fetcher import _COLS as KAP_COLS, fetch_fundamentals_with_fallback


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stmt(metrics: dict, period_end: str) -> pd.DataFrame:
    """metric_name -> value; yfinance-like DataFrame (index=metrics, columns=[date])."""
    col = pd.Timestamp(period_end)
    return pd.DataFrame({col: metrics})


def _mock_ticker(
    qf: "pd.DataFrame | None" = None,
    qbs: "pd.DataFrame | None" = None,
    af: "pd.DataFrame | None" = None,
    abs_: "pd.DataFrame | None" = None,
) -> MagicMock:
    t = MagicMock()
    t.quarterly_financials = qf if qf is not None else pd.DataFrame()
    t.quarterly_balance_sheet = qbs if qbs is not None else pd.DataFrame()
    t.financials = af if af is not None else pd.DataFrame()
    t.balance_sheet = abs_ if abs_ is not None else pd.DataFrame()
    return t


# ---------------------------------------------------------------------------
# TestPublicationDateLag
# ---------------------------------------------------------------------------

class TestPublicationDateLag:
    def test_quarterly_publication_date_lag_60_days(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_yf_mod, "_CACHE_DIR", tmp_path)
        qf = _make_stmt({"Gross Profit": 5e10, "Total Revenue": 8e10, "Net Income": 2e10}, "2023-09-30")
        mock_t = _mock_ticker(qf=qf)

        with patch("yfinance.Ticker", return_value=mock_t):
            df = fetch_yf_fundamentals("THYAO", 2023, 2023)

        assert len(df) == 1
        assert df.iloc[0]["publication_date"] == "2023-11-29"

    def test_annual_publication_date_lag_90_days(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_yf_mod, "_CACHE_DIR", tmp_path)
        af = _make_stmt({"Gross Profit": 2e11, "Total Revenue": 5e11, "Net Income": 8e10}, "2022-12-31")
        mock_t = _mock_ticker(af=af)

        with patch("yfinance.Ticker", return_value=mock_t):
            df = fetch_yf_fundamentals("THYAO", 2022, 2022)

        assert len(df) == 1
        assert df.iloc[0]["publication_date"] == "2023-03-31"


# ---------------------------------------------------------------------------
# TestFieldMapping
# ---------------------------------------------------------------------------

class TestFieldMapping:
    def test_field_mapping_gross_profit(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_yf_mod, "_CACHE_DIR", tmp_path)
        qf = _make_stmt(
            {"Gross Profit": 5e10, "Total Revenue": 1e11, "Net Income": 2e10},
            "2023-09-30",
        )
        mock_t = _mock_ticker(qf=qf)

        with patch("yfinance.Ticker", return_value=mock_t):
            df = fetch_yf_fundamentals("THYAO", 2023, 2023)

        assert len(df) == 1
        assert df.iloc[0]["gross_profit"] == pytest.approx(5e10)


# ---------------------------------------------------------------------------
# TestFallbackLogic
# ---------------------------------------------------------------------------

class TestFallbackLogic:
    def test_mkk_takes_priority_over_yfinance(self, monkeypatch):
        mkk_row = {col: None for col in KAP_COLS}
        mkk_row.update({"date": "2023-11-01", "ticker": "THYAO", "year": 2023, "gross_profit": 5e10})
        mkk_df = pd.DataFrame([mkk_row])

        yf_calls: list[int] = []

        def fake_fr_history(t, s, e):
            return mkk_df

        def fake_yf(t, s, e):
            yf_calls.append(1)
            return pd.DataFrame(columns=KAP_COLS)

        monkeypatch.setattr("src.data.kap_historical_fetcher.fetch_fr_history", fake_fr_history)
        monkeypatch.setattr(_yf_mod, "fetch_yf_fundamentals", fake_yf)

        result = fetch_fundamentals_with_fallback("THYAO", 2023, 2023)
        assert yf_calls == [], "MKK doluyken yfinance cagrılmamali"
        assert len(result) == 1

    def test_yfinance_fallback_when_mkk_empty(self, monkeypatch):
        yf_row = {col: None for col in KAP_COLS}
        yf_row.update({
            "date": "2023-11-29", "ticker": "THYAO", "year": 2023,
            "gross_profit": 3e10, "publication_date": "2023-11-29",
        })
        yf_df = pd.DataFrame([yf_row])

        monkeypatch.setattr("src.data.kap_historical_fetcher.fetch_fr_history",
                            lambda t, s, e: pd.DataFrame(columns=KAP_COLS))
        monkeypatch.setattr(_yf_mod, "fetch_yf_fundamentals", lambda t, s, e: yf_df)

        result = fetch_fundamentals_with_fallback("THYAO", 2023, 2023)
        assert len(result) == 1
        assert float(result.iloc[0]["gross_profit"]) == pytest.approx(3e10)

    def test_empty_when_both_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setattr(_yf_mod, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr("src.data.kap_historical_fetcher.fetch_fr_history",
                            lambda t, s, e: pd.DataFrame(columns=KAP_COLS))
        mock_t = _mock_ticker()

        with patch("yfinance.Ticker", return_value=mock_t):
            result = fetch_fundamentals_with_fallback("THYAO", 2023, 2023)

        assert result.empty

"""
Tests for src.data.fetcher.fetch_macro_symbol — D-148 Alt-B.
Dayanak: SPEC_DATA_ROBUSTNESS_1 §S-2.
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.fetcher import fetch_macro_symbol


class TestFetchMacroSymbol:
    """fetch_macro_symbol: None-guard, retry, and success path tests."""

    def test_returns_float_on_success(self):
        """Normal path: history returns two rows → returns last Close as float."""
        mock_hist = pd.DataFrame({"Close": [10.5, 11.2]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = fetch_macro_symbol("USDTRY=X")
        assert isinstance(result, float)
        assert result == pytest.approx(11.2)

    def test_returns_none_on_empty_dataframe(self):
        """Empty DataFrame → all retries yield empty → returns None (no raise)."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = fetch_macro_symbol("USDTRY=X", retries=1)
        assert result is None

    def test_returns_none_on_all_nan_close(self):
        """All-NaN Close column → dropna() empties series → returns None."""
        mock_hist = pd.DataFrame({"Close": [float("nan"), float("nan")]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_hist
        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = fetch_macro_symbol("^VIX", retries=1)
        assert result is None

    def test_retries_on_exception_then_succeeds(self):
        """First attempt raises RuntimeError, second returns valid data → float returned."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = [
            RuntimeError("connection timeout"),
            pd.DataFrame({"Close": [42.0]}),
        ]
        with patch("yfinance.Ticker", return_value=mock_ticker):
            with patch("time.sleep"):  # skip backoff delay in tests
                result = fetch_macro_symbol("TUR", retries=2)
        assert result == pytest.approx(42.0)

    def test_returns_none_after_all_retries_exhausted(self):
        """All retries raise exception → returns None, never raises."""
        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = RuntimeError("network down")
        with patch("yfinance.Ticker", return_value=mock_ticker):
            with patch("time.sleep"):
                result = fetch_macro_symbol("^DXY", retries=3)
        assert result is None

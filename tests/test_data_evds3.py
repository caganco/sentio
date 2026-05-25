"""
Tests for src.data.evds_client — D-151 RR-021 cleanup + TÜFE freshness audit.

Covers:
  - is_series_fresh(): stale-detect logic (boundary, empty, fresh, stale)
  - fetch_series(): response parsing with mocked requests (no live API calls)
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.data.evds_client import _parse_evds_date, is_series_fresh


class TestParseEvdsDate:
    """_parse_evds_date(): EVDS date format parsing tests."""

    def test_iso_full_date(self):
        """YYYY-MM-DD (daily series) → parsed correctly."""
        from datetime import date
        assert _parse_evds_date("2026-05-26") == date(2026, 5, 26)

    def test_monthly_zero_padded(self):
        """YYYY-MM (monthly, zero-padded) → first of that month."""
        from datetime import date
        assert _parse_evds_date("2025-10") == date(2025, 10, 1)

    def test_monthly_single_digit(self):
        """YYYY-M (monthly, single-digit) → first of that month."""
        from datetime import date
        assert _parse_evds_date("2026-1") == date(2026, 1, 1)

    def test_empty_string_returns_none(self):
        assert _parse_evds_date("") is None

    def test_garbage_returns_none(self):
        assert _parse_evds_date("not-a-date") is None


class TestIsSeriesFresh:
    """is_series_fresh(): stale-detect unit tests (D-151, RR-021 §3.3)."""

    def _data(self, days_ago: int) -> list[dict]:
        """Helper: build a single-observation mock series result N days ago."""
        d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        return [{"date": d, "value": 85.0}]

    def test_recent_data_is_fresh(self):
        """30 days ago, stale_days=45 → True (within window)."""
        assert is_series_fresh(self._data(30), stale_days=45) is True

    def test_old_data_is_stale(self):
        """60 days ago, stale_days=45 → False (exceeds window)."""
        assert is_series_fresh(self._data(60), stale_days=45) is False

    def test_empty_data_returns_false(self):
        """No observations → False (no date to check)."""
        assert is_series_fresh([], stale_days=45) is False

    def test_exactly_at_threshold_is_fresh(self):
        """Exactly stale_days=45 ago → True (boundary is inclusive)."""
        assert is_series_fresh(self._data(45), stale_days=45) is True

    def test_monthly_series_one_day_over_threshold(self):
        """Monthly series: 46 days old with stale_days=45 → False (stale)."""
        assert is_series_fresh(self._data(46), stale_days=45) is False

    def test_monthly_evds_format_stale(self):
        """Monthly EVDS date 'YYYY-M' parsed correctly: 2025-10 = Oct 2025 → stale today."""
        # 2025-10 = Oct 1 2025, ~237 days ago from May 2026 → stale
        data = [{"date": "2025-10", "value": 3453.09}]
        assert is_series_fresh(data, stale_days=45) is False

    def test_monthly_evds_format_recent(self):
        """'YYYY-M' (current month) → _parse returns 1st of month → within 45 days → True."""
        from datetime import date
        # Current month's 1st is always ≤ 31 days ago → within any stale_days >= 31
        today = date.today()
        month_str = f"{today.year}-{today.month}"
        data = [{"date": month_str, "value": 3700.0}]
        assert is_series_fresh(data, stale_days=45) is True

    def test_malformed_date_returns_false(self):
        """Unparseable date string → False (safe fallback, no exception)."""
        data = [{"date": "not-a-date", "value": 85.0}]
        assert is_series_fresh(data, stale_days=45) is False

    def test_missing_date_key_returns_false(self):
        """Item missing 'date' key → KeyError caught → False."""
        data = [{"value": 85.0}]
        assert is_series_fresh(data, stale_days=45) is False


class TestEvdsClientParse:
    """fetch_series(): response parsing with mocked requests — no live API calls."""

    def test_fetch_series_returns_list_on_success(self):
        """Mock valid JSON response with 2 items → list of 2 dicts returned."""
        from src.data.evds_client import fetch_series

        mock_json = {
            "items": [
                {"Tarih": "01-01-2024", "TP_FE_OKTG01": "85.5"},
                {"Tarih": "01-02-2024", "TP_FE_OKTG01": "87.1"},
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_json
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            # Pass api_key directly to bypass EVDS_API_KEY env-var check in unit tests
            result = fetch_series("TP.FE.OKTG01", "3m", api_key="test-key")

        assert isinstance(result, list)
        assert len(result) == 2

    def test_fetch_series_raises_on_empty_items(self):
        """items=[] → EvdsError raised (0 observations is a fetch failure, not silent)."""
        from src.data.evds_client import EvdsError, fetch_series

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"items": []}
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(EvdsError, match="0 observations"):
                fetch_series("TP.FE.OKTG01", "3m", api_key="test-key")

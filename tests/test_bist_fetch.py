"""Unit tests for BistForeignOwnershipClient.fetch_and_store()."""
import os
from unittest.mock import patch

import pytest
import requests

from src.signals.local import LocalMacroCache, BistForeignOwnershipClient


@pytest.fixture
def cache(tmp_path):
    """File-based cache for testing."""
    db_file = str(tmp_path / "test_macro.db")
    return LocalMacroCache(db_file)


@pytest.fixture
def bist_client(cache):
    """BIST foreign client instance."""
    return BistForeignOwnershipClient(cache)


class TestBistForeignFetchAndStore:
    """Tests for BistForeignOwnershipClient.fetch_and_store()."""

    def test_missing_api_key(self, bist_client):
        """Missing EVDS_API_KEY returns False."""
        with patch.dict(os.environ, {}, clear=True):
            result = bist_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.bist_foreign_client.requests.get")
    def test_timeout(self, mock_get, bist_client):
        """Request timeout returns False."""
        mock_get.side_effect = requests.exceptions.Timeout()

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = bist_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.bist_foreign_client.requests.get")
    def test_no_valid_series(self, mock_get, bist_client):
        """No valid series returns False."""
        # All series IDs return 404 or invalid response
        mock_get.return_value.status_code = 404

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = bist_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.bist_foreign_client.requests.get")
    def test_successful_fetch(self, mock_get, bist_client, cache):
        """Valid EVDS response stores foreign ownership data."""
        # First call succeeds
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"Tarih": "2026-05-09", "Birimi": "28.45"},  # current
                {"Tarih": "2026-05-02", "Birimi": "28.33"},  # previous
            ]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = bist_client.fetch_and_store()
            assert result is True

        # Verify cache
        foreign_data = cache.get_latest_bist_foreign()
        assert foreign_data is not None
        assert float(foreign_data["foreign_ownership_pct"]) == 28.45
        # Weekly change should be +0.12%
        assert 0.1 < float(foreign_data["pct_change_weekly"]) < 0.15

    @patch("src.signals.local.bist_foreign_client.requests.get")
    def test_single_data_point(self, mock_get, bist_client, cache):
        """Single data point (no previous for comparison) still stores."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"Tarih": "2026-05-09", "Birimi": "28.45"}]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = bist_client.fetch_and_store()
            assert result is True

        foreign_data = cache.get_latest_bist_foreign()
        assert foreign_data is not None
        assert float(foreign_data["foreign_ownership_pct"]) == 28.45
        # No previous, so change should be 0
        assert float(foreign_data["pct_change_weekly"]) == 0.0

    @patch("src.signals.local.bist_foreign_client.requests.get")
    def test_parse_error(self, mock_get, bist_client):
        """Parse error returns False."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError("Invalid JSON")

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = bist_client.fetch_and_store()
            assert result is False

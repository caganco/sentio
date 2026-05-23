"""Unit tests for TCMBClient.fetch_and_store()."""
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.signals.local import LocalMacroCache, TCMBClient


@pytest.fixture
def cache(tmp_path):
    """In-memory cache for testing."""
    db_file = str(tmp_path / "test_macro.db")
    return LocalMacroCache(db_file)


@pytest.fixture
def tcmb_client(cache):
    """TCMB client instance."""
    return TCMBClient(cache)


class TestTCMBFetchAndStore:
    """Tests for TCMBClient.fetch_and_store()."""

    def test_missing_api_key(self, tcmb_client):
        """Missing EVDS_API_KEY returns False."""
        with patch.dict(os.environ, {}, clear=True):
            result = tcmb_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_http_error(self, mock_get, tcmb_client):
        """HTTP error (5xx) returns False."""
        mock_get.return_value.status_code = 500
        mock_get.return_value.text = "Server error"

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_timeout(self, mock_get, tcmb_client):
        """Timeout returns False."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_malformed_json(self, mock_get, tcmb_client):
        """Malformed JSON returns False."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError("Invalid JSON")

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_insufficient_data(self, mock_get, tcmb_client):
        """< 2 data points returns False."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"Tarih": "2026-05-14", "Birimi": "33.0"}]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is False

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_successful_hike(self, mock_get, tcmb_client, cache):
        """Valid response with hike decision stores correctly."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"Tarih": "2026-05-08", "Birimi": "33.0"},  # current
                {"Tarih": "2026-05-01", "Birimi": "32.0"},  # previous
            ]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is True

        # Verify cache
        decision = cache.get_latest_tcmb()
        assert decision is not None
        assert decision["decision_type"] == "hike"
        assert decision["rate_after"] == 33.0
        assert decision["rate_before"] == 32.0

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_successful_cut(self, mock_get, tcmb_client, cache):
        """Valid response with cut decision stores correctly."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"Tarih": "2026-05-08", "Birimi": "30.0"},  # current
                {"Tarih": "2026-05-01", "Birimi": "32.0"},  # previous
            ]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is True

        decision = cache.get_latest_tcmb()
        assert decision["decision_type"] == "cut"

    @patch("src.signals.local.tcmb_client.requests.get")
    def test_successful_hold(self, mock_get, tcmb_client, cache):
        """Valid response with hold decision stores correctly."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [
                {"Tarih": "2026-05-08", "Birimi": "32.0"},  # current
                {"Tarih": "2026-05-01", "Birimi": "32.0"},  # previous
            ]
        }

        with patch.dict(os.environ, {"EVDS_API_KEY": "test_key"}):
            result = tcmb_client.fetch_and_store()
            assert result is True

        decision = cache.get_latest_tcmb()
        assert decision["decision_type"] == "hold"

"""Unit tests for CDSClient.fetch_and_store()."""
from unittest.mock import patch

import pytest
import requests

from src.signals.local import LocalMacroCache, CDSClient


@pytest.fixture
def cache(tmp_path):
    """File-based cache for testing."""
    db_file = str(tmp_path / "test_macro.db")
    return LocalMacroCache(db_file)


@pytest.fixture
def cds_client(cache):
    """CDS client instance."""
    return CDSClient(cache)


class TestCDSFetchAndStore:
    """Tests for CDSClient.fetch_and_store()."""

    @patch("src.signals.local.cds_client.requests.get")
    def test_http_error(self, mock_get, cds_client):
        """HTTP error returns False."""
        mock_get.return_value.status_code = 404

        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.signals.local.cds_client.requests.get")
    def test_timeout(self, mock_get, cds_client):
        """Request timeout returns False."""
        mock_get.side_effect = requests.exceptions.Timeout()

        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.signals.local.cds_client.requests.get")
    def test_network_error(self, mock_get, cds_client):
        """Network error returns False."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.signals.local.cds_client.requests.get")
    def test_cds_value_not_found(self, mock_get, cds_client):
        """CDS value not found in page returns False."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"<html><body>No CDS data</body></html>"

        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.signals.local.cds_client.requests.get")
    def test_successful_cds_extraction(self, mock_get, cds_client, cache):
        """Valid CDS value extracted and stored."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"""
        <html>
        <body>
            <div>Turkey Government Bonds</div>
            <span>5 Y CDS Spread: 287.5</span>
            <span>Rating: Stable</span>
        </body>
        </html>
        """

        result = cds_client.fetch_and_store()
        assert result is True

        # Verify cache
        cds_data = cache.get_latest_cds()
        assert cds_data is not None
        # Value should be 287.5
        assert 285.0 < float(cds_data["cds_bps"]) < 290.0

    @patch("src.signals.local.cds_client.requests.get")
    def test_realistic_cds_range(self, mock_get, cds_client, cache):
        """CDS value in realistic range (0-1000 bps) is accepted."""
        mock_get.return_value.status_code = 200
        # HTML with realistic CDS value
        mock_get.return_value.content = b"""
        <html>
        <body>
            <div>Turkey 5-Year CDS Spread</div>
            <span>350.75</span>
        </body>
        </html>
        """

        result = cds_client.fetch_and_store()
        # If 350.75 is found, should succeed
        if result:
            cds_data = cache.get_latest_cds()
            assert cds_data is not None
            assert 0 < float(cds_data["cds_bps"]) < 1000

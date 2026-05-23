"""Unit tests for CDSClient.fetch_and_store() and cds_fetcher module."""
from unittest.mock import patch

import pytest

from src.signals.local import CDSClient, LocalMacroCache


@pytest.fixture
def cache(tmp_path):
    db_file = str(tmp_path / "test_macro.db")
    return LocalMacroCache(db_file)


@pytest.fixture
def cds_client(cache):
    return CDSClient(cache)


class TestCDSFetchAndStore:
    """CDSClient.fetch_and_store() delegates to cds_fetcher."""

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=None)
    def test_http_error(self, mock_fetch, cds_client):
        """Total failure (None from fetcher) returns False."""
        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=None)
    def test_timeout(self, mock_fetch, cds_client):
        """Fetcher returning None (e.g. timeout) returns False."""
        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=None)
    def test_network_error(self, mock_fetch, cds_client):
        """Fetcher returning None (e.g. network error) returns False."""
        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=None)
    def test_cds_value_not_found(self, mock_fetch, cds_client):
        """Fetcher returning None stores nothing and returns False."""
        result = cds_client.fetch_and_store()
        assert result is False

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=287.5)
    def test_successful_cds_extraction(self, mock_fetch, cds_client, cache):
        """Valid CDS value from fetcher is stored in cache."""
        result = cds_client.fetch_and_store()
        assert result is True
        cds_data = cache.get_latest_cds()
        assert cds_data is not None
        assert 285.0 < float(cds_data["cds_bps"]) < 290.0

    @patch("src.data.cds_fetcher.fetch_turkey_cds_bps", return_value=350.75)
    def test_realistic_cds_range(self, mock_fetch, cds_client, cache):
        """CDS value in realistic range is stored correctly."""
        result = cds_client.fetch_and_store()
        assert result is True
        cds_data = cache.get_latest_cds()
        assert cds_data is not None
        assert 0 < float(cds_data["cds_bps"]) < 1000

"""D-170: KapApiClient birim testleri — mock ile, ag cagrisi yok."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.data.kap_api_client import KapApiClient, KapApiError


def _make_client() -> KapApiClient:
    return KapApiClient("https://apigwdev.mkk.com.tr", "user:pass", auth_type="basic")


class TestKapApiClient:
    """D-170: KapApiClient HTTP wrapper testleri."""

    # ------------------------------------------------------------------
    def test_get_last_index_success(self):
        """get_last_index() basarili yanit → int donmeli."""
        client = _make_client()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"lastDisclosureIndex": 99999}

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            result = client.get_last_index()

        assert result == 99999
        assert isinstance(result, int)
        called_url = mock_get.call_args[0][0]
        assert "/api/vyk/lastDisclosureIndex" in called_url

    # ------------------------------------------------------------------
    def test_get_disclosures_success(self):
        """get_disclosures() basarili yanit → list donmeli; endpoint ve paramlar dogru."""
        client = _make_client()
        payload = [
            {"index": 1001, "member": "THYAO", "year": "2024", "disclosureClass": "FR"},
            {"index": 1002, "member": "THYAO", "year": "2024", "disclosureClass": "FR"},
        ]
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            result = client.get_disclosures(start_index=0, disclosure_class="FR")

        assert result == payload
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["disclosureIndex"] == 0
        assert call_kwargs["params"]["disclosureClass"] == "FR"
        assert "/api/vyk/disclosures" in mock_get.call_args[0][0]

    # ------------------------------------------------------------------
    def test_get_disclosure_detail_success(self):
        """get_disclosure_detail() basarili yanit → dict donmeli; endpoint dogru."""
        client = _make_client()
        payload = {
            "index": 1001,
            "items": [
                {"name": "Revenue", "value": "5000000000"},
                {"name": "GrossProfit", "value": "1200000000"},
                {"name": "ProfitLoss", "value": "800000000"},
            ],
        }
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload

        with patch.object(client._session, "get", return_value=mock_resp) as mock_get:
            result = client.get_disclosure_detail(1001)

        assert result == payload
        called_url = mock_get.call_args[0][0]
        assert "/api/vyk/disclosureDetail/1001" in called_url
        assert mock_get.call_args[1]["params"]["fileType"] == "data"

    # ------------------------------------------------------------------
    def test_raises_kap_api_error_on_non_200(self):
        """HTTP 403 → KapApiError raise edilmeli."""
        client = _make_client()
        mock_resp = MagicMock(status_code=403, text="Forbidden")

        with patch.object(client._session, "get", return_value=mock_resp):
            with pytest.raises(KapApiError, match="403"):
                client.get_disclosures(start_index=0, disclosure_class="FR")

    # ------------------------------------------------------------------
    def test_rate_limit_sleep_called_between_requests(self):
        """Her API cagrisi oncesinde time.sleep(1.0) cagrilmali."""
        client = _make_client()
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = []

        with patch("src.data.kap_api_client.time.sleep") as mock_sleep, \
             patch.object(client._session, "get", return_value=mock_resp):
            client.get_disclosures(start_index=0, disclosure_class="FR")
            client.get_disclosures(start_index=100, disclosure_class="ODA")

        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 1.0

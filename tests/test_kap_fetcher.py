"""Tests for src/data/kap_fetcher.py."""

import time
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from kap_client.exceptions import CompanyNotFoundError, KapError, RateLimitError

from src.data.kap_fetcher import (
    _disclosure_to_dict,
    fetch_all_symbols,
    fetch_attachments_for_disclosure,
    fetch_disclosures_for_symbol,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_disclosure(index=1234567, subject="Ozel Durum", has_attachment=False):
    d = MagicMock()
    d.index = index
    d.publish_datetime.isoformat.return_value = "2026-05-13T09:14:00"
    d.company_name = "Turk Hava Yollari"
    d.stock_codes = "THYAO"
    d.subject = subject
    d.summary = "THYAO bildirimi."
    d.disclosure_type = "FS"
    d.has_attachment = has_attachment
    d.is_late = False
    d.is_corrective = False
    d.is_english = False
    d.url = f"https://www.kap.org.tr/tr/Bildirim/{index}"
    return d


def _make_kap_client(disclosures=None):
    kap = MagicMock()
    kap.fetch_disclosures.return_value = disclosures if disclosures is not None else [_make_disclosure()]
    return kap


# ---------------------------------------------------------------------------
# fetch_disclosures_for_symbol
# ---------------------------------------------------------------------------

class TestFetchDisclosuresForSymbol:

    def test_returns_list_of_dicts(self):
        kap = _make_kap_client([_make_disclosure()])
        result = fetch_disclosures_for_symbol("THYAO", date(2026, 5, 13), kap)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["index"] == 1234567

    def test_empty_day_returns_empty_list(self):
        kap = _make_kap_client([])
        result = fetch_disclosures_for_symbol("THYAO", date(2026, 5, 13), kap)
        assert result == []

    def test_unknown_symbol_returns_empty(self):
        kap = MagicMock()
        kap.fetch_disclosures.side_effect = CompanyNotFoundError("XXXXXX")
        result = fetch_disclosures_for_symbol("XXXXXX", date(2026, 5, 13), kap)
        assert result == []

    def test_kap_error_returns_empty(self):
        kap = MagicMock()
        kap.fetch_disclosures.side_effect = KapError("connection error")
        result = fetch_disclosures_for_symbol("THYAO", date(2026, 5, 13), kap)
        assert result == []

    def test_rate_limit_raises_after_max_retries(self):
        kap = MagicMock()
        kap.fetch_disclosures.side_effect = RateLimitError(None)
        with patch("src.data.kap_fetcher.time.sleep"):
            with pytest.raises(RateLimitError):
                fetch_disclosures_for_symbol("THYAO", date(2026, 5, 13), kap)

    def test_disclosure_dict_has_required_keys(self):
        kap = _make_kap_client([_make_disclosure()])
        result = fetch_disclosures_for_symbol("THYAO", date(2026, 5, 13), kap)
        d = result[0]
        for key in ("index", "publish_datetime", "subject", "url", "has_attachment", "disclosure_type"):
            assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# fetch_all_symbols
# ---------------------------------------------------------------------------

class TestFetchAllSymbols:

    def test_returns_dict_keyed_by_symbol(self):
        disc = _make_disclosure()
        with patch("src.data.kap_fetcher.Kap") as MockKap:
            instance = MagicMock()
            instance.fetch_disclosures.return_value = [disc]
            MockKap.return_value.__enter__.return_value = instance
            MockKap.return_value.__exit__.return_value = None

            result = fetch_all_symbols(["THYAO", "AKBNK"], date(2026, 5, 13), rate_limit_delay_sec=0)
        assert "THYAO" in result
        assert "AKBNK" in result
        assert isinstance(result["THYAO"], list)

    def test_rate_limit_delay_applied(self):
        with patch("src.data.kap_fetcher.Kap") as MockKap:
            instance = MagicMock()
            instance.fetch_disclosures.return_value = []
            MockKap.return_value.__enter__.return_value = instance
            MockKap.return_value.__exit__.return_value = None

            with patch("src.data.kap_fetcher.time.sleep") as mock_sleep:
                fetch_all_symbols(["THYAO", "AKBNK"], date(2026, 5, 13), rate_limit_delay_sec=0.5)

        assert mock_sleep.call_count == 1  # sleep called between symbols (n-1 times)

    def test_rate_limited_symbol_skipped_not_raised(self):
        with patch("src.data.kap_fetcher.Kap") as MockKap:
            instance = MagicMock()
            instance.fetch_disclosures.side_effect = RateLimitError(None)
            MockKap.return_value.__enter__.return_value = instance
            MockKap.return_value.__exit__.return_value = None

            with patch("src.data.kap_fetcher.time.sleep"):
                result = fetch_all_symbols(["THYAO"], date(2026, 5, 13))

        assert result["THYAO"] == []


# ---------------------------------------------------------------------------
# fetch_attachments_for_disclosure
# ---------------------------------------------------------------------------

class TestFetchAttachments:

    def test_returns_url_list(self):
        att = MagicMock()
        att.url = "https://www.kap.org.tr/tr/api/file/download/abc123"
        kap = MagicMock()
        kap.fetch_attachments.return_value = [att]
        result = fetch_attachments_for_disclosure(1234567, kap)
        assert result == ["https://www.kap.org.tr/tr/api/file/download/abc123"]

    def test_no_attachments_returns_empty(self):
        kap = MagicMock()
        kap.fetch_attachments.return_value = []
        result = fetch_attachments_for_disclosure(1234567, kap)
        assert result == []

    def test_exception_returns_empty_not_raised(self):
        kap = MagicMock()
        kap.fetch_attachments.side_effect = Exception("network error")
        result = fetch_attachments_for_disclosure(1234567, kap)
        assert result == []

    def test_attachment_without_url_skipped(self):
        att = MagicMock()
        att.url = ""
        kap = MagicMock()
        kap.fetch_attachments.return_value = [att]
        result = fetch_attachments_for_disclosure(1234567, kap)
        assert result == []


# ---------------------------------------------------------------------------
# _disclosure_to_dict helper
# ---------------------------------------------------------------------------

class TestDisclosureToDict:

    def test_serializes_all_fields(self):
        d = _make_disclosure(index=999)
        result = _disclosure_to_dict(d)
        assert result["index"] == 999
        assert result["subject"] == "Ozel Durum"
        assert result["has_attachment"] is False
        assert "url" in result
        assert "publish_datetime" in result

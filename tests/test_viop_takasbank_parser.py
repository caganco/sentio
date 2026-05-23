"""Tests for CB-008: Takasbank VIOP put/call ratio parser.

No network calls — HTML is injected as string via monkeypatch.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from src.data.viop_takasbank_parser import _parse_pcr, _to_int, fetch_viop_pcr

# ---------------------------------------------------------------------------
# Sample HTML fixtures
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """
<html><body>
<table>
  <tr><th>Tip</th><th>Acik Pozisyon (Lot)</th></tr>
  <tr><td>Call / Alim</td><td>150,000</td></tr>
  <tr><td>Put / Satis</td><td>180,000</td></tr>
</table>
</body></html>
"""

_HTML_NO_TABLE = "<html><body><p>Veri bulunamadi</p></body></html>"

_HTML_ZERO_CALL = """
<html><body>
<table>
  <tr><td>Put / Satis</td><td>50000</td></tr>
</table>
</body></html>
"""

_HTML_ENGLISH_KEYWORDS = """
<html><body>
<table>
  <tr><td>Call Options</td><td>200000</td></tr>
  <tr><td>Put Options</td><td>100000</td></tr>
</table>
</body></html>
"""


# ---------------------------------------------------------------------------
# TestParsePcr — unit tests for _parse_pcr()
# ---------------------------------------------------------------------------

class TestParsePcr:
    def test_parse_success_returns_correct_ratio(self):
        """Gecerli HTML -> PCR = 180000 / 150000 = 1.2."""
        result = _parse_pcr(_SAMPLE_HTML)
        assert result is not None
        assert result["put_oi"] == 180000
        assert result["call_oi"] == 150000
        assert abs(result["put_call_ratio"] - 1.2) < 1e-4

    def test_parse_sets_today_date(self):
        """Sonuc 'date' alani bugunun tarihini icermeli."""
        from datetime import date
        result = _parse_pcr(_SAMPLE_HTML)
        assert result is not None
        assert result["date"] == date.today().isoformat()

    def test_no_table_returns_none(self):
        """<table> yoksa call_oi=0 -> None."""
        result = _parse_pcr(_HTML_NO_TABLE)
        assert result is None

    def test_zero_call_oi_guard(self):
        """Sadece put satirlari var -> call_oi=0 -> None, ZeroDivisionError yok."""
        result = _parse_pcr(_HTML_ZERO_CALL)
        assert result is None

    def test_english_keywords_parsed(self):
        """'call'/'put' keyword'leri Ingilizce HTML'de de calisir."""
        result = _parse_pcr(_HTML_ENGLISH_KEYWORDS)
        assert result is not None
        assert result["call_oi"] == 200000
        assert result["put_oi"] == 100000
        assert abs(result["put_call_ratio"] - 0.5) < 1e-4


# ---------------------------------------------------------------------------
# TestToInt — unit tests for _to_int()
# ---------------------------------------------------------------------------

class TestToInt:
    def test_comma_separated(self):
        assert _to_int("150,000") == 150000

    def test_plain_number(self):
        assert _to_int("9876") == 9876

    def test_non_numeric_returns_none(self):
        assert _to_int("Call / Alim") is None

    def test_empty_string_returns_none(self):
        assert _to_int("") is None


# ---------------------------------------------------------------------------
# TestFetchViopPcr — network-mocked integration tests
# ---------------------------------------------------------------------------

class TestFetchViopPcr:
    def _make_response(self, html: str, status_code: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = html
        if status_code >= 400:
            resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                f"HTTP {status_code}"
            )
        else:
            resp.raise_for_status.return_value = None
        return resp

    def test_fetch_success(self, monkeypatch):
        """200 + gecerli HTML -> PCR dict donduruluyor."""
        monkeypatch.setattr(
            "src.data.viop_takasbank_parser.requests.get",
            lambda *a, **kw: self._make_response(_SAMPLE_HTML),
        )
        result = fetch_viop_pcr()
        assert result is not None
        assert "put_call_ratio" in result
        assert result["put_oi"] == 180000

    def test_http_error_returns_none(self, monkeypatch):
        """HTTP 500 -> None, exception yukariya firlatilmiyor."""
        monkeypatch.setattr(
            "src.data.viop_takasbank_parser.requests.get",
            lambda *a, **kw: self._make_response("", status_code=500),
        )
        result = fetch_viop_pcr()
        assert result is None

    def test_network_timeout_returns_none(self, monkeypatch):
        """Timeout -> None."""
        def _raise(*a, **kw):
            raise requests.exceptions.Timeout("timed out")

        monkeypatch.setattr("src.data.viop_takasbank_parser.requests.get", _raise)
        result = fetch_viop_pcr()
        assert result is None

    def test_connection_error_returns_none(self, monkeypatch):
        """ConnectionError -> None."""
        def _raise(*a, **kw):
            raise requests.exceptions.ConnectionError("refused")

        monkeypatch.setattr("src.data.viop_takasbank_parser.requests.get", _raise)
        result = fetch_viop_pcr()
        assert result is None

    def test_unparseable_html_returns_none(self, monkeypatch):
        """200 ama tablo yok -> None."""
        monkeypatch.setattr(
            "src.data.viop_takasbank_parser.requests.get",
            lambda *a, **kw: self._make_response(_HTML_NO_TABLE),
        )
        result = fetch_viop_pcr()
        assert result is None


# ---------------------------------------------------------------------------
# TestThresholdConstants — import kontrolu
# ---------------------------------------------------------------------------

class TestThresholdConstants:
    def test_viop_pcr_bearish_defined(self):
        from src.signals.thresholds import VIOP_PCR_BEARISH
        assert VIOP_PCR_BEARISH == 1.2

    def test_viop_pcr_bullish_defined(self):
        from src.signals.thresholds import VIOP_PCR_BULLISH
        assert VIOP_PCR_BULLISH == 0.6

    def test_bearish_greater_than_bullish(self):
        from src.signals.thresholds import VIOP_PCR_BEARISH, VIOP_PCR_BULLISH
        assert VIOP_PCR_BEARISH > VIOP_PCR_BULLISH

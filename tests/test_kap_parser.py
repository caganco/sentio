"""Tests for src/data/kap_parser.py."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.data.kap_parser import (
    KapEvent,
    EventCategory,
    classify_category,
    extract_structured_data,
    parse_all,
    parse_disclosure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _raw_disclosure(
    index=1234567,
    subject="Ozel Durum Aciklamasi",
    has_attachment=False,
    summary="Ozet metin.",
    url="https://www.kap.org.tr/tr/Bildirim/1234567",
    publish_datetime="2026-05-13T09:14:00",
):
    return {
        "index": index,
        "publish_datetime": publish_datetime,
        "company_name": "Turk Hava Yollari",
        "stock_codes": "THYAO",
        "subject": subject,
        "summary": summary,
        "disclosure_type": "FS",
        "has_attachment": has_attachment,
        "is_late": False,
        "is_corrective": False,
        "is_english": False,
        "url": url,
    }


def _mock_kap():
    kap = MagicMock()
    kap.fetch_attachments.return_value = []
    return kap


# ---------------------------------------------------------------------------
# classify_category
# ---------------------------------------------------------------------------

class TestClassifyCategory:

    def test_ozel_durum(self):
        assert classify_category("Ozel Durum Aciklamasi — Sozlesme") == "ozel_durum"

    def test_temettu(self):
        assert classify_category("Temettu Karari — Pay Basi 2.50 TL") == "temettu"

    def test_finansal_rapor(self):
        assert classify_category("Finansal Rapor Yayinlandi") == "finansal_rapor"

    def test_finansal_tablo(self):
        assert classify_category("Finansal Tablo Bildirimi") == "finansal_rapor"

    def test_genel_kurul(self):
        assert classify_category("Genel Kurul Toplanti Kararlari") == "genel_kurul"

    def test_sermaye_artirimi(self):
        assert classify_category("Sermaye Artirimi Karari") == "sermaye_artirimi"

    def test_bedelsiz_maps_to_sermaye(self):
        assert classify_category("Bedelsiz Sermaye Artirimi") == "sermaye_artirimi"

    def test_insider_iceriden(self):
        assert classify_category("Iceriden Islem Bildirimi") == "insider"

    def test_unknown_falls_to_diger(self):
        assert classify_category("Bilinmeyen Baslik XYZ 12345") == "diger"

    def test_empty_string_falls_to_diger(self):
        assert classify_category("") == "diger"

    def test_case_insensitive(self):
        assert classify_category("TEMETTU KARARI") == "temettu"


# ---------------------------------------------------------------------------
# extract_structured_data
# ---------------------------------------------------------------------------

class TestExtractStructuredData:

    def test_non_dividend_returns_empty(self):
        result = extract_structured_data("Ozel Durum", "ozel_durum", [])
        assert result == {}

    def test_diger_returns_empty(self):
        result = extract_structured_data("XYZ", "diger", [])
        assert result == {}

    def test_capital_increase_no_percentage(self):
        result = extract_structured_data("Bedelsiz Sermaye Artirimi", "sermaye_artirimi", [])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# parse_disclosure
# ---------------------------------------------------------------------------

class TestParseDisclosure:

    def test_returns_kap_event(self):
        raw = _raw_disclosure()
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert isinstance(ev, KapEvent)

    def test_source_type_is_kap_official(self):
        raw = _raw_disclosure()
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.source_type == "kap_official"

    def test_source_domain_is_kap(self):
        raw = _raw_disclosure()
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.source_domain == "kap.org.tr"

    def test_symbol_set_correctly(self):
        raw = _raw_disclosure()
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.symbol == "THYAO"

    def test_disclosure_index_is_string(self):
        raw = _raw_disclosure(index=9876)
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.disclosure_index == "9876"

    def test_category_classified_correctly(self):
        raw = _raw_disclosure(subject="Ozel Durum Aciklamasi")
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.category == "ozel_durum"

    def test_attachment_urls_fetched_when_has_attachment(self):
        raw = _raw_disclosure(has_attachment=True)
        att = MagicMock()
        att.url = "https://kap.org.tr/tr/api/file/download/xyz"
        kap = MagicMock()
        kap.fetch_attachments.return_value = [att]
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.has_attachment is True
        assert len(ev.attachment_urls) == 1

    def test_no_attachment_fetch_when_false(self):
        raw = _raw_disclosure(has_attachment=False)
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        kap.fetch_attachments.assert_not_called()

    def test_bad_publish_datetime_uses_epoch(self):
        raw = _raw_disclosure(publish_datetime="NOT_A_DATE")
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.published_at == datetime.min

    def test_summary_truncated_to_500(self):
        raw = _raw_disclosure(summary="X" * 600)
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert len(ev.summary) <= 500

    def test_empty_subject_gives_diger(self):
        raw = _raw_disclosure(subject="")
        kap = _mock_kap()
        ev = parse_disclosure(raw, "THYAO", datetime(2026, 5, 13, 17, 0), kap)
        assert ev.category == "diger"


# ---------------------------------------------------------------------------
# parse_all
# ---------------------------------------------------------------------------

class TestParseAll:

    def test_empty_input_returns_empty(self):
        kap = _mock_kap()
        result = parse_all({}, datetime(2026, 5, 13, 17, 0), kap)
        assert result == []

    def test_sorted_by_published_at_desc(self):
        raw1 = _raw_disclosure(index=1, publish_datetime="2026-05-13T08:00:00")
        raw2 = _raw_disclosure(index=2, publish_datetime="2026-05-13T10:00:00")
        kap = _mock_kap()
        result = parse_all({"THYAO": [raw1, raw2]}, datetime(2026, 5, 13, 17, 0), kap)
        assert result[0].disclosure_index == "2"
        assert result[1].disclosure_index == "1"

    def test_multiple_symbols_all_parsed(self):
        raw_thyao = _raw_disclosure(index=10)
        raw_akbnk = _raw_disclosure(index=20, subject="Temettu Karari")
        kap = _mock_kap()
        result = parse_all(
            {"THYAO": [raw_thyao], "AKBNK": [raw_akbnk]},
            datetime(2026, 5, 13, 17, 0),
            kap,
        )
        symbols = {ev.symbol for ev in result}
        assert "THYAO" in symbols
        assert "AKBNK" in symbols

    def test_bad_disclosure_skipped_not_raised(self):
        broken = {"index": None, "subject": "test"}  # missing required fields → exception
        kap = _mock_kap()
        result = parse_all({"THYAO": [broken]}, datetime(2026, 5, 13, 17, 0), kap)
        assert isinstance(result, list)

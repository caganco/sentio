"""D-172: kap_historical_fetcher birim testleri — mock, ag cagrisi yok.

Mock payload'lari canli MKK VYK test API'sinden dogrulanmis yapilari yansitir.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import src.data.kap_historical_fetcher as fetcher


def _fin_detail(year: str, gp_cur: str, gp_prev: str, rev_cur: str) -> dict:
    """subject=Financial Report olan gercek-yapi disclosureDetail (data)."""
    return {
        "disclosureIndex": "1118481",
        "year": year,
        "time": "01.03.2023 18:22:57",
        "period": {"tr": "Yillik", "en": "Annual"},
        "subject": {"tr": "Finansal Rapor", "en": "Financial Report"},
        "presentation": [
            {
                "id": "p1",
                "content": {
                    "ReportItem": {
                        "name": "root",
                        "abstract": "true",
                        "ReportItem": [
                            {
                                "name": "GrossProfit",
                                "Values": {"Value": [
                                    {"contextId": f"{year}-01-01{year}-12-31",
                                     "currency": "TRY", "value": gp_cur},
                                    {"contextId": "2021-01-012021-12-31",
                                     "currency": "TRY", "value": gp_prev},
                                ]},
                            },
                            {
                                "name": "Revenue",
                                "Values": {"Value": [
                                    {"contextId": f"{year}-01-01{year}-12-31",
                                     "currency": "TRY", "value": rev_cur},
                                ]},
                            },
                        ],
                    },
                },
            }
        ],
    }


class TestBuildCompanyMap:
    """D-172: companyId→ticker haritasi + cache."""

    def test_build_company_map_caches_result(self, tmp_path, monkeypatch):
        """Ilk cagri get_members; ikinci cagri cache'den (get_members tekrar cagrilmaz)."""
        monkeypatch.setenv("MKK_VYK_BASE_URL", "https://apigwdev.mkk.com.tr")
        monkeypatch.setenv("MKK_VYK_TOKEN", "user:pass")
        monkeypatch.setattr(fetcher, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(fetcher, "_COMPANY_MAP_PATH", tmp_path / "kap_company_map.json")

        mock_client = MagicMock()
        mock_client.get_members.return_value = [
            {"id": "1107", "title": "THY", "stockCode": "THYAO", "memberType": "IGS"},
            {"id": "1383", "title": "FB", "stockCode": "FENER", "memberType": "IGS"},
            {"id": "999", "title": "Nostock", "stockCode": None, "memberType": "X"},
        ]
        monkeypatch.setattr(fetcher, "_make_client", lambda: mock_client)

        m1 = fetcher.build_company_map()
        m2 = fetcher.build_company_map()

        assert m1 == {"1107": "THYAO", "1383": "FENER"}  # stockCode None atlanir
        assert m2 == m1
        assert mock_client.get_members.call_count == 1  # ikinci cagri cache hit


class TestFetchYear:
    """D-172: _fetch_year filtreleme mantigi."""

    def test_fetch_year_skips_pre_kap40_disclosures(self):
        """disclosureIndex < 538004 → detail cagrilmaz, atlanir."""
        client = MagicMock()
        client.get_disclosures.return_value = [{"disclosureIndex": "500000"}]

        rows = fetcher._fetch_year(client, "THYAO", 2022, {"THYAO": "1107"})

        assert rows == []
        client.get_disclosure_detail.assert_not_called()

    def test_fetch_year_skips_non_financial_report_subject(self):
        """subject Operating Review → atlanir; Financial Report → islenir."""
        client = MagicMock()
        client.get_disclosures.return_value = [
            {"disclosureIndex": "1118484"},  # operating review
            {"disclosureIndex": "1118481"},  # financial report
        ]

        def _detail(idx, file_type="data"):
            if idx == 1118484:
                return {
                    "year": "2022", "time": "01.03.2023 10:00:00",
                    "period": {"tr": "Yillik"}, "subject": {"en": "Operating Review"},
                    "presentation": [],
                }
            return _fin_detail("2022", "75641000000", "22145000000", "311169000000")

        client.get_disclosure_detail.side_effect = _detail

        rows = fetcher._fetch_year(client, "THYAO", 2022, {"THYAO": "1107"})

        assert len(rows) == 1
        assert rows[0]["year"] == 2022
        assert rows[0]["gross_profit"] == 75641000000.0

    def test_fetch_year_returns_empty_when_company_unknown(self):
        """ticker company_map'te yoksa → bos, get_disclosures cagrilmaz."""
        client = MagicMock()
        rows = fetcher._fetch_year(client, "ZZZZ", 2022, {"THYAO": "1107"})
        assert rows == []
        client.get_disclosures.assert_not_called()


class TestParsing:
    """D-172: TR tarih + XBRL traverse + CURR context."""

    def test_parse_tr_date_format(self):
        assert fetcher._parse_tr_date("29.10.2023 14:05:18") == "2023-10-29"
        assert fetcher._parse_tr_date("01.03.2023 18:22:57") == "2023-03-01"
        assert fetcher._parse_tr_date("") is None
        assert fetcher._parse_tr_date(None) is None
        assert fetcher._parse_tr_date("gecersiz") is None

    def test_xbrl_traverse_finds_gross_profit(self):
        """Nested presentation → gross_profit/revenue dogru CURR degeri + meta."""
        detail = _fin_detail("2022", "75641000000", "22145000000", "311169000000")
        row = fetcher._parse_xbrl(detail, "THYAO", 2022)

        assert row["gross_profit"] == 75641000000.0
        assert row["revenue"] == 311169000000.0
        assert row["publication_date"] == "2023-03-01"
        assert row["date"] == "2023-03-01"
        assert row["period"] == "Yillik"
        assert row["ticker"] == "THYAO"
        assert row["year"] == 2022

    def test_curr_context_selected_not_prev(self):
        """Value listesinde hem CURR (2022) hem PREV (2021) → CURR secilir."""
        detail = _fin_detail("2022", "100", "999", "200")
        row = fetcher._parse_xbrl(detail, "THYAO", 2022)
        assert row["gross_profit"] == 100.0   # 2022 CURR, 999 PREV degil
        assert row["revenue"] == 200.0

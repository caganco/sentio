"""Is Yatirim MaliTablo fetcher tests (D-183). Mock only, no network."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.data import isyatirim_malitablo_fetcher as mf


def _resp(status=200, text='{"value": []}', payload=None):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.json.return_value = payload if payload is not None else {"value": []}
    return r


_ROWS = [
    {"itemCode": "2O", "itemDescTr": "Ana Ortakliga Ait Ozkaynaklar",
     "value1": 1000.0, "value2": 900.0, "value3": 800.0, "value4": 700.0},
    {"itemCode": "3DF", "itemDescTr": "FAALIYET KARI (ZARARI)",
     "value1": 300.0, "value2": 250.0, "value3": 200.0, "value4": 150.0},
    {"itemCode": "4CAB", "itemDescTr": "Amortisman & Itfa Paylari",
     "value1": 50.0, "value2": 45.0, "value3": 40.0, "value4": 35.0},
    {"itemCode": "2OA", "itemDescTr": "Odenmis Sermaye",
     "value1": 100.0, "value2": 100.0, "value3": 100.0, "value4": 100.0},
]


def test_parse_values_maps_itemcodes():
    codes = {"book": "2O", "op": "3DF", "da": "4CAB", "shares": "2OA", "missing": "ZZZ"}
    out = mf.parse_values(_ROWS, codes)
    assert out["book"] == [1000.0, 900.0, 800.0, 700.0]
    assert out["op"][0] == 300.0
    assert out["da"][3] == 35.0
    assert out["shares"] == [100.0, 100.0, 100.0, 100.0]
    assert out["missing"] == [None, None, None, None]   # absent itemCode -> Nones


def test_fetch_requires_exactly_4_periods():
    with pytest.raises(mf.MaliTabloError, match="4 periods"):
        mf.fetch_malitablo("THYAO", [(2024, 12), (2023, 12), (2022, 12)])


def test_extract_rows_dict_and_list():
    assert mf._extract_rows({"value": _ROWS}) == _ROWS
    assert mf._extract_rows(_ROWS) == _ROWS
    assert mf._extract_rows({"d": _ROWS}) == _ROWS
    assert mf._extract_rows({"junk": 1}) == []


def test_soft_block_empty_body_raises():
    sess = MagicMock()
    sess.get.return_value = _resp(status=200, text="   ")     # blank body
    with pytest.raises(mf.MaliTabloError, match="SOFT-BLOCK"):
        mf.fetch_malitablo("THYAO", [(2024, 12), (2023, 12), (2022, 12), (2021, 12)],
                           session=sess)


def test_empty_rows_raises():
    sess = MagicMock()
    sess.get.return_value = _resp(status=200, text='{"value":[]}', payload={"value": []})
    with pytest.raises(mf.MaliTabloError, match="empty rows"):
        mf.fetch_malitablo("THYAO", [(2024, 12), (2023, 12), (2022, 12), (2021, 12)],
                           session=sess)


def test_fetch_success_returns_rows():
    sess = MagicMock()
    sess.get.return_value = _resp(payload={"value": _ROWS})
    rows = mf.fetch_malitablo("THYAO", [(2024, 12), (2023, 12), (2022, 12), (2021, 12)],
                              session=sess)
    assert len(rows) == 4
    # params built correctly (4 year/period pairs + group)
    _, kwargs = sess.get.call_args
    params = kwargs["params"]
    assert params["financialGroup"] == "XI_29"
    assert params["year1"] == "2024" and params["period4"] == "12"

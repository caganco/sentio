"""Tests for D-130: BIST DataStore authenticated file downloader.

No network calls — all HTTP mocked via monkeypatch.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(exp_offset_seconds: int = 3600) -> str:
    """Minimal JWT string with exp claim."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    exp = int((datetime.now(timezone.utc) + timedelta(seconds=exp_offset_seconds)).timestamp())
    payload_bytes = json.dumps({"sub": "test", "exp": exp}).encode()
    payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    return f"{header}.{payload}.fakesig"


def _make_session_json(
    tmp_path: Path,
    captured_offset_days: int = 0,
    jwt_offset_seconds: int = 3600,
) -> Path:
    """Write datastore_session.json to tmp_path, return path."""
    captured_at = (
        datetime.now(timezone.utc) - timedelta(days=captured_offset_days)
    ).isoformat()
    token = _make_jwt(jwt_offset_seconds)
    data = {
        "captured_at": captured_at,
        "x_auth_token": token,
        "cookies": {"token": token, "sid": "sess123"},
        "_raw_cookies": [
            {"name": "token", "value": token, "domain": ".borsaistanbul.com",
             "path": "/", "expires": -1, "httpOnly": False, "secure": True, "sameSite": "Lax"},
            {"name": "sid", "value": "sess123", "domain": "datastore.borsaistanbul.com",
             "path": "/", "expires": -1, "httpOnly": True, "secure": False, "sameSite": "Lax"},
        ],
    }
    path = tmp_path / "datastore_session.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# TestDatastoreSession
# ---------------------------------------------------------------------------

class TestDatastoreSession:
    def test_load_reads_raw_cookies(self, tmp_path):
        """_raw_cookies listesini cookies dict'e dogru cevirir."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        assert "token" in s.cookies
        assert "sid" in s.cookies
        assert s.cookies["sid"] == "sess123"

    def test_load_sets_x_auth_token(self, tmp_path):
        """x_auth_token alani yukleniyor."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        assert s.x_auth_token.count(".") == 2  # JWT formatinda

    def test_is_valid_fresh_session(self, tmp_path):
        """captured_at bugun, JWT exp gelecekte -> is_valid() True."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path, captured_offset_days=0, jwt_offset_seconds=3600)
        s = DatastoreSession(path)
        assert s.is_valid() is True

    def test_is_valid_stale_age(self, tmp_path, caplog):
        """captured_at 26 gun once -> is_valid() False + WARNING log."""
        import logging
        from src.data.bist_datastore_client import DatastoreSession

        # 26 gun eski session ama JWT exp'i gelecekte
        path = _make_session_json(tmp_path, captured_offset_days=26, jwt_offset_seconds=3600)
        s = DatastoreSession(path)
        with caplog.at_level(logging.WARNING, logger="src.data.bist_datastore_client"):
            result = s.is_valid()
        assert result is False
        assert any("gun eski" in r.message or "MAX_AGE" in r.message or "eski" in r.message
                   for r in caplog.records)

    def test_is_valid_expired_jwt(self, tmp_path, caplog):
        """JWT exp gecmiste -> is_valid() False + WARNING log."""
        import logging
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path, captured_offset_days=0, jwt_offset_seconds=-3600)
        s = DatastoreSession(path)
        with caplog.at_level(logging.WARNING, logger="src.data.bist_datastore_client"):
            result = s.is_valid()
        assert result is False
        assert any("suresi dolmus" in r.message or "expired" in r.message.lower()
                   for r in caplog.records)

    def test_missing_file_raises(self, tmp_path):
        """Dosya yok -> FileNotFoundError."""
        from src.data.bist_datastore_client import DatastoreSession

        with pytest.raises(FileNotFoundError):
            DatastoreSession(tmp_path / "nonexistent.json")

    def test_inject_adds_cookies_and_header(self, tmp_path):
        """inject_into() cookies.update() + Authorization + x-auth-token header ekler."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        req_session = requests.Session()
        s.inject_into(req_session)
        assert req_session.cookies.get("sid") == "sess123"
        assert "Authorization" in req_session.headers
        assert req_session.headers["Authorization"].startswith("Bearer ")
        assert "x-auth-token" in req_session.headers
        assert req_session.headers["x-auth-token"] == s.x_auth_token

    def test_decode_jwt_exp_future(self, tmp_path):
        """JWT decode: gelecek exp -> token_exp gelecekte."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path, jwt_offset_seconds=7200)
        s = DatastoreSession(path)
        assert s._token_exp is not None
        assert s._token_exp > datetime.now(timezone.utc)

    def test_decode_jwt_exp_past(self, tmp_path):
        """JWT decode: gecmis exp -> token_exp gecmiste."""
        from src.data.bist_datastore_client import DatastoreSession

        path = _make_session_json(tmp_path, jwt_offset_seconds=-3600)
        s = DatastoreSession(path)
        assert s._token_exp is not None
        assert s._token_exp < datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# TestDatastoreFileIndex
# ---------------------------------------------------------------------------

class TestDatastoreFileIndex:
    def _make_mock_response(self, status_code: int, json_data=None, content_type="application/json"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = status_code < 400
        resp.headers = {"Content-Type": content_type}
        if json_data is not None:
            resp.json.return_value = json_data
        else:
            resp.json.side_effect = ValueError("no json")
        return resp

    def test_list_files_parses_json(self, tmp_path, monkeypatch):
        """200 JSON {items:[...]} -> list[DatastoreFile], productTypeId filtresi."""
        from src.data.bist_datastore_client import DatastoreFileIndex, DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        index = DatastoreFileIndex(s)

        files_data = [
            {"referenceId": "6672666", "fileName": "yabanci202604.zip", "productTypeId": 3153},
            {"referenceId": "6626435", "fileName": "yabanci202603.zip", "productTypeId": 3153},
            {"referenceId": "9999999", "fileName": "other202603.zip",   "productTypeId": 9999},
        ]
        mock_resp = self._make_mock_response(200, {"items": files_data})
        monkeypatch.setattr(index._session, "get", lambda *a, **kw: mock_resp)

        result = index.list_files(3153)
        assert len(result) == 2
        assert result[0].file_id == "6672666"
        assert result[0].file_format == "zip"
        assert result[1].data_date == date(2026, 3, 1)

    def test_list_files_non_json_raises_expired(self, tmp_path, monkeypatch):
        """Content-Type: text/html -> DatastoreSessionExpiredError (session redirect)."""
        from src.data.bist_datastore_client import (
            DatastoreFileIndex,
            DatastoreSession,
            DatastoreSessionExpiredError,
        )

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        index = DatastoreFileIndex(s)

        mock_resp = self._make_mock_response(200, content_type="text/html; charset=utf-8")
        monkeypatch.setattr(index._session, "get", lambda *a, **kw: mock_resp)

        with pytest.raises(DatastoreSessionExpiredError):
            index.list_files(3153)

    def test_list_files_401_raises(self, tmp_path, monkeypatch):
        """401 -> DatastoreSessionExpiredError."""
        from src.data.bist_datastore_client import (
            DatastoreFileIndex,
            DatastoreSession,
            DatastoreSessionExpiredError,
        )

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        index = DatastoreFileIndex(s)

        mock_resp = self._make_mock_response(401, content_type="application/json")
        monkeypatch.setattr(index._session, "get", lambda *a, **kw: mock_resp)

        with pytest.raises(DatastoreSessionExpiredError):
            index.list_files(3153)

    def test_list_files_network_error_returns_empty(self, tmp_path, monkeypatch):
        """Network hatasi -> bos liste, exception yok."""
        from src.data.bist_datastore_client import DatastoreFileIndex, DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        index = DatastoreFileIndex(s)

        def _raise(*a, **kw):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr(index._session, "get", _raise)
        result = index.list_files(3153)
        assert result == []


# ---------------------------------------------------------------------------
# TestDatastoreDownloader
# ---------------------------------------------------------------------------

class TestDatastoreDownloader:
    def _setup(self, tmp_path):
        from src.data.bist_datastore_client import DatastoreDownloader, DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        dl = DatastoreDownloader(s, rate_limit_sec=0.0)
        return dl

    def test_download_file_writes_to_disk(self, tmp_path, monkeypatch):
        """200 binary response -> dosya disk'e yazildi, Path donduruldu."""
        dl = self._setup(tmp_path)

        content = b"PK\x03\x04fake_xlsx_content"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.iter_content = lambda chunk_size=65536: iter([content])
        monkeypatch.setattr(dl._req_session, "get", lambda *a, **kw: mock_resp)

        dest = tmp_path / "test.xlsx"
        result = dl.download_file("abc123", dest)
        assert result == dest
        assert dest.exists()
        assert dest.read_bytes() == content

    def test_download_skips_existing(self, tmp_path, monkeypatch):
        """Dosya varsa HTTP istegi yapilmaz."""
        from src.data.bist_datastore_client import DatastoreFile

        dl = self._setup(tmp_path)

        existing = tmp_path / "YabanciIslem_2026-04.xlsx"
        existing.write_bytes(b"already here")

        call_count = {"n": 0}

        def _get(*a, **kw):
            call_count["n"] += 1
            return MagicMock()

        monkeypatch.setattr(dl._req_session, "get", _get)

        files = [DatastoreFile("id1", existing.name, date(2026, 4, 1), "xlsx")]
        monkeypatch.setattr(dl._index, "list_files", lambda pid: files)

        result = dl.download_product(3153, tmp_path)
        assert call_count["n"] == 0
        assert len(result) == 1
        assert result[0] == existing

    def test_download_401_raises(self, tmp_path, monkeypatch):
        """401 -> DatastoreSessionExpiredError."""
        from src.data.bist_datastore_client import DatastoreSessionExpiredError

        dl = self._setup(tmp_path)

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.ok = False
        monkeypatch.setattr(dl._req_session, "get", lambda *a, **kw: mock_resp)

        with pytest.raises(DatastoreSessionExpiredError):
            dl.download_file("bad_id", tmp_path / "x.xlsx")

    def test_rate_limiting_between_downloads(self, tmp_path, monkeypatch):
        """2 dosya indiriminde time.sleep cagrilir."""
        from src.data.bist_datastore_client import DatastoreDownloader, DatastoreFile, DatastoreSession

        path = _make_session_json(tmp_path)
        s = DatastoreSession(path)
        dl = DatastoreDownloader(s, rate_limit_sec=0.05)

        content = b"data"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.iter_content = lambda chunk_size=65536: iter([content])
        monkeypatch.setattr(dl._req_session, "get", lambda *a, **kw: mock_resp)

        files = [
            DatastoreFile("id1", "file_2026-04.xlsx", date(2026, 4, 1), "xlsx"),
            DatastoreFile("id2", "file_2026-03.xlsx", date(2026, 3, 1), "xlsx"),
        ]
        monkeypatch.setattr(dl._index, "list_files", lambda pid: files)

        sleep_calls = []
        monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

        dl.download_product(3153, tmp_path)
        assert len(sleep_calls) >= 1

    def test_since_date_filter(self, tmp_path, monkeypatch):
        """since_date=2026-04-01 -> Mart 2026 dosyasi atlanir."""
        from src.data.bist_datastore_client import DatastoreFile

        dl = self._setup(tmp_path)

        content = b"data"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.ok = True
        mock_resp.iter_content = lambda chunk_size=65536: iter([content])
        monkeypatch.setattr(dl._req_session, "get", lambda *a, **kw: mock_resp)

        files = [
            DatastoreFile("id1", "file_2026-04.xlsx", date(2026, 4, 1), "xlsx"),
            DatastoreFile("id2", "file_2026-03.xlsx", date(2026, 3, 1), "xlsx"),
        ]
        monkeypatch.setattr(dl._index, "list_files", lambda pid: files)

        result = dl.download_product(3153, tmp_path, since_date=date(2026, 4, 1))
        names = [p.name for p in result]
        assert "file_2026-04.xlsx" in names
        assert "file_2026-03.xlsx" not in names


# ---------------------------------------------------------------------------
# TestThresholdConstants (Adim 1 dogrulama)
# ---------------------------------------------------------------------------

class TestLibraryPagination:
    """list_files tum sayfalari gezmeli (D-130 bug fix)."""

    def _resp(self, json_data, status=200, ct="application/json"):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = status < 400
        resp.headers = {"Content-Type": ct}
        resp.json.return_value = json_data
        return resp

    def test_list_files_walks_all_pages(self, tmp_path, monkeypatch):
        """page1 dolu (page-size kadar) -> page2 cekilir; kismi sayfada durur."""
        from src.data.bist_datastore_client import DatastoreFileIndex, DatastoreSession
        from src.signals.thresholds import DATASTORE_LIBRARY_PAGE_SIZE

        s = DatastoreSession(_make_session_json(tmp_path))
        index = DatastoreFileIndex(s)

        page1 = [
            {"referenceId": f"id{i}", "fileName": f"yabanci2026{i:02d}.zip", "productTypeId": 3153}
            for i in range(DATASTORE_LIBRARY_PAGE_SIZE)
        ]
        page2 = [{"referenceId": "last", "fileName": "yabanci_last.zip", "productTypeId": 3153}]
        pages = {1: page1, 2: page2}

        def _get(url, params=None, timeout=None):
            return self._resp(pages.get(params["page"], []))

        monkeypatch.setattr(index._session, "get", _get)
        result = index.list_files(3153)
        assert len(result) == DATASTORE_LIBRARY_PAGE_SIZE + 1
        assert result[-1].file_id == "last"

    def test_list_files_single_partial_page_stops(self, tmp_path, monkeypatch):
        """Ilk sayfa page-size'dan az -> tek istek, ikinci sayfa cekilmez."""
        from src.data.bist_datastore_client import DatastoreFileIndex, DatastoreSession

        s = DatastoreSession(_make_session_json(tmp_path))
        index = DatastoreFileIndex(s)

        calls = {"n": 0}

        def _get(url, params=None, timeout=None):
            calls["n"] += 1
            return self._resp([
                {"referenceId": "a", "fileName": "x2026.zip", "productTypeId": 3153},
            ])

        monkeypatch.setattr(index._session, "get", _get)
        result = index.list_files(3153)
        assert calls["n"] == 1
        assert len(result) == 1


class TestDatastoreCatalog:
    def _resp(self, json_data, status=200, ct="application/json"):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = status < 400
        resp.headers = {"Content-Type": ct}
        resp.json.return_value = json_data
        return resp

    def _raw(self, pid="111", price=0.0, in_lib=False, date_="01-04-2026"):
        return {
            "id": pid, "fileName": f"f{pid}.zip", "date": date_,
            "price": price, "discountPrice": price,
            "dataDefnEntity": {"description": "Yabanci Islem"},
            "inLibrary": in_lib, "createDate": date_,
            "category": "PPB", "group": "G1", "subcategory": "S1",
            "productTypeId": 3153, "period": None,
        }

    def test_list_products_parses(self, tmp_path, monkeypatch):
        from src.data.bist_datastore_client import DatastoreCatalog, DatastoreSession

        s = DatastoreSession(_make_session_json(tmp_path))
        cat = DatastoreCatalog(s)
        monkeypatch.setattr(cat._session, "get",
                            lambda *a, **kw: self._resp([self._raw("1"), self._raw("2", price=5.0)]))
        products = cat.list_products(3153)
        assert len(products) == 2
        assert products[0].reference_id == "1"
        assert products[0].is_free is True
        assert products[1].is_free is False
        assert products[0].type_name == "Yabanci Islem"

    def test_list_free_products_filters(self, tmp_path, monkeypatch):
        from src.data.bist_datastore_client import DatastoreCatalog, DatastoreSession

        s = DatastoreSession(_make_session_json(tmp_path))
        cat = DatastoreCatalog(s)
        items = [
            self._raw("free_new", price=0.0, in_lib=False),
            self._raw("free_owned", price=0.0, in_lib=True),
            self._raw("paid", price=10.0, in_lib=False),
        ]
        monkeypatch.setattr(cat._session, "get", lambda *a, **kw: self._resp(items))
        free = cat.list_free_products(3153)
        ids = [p.reference_id for p in free]
        assert ids == ["free_new"]

    def test_list_products_401_raises(self, tmp_path, monkeypatch):
        from src.data.bist_datastore_client import (
            DatastoreCatalog, DatastoreSession, DatastoreSessionExpiredError,
        )

        s = DatastoreSession(_make_session_json(tmp_path))
        cat = DatastoreCatalog(s)
        monkeypatch.setattr(cat._session, "get", lambda *a, **kw: self._resp(None, status=401))
        with pytest.raises(DatastoreSessionExpiredError):
            cat.list_products(3153)


class TestDatastoreAcquirer:
    def _customer_resp(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.ok = True
        resp.json.return_value = [{"id": 42, "name": "A", "surName": "B", "email": "a@b.c"}]
        return resp

    def _make_products(self, n, price=0.0):
        from src.data.bist_datastore_client import DatastoreProduct
        return [
            DatastoreProduct(
                reference_id=str(i), type_name="T", data_date="01-04-2026",
                price=price, in_library=False, product_type_id=3153,
                raw={"id": str(i), "price": price, "date": "01-04-2026",
                     "category": "PPB", "group": "G", "subcategory": "S",
                     "productTypeId": 3153, "createDate": "01-04-2026"},
            )
            for i in range(n)
        ]

    def _setup(self, tmp_path, batch_size=20):
        from src.data.bist_datastore_client import DatastoreAcquirer, DatastoreSession
        s = DatastoreSession(_make_session_json(tmp_path))
        return DatastoreAcquirer(s, rate_limit_sec=0.0, batch_size=batch_size)

    def test_add_free_success_204(self, tmp_path, monkeypatch):
        acq = self._setup(tmp_path)
        post_calls = []

        def _post(url, json=None, timeout=None):
            post_calls.append(json)
            r = MagicMock(); r.status_code = 204; r.ok = True
            return r

        monkeypatch.setattr(acq._req_session, "get", lambda *a, **kw: self._customer_resp())
        monkeypatch.setattr(acq._req_session, "post", _post)

        added = acq.add_free_to_library(self._make_products(3))
        assert added == 3
        assert len(post_calls) == 1
        payload = post_calls[0]
        assert payload["vPosInfo"] is None
        assert payload["senderApp"] == "DataStore"
        assert payload["customer"]["userProfileId"] == 42
        assert len(payload["products"]) == 3
        assert payload["products"][0]["referenceId"] == "0"

    def test_batching_splits_requests(self, tmp_path, monkeypatch):
        acq = self._setup(tmp_path, batch_size=2)
        post_calls = []

        def _post(url, json=None, timeout=None):
            post_calls.append(json)
            r = MagicMock(); r.status_code = 204; r.ok = True
            return r

        monkeypatch.setattr(acq._req_session, "get", lambda *a, **kw: self._customer_resp())
        monkeypatch.setattr(acq._req_session, "post", _post)
        monkeypatch.setattr(time, "sleep", lambda s: None)

        added = acq.add_free_to_library(self._make_products(5))
        assert added == 5
        assert len(post_calls) == 3  # 2 + 2 + 1
        assert [len(c["products"]) for c in post_calls] == [2, 2, 1]

    def test_rejects_paid_products(self, tmp_path):
        acq = self._setup(tmp_path)
        with pytest.raises(ValueError):
            acq.add_free_to_library(self._make_products(2, price=9.9))

    def test_409_price_conflict_raises(self, tmp_path, monkeypatch):
        acq = self._setup(tmp_path)
        monkeypatch.setattr(acq._req_session, "get", lambda *a, **kw: self._customer_resp())
        r = MagicMock(); r.status_code = 409; r.ok = False
        monkeypatch.setattr(acq._req_session, "post", lambda *a, **kw: r)
        with pytest.raises(RuntimeError, match="409"):
            acq.add_free_to_library(self._make_products(1))

    def test_add_library_401_raises_expired(self, tmp_path, monkeypatch):
        from src.data.bist_datastore_client import DatastoreSessionExpiredError
        acq = self._setup(tmp_path)
        monkeypatch.setattr(acq._req_session, "get", lambda *a, **kw: self._customer_resp())
        r = MagicMock(); r.status_code = 401; r.ok = False
        monkeypatch.setattr(acq._req_session, "post", lambda *a, **kw: r)
        with pytest.raises(DatastoreSessionExpiredError):
            acq.add_free_to_library(self._make_products(1))

    def test_empty_products_no_call(self, tmp_path, monkeypatch):
        acq = self._setup(tmp_path)
        called = {"n": 0}
        monkeypatch.setattr(acq._req_session, "post",
                            lambda *a, **kw: called.__setitem__("n", called["n"] + 1))
        assert acq.add_free_to_library([]) == 0
        assert called["n"] == 0


class TestPaymentItemHelper:
    def test_payment_item_shape(self):
        from src.data.bist_datastore_client import DatastoreProduct, _payment_item

        p = DatastoreProduct(
            reference_id="9", type_name="Yabanci", data_date="15-03-2026",
            price=0.0, in_library=False, product_type_id=3153,
            raw={"id": "9", "price": 0.0, "category": "PPB", "group": "G",
                 "subcategory": "S", "productTypeId": 3153, "createDate": "15-03-2026"},
        )
        item = _payment_item(p)
        assert item["referenceId"] == "9"
        assert item["type"] == 0
        assert item["price"] == 0.0
        assert item["categoryCode"] == "PPB"
        assert item["subCategoryCode"] == "S"
        assert isinstance(item["productDate"], int)  # epoch ms
        assert item["name"] == "15-03-2026 - Yabanci"


class TestDatastoreThresholdConstants:
    def test_constants_exist(self):
        from src.signals.thresholds import (
            DATASTORE_PRODUCT_FOREIGN,
            DATASTORE_PRODUCT_PRICES,
            DATASTORE_PRODUCT_SHORT,
            DATASTORE_RATE_LIMIT_SEC,
            DATASTORE_SESSION_FILE,
            DATASTORE_SESSION_MAX_AGE_DAYS,
        )
        assert DATASTORE_SESSION_FILE == "datastore_session.json"
        assert DATASTORE_SESSION_MAX_AGE_DAYS == 25
        assert DATASTORE_PRODUCT_FOREIGN == 3153
        assert DATASTORE_PRODUCT_SHORT == 3155
        assert DATASTORE_PRODUCT_PRICES == 3156
        assert DATASTORE_RATE_LIMIT_SEC == 2.0

    def test_rate_limit_positive(self):
        from src.signals.thresholds import DATASTORE_RATE_LIMIT_SEC
        assert DATASTORE_RATE_LIMIT_SEC > 0

    def test_max_age_reasonable(self):
        from src.signals.thresholds import DATASTORE_SESSION_MAX_AGE_DAYS
        assert 7 <= DATASTORE_SESSION_MAX_AGE_DAYS <= 31


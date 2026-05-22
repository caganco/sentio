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


"""BIST DataStore authenticated file downloader (D-130).

Auth: datastore_session.json (_raw_cookies + x_auth_token), monthly manual re-login.
CAPTCHA prevents full automation; capture_datastore_session.py handles login.
"""
from __future__ import annotations

import base64
import json as _json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from src.signals.thresholds import (
    DATASTORE_PRODUCT_FOREIGN,
    DATASTORE_PRODUCT_SHORT,
    DATASTORE_RATE_LIMIT_SEC,
    DATASTORE_SESSION_FILE,
    DATASTORE_SESSION_MAX_AGE_DAYS,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://datastore.borsaistanbul.com"


class DatastoreSessionExpiredError(RuntimeError):
    """JWT suresi dolmus veya session dosyasi DATASTORE_SESSION_MAX_AGE_DAYS'den eski."""


# ---------------------------------------------------------------------------
# DatastoreFile
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatastoreFile:
    file_id: str
    name: str
    data_date: date | None
    file_format: str   # "xlsx" | "xls" | "csv"
    url: str | None = None


# ---------------------------------------------------------------------------
# DatastoreSession
# ---------------------------------------------------------------------------

class DatastoreSession:
    """datastore_session.json'dan oturum yukler, gecerlilik kontrolu yapar."""

    def __init__(self, session_file: Path | str = DATASTORE_SESSION_FILE) -> None:
        path = Path(session_file)
        if not path.exists():
            raise FileNotFoundError(
                f"DataStore session dosyasi bulunamadi: {path}\n"
                "Cozum: python scripts/capture_datastore_session.py"
            )
        raw = _json.loads(path.read_text(encoding="utf-8"))
        self._captured_at: datetime = datetime.fromisoformat(raw["captured_at"])
        self.x_auth_token: str = raw.get("x_auth_token", "")
        self._raw_cookies: list[dict] = raw.get("_raw_cookies", [])
        self.cookies: dict[str, str] = {
            c["name"]: c["value"] for c in self._raw_cookies
        }
        self._token_exp: datetime | None = self._decode_jwt_exp(
            self.cookies.get("token", "")
        )

    @classmethod
    def load(cls, session_file: Path | str | None = None) -> "DatastoreSession":
        return cls(session_file or DATASTORE_SESSION_FILE)

    def is_valid(self) -> bool:
        """
        Iki kontrol:
        1. Dosya yasi < DATASTORE_SESSION_MAX_AGE_DAYS
        2. JWT (token cookie) exp > now
        """
        now = datetime.now(timezone.utc)
        captured = self._captured_at
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)

        age_days = (now - captured).days
        if age_days >= DATASTORE_SESSION_MAX_AGE_DAYS:
            logger.warning(
                "DataStore session %d gun eski (max=%d) — "
                "Cozum: python scripts/capture_datastore_session.py",
                age_days, DATASTORE_SESSION_MAX_AGE_DAYS,
            )
            return False

        if self._token_exp is not None and now >= self._token_exp:
            logger.warning(
                "DataStore JWT suresi dolmus (%s) — "
                "Cozum: python scripts/capture_datastore_session.py",
                self._token_exp.isoformat(),
            )
            return False

        return True

    def inject_into(self, session: requests.Session) -> None:
        """_raw_cookies'i requests.Session'a inject et + Authorization header."""
        session.cookies.update(self.cookies)
        if self.x_auth_token:
            session.headers.update({"Authorization": f"Bearer {self.x_auth_token}"})

    @staticmethod
    def _decode_jwt_exp(token: str) -> datetime | None:
        """JWT payload'dan exp claim'i cikart (stdlib only, dogrulama yok)."""
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload_b64 = parts[1]
            padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
            decoded = _json.loads(base64.b64decode(padded))
            exp_ts = decoded.get("exp")
            if exp_ts is None:
                return None
            return datetime.fromtimestamp(float(exp_ts), tz=timezone.utc)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# DatastoreFileIndex
# ---------------------------------------------------------------------------

class DatastoreFileIndex:
    """Urun tipi bazinda BIST DataStore dosya listesi."""

    def __init__(self, session: DatastoreSession, timeout: float = 20.0) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, */*",
        })
        session.inject_into(self._session)
        self._timeout = timeout

    def list_files(self, product_type_id: int) -> list[DatastoreFile]:
        """
        GET /api/library/files?productTypeId={id}
        200 + JSON -> list[DatastoreFile]
        401 -> DatastoreSessionExpiredError
        JSON gelmezse (HTML, 403, 404) -> WARNING + bos liste
        """
        url = f"{_BASE_URL}/api/library/files"
        try:
            resp = self._session.get(
                url,
                params={"productTypeId": product_type_id},
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.warning("DataStore list_files network hatasi: %s", exc)
            return []

        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore 401 — session suresi dolmus. "
                "Cozum: python scripts/capture_datastore_session.py"
            )

        ct = resp.headers.get("Content-Type", "")
        if not resp.ok or "json" not in ct.lower():
            logger.warning(
                "DataStore list_files: HTTP %d, Content-Type=%r — bos liste donuluyor",
                resp.status_code, ct,
            )
            return []

        try:
            data = resp.json()
        except Exception as exc:
            logger.warning("DataStore list_files: JSON parse hatasi — %s", exc)
            return []

        files_raw = data if isinstance(data, list) else data.get("files", data.get("data", []))
        result: list[DatastoreFile] = []
        for f in files_raw:
            try:
                file_id = str(f.get("id", f.get("fileId", "")))
                name = str(f.get("name", f.get("fileName", file_id)))
                fmt = _guess_format(name)
                data_date = _extract_date_from_name(name)
                url_val = f.get("url") or f.get("downloadUrl")
                result.append(DatastoreFile(
                    file_id=file_id,
                    name=name,
                    data_date=data_date,
                    file_format=fmt,
                    url=url_val,
                ))
            except Exception as exc:
                logger.debug("DataStore list_files: dosya parse atla — %s", exc)
        return result


# ---------------------------------------------------------------------------
# DatastoreDownloader
# ---------------------------------------------------------------------------

class DatastoreDownloader:
    """Dosya indirme + idempotent kayit."""

    def __init__(
        self,
        session: DatastoreSession,
        timeout: float = 30.0,
        rate_limit_sec: float = DATASTORE_RATE_LIMIT_SEC,
    ) -> None:
        self._ds_session = session
        self._timeout = timeout
        self._rate_limit_sec = rate_limit_sec
        self._req_session = requests.Session()
        self._req_session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        })
        session.inject_into(self._req_session)
        self._index = DatastoreFileIndex(session)

    def download_product(
        self,
        product_type_id: int,
        output_dir: Path,
        since_date: date | None = None,
    ) -> list[Path]:
        """
        1. list_files(product_type_id)
        2. since_date filtrele
        3. Idempotent indirme (mevcut skip) + rate limit
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files = self._index.list_files(product_type_id)
        if not files:
            logger.warning("DataStore urun %d: dosya listesi bos", product_type_id)
            return []

        downloaded: list[Path] = []
        first = True
        for f in files:
            if since_date is not None and f.data_date is not None and f.data_date < since_date:
                logger.debug("DataStore: %s atlandi (since_date filtresi)", f.name)
                continue

            dest = output_dir / f.name
            if dest.exists():
                logger.info("DataStore: %s mevcut, atlandi", f.name)
                downloaded.append(dest)
                continue

            if not first:
                time.sleep(self._rate_limit_sec)
            first = False

            try:
                path = self.download_file(f.file_id, dest)
                downloaded.append(path)
            except DatastoreSessionExpiredError:
                raise
            except Exception as exc:
                logger.error("ALERT DataStore: %s indirme hatasi — %s", f.name, exc)

        return downloaded

    def download_file(self, file_id: str, dest: Path) -> Path:
        """GET /api/file/{file_id} -> dest'e yaz."""
        url = f"{_BASE_URL}/api/file/{file_id}"
        try:
            resp = self._req_session.get(url, timeout=self._timeout, stream=True)
        except Exception as exc:
            raise RuntimeError(f"ALERT DataStore download_file network hatasi: {exc}") from exc

        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore 401 — session suresi dolmus. "
                "Cozum: python scripts/capture_datastore_session.py"
            )
        if not resp.ok:
            raise RuntimeError(
                f"ALERT DataStore download_file HTTP {resp.status_code} — {url}"
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                fh.write(chunk)

        logger.info("DataStore: %s indirildi (%d bytes)", dest.name, dest.stat().st_size)
        return dest


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------

import re as _re

_DATE_RE = _re.compile(r"(\d{4})[-_](\d{2})")


def _extract_date_from_name(name: str) -> date | None:
    """Dosya isminden YYYY-MM tarihini cikar. Bulunamazsa None."""
    m = _DATE_RE.search(name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), 1)
    except ValueError:
        return None


def _guess_format(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".xlsx"):
        return "xlsx"
    if lower.endswith(".xls"):
        return "xls"
    if lower.endswith(".csv"):
        return "csv"
    return "xlsx"

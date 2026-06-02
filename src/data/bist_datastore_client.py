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
    DATASTORE_ADD_LIBRARY_BATCH_SIZE,
    DATASTORE_CATALOG_PAGE_SIZE,
    DATASTORE_LIBRARY_PAGE_SIZE,
    DATASTORE_RATE_LIMIT_SEC,
    DATASTORE_SENDER_APP,
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
        """_raw_cookies'i requests.Session'a inject et + auth headers."""
        session.cookies.update(self.cookies)
        if self.x_auth_token:
            session.cookies.set("token", self.x_auth_token)
            sid = self.cookies.get("sid", "")
            if sid:
                session.cookies.set("sid", sid)
            session.headers.update({
                "Authorization": f"Bearer {self.x_auth_token}",
                "x-auth-token": self.x_auth_token,
            })

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
        Kutuphanedeki TUM sayfalari gez (GET /api/library?page=N&page-size=...).

        D-130 bug'i: tek sayfa cekiliyordu, 100+ urunde "alinanlar gozukmuyor".
        Artik bos/eksik sayfa gelene kadar page artirilir, productTypeId ile filtreli.
        401 -> DatastoreSessionExpiredError. HTML/JSON-disi -> DatastoreSessionExpiredError.
        """
        result: list[DatastoreFile] = []
        page = 1
        while True:
            raw = self._fetch_library_page(page)
            if not raw:
                break
            for f in raw:
                try:
                    pid = f.get("productTypeId") or (f.get("productType") or {}).get("id")
                    if pid is not None and int(pid) != product_type_id:
                        continue
                    file_id = str(f.get("referenceId", f.get("fileId", f.get("id", ""))))
                    name = str(f.get("fileName", f.get("name", file_id)))
                    result.append(DatastoreFile(
                        file_id=file_id,
                        name=name,
                        data_date=_extract_date_from_name(name),
                        file_format=_guess_format(name),
                        url=f.get("url") or f.get("downloadUrl"),
                    ))
                except Exception as exc:
                    logger.debug("DataStore list_files: dosya parse atla — %s", exc)
            if len(raw) < DATASTORE_LIBRARY_PAGE_SIZE:
                break
            page += 1
        return result

    def _fetch_library_page(self, page: int) -> list[dict]:
        """Tek bir /api/library sayfasini ham dict listesi olarak dondur."""
        try:
            resp = self._session.get(
                f"{_BASE_URL}/api/library",
                params={"page": page, "page-size": DATASTORE_LIBRARY_PAGE_SIZE},
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.warning("DataStore list_files network hatasi (page %d): %s", page, exc)
            return []

        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore 401 — session suresi dolmus. "
                "Cozum: python scripts/capture_datastore_session.py"
            )

        ct = resp.headers.get("Content-Type", "")
        if "html" in ct.lower():
            raise DatastoreSessionExpiredError(
                f"DataStore HTML yaniti (HTTP {resp.status_code}) — session suresi dolmus veya redirect. "
                "Cozum: python scripts/capture_datastore_session.py"
            )
        if not resp.ok or "json" not in ct.lower():
            raise DatastoreSessionExpiredError(
                f"DataStore list_files: HTTP {resp.status_code}, "
                f"Content-Type={ct!r} — session suresi dolmus olabilir. "
                "Cozum: python scripts/capture_datastore_session.py"
            )

        try:
            data = resp.json()
        except Exception as exc:
            logger.warning("DataStore list_files: JSON parse hatasi — %s", exc)
            return []

        return (
            data if isinstance(data, list)
            else data.get("items", data.get("files", data.get("data", [])))
        )


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
# DatastoreProduct — katalogtaki alinabilir urun (dosya)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatastoreProduct:
    """/api/product-type/{id}/products yanitindaki tek bir alinabilir dosya.

    add-library payload'i ham `raw` dict'ten birebir uretilir (alan kaybi yok).
    """
    reference_id: str          # API: id
    type_name: str             # API: dataDefnEntity.description
    data_date: str | None      # API: date (DD-MM-YYYY)
    price: float               # API: price (0 -> ucretsiz)
    in_library: bool           # API: inLibrary (zaten kutuphanede mi)
    product_type_id: int | None
    raw: dict

    @property
    def is_free(self) -> bool:
        return float(self.price or 0.0) <= 0.0


def _parse_product(raw: dict, default_product_type_id: int) -> DatastoreProduct:
    rid = str(raw.get("id", raw.get("referenceId", "")))
    defn = raw.get("dataDefnEntity") or {}
    type_name = str(defn.get("description") or raw.get("typeName") or rid)
    try:
        price = float(raw.get("price") or 0.0)
    except (TypeError, ValueError):
        price = 0.0
    ptid = raw.get("productTypeId") or default_product_type_id
    return DatastoreProduct(
        reference_id=rid,
        type_name=type_name,
        data_date=raw.get("date"),
        price=price,
        in_library=bool(raw.get("inLibrary")),
        product_type_id=int(ptid) if ptid is not None else None,
        raw=raw,
    )


# ---------------------------------------------------------------------------
# DatastoreCatalog — alinabilir urunleri listele (henuz satin alinmamis)
# ---------------------------------------------------------------------------

class DatastoreCatalog:
    """Urun-tipi bazinda alinabilir dosya listesi (GET /api/product-type/{id}/products)."""

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

    def list_products(
        self,
        product_type_id: int,
        since_date: date | None = None,
        until_date: date | None = None,
    ) -> list[DatastoreProduct]:
        """Urun-tipindeki tum alinabilir dosyalari sayfalari gezerek dondur.

        since_date/until_date -> d1/d2 (epoch ms) tarih filtresi.
        401/HTML -> DatastoreSessionExpiredError.
        """
        d1 = _epoch_ms(since_date) if since_date else None
        d2 = _epoch_ms(until_date) if until_date else None

        result: list[DatastoreProduct] = []
        page = 1
        while True:
            raw_items = self._fetch_products_page(product_type_id, page, d1, d2)
            if not raw_items:
                break
            for raw in raw_items:
                try:
                    result.append(_parse_product(raw, product_type_id))
                except Exception as exc:
                    logger.debug("DataStore list_products: parse atla — %s", exc)
            if len(raw_items) < DATASTORE_CATALOG_PAGE_SIZE:
                break
            page += 1
        return result

    def list_free_products(
        self,
        product_type_id: int,
        since_date: date | None = None,
        until_date: date | None = None,
        include_owned: bool = False,
    ) -> list[DatastoreProduct]:
        """Sadece ucretsiz (price==0) urunler; varsayilan olarak kutuphanede
        olmayanlar (include_owned=False -> inLibrary olanlar elenir)."""
        return [
            p for p in self.list_products(product_type_id, since_date, until_date)
            if p.is_free and (include_owned or not p.in_library)
        ]

    def _fetch_products_page(
        self, product_type_id: int, page: int, d1: int | None, d2: int | None
    ) -> list[dict]:
        params: dict = {"page": page, "page-size": DATASTORE_CATALOG_PAGE_SIZE}
        if d1 is not None:
            params["d1"] = d1
        if d2 is not None:
            params["d2"] = d2
        try:
            resp = self._session.get(
                f"{_BASE_URL}/api/product-type/{product_type_id}/products",
                params=params,
                timeout=self._timeout,
            )
        except Exception as exc:
            logger.warning("DataStore list_products network hatasi (page %d): %s", page, exc)
            return []

        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore 401 — session suresi dolmus. "
                "Cozum: python scripts/capture_datastore_session.py"
            )
        ct = resp.headers.get("Content-Type", "")
        if "html" in ct.lower() or not resp.ok or "json" not in ct.lower():
            raise DatastoreSessionExpiredError(
                f"DataStore list_products: HTTP {resp.status_code}, Content-Type={ct!r} — "
                "session suresi dolmus olabilir. "
                "Cozum: python scripts/capture_datastore_session.py"
            )
        try:
            data = resp.json()
        except Exception as exc:
            logger.warning("DataStore list_products: JSON parse hatasi — %s", exc)
            return []
        return (
            data if isinstance(data, list)
            else data.get("items", data.get("products", data.get("data", [])))
        )


# ---------------------------------------------------------------------------
# DatastoreAcquirer — ucretsiz urunleri kutuphaneye ekle (checkout baypas)
# ---------------------------------------------------------------------------

class DatastoreAcquirer:
    """Ucretsiz urunleri POST /api/add-library ile dogrudan kutuphaneye ekler.

    Sepet/odeme UI'i baypas edilir (sepet zaten client-side). Buyuk listeler
    cart-size bug'ini yenmek icin batch'lere bolunur. Basari = HTTP 204.
    """

    def __init__(
        self,
        session: DatastoreSession,
        timeout: float = 30.0,
        rate_limit_sec: float = DATASTORE_RATE_LIMIT_SEC,
        batch_size: int = DATASTORE_ADD_LIBRARY_BATCH_SIZE,
    ) -> None:
        self._timeout = timeout
        self._rate_limit_sec = rate_limit_sec
        self._batch_size = max(1, batch_size)
        self._req_session = requests.Session()
        self._req_session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, */*",
            "Content-Type": "application/json",
        })
        session.inject_into(self._req_session)

    def fetch_customer(self) -> dict:
        """GET /api/payment-profile -> add-library customer blogu.

        Ilk profil kullanilir. Profilin ham alanlari customer'a tasinir;
        userProfileId = profil id. Profil yoksa RuntimeError.
        """
        try:
            resp = self._req_session.get(
                f"{_BASE_URL}/api/payment-profile", timeout=self._timeout
            )
        except Exception as exc:
            raise RuntimeError(f"ALERT DataStore payment-profile network hatasi: {exc}") from exc
        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore 401 — session suresi dolmus. "
                "Cozum: python scripts/capture_datastore_session.py"
            )
        if not resp.ok:
            raise RuntimeError(f"ALERT DataStore payment-profile HTTP {resp.status_code}")
        profiles = resp.json()
        if not profiles:
            raise RuntimeError(
                "DataStore: kullanici profil yok — DataStore'da once bir "
                "fatura/kullanici profili tanimlayin."
            )
        p = profiles[0]
        return {
            "id": None,
            "name": p.get("name"),
            "surName": p.get("surName") or p.get("surname"),
            "email": p.get("email"),
            "ip": None,
            "address": p.get("address"),
            "phone": p.get("phone"),
            "tckn": p.get("tckn"),
            "type": p.get("type"),
            "university": None,
            "faculty": None,
            "title": None,
            "taxOffice": None,
            "taxNumber": None,
            "academic": False,
            "userProfileId": p.get("id"),
        }

    def add_free_to_library(
        self,
        products: list[DatastoreProduct],
        customer: dict | None = None,
    ) -> int:
        """Ucretsiz urunleri batch'ler halinde add-library ile ekle.

        Donen: kutuphaneye eklenen toplam urun sayisi.
        Ucretsiz olmayan urun verilirse ValueError.
        """
        if not products:
            return 0
        paid = [p for p in products if not p.is_free]
        if paid:
            raise ValueError(
                f"add_free_to_library yalnizca ucretsiz urun kabul eder; "
                f"{len(paid)} ucretli urun verildi (orn. {paid[0].reference_id})."
            )
        if customer is None:
            customer = self.fetch_customer()

        added = 0
        batches = [
            products[i:i + self._batch_size]
            for i in range(0, len(products), self._batch_size)
        ]
        for idx, batch in enumerate(batches):
            if idx > 0:
                time.sleep(self._rate_limit_sec)
            payload = {
                "orderId": None,
                "vPosInfo": None,
                "customer": customer,
                "products": [_payment_item(p) for p in batch],
                "senderApp": DATASTORE_SENDER_APP,
            }
            self._post_add_library(payload, len(batch))
            added += len(batch)
            logger.info(
                "DataStore add-library: batch %d/%d eklendi (%d urun)",
                idx + 1, len(batches), len(batch),
            )
        return added

    def _post_add_library(self, payload: dict, n_items: int) -> None:
        try:
            resp = self._req_session.post(
                f"{_BASE_URL}/api/add-library",
                json=payload,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise RuntimeError(f"ALERT DataStore add-library network hatasi: {exc}") from exc

        if resp.status_code == 204:
            return
        if resp.status_code == 401:
            raise DatastoreSessionExpiredError(
                "DataStore add-library 401 — session suresi dolmus veya akademik "
                "profil gerekli. Cozum: python scripts/capture_datastore_session.py"
            )
        if resp.status_code == 409:
            # priceConflict: urun aslinda ucretli ya da fiyat degismis
            raise RuntimeError(
                "ALERT DataStore add-library 409 (priceConflict) — urun ucretsiz "
                "olmayabilir ya da fiyati degismis. add-library ucretsiz yol calismiyor."
            )
        raise RuntimeError(
            f"ALERT DataStore add-library HTTP {resp.status_code} ({n_items} urun) — "
            f"beklenen 204."
        )


# ---------------------------------------------------------------------------
# Yardimci fonksiyonlar
# ---------------------------------------------------------------------------

import re as _re

_DATE_RE = _re.compile(r"(?<!\d)(\d{4})[-_]?(\d{2})(?!\d)")


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
    if lower.endswith(".zip"):
        return "zip"
    return "xlsx"


def _epoch_ms(d: date) -> int:
    """date -> epoch milisaniye (Ember 'moment(...).valueOf()' karsiligi)."""
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)


def _ddmmyyyy_to_epoch_ms(value) -> int | None:
    """'DD-MM-YYYY' string -> epoch ms; parse edilemezse None."""
    if not value or not isinstance(value, str):
        return None
    try:
        d = datetime.strptime(value.strip(), "%d-%m-%Y")
        return int(d.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        return None


def _payment_item(p: "DatastoreProduct") -> dict:
    """DatastoreProduct -> add-library products[] girdisi.

    Ember extractBasketItem -> extractPaymentItems zincirini birebir taklit eder;
    ham alanlar (category/group/subcategory/period/createDate) raw'dan tasinir.
    """
    r = p.raw
    return {
        "referenceId": p.reference_id,
        "name": f"{p.data_date} - {p.type_name}" if p.data_date else p.type_name,
        "type": 0,  # item-type-enum.productNumeric
        "price": float(r.get("price") or 0.0),
        "productDate": _ddmmyyyy_to_epoch_ms(p.data_date),
        "categoryCode": r.get("category", r.get("categoryCode")),
        "groupCode": r.get("group", r.get("groupCode")),
        "subCategoryCode": r.get("subcategory", r.get("subcategoryCode")),
        "productTypeId": p.product_type_id,
        "period": r.get("period"),
        "createDate": r.get("createDate"),
        "fileCreateDate": _ddmmyyyy_to_epoch_ms(r.get("createDate") or r.get("fileCreateDate")),
    }

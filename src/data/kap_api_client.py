"""MKK VYK API thin HTTP wrapper. D-170.

Auth: Bearer (production) / Basic (test env — "user:pass" format).
Rate limit: 1 istek/saniye (saygili; MKK politikasi).

Endpoint'ler (canli test API teyitli):
    GET /api/vyk/lastDisclosureIndex          → {"lastDisclosureIndex": N}
    GET /api/vyk/members                      → [{"id","title","stockCode","memberType"}]
    GET /api/vyk/disclosures
        ?disclosureIndex={N}&disclosureClass={FR|ODA}[&companyId={M}]
    GET /api/vyk/disclosureDetail/{index}?fileType=data

Env:
    MKK_VYK_BASE_URL — API base URL
    MKK_VYK_TOKEN    — Bearer token (prod) veya "user:pass" (test/Basic)

Kullanim:
    from src.data.kap_api_client import KapApiClient, KapApiError
    client = KapApiClient(base_url, token, auth_type="bearer")
    last   = client.get_last_index()
    items  = client.get_disclosures(start_index=0, disclosure_class="FR")
    detail = client.get_disclosure_detail(12345)
"""
from __future__ import annotations

import base64
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15
_RATE_LIMIT_SLEEP = 1.0


class KapApiError(RuntimeError):
    """MKK VYK API'den hata veya beklenmedik yanit."""


class KapApiClient:
    """MKK VYK API istemcisi. D-170.

    Args:
        base_url:  API koku (ornek: https://apigwdev.mkk.com.tr)
        token:     Bearer token (prod) veya "user:pass" (Basic/test)
        auth_type: "bearer" (varsayilan) veya "basic"
    """

    def __init__(self, base_url: str, token: str, auth_type: str = "bearer") -> None:
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        if auth_type == "bearer":
            self._session.headers["Authorization"] = f"Bearer {token}"
        else:
            encoded = base64.b64encode(token.encode()).decode()
            self._session.headers["Authorization"] = f"Basic {encoded}"

    # ------------------------------------------------------------------
    def get_last_index(self) -> int:
        """Son aciklama indeksini dondurur.

        Returns:
            int — en yeni disclosure index numarasi.

        Raises:
            KapApiError: API hatasi veya beklenmedik yanit.
        """
        time.sleep(_RATE_LIMIT_SLEEP)
        resp = self._session.get(
            f"{self._base}/api/vyk/lastDisclosureIndex",
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise KapApiError(f"get_last_index: HTTP {resp.status_code}: {resp.text[:200]}")
        return int(resp.json()["lastDisclosureIndex"])

    # ------------------------------------------------------------------
    def get_members(self) -> list[dict[str, Any]]:
        """Uye (sirket) listesini dondurur. D-172.

        Returns:
            list[dict] — her uye {id, title, stockCode, memberType[, kfifUrl]}.
            id = companyId (str), stockCode = BIST ticker.

        Raises:
            KapApiError: API hatasi.
        """
        time.sleep(_RATE_LIMIT_SLEEP)
        resp = self._session.get(
            f"{self._base}/api/vyk/members",
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise KapApiError(f"get_members: HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    # ------------------------------------------------------------------
    def get_disclosures(
        self,
        start_index: int,
        disclosure_class: str,
        company_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """disclosureIndex'ten itibaren bildirimleri getirir.

        Args:
            start_index:       Pagination baslangic indeksi.
            disclosure_class:  "FR" veya "ODA".
            company_id:        Sirket filtresi (None = tum sirketler).

        Returns:
            list[dict] — ham bildirim listesi.

        Raises:
            KapApiError: API hatasi.
        """
        time.sleep(_RATE_LIMIT_SLEEP)
        params: dict[str, Any] = {
            "disclosureIndex": start_index,
            "disclosureClass": disclosure_class,
        }
        if company_id is not None:
            params["companyId"] = company_id
        resp = self._session.get(
            f"{self._base}/api/vyk/disclosures",
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise KapApiError(
                f"get_disclosures: HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

    # ------------------------------------------------------------------
    def get_disclosure_detail(self, index: int, file_type: str = "data") -> dict[str, Any]:
        """Tek bir aciklamanin detayini (XBRL) getirir.

        Args:
            index:     Aciklama index numarasi.
            file_type: "data" (varsayilan) — XBRL finansal veri.

        Returns:
            dict — ham XBRL detay yaniti.

        Raises:
            KapApiError: API hatasi.
        """
        time.sleep(_RATE_LIMIT_SLEEP)
        resp = self._session.get(
            f"{self._base}/api/vyk/disclosureDetail/{index}",
            params={"fileType": file_type},
            timeout=_DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            raise KapApiError(
                f"get_disclosure_detail({index}): HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

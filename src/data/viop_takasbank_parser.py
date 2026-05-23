"""Takasbank VIOP istatistikleri put/call acik pozisyon parser (CB-008).

URL: https://www.takasbank.com.tr/tr/kaynaklar/viop-istatistikleri
Kimlik dogrulamasi gerekmez; HTML tablo parse ile market-wide PCR hesaplanir.
"""
from __future__ import annotations

import logging
import re
from datetime import date

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_URL = "https://www.takasbank.com.tr/tr/kaynaklar/viop-istatistikleri"
_TIMEOUT_DEFAULT: float = 10.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}


def fetch_viop_pcr(timeout: float = _TIMEOUT_DEFAULT) -> dict | None:
    """Takasbank VIOP istatistik sayfasindan put/call acik pozisyonu ceker.

    Returns:
        {"put_call_ratio": float, "put_oi": int, "call_oi": int, "date": str}
        veya None (parse/network hatasi).
    """
    try:
        resp = requests.get(_URL, timeout=timeout, headers=_HEADERS)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning("VIOP Takasbank: timeout (%.0fs)", timeout)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("VIOP Takasbank: network hatasi — %s", exc)
        return None

    return _parse_pcr(resp.text)


def _parse_pcr(html: str) -> dict | None:
    """BeautifulSoup ile HTML'den put/call OI satirlarini bulur ve PCR hesaplar."""
    soup = BeautifulSoup(html, "html.parser")
    put_oi = 0
    call_oi = 0

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if not cells:
                continue
            text = " ".join(cells).lower()

            nums = [_to_int(c) for c in cells]
            nums = [n for n in nums if n is not None]
            if not nums:
                continue
            oi_val = nums[-1]

            if "put" in text or "satis" in text:
                put_oi += oi_val
            elif "call" in text or "alim" in text:
                call_oi += oi_val

    if call_oi == 0:
        logger.warning(
            "VIOP Takasbank: call_oi=0 — tablo parse edilemedi veya sayfa yapisi degisti"
        )
        return None

    ratio = round(put_oi / call_oi, 4)
    logger.info(
        "VIOP Takasbank: put_oi=%d, call_oi=%d, PCR=%.4f", put_oi, call_oi, ratio
    )
    return {
        "put_call_ratio": ratio,
        "put_oi": put_oi,
        "call_oi": call_oi,
        "date": date.today().isoformat(),
    }


def _to_int(text: str) -> int | None:
    """Virgul/nokta/bosluk ayracli sayiyi int'e cevir. Parse edilemezse None."""
    clean = re.sub(r"[.,\s]", "", text.strip())
    try:
        return int(clean)
    except ValueError:
        return None

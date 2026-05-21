"""TCMB policy rate scraper — tcmb.gov.tr native (D-095).

Scrapes the official TCMB PPK (Monetary Policy Committee) press release pages.
Replaces TradingEconomics as the third-party fallback with a first-party source.

Fallback chain position: EVDS API → tcmb.gov.tr scrape → local_macro_fallback.yaml

Usage:
    from src.data.tcmb_scraper import fetch_tcmb_policy_rate
    rate = fetch_tcmb_policy_rate()  # float, e.g. 37.0, or None on failure
"""
from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE = "https://www.tcmb.gov.tr"
# PPK (Para Politikası Kurulu) press releases listing page
_PPK_LIST_URL = _BASE + "/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Temel+Faaliyetler/Para+Politikasi/PPK/{year}"
# Press release base path pattern — e.g. /wps/wcm/.../duyurular/basin/2026/duy2026-19
_PPK_PRESS_BASE = _BASE + "/wps/wcm/connect/tr/tcmb+tr/main+menu/duyurular/basin/{year}"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}
_TIMEOUT = 12

# Regex: "bir hafta vadeli repo ihale faiz oranının yüzde XX'de sabit tutulmasına"
# Typical TCMB PPK decision text (Turkish). Rate is a number like 37, 42.5, etc.
_DECISION_PATTERN = re.compile(
    r"politika\s+faizi\s+olan\s+bir\s+hafta\s+vadeli\s+repo[^.]{0,100}"
    r"y[üu]zde\s+(\d+(?:[,\.]\d{1,2})?)",
    re.IGNORECASE | re.DOTALL,
)
# Simpler pattern: "yüzde NN'de sabit" or "yüzde NN olarak belirledi"
_RATE_DECISION_PATTERNS = [
    re.compile(
        r"bir\s+hafta[lk]*\s+(?:vadeli\s+)?repo[^.]{0,120}"
        r"y[üu]zde\s+(\d+(?:[,\.]\d{1,2})?)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"politika\s+faiz\s+oran[ıi][^.]{0,80}"
        r"y[üu]zde\s+(\d+(?:[,\.]\d{1,2})?)",
        re.IGNORECASE | re.DOTALL,
    ),
    # Fallback: "yüzde XX'de sabit" / "yüzde XX olarak"
    re.compile(
        r"y[üu]zde\s+(\d+(?:[,\.]\d{1,2})?)\s*[''']de\s+sabit",
        re.IGNORECASE,
    ),
]


def fetch_tcmb_policy_rate(
    year: int | None = None,
    timeout: int = _TIMEOUT,
) -> float | None:
    """Fetch the most recent TCMB 1-week repo (policy) rate from tcmb.gov.tr.

    Args:
        year: Calendar year for PPK decisions. Defaults to current year.
        timeout: HTTP timeout in seconds.

    Returns:
        Policy rate as float (e.g. 37.0) or None on failure.
    """
    from datetime import datetime, timezone
    if year is None:
        year = datetime.now(timezone.utc).year

    # Step 1: Get list of PPK press releases for this year
    press_links = _get_press_release_links(year, timeout)
    if not press_links:
        # Fallback to prior year
        press_links = _get_press_release_links(year - 1, timeout)

    if not press_links:
        logger.warning("tcmb_scraper: no PPK press release links found for %d/%d", year, year - 1)
        return None

    # Step 2: Try latest press releases (newest first) until rate found
    for link in press_links[:5]:
        url = _BASE + link if link.startswith("/") else link
        rate = _extract_rate_from_press_release(url, timeout)
        if rate is not None:
            logger.info("tcmb_scraper: policy rate = %.2f%% (from %s)", rate, url.split("/")[-1])
            return rate

    logger.warning("tcmb_scraper: rate not found in %d press releases", len(press_links[:5]))
    return None


def _get_press_release_links(year: int, timeout: int) -> list[str]:
    """Return PPK press release links for the given year, newest first."""
    url = _PPK_LIST_URL.format(year=year)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            logger.debug("tcmb_scraper: PPK list %d HTTP %d", year, resp.status_code)
            return []
        soup = BeautifulSoup(resp.content, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # PPK press release links: /wps/wcm/.../duyurular/basin/YYYY/duyYYYY-NN
            if "/duyurular/" in href.lower() or "/basin/" in href.lower():
                if f"/{year}/" in href or f"/{year}" in href:
                    links.append(href)
        # De-dup, preserve order
        seen: set[str] = set()
        result = []
        for lnk in links:
            if lnk not in seen:
                seen.add(lnk)
                result.append(lnk)
        return list(reversed(result))  # newest last → reverse to newest first
    except Exception as exc:
        logger.warning("tcmb_scraper: failed to get PPK list for %d: %s", year, exc)
        return []


def _extract_rate_from_press_release(url: str, timeout: int) -> float | None:
    """Fetch a PPK press release page and extract the policy rate."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.content, "lxml")
        text = soup.get_text(" ", strip=True)

        for pattern in _RATE_DECISION_PATTERNS:
            m = pattern.search(text)
            if m:
                raw = m.group(1).replace(",", ".")
                val = float(raw)
                if 5.0 < val < 100.0:
                    return val

    except Exception as exc:
        logger.debug("tcmb_scraper: error fetching %s: %s", url, exc)

    return None

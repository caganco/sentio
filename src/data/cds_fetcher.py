"""Turkey 5Y CDS EOD scraper.

Fallback chain:
  1. worldgovernmentbonds.com wp-json API  (primary)
  2. yfinance proxy model via iShares TUR  (secondary)
  3. Caller falls back to local_macro_fallback.yaml (handled upstream)
"""
import logging
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_WGB_API = "https://www.worldgovernmentbonds.com/wp-json/cds/v1/main"
_WGB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Origin": "https://www.worldgovernmentbonds.com",
    "Referer": "https://www.worldgovernmentbonds.com/sovereign-cds/",
}


def fetch_turkey_cds_bps() -> float | None:
    """Return Turkey 5Y CDS in basis points, or None on failure.

    Tries primary (WGB API) then secondary (yfinance proxy).
    Logs each step so the fallback chain is visible.
    """
    value = _fetch_wgb()
    if value is not None:
        logger.info(f"CDS scraper: primary success — Turkey 5Y CDS = {value:.1f} bps")
        return value

    logger.warning("CDS scraper: primary (WGB API) failed, trying yfinance proxy")
    value = _fetch_yfinance_proxy()
    if value is not None:
        logger.warning(f"CDS scraper: secondary (yfinance proxy) ~ {value:.0f} bps")
        return value

    logger.error("CDS scraper: all sources failed — caller should use YAML fallback")
    return None


def _fetch_wgb() -> float | None:
    """POST to worldgovernmentbonds.com wp-json CDS API, parse Turkey row."""
    try:
        resp = requests.post(_WGB_API, headers=_WGB_HEADERS, json={}, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"CDS WGB API: HTTP {resp.status_code}")
            return None

        body = resp.json()
        table_html = body.get("table", "")
        if not table_html:
            logger.warning("CDS WGB API: empty table in response")
            return None

        soup = BeautifulSoup(table_html, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            texts = [c.get_text(strip=True) for c in cells]
            if any("turkey" in t.lower() for t in texts):
                # Row structure: ['', 'Turkey', 'Rating', '5Y_CDS', ...]
                for t in texts:
                    clean = t.replace(",", "")
                    try:
                        val = float(clean)
                        if 50 < val < 2000:  # realistic CDS range
                            return val
                    except ValueError:
                        continue
        logger.warning("CDS WGB API: Turkey row not found in table")
        return None

    except requests.exceptions.Timeout:
        logger.warning("CDS WGB API: timeout (10s)")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"CDS WGB API: network error: {e}")
        return None
    except (ValueError, KeyError) as e:
        logger.warning(f"CDS WGB API: parse error: {e}")
        return None


def _fetch_yfinance_proxy() -> float | None:
    """Estimate Turkey CDS via iShares TUR + macro model (same as CDSFallbackClient)."""
    try:
        import yfinance as yf

        usdtry = yf.Ticker("USDTRY=X").history(period="1d")
        vix = yf.Ticker("^VIX").history(period="1d")
        tur = yf.Ticker("TUR").history(period="5d")

        if usdtry.empty or vix.empty or tur.empty or len(tur) < 2:
            logger.warning("CDS yfinance proxy: missing market data")
            return None

        usdtry_val = float(usdtry["Close"].iloc[-1])
        vix_val = float(vix["Close"].iloc[-1])
        tur_ret = float(tur["Close"].pct_change().iloc[-1]) * 100

        # Quarterly-calibrated coefficients (same as CDSFallbackClient)
        cds_est = (
            250.0
            + 30.0 * (usdtry_val - 30.0)
            + 2.0 * vix_val
            - 100.0 * tur_ret
        )
        return max(100.0, min(800.0, cds_est))

    except Exception as e:
        logger.warning(f"CDS yfinance proxy: {e.__class__.__name__}: {e}")
        return None

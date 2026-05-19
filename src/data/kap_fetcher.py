"""KAP (Kamuyu Aydınlatma Platformu) disclosure fetcher.

Wraps kap-client to fetch daily disclosures for BIST tickers.
All network I/O goes through a single Kap() context manager session.
"""

import logging
import time
from datetime import date

from kap_client import Kap
from kap_client.exceptions import CompanyNotFoundError, KapError, RateLimitError

logger = logging.getLogger(__name__)

# Seconds to wait between per-symbol requests to avoid rate limiting
_DEFAULT_DELAY = 0.5
# Seconds to wait after a rate-limit hit before retrying
_RATE_LIMIT_BACKOFF = 10.0
_MAX_RETRIES = 3


class KapFetchError(Exception):
    """Raised when a symbol fetch fails after all retries."""


def fetch_disclosures_for_symbol(
    symbol: str,
    target_date: date,
    kap_client: Kap,
) -> list[dict]:
    """Fetch daily KAP disclosures for a single BIST symbol.

    Args:
        symbol: BIST ticker (e.g. "THYAO")
        target_date: The calendar day to fetch (inclusive start and end)
        kap_client: An active Kap() context manager instance

    Returns:
        List of disclosure dicts (serialized from kap_client Disclosure objects).
        Empty list if symbol not found on KAP or no disclosures on that day.

    Raises:
        RateLimitError: If still rate-limited after _MAX_RETRIES attempts.
    """
    date_str = target_date.strftime("%Y-%m-%d")
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            disclosures = kap_client.fetch_disclosures(
                symbol,
                start_date=date_str,
                end_date=date_str,
            )
            return [_disclosure_to_dict(d) for d in disclosures]
        except CompanyNotFoundError:
            logger.warning("KAP: symbol not found: %s", symbol)
            return []
        except RateLimitError:
            if attempt == _MAX_RETRIES:
                logger.error("KAP: rate limit after %d retries for %s", _MAX_RETRIES, symbol)
                raise
            logger.warning("KAP: rate limit for %s, waiting %.0fs (attempt %d)", symbol, _RATE_LIMIT_BACKOFF, attempt)
            time.sleep(_RATE_LIMIT_BACKOFF)
        except KapError as exc:
            logger.warning("KAP: fetch error for %s: %s", symbol, exc)
            return []
    return []


def fetch_all_symbols(
    symbols: list[str],
    target_date: date,
    rate_limit_delay_sec: float = _DEFAULT_DELAY,
) -> dict[str, list[dict]]:
    """Fetch daily KAP disclosures for all symbols in a single session.

    Opens one Kap() context manager and iterates over all symbols.
    Rate-limited symbols are skipped (empty list) after backoff+retry;
    a WARNING is logged for each skipped symbol.

    Args:
        symbols: List of BIST tickers
        target_date: Calendar day to fetch
        rate_limit_delay_sec: Delay between each symbol request (default 0.5s)

    Returns:
        {symbol: [disclosure_dicts]} — skipped symbols have empty list.
    """
    result: dict[str, list[dict]] = {}
    with Kap() as kap:
        for i, symbol in enumerate(symbols):
            if i > 0:
                time.sleep(rate_limit_delay_sec)
            try:
                result[symbol] = fetch_disclosures_for_symbol(symbol, target_date, kap)
                count = len(result[symbol])
                if count:
                    logger.info("KAP: %s → %d disclosure(s)", symbol, count)
            except RateLimitError:
                logger.warning("KAP: skipping %s after persistent rate limit", symbol)
                result[symbol] = []
    return result


def fetch_attachments_for_disclosure(
    disclosure_index: int,
    kap_client: Kap,
) -> list[str]:
    """Return download URLs for all attachments of a disclosure.

    Args:
        disclosure_index: The integer index from a Disclosure object
        kap_client: An active Kap() context manager instance

    Returns:
        List of attachment URL strings. Empty list on any error.
    """
    try:
        attachments = kap_client.fetch_attachments(disclosure_index)
        return [a.url for a in attachments if a.url]
    except Exception as exc:
        logger.warning("KAP: could not fetch attachments for index %s: %s", disclosure_index, exc)
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _disclosure_to_dict(d) -> dict:
    """Serialize a kap_client Disclosure object to a plain dict."""
    return {
        "index": d.index,
        "publish_datetime": d.publish_datetime.isoformat(),
        "company_name": d.company_name,
        "stock_codes": d.stock_codes,
        "subject": d.subject,
        "summary": d.summary,
        "disclosure_type": d.disclosure_type,
        "has_attachment": d.has_attachment,
        "is_late": d.is_late,
        "is_corrective": d.is_corrective,
        "is_english": d.is_english,
        "url": d.url,
    }

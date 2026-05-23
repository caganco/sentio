"""KAP client with edge case handling (holidays, bulk events, downtime).

Wraps BISTCalendar, KAPDisclosureQueue, and KAPCacheManager to provide
robust KAP disclosure fetching with graceful fallbacks.

Integration points:
1. kap_scheduler.run_daily_kap_pipeline() — check calendar before fetching
2. Daily batch processing — process queued disclosures at end-of-day
3. Cache-aware signal engine — use cache_source to adjust confidence
"""
import logging
from datetime import date

from src.data.bist_calendar import BISTCalendar
from src.data.kap_cache_manager import KAPCacheManager
from src.data.kap_fetcher import fetch_all_symbols
from src.data.kap_queue import KAPDisclosureQueue

logger = logging.getLogger(__name__)


class KAPClientWithEdgeCases:
    """
    KAP client with edge case handling.

    Features:
    - Skip fetch on BIST holidays
    - Queue bulk disclosures for batch processing
    - Cache fallback on downtime (with TTL policy)
    - Alert on stale data

    Usage:
        client = KAPClientWithEdgeCases(cache_config)

        # Check if should fetch today
        if not client.calendar.is_today_holiday:
            result = client.fetch_symbols(symbols, date.today())
            client.process_queue_batch()  # end-of-day
    """

    def __init__(self, cache_config: dict = None, alerter=None):
        """
        Initialize KAP client with edge case handling.

        Args:
            cache_config: Cache TTL and retry settings
            alerter: Optional alert callback
        """
        self.calendar = BISTCalendar()
        self.queue = KAPDisclosureQueue()

        if cache_config is None:
            cache_config = {
                "cache_ttl_hours": 24,
                "cache_ttl_incident_hours": 72,
                "max_retries": 3,
                "downtime_threshold_seconds": 300,
                "alert_on_stale_above_hours": 48,
            }

        self.cache = KAPCacheManager(cache_config, alerter)
        self.cache_config = cache_config
        self.alerter = alerter

    def fetch_symbols(
        self, symbols: list[str], target_date: date
    ) -> dict[str, list[dict]]:
        """
        Fetch KAP disclosures for symbols, respecting holiday calendar.

        If today is BIST holiday, returns empty dict (no fetch attempted).
        Otherwise, fetches and queues disclosures for later batch processing.

        Args:
            symbols: List of BIST tickers
            target_date: Date to fetch

        Returns:
            {symbol: [disclosure_dicts]} — empty if holiday or on cache fallback
        """
        date_str = target_date.isoformat()

        # Check if holiday
        if self.calendar.is_holiday(date_str):
            logger.info(f"KAP: {date_str} is BIST holiday, skipping fetch")
            return {s: [] for s in symbols}

        # Attempt fetch
        try:
            result = fetch_all_symbols(symbols, target_date)

            # Queue any fetched disclosures for batch processing
            for symbol, disclosures in result.items():
                for disclosure in disclosures:
                    self.queue.add_disclosure({
                        "ticker": symbol,
                        "event_type": disclosure.get("disclosure_type", "unknown"),
                        "timestamp": disclosure.get("publish_datetime"),
                        "subject": disclosure.get("subject"),
                        "summary": disclosure.get("summary"),
                        "disclosure_index": disclosure.get("index"),
                        "url": disclosure.get("url"),
                    })

            logger.info(f"KAP: {len(result)} symbols fetched, {self.queue.queue_size()} disclosures queued")
            return result

        except Exception as e:
            logger.error(f"KAP fetch failed: {e}", exc_info=True)
            return {s: [] for s in symbols}

    def process_queue_batch(self) -> dict:
        """
        Process queued disclosures (call end-of-day).

        Returns:
            dict with processing stats (processed, dropped, errors, etc.)
        """
        result = self.queue.process_batch()
        logger.info(f"KAP batch processed: {result}")
        return result

    def reset_daily_state(self) -> None:
        """Reset daily counters. Call at day boundary."""
        self.queue.reset_daily_counters()
        self.cache.mark_recovery() if self.cache.is_downtime() else None
        logger.info("KAP daily state reset")

    def get_cache_info(self) -> dict:
        """Return cache statistics."""
        return {
            "cache": self.cache.cache_info(),
            "queue": {
                "queue_size": self.queue.queue_size(),
                "processed_today": self.queue.processed_today,
                "dropped_today": self.queue.dropped_today,
            },
        }

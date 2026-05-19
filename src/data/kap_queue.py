"""Queue for KAP disclosures. Prevents rate limiting on bulk events."""
import logging
import time

logger = logging.getLogger(__name__)


class KAPDisclosureQueue:
    """
    Queue for KAP disclosures. Non-blocking ingestion, batch processing at end-of-day.

    Usage:
        1. Scraper adds disclosures to queue (add_disclosure) — non-blocking
        2. End-of-day batch processor empties queue (process_batch) — async-safe
        3. Signal engine uses processed disclosures

    In-memory implementation: crash loses queue. Acceptable for daily bulk events.
    TODO: SQLite persistence option for high-volume scenarios.
    """

    def __init__(self, max_queue_size: int = 500, max_per_batch: int = 100):
        """
        Initialize disclosure queue.

        Args:
            max_queue_size: Max items before dropping (500 = ~1 day of bulk events)
            max_per_batch: Max items processed per batch call (100 = rate limit safety)
        """
        self.queue: list[dict] = []
        self.max_queue_size = max_queue_size
        self.max_per_batch = max_per_batch
        self.processed_today = 0
        self.dropped_today = 0

    def add_disclosure(self, disclosure: dict) -> bool:
        """
        Add disclosure to queue. Non-blocking.

        Args:
            disclosure: {
                "ticker": str,
                "event_type": str,
                "timestamp": str (ISO format),
                "subject": str,
                "summary": str,
                ... other fields
            }

        Returns:
            bool: True if queued, False if queue full (dropped)
        """
        if len(self.queue) >= self.max_queue_size:
            self.dropped_today += 1
            logger.warning(
                f"KAP queue full ({self.max_queue_size}), dropped disclosure: "
                f"{disclosure.get('ticker')} {disclosure.get('event_type')}"
            )
            return False

        self.queue.append(disclosure)
        logger.debug(
            f"KAP disclosure queued: {disclosure.get('ticker')} "
            f"(queue size: {len(self.queue)}/{self.max_queue_size})"
        )
        return True

    def queue_size(self) -> int:
        """Return current queue size."""
        return len(self.queue)

    def process_batch(self) -> dict:
        """
        Process queued disclosures (called end-of-day or on-demand).

        Processes up to max_per_batch items, respects rate limiting via sleep.
        Skips duplicates (ticker+timestamp).

        Returns:
            dict: {
                "processed": int,
                "dropped": int (cumulative today),
                "errors": int,
                "tickers_affected": list[str],
                "queue_remaining": int,
            }
        """
        processed = 0
        errors = 0
        tickers_affected = set()
        seen = set()  # (ticker, timestamp) pairs for deduplication

        while self.queue and processed < self.max_per_batch:
            disclosure = self.queue.pop(0)

            try:
                ticker = disclosure.get("ticker")
                timestamp = disclosure.get("timestamp")

                # Deduplicate by ticker+timestamp
                key = (ticker, timestamp)
                if key in seen:
                    logger.debug(f"KAP duplicate disclosure skipped: {ticker} {timestamp}")
                    # Skip processing but don't count as processed
                    continue

                seen.add(key)

                # Rate limiting: 100ms per disclosure (10 disclosures/sec)
                time.sleep(0.1)

                self._process_single(disclosure)
                processed += 1
                tickers_affected.add(ticker)

            except Exception as e:
                logger.error(f"KAP disclosure processing error: {e}", exc_info=True)
                errors += 1

        self.processed_today += processed

        logger.info(
            f"KAP batch processed: {processed} | "
            f"dropped (total): {self.dropped_today} | "
            f"errors: {errors} | "
            f"tickers affected: {len(tickers_affected)} | "
            f"queue remaining: {len(self.queue)}"
        )

        return {
            "processed": processed,
            "dropped": self.dropped_today,
            "errors": errors,
            "tickers_affected": sorted(tickers_affected),
            "queue_remaining": len(self.queue),
        }

    def _process_single(self, disclosure: dict) -> None:
        """
        Process single disclosure.

        Currently a no-op (validation happens in tests).
        In production: store in cache, update signals, etc.

        Args:
            disclosure: Disclosure dict
        """
        # TODO: store in signal cache, update signal engine
        # For now, validation happens via tests
        pass

    def reset_daily_counters(self) -> None:
        """Reset daily counters. Call after processing batch at day boundary."""
        self.processed_today = 0
        self.dropped_today = 0
        logger.info("KAP queue daily counters reset")

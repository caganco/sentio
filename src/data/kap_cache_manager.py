"""KAP data caching with TTL and fallback policy on downtime."""
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class KAPCacheManager:
    """
    Manage KAP data caching with TTL and fallback policy.

    During normal operation: use fresh data or cache < 24h old
    During downtime (5+ min): switch to incident mode, extend TTL to 72h
    Alert when cache becomes stale (> 48h old)

    Config via dict:
    {
        "cache_ttl_hours": 24,             # Normal TTL
        "cache_ttl_incident_hours": 72,    # Incident mode TTL
        "max_retries": 3,                  # Failures before incident mode
        "downtime_threshold_seconds": 300, # 5 min = downtime
        "alert_on_stale_above_hours": 48,  # Alert threshold
    }
    """

    def __init__(self, config: dict, alerter=None):
        """
        Initialize cache manager.

        Args:
            config: Configuration dict with TTL and retry settings
            alerter: Optional alert callback (called with level, service, message)
        """
        self.config = config
        self.alerter = alerter
        self.cache: dict[str, dict] = {}  # {ticker: {data, timestamp, source}}
        self.last_fetch_status = "unknown"
        self.consecutive_failures = 0
        self.downtime_start_time: Optional[datetime] = None

    def is_downtime(self) -> bool:
        """Check if system is in downtime mode."""
        return (
            self.consecutive_failures >= self.config.get("max_retries", 3)
            and self.last_fetch_status == "downtime"
        )

    def get_with_fallback(
        self, ticker: str, fetch_func=None
    ) -> dict:
        """
        Get KAP data for ticker. Use fresh, cached, or fail gracefully.

        Flow:
        1. Try fetch_func (if provided)
        2. On success: store in cache, return source="fresh"
        3. On fail: check cache age, return cached if within TTL
        4. If cache expired or missing: return error dict

        Args:
            ticker: Stock ticker
            fetch_func: Callable() -> dict. If None, skip to cache lookup.

        Returns:
            dict: {
                "data": dict or None,
                "source": "fresh" | "cache_fresh" | "cache_stale" | "expired" | "none",
                "age_hours": float or None,
                "error": str or None,
            }
        """

        # Attempt fresh fetch
        if fetch_func is not None:
            try:
                data = fetch_func()
                if data is not None:
                    self.cache[ticker] = {
                        "data": data,
                        "timestamp": datetime.now(),
                        "source": "fresh",
                    }
                    self.consecutive_failures = 0
                    self.last_fetch_status = "success"

                    return {
                        "data": data,
                        "source": "fresh",
                        "age_hours": 0,
                        "error": None,
                    }
                else:
                    logger.warning(f"KAP fetch returned None for {ticker}")
                    self.consecutive_failures += 1
                    self.last_fetch_status = "fetch_returned_none"

            except Exception as e:
                self.consecutive_failures += 1
                logger.warning(
                    f"KAP fetch failed ({self.consecutive_failures}/"
                    f"{self.config.get('max_retries', 3)}): {e}"
                )

                # Determine if downtime
                if self.consecutive_failures >= self.config.get("max_retries", 3):
                    self.last_fetch_status = "downtime"
                    if self.downtime_start_time is None:
                        self.downtime_start_time = datetime.now()

        # Fall back to cache
        if ticker in self.cache:
            cached = self.cache[ticker]
            age = (datetime.now() - cached["timestamp"]).total_seconds() / 3600

            # Determine TTL based on mode
            is_downtime = self.is_downtime()
            if is_downtime:
                ttl = self.config.get("cache_ttl_incident_hours", 72)
                mode = "incident"
            else:
                ttl = self.config.get("cache_ttl_hours", 24)
                mode = "normal"

            if age < ttl:
                # Cache still valid (< TTL, not <=)
                source_label = (
                    "cache_fresh"
                    if age < self.config.get("cache_ttl_hours", 24)
                    else "cache_stale"
                )

                # Alert if stale
                if age > self.config.get("alert_on_stale_above_hours", 48):
                    self._send_alert(
                        f"KAP cache stale: {ticker} {age:.1f}h old ({mode} mode)",
                        level="warning",
                    )

                return {
                    "data": cached["data"],
                    "source": source_label,
                    "age_hours": age,
                    "error": None,
                }
            else:
                # Cache expired
                self._send_alert(
                    f"KAP cache expired: {ticker} {age:.1f}h old (ttl={ttl}h, mode={mode})",
                    level="warning",
                )

                return {
                    "data": None,
                    "source": "expired",
                    "age_hours": age,
                    "error": f"Cache expired ({age:.1f}h > {ttl}h)",
                }

        # No cache at all
        return {
            "data": None,
            "source": "none",
            "age_hours": None,
            "error": "No cached data available",
        }

    def clear_cache(self, ticker: Optional[str] = None) -> None:
        """
        Clear cache for a ticker or all tickers.

        Args:
            ticker: Specific ticker to clear, or None for all
        """
        if ticker is not None:
            if ticker in self.cache:
                del self.cache[ticker]
                logger.info(f"KAP cache cleared for {ticker}")
        else:
            self.cache.clear()
            logger.info("KAP cache cleared (all tickers)")

    def mark_recovery(self) -> None:
        """Mark recovery from downtime. Reset counters."""
        if self.is_downtime():
            duration = (
                (datetime.now() - self.downtime_start_time).total_seconds() / 60
                if self.downtime_start_time
                else 0
            )
            logger.info(f"KAP downtime recovery after {duration:.0f} minutes")
            self._send_alert(
                f"KAP system recovered after {duration:.0f} min downtime",
                level="info",
            )

        self.consecutive_failures = 0
        self.last_fetch_status = "recovered"
        self.downtime_start_time = None

    def cache_info(self) -> dict:
        """Return cache statistics."""
        return {
            "cached_tickers": len(self.cache),
            "consecutive_failures": self.consecutive_failures,
            "is_downtime": self.is_downtime(),
            "last_fetch_status": self.last_fetch_status,
            "downtime_duration_minutes": (
                (datetime.now() - self.downtime_start_time).total_seconds() / 60
                if self.downtime_start_time
                else 0
            ),
        }

    def _send_alert(self, message: str, level: str = "warning") -> None:
        """
        Send alert to monitoring system.

        Args:
            message: Alert message
            level: "info" | "warning" | "error"
        """
        logger.log(
            {"info": 20, "warning": 30, "error": 40}.get(level, 20),
            f"KAP ALERT ({level}): {message}",
        )

        if self.alerter is not None:
            try:
                self.alerter.send(
                    level=level,
                    service="kap_cache_manager",
                    message=message,
                )
            except Exception as e:
                logger.error(f"Alert send failed: {e}")

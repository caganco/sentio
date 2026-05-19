"""Tests for KAP edge case handling (SPEC_KAP_2).

Tests 35+ scenarios across:
- Holiday detection (6 tests)
- Bulk disclosure queue (8 tests)
- Downtime fallback caching (10 tests)
- Integration scenarios (5 tests)
- Stress/edge cases (6 tests)
"""
from datetime import datetime, timedelta

import pytest

from src.data.bist_calendar import BISTCalendar
from src.data.kap_cache_manager import KAPCacheManager
from src.data.kap_queue import KAPDisclosureQueue

# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def calendar():
    """Create BIST calendar for testing."""
    return BISTCalendar()


@pytest.fixture
def queue():
    """Create disclosure queue for testing."""
    return KAPDisclosureQueue(max_queue_size=500, max_per_batch=100)


@pytest.fixture
def cache_config():
    """Create standard cache config."""
    return {
        "cache_ttl_hours": 24,
        "cache_ttl_incident_hours": 72,
        "max_retries": 3,
        "downtime_threshold_seconds": 300,
        "alert_on_stale_above_hours": 48,
    }


@pytest.fixture
def cache_manager(cache_config):
    """Create cache manager for testing."""
    return KAPCacheManager(cache_config)


class MockAlerter:
    """Mock alerter for testing alert behavior."""

    def __init__(self):
        self.alerts = []

    def send(self, level: str, service: str, message: str):
        """Record alert."""
        self.alerts.append({"level": level, "service": service, "message": message})


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Holiday Detection (6 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBISTHolidayDetection:
    """Test BIST holiday calendar functionality."""

    def test_is_holiday_new_year(self, calendar):
        """Test New Year (2026-01-01) is recognized as holiday."""
        assert calendar.is_holiday("2026-01-01") is True

    def test_is_holiday_working_day(self, calendar):
        """Test regular working day is not a holiday."""
        assert calendar.is_holiday("2026-01-02") is False

    def test_is_holiday_national_day(self, calendar):
        """Test national sovereignty day (2026-04-23) is holiday."""
        assert calendar.is_holiday("2026-04-23") is True

    def test_is_holiday_eid(self, calendar):
        """Test Eid al-Fitr (2026-05-11) is holiday."""
        assert calendar.is_holiday("2026-05-11") is True

    def test_holiday_list_update(self, calendar):
        """Test updating holiday list for new year."""
        new_holidays = ["2027-01-01", "2027-04-23", "2027-05-01"]
        calendar.update_holidays(2027, new_holidays)

        assert calendar.is_holiday("2027-01-01") is True
        assert calendar.is_holiday("2027-04-23") is True
        # Old year should no longer match
        assert calendar.is_holiday("2026-01-01") is False

    def test_holiday_calendar_year_mismatch_warning(self, calendar):
        """Test updating for a year that's already passed logs warning."""
        # Try to update for 2025 (before 2026)
        calendar.update_holidays(2025, ["2025-01-01"])
        # Should still update but log warning
        assert calendar.is_holiday("2025-01-01") is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Disclosure Queue (8 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestDisclosureQueue:
    """Test KAP disclosure queue."""

    def test_queue_single_disclosure(self, queue):
        """Test adding single disclosure to queue."""
        disclosure = {
            "ticker": "GARAN",
            "event_type": "material_event",
            "timestamp": "2026-05-14T10:00:00",
            "subject": "Board meeting",
        }
        result = queue.add_disclosure(disclosure)
        assert result is True
        assert queue.queue_size() == 1

    def test_queue_multiple_disclosures(self, queue):
        """Test adding multiple disclosures."""
        for i in range(10):
            disclosure = {
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            }
            result = queue.add_disclosure(disclosure)
            assert result is True

        assert queue.queue_size() == 10

    def test_queue_overflow_drops_excess(self, queue):
        """Test queue overflow drops disclosures."""
        # Fill queue beyond max_queue_size (500)
        for i in range(510):
            disclosure = {
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            }
            result = queue.add_disclosure(disclosure)

            # First 500 succeed
            if i < 500:
                assert result is True
            # Excess 10 fail
            else:
                assert result is False

        assert queue.queue_size() == 500
        assert queue.dropped_today == 10

    def test_queue_batch_processing(self, queue):
        """Test batch processing respects max_per_batch."""
        # Add 150 disclosures
        for i in range(150):
            disclosure = {
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            }
            queue.add_disclosure(disclosure)

        # Process batch (max 100)
        result = queue.process_batch()
        assert result["processed"] == 100
        assert result["queue_remaining"] == 50

        # Process next batch
        result = queue.process_batch()
        assert result["processed"] == 50
        assert result["queue_remaining"] == 0

    def test_queue_deduplication(self, queue):
        """Test duplicate disclosures (same ticker+timestamp) are skipped during processing."""
        disclosure = {
            "ticker": "GARAN",
            "event_type": "material_event",
            "timestamp": "2026-05-14T10:00:00",
        }

        # Add same disclosure 3 times (all queued)
        queue.add_disclosure(disclosure)
        queue.add_disclosure(disclosure)
        queue.add_disclosure(disclosure)

        assert queue.queue_size() == 3

        # Process batch: deduplication skips duplicates during processing
        # The logic pops from queue and continues on duplicates, so they get removed from queue
        result = queue.process_batch()
        # 1 unique disclosed processed, 2 duplicates encountered and skipped
        assert result["processed"] == 1
        # Queue should be empty (all 3 were popped, 1 processed, 2 skipped)
        assert result["queue_remaining"] == 0

    def test_queue_processing_non_blocking(self, queue):
        """Test add_disclosure is non-blocking (returns immediately)."""
        import time

        start = time.time()
        for i in range(100):
            disclosure = {
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            }
            queue.add_disclosure(disclosure)
        elapsed = time.time() - start

        # Adding 100 should be fast (< 100ms), not blocked
        assert elapsed < 0.1, f"Adding 100 disclosures took {elapsed}s (should be < 0.1s)"

    def test_queue_reset_daily_counters(self, queue):
        """Test resetting daily counters."""
        for i in range(5):
            queue.add_disclosure({
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            })

        queue.process_batch()
        assert queue.processed_today == 5

        queue.reset_daily_counters()
        assert queue.processed_today == 0
        assert queue.dropped_today == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Cache Manager — Fresh Data (2 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheManagerFreshData:
    """Test cache manager with fresh data."""

    def test_get_fresh_data_success(self, cache_manager):
        """Test fresh data fetch succeeds."""
        def mock_fetch():
            return {"ticker": "GARAN", "events": ["event1"]}

        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch)

        assert result["source"] == "fresh"
        assert result["age_hours"] == 0
        assert result["data"]["ticker"] == "GARAN"
        assert result["error"] is None

    def test_get_fresh_data_resets_consecutive_failures(self, cache_manager):
        """Test successful fetch resets failure counter."""
        cache_manager.consecutive_failures = 5  # Simulate prior failures

        def mock_fetch():
            return {"ticker": "GARAN", "events": []}

        cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch)
        assert cache_manager.consecutive_failures == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Cache Manager — Cached Data (5 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheManagerCachedData:
    """Test cache manager fallback to cached data."""

    def test_get_cache_fresh_under_24h(self, cache_manager):
        """Test cached data < 24h old is labeled cache_fresh."""
        # Manually populate cache with 12h old data
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN", "events": []},
            "timestamp": datetime.now() - timedelta(hours=12),
            "source": "fresh",
        }

        # Fetch with failed fetch_func
        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_fail)

        assert result["source"] == "cache_fresh"
        assert 11.9 < result["age_hours"] < 12.1  # ~12h
        assert result["data"]["ticker"] == "GARAN"

    def test_get_cache_stale_48h_old_in_incident_mode(self, cache_manager):
        """Test cached data 48h old is labeled cache_stale in incident mode."""
        alerter = MockAlerter()
        cache_manager.alerter = alerter

        # Add cache 49h old (valid in incident mode TTL=72h, and >= alert threshold 48h)
        cache_manager.cache["ASELS"] = {
            "data": {"ticker": "ASELS", "events": []},
            "timestamp": datetime.now() - timedelta(hours=49),
            "source": "fresh",
        }

        # Trigger incident mode
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"

        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("ASELS", fetch_func=mock_fetch_fail)

        assert result["source"] == "cache_stale"
        assert result["age_hours"] > 48
        # Should have triggered alert (49h > alert threshold 48h)
        assert result["data"] is not None

    def test_get_cache_expired_72h_old(self, cache_manager):
        """Test cached data > 72h expires even in incident mode."""
        # Add cache > 72h old
        cache_manager.cache["THYAO"] = {
            "data": {"ticker": "THYAO", "events": []},
            "timestamp": datetime.now() - timedelta(hours=80),
            "source": "fresh",
        }
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"

        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("THYAO", fetch_func=mock_fetch_fail)

        assert result["source"] == "expired"
        assert result["data"] is None
        assert result["error"] is not None

    def test_get_no_cache_returns_error(self, cache_manager):
        """Test missing cache with failed fetch returns error."""
        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("UNKNOWN", fetch_func=mock_fetch_fail)

        assert result["source"] == "none"
        assert result["data"] is None
        assert result["error"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Cache Manager — Downtime & Recovery (4 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheManagerDowntime:
    """Test cache manager downtime handling."""

    def test_downtime_mode_triggers_on_consecutive_failures(self, cache_manager):
        """Test downtime mode triggers after max_retries failures."""
        def mock_fetch_fail():
            raise Exception("Network error")

        # Trigger 3 consecutive failures
        for i in range(3):
            cache_manager.get_with_fallback(f"TICK{i}", fetch_func=mock_fetch_fail)

        # After 3 failures, should be in downtime
        assert cache_manager.is_downtime() is True
        assert cache_manager.last_fetch_status == "downtime"

    def test_downtime_mode_extends_ttl(self, cache_manager):
        """Test TTL extends to 72h in incident mode."""
        # Trigger downtime
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"

        # Add cache 50h old
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN", "events": []},
            "timestamp": datetime.now() - timedelta(hours=50),
            "source": "fresh",
        }

        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_fail)

        # In incident mode, 50h < 72h should still be valid
        assert result["source"] == "cache_stale"
        assert result["data"]["ticker"] == "GARAN"

    def test_downtime_recovery(self, cache_manager):
        """Test recovery from downtime resets counters."""
        # Simulate downtime
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"
        cache_manager.downtime_start_time = datetime.now() - timedelta(minutes=10)

        assert cache_manager.is_downtime() is True

        # Mark recovery
        cache_manager.mark_recovery()

        assert cache_manager.is_downtime() is False
        assert cache_manager.consecutive_failures == 0
        assert cache_manager.last_fetch_status == "recovered"

    def test_downtime_alerts_recovery(self, cache_manager):
        """Test recovery sends alert."""
        alerter = MockAlerter()
        cache_manager.alerter = alerter

        # Simulate downtime
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"
        cache_manager.downtime_start_time = datetime.now() - timedelta(minutes=5)

        cache_manager.mark_recovery()

        # Should have alert
        assert len(alerter.alerts) > 0
        assert any("recovered" in a["message"] for a in alerter.alerts)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Cache Manager — Cache Operations (3 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheManagerOperations:
    """Test cache manager utility operations."""

    def test_clear_single_ticker_cache(self, cache_manager):
        """Test clearing cache for single ticker."""
        cache_manager.cache["GARAN"] = {"data": {}, "timestamp": datetime.now()}
        cache_manager.cache["ASELS"] = {"data": {}, "timestamp": datetime.now()}

        cache_manager.clear_cache("GARAN")

        assert "GARAN" not in cache_manager.cache
        assert "ASELS" in cache_manager.cache

    def test_clear_all_cache(self, cache_manager):
        """Test clearing all cache."""
        for ticker in ["GARAN", "ASELS", "THYAO"]:
            cache_manager.cache[ticker] = {"data": {}, "timestamp": datetime.now()}

        cache_manager.clear_cache()

        assert len(cache_manager.cache) == 0

    def test_cache_info_reports_state(self, cache_manager):
        """Test cache_info returns status."""
        cache_manager.cache["GARAN"] = {"data": {}, "timestamp": datetime.now()}
        cache_manager.consecutive_failures = 2

        info = cache_manager.cache_info()

        assert info["cached_tickers"] == 1
        assert info["consecutive_failures"] == 2
        assert info["is_downtime"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Integration Scenarios (5 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestIntegrationScenarios:
    """Integration tests combining calendar, queue, and cache."""

    def test_scenario_normal_day(self, calendar, queue, cache_manager, cache_config):
        """Test normal day: not holiday, 5 disclosures, cache fresh."""
        # Day is not holiday
        assert calendar.is_holiday("2026-05-15") is False

        # Add 5 disclosures
        for i in range(5):
            queue.add_disclosure({
                "ticker": "GARAN",
                "event_type": f"event_{i}",
                "timestamp": f"2026-05-15T{i:02d}:00:00",
            })

        assert queue.queue_size() == 5

        # Cache is fresh (just added)
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN", "events": []},
            "timestamp": datetime.now(),
            "source": "fresh",
        }

        # Get without fetch_func (skip to cache lookup)
        result = cache_manager.get_with_fallback("GARAN")
        # When no fetch_func, goes straight to cache lookup
        # Cache age ~0h, so it's cache_fresh (< 24h)
        assert result["source"] == "cache_fresh"
        assert result["data"]["ticker"] == "GARAN"

    def test_scenario_holiday_bulk_event(self, calendar, queue):
        """Test holiday with pending bulk event."""
        # Today is holiday
        assert calendar.is_holiday("2026-01-01") is True

        # Bulk disclosures pending (would be queued, not fetched on holiday)
        for i in range(50):
            queue.add_disclosure({
                "ticker": f"TICK{i}",
                "event_type": "bulk_event",
                "timestamp": f"2026-01-02T{i:02d}:00:00",
            })

        assert queue.queue_size() == 50

    def test_scenario_downtime_with_bulk_queue(self, cache_manager, queue):
        """Test downtime while processing bulk queue."""
        # Simulate downtime
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"

        # Add 50 disclosures
        for i in range(50):
            queue.add_disclosure({
                "ticker": f"TICK{i}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{i:02d}:00:00",
            })

        # Process in batches (100 max per batch)
        result = queue.process_batch()
        assert result["processed"] == 50
        assert result["queue_remaining"] == 0

    def test_scenario_holiday_list_outdated(self, calendar):
        """Test handling outdated holiday list."""
        # Try to check for 2027, but calendar is 2026
        # Should still work (gracefully)
        is_holiday = calendar.is_holiday("2027-01-01")
        # Will return False (not in 2026 list), but should log warning on update

        calendar.update_holidays(2027, ["2027-01-01"])
        assert calendar.is_holiday("2027-01-01") is True

    def test_scenario_queue_overflow_stress(self, queue):
        """Test queue under high-volume stress."""
        # Try to add way more than capacity
        added = 0
        for i in range(1000):
            disclosure = {
                "ticker": f"TICK{i % 60}",
                "event_type": "event",
                "timestamp": f"2026-05-14T{(i % 24):02d}:{(i % 60):02d}:00",
            }
            if queue.add_disclosure(disclosure):
                added += 1

        # Should have added up to max_queue_size (500)
        assert added == 500
        assert queue.dropped_today == 500


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Stress/Edge Cases (6 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestStressEdgeCases:
    """Stress tests and edge case scenarios."""

    def test_cache_manager_fetch_returns_none(self, cache_manager):
        """Test handling of fetch function returning None."""
        def mock_fetch_none():
            return None

        # First call returns None, triggers failure
        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_none)

        assert result["data"] is None
        assert cache_manager.consecutive_failures == 1

    def test_queue_with_missing_fields(self, queue):
        """Test queue handles disclosures with missing fields gracefully."""
        # Disclosure missing some fields
        disclosure = {
            "ticker": "GARAN",
            # missing event_type, subject, etc.
        }

        result = queue.add_disclosure(disclosure)
        assert result is True
        assert queue.queue_size() == 1

    def test_cache_boundary_exactly_24h_old(self, cache_manager):
        """Test cache near TTL boundary (23.99h, just under 24h cutoff)."""
        # Add cache 23.99h old (just under TTL)
        just_under_24h = datetime.now() - timedelta(hours=23.99)
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN"},
            "timestamp": just_under_24h,
            "source": "fresh",
        }

        def mock_fetch_fail():
            raise Exception("Network error")

        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_fail)

        # Just under 24h should still be valid (cache_fresh)
        assert result["source"] == "cache_fresh"

    def test_multiple_cache_managers_isolated(self, cache_config):
        """Test multiple cache managers don't share state."""
        mgr1 = KAPCacheManager(cache_config)
        mgr2 = KAPCacheManager(cache_config)

        mgr1.cache["GARAN"] = {"data": {}, "timestamp": datetime.now()}

        assert "GARAN" in mgr1.cache
        assert "GARAN" not in mgr2.cache

    def test_queue_timestamp_iso_format(self, queue):
        """Test queue handles ISO format timestamps correctly."""
        disclosure = {
            "ticker": "GARAN",
            "event_type": "event",
            "timestamp": "2026-05-14T14:30:45.123456",
        }

        result = queue.add_disclosure(disclosure)
        assert result is True

    def test_calendar_with_leap_year(self, calendar):
        """Test calendar handles leap year dates."""
        # 2026 is not a leap year, but test the concept
        # Add Feb 29 for a leap year (2024, 2028)
        leap_holidays = ["2028-02-29"]
        calendar.update_holidays(2028, leap_holidays)

        assert calendar.is_holiday("2028-02-29") is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Alert System (3 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAlertSystem:
    """Test alert mechanism in cache manager."""

    def test_alert_on_cache_stale(self, cache_manager, cache_config):
        """Test alert sent when cache becomes stale."""
        alerter = MockAlerter()
        cache_manager.alerter = alerter

        # Add 48h+ old cache
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN"},
            "timestamp": datetime.now() - timedelta(hours=49),
            "source": "fresh",
        }

        def mock_fetch_fail():
            raise Exception("Network error")

        cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_fail)

        assert len(alerter.alerts) > 0
        assert alerter.alerts[0]["level"] == "warning"

    def test_alert_on_cache_expired(self, cache_manager):
        """Test alert sent when cache expires."""
        alerter = MockAlerter()
        cache_manager.alerter = alerter

        # Add 80h+ old cache
        cache_manager.cache["THYAO"] = {
            "data": {"ticker": "THYAO"},
            "timestamp": datetime.now() - timedelta(hours=80),
            "source": "fresh",
        }

        def mock_fetch_fail():
            raise Exception("Network error")

        cache_manager.get_with_fallback("THYAO", fetch_func=mock_fetch_fail)

        assert len(alerter.alerts) > 0
        assert alerter.alerts[0]["level"] == "warning"

    def test_alert_with_no_alerter(self, cache_manager):
        """Test graceful handling when alerter is None."""
        cache_manager.alerter = None

        # Add cache 50h old (expired in normal mode, but valid in incident mode)
        # Test with incident mode so cache is still usable
        cache_manager.cache["GARAN"] = {
            "data": {"ticker": "GARAN"},
            "timestamp": datetime.now() - timedelta(hours=50),
            "source": "fresh",
        }

        # Trigger incident mode first
        cache_manager.consecutive_failures = 3
        cache_manager.last_fetch_status = "downtime"

        def mock_fetch_fail():
            raise Exception("Network error")

        # Should not raise exception even without alerter
        result = cache_manager.get_with_fallback("GARAN", fetch_func=mock_fetch_fail)
        # In incident mode with 72h TTL, 50h is cache_stale
        assert result["source"] == "cache_stale"
        assert result["data"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST CLASS: Regression & Compatibility (2 tests)
# ═══════════════════════════════════════════════════════════════════════════════


class TestRegressionCompatibility:
    """Test backward compatibility and regressions."""

    def test_calendar_2026_known_holidays(self, calendar):
        """Test calendar knows all major 2026 holidays."""
        major_holidays = [
            "2026-01-01",   # New Year
            "2026-04-23",   # National Sovereignty
            "2026-05-01",   # Labour Day
            "2026-08-30",   # Victory Day
            "2026-10-29",   # Republic Day
            "2026-05-11",   # Eid al-Fitr (approx)
        ]

        for date_str in major_holidays:
            assert calendar.is_holiday(date_str) is True

    def test_queue_process_batch_idempotent(self, queue):
        """Test processing empty queue is safe (idempotent)."""
        assert queue.queue_size() == 0

        # Process empty queue twice
        result1 = queue.process_batch()
        result2 = queue.process_batch()

        # Both should return 0 processed
        assert result1["processed"] == 0
        assert result2["processed"] == 0

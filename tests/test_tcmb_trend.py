"""Unit tests for TCMB trend modeling (Gap 2 — SPEC_L2_ENHANCEMENT_1)."""
import tempfile
from datetime import datetime, timedelta

import pytest

from src.signals.local.cache_store import LocalMacroCache
from src.signals.local.tcmb_client import TCMBClient
from src.signals.thresholds import TCMB_TREND_SCORES


def _make_cache() -> LocalMacroCache:
    td = tempfile.mkdtemp()
    return LocalMacroCache(db_path=f"{td}/tcmb_trend_test.db")


def _date(days_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).date().isoformat()


class TestCalculateTrend:
    """calculate_trend() inflection and rate delta logic."""

    def test_cutting_cycle_detected(self):
        """Last=cut, prev=hike → cutting_cycle (very bullish inflection)."""
        cache = _make_cache()
        cache.store_tcmb(_date(60), "hike", rate_before=35.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "cut",  rate_before=37.5, rate_after=35.0)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "cutting_cycle"

    def test_hiking_cycle_detected(self):
        """Last=hike, prev=cut → hiking_cycle (very bearish inflection)."""
        cache = _make_cache()
        cache.store_tcmb(_date(60), "cut",  rate_before=40.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "hike", rate_before=37.5, rate_after=40.0)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "hiking_cycle"

    def test_continued_easing(self):
        """Two consecutive cuts → easing."""
        cache = _make_cache()
        cache.store_tcmb(_date(60), "cut", rate_before=45.0, rate_after=42.5)
        cache.store_tcmb(_date(5),  "cut", rate_before=42.5, rate_after=40.0)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "easing"

    def test_continued_tightening(self):
        """Two consecutive hikes → tightening."""
        cache = _make_cache()
        cache.store_tcmb(_date(60), "hike", rate_before=35.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "hike", rate_before=37.5, rate_after=40.0)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "tightening"

    def test_hold_after_cut_inherits_easing(self):
        """hold after cut → easing (paused cutting cycle)."""
        cache = _make_cache()
        cache.store_tcmb(_date(90), "cut",  rate_before=45.0, rate_after=42.5)
        cache.store_tcmb(_date(5),  "hold", rate_before=42.5, rate_after=42.5)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "easing"

    def test_hold_after_hike_inherits_tightening(self):
        """hold after hike → tightening."""
        cache = _make_cache()
        cache.store_tcmb(_date(90), "hike", rate_before=35.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "hold", rate_before=37.5, rate_after=37.5)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "tightening"

    def test_no_history_returns_unknown(self):
        """Empty cache → unknown category."""
        cache = _make_cache()
        client = TCMBClient(cache)
        trend = client.calculate_trend()
        assert trend["category"] == "unknown"
        assert trend["delta_3m"] is None
        assert trend["delta_6m"] is None
        assert trend["delta_12m"] is None

    def test_rate_delta_3m_computed(self):
        """3-month delta = latest rate_after minus rate_after ~90 days ago."""
        cache = _make_cache()
        cache.store_tcmb(_date(95), "hike", rate_before=35.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "cut",  rate_before=37.5, rate_after=35.0)

        client = TCMBClient(cache)
        trend = client.calculate_trend()
        # latest=35.0, ref_after_3m=37.5 → delta = 35.0 - 37.5 = -2.5 (easing)
        assert trend["delta_3m"] == pytest.approx(-2.5, abs=1e-4)


class TestTrendAwareScore:
    """score() uses TCMB_TREND_SCORES instead of flat TCMB_DECISION_MAP."""

    def test_cutting_cycle_score_higher_than_plain_cut(self):
        """Inflection cut (cutting_cycle=80) > plain cut (easing=75)."""
        cache_inflection = _make_cache()
        cache_inflection.store_tcmb(_date(60), "hike", rate_before=35.0, rate_after=37.5)
        cache_inflection.store_tcmb(_date(5),  "cut",  rate_before=37.5, rate_after=35.0)

        cache_plain = _make_cache()
        cache_plain.store_tcmb(_date(60), "cut", rate_before=42.5, rate_after=40.0)
        cache_plain.store_tcmb(_date(5),  "cut", rate_before=40.0, rate_after=37.5)

        s_inflection = TCMBClient(cache_inflection).score().score
        s_plain = TCMBClient(cache_plain).score().score
        assert s_inflection > s_plain
        assert s_inflection == TCMB_TREND_SCORES["cutting_cycle"]
        assert s_plain == TCMB_TREND_SCORES["easing"]

    def test_hiking_cycle_score_lower_than_plain_hike(self):
        """Inflection hike (hiking_cycle=20) < plain hike (tightening=25)."""
        cache_inflection = _make_cache()
        cache_inflection.store_tcmb(_date(60), "cut",  rate_before=42.5, rate_after=40.0)
        cache_inflection.store_tcmb(_date(5),  "hike", rate_before=40.0, rate_after=42.5)

        cache_plain = _make_cache()
        cache_plain.store_tcmb(_date(60), "hike", rate_before=37.5, rate_after=40.0)
        cache_plain.store_tcmb(_date(5),  "hike", rate_before=40.0, rate_after=42.5)

        s_inflection = TCMBClient(cache_inflection).score().score
        s_plain = TCMBClient(cache_plain).score().score
        assert s_inflection < s_plain
        assert s_inflection == TCMB_TREND_SCORES["hiking_cycle"]
        assert s_plain == TCMB_TREND_SCORES["tightening"]

    def test_trend_category_in_audit_msg(self):
        """Audit message includes trend category."""
        cache = _make_cache()
        cache.store_tcmb(_date(60), "hike", rate_before=35.0, rate_after=37.5)
        cache.store_tcmb(_date(5),  "cut",  rate_before=37.5, rate_after=35.0)

        sig = TCMBClient(cache).score()
        assert "cutting_cycle" in sig.audit_msg

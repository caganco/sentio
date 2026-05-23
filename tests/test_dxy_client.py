"""Unit tests for DXYClient (Gap 3 — SPEC_L2_ENHANCEMENT_1)."""
import tempfile
from datetime import datetime, timedelta

import pytest

from src.signals.local.cache_store import LocalMacroCache
from src.signals.local.dxy_client import DXYClient
from src.signals.thresholds import (
    DXY_SCORE_THRESHOLDS,
    DXY_SCORE_WEAK_USD,
    DXY_STALE_DAYS,
)


def _make_cache() -> LocalMacroCache:
    td = tempfile.mkdtemp()
    return LocalMacroCache(db_path=f"{td}/dxy_test.db")


def _date(days_ago: int = 0) -> str:
    return (datetime.utcnow() - timedelta(days=days_ago)).date().isoformat()


class TestDxyToScore:
    """dxy_to_score() maps weekly % change to 0-100 score."""

    def test_strong_usd_gives_low_score(self):
        """DXY weekly +2% → strong USD → bearish BIST → score 25."""
        client = DXYClient(_make_cache())
        assert client.dxy_to_score(0.02) == 25.0

    def test_mild_usd_strength(self):
        """DXY weekly +0.8% → mild strength → score 40."""
        client = DXYClient(_make_cache())
        assert client.dxy_to_score(0.008) == 40.0

    def test_neutral_dxy(self):
        """DXY weekly 0.0% → neutral → score 50."""
        client = DXYClient(_make_cache())
        assert client.dxy_to_score(0.0) == 50.0

    def test_mild_usd_weakness(self):
        """DXY weekly -0.8% → mild USD weakness → score 60."""
        client = DXYClient(_make_cache())
        assert client.dxy_to_score(-0.008) == 60.0

    def test_weak_usd_gives_high_score(self):
        """DXY weekly -2% → very weak USD → bullish BIST → score 75."""
        client = DXYClient(_make_cache())
        assert client.dxy_to_score(-0.02) == DXY_SCORE_WEAK_USD

    def test_exact_threshold_boundaries(self):
        """Values at exact threshold boundaries map correctly."""
        client = DXYClient(_make_cache())
        # ≥ 0.015 → 25
        assert client.dxy_to_score(0.015) == 25.0
        # ≥ 0.005 but < 0.015 → 40
        assert client.dxy_to_score(0.005) == 40.0
        # ≥ -0.005 but < 0.005 → 50
        assert client.dxy_to_score(-0.005) == 50.0
        # ≥ -0.015 but < -0.005 → 60
        assert client.dxy_to_score(-0.015) == 60.0
        # < -0.015 → DXY_SCORE_WEAK_USD
        assert client.dxy_to_score(-0.016) == DXY_SCORE_WEAK_USD


class TestDxyScore:
    """score() reads from cache and computes confidence."""

    def test_no_data_returns_neutral_zero_confidence(self):
        sig = DXYClient(_make_cache()).score()
        assert sig.score == 50.0
        assert sig.confidence == 0.0
        assert sig.data_freshness == "missing"
        assert sig.component == "dxy"

    def test_fresh_data_gives_full_confidence(self):
        cache = _make_cache()
        cache.store_dxy(data_date=_date(0), close=104.5, weekly_change_pct=0.008)
        sig = DXYClient(cache).score()
        assert sig.confidence == 1.0
        assert sig.data_freshness == "fresh"
        assert sig.score == 40.0   # weekly_change_pct=0.008 → mild strength → 40

    def test_stale_data_gives_reduced_confidence(self):
        cache = _make_cache()
        cache.store_dxy(data_date=_date(3), close=104.0, weekly_change_pct=0.0)
        sig = DXYClient(cache).score()
        assert sig.confidence == 0.8
        assert sig.data_freshness == "stale"

    def test_very_stale_data_gives_zero_confidence(self):
        cache = _make_cache()
        cache.store_dxy(data_date=_date(10), close=103.0, weekly_change_pct=0.0)
        sig = DXYClient(cache).score()
        assert sig.confidence == 0.0
        assert sig.data_freshness == "very_stale"

    def test_raw_value_is_close_price(self):
        cache = _make_cache()
        cache.store_dxy(data_date=_date(0), close=105.2, weekly_change_pct=-0.01)
        sig = DXYClient(cache).score()
        assert sig.raw_value == pytest.approx(105.2, abs=1e-6)


class TestCacheOperations:
    """store_dxy / get_latest_dxy round-trip."""

    def test_store_and_retrieve(self):
        cache = _make_cache()
        cache.store_dxy("2026-05-10", close=104.0, weekly_change_pct=0.005)
        row = cache.get_latest_dxy()
        assert row is not None
        assert row["data_date"] == "2026-05-10"
        assert row["close"] == pytest.approx(104.0)
        assert row["weekly_change_pct"] == pytest.approx(0.005)

    def test_idempotent_upsert(self):
        cache = _make_cache()
        cache.store_dxy("2026-05-10", close=104.0, weekly_change_pct=0.005)
        cache.store_dxy("2026-05-10", close=104.5, weekly_change_pct=0.01)
        row = cache.get_latest_dxy()
        # Latest write wins on UNIQUE(data_date)
        assert row["close"] == pytest.approx(104.5)

    def test_empty_cache_returns_none(self):
        assert _make_cache().get_latest_dxy() is None

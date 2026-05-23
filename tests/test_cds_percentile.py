"""CDS history + percentile tests (D-108 Phase A / SPEC_MACRO_GATE_SOFTENING_1)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.signals.layers.macro_layer import _compute_cds_percentile
from src.signals.local.cache_store import LocalMacroCache


@pytest.fixture()
def cache(tmp_path) -> LocalMacroCache:
    return LocalMacroCache(db_path=str(tmp_path / "cds_test.db"))


def _seed_cds(cache: LocalMacroCache, values: list[float], start: date | None = None) -> None:
    """Seed N consecutive daily CDS rows (ascending by date)."""
    start = start or date(2025, 1, 1)
    for i, v in enumerate(values):
        d = (start + timedelta(days=i)).isoformat()
        cache.store_cds(data_date=d, cds_bps=v)


class TestGetCdsHistory:

    def test_round_trip_ascending(self, cache: LocalMacroCache) -> None:
        """get_cds_history returns rows in ascending date order, length-bounded."""
        _seed_cds(cache, [250.0, 260.0, 270.0])
        rows = cache.get_cds_history(days=30)
        assert len(rows) == 3
        dates = [r["data_date"] for r in rows]
        assert dates == sorted(dates)        # ascending
        assert [r["cds_bps"] for r in rows] == [250.0, 260.0, 270.0]

    def test_limit_respects_days_param(self, cache: LocalMacroCache) -> None:
        """days=5 returns at most 5 rows (most recent 5)."""
        _seed_cds(cache, [float(100 + i) for i in range(20)])
        rows = cache.get_cds_history(days=5)
        assert len(rows) == 5
        # Most recent 5 of the seeded values (115..119)
        assert [r["cds_bps"] for r in rows] == [115.0, 116.0, 117.0, 118.0, 119.0]


class TestComputeCdsPercentile:

    def test_insufficient_history_returns_none(self) -> None:
        """< 30 data points -> None (caller falls back to 0.5)."""
        history = [{"cds_bps": 250.0 + i} for i in range(29)]
        assert _compute_cds_percentile(history) is None
        assert _compute_cds_percentile([]) is None
        assert _compute_cds_percentile(None) is None

    def test_latest_is_max_yields_percentile_one(self) -> None:
        """Latest value strictly > all others -> percentile = 1.0."""
        history = [{"cds_bps": 200.0 + i} for i in range(50)]
        # Last value (249) is max
        assert _compute_cds_percentile(history) == 1.0

    def test_midpoint_yields_around_half(self) -> None:
        """Latest value equals median -> percentile around 0.5."""
        # 51 values 0..50; latest = 25 (median index)
        # Reorder so the 25 is last:
        vals = list(range(0, 26)) + list(range(26, 51)) + [25]
        # Actually simpler: latest at position 50 with value 25
        # easier: build history where last value = median
        sorted_vals = list(range(0, 50))
        history = [{"cds_bps": float(v)} for v in sorted_vals] + [{"cds_bps": 25.0}]
        pct = _compute_cds_percentile(history)
        assert pct is not None
        # 26 of 51 values <= 25 -> 26/51 = 0.5098
        assert 0.45 <= pct <= 0.55

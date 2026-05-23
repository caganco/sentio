"""Unit tests for CorrelationMatrix (SPEC_CORRELATION_MATRIX_1, Phase 4.3 Week 1)."""
import time

import numpy as np
import pandas as pd
import pytest

from src.risk.correlation_matrix import CorrelationMatrix
from src.signals.thresholds import (
    CORRELATION_MIN_SAMPLES,
    CORRELATION_WINDOW_DAYS,
)


def _make_price_df(prices: dict[str, list[float]], start="2026-01-01") -> pd.DataFrame:
    """Build long-format [stock, date, close] DataFrame from per-stock price lists."""
    n = len(next(iter(prices.values())))
    dates = pd.date_range(start=start, periods=n, freq="D")
    rows = []
    for stock, series in prices.items():
        for d, px in zip(dates, series):
            rows.append({"stock": stock, "date": d, "close": px})
    return pd.DataFrame(rows)


def _random_walk(seed: int, n: int, start: float = 100.0) -> list[float]:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1, n)
    return list(start * np.exp(np.cumsum(steps * 0.01)))


class TestCalculation:
    """Core correlation calculation."""

    def test_calculation_matches_numpy(self):
        """Correlation matches numpy.corrcoef on the same log returns."""
        a = _random_walk(seed=1, n=80)
        b = _random_walk(seed=2, n=80)
        df = _make_price_df({"AAA": a, "BBB": b})

        cm = CorrelationMatrix()
        matrix, _ = cm.calculate(df)

        # Reference: numpy corr of log returns over the same 60-day window.
        pivot = df.pivot(index="date", columns="stock", values="close").sort_index()
        pivot = pivot.iloc[-(CORRELATION_WINDOW_DAYS + 1):]
        lr = np.log(pivot / pivot.shift(1)).dropna()
        expected = np.corrcoef(lr["AAA"], lr["BBB"])[0, 1]

        assert matrix.loc["AAA", "BBB"] == pytest.approx(expected, abs=1e-9)

    def test_perfect_positive_correlation(self):
        """A monotone scaling of another series yields correlation ~ +1."""
        base = _random_walk(seed=5, n=70)
        scaled = [p * 2.0 for p in base]  # identical returns
        df = _make_price_df({"AAA": base, "BBB": scaled})

        cm = CorrelationMatrix()
        cm.calculate(df)
        assert cm.get_correlation("AAA", "BBB") == pytest.approx(1.0, abs=1e-9)

    def test_self_correlation_is_one(self):
        df = _make_price_df({"AAA": _random_walk(3, 60), "BBB": _random_walk(4, 60)})
        cm = CorrelationMatrix()
        cm.calculate(df)
        assert cm.get_correlation("AAA", "AAA") == 1.0

    def test_unknown_pair_returns_zero(self):
        df = _make_price_df({"AAA": _random_walk(7, 60), "BBB": _random_walk(8, 60)})
        cm = CorrelationMatrix()
        cm.calculate(df)
        assert cm.get_correlation("AAA", "ZZZ") == 0.0

    def test_missing_columns_raises(self):
        bad = pd.DataFrame({"stock": ["AAA"], "close": [10.0]})
        cm = CorrelationMatrix()
        with pytest.raises(ValueError, match="missing required columns"):
            cm.calculate(bad)

    def test_empty_dataframe_raises(self):
        empty = pd.DataFrame(columns=["stock", "date", "close"])
        cm = CorrelationMatrix()
        with pytest.raises(ValueError, match="empty"):
            cm.calculate(empty)

    def test_call_before_calculate_raises(self):
        cm = CorrelationMatrix()
        with pytest.raises(RuntimeError):
            cm.get_correlation("AAA", "BBB")


class TestRollingWindow:
    """60-day rolling window behaviour."""

    def test_window_truncates_to_window_days(self):
        """200 days of data -> only the last 60 returns are used."""
        long_a = _random_walk(seed=11, n=200)
        long_b = _random_walk(seed=12, n=200)
        df = _make_price_df({"AAA": long_a, "BBB": long_b})

        cm = CorrelationMatrix(window_days=60)
        cm.calculate(df)
        # Confidence caps at 1.0 with >=50 samples; 60 returns -> 1.0.
        assert cm.get_confidence("AAA") == 1.0

    def test_confidence_scales_with_samples(self):
        """30 return samples with min_samples=50 -> confidence 0.6."""
        a = _random_walk(seed=21, n=31)  # 31 prices -> 30 returns
        b = _random_walk(seed=22, n=31)
        df = _make_price_df({"AAA": a, "BBB": b})

        cm = CorrelationMatrix(window_days=60, min_samples=50)
        _, confidence = cm.calculate(df)
        assert confidence["AAA"] == pytest.approx(30 / 50, abs=1e-9)

    def test_custom_window_smaller_than_data(self):
        a = _random_walk(seed=31, n=120)
        b = _random_walk(seed=32, n=120)
        df = _make_price_df({"AAA": a, "BBB": b})

        cm = CorrelationMatrix(window_days=20, min_samples=CORRELATION_MIN_SAMPLES)
        cm.calculate(df)
        # 20-day window -> 20 returns -> confidence 20/50 = 0.4.
        assert cm.get_confidence("AAA") == pytest.approx(0.4, abs=1e-9)


class TestSectorExposure:
    """Sector exposure aggregation."""

    def test_sector_exposure_mean_of_peers(self):
        base = _random_walk(seed=41, n=70)
        df = _make_price_df({
            "GARAN": base,
            "AKBANK": [p * 1.5 for p in base],   # corr ~1 with GARAN
            "ISBANK": [p * 0.8 for p in base],   # corr ~1 with GARAN
            "TUPRS": _random_walk(seed=42, n=70),
        })
        sector_map = {
            "GARAN": "Financial",
            "AKBANK": "Financial",
            "ISBANK": "Financial",
            "TUPRS": "Energy",
        }
        cm = CorrelationMatrix()
        cm.calculate(df)
        exposure = cm.get_sector_exposure("GARAN", sector_map)
        assert exposure == pytest.approx(1.0, abs=1e-6)

    def test_sector_exposure_no_peers_returns_zero(self):
        df = _make_price_df({"GARAN": _random_walk(51, 60), "TUPRS": _random_walk(52, 60)})
        sector_map = {"GARAN": "Financial", "TUPRS": "Energy"}
        cm = CorrelationMatrix()
        cm.calculate(df)
        assert cm.get_sector_exposure("GARAN", sector_map) == 0.0

    def test_sector_exposure_unknown_stock_returns_zero(self):
        df = _make_price_df({"GARAN": _random_walk(61, 60), "AKBANK": _random_walk(62, 60)})
        cm = CorrelationMatrix()
        cm.calculate(df)
        assert cm.get_sector_exposure("XXXX", {"GARAN": "Financial"}) == 0.0


class TestClusters:
    """Cluster identification."""

    def test_correlated_stocks_cluster_together(self):
        base = _random_walk(seed=71, n=70)
        independent = _random_walk(seed=99, n=70)
        df = _make_price_df({
            "AAA": base,
            "BBB": [p * 1.3 for p in base],   # moves with AAA
            "CCC": [p * 0.7 for p in base],   # moves with AAA
            "DDD": independent,               # uncorrelated
        })
        cm = CorrelationMatrix()
        cm.calculate(df)
        clusters = cm.identify_clusters(threshold=0.9)

        # The base-driven trio should land in one cluster.
        big = max(clusters, key=len)
        assert set(big) == {"AAA", "BBB", "CCC"}
        # Every stock is assigned exactly once.
        assert sum(len(c) for c in clusters) == 4

    def test_high_threshold_no_clusters_merge(self):
        df = _make_price_df({
            "AAA": _random_walk(81, 70),
            "BBB": _random_walk(82, 70),
            "CCC": _random_walk(83, 70),
        })
        cm = CorrelationMatrix()
        cm.calculate(df)
        clusters = cm.identify_clusters(threshold=0.99)
        # Independent random walks -> each in its own singleton cluster.
        assert all(len(c) == 1 for c in clusters)
        assert len(clusters) == 3


class TestPerformance:
    """Latency benchmark — SPEC target <100ms for a 100x100 matrix."""

    def test_latency_under_100ms_for_100x100(self):
        n_stocks = 100
        n_days = CORRELATION_WINDOW_DAYS + 1
        prices = {
            f"S{i:03d}": _random_walk(seed=1000 + i, n=n_days)
            for i in range(n_stocks)
        }
        df = _make_price_df(prices)

        cm = CorrelationMatrix()
        start = time.perf_counter()
        matrix, _ = cm.calculate(df)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert matrix.shape == (n_stocks, n_stocks)
        assert elapsed_ms < 100.0, f"calculate() took {elapsed_ms:.1f}ms (target <100ms)"

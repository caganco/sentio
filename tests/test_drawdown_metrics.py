"""
Test: src.risk.drawdown_metrics — RR-016 §2.1, §8 Sanity Tests.
D-147: Vol-targeting Faz 1 (Gözlem Modu).
"""
import math

import pytest

from src.risk.drawdown_metrics import (
    compute_calmar_ratio,
    compute_current_drawdown,
    compute_sortino_ratio,
    compute_ulcer_index,
)


class TestUlcerIndex:
    """Ulcer Index — RR-016 §2.1 A4 sanity testleri."""

    def test_always_at_peak_returns_zero(self):
        """Sanity Test 1: Hep yeni peak → D'_i = 0 her gün → UI = 0."""
        series = [100.0, 105.0, 110.0, 115.0, 120.0, 130.0]
        assert compute_ulcer_index(series, n=len(series)) == 0.0

    def test_constant_5pct_dip(self):
        """Sanity Test 2: Sabit %5 dip, n=14 → UI = 5.00."""
        # peak=100, sonraki 14 gün price=95 (her gün %5 dip)
        series = [100.0] + [95.0] * 14
        result = compute_ulcer_index(series, n=14)
        assert abs(result - 5.0) < 1e-9

    def test_single_20pct_dip_then_recovery(self):
        """Sanity Test 3: Tek %20 dip + 13 gün peak → UI ≈ 5.35."""
        # Son 14 değer: [80, 100, 100, ..., 100] (1 dip + 13 peak)
        series = [100.0] + [80.0] + [100.0] * 13
        result = compute_ulcer_index(series, n=14)
        expected = math.sqrt(20.0 ** 2 / 14)  # sqrt(400/14) ≈ 5.345
        assert abs(result - expected) < 0.01

    def test_sustained_15pct_dip(self):
        """Sanity Test 4: 14 gün %15 dipte kalış → UI = 15.0."""
        series = [100.0] + [85.0] * 14
        result = compute_ulcer_index(series, n=14)
        assert abs(result - 15.0) < 1e-9

    def test_empty_series_returns_zero(self):
        """Boş seri → 0.0 (güvenli fallback)."""
        assert compute_ulcer_index([]) == 0.0

    def test_single_element_returns_zero(self):
        """Tek eleman → dip yok → 0.0."""
        assert compute_ulcer_index([100.0], n=1) == 0.0


class TestCalmarRatio:
    """Calmar Ratio — RR-016 §2.1 A5 sanity testleri."""

    def test_bist_2024_proxy(self):
        """BIST 2024 proxy: +%20 nominal, MDD ~%15 → Calmar ≈ 1.33."""
        daily_return = 0.20 / 252
        returns = [daily_return] * 252
        result = compute_calmar_ratio(returns, mdd=0.15)
        assert abs(result - 0.20 / 0.15) < 0.01

    def test_calmar_30pct_return_20pct_mdd(self):
        """Sanity Test 1: %30 getiri, MDD=%20 → Calmar = 1.5."""
        daily_return = 0.30 / 252
        returns = [daily_return] * 252
        result = compute_calmar_ratio(returns, mdd=0.20)
        assert abs(result - 1.5) < 0.01

    def test_zero_mdd_returns_zero(self):
        """MDD = 0 → sıfıra bölme koruması → 0.0."""
        assert compute_calmar_ratio([0.01] * 10, mdd=0.0) == 0.0

    def test_empty_returns_returns_zero(self):
        """Boş seri → 0.0."""
        assert compute_calmar_ratio([], mdd=0.15) == 0.0


class TestSortinoRatio:
    """Sortino Ratio — RR-016 §8 sanity testi."""

    def test_sortino_sanity_rr016(self):
        """RR-016 §8: [5,3,-2,-4,6,1,-1,4,3,-3,2,5], MAR=0 → Sortino ≈ 1.0."""
        returns = [5, 3, -2, -4, 6, 1, -1, 4, 3, -3, 2, 5]
        result = compute_sortino_ratio(returns, mar=0)
        assert abs(result - 1.0) < 0.01

    def test_no_negative_returns_zero_downside(self):
        """Negatif getiri yok → downside_dev = 0 → Sortino = 0.0."""
        returns = [1.0, 2.0, 3.0, 4.0]
        assert compute_sortino_ratio(returns, mar=0) == 0.0

    def test_empty_returns_returns_zero(self):
        """Boş seri → 0.0."""
        assert compute_sortino_ratio([]) == 0.0


class TestCurrentDrawdown:
    """compute_current_drawdown: peak-to-current DD testleri."""

    def test_at_peak_returns_zero(self):
        """Sürekli yükselen seri → son değer = peak → DD = 0."""
        assert compute_current_drawdown([100.0, 105.0, 110.0]) == 0.0

    def test_peak_tracking(self):
        """100 peak → 80 son değer → DD = 0.20."""
        result = compute_current_drawdown([100.0, 90.0, 80.0])
        assert abs(result - 0.20) < 1e-9

    def test_partial_recovery(self):
        """100 peak → 70 dip → 85 kısmi recovery → DD = 0.15."""
        result = compute_current_drawdown([100.0, 70.0, 85.0])
        assert abs(result - 0.15) < 1e-9

    def test_empty_series_returns_zero(self):
        """Boş seri → 0.0."""
        assert compute_current_drawdown([]) == 0.0

    def test_drawdown_non_negative(self):
        """DD her zaman ≥ 0."""
        result = compute_current_drawdown([50.0, 100.0, 110.0])
        assert result == 0.0  # Son değer peak → 0 DD

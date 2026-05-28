"""D-169: TÜFE-deflate reel getiri birim testleri.

Saf hesap testleri — EVDS ag cagrisi yok, BacktestEngine ornegi yok.
Synthetic TÜFE serisi: linspace ile sabit kumulatif enflasyon.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import TUFE_UNAVAILABLE, calculate_real_returns


def _make_tufe(start: str, end: str, cumulative_inflation: float) -> pd.Series:
    """Verilen kumulatif enflasyon ile gunluk TÜFE serisi uretir (ffill monthly)."""
    monthly_idx = pd.date_range(start=start, end=end, freq="MS")
    n = len(monthly_idx)
    start_val = 1000.0
    end_val = start_val * (1.0 + cumulative_inflation)
    monthly = pd.Series(np.linspace(start_val, end_val, n), index=monthly_idx)
    daily_idx = pd.date_range(start=start, end=end, freq="D")
    return monthly.reindex(daily_idx, method="ffill")


class TestRealReturnDeflation:
    """D-169: TÜFE-deflate formul ve fallback davranisi."""

    def test_deflates_nominal_return_correctly(self):
        """20% kumulatif enflasyon: (1.395 / 1.20) - 1 = %16.25."""
        tufe = _make_tufe("2024-01-01", "2026-04-30", 0.20)
        result = calculate_real_returns(
            nominal_return=0.395,
            benchmark_return=0.8771,
            tufe_series=tufe,
            start_date="2024-01-01",
            end_date="2026-04-30",
            holding_days=580,
        )
        assert result["real_return_pct"] != TUFE_UNAVAILABLE
        expected = (1.395 / 1.20 - 1.0) * 100
        assert abs(result["real_return_pct"] - expected) < 0.1, (
            f"Beklenen ~{expected:.2f}%, got {result['real_return_pct']}"
        )

    def test_returns_sentinel_when_tufe_none(self):
        """None TÜFE serisi → tum alanlar TÜFE_UNAVAILABLE."""
        result = calculate_real_returns(
            nominal_return=0.30,
            benchmark_return=0.50,
            tufe_series=None,
            start_date="2024-01-01",
            end_date="2026-04-30",
            holding_days=580,
        )
        assert result["real_return_pct"] == TUFE_UNAVAILABLE
        assert result["benchmark_real_return_pct"] == TUFE_UNAVAILABLE
        assert result["real_alpha_pct"] == TUFE_UNAVAILABLE
        assert result["avg_annual_tufe_pct"] == TUFE_UNAVAILABLE

    def test_returns_sentinel_when_tufe_empty(self):
        """Bos Series → sentinel."""
        result = calculate_real_returns(
            nominal_return=0.30,
            benchmark_return=0.50,
            tufe_series=pd.Series(dtype=float),
            start_date="2024-01-01",
            end_date="2026-04-30",
            holding_days=580,
        )
        assert result["real_return_pct"] == TUFE_UNAVAILABLE

    def test_real_alpha_equals_difference(self):
        """real_alpha_pct = real_return_pct - benchmark_real_return_pct."""
        tufe = _make_tufe("2024-01-01", "2026-04-30", 0.60)
        result = calculate_real_returns(
            nominal_return=0.395,
            benchmark_return=0.8771,
            tufe_series=tufe,
            start_date="2024-01-01",
            end_date="2026-04-30",
            holding_days=580,
        )
        assert result["real_alpha_pct"] != TUFE_UNAVAILABLE
        expected_alpha = round(
            float(result["real_return_pct"]) - float(result["benchmark_real_return_pct"]), 2
        )
        assert abs(result["real_alpha_pct"] - expected_alpha) < 0.01, (
            f"real_alpha={result['real_alpha_pct']}, expected {expected_alpha}"
        )

    def test_avg_annual_tufe_within_plausible_range(self):
        """60% kumulatif / ~580 gun (~2.3 yil) → yillik %20-35 arasi."""
        tufe = _make_tufe("2024-01-01", "2026-04-30", 0.60)
        result = calculate_real_returns(
            nominal_return=0.395,
            benchmark_return=0.8771,
            tufe_series=tufe,
            start_date="2024-01-01",
            end_date="2026-04-30",
            holding_days=580,
        )
        assert result["avg_annual_tufe_pct"] != TUFE_UNAVAILABLE
        ann = float(result["avg_annual_tufe_pct"])
        assert 15.0 < ann < 45.0, (
            f"Yillik TÜFE {ann:.1f}% — 2.3 yilda 60% icin makul aralik 15-45%"
        )

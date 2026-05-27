"""D-161/D-168: Period-adjusted Sharpe + IR + Calmar + benchmark NaN fix tests.

Dayanak: validation_constants.SHARPE_PASS_THRESHOLD, IR_PASS_THRESHOLD,
         CALMAR_PASS_THRESHOLD, CALMAR_STRONG_THRESHOLD
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import calculate_alpha, calculate_ir, calculate_sharpe
from src.backtest.validation_constants import (
    CALMAR_PASS_THRESHOLD,
    CALMAR_STRONG_THRESHOLD,
    IR_PASS_THRESHOLD,
    SHARPE_PASS_THRESHOLD,
)


# ── TestSharpePeriodAdjusted ──────────────────────────────────────────────────


class TestSharpePeriodAdjusted:
    """Period-adjusted Sharpe formula dogrulamasi (D-161)."""

    def test_positive_return_beats_rf_period(self):
        """Donem RF'ini gecen getiri pozitif Sharpe uretmeli.

        170 gun, +35% toplam getiri, %42 RF:
          rf_period = 0.42 * (170/252) = 0.2835
          excess    = 0.35 - 0.2835   = +0.0665 → Sharpe > 0
        """
        n = 170
        start = 100_000.0
        total_return = 0.35
        daily_ret = (1 + total_return) ** (1 / n) - 1
        curve = [start]
        for _ in range(n):
            curve.append(curve[-1] * (1 + daily_ret))
        sharpe = calculate_sharpe(curve, rf_rate=0.42)
        assert sharpe > 0.0, (
            f"35% > rf_period(28.35%) -> pozitif Sharpe beklenir, got {sharpe}"
        )

    def test_below_rf_period_negative_sharpe(self):
        """Donem RF'inin altinda kalan getiri negatif Sharpe uretmeli.

        170 gun, yakl. +10.6% getiri, %42 RF:
          rf_period = 0.42 * (170/252) = 0.2835
          excess    = 0.106 - 0.2835   = -0.1775 -> Sharpe < 0
        Sep-Nis 2026 backtest senaryosu: +10.60%, RF=42%.
        Gercekci gürültü ile (annual_vol sifirdan uzak kalmali).
        """
        n = 170
        start = 100_000.0
        # Hedef ~+10.6% total; gürültü ekleyerek realistic vol sagla
        rng = np.random.default_rng(seed=7)
        # ~0.059% gunluk drift -> 170 gun ~ +10.6%, vol=1% gunluk
        noise = rng.normal(0.00059, 0.01, n)
        curve = [start]
        for r in noise:
            curve.append(curve[-1] * (1 + r))
        actual_return = (curve[-1] - start) / start
        sharpe = calculate_sharpe(curve, rf_rate=0.42)
        # actual_return yaklasik 0.10; rf_period=0.2835 -> excess negatif
        assert actual_return < 0.28, (
            f"Test kurulumu: return {actual_return:.2%} < rf_period(28.35%) olmali"
        )
        assert sharpe < 0.0, (
            f"return({actual_return:.2%}) < rf_period(28.35%) -> negatif Sharpe beklenir, got {sharpe}"
        )
        assert sharpe > -10.0, f"Asiri negatif deger: {sharpe}"

    def test_zero_rf_equals_return_over_vol(self):
        """rf_rate=0 iken Sharpe = (total_return/annual_vol) * sqrt(252/n)."""
        rng = np.random.default_rng(42)
        daily_rets = rng.normal(0.001, 0.01, 100)
        curve = [100_000.0]
        for r in daily_rets:
            curve.append(curve[-1] * (1 + r))
        sharpe_zero_rf = calculate_sharpe(curve, rf_rate=0.0)
        # Manuel hesap: rf=0 -> excess = total_return
        arr = np.array(curve)
        dr = np.diff(arr) / arr[:-1]
        av = float(np.std(dr)) * np.sqrt(252)
        tr = (arr[-1] - arr[0]) / arr[0]
        expected = float((tr / av) * np.sqrt(252 / len(dr)))
        assert abs(sharpe_zero_rf - expected) < 1e-9, (
            f"rf=0 Sharpe mismatch: got {sharpe_zero_rf}, expected {expected}"
        )

    def test_insufficient_data_returns_zero(self):
        """Tek noktali equity curve 0.0 dondurmeli."""
        assert calculate_sharpe([100_000.0]) == 0.0
        assert calculate_sharpe([]) == 0.0

    def test_zero_volatility_returns_zero(self):
        """Sabit equity curve (sifir vol) 0.0 dondurmeli."""
        curve = [100_000.0] * 50
        assert calculate_sharpe(curve) == 0.0


# ── TestIRCalculation ─────────────────────────────────────────────────────────


class TestIRCalculation:
    """Information Ratio hesaplamasi (D-161)."""

    def test_positive_ir_when_portfolio_beats_benchmark(self):
        """Portfolio benchmark'i tutarli sekilde geciyorsa IR pozitif olmali."""
        n = 252
        bench = [0.0005] * n   # benchmark: +0.05%/gun
        port  = [0.0010] * n   # portfolio: +0.10%/gun (sabit outperform)
        ir = calculate_ir(port, bench)
        assert ir > 0.0, f"Tutarli outperform -> IR > 0 beklenir, got {ir}"

    def test_zero_ir_when_tracking_benchmark(self):
        """Portfolio == benchmark olunca std(active)=0 -> IR=0 olmali."""
        returns = [0.001 * (i % 5) for i in range(100)]
        ir = calculate_ir(returns, returns)
        assert ir == 0.0, f"Portfolio == benchmark -> IR=0 beklenir, got {ir}"

    def test_ir_annualization_factor(self):
        """IR sqrt(252) ile annualize edilmeli."""
        n = 252
        rng = np.random.default_rng(0)
        port  = list(rng.normal(0.001, 0.015, n))
        bench = list(rng.normal(0.0005, 0.015, n))
        ir = calculate_ir(port, bench)
        # Manuel hesap
        active = np.array(port) - np.array(bench)
        expected = float(np.mean(active) / np.std(active) * np.sqrt(252))
        assert abs(ir - expected) < 1e-9, (
            f"IR annualization mismatch: got {ir}, expected {expected}"
        )

    def test_insufficient_data_returns_zero(self):
        """Tek noktali listeler 0.0 dondurmeli."""
        assert calculate_ir([0.001], [0.001]) == 0.0
        assert calculate_ir([], []) == 0.0


# ── TestBenchmarkNaNFix ───────────────────────────────────────────────────────


class TestBenchmarkNaNFix:
    """D-168: calculate_alpha() NaN baslangi degerini tolere etmeli."""

    def test_nan_start_skipped_uses_first_valid(self):
        """Baslangic NaN ise first_valid_index() kullanilmali (tatil gunu sorunu)."""
        idx = pd.date_range("2024-01-01", periods=5)
        series = pd.Series([float("nan"), 10_000.0, 10_200.0, 10_100.0, 10_500.0], index=idx)
        equity = [100_000.0, 105_000.0]
        result = calculate_alpha(equity, series, 100_000.0)
        assert not math.isnan(result["benchmark_return"]), "NaN baslangic degerinin atlanmasi gerekiyor"
        # 10_000 -> 10_500 = +%5
        assert abs(result["benchmark_return"] - 0.05) < 1e-9

    def test_all_nan_returns_nan(self):
        """Tum degerler NaN ise benchmark_return=nan dondurmeli."""
        series = pd.Series([float("nan"), float("nan")])
        result = calculate_alpha([100_000.0, 105_000.0], series, 100_000.0)
        assert math.isnan(result["benchmark_return"])
        assert math.isnan(result["alpha"])

    def test_valid_series_unchanged(self):
        """NaN olmayan normal seriler onceki gibi calismalı."""
        series = pd.Series([10_000.0, 11_000.0, 12_000.0])
        result = calculate_alpha([100_000.0, 110_000.0], series, 100_000.0)
        assert abs(result["benchmark_return"] - 0.2) < 1e-9   # 10k -> 12k = +%20
        assert abs(result["system_return"] - 0.10) < 1e-9    # 100k -> 110k = +%10


# ── TestCalmarRatio ───────────────────────────────────────────────────────────


class TestCalmarRatio:
    """D-168: Calmar Ratio sabitleri ve esik kontrolu."""

    def test_calmar_pass_threshold_value(self):
        assert CALMAR_PASS_THRESHOLD == 1.0

    def test_calmar_strong_threshold_value(self):
        assert CALMAR_STRONG_THRESHOLD == 3.0

    def test_calmar_formula(self):
        """Calmar = |toplam_getiri| / |max_dd| mantiği."""
        total_return = 0.3995   # +39.95%
        max_dd = -0.1087        # -10.87%
        calmar = abs(total_return / max_dd)
        assert abs(calmar - 3.674) < 0.01, f"Beklenen ~3.67, got {calmar:.3f}"
        assert calmar >= CALMAR_STRONG_THRESHOLD

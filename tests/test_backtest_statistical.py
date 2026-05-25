"""Statistical validation tests — D-150d (SPEC_STATISTICAL_VALIDATION_1 §5).

19 test:
  TestPurgedKFold           (4)
  TestCombinatorialPurgedCV (3)
  TestDSR                   (4)
  TestPBO                   (3)
  TestMinBTL                (3)
  TestNeweyWest             (2)

Kısıtlar:
  - np.random.seed(42) deterministik — seed değiştirme
  - Canlı API çağrısı yok (unit test)
  - BacktestEngine import edilmez (pure-math tests)
  - TestNeweyWest: lags=0 IID baseline kullanır (rf_rate uyumsuzluğu nedeniyle
    calculate_sharpe() kullanılmaz — bkz. D-150d plan notu)

Dayanak: SPEC_STATISTICAL_VALIDATION_1 §5
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.cross_validation import CombinatorialPurgedCV, PurgedKFold
from src.backtest.statistical_validation import (
    compute_dsr,
    compute_pbo,
    min_btl_days,
    sharpe_newey_west,
)
from src.backtest.validation_constants import (
    DSR_THRESHOLD,
    MIN_BACKTEST_DAYS,
    PBO_THRESHOLD,
)

pytestmark = pytest.mark.new

# ── Modül düzeyinde test verisi ───────────────────────────────────────────────

_N = 750
_DATES = pd.date_range("2020-01-01", periods=_N, freq="B")


# ── TestPurgedKFold (4 test) ──────────────────────────────────────────────────

class TestPurgedKFold:
    """PurgedKFold: temporal K-Fold + purge + embargo garantileri."""

    def test_split_yields_n_splits(self):
        """n_splits=5 → 5 (train, test) tuple üretilir."""
        pkf = PurgedKFold(n_splits=5, purge_days=10, embargo_days=5)
        folds = list(pkf.split(_DATES))
        assert len(folds) == 5

    def test_purge_removes_samples_before_test(self):
        """purge_days=10 → test_start - 10 gün içindeki train sample yok."""
        pkf = PurgedKFold(n_splits=5, purge_days=10, embargo_days=5)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        for train_idx, test_idx in pkf.split(dates):
            test_start = dates[test_idx[0]]
            purge_cutoff = test_start - pd.Timedelta(days=10)
            # [purge_cutoff, test_start) arasındaki indeksler train'de olmamalı
            purge_mask = (dates >= purge_cutoff) & (dates < test_start)
            purge_indices = np.where(purge_mask)[0]
            overlap = np.intersect1d(train_idx, purge_indices)
            assert len(overlap) == 0, (
                f"Purge zone leakage: {len(overlap)} samples in train"
            )

    def test_embargo_removes_samples_after_test(self):
        """embargo_days=5 → test_end + 5 gün içindeki train sample yok."""
        pkf = PurgedKFold(n_splits=5, purge_days=10, embargo_days=5)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        for train_idx, test_idx in pkf.split(dates):
            test_end = dates[test_idx[-1]]
            embargo_cutoff = test_end + pd.Timedelta(days=5)
            # (test_end, embargo_cutoff] arasındaki indeksler train'de olmamalı
            embargo_mask = (dates > test_end) & (dates <= embargo_cutoff)
            embargo_indices = np.where(embargo_mask)[0]
            overlap = np.intersect1d(train_idx, embargo_indices)
            assert len(overlap) == 0, (
                f"Embargo zone leakage: {len(overlap)} samples in train"
            )

    def test_no_data_leakage_train_test_overlap(self):
        """train_idx ∩ test_idx = ∅ tüm fold'larda."""
        pkf = PurgedKFold(n_splits=5, purge_days=10, embargo_days=5)
        for train_idx, test_idx in pkf.split(_DATES):
            assert len(np.intersect1d(train_idx, test_idx)) == 0


# ── TestCombinatorialPurgedCV (3 test) ────────────────────────────────────────

class TestCombinatorialPurgedCV:
    """CombinatorialPurgedCV: C(N,k) path üretimi ve overlap garantisi."""

    def test_n_paths_equals_c_n_k(self):
        """C(6,2) == 15."""
        cpcv = CombinatorialPurgedCV(N=6, k=2)
        assert cpcv.n_paths == 15

    def test_split_returns_correct_count(self):
        """split() → tam olarak n_paths tuple döner."""
        cpcv = CombinatorialPurgedCV(N=6, k=2)
        paths = cpcv.split(_DATES)
        assert len(paths) == cpcv.n_paths == 15

    def test_test_indices_non_overlapping_within_path(self):
        """Her path'te train_idx ∩ test_idx = ∅."""
        cpcv = CombinatorialPurgedCV(N=6, k=2)
        for train_idx, test_idx in cpcv.split(_DATES):
            assert len(np.intersect1d(train_idx, test_idx)) == 0


# ── TestDSR (4 test) ──────────────────────────────────────────────────────────

class TestDSR:
    """Deflated Sharpe Ratio — Bailey & López de Prado (2014)."""

    def test_high_consistent_sharpe_yields_dsr_above_threshold(self):
        """15 path, hepsi SR=2.0 → DSR > 0.95."""
        dsr = compute_dsr([2.0] * 15, T=250)
        assert dsr > 0.95

    def test_negative_sharpe_yields_low_dsr(self):
        """SR=-1.0 → DSR < 0.10."""
        dsr = compute_dsr([-1.0] * 15, T=250)
        assert dsr < 0.10

    def test_dsr_threshold_constant_value(self):
        """DSR_THRESHOLD == 0.95 (regresyon koruması)."""
        assert DSR_THRESHOLD == 0.95

    def test_fat_tail_kurtosis_reduces_dsr(self):
        """kurtosis=6 (fat tail) aynı SR için daha düşük DSR üretir.

        Not: T=15, SR=0.5 kullanılır — T=250 ile norm.cdf saturasyona girer
        (DSR≈1.0 her iki kurtosis için), fark ölçülemez. D-150c plan notu.
        Hesap: norm.cdf(1.764)=0.961 vs norm.cdf(1.634)=0.949 → 0.949 < 0.961.
        """
        dsr_normal = compute_dsr([0.5] * 15, T=15, kurtosis=3.0)
        dsr_fat    = compute_dsr([0.5] * 15, T=15, kurtosis=6.0)
        assert dsr_fat < dsr_normal


# ── TestPBO (3 test) ──────────────────────────────────────────────────────────

class TestPBO:
    """Probability of Backtest Overfitting — konservatif frekans yaklaşımı."""

    def test_all_positive_sharpe_yields_zero_pbo(self):
        """15 path, hepsi SR > 0 → PBO = 0.0."""
        assert compute_pbo([1.0, 0.5, 2.0, 0.1, 0.3] * 3) == 0.0

    def test_all_negative_sharpe_yields_one_pbo(self):
        """15 path, hepsi SR < 0 → PBO = 1.0."""
        assert compute_pbo([-1.0] * 15) == 1.0

    def test_pbo_threshold_constant_value(self):
        """PBO_THRESHOLD == 0.50 (regresyon koruması)."""
        assert PBO_THRESHOLD == 0.50


# ── TestMinBTL (3 test) ───────────────────────────────────────────────────────

class TestMinBTL:
    """MinBTL — parametrik form + validation_constants bağlayıcı değer."""

    def test_min_btl_n12_sr15_approx_307(self):
        """N=12, SR=1.5 → parametrik formül ~307 gün verir ([250, 400] tolerans).

        Not: MIN_BACKTEST_DAYS=553 RR-018 bağlayıcı değerdir;
        bu test parametrik fonksiyonu doğrular, constanti değil.
        """
        result = min_btl_days(n_trials=12, target_sr=1.5, annual_factor=250)
        assert 250 <= result <= 400

    def test_min_btl_increases_with_n_trials(self):
        """Daha fazla deneme → daha uzun MinBTL gereksinimi."""
        assert min_btl_days(n_trials=20) > min_btl_days(n_trials=10)

    def test_min_backtest_days_constant(self):
        """MIN_BACKTEST_DAYS == 553 (RR-018 §6.1 bağlayıcı değer, regresyon koruması)."""
        assert MIN_BACKTEST_DAYS == 553


# ── TestNeweyWest (2 test) ────────────────────────────────────────────────────

class TestNeweyWest:
    """Newey-West HAC Sharpe — Bartlett kernel, IID karşılaştırması.

    Baseline olarak sharpe_newey_west(lags=0) kullanılır (lags=0 → boş döngü
    → var_nw = sample_var, IID varsayımı). calculate_sharpe() kullanılmaz;
    rf_rate=0.42 (TCMB) nedeniyle sharpe_newey_west() ile karşılaştırılamaz.
    """

    def test_nw_sharpe_lower_than_naive_for_autocorrelated_returns(self):
        """Pozitif otokorelasyonlu seriler: HAC düzeltmesi Sharpe'ı düşürür.

        Seri: autocorr[i] = 0.4*base[i-1] + 0.6*base[i]
        → Lag-1 cov = 0.24*σ² > 0 → HAC var artışı → SR_NW < SR_IID
        """
        np.random.seed(42)
        base = np.random.normal(0.001, 0.015, 300)
        autocorr = 0.4 * np.roll(base, 1) + 0.6 * base
        autocorr[0] = base[0]
        # HAC (lags=5) vs IID-varsayımı (lags=0)
        nw_hac = sharpe_newey_west(autocorr, lags=5)
        nw_iid = sharpe_newey_west(autocorr, lags=0)
        # Pozitif otokorelasyon HAC varyansını artırır → Sharpe düşer
        assert nw_hac < nw_iid

    def test_nw_sharpe_close_to_naive_for_iid_returns(self):
        """IID returns → HAC düzeltmesi minimal etki (≤15% tolerans).

        500 IID örnek: lag-k otokovaryans ≈ 0 → var_nw ≈ var → SR_NW ≈ SR_IID
        """
        np.random.seed(7)
        iid_returns = np.random.normal(0.0008, 0.012, 500)
        nw_hac = sharpe_newey_west(iid_returns, lags=5)
        nw_iid = sharpe_newey_west(iid_returns, lags=0)
        assert abs(nw_hac - nw_iid) / (abs(nw_iid) + 1e-9) < 0.15

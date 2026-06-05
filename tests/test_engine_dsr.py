"""Tests for the FAZ-4 (b) DSR trial-count deflation (src/engine/dsr.py).

Pins:
- ``expected_max_sharpe(N)`` at N=1 (-> 0.0, no deflation) and N=2/10/100
  (hand-computed Bailey-LdP order-statistic values, Euler-Mascheroni);
- ``deflation_benchmark_sr`` returns 0 at N<=1 / T<=1 / degenerate denom, and is
  positive + monotone-increasing in N otherwise;
- the IDENTITY: feeding the benchmark to the committed ``compute_dsr`` reproduces
  the canonical deflated DSR = Phi(SR_obs/se_SR - E[max_N]);
- N=1 reproduces the pre-FAZ-4 (benchmark_sr=0) DSR byte-for-byte (zero regression);
- N>>1 strictly lowers the DSR (deflation bites).

Strangler note: every assert below calls the COMMITTED ``compute_dsr`` unchanged;
the engine only computes the ``benchmark_sr`` it has always accepted.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.stats import norm

from src.backtest.statistical_validation import compute_dsr
from src.engine.dsr import deflation_benchmark_sr, expected_max_sharpe


class TestExpectedMaxSharpe:
    def test_single_or_fewer_trials_is_zero(self):
        # N<=1: no multiple-test inflation, and Phi^-1(0) = -inf would be undefined.
        assert expected_max_sharpe(1) == 0.0
        assert expected_max_sharpe(0) == 0.0
        assert expected_max_sharpe(-5) == 0.0

    @pytest.mark.parametrize(
        ("n", "expected"),
        [
            (2, 0.5197553442792135),
            (10, 1.5745983013449718),
            (100, 2.5306028932011424),
        ],
    )
    def test_matches_hand_computed(self, n, expected):
        assert expected_max_sharpe(n) == pytest.approx(expected, rel=1e-12)

    def test_monotone_increasing_in_n(self):
        vals = [expected_max_sharpe(n) for n in (2, 5, 10, 50, 100, 1000)]
        assert all(b > a for a, b in zip(vals, vals[1:], strict=False))


class TestDeflationBenchmark:
    def test_no_deflation_below_two_trials(self):
        assert deflation_benchmark_sr(0.5, 250, 0.0, 3.0, 1) == 0.0
        assert deflation_benchmark_sr(0.5, 250, 0.0, 3.0, 0) == 0.0

    def test_degenerate_T_is_zero(self):
        assert deflation_benchmark_sr(0.5, 1, 0.0, 3.0, 10) == 0.0
        assert deflation_benchmark_sr(0.5, 0, 0.0, 3.0, 10) == 0.0

    def test_degenerate_denominator_is_zero(self):
        # denom_sq = 1 - skew*sr + (kurt-1)/4*sr^2 <= 0 -> 0.0 (compute_dsr also bails).
        assert deflation_benchmark_sr(2.0, 250, 5.0, 3.0, 10) == 0.0

    def test_positive_and_monotone_in_n(self):
        b10 = deflation_benchmark_sr(0.5, 250, 0.0, 3.0, 10)
        b100 = deflation_benchmark_sr(0.5, 250, 0.0, 3.0, 100)
        assert 0.0 < b10 < b100

    def test_equals_se_times_expected_max(self):
        # benchmark == se_SR * E[max_N], se_SR = sqrt(denom_sq/(T-1)),
        # denom_sq = 1 - skew*sr + (kurt-1)/4*sr^2 (re-derived independently here).
        sr_obs, T, sk, ku, n = 0.5, 250, 0.0, 3.0, 10
        b = deflation_benchmark_sr(sr_obs, T, sk, ku, n)
        denom_sq = 1.0 - sk * sr_obs + ((ku - 1.0) / 4.0) * sr_obs**2
        se = math.sqrt(denom_sq / (T - 1))
        assert b == pytest.approx(se * expected_max_sharpe(n), rel=1e-12)


class TestDsrDeflationIdentity:
    # a modest OOS Sharpe distribution with mild non-normality, kept small enough
    # that Phi is NOT saturated at 1.0 (so deflation visibly moves the DSR).
    _SR = [0.05, 0.15, 0.10, 0.20, 0.08]
    _T, _SK, _KU = 250, 0.1, 3.5

    def test_n1_reproduces_undeflated_dsr(self):
        sr_obs = float(np.mean(self._SR))
        b = deflation_benchmark_sr(sr_obs, self._T, self._SK, self._KU, 1)
        assert b == 0.0
        d_n1 = compute_dsr(self._SR, T=self._T, skewness=self._SK, kurtosis=self._KU, benchmark_sr=b)
        d_current = compute_dsr(self._SR, T=self._T, skewness=self._SK, kurtosis=self._KU)
        assert d_n1 == d_current  # byte-identical -> zero regression

    def test_canonical_identity(self):
        sr_obs = float(np.mean(self._SR))
        n = 20
        b = deflation_benchmark_sr(sr_obs, self._T, self._SK, self._KU, n)
        dsr = compute_dsr(self._SR, T=self._T, skewness=self._SK, kurtosis=self._KU, benchmark_sr=b)
        # independent re-derivation: Phi(SR_obs/se_SR - E[max_N]).
        denom_sq = 1.0 - self._SK * sr_obs + ((self._KU - 1.0) / 4.0) * sr_obs**2
        se = math.sqrt(denom_sq / (self._T - 1))
        canonical = float(norm.cdf(sr_obs / se - expected_max_sharpe(n)))
        assert dsr == pytest.approx(canonical, rel=1e-12)

    def test_deflation_strictly_lowers_dsr(self):
        sr_obs = float(np.mean(self._SR))
        d1 = compute_dsr(self._SR, T=self._T, skewness=self._SK, kurtosis=self._KU)
        b = deflation_benchmark_sr(sr_obs, self._T, self._SK, self._KU, 100)
        d100 = compute_dsr(self._SR, T=self._T, skewness=self._SK, kurtosis=self._KU, benchmark_sr=b)
        assert d100 < d1

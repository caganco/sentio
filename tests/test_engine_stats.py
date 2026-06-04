"""Tier-A tests for the engine stats core (rank-IC / IR / Newey-West t).

The NW-equivalence block pins the engine estimator to the committed precedents
(``d213``/``d211`` ``nw_mean_tstat``), which share the population-variance
convention of the untracked ``c9._nw_t`` that produced the C12 golden. The
``c9``-golden reproduction itself is a Faz-3 hard gate (placeholder below).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.engine.stats import ic_ir, nw_tstat, rank_ic_series
from src.screening.d211_foreign_flow import nw_mean_tstat as d211_nw
from src.screening.d213_real_rate import nw_mean_tstat as d213_nw


def _aligned_panels(n_dates: int = 6, n_names: int = 40, sign: float = 1.0):
    dates = pd.bdate_range("2022-01-03", periods=n_dates)
    names = [f"S{i:02d}" for i in range(n_names)]
    base = np.arange(n_names, dtype=float)
    scores = pd.DataFrame([base] * n_dates, index=dates, columns=names)
    fwd = pd.DataFrame([sign * base] * n_dates, index=dates, columns=names)
    return scores, fwd


class TestRankIC:
    def test_monotone_is_plus_one(self):
        scores, fwd = _aligned_panels(sign=1.0)
        ic = rank_ic_series(scores, fwd)
        assert len(ic) == 6
        assert ic.to_numpy() == pytest.approx(1.0)

    def test_antimonotone_is_minus_one(self):
        scores, fwd = _aligned_panels(sign=-1.0)
        ic = rank_ic_series(scores, fwd)
        assert ic.to_numpy() == pytest.approx(-1.0)

    def test_min_names_floor_drops_thin_dates(self):
        scores, fwd = _aligned_panels(n_dates=4, n_names=40)
        # Blank out 15 names on the 2nd date -> 25 pairs < 30 floor -> dropped.
        thin = scores.index[1]
        scores.loc[thin, scores.columns[:15]] = np.nan
        ic = rank_ic_series(scores, fwd, min_names=30)
        assert thin not in ic.index
        assert len(ic) == 3

    def test_below_floor_everywhere_is_empty(self):
        scores, fwd = _aligned_panels(n_names=20)  # 20 < 30
        ic = rank_ic_series(scores, fwd, min_names=30)
        assert ic.empty


class TestIR:
    def test_known_value(self):
        assert ic_ir(pd.Series([1.0, 2.0, 3.0])) == pytest.approx(2.0)  # mean 2 / std 1

    def test_sign_flips(self):
        assert ic_ir(pd.Series([-1.0, -2.0, -3.0])) == pytest.approx(-2.0)

    def test_scale_invariant(self):
        assert ic_ir(pd.Series([2.0, 4.0, 6.0])) == pytest.approx(ic_ir(pd.Series([1.0, 2.0, 3.0])))

    def test_degenerate_is_nan(self):
        assert np.isnan(ic_ir(pd.Series([5.0, 5.0, 5.0])))  # zero dispersion
        assert np.isnan(ic_ir(pd.Series([1.0])))  # < 2 obs


class TestNeweyWestEquivalence:
    @pytest.mark.parametrize("lag", [3, 6, 10])
    def test_matches_committed_d213_and_d211(self, lag):
        rng = np.random.default_rng(20260605)
        x = rng.standard_normal(200) * 0.01 + 0.0008  # autocorr-free, finite n
        t_engine = nw_tstat(x, lag=lag)
        assert t_engine == pytest.approx(d213_nw(x, lag=lag)[0], rel=1e-12, abs=1e-12)
        assert t_engine == pytest.approx(d211_nw(x, lag=lag)[0], rel=1e-12, abs=1e-12)


class TestNeweyWestEdges:
    def test_below_guard_is_nan(self):
        assert np.isnan(nw_tstat(np.zeros(5), lag=3))  # n=5 < lag+3=6

    def test_zero_variance_is_nan(self):
        # Exact-constant -> deviations are exactly 0 -> HAC variance 0 -> NaN.
        # (np.full(50, 0.7) would NOT qualify: 0.7 is inexact, so FP rounding
        # leaves a ~1e-30 dispersion and yields a huge finite t -- that is the
        # near-constant case covered by test_perfect_signal_is_large_t.)
        assert np.isnan(nw_tstat(np.ones(50), lag=5))

    def test_perfect_signal_is_large_t(self):
        x = 0.05 + np.zeros(60)
        x[::2] += 1e-6  # tiny dispersion so variance > 0
        assert nw_tstat(x, lag=5) > 50.0

    def test_pure_noise_is_small_t(self):
        rng = np.random.default_rng(7)
        assert abs(nw_tstat(rng.standard_normal(400), lag=5)) < 3.0

    def test_drops_nonfinite(self):
        rng = np.random.default_rng(11)
        x = rng.standard_normal(200) * 0.01 + 0.001
        x_holes = x.copy()
        x_holes[5] = np.nan
        x_holes[50] = np.inf
        # Same finite subset -> identical t to the explicitly-cleaned array.
        clean = x[np.isfinite(x_holes)]
        assert nw_tstat(x_holes, lag=5) == pytest.approx(nw_tstat(clean, lag=5))


@pytest.mark.skip(
    reason="Faz-3 HARD GATE (not optional): nw_tstat(pooled C12 OOS active return, "
    "lag=10) must reproduce the c9 golden NW-t == approx(6.928414) on the real, "
    "gitignored data. Filled once the Faz-3 expanding-WF cut-policy + C12 Signal + "
    "per-name D-207 cost wiring + Section-7 report fields exist."
)
def test_nw_reproduces_c9_golden():
    raise AssertionError("Faz-3 data-bound c9 golden not yet wired (placeholder).")

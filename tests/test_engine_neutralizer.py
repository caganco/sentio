"""Tier-A tests for the factor neutralizer (Section 3.5): the gate to a fair
conjugate test.

The look-ahead-safety claim is not asserted in prose here -- it is the reason the
beta must be recoverable from PAST returns only and the residual must be
market-orthogonal. The four checks: beta recovery after warm-up, pre-warm-up
NaN, thin-history NaN, and residual-vs-market orthogonality.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine.neutralizer import residualize, rolling_beta

_WINDOW = 120
_MP = int(np.ceil(0.8 * _WINDOW))  # 96


def _market_and_returns(
    n_dates: int = 320, seed: int = 0
) -> tuple[pd.Series, pd.DataFrame, dict[str, float]]:
    """r_i = beta_i * r_mkt + idio (idio orthogonal to the market by construction)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n_dates)
    mkt_ret = pd.Series(rng.normal(0.0, 0.01, size=n_dates), index=dates)
    betas = {"LO": 0.5, "MID": 1.0, "HI": 1.5}
    cols = {}
    for name, b in betas.items():
        cols[name] = b * mkt_ret.to_numpy() + rng.normal(0.0, 0.003, size=n_dates)
    returns = pd.DataFrame(cols, index=dates)
    return mkt_ret, returns, betas


class TestBetaRecovery:
    def test_recovers_true_beta_after_warmup(self):
        mkt_ret, returns, betas = _market_and_returns()
        beta = rolling_beta(returns, mkt_ret, window=_WINDOW, min_coverage=0.8)
        post = beta.iloc[_WINDOW:]  # comfortably past the warm-up
        for name, b_true in betas.items():
            assert abs(float(post[name].mean()) - b_true) < 0.08

    def test_pre_warmup_is_nan(self):
        mkt_ret, returns, _ = _market_and_returns()
        beta = rolling_beta(returns, mkt_ret, window=_WINDOW, min_coverage=0.8)
        # need _MP trailing observations (day t excluded via shift) -> rows before
        # the floor cannot carry a beta.
        assert beta.iloc[: _MP - 1].isna().all().all()
        assert beta.iloc[_WINDOW + 5 :].notna().all().all()

    def test_thin_history_name_is_nan(self):
        mkt_ret, returns, _ = _market_and_returns()
        thin = pd.Series(np.nan, index=returns.index)
        thin.iloc[:10] = mkt_ret.iloc[:10].to_numpy()  # only 10 finite obs, never >= _MP
        returns = returns.assign(THIN=thin)
        beta = rolling_beta(returns, mkt_ret, window=_WINDOW, min_coverage=0.8)
        assert beta["THIN"].isna().all()


class TestResidualOrthogonality:
    def test_residual_is_market_orthogonal(self):
        mkt_ret, returns, _ = _market_and_returns()
        beta = rolling_beta(returns, mkt_ret, window=_WINDOW, min_coverage=0.8)
        resid = residualize(returns, mkt_ret, beta)
        post = resid.iloc[_WINDOW:]
        mkt_post = mkt_ret.iloc[_WINDOW:]
        for name in returns.columns:
            joined = pd.concat([post[name], mkt_post], axis=1).dropna()
            assert abs(float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))) < 0.15

    def test_beta_is_arm_independent(self):
        # The beta of a name depends on its OWN past only: estimating it on the
        # full universe vs on an arbitrary subset must give the identical column
        # (no cross-name leakage, so a name-split cannot move a residual).
        mkt_ret, returns, _ = _market_and_returns()
        full = rolling_beta(returns, mkt_ret, window=_WINDOW, min_coverage=0.8)
        subset = rolling_beta(returns[["LO", "HI"]], mkt_ret, window=_WINDOW, min_coverage=0.8)
        pd.testing.assert_series_equal(full["LO"], subset["LO"])
        pd.testing.assert_series_equal(full["HI"], subset["HI"])

"""Factor neutralization (Section 3.5, gap c): the gate to a fair conjugate test.

The Mod-A core asks whether a signal that ranks names in arm X1 also ranks the
*disjoint* names in X2 -- but only after the market component is stripped, so the
agreement reflects idiosyncratic skill rather than a shared beta ride. This
module produces the market-neutral (residual) returns the rank-IC and agreement
are computed on.

Look-ahead safety (the whole point):
- ``rolling_beta`` estimates beta_{i,t} from DAILY returns over tau in [t-W, t-1]
  -- the day ``t`` itself is EXCLUDED. Implemented by ``shift(1)`` BEFORE the
  rolling window, so a window ending at row ``t`` covers returns at [t-W, t-1].
- beta is a function of each name's OWN past only -- it takes no arm argument, so
  the name-split cannot change it (no cross-arm leakage by construction; a unit
  test pins this).
- the residual at ``t`` applies that trailing beta to the contemporaneous (or
  forward) market move; nothing from the future enters the estimate.

Convention: explicit vectorized POPULATION cov/var (the ``/n`` cancels in the
ratio, so the OLS slope is exact regardless of ddof). No alpha term -- the
spec Section 3 formula is ``r_tilde = r - beta_hat * r_mkt`` exactly.

Scope: market-beta neutralization is the Mod-A minimum (mandatory, enforced by
``DialConfig.requires_market_neutralization``). The optional size/value
within-arm orthogonalization (each arm's cross-section demeaned SEPARATELY, so
one arm's characteristics never enter the other's residual) is default-OFF and
carries no fixture, so it is deferred rather than shipped as speculative code.
Sector is likewise default-OFF (long-only -> sector-neutralization destroys
cross-component value, FAJ 2023).
"""
from __future__ import annotations

import math

import pandas as pd

from . import config


def rolling_beta(
    returns: pd.DataFrame,
    market: pd.Series,
    *,
    window: int = config.BETA_WINDOW_DAYS,
    min_coverage: float = config.BETA_MIN_COVERAGE,
) -> pd.DataFrame:
    """Look-ahead-safe trailing-window market beta per name.

    ``beta_hat_{i,t} = Cov_{tau in [t-W, t-1]}(r_i, r_mkt) / Var_{tau in [t-W, t-1]}(r_mkt)``

    Both inputs are DAILY simple returns: ``returns`` is wide (index=date,
    columns=symbol), ``market`` is a Series on the same date index. The ``shift(1)``
    applied to both BEFORE the rolling window is what excludes day ``t`` from its
    own estimate (the window ending at ``t`` then spans [t-W, t-1]).

    A name (or the market) with fewer than ``ceil(min_coverage * window)`` finite
    observations in the window yields NaN -> the residual is NaN there, so
    thin-history names drop out early rather than carrying a noisy beta. Dates
    where the trailing market variance is non-positive also yield NaN.
    """
    mp = max(2, math.ceil(min_coverage * window))

    r = returns.shift(1)
    m = market.shift(1)

    roll_m = m.rolling(window, min_periods=mp)
    m_mean = roll_m.mean()
    m_var = roll_m.var(ddof=0)  # population: matches the cov convention below
    m_var = m_var.where(m_var > 0.0)

    r_mean = r.rolling(window, min_periods=mp).mean()
    rm_mean = r.mul(m, axis=0).rolling(window, min_periods=mp).mean()
    cov = rm_mean.sub(r_mean.mul(m_mean, axis=0))

    return cov.div(m_var, axis=0)


def residualize(
    target: pd.DataFrame,
    factor: pd.Series,
    beta: pd.DataFrame,
) -> pd.DataFrame:
    """Strip the factor component: ``r_tilde_{i,t} = target_{i,t} - beta_{i,t} * factor_t``.

    ``target`` is wide (date x name), ``factor`` is a Series on the same date
    index (the market move to remove), ``beta`` is the wide per-name loading from
    ``rolling_beta``. No intercept -- spec Section 3 formula exactly. Where beta is
    NaN (pre-warm-up or thin history) the residual is NaN.
    """
    return target.sub(beta.mul(factor, axis=0))


def market_neutral_forward(
    fwd_returns: pd.DataFrame,
    fwd_market: pd.Series,
    daily_returns: pd.DataFrame,
    daily_market: pd.Series,
    *,
    window: int = config.BETA_WINDOW_DAYS,
    min_coverage: float = config.BETA_MIN_COVERAGE,
) -> pd.DataFrame:
    """Market-neutralize forward returns with a trailing-daily beta (Section 3.5).

    The beta is estimated from PAST daily returns (knowable as-of ``t``); it is
    then applied to the forward market move to remove the market component of each
    name's forward return:

        ``r_tilde_fwd_{i,t} = fwd_{i,t} - beta_hat_{i,t} * fwd_mkt_t``

    Estimating beta on daily (not forward) returns is deliberate: forward returns
    overlap by ``h`` days and look ahead, so they cannot drive a look-ahead-safe
    loading. ``rank_ic`` / agreement are computed on the residual this returns.
    """
    beta = rolling_beta(
        daily_returns, daily_market, window=window, min_coverage=min_coverage
    )
    return residualize(fwd_returns, fwd_market, beta)

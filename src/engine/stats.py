"""Cross-sectional statistics core (Section 4.1, gap a): rank-IC -> IR -> NW t.

Three primitives the conjugate-agreement core (Faz-2) and the Mod-B leg (modb.py)
both consume:

- ``rank_ic_series`` : per-date cross-sectional Spearman rank-IC (psi, dial 1).
- ``ic_ir``          : realized information ratio = mean_t(IC) / std_t(IC).
- ``nw_tstat``       : Newey-West HAC mean t-stat (population-variance Bartlett).

``nw_tstat`` is a faithful RE-IMPLEMENTATION of the committed precedent
(``d213``/``d211`` ``nw_mean_tstat``) -- NOT an import -- because there is no
shared primitive: the committed copies disagree on variance convention
(population ``e@e/n`` vs sample ``ddof=1``) and on edge guards. The engine gets
ONE authoritative estimator with an explicit ``lag`` and is pinned to the
committed precedent by an equivalence test (tests/test_engine_stats.py).

Variance-convention pin: ``d213``/``d211`` use ``gamma0 = (e@e)/n`` (population),
the SAME convention as the untracked ``c9._nw_t`` that produced the C12 golden
(NW-t = 6.928414). So pinning here to the committed anchors transitively pins the
engine to the golden, which Faz-3 reproduces on real data.
"""
from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import stats

from . import config


def rank_ic_series(
    scores: pd.DataFrame,
    fwd: pd.DataFrame,
    *,
    min_names: int = config.MIN_NAMES_CROSS_SECTION,
) -> pd.Series:
    """Per-date cross-sectional Spearman rank-IC of ``scores`` vs forward returns.

    Both frames are wide (index=date, columns=symbol). For each shared date the IC
    is ``rho(scores_t, fwd_t)`` over names where BOTH are finite; dates with fewer
    than ``min_names`` paired names are dropped (NaN cross-sections excluded).

    Mirrors the committed ``factor_ic_harness.daily_ic_series`` rule, but
    engine-scoped: the floor is ``config.MIN_NAMES_CROSS_SECTION`` (30), not the
    prototype's 5.
    """
    out: dict[pd.Timestamp, float] = {}
    for date in scores.index.intersection(fwd.index):
        a = scores.loc[date]
        b = fwd.loc[date]
        mask = a.notna() & b.notna()
        if int(mask.sum()) < min_names:
            continue
        ic, _ = stats.spearmanr(a[mask].to_numpy(), b[mask].to_numpy())
        if not np.isnan(ic):
            out[date] = float(ic)
    return pd.Series(out, dtype=float).sort_index()


def ic_ir(ic: pd.Series) -> float:
    """Realized information ratio = mean_t(IC) / std_t(IC, ddof=1).

    Not annualized (Section 8 frozen). Scale-invariant by construction. Returns
    NaN if fewer than 2 observations or zero dispersion (IR undefined).
    """
    x = ic.dropna().to_numpy()
    if x.size < 2:
        return float("nan")
    sd = float(np.std(x, ddof=1))
    if sd <= 0.0:
        return float("nan")
    return float(np.mean(x) / sd)


def nw_tstat(x: npt.ArrayLike, *, lag: int) -> float:
    """Newey-West HAC t-stat of the MEAN of ``x`` (H0: mean = 0).

    Population-variance Bartlett kernel; non-finite values are dropped (order
    preserved). Faithful re-implementation of the committed
    ``d213``/``d211.nw_mean_tstat`` -- same ``gamma0 = e@e/n`` convention, same
    Bartlett weights, same ``n < lag + 3`` guard -- returning only the t-value
    (the precedent returns ``(t, mean, n)``). Returns NaN below the guard or when
    the HAC variance is non-positive.
    """
    arr = np.asarray(x, dtype=float)
    a = arr[np.isfinite(arr)]
    n = a.size
    if n < lag + 3:
        return float("nan")
    m = float(a.mean())
    e = a - m
    s = float(e @ e) / n  # gamma0 -- POPULATION variance (matches d213/d211/c9)
    for lag_k in range(1, lag + 1):
        w = 1.0 - lag_k / (lag + 1.0)
        s += 2.0 * w * float(e[lag_k:] @ e[:-lag_k]) / n
    if s <= 0.0:
        return float("nan")
    return float(m / np.sqrt(s / n))

"""Real CSCV median-rank PBO (Section 4.1/5, Catal-1): the overfit probe the
Mod-A conjugate core uses INSTEAD of the simplified Mod-B proxy.

What the proxy cannot do. The committed
``statistical_validation.compute_pbo(oos_sharpe_list)`` is literally
``sum(s < 0) / len(...)`` = ``P(OOS Sharpe < 0)``. It has no in-sample
selection, no rank, no logit -- a strategy can post a positive OOS Sharpe and
still be the IS-luckiest of many, which the proxy never detects. The Mod-A core
must NOT call it (Faz-1's ``modb`` uses it only on the convenience leg, labeled
``pbo_is_simplified_proxy``).

The real CSCV (Bailey & Lopez de Prado), mapped to the conjugate context:
- the "configs" being selected among are cross-sectional sort-buckets (deciles,
  ``config.PBO_N_BUCKETS``), ranked within an arm -- NOT the splits. (If configs
  were the splits, a *real* factor makes every split good, the ranking among
  them is noise, and PBO -> 0.5, which would falsely fail the embedded-factor
  fixture. Buckets-as-configs avoids that: for a real factor the ranking among
  buckets is informative.)
- the combinatorial resampling is the R name-splits (the cross-sectional analog
  of CPCV paths).
- IS = arm X1, OOS = arm X2 (and the symmetric direction; the caller averages).

This module is deliberately generic: it takes the two performance matrices
``M_IS`` / ``M_OOS`` (R splits x B buckets) and returns one PBO. The
name -> bucket mapping and the per-bucket neutralized active returns are built by
``moda`` and handed in here; degenerate buckets arrive as NaN and are excluded.
"""
from __future__ import annotations

import numpy as np
import numpy.typing as npt

# minimum joint-valid buckets in a split's row for its IS-best bucket to carry a
# meaningful OOS rank (a single bucket cannot be ranked against anything).
_MIN_VALID_BUCKETS = 2


def _logit_relative_rank(is_row: npt.NDArray[np.float64], oos_row: npt.NDArray[np.float64]) -> float:
    """Logit of the IS-best bucket's relative rank in the OOS arm, for one split.

    Considers only buckets finite in BOTH arms (a bucket must be scorable IS and
    OOS to enter the comparison). The IS-best bucket ``b*`` is ``argmax`` over the
    IS values; its OOS relative rank uses the Bailey-Lopez de Prado average-rank
    convention ``omega = rank(b*) / (n_valid + 1)`` in (0, 1), so the logit is
    always finite. Returns NaN if fewer than ``_MIN_VALID_BUCKETS`` are jointly
    valid (the row is then dropped from the PBO fraction).
    """
    mask = np.isfinite(is_row) & np.isfinite(oos_row)
    n_valid = int(mask.sum())
    if n_valid < _MIN_VALID_BUCKETS:
        return float("nan")

    is_vals = is_row[mask]
    oos_vals = oos_row[mask]
    b_star = int(np.argmax(is_vals))  # ties -> first; deterministic
    oos_at_star = oos_vals[b_star]

    # average rank (1-based) of the IS-best bucket's OOS value, ties shared:
    #   rank = #(strictly less) + (#equal + 1) / 2
    count_less = float(np.sum(oos_vals < oos_at_star))
    count_equal = float(np.sum(oos_vals == oos_at_star))
    avg_rank = count_less + (count_equal + 1.0) / 2.0
    omega = avg_rank / (n_valid + 1.0)
    return float(np.log(omega / (1.0 - omega)))


def cscv_pbo(
    m_is: npt.ArrayLike,
    m_oos: npt.ArrayLike,
    *,
    min_valid_buckets: int = _MIN_VALID_BUCKETS,
) -> float:
    """Probability of backtest overfitting for one IS->OOS direction.

    ``m_is`` / ``m_oos`` are (R, B) matrices: row = name-split, column = bucket,
    entry = that bucket's neutralized active return (time-mean) in the IS / OOS
    arm. Degenerate buckets (below the per-bucket name floor) must arrive as NaN;
    they are excluded from the per-split argmax and rank.

    For each split the IS-best bucket's OOS relative rank gives a logit
    ``lambda``; ``PBO = fraction of splits with lambda < 0`` -- i.e. the rate at
    which the in-sample winner lands BELOW the out-of-sample median. Pure noise
    -> ~0.5; a bucket order that transfers IS->OOS -> ~0; an inverted order
    -> ~1. Returns NaN if no split yields a rankable row.
    """
    is_mat = np.asarray(m_is, dtype=float)
    oos_mat = np.asarray(m_oos, dtype=float)
    if is_mat.shape != oos_mat.shape:
        raise ValueError(f"M_IS {is_mat.shape} and M_OOS {oos_mat.shape} must match")
    if is_mat.ndim != 2:
        raise ValueError(f"expected (R, B) matrices, got ndim={is_mat.ndim}")

    lambdas: list[float] = []
    for is_row, oos_row in zip(is_mat, oos_mat, strict=True):
        mask = np.isfinite(is_row) & np.isfinite(oos_row)
        if int(mask.sum()) < min_valid_buckets:
            continue
        lam = _logit_relative_rank(is_row, oos_row)
        if np.isfinite(lam):
            lambdas.append(lam)

    if not lambdas:
        return float("nan")
    arr = np.asarray(lambdas, dtype=float)
    return float(np.mean(arr < 0.0))

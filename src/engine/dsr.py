"""DSR trial-count deflation benchmark (Section 4.2, FAZ-4 (b)).

Multiple-test / search-overfit is caught by the Deflated Sharpe Ratio's
N-deflation -- NOT by bucket-PBO (which measures single-prototype-internal
overfit; a different layer). The committed ``compute_dsr`` already accepts a
``benchmark_sr`` but the Mod-B leg has been feeding the conservative 0.0 (no
deflation). This module computes the Bailey-Lopez de Prado deflation benchmark
from the honest tried-config count N and feeds it to the EXISTING ``compute_dsr``
-- strangler: the committed estimator is REUSED, never rewritten (math-spec
Section 5 "yeniden-kullan, yeniden-yazma").

Identity: ``compute_dsr`` returns ``Phi((SR_obs - benchmark_sr) / se_SR)`` with
``se_SR = sqrt(denom_sq / (T-1))``. Setting ``benchmark_sr = se_SR * E[max_N]``
makes that EXACTLY the canonical deflated DSR ``Phi(SR_obs/se_SR - E[max_N])``.

The ``E[max]`` order-statistic closed form is the SAME one committed in
``statistical_validation.min_btl_days`` (Euler-Mascheroni); reimplemented here
engine-side (additive, the committed copy is untouched).
"""
from __future__ import annotations

import math

from scipy.stats import norm

from . import config


def expected_max_sharpe(n_trials: int) -> float:
    """E[max of N i.i.d. standard-normal Sharpe estimates] -- Bailey-LdP order stat.

    ``(1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N*e))``, g = Euler-Mascheroni.

    Returns 0.0 for ``N <= 1``: a single trial carries no multiple-test inflation,
    and ``Phi^-1(1 - 1/1) = Phi^-1(0) = -inf`` is undefined. ``N=1 -> 0.0`` is the
    no-deflation case that keeps the DSR byte-identical to the pre-FAZ-4 call.
    """
    if n_trials <= 1:
        return 0.0
    g = config.EULER_MASCHERONI
    z1 = float(norm.ppf(1.0 - 1.0 / n_trials))
    z2 = float(norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
    return (1.0 - g) * z1 + g * z2


def deflation_benchmark_sr(
    sr_obs: float, T: int, skewness: float, kurtosis: float, n_trials: int
) -> float:
    """Bailey-LdP deflation benchmark to feed ``compute_dsr``'s ``benchmark_sr``.

    ``se_SR = sqrt(denom_sq / (T-1))`` where ``denom_sq = 1 - skew*SR_obs +
    (kurt-1)/4 * SR_obs**2`` (the SAME denominator ``compute_dsr`` uses);
    returns ``se_SR * E[max_N]``.

    Returns 0.0 where there is nothing to deflate or the inputs are degenerate
    (``N <= 1``, ``T <= 1``, or ``denom_sq <= 0``) -- in those cases ``compute_dsr``
    itself collapses to its undeflated/zero value, so a 0.0 benchmark keeps the
    engine-computed benchmark and the committed estimator consistent.
    """
    e_max = expected_max_sharpe(n_trials)
    if e_max <= 0.0 or T <= 1:
        return 0.0
    denom_sq = 1.0 - skewness * sr_obs + ((kurtosis - 1.0) / 4.0) * sr_obs**2
    if denom_sq <= 0.0:
        return 0.0
    se_sr = math.sqrt(denom_sq / (T - 1))
    return se_sr * e_max

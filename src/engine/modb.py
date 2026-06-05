"""Mod-B temporal-CPCV leg (Section 3.2/3.4): the convenience time-axis check.

Wraps the committed ``CombinatorialPurgedCV`` (purge + embargo) driven by the
engine's own config (N=10, k=2 daily; ``CPCV_DAILY_N/K``) rather than the
committed default 6,2. For a zero-discretion cross-sectional scorer the per-date
rank-IC does not depend on the train/test fold, so this leg uses CPCV for the
OOS *Sharpe distribution* (-> PBO / DSR) and computes the pooled OOS rank-IC
t-stat once over the full IC series.

Catal-1 boundary: this leg reuses the SIMPLIFIED ``compute_pbo`` proxy
(P(OOS Sharpe < 0)). That is NOT the real CSCV median-rank PBO -- the real
Lopez de Prado PBO for the Mod-A conjugate core is Faz-2. The proxy is labeled
in the output dict (``pbo_is_simplified_proxy``) so a reader can never mistake it.

PM-1 (Section 10): the only weights this leg builds are a fully-invested
long-only top tilt (EW over the selected names, summing to 1). Each vector is
checked with ``assert_pm1_compliant`` -- a cash-gate would RAISE.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.backtest.cross_validation import CombinatorialPurgedCV
from src.backtest.statistical_validation import compute_dsr, compute_pbo, sharpe_newey_west

from . import config
from .contracts import DialConfig, Panel, SortDepth, SplitSpec
from .data_adapter import forward_return
from .dsr import deflation_benchmark_sr
from .signal_protocol import Signal, assert_pm1_compliant
from .stats import nw_tstat, rank_ic_series

_DEPTH_FRACTION: dict[SortDepth, float] = {
    SortDepth.TERCILE: 1.0 / 3.0,
    SortDepth.DECILE: 0.10,
}


def _scores_panel(
    panel: Panel, signal: Signal, dates: pd.DatetimeIndex, names: list[str]
) -> pd.DataFrame:
    """Materialize the zero-discretion scorer into a wide (date x name) frame."""
    rows = {asof: signal.scores(panel, names, asof) for asof in dates}
    return pd.DataFrame.from_dict(rows, orient="index")


def _select_top(scores: pd.Series, depth: SortDepth) -> pd.Series:
    """Top fraction of names by score (tercile default; decile supported).

    ``TOPN`` has no N at the leg level, so it falls back to tercile -- richer
    sort-depths belong to the Mod-A conjugate core (Faz-2).
    """
    frac = _DEPTH_FRACTION.get(depth, 1.0 / 3.0)
    k = max(1, int(len(scores) * frac))
    return scores.nlargest(k)


def _active_return_series(
    scores_panel: pd.DataFrame,
    fwd: pd.DataFrame,
    depth: SortDepth,
    *,
    name: str,
    min_names: int = config.MIN_NAMES_CROSS_SECTION,
) -> pd.Series:
    """Per-date active forward return = (top-tilt EW) - (eligible-basket EW).

    The tilt is a fully-invested long-only re-tilt (PM-1 compliant); the basket
    subtraction is a performance benchmark, not a short leg. Dates with fewer
    than ``min_names`` finite pairs are skipped.
    """
    out: dict[pd.Timestamp, float] = {}
    for date in scores_panel.index.intersection(fwd.index):
        sc = scores_panel.loc[date]
        fr = fwd.loc[date]
        mask = sc.notna() & fr.notna()
        if int(mask.sum()) < min_names:
            continue
        sc_e = sc[mask]
        fr_e = fr[mask]
        top = _select_top(sc_e, depth)
        weights = pd.Series(1.0 / len(top), index=top.index)
        assert_pm1_compliant(weights, name=name)
        port = float((fr_e.reindex(top.index) * weights).sum())
        bench = float(fr_e.mean())
        out[date] = port - bench
    return pd.Series(out, dtype=float).sort_index()


def run_modb(
    panel: Panel, signal: Signal, spec: SplitSpec, dial: DialConfig, *, n_trials: int = 1
) -> dict[str, object]:
    """Run the Mod-B temporal-CPCV leg and return a result dict.

    Keys: ``n_paths``, ``pooled_oos_ic_t`` / ``pooled_oos_ic_mean`` / ``n_ic_obs``,
    ``oos_sharpe`` (per-path distribution) / ``oos_sharpe_median``, ``pbo``
    (+ ``pbo_is_simplified_proxy``), ``dsr`` (+ ``dsr_n_trials`` /
    ``dsr_deflation_benchmark_sr``), and split provenance.

    ``n_trials`` is the honest tried-config count (Stage-0 ``denenen_konfig_sayisi``);
    it deflates the DSR via the Bailey-LdP E[max] benchmark (FAZ-4 (b)). The default
    1 -> no deflation -> the DSR is byte-identical to the pre-FAZ-4 call.
    """
    dates = panel.dates
    names = panel.names
    h = int(signal.construction_window)
    lag = dial.nw_lag_for(panel.frequency)

    fwd = forward_return(panel, h, basis=str(dial.return_basis))
    scores_panel = _scores_panel(panel, signal, dates, names)
    ic = rank_ic_series(scores_panel, fwd)
    active = _active_return_series(scores_panel, fwd, spec.sort_depth, name=signal.name)

    cv = CombinatorialPurgedCV(N=spec.cpcv_n, k=spec.cpcv_k)
    paths = cv.split(dates, embargo_days=spec.embargo_h)
    oos_sharpe: list[float] = []
    oos_lengths: list[int] = []
    for _train_idx, test_idx in paths:
        seg = active.reindex(dates[test_idx]).dropna()
        oos_lengths.append(int(seg.size))
        oos_sharpe.append(float(sharpe_newey_west(seg.to_numpy())) if seg.size else 0.0)

    pbo = compute_pbo(oos_sharpe)
    t_oos = int(np.mean(oos_lengths)) if oos_lengths else 0
    a = active.dropna()
    skew = float(a.skew()) if a.size > 2 else 0.0
    kurt = float(a.kurt()) + 3.0 if a.size > 3 else 3.0
    if not math.isfinite(skew):
        skew = 0.0
    if not math.isfinite(kurt):
        kurt = 3.0
    sr_obs = float(np.mean(oos_sharpe)) if oos_sharpe else 0.0
    benchmark_sr = deflation_benchmark_sr(sr_obs, t_oos, skew, kurt, n_trials)
    dsr = compute_dsr(
        oos_sharpe, T=t_oos, skewness=skew, kurtosis=kurt, benchmark_sr=benchmark_sr
    )

    return {
        "n_paths": cv.n_paths,
        "pooled_oos_ic_t": nw_tstat(ic.to_numpy(), lag=lag),
        "pooled_oos_ic_mean": float(ic.mean()) if ic.size else float("nan"),
        "n_ic_obs": int(ic.size),
        "oos_sharpe": oos_sharpe,
        "oos_sharpe_median": float(np.median(oos_sharpe)) if oos_sharpe else float("nan"),
        "pbo": pbo,
        "pbo_is_simplified_proxy": True,
        "dsr": dsr,
        "dsr_n_trials": int(n_trials),
        "dsr_deflation_benchmark_sr": float(benchmark_sr),
        "embargo_h": int(spec.embargo_h),
        "cpcv_n": int(spec.cpcv_n),
        "cpcv_k": int(spec.cpcv_k),
        "nw_lag": int(lag),
    }

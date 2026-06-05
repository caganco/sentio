"""Mod-C intra-regime forward time-holdout leg (Section 3 / RR-Y1-005 sec 3/4.8; RR-Y1-010).

Where Mod-A splits *names* and Mod-B splits *time* into CPCV folds, Mod-C answers
the core research question directly: freeze a cross-sectional factor on a TRAINING
time-window and measure its forward cross-sectional rank-IC on a LATER held-out
window WITHIN THE SAME regime, with an embargo (= the forward-return horizon)
purged between them so no construction-period return leaks across the boundary (the
look-ahead-safe discipline Mod-B uses).

For a zero-discretion scorer the factor carries no fitted parameters, so "freeze on
train" is the discovery-window the researcher would have iterated on; the held-out
window is the forward OOS read. Persistence PASS reuses the existing conjugate bar
(no new tunable): the holdout IC Newey-West t clears ``AGREEMENT_CROSS_IC_T_MIN``
AND its sign matches the train-window IC sign. Honesty about power is carried by the
SEPARATE holdout confidence qualifier (``assess_holdout_confidence``), never by
softening the bar.

Strangler: imports only engine-internal helpers (the Mod-A residual machinery and
the shared stats/data_adapter/neutralizer primitives) -- no lab/committed-motor import.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .contracts import DialConfig, Panel, SortDepth, SplitSpec
from .data_adapter import forward_return
from .holdout_confidence import assess_holdout_confidence
from .moda import (
    _arm_active_series,
    _eligible_names,
    _random_halves,
    _safe_mean,
    arm_active_correlation,
    name_splits,
    residual_arm_correlation,
)
from .neutralizer import market_neutral_forward
from .signal_protocol import Signal
from .stats import nw_tstat, rank_ic_series

_DEPTH_FRACTION: dict[SortDepth, float] = {
    SortDepth.TERCILE: 1.0 / 3.0,
    SortDepth.DECILE: 0.10,
}


def _residual_flag_on_window(
    panel: Panel,
    scores_w: pd.DataFrame,
    resid_w: pd.DataFrame,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    *,
    spec: SplitSpec,
    dial: DialConfig,
    frac: float,
    min_names: int,
) -> bool:
    """Shared common-factor detector on a single window, reusing the Mod-A machinery.

    Splits the window's eligible universe into liquidity-balanced arms and flags the
    two arms' active-return co-movement against a permutation null (the SAME detector
    RR-Y1-008 used to catch the hi52 confound). Returns False when the window is too
    thin to form two arms -- cannot reject, so do not flag.
    """
    eligible = _eligible_names(
        panel, panel.names, split_asof=d0, d0=d0, d1=d1,
        floor_tl=spec.split_arm_floor_tl, trailing=config.LIQUID_TRAILING_DAYS,
    )
    if len(eligible) < 2 * spec.min_names_per_arm:
        return False
    splits = name_splits(panel, eligible, spec=spec, split_asof=d0)
    obs_corrs = [
        arm_active_correlation(
            _arm_active_series(scores_w, resid_w, x1, frac, name="modc", min_names=min_names),
            _arm_active_series(scores_w, resid_w, x2, frac, name="modc", min_names=min_names),
        )
        for x1, x2 in splits
    ]
    observed = _safe_mean(obs_corrs)
    null_children = np.random.SeedSequence(spec.seed + 2_000_000).spawn(config.RESIDUAL_NULL_RESAMPLES)
    null_corrs: list[float] = []
    for child in null_children:
        nx1, nx2 = _random_halves(eligible, np.random.default_rng(child))
        a1 = _arm_active_series(scores_w, resid_w, nx1, frac, name="modc", min_names=min_names)
        a2 = _arm_active_series(scores_w, resid_w, nx2, frac, name="modc", min_names=min_names)
        null_corrs.append(arm_active_correlation(a1, a2))
    _, flag = residual_arm_correlation(observed, null_corrs, pctile=dial.residual_corr_null_pctile)
    return bool(flag)


def run_modc(
    panel: Panel, signal: Signal, spec: SplitSpec, dial: DialConfig
) -> dict[str, object]:
    """Run the Mod-C intra-regime time-holdout leg and return a result dict.

    Keys: ``holdout_persistence_pass``, ``holdout_ic_t`` / ``holdout_ic_mean``,
    ``train_ic_t`` / ``train_ic_mean``, ``holdout_sign_consistent``,
    ``n_holdout_obs`` / ``n_train_obs``, ``holdout_confidence`` /
    ``holdout_confidence_reasons``, and ``guard_messages``.

    A degenerate split (boundary outside the eval window, or train/holdout too short
    to field a NW t-stat) returns ``holdout_persistence_pass=None`` with a guard
    message rather than a misleading number.
    """
    guards: list[str] = []
    dates = panel.dates
    h = int(signal.construction_window)
    lag = dial.nw_lag_for(panel.frequency)
    frac = _DEPTH_FRACTION.get(spec.sort_depth, 1.0 / 3.0)
    mn = config.MIN_NAMES_CROSS_SECTION

    tr = panel.tr_gross if str(dial.return_basis) == "tr_index_gross" else panel.tr_net
    daily_ret = tr.pct_change()
    mkt = panel.market.reindex(dates)
    daily_mkt = mkt.pct_change()
    fwd = forward_return(panel, h, basis=str(dial.return_basis))
    fwd_mkt = mkt.shift(-h) / mkt - 1.0
    resid_fwd = market_neutral_forward(
        fwd, fwd_mkt, daily_ret, daily_mkt, window=dial.beta_window, min_coverage=config.BETA_MIN_COVERAGE
    )

    scores = pd.DataFrame.from_dict(
        {asof: signal.scores(panel, panel.names, asof) for asof in dates}, orient="index"
    )

    eval_mask = resid_fwd.notna().sum(axis=1) >= mn
    eval_dates = resid_fwd.index[eval_mask]
    if eval_dates.empty:
        guards.append("no evaluation date clears the cross-section floor after beta warm-up")
        return _guard_result(guards)

    boundary = pd.Timestamp(spec.holdout_start)
    holdout_dates = eval_dates[eval_dates >= boundary]
    pre = eval_dates[eval_dates < boundary]
    # Purge an embargo band (= forward-return horizon, in eval-day units) from the tail of
    # the pre-boundary segment so no train forward-return reaches across the boundary.
    embargo_gap = int(spec.embargo_h)
    n_train_avail = max(0, len(pre) - embargo_gap)
    train_dates = pre[:n_train_avail]

    train_ic = rank_ic_series(scores.loc[train_dates], resid_fwd.loc[train_dates])
    holdout_ic = rank_ic_series(scores.loc[holdout_dates], resid_fwd.loc[holdout_dates])
    floor = lag + 3
    if train_ic.size < floor or holdout_ic.size < floor:
        guards.append(
            f"insufficient train/holdout IC observations (train={train_ic.size}, "
            f"holdout={holdout_ic.size}; need >= {floor} each for a NW t-stat -- "
            "boundary too close to an edge or embargo purges the whole train segment)"
        )
        return _guard_result(guards)

    train_ic_t = nw_tstat(train_ic.to_numpy(), lag=lag)
    holdout_ic_t = nw_tstat(holdout_ic.to_numpy(), lag=lag)
    train_ic_mean = float(train_ic.mean())
    holdout_ic_mean = float(holdout_ic.mean())
    s_train = float(np.sign(train_ic_mean))
    s_holdout = float(np.sign(holdout_ic_mean))
    sign_consistent = bool(s_holdout != 0.0 and s_holdout == s_train)
    persistence_pass = bool(
        np.isfinite(holdout_ic_t) and holdout_ic_t > dial.agreement_t_min and sign_consistent
    )

    regime_split = pd.Timestamp(config.REGIME_SPLIT)
    hd0, hd1 = holdout_dates[0], holdout_dates[-1]
    holdout_crosses_regime = bool(hd0 < regime_split <= hd1)
    resid_flag = _residual_flag_on_window(
        panel, scores.loc[holdout_dates], resid_fwd.loc[holdout_dates], hd0, hd1,
        spec=spec, dial=dial, frac=frac, min_names=mn,
    )
    confidence, confidence_reasons = assess_holdout_confidence(
        n_holdout_obs=int(holdout_ic.size),
        holdout_crosses_regime=holdout_crosses_regime,
        residual_corr_flag=resid_flag,
        obs_floor=config.HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE,
    )
    return {
        "holdout_persistence_pass": persistence_pass,
        "holdout_ic_t": holdout_ic_t,
        "holdout_ic_mean": holdout_ic_mean,
        "train_ic_t": train_ic_t,
        "train_ic_mean": train_ic_mean,
        "holdout_sign_consistent": sign_consistent,
        "n_holdout_obs": int(holdout_ic.size),
        "n_train_obs": int(train_ic.size),
        "holdout_confidence": confidence,
        "holdout_confidence_reasons": confidence_reasons,
        "guard_messages": tuple(guards),
    }


def _guard_result(guards: list[str]) -> dict[str, object]:
    """Uniform degenerate result: no verdict (None), NaN reads, the guard reasons.

    Fed zero holdout observations, ``assess_holdout_confidence`` naturally grades it
    ``low`` (0 < floor) -- no special-casing.
    """
    confidence, confidence_reasons = assess_holdout_confidence(
        n_holdout_obs=0,
        holdout_crosses_regime=False,
        residual_corr_flag=False,
        obs_floor=config.HOLDOUT_MIN_IC_OBS_FOR_HIGH_CONFIDENCE,
    )
    return {
        "holdout_persistence_pass": None,
        "holdout_ic_t": float("nan"),
        "holdout_ic_mean": float("nan"),
        "train_ic_t": float("nan"),
        "train_ic_mean": float("nan"),
        "holdout_sign_consistent": None,
        "n_holdout_obs": 0,
        "n_train_obs": 0,
        "holdout_confidence": confidence,
        "holdout_confidence_reasons": confidence_reasons,
        "guard_messages": tuple(guards),
    }

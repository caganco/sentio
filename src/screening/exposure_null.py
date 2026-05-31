"""D-187 -- random-switch null for S-B (active-timing) significance test.

Random null: same number of switches as S-B in the slice window, on random dates,
same switch cost, same equity/TLREF returns. Distribution of real annual returns ->
null p95 and pctile of S-B against this null.
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening.exposure_backtest import _rebase, compute_metrics
from src.screening.exposure_config import (
    DECISION_RANDOM_PCTILE_MIN,
    RANDOM_SWITCH_NRESAMPLES,
    RANDOM_SWITCH_SEED,
    SWITCH_COST_BPS,
)


def random_switch_null(
    xu100: pd.Series,
    tlref: pd.Series,
    tufe: pd.Series,
    n_switches: int,
    slice_lo: str,
    slice_hi: str,
    strategy_annual_real: float,
    seed: int = RANDOM_SWITCH_SEED,
    n_resamples: int = RANDOM_SWITCH_NRESAMPLES,
    cost_bps: float = SWITCH_COST_BPS,
) -> dict:
    """Null distribution of annual real return for random switches in the slice.

    Aligns to slice window; n_switches random switch-dates drawn per resample;
    same cost structure as S-B. Returns null distribution statistics.
    """
    cost_frac = cost_bps / 10_000.0
    # align to slice
    idx_mask = (xu100.index >= slice_lo) & (xu100.index <= slice_hi)
    xu = _rebase(xu100[idx_mask].dropna())
    tl = _rebase(tlref.reindex(xu.index).ffill().dropna())
    tu = tufe.reindex(xu.index).ffill().dropna()
    # need common index
    common = xu.index.intersection(tl.index).intersection(tu.index)
    xu, tl, tu = xu.reindex(common), tl.reindex(common), tu.reindex(common)
    n = len(common)
    if n < 4 or n_switches <= 0 or not np.isfinite(strategy_annual_real):
        return {"n_switches": n_switches, "pool_size": n, "null_mean": float("nan"),
                "null_p95": float("nan"), "strategy_annual_real": strategy_annual_real,
                "random_pctile": float("nan"), "beats_random_95": False}
    xu_a = xu.to_numpy(float)
    tl_a = tl.to_numpy(float)
    rng = np.random.default_rng(seed)
    null_ann_reals = np.empty(n_resamples, dtype=float)

    for r in range(n_resamples):
        # random switch dates (sorted)
        sw_idx = np.sort(rng.choice(np.arange(1, n), size=min(n_switches, n - 1), replace=False))
        # build portfolio
        portfolio = np.empty(n, dtype=float)
        portfolio[0] = 1.0
        val = 1.0
        # initial position: random
        pos = int(rng.integers(0, 2))
        prev = {"xu": xu_a[0], "tl": tl_a[0]}
        sw_set = set(sw_idx)
        for i in range(1, n):
            if pos == 1:
                val *= xu_a[i] / prev["xu"]
            else:
                val *= tl_a[i] / prev["tl"]
            if i in sw_set:
                val -= val * cost_frac
                pos = 1 - pos
            prev = {"xu": xu_a[i], "tl": tl_a[i]}
            portfolio[i] = val
        port_s = pd.Series(portfolio, index=common)
        m = compute_metrics(port_s, tu, slice_lo, slice_hi)
        null_ann_reals[r] = m["annual_real"]

    valid = null_ann_reals[np.isfinite(null_ann_reals)]
    if len(valid) < 10:
        return {"n_switches": n_switches, "pool_size": n, "null_mean": float("nan"),
                "null_p95": float("nan"), "strategy_annual_real": strategy_annual_real,
                "random_pctile": float("nan"), "beats_random_95": False}
    pctile = float(np.mean(valid < strategy_annual_real))
    return {
        "n_switches": int(n_switches), "pool_size": int(n),
        "null_mean": round(float(np.mean(valid)), 4),
        "null_p95": round(float(np.percentile(valid, 95)), 4),
        "null_std": round(float(np.std(valid)), 4),
        "strategy_annual_real": round(float(strategy_annual_real), 4),
        "random_pctile": round(pctile, 4),
        "beats_random_95": bool(pctile >= DECISION_RANDOM_PCTILE_MIN),
    }

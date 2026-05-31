"""D-188 -- the TWO nulls (the report's methodological correction).

NULL-1 (event-conditional): on the SAME catalyst-event days, technical confirmation
  is assigned at RANDOM (a random size-n_confluence subset of all event days) ->
  isolates "does technical confirmation add value to the event itself?"
NULL-2 (no-event): the SAME technical confirmation on RANDOM NON-event days ->
  isolates "does the event add value to the technical signal?"
Confluence is REAL only if the observed confluence mean beats BOTH nulls at >= 0.95.

Pure, seeded, deterministic functions over return arrays (adapted from
trend_d186.fair_random_null mechanics). No network, no composite/engine imports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening.event_config import NULL_N_RESAMPLES, NULL_SEED, TOTAL_COST_BPS
from src.screening.event_confirm import technical_confirm
from src.screening.event_study import forward_window, relative_net


def _percentile_null(pool: np.ndarray, n_draw: int, observed: float,
                     seed: int, n_resamples: int, replace: bool) -> dict:
    """Resample mean-of-n_draw from `pool`; locate `observed` in that null distribution."""
    pool = np.asarray(pool, dtype=float)
    pool = pool[np.isfinite(pool)]
    nan = float("nan")
    base = {"pool_size": int(pool.size), "n_draw": int(n_draw),
            "null_mean": nan, "null_p95": nan, "observed": observed,
            "random_pctile": nan, "beats_95": False, "p_value": nan, "degenerate": True}
    if pool.size == 0 or n_draw <= 0 or not np.isfinite(observed):
        return base
    if not replace and n_draw >= pool.size:
        # drawing the whole pool every time -> no contrast (all events are confluence)
        return base
    rng = np.random.default_rng(seed)
    draw_n = n_draw if replace else min(n_draw, pool.size)
    means = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        means[i] = float(rng.choice(pool, size=draw_n, replace=replace).mean())
    pctile = float(np.mean(means < observed))
    p_value = float((np.sum(means >= observed) + 1) / (n_resamples + 1))
    return {"pool_size": int(pool.size), "n_draw": int(draw_n),
            "null_mean": round(float(means.mean()), 6),
            "null_p95": round(float(np.percentile(means, 95)), 6),
            "observed": round(float(observed), 6),
            "random_pctile": round(pctile, 4),
            "beats_95": bool(pctile >= 0.95),
            "p_value": round(p_value, 5), "degenerate": False}


def event_conditional_null(
    event_pool_returns: np.ndarray, n_confluence: int, observed_confluence_mean: float,
    seed: int = NULL_SEED, n_resamples: int = NULL_N_RESAMPLES,
) -> dict:
    """NULL-1: random size-n_confluence subset of ALL event-day returns (no replacement)."""
    return _percentile_null(event_pool_returns, n_confluence, observed_confluence_mean,
                            seed, n_resamples, replace=False)


def no_event_null(
    noevent_returns: np.ndarray, n_target: int, observed_confluence_mean: float,
    seed: int = NULL_SEED, n_resamples: int = NULL_N_RESAMPLES,
) -> dict:
    """NULL-2: resample n_target from no-event technical-confirmed returns (bootstrap)."""
    return _percentile_null(noevent_returns, n_target, observed_confluence_mean,
                            seed, n_resamples, replace=True)


def sample_noevent_technical_returns(
    prices: dict[str, pd.DataFrame],
    xu100: pd.Series,
    event_keys: set[tuple[str, str]],
    horizon: int,
    cost_bps: float = TOTAL_COST_BPS,
    max_pool: int = 20000,
) -> np.ndarray:
    """XU100-relative returns of technical-confirmed bars on NON-event days.

    Scans every ticker/bar; keeps bars where technical_confirm is True and the
    (ticker, date) is NOT a catalyst event. Bounded by max_pool (FIFO cap; if the
    universe overflows it, the cap is reported by the caller). Used to build NULL-2.
    """
    out: list[float] = []
    for ticker, ohlcv in prices.items():
        if ohlcv is None or len(ohlcv) == 0:
            continue
        idx = ohlcv.index
        for pos in range(len(ohlcv)):
            date = str(pd.Timestamp(idx[pos]).date())
            if (ticker, date) in event_keys:
                continue
            if not technical_confirm(ohlcv, date):
                continue
            fw = forward_window(ohlcv, date, horizon)
            if fw is None:
                continue
            entry_date, exit_date, gross = fw
            rel = relative_net(gross, xu100, entry_date, exit_date, cost_bps)
            if rel is not None:
                out.append(float(rel))
                if len(out) >= max_pool:
                    return np.array(out, dtype=float)
    return np.array(out, dtype=float)

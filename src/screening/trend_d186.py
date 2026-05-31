"""D-186 FIX 2 + FIX 3 -- drift-free returns, fair null, cross-sectional significance.

FIX 2: XU100-relative (decisive) and real-CPI (confirmatory) per-trade returns,
strip the nominal TL inflation drift that dominated D-185.
FIX 3: FAIR random null -- random entries get the SAME exit machinery (initial
ATR-stop + Donchian-20 trailing + MAX_HOLD) AND the SAME active pre-filter as the
cell (ADV always; parabolic-eligibility when parabolic_on) -> isolates ENTRY timing.
Cross-sectional significance via daily-aggregated block-bootstrap (reuse).

Reuses D-185 frozen core (trend_signals, trend_backtest, indicators) unchanged.
No composite / conviction / signal-engine imports.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from src.screening import indicators as ind
from src.screening import trend_d186_config as cfg
from src.screening import trend_signals as tsig
from src.screening.factor_ic_harness import block_bootstrap_ci
from src.screening.trend_config import ATR_WINDOW, MAX_HOLD_DAYS  # noqa: F401 (doc)


# ---------------------------------------------------------------------------
# FIX 2 -- drift-free per-trade returns
# ---------------------------------------------------------------------------
def _ret_over(series: pd.Series, entry_date: str, exit_date: str) -> float:
    """Geometric return of `series` between entry and exit (point-in-time asof)."""
    if series is None or len(series) == 0:
        return float("nan")
    e = series.asof(pd.Timestamp(entry_date))
    x = series.asof(pd.Timestamp(exit_date))
    if not (np.isfinite(e) and np.isfinite(x)) or e <= 0:
        return float("nan")
    return float(x / e - 1.0)


def add_relative_returns(trades: list[dict], xu100: pd.Series, cost_bps: float) -> list[dict]:
    """XU100-relative net return (geometric excess over index, post-cost)."""
    cost = cost_bps / 10_000.0
    for t in trades:
        xu = _ret_over(xu100, t["entry_date"], t["exit_date"])
        if np.isfinite(xu):
            t["xu100_return"] = round(xu, 5)
            t["rel_net_return"] = round((1.0 + t["gross_return"]) / (1.0 + xu) - 1.0 - cost, 5)
        else:
            t["xu100_return"] = None
            t["rel_net_return"] = None
    return trades


def add_real_returns(trades: list[dict], cpi: pd.Series | None) -> list[dict]:
    """Real (CPI-deflated) net return. cpi=None (no EVDS key) -> left null."""
    for t in trades:
        if cpi is None:
            t["real_net_return"] = None
            continue
        ce = cpi.asof(pd.Timestamp(t["entry_date"]))
        cx = cpi.asof(pd.Timestamp(t["exit_date"]))
        if np.isfinite(ce) and np.isfinite(cx) and ce > 0:
            t["real_net_return"] = round((1.0 + t["net_return"]) / (cx / ce) - 1.0, 5)
        else:
            t["real_net_return"] = None
    return trades


def slice_trades(trades: list[dict], lo: str, hi: str) -> list[dict]:
    """Trades whose ENTRY date falls in [lo, hi] (inflation slice)."""
    return [t for t in trades if lo <= t["entry_date"] <= hi]


def mean_key(trades: list[dict], key: str) -> float:
    vals = [t[key] for t in trades if t.get(key) is not None]
    return float(np.mean(vals)) if vals else float("nan")


# ---------------------------------------------------------------------------
# FIX 3a -- fast exit simulator (mirrors trend_backtest.simulate_trade exactly)
# ---------------------------------------------------------------------------
def _fast_sim(open_a, low_a, close_a, dlow_a, ep, init_stop, cost_frac, max_hold) -> dict | None:
    """Numpy exit simulation: initial stop + Donchian trailing + MAX_HOLD.

    Identical logic to trend_backtest.simulate_trade (verified by equivalence test).
    """
    last = len(open_a) - 1
    if ep > last:
        return None
    entry = open_a[ep]
    if not np.isfinite(entry) or entry <= 0:
        return None
    if (entry - init_stop) / entry <= 0:
        return None
    eff = float(init_stop)
    for j in range(ep, last + 1):
        cand = dlow_a[j]
        if np.isfinite(cand):
            eff = max(eff, float(cand))
        loj = low_a[j]
        opj = open_a[j]
        if loj <= eff:
            exitp = opj if opj <= eff else eff
            xj = j
            break
        if (j - ep + 1) >= max_hold:
            exitp = close_a[j]
            xj = j
            break
        if j == last:
            exitp = close_a[j]
            xj = j
            break
    gross = exitp / entry - 1.0
    return {"entry_pos": int(ep), "exit_pos": int(xj),
            "gross": float(gross), "net": float(gross - cost_frac)}


# ---------------------------------------------------------------------------
# FIX 3b -- fair random null (matched exit + matched pre-filter)
# ---------------------------------------------------------------------------
def fair_random_null(
    prices: dict[str, pd.DataFrame],
    xu100: pd.Series,
    strategy_slice_mean_rel: float,
    n_target: int,
    slice_lo: str,
    slice_hi: str,
    parabolic_on: bool,
    cost_bps: float,
    seed: int = cfg.FAIR_NULL_SEED,
    n_resamples: int = cfg.FAIR_NULL_N_RESAMPLES,
    stop_mult: float = cfg.FAIR_NULL_STOP_ATR_MULT,
    trail_n: int = cfg.FAIR_NULL_TRAIL_DONCHIAN_N,
) -> dict:
    """Null distribution of mean XU100-relative return for matched random entries.

    Random entries: same exit machinery (ATR-stop + Donchian trailing + MAX_HOLD)
    AND same active pre-filter (ADV universe always; parabolic-eligibility when
    parabolic_on) -> isolates entry timing. Entry day must fall in the slice.
    """
    if n_target <= 0 or not np.isfinite(strategy_slice_mean_rel):
        return {"n_target": int(n_target), "pool_size": 0, "null_mean": float("nan"),
                "null_p95": float("nan"), "random_pctile": float("nan"),
                "beats_fair_random_95": False}
    cost = cost_bps / 10_000.0
    warm = tsig._warmup()
    pool: list[tuple[str, int]] = []
    cache: dict[str, tuple] = {}
    for tk, o in prices.items():
        n = len(o)
        if n <= warm + 2:
            continue
        ix = tsig.compute_indicators(o)
        dlow = ind.donchian_lower_prior(o["low"], trail_n)
        open_a = o["open"].to_numpy(float)
        low_a = o["low"].to_numpy(float)
        close_a = o["close"].to_numpy(float)
        atr_a = ix["atr"].to_numpy(float)
        dlow_a = dlow.to_numpy(float)
        xu_a = xu100.reindex(o.index).ffill().to_numpy(float)
        cache[tk] = (open_a, low_a, close_a, atr_a, dlow_a, xu_a)
        dates = o.index
        lo_ser, swing_lo = o["low"], ix["swing_lo"]
        for s in range(warm, n - 2):
            ed = dates[s + 1].strftime("%Y-%m-%d")
            if not (slice_lo <= ed <= slice_hi):
                continue
            a = atr_a[s]
            if not np.isfinite(a) or a <= 0:
                continue
            if parabolic_on and tsig._parabolic_block(close_a[s], ix, s, lo_ser, swing_lo):
                continue
            pool.append((tk, s))
    if len(pool) < n_target:
        return {"n_target": int(n_target), "pool_size": len(pool), "null_mean": float("nan"),
                "null_p95": float("nan"), "random_pctile": float("nan"),
                "beats_fair_random_95": False}
    rng = np.random.default_rng(seed)
    pool_arr = np.arange(len(pool))
    null_means = np.empty(n_resamples, dtype=float)
    for r in range(n_resamples):
        pick = rng.choice(pool_arr, size=n_target, replace=True)
        rels: list[float] = []
        for pi in pick:
            tk, s = pool[pi]
            open_a, low_a, close_a, atr_a, dlow_a, xu_a = cache[tk]
            init_stop = close_a[s] - stop_mult * atr_a[s]
            sim = _fast_sim(open_a, low_a, close_a, dlow_a, s + 1, init_stop, cost, MAX_HOLD_DAYS)
            if sim is None:
                continue
            xe, xx = xu_a[sim["entry_pos"]], xu_a[sim["exit_pos"]]
            if not (np.isfinite(xe) and np.isfinite(xx)) or xe <= 0:
                continue
            xu_ret = xx / xe - 1.0
            rels.append((1.0 + sim["gross"]) / (1.0 + xu_ret) - 1.0 - cost)
        null_means[r] = float(np.mean(rels)) if rels else 0.0
    pctile = float(np.mean(null_means < strategy_slice_mean_rel))
    return {
        "n_target": int(n_target), "pool_size": len(pool),
        "null_mean": round(float(np.mean(null_means)), 5),
        "null_p95": round(float(np.percentile(null_means, 95)), 5),
        "strategy_slice_mean_rel": round(float(strategy_slice_mean_rel), 5),
        "random_pctile": round(pctile, 4),
        "beats_fair_random_95": bool(pctile >= cfg.DECISION_RANDOM_PCTILE_MIN),
    }


# ---------------------------------------------------------------------------
# FIX 3c -- cross-sectional-robust significance (daily aggregation + block bootstrap)
# ---------------------------------------------------------------------------
def daily_aggregated_series(trades: list[dict], key: str = "rel_net_return") -> np.ndarray:
    """Mean of `key` grouped by EXIT date -> one value/day (collapses same-day cluster)."""
    by: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        v = t.get(key)
        if v is not None:
            by[t["exit_date"]].append(float(v))
    if not by:
        return np.array([], dtype=float)
    return np.array([np.mean(by[d]) for d in sorted(by)], dtype=float)


def cs_significance(trades: list[dict], key: str = "rel_net_return") -> dict:
    """Block-bootstrap 95% CI of the mean daily-aggregated relative return."""
    series = daily_aggregated_series(trades, key)
    if len(series) < 2:
        return {"n_days": int(len(series)), "mean": float("nan"),
                "ci95_low": float("nan"), "ci95_high": float("nan"), "ci_excludes_zero": False}
    lo, hi = block_bootstrap_ci(series, cfg.SIG_BLOCK, cfg.SIG_N_BOOT, cfg.SIG_SEED)
    return {"n_days": int(len(series)), "mean": round(float(np.mean(series)), 5),
            "ci95_low": round(lo, 5), "ci95_high": round(hi, 5),
            "ci_excludes_zero": bool(lo > 0 or hi < 0)}


# ---------------------------------------------------------------------------
# DEC-044 verdict
# ---------------------------------------------------------------------------
def d186_verdict(null_block: dict, portfolio_max_dd: float, cs_block: dict) -> dict:
    """Frozen DEC-044: disinflation + XU100-relative + fair-null>95pctile + DD<=35%."""
    mean_rel = null_block.get("strategy_slice_mean_rel", float("nan"))
    pos = np.isfinite(mean_rel) and mean_rel > 0
    beats = bool(null_block.get("beats_fair_random_95"))
    dd_ok = np.isfinite(portfolio_max_dd) and portfolio_max_dd <= cfg.DECISION_MAXDD_MAX
    fails: list[str] = []
    if not pos:
        fails.append("rel_expectancy<=0")
    if not beats:
        fails.append("fails_fair_random_benchmark")
    if not dd_ok:
        fails.append("max_dd_exceeded")
    return {
        "passes_DEC044": bool(pos and beats and dd_ok),
        "slice_mean_rel_return": round(float(mean_rel), 5) if np.isfinite(mean_rel) else None,
        "beats_fair_random_95": beats,
        "random_pctile": null_block.get("random_pctile"),
        "portfolio_max_dd": portfolio_max_dd,
        "dd_ok": bool(dd_ok),
        "cs_ci_excludes_zero": cs_block.get("ci_excludes_zero"),
        "failures": fails,
    }

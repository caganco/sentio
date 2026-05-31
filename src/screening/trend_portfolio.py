"""D-186 FIX 1 -- concurrency-capped, equal-weight, daily mark-to-market portfolio.

Replaces D-185's broken sequential_equity_max_dd (full-capital cumprod ->
total_net_return ~1e+26, max_dd~0.99 deterministic artifact). This builds a REAL
portfolio equity curve: at most K simultaneous open positions, each a fixed
notional slot (1/K of initial equity), marked daily on close -> real max-drawdown
(bounded, realistic) + a daily portfolio-return series (used for cross-sectional-
robust significance, since same-day trades collapse into one daily return).

Consumes the SAME D-185 trade dicts (entry_date/exit_date/entry/net_return). No
composite / conviction / signal-engine imports.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from src.screening import trend_d186_config as cfg


def build_portfolio(
    trades: list[dict],
    prices: dict[str, pd.DataFrame],
    k: int = cfg.PORTFOLIO_MAX_CONCURRENT,
    slot_fraction: float = cfg.PORTFOLIO_SLOT_FRACTION,
    initial_equity: float = cfg.PORTFOLIO_INITIAL_EQUITY,
) -> dict:
    """Concurrency-capped daily MTM portfolio. Returns equity curve + real max-DD.

    Slot contention: admit earliest (entry_date, ticker); excess skipped + counted.
    Interim marks use gross close/entry; realization on exit uses net_return (cost).
    """
    if not trades:
        return {"max_drawdown": float("nan"), "final_equity": float("nan"),
                "n_admitted": 0, "n_skipped": 0, "equity_curve": pd.Series(dtype=float),
                "daily_returns": pd.Series(dtype=float)}

    # 1) admit by concurrency cap (earliest entry_date, then ticker)
    ordered = sorted(trades, key=lambda t: (t["entry_date"], t["ticker"]))
    open_exits: list[pd.Timestamp] = []
    admitted: list[dict] = []
    skipped = 0
    for t in ordered:
        e = pd.Timestamp(t["entry_date"])
        open_exits = [x for x in open_exits if x >= e]   # free positions exited before e
        if len(open_exits) < k:
            admitted.append(t)
            open_exits.append(pd.Timestamp(t["exit_date"]))
        else:
            skipped += 1
    if not admitted:
        return {"max_drawdown": float("nan"), "final_equity": float("nan"),
                "n_admitted": 0, "n_skipped": skipped, "equity_curve": pd.Series(dtype=float),
                "daily_returns": pd.Series(dtype=float)}

    # 2) daily timeline = union of dates across admitted tickers, within [minEntry, maxExit]
    tickers = {t["ticker"] for t in admitted}
    min_e = min(pd.Timestamp(t["entry_date"]) for t in admitted)
    max_x = max(pd.Timestamp(t["exit_date"]) for t in admitted)
    date_set: set[pd.Timestamp] = set()
    for tk in tickers:
        idx = prices[tk].index
        date_set.update(d for d in idx if min_e <= d <= max_x)
    timeline = sorted(date_set)
    close_map = {tk: prices[tk]["close"].reindex(timeline).ffill() for tk in tickers}

    # 3) schedule entries/exits
    entries_by: dict[pd.Timestamp, list[int]] = defaultdict(list)
    exits_by: dict[pd.Timestamp, list[int]] = defaultdict(list)
    for i, t in enumerate(admitted):
        entries_by[pd.Timestamp(t["entry_date"])].append(i)
        exits_by[pd.Timestamp(t["exit_date"])].append(i)

    slot_cap = slot_fraction * initial_equity
    cash = initial_equity
    open_pos: dict[int, dict] = {}
    equity = np.empty(len(timeline), dtype=float)

    for di, d in enumerate(timeline):
        for i in entries_by.get(d, []):          # deploy cash
            cash -= slot_cap
            open_pos[i] = admitted[i]
        for i in exits_by.get(d, []):            # realize net (incl. cost)
            t = open_pos.pop(i, None)
            if t is not None:
                cash += slot_cap * (1.0 + t["net_return"])
        marks = 0.0                              # MTM remaining open positions
        for t in open_pos.values():
            c = close_map[t["ticker"]].get(d, np.nan)
            if not np.isfinite(c):
                c = t["entry"]
            marks += slot_cap * (c / t["entry"])
        equity[di] = cash + marks

    eq = pd.Series(equity, index=pd.DatetimeIndex(timeline))
    daily_ret = eq.pct_change().dropna()
    peak = -np.inf
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return {
        "max_drawdown": round(float(mdd), 4),
        "final_equity": round(float(equity[-1]), 4),
        "n_admitted": len(admitted),
        "n_skipped": int(skipped),
        "equity_curve": eq,
        "daily_returns": daily_ret,
    }

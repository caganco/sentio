"""D-188 -- event-study forward returns + confluence flags (look-ahead safe).

For each catalyst event: event_day = published_at; ACTION at t+1 (enter the bar
AFTER the disclosure -> the speed disadvantage is modelled). Forward return over
each horizon is measured close-to-close and expressed XU100-RELATIVE (geometric
excess over the index, net of cost+slippage) -- the D-186 nominal-drift lesson.

Reuses trend_d186._ret_over (geometric point-in-time return). No network, no
composite/engine imports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening.event_config import (
    ENTRY_OFFSET_DAYS,
    EVENT_HORIZONS,
    TOTAL_COST_BPS,
    regime_label,
)
from src.screening.event_confirm import bar_pos, technical_confirm
from src.screening.trend_d186 import _ret_over


def forward_window(ohlcv: pd.DataFrame, event_date, horizon: int,
                   offset: int = ENTRY_OFFSET_DAYS):
    """(entry_date, exit_date, gross_return) for a t+offset entry held `horizon` bars.

    entry = close at (event bar + offset); exit = close at (entry + horizon).
    Returns None if the bars do not exist (event too recent / near series end).
    """
    pos = bar_pos(ohlcv, event_date)
    if pos < 0:
        return None
    entry_pos = pos + offset
    exit_pos = entry_pos + horizon
    if entry_pos < 0 or exit_pos > len(ohlcv) - 1:
        return None
    close = ohlcv["Close"].to_numpy(dtype="float64")
    entry_px, exit_px = close[entry_pos], close[exit_pos]
    if not (np.isfinite(entry_px) and np.isfinite(exit_px)) or entry_px <= 0:
        return None
    idx = ohlcv.index
    entry_date = str(pd.Timestamp(idx[entry_pos]).date())
    exit_date = str(pd.Timestamp(idx[exit_pos]).date())
    return entry_date, exit_date, float(exit_px / entry_px - 1.0)


def relative_net(gross: float, xu100: pd.Series, entry_date: str, exit_date: str,
                 cost_bps: float = TOTAL_COST_BPS) -> float | None:
    """XU100-relative net return: (1+gross)/(1+xu_ret) - 1 - cost. None if index NaN."""
    xu = _ret_over(xu100, entry_date, exit_date)
    if not np.isfinite(xu):
        return None
    cost = cost_bps / 10_000.0
    return round((1.0 + gross) / (1.0 + xu) - 1.0 - cost, 5)


def build_event_returns(
    events: list[dict],
    prices: dict[str, pd.DataFrame],
    xu100: pd.Series,
    horizons: tuple[int, ...] = EVENT_HORIZONS,
    cost_bps: float = TOTAL_COST_BPS,
) -> list[dict]:
    """Enrich each event with technical-confirm flag + per-horizon XU100-relative return.

    Output per event: {..., technical_confirm, regime, rel_net: {h: value|None}}.
    Events whose ticker has no price frame are skipped.
    """
    out: list[dict] = []
    for ev in events:
        ohlcv = prices.get(ev["ticker"])
        if ohlcv is None or len(ohlcv) == 0:
            continue
        confirm = technical_confirm(ohlcv, ev["event_date"])
        rel: dict[int, float | None] = {}
        for h in horizons:
            fw = forward_window(ohlcv, ev["event_date"], h)
            if fw is None:
                rel[h] = None
                continue
            entry_date, exit_date, gross = fw
            rel[h] = relative_net(gross, xu100, entry_date, exit_date, cost_bps)
        enriched = dict(ev)
        enriched["technical_confirm"] = bool(confirm)
        enriched["regime"] = regime_label(ev["event_date"])
        enriched["rel_net"] = rel
        out.append(enriched)
    return out


def split_confluence(enriched: list[dict], horizon: int) -> dict:
    """Per-horizon split of enriched events into confluence / event-only sets.

    confluence = event AND technical_confirm; event_only = event AND NOT confirm.
    Returns arrays of XU100-relative returns (NaNs dropped) + their means.
    """
    conf, eonly = [], []
    for e in enriched:
        v = e["rel_net"].get(horizon)
        if v is None:
            continue
        (conf if e["technical_confirm"] else eonly).append(float(v))
    conf_a = np.array(conf, dtype=float)
    eonly_a = np.array(eonly, dtype=float)
    return {
        "confluence_returns": conf_a,
        "event_only_returns": eonly_a,
        "n_confluence": int(conf_a.size),
        "n_event_only": int(eonly_a.size),
        "confluence_mean": float(conf_a.mean()) if conf_a.size else float("nan"),
        "event_only_mean": float(eonly_a.mean()) if eonly_a.size else float("nan"),
    }

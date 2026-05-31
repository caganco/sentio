"""D-188 -- technical confirmation layer (look-ahead safe, OHLCV-only).

A catalyst event "confluence" requires technical confirmation on the event bar:
  - volume surge: event-day volume / trailing volume MA (EXCLUDING the event bar) > mult
  - breakout: event-day close > prior N-bar high (EXCLUDING the event bar)

Both use only data up to and including the event bar -> no look-ahead.
Pure functions over an injected OHLCV DataFrame (yfinance shape: Open/High/Low/
Close/Volume on a DatetimeIndex). No network, no composite/engine imports.
"""
from __future__ import annotations

import pandas as pd

from src.screening.event_config import (
    BREAKOUT_RESISTANCE_N,
    VOLUME_SURGE_MULT,
    VOLUME_SURGE_WINDOW,
)


def bar_pos(ohlcv: pd.DataFrame, date) -> int:
    """Integer position of the last bar with index <= date; -1 if none / empty."""
    if ohlcv is None or len(ohlcv) == 0:
        return -1
    ts = pd.Timestamp(date)
    idx = ohlcv.index
    # positions of bars at or before `date`
    le = idx[idx <= ts]
    if len(le) == 0:
        return -1
    return int(idx.get_indexer([le[-1]])[0])


def volume_surge(
    ohlcv: pd.DataFrame, date,
    win: int = VOLUME_SURGE_WINDOW, mult: float = VOLUME_SURGE_MULT,
) -> bool:
    """Event-day volume / trailing `win`-bar mean volume (excl. event bar) > mult."""
    pos = bar_pos(ohlcv, date)
    if pos < win:
        return False
    vol = ohlcv["Volume"].to_numpy(dtype="float64")
    ev = vol[pos]
    trailing = vol[pos - win:pos]   # excludes the event bar
    if trailing.size == 0:
        return False
    ma = float(trailing.mean())
    if not (ma > 0) or not (ev == ev):  # ma>0 and ev not NaN
        return False
    return bool(ev / ma > mult)


def breakout(ohlcv: pd.DataFrame, date, n: int = BREAKOUT_RESISTANCE_N) -> bool:
    """Event-day close > prior `n`-bar high (excl. event bar) -> resistance breakout."""
    pos = bar_pos(ohlcv, date)
    if pos < n:
        return False
    high = ohlcv["High"].to_numpy(dtype="float64")
    close = ohlcv["Close"].to_numpy(dtype="float64")
    prior_high = high[pos - n:pos]   # excludes the event bar
    if prior_high.size == 0:
        return False
    ev_close = close[pos]
    if not (ev_close == ev_close):   # NaN guard
        return False
    return bool(ev_close > float(prior_high.max()))


def technical_confirm(ohlcv: pd.DataFrame, date) -> bool:
    """Confluence technical leg: volume surge AND breakout on the event bar."""
    return volume_surge(ohlcv, date) and breakout(ohlcv, date)

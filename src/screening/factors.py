"""Faz 0 price-only factors (RAW sub-factors). D-177.

Deterministic and look-ahead safe: factors use only PAST prices; forward returns
are the IC label (intentionally future). No composite/conviction/engine imports.

- rs_vs_xu100   : relative strength vs XU100 (stock - index), skip-1-month.
- realized_vol  : trailing std of daily log returns (low-vol factor source).
- forward_returns: future simple return (IC label).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def close_panel(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """{ticker: OHLCV df} -> wide Close panel (index=date, columns=ticker).

    Columns sorted for determinism; rows sorted by date.
    """
    closes = {t: df["Close"] for t, df in prices.items()}
    panel = pd.DataFrame(closes).sort_index()
    return panel.reindex(sorted(panel.columns), axis=1)


def rs_vs_xu100(
    close: pd.DataFrame,
    xu100: pd.Series,
    lookback: int,
    skip: int,
) -> pd.DataFrame:
    """Relative strength vs XU100 over the window [t-skip-lookback, t-skip].

    rs = stock_ret(window) - xu100_ret(window). Relative (not absolute nominal)
    so the common inflation drift cancels (invariant 5). Uses only past prices.
    Returns a (date x ticker) panel; NaN where insufficient history.
    """
    xu = xu100.reindex(close.index).ffill()
    shift_total = skip + lookback
    stock_ret = close.shift(skip) / close.shift(shift_total) - 1.0
    xu_ret = xu.shift(skip) / xu.shift(shift_total) - 1.0
    return stock_ret.sub(xu_ret, axis=0)


def realized_vol(close: pd.DataFrame, window: int) -> pd.DataFrame:
    """Trailing realized volatility of daily log returns over `window` days.

    Higher value = more volatile (the low-vol factor inverts this at rank stage).
    Look-ahead safe (trailing only).

    min_periods = ceil(0.75*window): BIST names have scattered halt/non-trading
    days, so on a union calendar each name carries ~few NaN returns. Requiring a
    FULL gap-free window (default min_periods=window) nulls vol after any single
    halt and collapses the low-vol cross-section (~113 vs ~560 usable dates here).
    A 75%-present window keeps vol representative without look-ahead. (D-178.)
    """
    log_ret = np.log(close / close.shift(1))
    min_p = max(2, int(np.ceil(window * 0.75)))
    return log_ret.rolling(window, min_periods=min_p).std()


def forward_returns(close: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Forward simple return over `horizon` days: close(t+h)/close(t) - 1.

    This is the IC LABEL -> intentionally uses future prices.
    """
    return close.shift(-horizon) / close - 1.0

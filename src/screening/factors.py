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


# ---------------------------------------------------------------------------
# D-183 Faz 0b: value factors (P/B, EV/EBITDA) -- point-in-time, look-ahead safe
# ---------------------------------------------------------------------------

def _pit_index(funds: pd.DataFrame) -> dict[str, list[tuple[str, dict]]]:
    """ticker -> [(pub_date, row_fields), ...] sorted ascending by pub_date."""
    idx: dict[str, list[tuple[str, dict]]] = {}
    for tkr, g in funds.groupby("ticker"):
        recs = [(str(r["pub_date"]), r.to_dict())
                for _, r in g.sort_values("pub_date").iterrows()]
        idx[tkr] = recs
    return idx


def _latest_as_of(recs: list[tuple[str, dict]], asof: str) -> dict | None:
    """Latest annual whose pub_date <= asof (point-in-time, no look-ahead)."""
    chosen = None
    for pub, row in recs:                      # recs sorted ascending
        if pub <= asof:
            chosen = row
        else:
            break
    return chosen


def value_ratios(
    funds: pd.DataFrame,
    close: pd.DataFrame,
    dates: pd.DatetimeIndex,
    par: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-date cross-sectional P/B and EV/EBITDA panels (TL, point-in-time).

    For each (date t, ticker): pick the latest annual with pub_date <= t.
    shares = issued_capital / par; market_cap = shares * close(t).
    P/B = market_cap / book_eaoop  (book<=0 -> NaN).
    EV/EBITDA = (market_cap + total_liab - cash) / (op_profit + d_and_a)
                (bank or missing comps -> NaN; EBITDA<=0 -> NaN).
    Lower ratio = cheaper = higher value (inverted at rank stage). FX-free (TL);
    USD conversion is rank-invariant (D-180) -> applied only for sanity/level.
    """
    pit = _pit_index(funds)
    cols = sorted(close.columns)
    pb = pd.DataFrame(index=dates, columns=cols, dtype=float)
    ev = pd.DataFrame(index=dates, columns=cols, dtype=float)
    for t in dates:
        asof = pd.Timestamp(t).strftime("%Y-%m-%d")
        for tkr in cols:
            recs = pit.get(tkr)
            if not recs:
                continue
            row = _latest_as_of(recs, asof)
            if row is None:
                continue
            price = close.at[t, tkr] if tkr in close.columns else np.nan
            ic = row.get("issued_capital")
            book = row.get("book_eaoop")
            if price is None or np.isnan(price) or ic is None or float(par) <= 0:
                continue
            shares = float(ic) / float(par)
            mcap = shares * float(price)
            if book is not None and float(book) > 0:
                pb.at[t, tkr] = mcap / float(book)
            if not bool(row.get("is_bank")):
                tl = row.get("total_liab"); cash = row.get("cash")
                op = row.get("operating_profit"); da = row.get("d_and_a")
                if None not in (tl, cash, op, da):
                    ebitda = float(op) + float(da)
                    if ebitda > 0:
                        ev.at[t, tkr] = (mcap + float(tl) - float(cash)) / ebitda
    return pb, ev

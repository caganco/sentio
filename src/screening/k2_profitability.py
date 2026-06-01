"""K2 profitability factor panels (Novy-Marx GP/TA + ROE). D-191.

Strangler-clean ADD-ON: reuses the point-in-time helpers from factors.py
(_pit_index / _latest_as_of) read-only; does NOT modify factors.py. No
composite/conviction/engine imports (screening isolation).

profitability_panel(funds, close, dates, kind):
  kind="gpa" -> gross_profit / total_assets   (Novy-Marx 2013, PRIMARY)
  kind="roe" -> net_income  / book_eaoop       (robustness; equity attributable)

Point-in-time + look-ahead safe: for each (date t, ticker) pick the latest annual
whose pub_date <= t (pub_date = period_end + lag, frozen upstream). Higher value =
higher rank (NOT inverted). Banks: GP/TA undefined -> NULL (R3). Missing/<=0
denominator -> NULL.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.screening.factors import _latest_as_of, _pit_index


def profitability_panel(
    funds: pd.DataFrame,
    close: pd.DataFrame,
    dates: pd.DatetimeIndex,
    kind: str = "gpa",
) -> pd.DataFrame:
    """Per-date cross-sectional profitability panel (date x ticker).

    kind="gpa": gross_profit / total_assets (banks -> NULL; gross profit undefined).
    kind="roe": net_income / book_eaoop (equity attributable to parent).
    Look-ahead safe via _latest_as_of (pub_date <= t). Returns NaN where undefined.
    """
    if kind not in ("gpa", "roe"):
        raise ValueError(f"profitability kind must be 'gpa' or 'roe', got {kind!r}")
    pit = _pit_index(funds)
    cols = sorted(close.columns)
    out = pd.DataFrame(index=dates, columns=cols, dtype=float)
    for t in dates:
        asof = pd.Timestamp(t).strftime("%Y-%m-%d")
        for tkr in cols:
            recs = pit.get(tkr)
            if not recs:
                continue
            row = _latest_as_of(recs, asof)
            if row is None:
                continue
            val = _ratio(row, kind)
            if val is not None:
                out.at[t, tkr] = val
    return out


def _ratio(row: dict, kind: str) -> float | None:
    """Single point-in-time profitability ratio from a fundamental row."""
    if kind == "gpa":
        if bool(row.get("is_bank")):          # banks: no comparable gross profit (R3)
            return None
        num = row.get("gross_profit")
        den = row.get("total_assets")
    else:  # roe
        num = row.get("net_income")
        den = row.get("book_eaoop")
    if num is None or den is None:
        return None
    den = float(den)
    if den <= 0 or not np.isfinite(den):      # negative/zero equity or assets -> undefined
        return None
    num = float(num)
    if not np.isfinite(num):
        return None
    return num / den

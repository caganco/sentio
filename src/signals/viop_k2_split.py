"""VIOP K2 harness helpers: liquidity split + Signal wrapper.

LiquiditySplit: diagnostic utility — splits tickers into high/low OI groups
for the Mod-A name-split diagnostic report.

ViOpK2Signal: implements the Signal protocol for the engine harness.
  - Scores are K2 values at month-end dates.
  - Non-month-end dates → empty Series (no opinion).
  - OI_prev floor applied at construction to suppress new-contract outliers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from src.engine.contracts import Panel
from src.engine.signal_protocol import Signal

_OI_PREV_FLOOR: Final[int] = 500  # suppress outlier K2 from new contracts with tiny OI_prev


@dataclass(frozen=True)
class LiquiditySplit:
    """High/low liquidity ticker groups computed from median OI."""

    high_liq: list[str]  # top-half by median OI
    low_liq: list[str]  # bottom-half by median OI
    median_oi: pd.Series  # index=ticker, values=median OI over history


def compute_liquidity_split(k2_df: pd.DataFrame) -> LiquiditySplit:
    """Split tickers into high/low liquidity groups by median OI.

    Only tickers with OI_prev >= 500 in at least one observation are included.
    Tickers with below-floor OI are omitted from both groups.

    Args:
        k2_df: DataFrame with columns [ticker, OI, OI_prev, K2, ...].

    Returns:
        LiquiditySplit with high_liq (top half) and low_liq (bottom half).
    """
    if k2_df.empty:
        return LiquiditySplit(high_liq=[], low_liq=[], median_oi=pd.Series(dtype=float))

    valid = k2_df[k2_df["OI_prev"].fillna(0) >= _OI_PREV_FLOOR]
    if valid.empty:
        return LiquiditySplit(high_liq=[], low_liq=[], median_oi=pd.Series(dtype=float))

    median_oi = valid.groupby("ticker")["OI"].median().sort_values(ascending=False)
    n = len(median_oi)
    mid = n // 2 + (n % 2)  # top group gets the extra ticker when odd
    high_liq = median_oi.iloc[:mid].index.tolist()
    low_liq = median_oi.iloc[mid:].index.tolist()
    return LiquiditySplit(high_liq=high_liq, low_liq=low_liq, median_oi=median_oi)


class ViOpK2Signal:
    """Cross-sectional K2 scorer implementing the engine Signal protocol.

    construction_window = 21 trading days (approximately 1 month); used by the
    harness as the forward-return horizon h and Mod-B embargo.
    """

    name: str = "viop_k2_oi_growth"
    construction_window: int = 21  # ~1 month in trading days

    def __init__(self, k2_df: pd.DataFrame, oi_prev_floor: int = _OI_PREV_FLOOR) -> None:
        """
        Args:
            k2_df: DataFrame with columns [date, ticker, K2, OI_prev, ...].
            oi_prev_floor: rows with OI_prev < floor are excluded (K2 suppressed).
        """
        filtered = k2_df[k2_df["OI_prev"].fillna(0) >= oi_prev_floor].copy()
        self._pivot: pd.DataFrame = filtered.pivot_table(
            index="date", columns="ticker", values="K2", aggfunc="last"
        )
        self._pivot.index = pd.to_datetime(self._pivot.index)

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        """Return K2 scores for names at asof date.

        Returns empty Series for dates not in K2 index (non-month-end eval dates
        are naturally absent → the harness masks them as NaN).
        """
        if asof not in self._pivot.index:
            return pd.Series(dtype=float)
        row = self._pivot.loc[asof]
        valid = row[row.index.isin(names)].dropna()
        return valid


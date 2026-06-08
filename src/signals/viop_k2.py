"""VIOP K2 signal: monthly SSF OI-growth rate cross-sectional scorer.

K2_t = (OI_t - OI_{t-1}) / OI_{t-1}

Stage-0 thread: VIOP-SSF-OI. Breadth veto: <10 names/month → NaN.
Total valid months < 36 → InsufficientDataError (TRADEABLE-DEĞİL).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from src.data.viop_loader import InsufficientDataError, ViOpMonthlyPanel
from src.engine.data_adapter import load_panel
from src.engine.signal_protocol import PM1Violation, assert_pm1_compliant

logger = logging.getLogger(__name__)

# Frozen Stage-0 breadth constraints (VIOP-SSF-OI pre-registration).
_MIN_NAMES_PER_MONTH: Final[int] = 10
_MIN_VALID_MONTHS: Final[int] = 36

_STAGE0_PATH: Final[Path] = (
    Path(__file__).resolve().parents[2] / "docs" / "yol1" / "STAGE0_VIOP_SSF_OI.json"
)


@dataclass
class SignalPanel:
    """K2 signal panel ready for harness input."""

    data: pd.DataFrame  # cols: date, ticker, K2, spot_fwd_ret_1m, OI, OI_prev,
    #                          n_month_names (int), breadth_excluded (bool)
    metadata: dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# K2 computation
# ---------------------------------------------------------------------------

def compute_k2(panel: ViOpMonthlyPanel) -> pd.DataFrame:
    """Compute K2 = OI_t/OI_{t-1} - 1 per ticker; apply breadth veto.

    Returns DataFrame with columns: date, ticker, K2, OI, OI_prev,
    n_month_names, breadth_excluded. Rows with OI_{t-1}==0 or NaN → K2=NaN.

    Raises:
        InsufficientDataError: valid months after breadth veto < 36.
    """
    df = panel.data.reset_index()  # year_month, ticker, OI, ISLEM_HACMI, ISLEM_MIKTARI

    # Pivot to (month × ticker) for lag
    oi_wide = df.pivot(index="year_month", columns="ticker", values="OI").sort_index()

    oi_prev = oi_wide.shift(1)

    # K2: divide where prev > 0; NaN otherwise
    with np.errstate(divide="ignore", invalid="ignore"):
        k2_wide = np.where(
            (oi_prev.to_numpy(dtype=float) > 0) & (~np.isnan(oi_prev.to_numpy(dtype=float))),
            (oi_wide.to_numpy(dtype=float) - oi_prev.to_numpy(dtype=float))
            / oi_prev.to_numpy(dtype=float),
            np.nan,
        )
    k2_df = pd.DataFrame(k2_wide, index=oi_wide.index, columns=oi_wide.columns)

    # Melt back to long form
    records: list[dict[str, object]] = []
    for ym in k2_df.index:
        n_valid = int(k2_df.loc[ym].notna().sum())
        for ticker in k2_df.columns:
            k2_val = k2_df.loc[ym, ticker]
            oi_val = oi_wide.loc[ym, ticker] if ticker in oi_wide.columns else float("nan")
            oi_prev_val = oi_prev.loc[ym, ticker] if ticker in oi_prev.columns else float("nan")
            breadth_excluded = n_valid < _MIN_NAMES_PER_MONTH
            records.append({
                "date": ym.to_timestamp(how="end").normalize(),
                "ticker": ticker,
                "K2": float("nan") if breadth_excluded else float(k2_val) if not pd.isna(k2_val) else float("nan"),
                "OI": float(oi_val) if not pd.isna(oi_val) else float("nan"),
                "OI_prev": float(oi_prev_val) if not pd.isna(oi_prev_val) else float("nan"),
                "n_month_names": n_valid,
                "breadth_excluded": breadth_excluded,
            })

    long = pd.DataFrame(records)

    # Count valid months (at least 1 non-NaN K2 in the month, breadth not excluded)
    valid_month_mask = long.groupby("date")["K2"].transform(lambda x: x.notna().any())
    n_valid_months = int(valid_month_mask.sum() > 0)  # conservative count via unique dates
    unique_valid_dates = long[long["K2"].notna()]["date"].nunique()
    if unique_valid_dates < _MIN_VALID_MONTHS:
        raise InsufficientDataError(
            f"Only {unique_valid_dates} valid months after breadth veto "
            f"(Stage-0 minimum: {_MIN_VALID_MONTHS}). "
            "TRADEABLE-DEĞİL — verdict is independent of NW-t."
        )

    breadth_excluded_months = int(long[long["breadth_excluded"]]["date"].nunique())
    if breadth_excluded_months:
        logger.info(
            "viop_k2: %d month(s) breadth-excluded (<10 names); K2=NaN for those dates.",
            breadth_excluded_months,
        )

    return long


# ---------------------------------------------------------------------------
# Spot forward-return join
# ---------------------------------------------------------------------------

def _monthly_forward_return(data_root: Path | None = None) -> pd.DataFrame:
    """Compute 1-month forward total return from tr_index_gross.

    Returns long DataFrame: date (month-end), ticker, spot_fwd_ret_1m.
    date = end of month M; spot_fwd_ret_1m = return over month M+1.
    """
    panel = load_panel(data_root)
    monthly_tr = panel.tr_gross.resample("ME").last()
    fwd = monthly_tr.shift(-1) / monthly_tr - 1.0
    long = (
        fwd.stack(future_stack=True)
        .reset_index()
        .rename(columns={"symbol": "ticker", 0: "spot_fwd_ret_1m"})
    )
    long["date"] = pd.to_datetime(long["date"]).dt.normalize()
    return long


def join_spot_returns(k2_df: pd.DataFrame, data_root: Path | None = None) -> pd.DataFrame:
    """Join K2 with 1-month forward spot return.

    PIT-safe: K2 at month-end M → spot_fwd_ret_1m is month M+1 return.
    No look-ahead: K2 is computed from OI knowable at end of month M.
    """
    fwd = _monthly_forward_return(data_root)
    merged = k2_df.merge(fwd, on=["date", "ticker"], how="left")
    return merged


# ---------------------------------------------------------------------------
# PM-1 check
# ---------------------------------------------------------------------------

def _check_pm1(k2_df: pd.DataFrame, signal_name: str = "viop_k2_oi_growth") -> None:
    """Validate PM-1 compliance for a representative cross-section.

    Constructs equal-weight top-tercile weights from K2 and asserts they
    sum to 1.0 with no negatives (fully-invested within-basket re-tilt).
    """
    last_date = k2_df["date"].max()
    day = k2_df[(k2_df["date"] == last_date) & k2_df["K2"].notna()]
    if len(day) < 3:
        return  # too few names to form a tercile; skip check
    n_top = max(1, len(day) // 3)
    top = day.nlargest(n_top, "K2")
    weights = pd.Series(
        [1.0 / n_top] * len(top), index=top["ticker"].to_numpy(), name=signal_name
    )
    assert_pm1_compliant(weights, name=signal_name)


# ---------------------------------------------------------------------------
# Public orchestration
# ---------------------------------------------------------------------------

def build_signal_panel(
    viop: ViOpMonthlyPanel,
    data_root: Path | None = None,
) -> SignalPanel:
    """Compute K2, join spot returns, verify PM-1.

    Raises:
        InsufficientDataError: valid months < 36.
        PM1Violation: constructed top-tercile weights fail PM-1.
    """
    k2_df = compute_k2(viop)
    full = join_spot_returns(k2_df, data_root)
    _check_pm1(k2_df)

    n_obs = len(full)
    n_tickers = int(full["ticker"].nunique())
    valid_dates = sorted(full[full["K2"].notna()]["date"].unique())
    breadth_excluded = int(full[full["breadth_excluded"]]["date"].nunique())
    date_range_str = (
        f"{valid_dates[0].date()} .. {valid_dates[-1].date()}" if valid_dates else "empty"
    )

    metadata: dict[str, object] = {
        "n_obs": n_obs,
        "n_tickers": n_tickers,
        "n_valid_months": len(valid_dates),
        "breadth_excluded_months": breadth_excluded,
        "date_range": date_range_str,
        "stage0_path": str(_STAGE0_PATH),
    }
    logger.info(
        "viop_k2: signal panel built — %d obs, %d tickers, %d valid months",
        n_obs, n_tickers, len(valid_dates),
    )
    return SignalPanel(data=full, metadata=metadata)

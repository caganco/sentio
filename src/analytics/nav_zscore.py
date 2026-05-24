"""NAV discount z-score tracker -- 252d rolling (D-143, RR-013 sec.5).

Append-only parquet: data/analytics/nav_history.parquet
Schema: date, ticker, nav_per_share, price, discount_pct,
        mean_252d, std_252d, z_score, signal

Signal zones (thresholds from thresholds.py):
  BUY        z >  NAV_ZSCORE_BUY       (+2.0)
  BUY-LEAN   z >  NAV_ZSCORE_BUY_LEAN  (+1.0)
  HOLD      -1.0 <= z <= +1.0
  TRIM       z <  NAV_ZSCORE_TRIM      (-1.0)
  AVOID      z <  NAV_ZSCORE_AVOID     (-2.0)
  COLLECTING  < 60 observations (insufficient history)

No signal engine import (K-08 invariant).
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Parquet schema column order (frozen)
_COLS: list[str] = [
    "date", "ticker", "nav_per_share", "price", "discount_pct",
    "mean_252d", "std_252d", "z_score", "signal",
]

# Minimum observations before a signal label is emitted
NAV_MIN_OBS_SIGNAL: int = 60


class NAVZScoreTracker:
    """Append-only NAV history + rolling 252-day z-score computation."""

    def __init__(self, history_path: str | None = None) -> None:
        from src.signals.thresholds import NAV_HISTORY_PATH
        self._path = Path(history_path or NAV_HISTORY_PATH)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def update(
        self,
        nav_result: dict,
        as_of_date: date | None = None,
    ) -> dict:
        """Append today's row and return z-score result dict.

        Args:
            nav_result: output dict from NAVCalculator.compute_tier1_nav()
            as_of_date: trading date (defaults to today)

        Returns:
            dict with keys: date, ticker, nav_per_share, price, discount_pct,
                            mean_252d, std_252d, z_score, signal
        """
        from src.signals.thresholds import NAV_LOOKBACK_DAYS

        today = as_of_date or date.today()
        ticker: str = nav_result["ticker"]
        disc: float = float(nav_result["discount_pct"])
        price: float = float(nav_result["price"])
        nav_ps: float = float(nav_result["nav_per_share"])

        # Load existing history BEFORE appending (no lookahead)
        history = self._load_history(ticker)
        n_obs = len(history)

        # Compute rolling stats from existing history
        mean_252d = float("nan")
        std_252d = float("nan")
        z_score = float("nan")

        if n_obs >= 2:
            window = history["discount_pct"].tail(NAV_LOOKBACK_DAYS).dropna()
            if len(window) >= 2:
                mean_252d = float(window.mean())
                std_252d = float(window.std(ddof=1))
                if std_252d > 0:
                    z_score = (disc - mean_252d) / std_252d

        signal = self._signal_label(z_score, n_obs)

        new_row: dict = {
            "date": today,
            "ticker": ticker,
            "nav_per_share": nav_ps,
            "price": price,
            "discount_pct": disc,
            "mean_252d": mean_252d,
            "std_252d": std_252d,
            "z_score": z_score,
            "signal": signal,
        }

        self._append(new_row)
        logger.info(
            "NAVZScore %s: disc=%.1f%% z=%.2f signal=%s n_obs=%d",
            ticker,
            disc * 100,
            z_score if not np.isnan(z_score) else float("nan"),
            signal,
            n_obs,
        )
        return new_row

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def _load_history(self, ticker: str) -> pd.DataFrame:
        """Load existing history for ticker; empty DataFrame if none."""
        if not self._path.exists():
            return pd.DataFrame(columns=_COLS)
        df = pd.read_parquet(self._path)
        return (
            df[df["ticker"] == ticker]
            .sort_values("date")
            .reset_index(drop=True)
        )

    def _signal_label(self, z_score: float, n_obs: int) -> str:
        """Map z-score + observation count to 5-zone signal label."""
        from src.signals.thresholds import (
            NAV_ZSCORE_AVOID,
            NAV_ZSCORE_BUY,
            NAV_ZSCORE_BUY_LEAN,
            NAV_ZSCORE_TRIM,
        )
        if n_obs < NAV_MIN_OBS_SIGNAL or np.isnan(z_score):
            return "COLLECTING"
        if z_score > NAV_ZSCORE_BUY:
            return "BUY"
        if z_score > NAV_ZSCORE_BUY_LEAN:
            return "BUY-LEAN"
        if z_score < NAV_ZSCORE_AVOID:
            return "AVOID"
        if z_score < NAV_ZSCORE_TRIM:
            return "TRIM"
        return "HOLD"

    def _append(self, row: dict) -> None:
        """Append row to parquet (idempotent: same date+ticker → overwrite)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        new_df = pd.DataFrame([row])[_COLS]
        new_df["date"] = pd.to_datetime(new_df["date"]).dt.date

        if self._path.exists():
            existing = pd.read_parquet(self._path)
            # Drop existing row for same date+ticker (idempotency)
            mask = ~(
                (existing["ticker"] == row["ticker"])
                & (existing["date"].astype(str) == str(row["date"]))
            )
            existing = existing[mask]
            combined = pd.concat([existing, new_df], ignore_index=True)
        else:
            combined = new_df

        combined.sort_values(["ticker", "date"], inplace=True)
        combined.reset_index(drop=True, inplace=True)
        combined.to_parquet(self._path, index=False, compression="snappy")

"""Multi-window foreign flow parser (D-144, CB-011).

Pure functions -- no network, no DB, no signal engine import.
K-08 architecture invariant: analytics/* -> engine import yok.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# QNBFB.IS correction: QNB Group holds ~99.8% and is classified foreign.
# Actual floating-share foreign ratio ~12% (KAP approximation).
_QNB_FLOAT_RATIO: float = 0.12


def qnb_filter(raw_foreign_pct: float, ticker: str) -> float:
    """Adjust QNBFB.IS foreign ownership to reflect actual free float.

    QNB Group (Qatar National Bank) classification inflates market-wide
    foreign ownership figure. Scale down QNBFB.IS to floating-share ratio.
    Returns raw_foreign_pct unchanged for any other ticker.
    """
    from src.signals.thresholds import (
        FOREIGN_FLOW_QNB_FILTER_ENABLED,
        FOREIGN_FLOW_QNB_TICKER,
    )

    if FOREIGN_FLOW_QNB_FILTER_ENABLED and ticker.upper() == FOREIGN_FLOW_QNB_TICKER:
        return raw_foreign_pct * _QNB_FLOAT_RATIO
    return raw_foreign_pct


def compute_multi_window(ticker: str, daily_series: list[float]) -> dict:
    """Compute multi-window foreign flow metrics.

    Args:
        ticker: e.g. "BIST" (market-wide) or specific stock ticker.
        daily_series: sequential foreign ownership % readings, most recent LAST.

    Returns:
        {
          delta_3d: float | None,  # (latest - 3d_ago) * 100 bps; None if < 4 pts
          delta_5d: float | None,  # None if < 6 pts
          delta_10d: float | None, # None if < 11 pts
          persistence: int,        # consecutive days same-direction change
          direction: str,          # "BUY" / "SELL" / "NEUTRAL"
          qnb_adjusted: bool,      # True if QNB filter applied to series
        }
    """
    from src.signals.thresholds import (
        FOREIGN_FLOW_QNB_FILTER_ENABLED,
        FOREIGN_FLOW_QNB_TICKER,
    )

    if not daily_series:
        return {
            "delta_3d": None,
            "delta_5d": None,
            "delta_10d": None,
            "persistence": 0,
            "direction": "NEUTRAL",
            "qnb_adjusted": False,
        }

    # Apply QNB filter to the whole series if applicable
    qnb_adjusted = False
    if FOREIGN_FLOW_QNB_FILTER_ENABLED and ticker.upper() == FOREIGN_FLOW_QNB_TICKER:
        series = [qnb_filter(v, ticker) for v in daily_series]
        qnb_adjusted = True
    else:
        series = list(daily_series)

    n = len(series)
    latest = series[-1]

    def _delta(window: int) -> "float | None":
        """Return (latest - value_window_days_ago) * 100 in bps."""
        if n > window:
            return (latest - series[-(window + 1)]) * 100.0
        return None

    d3 = _delta(3)
    d5 = _delta(5)
    d10 = _delta(10)

    # Persistence: count consecutive same-direction daily changes from the end
    persistence = 0
    if n >= 2:
        changes = [series[i] - series[i - 1] for i in range(1, n)]
        if changes:
            # Sign of last change (+1 up, -1 down, 0 flat)
            last_sign = 1 if changes[-1] > 0 else (-1 if changes[-1] < 0 else 0)
            if last_sign != 0:
                for ch in reversed(changes):
                    ch_sign = 1 if ch > 0 else (-1 if ch < 0 else 0)
                    if ch_sign == last_sign:
                        persistence += 1
                    else:
                        break

    # Direction: use delta_5d if available, else delta_3d; neutral if < 1 bps
    ref = d5 if d5 is not None else d3
    _NEUTRAL_BPS = 1.0  # < 1 bps absolute -> NEUTRAL
    if ref is None or abs(ref) < _NEUTRAL_BPS:
        direction = "NEUTRAL"
    elif ref > 0:
        direction = "BUY"
    else:
        direction = "SELL"

    return {
        "delta_3d": d3,
        "delta_5d": d5,
        "delta_10d": d10,
        "persistence": persistence,
        "direction": direction,
        "qnb_adjusted": qnb_adjusted,
    }


def compute_boost_multiplier(mw: dict) -> float:
    """Convert compute_multi_window result to a [1.0, 1.5] boost multiplier.

    Rules (D-144):
      +0.20  if persistence >= FOREIGN_FLOW_PERSISTENCE_MIN (3)
      +0.10  if delta_5d and delta_10d are both non-None, non-NaN, same sign
      cap    min(boost, 1.5)
    """
    from src.signals.thresholds import FOREIGN_FLOW_PERSISTENCE_MIN

    boost = 1.0
    if mw.get("persistence", 0) >= FOREIGN_FLOW_PERSISTENCE_MIN:
        boost += 0.20

    d5 = mw.get("delta_5d")
    d10 = mw.get("delta_10d")
    if (
        d5 is not None
        and d10 is not None
        and d5 == d5  # nan-safe (nan != nan)
        and d10 == d10
        and d5 * d10 > 0  # same sign = aligned direction
    ):
        boost += 0.10

    return min(boost, 1.5)

"""Signal contract + PM-1 guard (Section 10).

A prototype is a *zero-discretion* cross-sectional scorer: given the panel, the
eligible names and an as-of date, it returns one score per name. The engine
ranks names by that score; it NEVER interprets a score as a cash/exit decision.

PM-1 law: the engine never evaluates a cash-gate signal. Idle = fully-invested
equal-weight; a trigger re-tilts WITHIN the basket. A weight vector that pulls
the book to cash (partial investment) is a cash-gate -> guard-RAISE.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .contracts import Panel


@runtime_checkable
class Signal(Protocol):
    """Cross-sectional prototype interface.

    ``construction_window`` is the signal's look-back horizon; it equals the
    Mod-B embargo ``h`` (Section 3.4), so the engine can derive embargo from the
    signal rather than hard-coding it.
    """

    name: str
    construction_window: int

    def scores(self, panel: Panel, names: list[str], asof: pd.Timestamp) -> pd.Series:
        """Return a score per name (index = subset of ``names``). Higher = stronger long tilt."""
        ...


class PM1Violation(RuntimeError):
    """Raised when a prototype's weights imply a cash-gate (Section 10, PM-1)."""


def assert_pm1_compliant(
    weights: pd.Series,
    *,
    name: str = "signal",
    cash_tol: float = 1e-6,
    neg_tol: float = 1e-12,
) -> None:
    """Validate a target-weight vector against PM-1.

    - negative weight  -> not a long-only within-basket re-tilt -> raise.
    - sum ~ 0          -> "no opinion"; the engine fills a fully-invested EW basket
                          elsewhere, so this is allowed (not a cash-gate).
    - sum ~ 1          -> fully invested re-tilt -> OK.
    - 0 < sum < 1      -> explicit cash holding -> cash-gate -> raise.
    """
    w = weights.dropna()
    if (w < -neg_tol).any():
        raise PM1Violation(
            f"{name}: negative weights are not a long-only within-basket re-tilt (PM-1)."
        )
    total = float(w.sum())
    if total <= neg_tol:
        return  # idle / no-opinion -> engine substitutes fully-invested EW
    if abs(total - 1.0) > cash_tol:
        raise PM1Violation(
            f"{name}: target weights sum to {total:.6f} (holding {1.0 - total:.2%} cash). "
            "The engine never evaluates a cash-gate (PM-1); idle must be fully-invested EW."
        )

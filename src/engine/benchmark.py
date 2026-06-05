"""Real-return deflate + benchmark-floor (math-spec v1.1 Section 6).

Frozen rule (Section 6, recon Section 4):
- real-deflate: TUFE ALWAYS (CPI, TP.FG.J0, 2019+; finite throughout the panel).
- benchmark-floor: pre-2022-07 = TUFE-only; 2022-07+ = max(TUFE, TLREF).
- silent-NaN trap (d213 precedent): the clean TLREF series is NaN before
  2022-07. If the floor window would reach into that NaN region, DO NOT let the
  NaN silently collapse the ``max`` -- guard-RAISE (record the message) and fall
  back to TUFE-only for that window.

Both TUFE and TLREF are LEVEL/INDEX series (not rates), so the annualized
benchmark is a calendar-day CAGR between the window endpoints, looked up with
``Series.asof`` (robust to the snapshots keeping their own, possibly monthly,
index that is NOT reindexed onto the panel's trading days).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .contracts import Panel

# Julian year in calendar days -- the CAGR convention for the LEVEL series above.
# (config.TRADING_DAYS_YR is the SEPARATE 252-day axis used for return-series
# annualization; mixing the two would mis-scale the floor.)
_CALENDAR_DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class BenchmarkFloor:
    """Section 7 benchmark-floor sub-vector (bullet 4).

    ``tlref_ann`` is None when TLREF did not enter the floor -- either the window
    predates the clean series (by design, no guard) or the silent-NaN guard
    fired and we fell back to TUFE-only (``guard_raised`` True). ``beats_*`` is
    None when the comparison is undefined (a non-finite real return or floor).
    """

    real_active_ann: float
    benchmark_floor_ann: float
    beats_benchmark_floor: bool | None
    tufe_ann: float
    tlref_ann: float | None
    guard_raised: bool
    guard_messages: tuple[str, ...]


def _cagr(level: pd.Series, d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    """Calendar-day CAGR of a LEVEL series between its asof-levels at d0 and d1.

    ``asof`` returns the last non-NaN level at or before each endpoint, so a
    monthly CPI series -- or a snapshot index that does not land exactly on the
    trading-day endpoints -- still resolves. A pre-start (or all-NaN) endpoint
    yields NaN, which propagates to a NaN CAGR; the caller reads NaN as
    'benchmark unavailable on this window'.
    """
    if len(level) == 0:
        return float("nan")
    lvl0 = float(level.asof(d0))
    lvl1 = float(level.asof(d1))
    days = (pd.Timestamp(d1) - pd.Timestamp(d0)).days
    if not (np.isfinite(lvl0) and np.isfinite(lvl1)) or lvl0 <= 0.0 or days <= 0:
        return float("nan")
    return float((lvl1 / lvl0) ** (_CALENDAR_DAYS_PER_YEAR / days) - 1.0)


def benchmark_floor(
    nominal_active_ann: float,
    panel: Panel,
    d0: pd.Timestamp,
    d1: pd.Timestamp,
    *,
    tlref_from: str = config.BENCHMARK_TLREF_FROM,
) -> BenchmarkFloor:
    """Real (TUFE-deflated) active return vs the frozen benchmark floor (Section 6).

    ``nominal_active_ann`` is the engine's annualized nominal active return over
    the [d0, d1] window; ``d0``/``d1`` are that window's first/last return-dates.
    Never raises on a silent TLREF NaN: it records a guard message and falls back
    to TUFE-only (the d213-precedent silent-NaN trap).
    """
    messages: list[str] = []
    tlref_from_ts = pd.Timestamp(tlref_from)

    tufe_ann = _cagr(panel.tufe, d0, d1)
    if not np.isfinite(tufe_ann):
        messages.append(
            f"TUFE deflator unavailable on [{d0.date()}, {d1.date()}] "
            "-- real return and benchmark floor cannot be computed."
        )

    tlref_ann: float | None = None
    if d1 < tlref_from_ts:
        # whole window predates the clean TLREF series -> TUFE-only, BY DESIGN (no guard)
        pass
    elif d0 < tlref_from_ts:
        # window straddles the boundary: the pre-2022-07 TLREF is the silent NaN.
        # Do NOT fabricate a CAGR across it -- record the guard, fall back to TUFE.
        messages.append(
            f"TLREF floor window [{d0.date()}, {d1.date()}] straddles the "
            f"pre-{tlref_from} silent-NaN region (d213 precedent); "
            "floor falls back to TUFE-only for this window."
        )
    else:
        tl = _cagr(panel.tlref, d0, d1)
        if np.isfinite(tl):
            tlref_ann = tl
        else:
            messages.append(
                f"TLREF non-finite inside its eligible window "
                f"[{d0.date()}, {d1.date()}] (>= {tlref_from}); "
                "floor falls back to TUFE-only for this window."
            )

    floor_components: list[float] = [tufe_ann] if np.isfinite(tufe_ann) else []
    if tlref_ann is not None and np.isfinite(tlref_ann):
        floor_components.append(tlref_ann)
    benchmark_floor_ann = max(floor_components) if floor_components else float("nan")

    if np.isfinite(tufe_ann):
        real_active_ann = (1.0 + nominal_active_ann) / (1.0 + tufe_ann) - 1.0
    else:
        real_active_ann = float("nan")

    if np.isfinite(real_active_ann) and np.isfinite(benchmark_floor_ann):
        beats: bool | None = bool(real_active_ann > benchmark_floor_ann)
    else:
        beats = None

    return BenchmarkFloor(
        real_active_ann=real_active_ann,
        benchmark_floor_ann=benchmark_floor_ann,
        beats_benchmark_floor=beats,
        tufe_ann=tufe_ann,
        tlref_ann=tlref_ann,
        guard_raised=bool(messages),
        guard_messages=tuple(messages),
    )

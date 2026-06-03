"""RR-046 ASAMA-2a -- behavioral tests for the macro-event-dates builder (secondary).

Verifies the deterministic TUIK CPI release rule-proxy (3rd of M+1 rolled past weekends,
honestly flagged exact=False), the source-tagged exact PPK rows, and that the meta is
HONEST about the deferred 2019-2025 PPK history (no fabricated dates).
"""
from __future__ import annotations

import pandas as pd

from src.data.macro_event_snapshot_builder import (
    CPI_FIRST_REF_MONTH,
    CPI_LAST_REF_MONTH,
    CPI_RELEASE_DAY,
    _cpi_release_rows,
    _ppk_rows,
    build_macro_events,
)


def test_cpi_release_is_third_of_next_month_rolled_off_weekends():
    rows = _cpi_release_rows()
    n_ref = len(pd.period_range(CPI_FIRST_REF_MONTH, CPI_LAST_REF_MONTH, freq="M"))
    assert len(rows) == n_ref                       # exactly one release per reference month
    for r in rows:
        ref = pd.Period(r["reference_period"], freq="M")
        d = pd.Timestamp(r["event_date"])
        # release lands in the month AFTER the reference month (look-ahead intent)
        assert pd.Period(d, freq="M") == ref + 1
        assert d.weekday() < 5                       # rolled forward off Sat/Sun
        assert d.day >= CPI_RELEASE_DAY              # 3rd, or the next business day
        assert r["exact"] is False                   # honest: rule-proxy, not actual
        assert r["source"] == "tuik-rule-proxy"
        assert r["event_type"] == "cpi_release"


def test_ppk_rows_exact_and_source_tagged():
    rows = _ppk_rows()
    # Locally-known PPK meetings (the fallback yaml ships the recent ones). If present they
    # must be honestly tagged exact + sourced; absence is acceptable (deferred history).
    for r in rows:
        assert r["event_type"] == "ppk_decision"
        assert r["exact"] is True
        assert r["source"].startswith("local_macro_fallback")
        pd.Timestamp(r["event_date"])                # parseable ISO date


def test_build_macro_events_meta_is_honest_about_deferral():
    df, meta = build_macro_events()
    assert set(df.columns) == {"event_type", "event_date", "reference_period", "source", "exact"}
    assert meta["n_rows"] == len(df)
    # CPI tier is explicitly NOT exact; PPK history is explicitly DEFERRED, not hardcoded.
    assert meta["cpi_release"]["exact"] is False
    assert meta["ppk_decision"]["n"] == int((df["event_type"] == "ppk_decision").sum())
    deferred = meta["ppk_decision"]["deferred_note"].lower()
    assert "defer" in deferred and "not hardcoded" in deferred

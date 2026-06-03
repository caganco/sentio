"""RR-046 ASAMA-2a -- behavioral tests for the PEAD earnings-month + SUE builder.

These test the documented data-pipeline GUARANTEES on small synthetic inputs (no real
degoran load): look-ahead-safety (consume = announce+1), the regulated calendar bucket
mapping (incl. the Dec-31 fiscal-year-end), step-change announcement detection + dedup,
YTD->quarter de-cumulation with fiscal-year reset and gap-awareness, and the seasonal
(t-4q) SUE alignment on an absolute-quarter index.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.pead_snapshot_builder import (
    LOOK_AHEAD_LAG_MONTHS,
    SUE_SEASONAL_LAG_Q,
    _announce_to_fiscal,
    _compute_sue,
    _decumulate,
    _detect_announcements,
)


# --- calendar bucket / look-ahead ------------------------------------------------------

def test_announce_to_fiscal_buckets():
    # Feb-Apr -> prior fiscal year, annual (Q4), period_end Dec-31 (NOT Dec-30).
    for m in ("2023-02", "2023-03", "2023-04"):
        fy, q, pe = _announce_to_fiscal(pd.Period(m, freq="M"))
        assert (fy, q) == (2022, 4)
        assert pe == pd.Timestamp("2022-12-31")
    # May -> Q1 (Mar-31), Aug -> H1 (Jun-30), Nov -> 9M (Sep-30), all current year.
    assert _announce_to_fiscal(pd.Period("2023-05", freq="M"))[:2] == (2023, 1)
    assert _announce_to_fiscal(pd.Period("2023-08", freq="M"))[2] == pd.Timestamp("2023-06-30")
    assert _announce_to_fiscal(pd.Period("2023-11", freq="M"))[2] == pd.Timestamp("2023-09-30")
    # Jan -> late 9M of the PRIOR year (Q3, Sep-30 of prior year).
    fy, q, pe = _announce_to_fiscal(pd.Period("2023-01", freq="M"))
    assert (fy, q) == (2022, 3)
    assert pe == pd.Timestamp("2022-09-30")


def test_consume_is_announce_plus_one_lookahead_safe():
    # The builder sets consume_from_month = announce_month + LOOK_AHEAD_LAG_MONTHS.
    assert LOOK_AHEAD_LAG_MONTHS >= 1
    announce = pd.Period("2023-03", freq="M")
    consume = announce + LOOK_AHEAD_LAG_MONTHS
    assert consume == pd.Period("2023-04", freq="M")
    assert consume > announce  # never consume in (or before) the announce month


# --- announcement detection (step-change in carried-forward YTD) ------------------------

def _long(symbol: str, months: list[str], vals: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "month": pd.PeriodIndex(months, freq="M"),
        "symbol": symbol,
        "net_profit_h": vals,
    })


def test_detect_announcements_first_value_is_not_a_step():
    # Flat 100 for three months, then steps to 250: only the 250 transition is an event.
    npl = _long("AAA",
                ["2023-04", "2023-05", "2023-06", "2023-07", "2023-08"],
                [100.0, 100.0, 100.0, 250.0, 250.0])
    ev = _detect_announcements(npl)
    assert len(ev) == 1
    row = ev.iloc[0]
    assert str(row["announce_month"]) == "2023-07"
    assert row["net_profit_ytd"] == 250.0


def test_detect_announcements_dedup_same_fiscal_quarter_keeps_earliest():
    # Two steps both land in Feb & Mar -> both map to prior-FY annual (Q4); keep earliest.
    npl = _long("BBB",
                ["2023-01", "2023-02", "2023-03"],
                [10.0, 20.0, 30.0])
    ev = _detect_announcements(npl)
    annual = ev[(ev["fiscal_year"] == 2022) & (ev["quarter"] == 4)]
    assert len(annual) == 1
    assert str(annual.iloc[0]["announce_month"]) == "2023-02"  # earliest of the two


# --- de-cumulation (YTD -> single quarter, fiscal-year reset, gap-aware) -----------------

def _ev(symbol: str, rows: list[tuple[int, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["fiscal_year", "quarter", "net_profit_ytd"]).assign(symbol=symbol)


def test_decumulate_year_boundary_reset():
    # Y2021 YTD: Q1..Q4; Y2022 Q1 must RESET to raw YTD (not differenced across the boundary).
    ev = _ev("THYAO", [
        (2021, 1, -3127.0), (2021, 2, -1390.0), (2021, 3, 5847.0), (2021, 4, 8213.0),
        (2022, 1, 500.0),
    ])
    out = _decumulate(ev).set_index(["fiscal_year", "quarter"])
    assert out.loc[(2021, 1), "net_profit_q"] == -3127.0          # Q1 = raw YTD
    assert out.loc[(2021, 2), "net_profit_q"] == (-1390.0 - -3127.0)
    assert out.loc[(2021, 3), "net_profit_q"] == (5847.0 - -1390.0)
    assert out.loc[(2021, 4), "net_profit_q"] == (8213.0 - 5847.0)
    assert out.loc[(2022, 1), "net_profit_q"] == 500.0            # reset, NOT 500-8213
    assert bool(out.loc[(2022, 1), "decum_ok"])


def test_decumulate_gap_leaves_nan_never_fabricated():
    # Q1 missing -> Q2 has no contiguous predecessor: net_profit_q NaN, decum_ok False.
    ev = _ev("CCC", [(2023, 2, 200.0), (2023, 3, 350.0)])
    out = _decumulate(ev).set_index(["fiscal_year", "quarter"])
    assert np.isnan(out.loc[(2023, 2), "net_profit_q"])
    assert not bool(out.loc[(2023, 2), "decum_ok"])
    # Q3 has contiguous Q2 predecessor -> differenced normally.
    assert out.loc[(2023, 3), "net_profit_q"] == (350.0 - 200.0)
    assert bool(out.loc[(2023, 3), "decum_ok"])


# --- SUE (seasonal random walk on an absolute-quarter index) ----------------------------

def _ev_q(symbol: str, fy_q_npq: list[tuple[int, int, float]]) -> pd.DataFrame:
    return pd.DataFrame(fy_q_npq, columns=["fiscal_year", "quarter", "net_profit_q"]).assign(symbol=symbol)


def test_compute_sue_uses_same_quarter_prior_year():
    rng = np.random.default_rng(12345)
    rows = []
    for fy in range(2015, 2024):           # 9 years x 4q = 36 quarters (plenty for std window)
        for q in range(1, 5):
            rows.append((fy, q, float(rng.normal(1000, 300))))
    ev = _ev_q("DDD", rows)
    out = _compute_sue(_decumulate_passthrough(ev)).sort_values(["fiscal_year", "quarter"])
    out = out.set_index(["fiscal_year", "quarter"])
    npq = ev.set_index(["fiscal_year", "quarter"])["net_profit_q"]
    # UE_t = Q_t - Q_{t-4q}: same calendar quarter, prior year.
    assert SUE_SEASONAL_LAG_Q == 4
    got = out.loc[(2020, 3), "ue"]
    expected = npq.loc[(2020, 3)] - npq.loc[(2019, 3)]
    assert abs(got - expected) < 1e-6
    # First year has no t-4 predecessor -> UE NaN; later quarters become defined.
    assert np.isnan(out.loc[(2015, 1), "ue"])
    assert out["sue"].notna().sum() > 0


def test_compute_sue_gap_safe_alignment():
    # Drop 2019-Q3: the 2020-Q3 UE (which needs 2019-Q3) must be NaN, NOT silently shifted
    # to a different calendar quarter. Quarters whose t-4 IS present stay defined.
    rng = np.random.default_rng(7)
    rows = []
    for fy in range(2015, 2024):
        for q in range(1, 5):
            if (fy, q) == (2019, 3):
                continue                    # gap
            rows.append((fy, q, float(rng.normal(1000, 300))))
    ev = _ev_q("EEE", rows)
    out = _compute_sue(_decumulate_passthrough(ev)).set_index(["fiscal_year", "quarter"])
    assert np.isnan(out.loc[(2020, 3), "ue"])     # t-4 (2019-Q3) absent -> NaN, not mis-aligned
    assert out.loc[(2020, 2), "ue"] == out.loc[(2020, 2), "ue"]  # neighbor (t-4 present) defined


def _decumulate_passthrough(ev: pd.DataFrame) -> pd.DataFrame:
    """_compute_sue consumes the post-decumulation frame; here net_profit_q is already set."""
    out = ev.copy()
    out["decum_ok"] = True
    return out

"""Behavior tests for the D-203 FAZ-1 5-gate engine. Synthetic data, no network.

Verifies: monthly rebalance calendar, daily return clipping, delisted-inclusive
period returns, liquidity-tercile partition, fixed top-N EW selection, equal-weight
composite, the frozen 3-way verdict rule (GERCEK-EDGE / REJIM-TILT / SERAP), and the
Stage-0 pre-registration guard.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import d203_clean_universe_test as eng


# ---------------------------------------------------------------------------
# Calendar + return cleaning
# ---------------------------------------------------------------------------
def test_monthly_rebalance_dates_sorted_unique_last_of_month():
    idx = pd.bdate_range("2019-01-01", "2026-04-30")
    dates = eng.monthly_rebalance_dates(idx, "2019-07-01", "2026-04-30")
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    assert 75 <= len(dates) <= 90                     # ~82 month-ends
    # each is the last trading day of its (year, month)
    s = pd.Series(idx)
    for d in dates:
        same_month = s[(s.dt.year == d.year) & (s.dt.month == d.month)]
        assert d == same_month.max()


def test_clip_clean_returns_caps_at_ten_percent():
    close = pd.DataFrame({"A": [100.0, 130.0, 97.5, 102.375]},
                         index=pd.bdate_range("2020-01-01", periods=4))
    rets = eng.clip_clean_returns(close, cap=0.10)["A"].tolist()
    assert np.isnan(rets[0])
    assert rets[1] == pytest.approx(0.10)             # +30% clipped to +10%
    assert rets[2] == pytest.approx(-0.10)            # -25% clipped to -10%
    assert rets[3] == pytest.approx(0.05)             # +5% untouched


def test_period_return_matrix_delisted_inclusive():
    idx = pd.bdate_range("2020-01-01", periods=6)
    # B delists after day 3 (NaN afterwards) but still contributes a partial return
    close = pd.DataFrame({
        "A": [100, 101, 102, 103, 104, 105],
        "B": [100, 110, 121, np.nan, np.nan, np.nan],
    }, index=idx, dtype=float)
    daily = eng.clip_clean_returns(close, cap=0.50)
    rebal = [idx[0], idx[-1]]
    pmat = eng._period_return_matrix(daily, rebal)
    assert np.isfinite(pmat.iloc[0]["B"])             # partial return captured
    # EW_full includes B's partial leg -> differs from survivor-only (A alone)
    ewf = eng.ew_full_benchmark(pmat)[0]
    assert ewf != pytest.approx(pmat.iloc[0]["A"])


# ---------------------------------------------------------------------------
# Liquidity terciles
# ---------------------------------------------------------------------------
def test_liquidity_terciles_disjoint_and_cover_pool():
    idx = pd.bdate_range("2020-01-01", periods=80)
    syms = [f"S{i:02d}" for i in range(9)]
    value_tl = pd.DataFrame(
        {s: np.full(80, float(rank + 1) * 1000.0) for rank, s in enumerate(syms)}, index=idx)
    rebal = [idx[-1]]
    pools = eng.liquidity_tercile_pools(value_tl, rebal, trailing_days=20)[idx[-1]]
    liq, mid, ill = set(pools["liquid"]), set(pools["mid"]), set(pools["illiquid"])
    assert liq.isdisjoint(mid) and liq.isdisjoint(ill) and mid.isdisjoint(ill)
    assert liq | mid | ill == set(syms)               # union == eligible pool


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------
def test_select_top_n_fixed_basket_and_pool_respected():
    d = pd.Timestamp("2020-06-30")
    comp = pd.DataFrame({f"S{i}": [float(i)] for i in range(20)}, index=[d])
    top = eng.select_top_n(d, comp, n=15)
    assert len(top) == 15
    assert "S19" in top and "S0" not in top           # highest scores selected
    # pool smaller than N -> basket = min(N, pool)
    pool = ["S0", "S1", "S2"]
    small = eng.select_top_n(d, comp, n=15, pool=pool)
    assert set(small) == set(pool)


def test_composite_edge2_is_equal_weight_rank_average():
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2019-01-01", periods=400)
    syms = [f"S{i:02d}" for i in range(25)]
    close = pd.DataFrame(
        {s: 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.02, 400)) for s in syms}, index=idx)
    daily = eng.clip_clean_returns(close)
    rebal = [idx[-1]]
    comp = eng.composite_edge2_panel(close, daily, rebal)
    mom = eng._xs_rank(eng.momentum_panel(close, rebal))
    hi = eng._xs_rank(eng.hi52_panel(close, rebal))
    lv = eng._xs_rank(eng.lowvol_panel(daily, rebal))
    d = rebal[0]
    manual = pd.concat([mom.loc[d], hi.loc[d], lv.loc[d]], axis=1).mean(axis=1, skipna=False)
    both = comp.loc[d].dropna().index.intersection(manual.dropna().index)
    assert len(both) > 0
    for s in both:
        assert comp.loc[d, s] == pytest.approx(manual[s])   # unweighted average


# ---------------------------------------------------------------------------
# Verdict rule (frozen 3-way)
# ---------------------------------------------------------------------------
def _gate_block(gates, rel_mean=0.01, ls_mean=0.01, collapse=False, only_post=False):
    return {"_internal": {"gates": list(gates), "rel_ew_mean": rel_mean,
                          "ls_mean": ls_mean, "liquidity_collapse": collapse,
                          "only_post_positive": only_post}}


def test_verdict_gercek_edge_all_gates_both_regimes():
    v = eng.d203_verdict(_gate_block([True] * 5, only_post=False))
    assert v["verdict"] == "GERCEK-EDGE"


def test_verdict_rejim_tilt_when_only_post_regime_positive():
    # gate3 (regime) fails, others pass, edge exists only post-2022 -> REJIM-TILT
    v = eng.d203_verdict(_gate_block([True, True, False, True, True], only_post=True))
    assert v["verdict"] == "REJIM-TILT"


def test_verdict_serap_on_negative_long_short():
    v = eng.d203_verdict(_gate_block([True] * 5, ls_mean=-0.02))
    assert v["verdict"] == "SERAP"
    assert "long_short_negative" in v["reasons"]


def test_verdict_serap_on_nonpositive_relative():
    v = eng.d203_verdict(_gate_block([True] * 5, rel_mean=-0.001))
    assert v["verdict"] == "SERAP"


def test_verdict_serap_on_liquidity_collapse():
    v = eng.d203_verdict(_gate_block([True] * 5, collapse=True))
    assert v["verdict"] == "SERAP"


# ---------------------------------------------------------------------------
# Stage-0 pre-registration guard
# ---------------------------------------------------------------------------
def test_run_d203_requires_stage0(tmp_path: Path):
    missing = tmp_path / "STAGE0_missing.json"
    with pytest.raises(RuntimeError, match="Stage-0"):
        eng.run_d203(stage0_path=missing, require_stage0=True)


def test_regime_split_assigns_by_start_date():
    rebal = [pd.Timestamp("2021-06-30"), pd.Timestamp("2021-12-31"),
             pd.Timestamp("2022-06-30"), pd.Timestamp("2022-12-31")]
    series = [0.05, 0.04, -0.02, -0.03]               # positive pre-2022, negative post
    r = eng.regime_split(series, rebal, "2022-01-01")
    assert r["pre_mean"] > 0 and r["post_mean"] < 0
    assert r["both_positive"] is False
    assert r["only_post_positive"] is False

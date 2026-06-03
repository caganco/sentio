"""Behavior tests for the D-205 hi52 LIKIT-ONCE harness. Synthetic, no network.

Verifies: the liquid universe (ADV >= floor filter + HONEST narrow-pool size series),
the liquid-EW benchmark (only liquid names averaged), liquid-first selection (every pick
is in the liquid pool), the after-cost wiring (net < cost-free via the reused D-204 series),
the within-liquid sub-tier gate (both-half structure + lower-half SAMPLE SIZE reported per
the the maintainer note), the frozen 2-way verdict (TRADEABLE-EDGE / YINE-TRADEABLE-DEGIL, with the
OOS gap ALWAYS attached), and the Stage-0 pre-registration guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d203_clean_universe_test as eng
from src.screening import d205_config as cfg
from src.screening import d205_hi52_liquid as d205


# ---------------------------------------------------------------------------
# Liquid universe (D-205 core) -- ADV floor + honest size reporting
# ---------------------------------------------------------------------------
def _liq_panel():
    """3 names with constant, well-separated traded value: HI >> MID >> LO."""
    idx = pd.bdate_range("2020-01-01", periods=80)
    value_tl = pd.DataFrame(
        {"HI": np.full(80, 5e7), "MID": np.full(80, 1.2e7), "LO": np.full(80, 2e6)},
        index=idx)
    return value_tl, [idx[-1]]


def test_liquid_universe_filters_by_adv_floor():
    value_tl, rebal = _liq_panel()
    out = d205.liquid_universe_pools(value_tl, rebal, adv_min=1.0e7, trailing=63)
    d = rebal[0]
    assert out["pools"][d] == ["HI", "MID"]              # LO (2e6) excluded
    assert "LO" not in out["adv"][d]
    assert out["adv"][d]["HI"] == pytest.approx(5e7)
    assert out["sizes"] == [2]


def test_liquid_universe_reports_narrow_pool_honestly():
    """A floor above all names -> empty universe; reported as size 0, not forced."""
    value_tl, rebal = _liq_panel()
    out = d205.liquid_universe_pools(value_tl, rebal, adv_min=1.0e9, trailing=63)
    assert out["pools"][rebal[0]] == []
    assert out["sizes"] == [0]


# ---------------------------------------------------------------------------
# Liquid-EW benchmark -- only liquid names averaged (differs from full universe)
# ---------------------------------------------------------------------------
def test_ew_liquid_benchmark_averages_only_liquid_names():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
    pmat = pd.DataFrame({"HI": [0.10], "MID": [0.20], "LO": [-0.90]},
                        index=pd.DatetimeIndex(rebal[:-1]))
    pools = {rebal[0]: ["HI", "MID"]}                    # LO is illiquid -> excluded
    ew = d205.ew_liquid_benchmark(pmat, pools, rebal)
    assert ew[0] == pytest.approx(0.15)                  # mean(0.10, 0.20), LO ignored


# ---------------------------------------------------------------------------
# Liquid-first selection -- every pick lives in the liquid pool
# ---------------------------------------------------------------------------
def test_liquid_first_selection_picks_only_liquid_names():
    d = pd.Timestamp("2020-01-31")
    comp = pd.DataFrame({"HI": [0.9], "MID": [0.8], "LO": [0.99]},
                        index=pd.DatetimeIndex([d]))     # LO ranks highest but is illiquid
    pool = ["HI", "MID"]
    picks = eng.select_top_n(d, comp, 2, pool=pool)
    assert set(picks) <= set(pool)
    assert "LO" not in picks


# ---------------------------------------------------------------------------
# After-cost wiring -- net < cost-free via the reused D-204 series
# ---------------------------------------------------------------------------
def test_after_cost_net_below_costfree():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"),
             pd.Timestamp("2020-03-31")]
    pmat = pd.DataFrame({"HI": [0.05, 0.04], "MID": [0.03, 0.02]},
                        index=pd.DatetimeIndex(rebal[:-1]))
    baskets = [["HI", "MID"], ["HI", "MID"]]
    cost_map = {rebal[0]: {"HI": 0.01, "MID": 0.02}, rebal[1]: {"HI": 0.01, "MID": 0.02}}
    free = d205.d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=None)
    costed = d205.d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_map)
    assert costed["net"][0] < free["net"][0]


# ---------------------------------------------------------------------------
# gate-4 -- within-liquid sub-tier consistency + lower-half SAMPLE SIZE (the maintainer note)
# ---------------------------------------------------------------------------
def test_subtier_consistency_structure_and_reports_lower_half_size():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29")]
    syms = [f"S{i}" for i in range(6)]
    comp = pd.DataFrame({s: [float(i)] for i, s in enumerate(syms)},
                        index=pd.DatetimeIndex(rebal[:-1]))
    pmat = pd.DataFrame({s: [0.01 * (i + 1)] for i, s in enumerate(syms)},
                        index=pd.DatetimeIndex(rebal[:-1]))
    adv = {s: float(6 - i) * 1e7 for i, s in enumerate(syms)}   # S0 most liquid .. S5 least
    liq = {"pools": {rebal[0]: syms}, "adv": {rebal[0]: adv}}
    cost_roll = {rebal[0]: {s: 0.001 for s in syms}}
    out = d205.subtier_consistency(comp, pmat, rebal, liq, cost_roll, split=0.5, top_n=2)
    for h in ("upper", "lower"):
        assert "rel_aftercost_mean" in out[h]
        assert "basket_size_min" in out[h] and "basket_size_median" in out[h]
        assert isinstance(out[h]["positive"], bool)
    assert isinstance(out["pass"], bool)
    assert out["lower"]["basket_size_min"] >= 0          # lower-half size is reported


# ---------------------------------------------------------------------------
# Verdict (frozen 2-way + OOS gap always)
# ---------------------------------------------------------------------------
def _all_pass_kwargs(**over):
    base = dict(
        rel_aftercost_mean=0.01, nw_t=3.0, both_regimes_positive=True,
        gate1_null=True, gate4_subtier=True,
        real_aftercost_mean=cfg.D205_DEPLOY_MIN_LIQUID_NET * 2,
        breakeven_bps=300.0, realistic_cost_bps=50.0, pool_size_min=40)
    base.update(over)
    return base


def test_verdict_tradeable_edge_when_all_conditions_met():
    v = d205.d205_verdict(**_all_pass_kwargs())
    assert v["verdict"] == "TRADEABLE-EDGE"
    assert all(v["gates"].values())
    assert v["oos_gap"]


def test_verdict_closes_when_after_cost_nonpositive():
    v = d205.d205_verdict(**_all_pass_kwargs(rel_aftercost_mean=-0.001))
    assert v["verdict"] == "YINE-TRADEABLE-DEGIL"
    assert v["gates"]["gate5_after_cost"] is False
    assert v["oos_gap"]


def test_verdict_closes_when_universe_too_narrow():
    v = d205.d205_verdict(**_all_pass_kwargs(pool_size_min=10))   # < top-15
    assert v["verdict"] == "YINE-TRADEABLE-DEGIL"
    assert any("cok-dar" in r for r in v["reasons"])


def test_verdict_closes_when_breakeven_near_cost():
    v = d205.d205_verdict(**_all_pass_kwargs(breakeven_bps=80.0, realistic_cost_bps=50.0))
    assert v["verdict"] == "YINE-TRADEABLE-DEGIL"   # 80 < 2x50


def test_verdict_closes_below_deposit_hurdle():
    v = d205.d205_verdict(**_all_pass_kwargs(
        real_aftercost_mean=cfg.D205_DEPLOY_MIN_LIQUID_NET / 2))
    assert v["verdict"] == "YINE-TRADEABLE-DEGIL"
    assert v["oos_gap"]


# ---------------------------------------------------------------------------
# Stage-0 guard
# ---------------------------------------------------------------------------
def test_run_d205_refuses_without_stage0(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        d205.run_d205(stage0_path=missing, require_stage0=True)

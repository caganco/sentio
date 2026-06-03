"""Behavior tests for the D-204 hi52 stress-test harness. Synthetic, no network.

Verifies: multi-cadence calendar, per-stock cost panel (liquid < illiquid + roll-zero
accounting), per-stock net series (differs from flat, first-entry full round-trip),
breakeven bps (monotone, edge>0 -> positive crossing), effective flat bps, holding-
period stats, factor overlap (identical panels -> 1.0), walk-forward split-by-start,
the TLREF deposit-hurdle derivation, the liquidity-paradox decomposition, the frozen
3-way verdict (with the OOS gap ALWAYS attached), and the Stage-0 guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d203_clean_universe_test as eng
from src.screening import d204_config as cfg
from src.screening import d204_hi52_stress as d204


# ---------------------------------------------------------------------------
# Cadence (STRES-2)
# ---------------------------------------------------------------------------
def test_multi_cadence_sorted_unique_and_halves_at_two_months():
    idx = pd.bdate_range("2019-07-01", "2026-04-30")
    m1 = d204.multi_cadence_rebalance_dates(idx, "2019-07-01", "2026-04-30", 1)
    m2 = d204.multi_cadence_rebalance_dates(idx, "2019-07-01", "2026-04-30", 2)
    m3 = d204.multi_cadence_rebalance_dates(idx, "2019-07-01", "2026-04-30", 3)
    for m in (m1, m2, m3):
        assert m == sorted(m)
        assert len(m) == len(set(m))
    assert len(m2) == pytest.approx(len(m1) / 2, abs=1)
    assert len(m3) == pytest.approx(len(m1) / 3, abs=1)
    assert set(m2).issubset(set(m1))                   # subsample of the monthly calendar


# ---------------------------------------------------------------------------
# Per-stock cost panel (STRES-1 + EKLEME-A)
# ---------------------------------------------------------------------------
def _smooth_panel():
    idx = pd.bdate_range("2020-01-01", periods=90)
    liquid = pd.Series(100.0 * (1.001 ** np.arange(90)), index=idx)    # smooth -> roll 0
    illiquid = pd.Series(20.0 * (1.001 ** np.arange(90)), index=idx)
    close = pd.DataFrame({"LIQ": liquid, "ILL": illiquid})
    value_tl = pd.DataFrame({"LIQ": np.full(90, 1e10), "ILL": np.full(90, 1e7)}, index=idx)
    return close, value_tl, [idx[-1]]


def test_per_stock_cost_liquid_cheaper_than_illiquid():
    close, value_tl, rebal = _smooth_panel()
    out = d204.per_stock_cost_panel(close, value_tl, rebal)
    d = rebal[0]
    assert out["cost_roll"][d]["LIQ"] < out["cost_roll"][d]["ILL"]
    assert out["summary"]["n_evaluated"] == 2


def test_per_stock_cost_roll_zero_accounting_present():
    close, value_tl, rebal = _smooth_panel()
    out = d204.per_stock_cost_panel(close, value_tl, rebal)
    s = out["summary"]
    # No quoted panel + 90 rows < 252-day fallback Roll window -> Roll NaN -> tier-floor
    # engaged for both names (D-207: n_roll_zero now counts spread_source=="tier" cells).
    assert s["n_roll_zero"] == 2
    assert s["roll_zero_frac"] == pytest.approx(1.0)
    assert s["spread_source_counts"] == {"quoted": 0, "roll": 0, "tier": 2}
    assert s["spread_source_frac"]["tier"] == pytest.approx(1.0)
    assert s["mean_round_trip_tier"] is not None


# ---------------------------------------------------------------------------
# Per-stock net series
# ---------------------------------------------------------------------------
def _pmat_baskets():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"), pd.Timestamp("2020-03-31")]
    pmat = pd.DataFrame({"A": [0.05, 0.04], "B": [0.03, 0.02], "C": [0.01, 0.06]},
                        index=pd.DatetimeIndex(rebal[:-1]))
    baskets = [["A", "B"], ["A", "C"]]
    return pmat, baskets, rebal


def test_net_series_per_stock_differs_from_costfree_and_first_entry_full_round_trip():
    pmat, baskets, rebal = _pmat_baskets()
    cost_map = {rebal[0]: {"A": 0.01, "B": 0.02}, rebal[1]: {"A": 0.01, "C": 0.03}}
    free = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=None)
    costed = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_map)
    assert free["cost"][0] == 0.0
    # first entry (no prior basket) -> FULL round trip = mean of basket round-trips
    assert costed["cost"][0] == pytest.approx((0.01 + 0.02) / 2)
    assert costed["net"][0] < free["net"][0]


# ---------------------------------------------------------------------------
# Breakeven (STRES-1 main verdict)
# ---------------------------------------------------------------------------
def test_breakeven_monotone_and_positive_crossing():
    n = 12
    long_net = [0.01] * n          # +1%/period edge over a flat benchmark
    bench = [0.0] * n
    turnover = [1.0] * n           # full turnover each period
    out = d204.breakeven_cost_bps(long_net, bench, turnover)
    means = [g["rel_mean"] for g in out["grid"]]
    assert all(means[i] >= means[i + 1] for i in range(len(means) - 1))   # non-increasing
    # edge 1% at turnover 1.0 -> zeroed at 100 bps round trip
    assert out["breakeven_bps"] == pytest.approx(100.0, abs=1.0)


def test_breakeven_zero_when_edge_already_negative():
    out = d204.breakeven_cost_bps([-0.01] * 6, [0.0] * 6, [1.0] * 6)
    assert out["breakeven_bps"] == pytest.approx(0.0)


def test_effective_flat_bps_ratio():
    assert d204.effective_flat_bps([0.001, 0.002], [1.0, 0.5]) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Holding period (STRES-2)
# ---------------------------------------------------------------------------
def test_holding_period_stats_runs_and_turnover():
    rebal = list(pd.date_range("2020-01-31", periods=4, freq="ME"))
    baskets = [["A", "B"], ["A", "C"], ["A", "C"]]
    out = d204.holding_period_stats(baskets, rebal, cadence_months=1)
    assert out["n_holds"] == 3                          # A(run 3), B(run 1), C(run 2)
    assert out["avg_holding_periods"] == pytest.approx(2.0)
    assert out["avg_holding_months"] == pytest.approx(2.0)
    assert out["mean_turnover"] == pytest.approx(0.5)   # turns = [1.0, 0.5, 0.0]


# ---------------------------------------------------------------------------
# Mechanism (STRES-4): factor overlap
# ---------------------------------------------------------------------------
def test_factor_overlap_identical_panels_is_one():
    dates = pd.DatetimeIndex(pd.date_range("2020-01-31", periods=3, freq="ME"))
    syms = [f"S{i}" for i in range(6)]
    rank = pd.DataFrame({s: [float(i)] * 3 for i, s in enumerate(syms)}, index=dates)
    pmat = pd.DataFrame({s: [0.01 * i, 0.02 * i] for i, s in enumerate(syms)},
                        index=dates[:-1])
    rebal = list(dates)
    out = d204.factor_overlap(rank, rank, pmat, rebal, top_n=3)
    assert out["mean_basket_overlap"] == pytest.approx(1.0)
    assert out["long_short_correlation"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# OOS / walk-forward (STRES-3)
# ---------------------------------------------------------------------------
def test_walk_forward_splits_by_start_date():
    rebal = [pd.Timestamp("2021-06-30"), pd.Timestamp("2022-06-30"),
             pd.Timestamp("2023-06-30"), pd.Timestamp("2024-06-30")]
    rel = [0.01, 0.02, 0.03, 0.04]
    out = d204.walk_forward(rel, rebal, "2023-01-01", ("2024-01-01", "2024-12-31"))
    assert out["train_n"] == 2 and out["holdout_n"] == 2
    assert out["train_mean"] == pytest.approx(0.015)
    assert out["holdout_mean"] == pytest.approx(0.035)
    assert out["disinflation_mean"] == pytest.approx(0.04)


# ---------------------------------------------------------------------------
# TLREF deposit hurdle (EKLEME-B)
# ---------------------------------------------------------------------------
def test_deploy_threshold_from_tlref_real_carry():
    rebal = list(pd.date_range("2022-07-31", periods=5, freq="ME"))
    idx = pd.date_range("2022-07-01", periods=200, freq="D")
    # TLREF return-index +1%/period; CPI +0.5%/period -> positive real carry.
    tlref = pd.Series(1.0 * (1.01 ** (np.arange(200) / 30.0)), index=idx)
    cpi = pd.Series(100.0 * (1.005 ** (np.arange(200) / 30.0)), index=idx)
    out = d204.deploy_threshold_from_tlref(tlref, cpi, rebal)
    assert out["n_periods"] == 4
    assert out["mean_monthly_real_carry"] > 0
    assert out["coverage_start"] == str(rebal[0].date())


def test_deploy_threshold_none_when_data_missing():
    out = d204.deploy_threshold_from_tlref(None, None, [])
    assert out["mean_monthly_real_carry"] is None
    assert out["n_periods"] == 0


# ---------------------------------------------------------------------------
# Liquidity paradox (EKLEME-3 / H1)
# ---------------------------------------------------------------------------
def test_liquidity_paradox_decompose_structure_and_flags():
    idx = pd.bdate_range("2020-01-01", periods=90)
    rng = np.random.default_rng(1)
    syms = [f"S{i:02d}" for i in range(9)]
    close = pd.DataFrame(
        {s: 100.0 * np.cumprod(1 + rng.normal(0.001, 0.01, 90)) for s in syms}, index=idx)
    value_tl = pd.DataFrame(
        {s: np.full(90, float(r + 1) * 1e8) for r, s in enumerate(syms)}, index=idx)
    rebal = [idx[40], idx[-1]]
    daily = eng.clip_clean_returns(close)
    pmat = eng._period_return_matrix(daily, rebal)
    ew_full = eng.ew_full_benchmark(pmat)
    liq = eng.liquidity_tercile_pools(value_tl, rebal, trailing_days=20)
    comp = eng._xs_rank(eng.hi52_panel(close, rebal))
    cost = d204.per_stock_cost_panel(close, value_tl, rebal)
    cpi = pd.Series(100.0 * (1.002 ** np.arange(90)), index=idx)
    out = d204.liquidity_paradox_decompose(
        comp, pmat, ew_full, rebal, liq, cost["cost_roll"], cpi, top_n=2)
    for tercile in ("liquid", "mid", "illiquid"):
        assert "rel_costfree_mean" in out[tercile]
        assert "rel_aftercost_mean" in out[tercile]
    assert isinstance(out["illiquid_still_dominates_after_cost"], bool)
    assert isinstance(out["liquid_positive_after_cost"], bool)


# ---------------------------------------------------------------------------
# Verdict (frozen 3-way + OOS gap always)
# ---------------------------------------------------------------------------
def test_verdict_deploy_aday():
    v = d204.d204_verdict(liquid_aftercost_real_mean=0.01, breakeven_bps=300.0,
                          realistic_cost_bps=50.0, illiquid_dominates_after_cost=False,
                          liquid_positive_after_cost=True)
    assert v["verdict"] == "DEPLOY-ADAY"
    assert v["oos_gap"]


def test_verdict_kirilgan_when_breakeven_near_cost():
    v = d204.d204_verdict(liquid_aftercost_real_mean=0.01, breakeven_bps=80.0,
                          realistic_cost_bps=50.0, illiquid_dominates_after_cost=False,
                          liquid_positive_after_cost=True)
    assert v["verdict"] == "KIRILGAN"
    assert v["oos_gap"]


def test_verdict_kirilgan_when_illiquid_concentrated():
    v = d204.d204_verdict(liquid_aftercost_real_mean=0.01, breakeven_bps=300.0,
                          realistic_cost_bps=50.0, illiquid_dominates_after_cost=True,
                          liquid_positive_after_cost=True)
    assert v["verdict"] == "KIRILGAN"


def test_verdict_tradeable_degil_when_liquid_nonpositive():
    v = d204.d204_verdict(liquid_aftercost_real_mean=-0.001, breakeven_bps=300.0,
                          realistic_cost_bps=50.0, illiquid_dominates_after_cost=False,
                          liquid_positive_after_cost=False)
    assert v["verdict"] == "GERCEK-ama-tradeable-DEGIL"
    assert v["oos_gap"]


def test_verdict_below_deposit_hurdle_is_kirilgan():
    # liquid positive but below the TLREF deposit hurdle -> not deployable, fragile.
    v = d204.d204_verdict(liquid_aftercost_real_mean=cfg.D204_DEPLOY_MIN_LIQUID_NET / 2,
                          breakeven_bps=300.0, realistic_cost_bps=50.0,
                          illiquid_dominates_after_cost=False, liquid_positive_after_cost=True)
    assert v["verdict"] == "KIRILGAN"


# ---------------------------------------------------------------------------
# Stage-0 guard
# ---------------------------------------------------------------------------
def test_run_d204_refuses_without_stage0(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        d204.run_d204(stage0_path=missing, require_stage0=True)

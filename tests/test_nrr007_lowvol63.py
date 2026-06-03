"""Behavior tests for the NRR-007 lowvol63 ISOLATED harness. Synthetic, no network.

Verifies: the run_gates_on_score replica reproduces eng.run_gates EXACTLY on the hi52
candidate (MATCH=True fidelity -- proves zero-touch to the committed engine is faithful),
the injected lowvol63 score path produces the full 5-gate dict while the committed
score_panel_for stays untouched (no "lowvol63" dispatch key), the lowvol signal direction
(low-vol name -> high score), the realistic after-cost wiring (net < cost-free via the reused
D-204 series), the turnover/holding stats, the combined verdict (ELENDI / GERCEK-EDGE /
GERCEK-ama-tradeable-DEGIL with the OOS gap attached on every non-SERAP branch), and the
Stage-0 pre-registration guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d203_clean_universe_test as eng
from src.screening import nrr007_config as cfg
from src.screening import nrr007_lowvol63 as nrr007


# ---------------------------------------------------------------------------
# Synthetic D-202-like panel -> eng._prepare_window-compatible data dict
# ---------------------------------------------------------------------------
def _synth_data(n_days: int = 340, n_syms: int = 40, seed: int = 7) -> dict:
    """Geometric random-walk closes + positive value_tl + all-bist100 + rising CPI. Enough
    days (>252) for the hi52 lookback so the MATCH test exercises a full window."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=n_days)
    syms = [f"S{i:02d}" for i in range(n_syms)]
    steps = rng.normal(0.0005, 0.02, size=(n_days, n_syms))
    close = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=idx, columns=syms)
    value_tl = pd.DataFrame(rng.uniform(1e6, 5e7, size=(n_days, n_syms)), index=idx, columns=syms)
    bist100 = pd.DataFrame(1, index=idx, columns=syms)
    cpi = pd.Series(np.linspace(100.0, 200.0, n_days), index=idx)
    return {"close": close, "value_tl": value_tl, "bist100": bist100,
            "funds": None, "cpi": cpi}


# ---------------------------------------------------------------------------
# MATCH=True fidelity -- replica reproduces eng.run_gates EXACTLY on hi52
# ---------------------------------------------------------------------------
def test_run_gates_on_score_matches_engine_run_gates_on_hi52():
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    rebal = pdata["rebal"]
    comp_hi52 = eng.score_panel_for("hi52", pdata, rebal)

    replica = nrr007.run_gates_on_score(comp_hi52, pdata, rebal, candidate="hi52")
    canonical = eng.run_gates("hi52", pdata, rebal)
    assert replica == canonical            # byte-for-byte identical -> faithful replica


# ---------------------------------------------------------------------------
# Injected lowvol63 score path + committed engine stays untouched
# ---------------------------------------------------------------------------
def test_injected_lowvol63_score_produces_full_gate_block():
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    rebal = pdata["rebal"]
    comp = eng._xs_rank(eng.lowvol_panel(pdata["daily"], rebal))

    block = nrr007.run_gates_on_score(comp, pdata, rebal)
    for k in ("gate1_selection_null", "gate2_newey_west", "gate3_cross_regime",
              "gate4_liquidity", "gate5_after_cost", "_internal"):
        assert k in block
    assert len(block["_internal"]["gates"]) == 5
    assert block["candidate"] == cfg.NRR007_CANDIDATE


def test_committed_engine_dispatch_untouched():
    """NRR-007 must NOT have added a 'lowvol63' branch to the committed score_panel_for."""
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    with pytest.raises(ValueError, match="unknown candidate"):
        eng.score_panel_for("lowvol63", pdata, pdata["rebal"])


# ---------------------------------------------------------------------------
# lowvol signal direction -- low-vol name scores higher
# ---------------------------------------------------------------------------
def test_lowvol_signal_low_vol_scores_higher():
    idx = pd.bdate_range("2020-01-01", periods=80)
    flat = np.full(80, 0.0002)                         # near-constant -> tiny std
    vol = np.tile([0.05, -0.05], 40)                   # large alternating -> big std
    daily = pd.DataFrame({"FLAT": flat, "VOL": vol}, index=idx)
    rebal = [idx[-1]]
    comp = eng._xs_rank(eng.lowvol_panel(daily, rebal))
    d = rebal[0]
    assert comp.loc[d]["FLAT"] > comp.loc[d]["VOL"]    # lower vol -> higher score


# ---------------------------------------------------------------------------
# Realistic after-cost wiring -- net < cost-free via the reused D-204 series
# ---------------------------------------------------------------------------
def test_after_cost_net_below_costfree():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"),
             pd.Timestamp("2020-03-31")]
    pmat = pd.DataFrame({"HI": [0.05, 0.04], "MID": [0.03, 0.02]},
                        index=pd.DatetimeIndex(rebal[:-1]))
    baskets = [["HI", "MID"], ["HI", "MID"]]
    cost_map = {rebal[0]: {"HI": 0.01, "MID": 0.02}, rebal[1]: {"HI": 0.01, "MID": 0.02}}
    free = nrr007.d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=None)
    costed = nrr007.d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_map)
    assert costed["net"][0] < free["net"][0]
    ew_full = [0.02, 0.01]
    rel = eng._relative(costed["net"], ew_full)
    assert any(np.isfinite(v) for v in rel)


# ---------------------------------------------------------------------------
# Turnover / holding -- lowvol baskets feed holding_period_stats
# ---------------------------------------------------------------------------
def test_holding_period_stats_runs_on_baskets():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"),
             pd.Timestamp("2020-03-31")]
    baskets = [["A", "B"], ["A", "B"]]                 # fully persistent -> low turnover
    hold = nrr007.d204.holding_period_stats(baskets, rebal, cfg.NRR007_PRIMARY_CADENCE)
    assert hold["avg_holding_periods"] is not None
    assert hold["mean_turnover"] is not None


# ---------------------------------------------------------------------------
# Combined verdict (cost-free 3-way + realistic addendum)
# ---------------------------------------------------------------------------
def test_verdict_eliminated_when_cost_free_serap():
    v = nrr007.nrr007_verdict(
        cost_free_verdict={"verdict": "SERAP", "reasons": ["ew_full_relative<=0"]},
        g5_realistic=False, breakeven_bps=None, realistic_cost_bps=50.0,
        rel_aftercost_mean=-0.001)
    assert v["headline"] == "ELENDI"
    assert v["oos_gap"] is None                        # signal not even real cost-free


def test_verdict_real_edge_when_costfree_edge_and_realistic_survives():
    v = nrr007.nrr007_verdict(
        cost_free_verdict={"verdict": "GERCEK-EDGE", "reasons": ["all_5_gates_pass"]},
        g5_realistic=True, breakeven_bps=300.0, realistic_cost_bps=50.0,
        rel_aftercost_mean=0.01)
    assert v["headline"] == "GERCEK-EDGE"
    assert v["oos_gap"]                                # OOS gap attached on non-SERAP


def test_verdict_tradeable_degil_when_realistic_after_cost_nonpositive():
    v = nrr007.nrr007_verdict(
        cost_free_verdict={"verdict": "GERCEK-EDGE", "reasons": ["all_5_gates_pass"]},
        g5_realistic=False, breakeven_bps=300.0, realistic_cost_bps=50.0,
        rel_aftercost_mean=-0.002)
    assert v["headline"] == "GERCEK-ama-tradeable-DEGIL"
    assert v["oos_gap"]


def test_verdict_tradeable_degil_when_breakeven_near_cost():
    v = nrr007.nrr007_verdict(
        cost_free_verdict={"verdict": "REJIM-TILT", "reasons": ["only_post_2022"]},
        g5_realistic=True, breakeven_bps=80.0, realistic_cost_bps=50.0,   # 80 < 2x50
        rel_aftercost_mean=0.003)
    assert v["headline"] == "GERCEK-ama-tradeable-DEGIL"
    assert v["oos_gap"]


# ---------------------------------------------------------------------------
# Stage-0 guard
# ---------------------------------------------------------------------------
def test_run_nrr007_refuses_without_stage0(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        nrr007.run_nrr007(stage0_path=missing, require_stage0=True)

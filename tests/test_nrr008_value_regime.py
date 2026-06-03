"""Behavior tests for the NRR-008 value-REJIM-KOLU harness. Synthetic, no network.

Verifies: the run_gates_on_score replica reproduces eng.run_gates EXACTLY on the value
candidate when regime_mask=None (MATCH=True fidelity -- proves the regime overlay is a faithful
zero-touch extension of the committed engine); an all-ON mask equals no mask (gating is a no-op
when every month is ON) and an all-OFF mask zeroes every EW_FULL-relative series (the frozen
OFF=EW-neutral semantics); the look-ahead-safe regime rule (undefined warmup -> ON; YoY rising
-> ON; YoY falling -> OFF); the committed score_panel_for stays untouched (no "value-regime"
dispatch key -- the value signal is the D-203 "value" key); the tilt-only realistic cost
(OFF->OFF zero cost, entry cost > 0, after-cost <= cost-free); the combined verdict branches;
and the Stage-0 pre-registration guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d203_clean_universe_test as eng
from src.screening import nrr008_config as cfg
from src.screening import nrr008_value_regime as nrr008


# ---------------------------------------------------------------------------
# Synthetic D-202-like panel (+ fundamentals for the value factor)
# ---------------------------------------------------------------------------
def _synth_data(n_days: int = 340, n_syms: int = 40, seed: int = 7) -> dict:
    """Geometric random-walk closes + positive value_tl + all-bist100 + rising CPI + monthly
    fundamentals (bm/ey/mktval) so score_panel_for('value',..) returns a full panel."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-01", periods=n_days)
    syms = [f"S{i:02d}" for i in range(n_syms)]
    steps = rng.normal(0.0005, 0.02, size=(n_days, n_syms))
    close = pd.DataFrame(100.0 * np.exp(np.cumsum(steps, axis=0)), index=idx, columns=syms)
    value_tl = pd.DataFrame(rng.uniform(1e6, 5e7, size=(n_days, n_syms)), index=idx, columns=syms)
    bist100 = pd.DataFrame(1, index=idx, columns=syms)
    cpi = pd.Series(np.linspace(100.0, 200.0, n_days), index=idx)

    months = pd.period_range(idx[0].to_period("M") - 1, idx[-1].to_period("M"), freq="M")
    rows = []
    for m in months:
        for s in syms:
            rows.append({"month": m.to_timestamp(), "symbol": s,
                         "bm": float(rng.uniform(0.2, 3.0)),
                         "ey": float(rng.uniform(-0.1, 0.3)),
                         "mktval": float(rng.uniform(1e7, 1e10))})
    funds = pd.DataFrame(rows)
    return {"close": close, "value_tl": value_tl, "bist100": bist100,
            "funds": funds, "cpi": cpi}


def _value_comp(pdata, rebal):
    return eng.score_panel_for("value", pdata, rebal, cfg.NRR008_VALUE_PRIMARY)


# ---------------------------------------------------------------------------
# MATCH=True fidelity -- replica (regime_mask=None) reproduces eng.run_gates on value
# ---------------------------------------------------------------------------
def test_run_gates_on_score_matches_engine_run_gates_on_value():
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    rebal = pdata["rebal"]
    comp = _value_comp(pdata, rebal)

    replica = nrr008.run_gates_on_score(comp, pdata, rebal, candidate="value", regime_mask=None)
    canonical = eng.run_gates("value", pdata, rebal)
    assert replica == canonical            # byte-for-byte identical -> faithful replica


def test_all_on_mask_equals_no_mask():
    """A mask that is ON every period must be a no-op (gating only acts on OFF months)."""
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    rebal = pdata["rebal"]
    comp = _value_comp(pdata, rebal)

    no_mask = nrr008.run_gates_on_score(comp, pdata, rebal, candidate="value", regime_mask=None)
    all_on = nrr008.run_gates_on_score(comp, pdata, rebal, candidate="value",
                                       regime_mask=[True] * (len(rebal) - 1))
    assert all_on == no_mask


def test_all_off_mask_zeroes_every_relative_series():
    """OFF months hold EW_FULL -> every EW_FULL-relative series is exactly 0 (frozen)."""
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    rebal = pdata["rebal"]
    comp = _value_comp(pdata, rebal)

    block = nrr008.run_gates_on_score(comp, pdata, rebal, candidate="value",
                                      regime_mask=[False] * (len(rebal) - 1))
    assert block["ew_full_relative"]["mean"] == 0.0
    assert block["long_short"]["mean"] == 0.0
    assert block["gate4_liquidity"]["liquid_rel_mean"] == 0.0
    assert block["gate2_newey_west"]["pass"] is False          # zero series -> no significance


# ---------------------------------------------------------------------------
# Look-ahead-safe regime rule
# ---------------------------------------------------------------------------
def _monthly_cpi(coef_lin: float, coef_quad: float, start="2018-01", end="2022-12") -> pd.Series:
    months = pd.period_range(start, end, freq="M")
    t = np.arange(len(months), dtype=float)
    vals = np.exp(coef_lin * t + coef_quad * t * t)        # log-YoY slope ~ 24*coef_quad
    return pd.Series(vals, index=months.to_timestamp("M"))


def test_regime_warmup_stays_on_when_history_insufficient():
    cpi = _monthly_cpi(0.02, 0.0, start="2019-01", end="2019-12")
    rebal = [pd.Timestamp("2019-08-31"), pd.Timestamp("2019-09-30")]
    reg = nrr008.regime_mask_for(rebal, cpi)
    assert reg["mask"][0] is True                          # undefined YoY -> ON (look-ahead-safe)
    assert reg["recent_prior"][0]["defined"] is False


def test_regime_on_when_yoy_rising():
    cpi = _monthly_cpi(0.02, 0.001, start="2018-01", end="2022-12")   # accelerating -> YoY rising
    rebal = [pd.Timestamp("2021-06-30"), pd.Timestamp("2021-07-31")]
    reg = nrr008.regime_mask_for(rebal, cpi)
    assert reg["recent_prior"][0]["defined"] is True
    assert reg["mask"][0] is True                          # recent >= prior -> ON


def test_regime_off_when_yoy_falling():
    cpi = _monthly_cpi(0.08, -0.001, start="2018-01", end="2022-12")  # decelerating -> YoY falling
    rebal = [pd.Timestamp("2020-06-30"), pd.Timestamp("2020-07-31")]
    reg = nrr008.regime_mask_for(rebal, cpi)
    assert reg["recent_prior"][0]["defined"] is True
    assert reg["mask"][0] is False                         # recent < prior -> OFF (disinflation)


# ---------------------------------------------------------------------------
# Committed engine dispatch untouched -- value signal reuses the D-203 "value" key
# ---------------------------------------------------------------------------
def test_committed_engine_dispatch_untouched():
    data = _synth_data()
    pdata = eng._prepare_window(data, "2019-01-01", "2020-12-31")
    with pytest.raises(ValueError, match="unknown candidate"):
        eng.score_panel_for("value-regime", pdata, pdata["rebal"])


# ---------------------------------------------------------------------------
# Tilt-only realistic cost -- OFF->OFF zero cost, entry cost > 0, after-cost <= cost-free
# ---------------------------------------------------------------------------
def test_tilt_cost_off_to_off_is_zero_and_entry_positive():
    rebal = [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"),
             pd.Timestamp("2020-03-31"), pd.Timestamp("2020-04-30")]
    syms = ["A", "B", "C", "D"]
    pmat = pd.DataFrame({s: [0.03, 0.02, 0.01] for s in syms},
                        index=pd.DatetimeIndex(rebal[:-1]))
    comp = pd.DataFrame({s: [1.0, 1.0, 1.0] for s in syms},
                        index=pd.DatetimeIndex(rebal[:-1]))
    ew_full = [0.02, 0.02, 0.02]
    cmap = {d: {s: 0.01 for s in syms} for d in rebal}
    mask = [False, True, False]            # OFF, ON(entry), OFF(exit)
    out = nrr008.gated_tilt_cost_series(comp, pmat, ew_full, rebal, cmap, mask, top_n=2)
    assert out["active_cost"][0] == 0.0                    # OFF with no prior tilt -> no cost
    assert out["active_cost"][1] > 0.0                     # ON entry -> full round-trip charged
    assert out["active_cost"][2] > 0.0                     # exit of the tilt -> charged
    # after-cost relative never above cost-free
    for rc, rf in zip(out["rel_aftercost"], out["rel_costfree"]):
        if np.isfinite(rc) and np.isfinite(rf):
            assert rc <= rf + 1e-12


# ---------------------------------------------------------------------------
# Combined verdict (cost-free 3-way + realistic addendum)
# ---------------------------------------------------------------------------
def test_verdict_eliminated_when_cost_free_serap():
    v = nrr008.nrr008_verdict(
        cost_free_verdict={"verdict": "SERAP", "reasons": ["gate2 t<2"]},
        g5_realistic=False, breakeven_bps=None, realistic_cost_bps=50.0,
        rel_aftercost_mean=-0.001)
    assert v["headline"] == "ELENDI"
    assert v["oos_gap"] is None
    assert "value-ipligi KAPANIR" in v["close_note"]


def test_verdict_real_edge_when_costfree_edge_and_realistic_survives():
    v = nrr008.nrr008_verdict(
        cost_free_verdict={"verdict": "GERCEK-EDGE", "reasons": ["all_5_gates_pass"]},
        g5_realistic=True, breakeven_bps=300.0, realistic_cost_bps=50.0,
        rel_aftercost_mean=0.01)
    assert v["headline"] == "GERCEK-EDGE"
    assert v["oos_gap"]


def test_verdict_tradeable_degil_when_breakeven_near_cost():
    v = nrr008.nrr008_verdict(
        cost_free_verdict={"verdict": "REJIM-TILT", "reasons": ["only_post_2022"]},
        g5_realistic=True, breakeven_bps=80.0, realistic_cost_bps=50.0,   # 80 < 2x50
        rel_aftercost_mean=0.003)
    assert v["headline"] == "GERCEK-ama-tradeable-DEGIL"
    assert v["oos_gap"]


# ---------------------------------------------------------------------------
# Stage-0 guard
# ---------------------------------------------------------------------------
def test_run_nrr008_refuses_without_stage0(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        nrr008.run_nrr008(stage0_path=missing, require_stage0=True)

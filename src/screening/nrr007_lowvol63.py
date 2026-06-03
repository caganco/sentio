"""NRR-007 lowvol63-IZOLE engine -- isolated 5-gate test of the lowvol63 factor.

lowvol63 lived INSIDE the D-203 EDGE-2 composite (mom120 + hi52 + lowvol63, equal-weight
rank-avg) but was NEVER tested in ISOLATION (the D-203 engine only dispatched value/edge2/
hi52). hi52 lesson: a bundle can HIDE a distinct factor -> it deserves an isolated test.
NRR-007 runs the IDENTICAL lowvol63 signal (eng.lowvol_panel, D-203/EDGE-2-BIREBIR) through
the D-203 5-gate methodology, swapping ONLY gate-5 to realistic Roll+Kyle cost (D-204 reuse).

HONEST EXPECTATION (BEFORE results): demo-3 S1/H4 pre-measured lowvol63-isolated +0.56%/mo,
t=0.94 (below the Gate-2 t>=2 bar) -> PROBABLY ELIMINATED. This is a DEFINITIVE-CLOSURE run,
no celebration expected; elimination is a clean, valuable result.

Strangler -- ZERO touch to the committed engine: gates 1-4 run via run_gates_on_score, a
BIREBIR copy of eng.run_gates whose ONLY difference is that the score panel is INJECTED
(comp parameter) rather than dispatched through eng.score_panel_for. A MATCH=True test
(tests/test_nrr007_lowvol63.py) proves the replica reproduces eng.run_gates exactly on the
hi52 candidate. The D-204 cost harness (per_stock_cost_panel / d204_basket_net_series /
breakeven / holding-period) is REUSED READ-ONLY. Refuses to run unless STAGE0_nrr007.json
exists (pre-registration). MEASUREMENT-ONLY: lowvol window FROZEN (63, D-203-identical),
lambda_kyle FROZEN, no new factor definition, no post-hoc threshold pick.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import d203_clean_universe_test as eng
from src.screening import d204_hi52_stress as d204
from src.screening import nrr007_config as cfg

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_nrr007.json"

_OOS_GAP = d204._OOS_GAP


# ===========================================================================
# gates 1-4 (+ D-203 flat gate-5, context) -- injected-score replica of eng.run_gates
# ===========================================================================
def run_gates_on_score(
    comp: pd.DataFrame, data: dict, rebal: list[pd.Timestamp],
    candidate: str = cfg.NRR007_CANDIDATE, value_kind: str | None = None,
) -> dict:
    """BIREBIR copy of eng.run_gates -- the ONLY difference is that the score panel `comp`
    is INJECTED rather than dispatched through eng.score_panel_for (Strangler: committed
    engine untouched). Uses the engine's frozen D-203 constants verbatim so a MATCH=True test
    can assert run_gates_on_score(score_panel_for("hi52",..),..) == run_gates("hi52",..)."""
    pmat, cpi = data["pmat"], data["cpi"]
    liq = data["liquidity"]

    # full-pool long + bottom baskets
    long_baskets, short_baskets, pools = [], [], []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        pool = sorted(comp.loc[d].dropna().index) if d in comp.index else []
        pools.append(pool)
        long_baskets.append(eng.select_top_n(d, comp, eng.cfg.D203_TOP_N))
        short_baskets.append(eng.select_bottom_n(d, comp, eng.cfg.D203_TOP_N))

    long_net = eng.basket_net_series(pmat, long_baskets, rebal, cost_bps=0.0)["net"]
    short_net = eng.basket_net_series(pmat, short_baskets, rebal, cost_bps=0.0)["net"]
    ew_full = data["ew_full"]
    rel_ew = eng._relative(long_net, ew_full)
    ls = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
          for a, b in zip(long_net, short_net)]

    long_real = eng.to_real(long_net, rebal, cpi)
    long_real_mean = np.nanmean([v for v in long_real if np.isfinite(v)]) if any(
        np.isfinite(v) for v in long_real) else float("nan")
    rel_ci = eng._mean_ci(rel_ew)
    ls_ci = eng._mean_ci(ls)
    long_real_ci = eng._mean_ci(long_real)

    # GATE 1 -- selection null (real terms, top-15 vs random top-15 from same pool)
    null = eng.fair_selection_null(pmat, pools, rebal, cpi, long_real_mean)
    g1 = bool(null.get("beats_fair_null"))

    # GATE 2 -- Newey-West HAC |t| on EW_FULL-relative
    nw_t = eng._nw_t(rel_ew)
    g2 = bool(np.isfinite(nw_t) and abs(nw_t) >= eng.cfg.D203_GATE_NW_T_MIN)

    # GATE 3 -- cross-regime (PRIMARY split decides; SECONDARY reported)
    reg_primary = eng.regime_split(rel_ew, rebal, eng.cfg.D203_REGIME_PRIMARY)
    reg_secondary = eng.regime_split(rel_ew, rebal, eng.cfg.D203_REGIME_SECONDARY)
    g3 = reg_primary["both_positive"]

    # GATE 4 -- liquidity-tercile survival (LIQUID tercile relative edge > 0)
    liq_long = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        lpool = liq.get(d, {}).get("liquid", [])
        liq_long.append(eng.select_top_n(d, comp, eng.cfg.D203_TOP_N, pool=lpool))
    liq_net = eng.basket_net_series(pmat, liq_long, rebal, cost_bps=0.0)["net"]
    liq_rel = eng._relative(liq_net, ew_full)
    liq_rel_mean = np.nanmean([v for v in liq_rel if np.isfinite(v)]) if any(
        np.isfinite(v) for v in liq_rel) else float("nan")
    g4 = bool(np.isfinite(liq_rel_mean) and liq_rel_mean > 0)

    # illiquid tercile (for liquidity-collapse / mirage detection)
    illq_long = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        ipool = liq.get(d, {}).get("illiquid", [])
        illq_long.append(eng.select_top_n(d, comp, eng.cfg.D203_TOP_N, pool=ipool))
    illq_net = eng.basket_net_series(pmat, illq_long, rebal, cost_bps=0.0)["net"]
    illq_rel = eng._relative(illq_net, ew_full)
    illq_rel_mean = np.nanmean([v for v in illq_rel if np.isfinite(v)]) if any(
        np.isfinite(v) for v in illq_rel) else float("nan")
    liquidity_collapse = bool(illq_rel_mean > 0 and not (liq_rel_mean > 0))

    # GATE 5 -- after-cost (relative edge stays > 0 at 20bp AND 100bp)
    cost_legs = {}
    g5_low = g5_high = False
    for tag, bps in (("low_20bp", eng.cfg.D203_GATE_COST_LOW_BPS),
                     ("high_100bp", eng.cfg.D203_GATE_COST_HIGH_BPS)):
        net_c = eng.basket_net_series(pmat, long_baskets, rebal, cost_bps=bps)["net"]
        rel_c = eng._relative(net_c, ew_full)
        m = np.nanmean([v for v in rel_c if np.isfinite(v)]) if any(
            np.isfinite(v) for v in rel_c) else float("nan")
        cost_legs[tag] = {"bps": bps, "rel_ew_mean": eng._r(m), "positive": bool(m > 0)}
        if tag == "low_20bp":
            g5_low = bool(m > 0)
        else:
            g5_high = bool(m > 0)
    g5 = bool(g5_low and g5_high)

    eq = eng._equity_curve(pmat, long_baskets)
    return {
        "candidate": candidate,
        "value_kind": value_kind,
        "n_periods": len(long_net),
        "long_real": long_real_ci,
        "ew_full_relative": rel_ci,
        "long_short": ls_ci,
        "max_drawdown": eng._r(eng.max_drawdown(eq)) if len(eq) > 1 else None,
        "gate1_selection_null": {"pass": g1, **null},
        "gate2_newey_west": {"pass": g2, "hac_t": eng._r(nw_t), "t_min": eng.cfg.D203_GATE_NW_T_MIN},
        "gate3_cross_regime": {"pass": g3, "primary": reg_primary, "secondary": reg_secondary},
        "gate4_liquidity": {"pass": g4, "liquid_rel_mean": eng._r(liq_rel_mean),
                            "illiquid_rel_mean": eng._r(illq_rel_mean),
                            "liquidity_collapse": liquidity_collapse},
        "gate5_after_cost": {"pass": g5, **cost_legs},
        "_internal": {"rel_ew_mean": eng._r(rel_ci.get("mean")), "ls_mean": eng._r(ls_ci.get("mean")),
                      "liquidity_collapse": liquidity_collapse,
                      "only_post_positive": reg_primary["only_post_positive"],
                      "gates": [g1, g2, g3, g4, g5]},
    }


# ===========================================================================
# Selected-picks cost characterization (over the ACTUALLY-traded (date, name) cells)
# ===========================================================================
def selected_cost_summary(
    baskets: list[list[str]], cost_roll: dict, roll_zero: dict, rebal: list[pd.Timestamp],
) -> dict:
    """Mean Roll-leg round-trip + roll-zero share AMONG the names lowvol63 actually trades
    (the 'what does it cost to trade THESE picks' read; compare to the D-204 microcap ~340bp
    / roll-zero %51.9)."""
    n = n_zero = 0
    rt_sum = 0.0
    for i in range(len(baskets)):
        d = rebal[i]
        cmap = cost_roll.get(d, {})
        zmap = roll_zero.get(d, {})
        for name in baskets[i]:
            if name in cmap and np.isfinite(cmap[name]):
                rt_sum += cmap[name]
                n += 1
                n_zero += int(bool(zmap.get(name, False)))
    return {
        "n_selected_cells": n,
        "mean_round_trip_roll": eng._r(rt_sum / n) if n else None,
        "roll_zero_frac": eng._r(n_zero / n) if n else None,
    }


# ===========================================================================
# Verdict -- cost-free 3-way (eng.d203_verdict, canonical) + realistic-cost addendum
# ===========================================================================
def nrr007_verdict(
    cost_free_verdict: dict, g5_realistic: bool, breakeven_bps,
    realistic_cost_bps: float | None, rel_aftercost_mean: float | None,
    safety_mult: float = cfg.NRR007_BREAKEVEN_SAFETY_MULT,
) -> dict:
    """Combine the canonical D-203 cost-free 3-way verdict (SERAP / GERCEK-EDGE / REJIM-TILT)
    with a realistic-cost addendum into a single headline:

      SERAP                        -> ELENDI (expected; consistent with demo-3 t=0.94)
      GERCEK-EDGE/REJIM-TILT, and  -> GERCEK-EDGE (deploy-aday; surprise, first non-hi52)
        g5_realistic AND breakeven >= safety_mult x realistic cost
      GERCEK-EDGE/REJIM-TILT, but  -> GERCEK-ama-tradeable-DEGIL (signal real, cost eats it)
        g5_realistic<=0 OR breakeven < safety_mult x cost

    OOS-gap attached in EVERY non-SERAP branch (hi52-like: inflation-normalization OOS absent).
    """
    cf = cost_free_verdict.get("verdict")
    be = float("inf") if breakeven_bps == "inf" else (
        float(breakeven_bps) if breakeven_bps is not None else None)
    cost = realistic_cost_bps if (realistic_cost_bps is not None
                                  and np.isfinite(realistic_cost_bps)) else None
    be_ok = bool(be is not None and (be == float("inf")
                 or (cost is not None and be >= safety_mult * cost) or cost is None))
    g5 = bool(g5_realistic)

    realistic = {
        "g5_realistic_after_cost": g5,
        "rel_aftercost_mean": eng._r(rel_aftercost_mean) if rel_aftercost_mean is not None else None,
        "breakeven_bps": breakeven_bps,
        "realistic_cost_bps": eng._r(realistic_cost_bps) if realistic_cost_bps is not None else None,
        "breakeven_ge_safetyx_cost": be_ok,
        "safety_mult": safety_mult,
    }

    if cf == "SERAP":
        return {
            "headline": "ELENDI",
            "cost_free_verdict": cost_free_verdict,
            "realistic": realistic,
            "reasons": ["cost-free verdict SERAP -- lowvol63 sinyali maliyet-oncesi bile "
                        "gate-gecmiyor (rel<=0 / long-short<0 / gate-FAIL); demo-3 t=0.94 "
                        "on-gostergesi ile TUTARLI"],
            "close_note": ("lowvol63 izole-olcumde ELENDI (N<=3): EDGE-2-bundle'da gizliydi, "
                           "izole-test maliyet-oncesi bile gate-gecmedigini gosterdi; temiz-arsiv"),
            "oos_gap": None,
        }

    if g5 and be_ok:
        return {
            "headline": "GERCEK-EDGE",
            "cost_free_verdict": cost_free_verdict,
            "realistic": realistic,
            "reasons": [f"cost-free {cf} AND maliyet-sonrasi EW_FULL-relatif > 0 AND "
                        f"breakeven >= {safety_mult}x gercekci-maliyet"],
            "deploy_note": ("hi52-disi ILK deploy-edilebilir Yol-1 cross-sectional aday "
                            "(SURPRIZ; demo-3 on-gostergesinin aksine) -- deploy ayri "
                            "the project karari, otomatik-DEGIL"),
            "oos_gap": _OOS_GAP,
        }

    reasons = [f"cost-free {cf} (sinyal-var) AMA"]
    if not g5:
        reasons.append("maliyet-sonrasi EW_FULL-relatif <= 0")
    if not be_ok:
        reasons.append(f"breakeven < {safety_mult}x gercekci-maliyet")
    return {
        "headline": "GERCEK-ama-tradeable-DEGIL",
        "cost_free_verdict": cost_free_verdict,
        "realistic": realistic,
        "reasons": reasons,
        "close_note": ("lowvol63 sinyal-GERCEK ama retail-tradeable-degil -- maliyet edge'i "
                       "yiyor; temiz-arsiv, hi52-verdict ile tutarli desen"),
        "oos_gap": _OOS_GAP,
    }


# ===========================================================================
# Orchestrator
# ===========================================================================
def _series_block(series: list[float]) -> dict:
    return {**eng._mean_ci(series), "nw_t": eng._r(eng._nw_t(series))}


def run_nrr007(
    root: Path | str = cfg.NRR007_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
) -> dict:
    """Full NRR-007 lowvol63 ISOLATED test. REFUSES to run unless STAGE0_nrr007.json exists
    (pre-registration). Reuses the D-203 engine (via run_gates_on_score replica) + D-204 cost
    harness + frozen D-202 panel. Gates 1-4 are D-203 cost-free; gate-5 is realistic Roll+Kyle."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; NRR-007 must be frozen "
            "BEFORE results (pre-registration discipline).")

    data = eng.load_d202_panel(root)
    close, value_tl = data["close"], data["value_tl"]

    pdata = eng._prepare_window(data, cfg.NRR007_COMMON_WINDOW_START, cfg.NRR007_COMMON_WINDOW_END)
    rebal = pdata["rebal"]
    daily, pmat, ew_full = pdata["daily"], pdata["pmat"], pdata["ew_full"]

    # --- lowvol63 signal (IDENTICAL to D-203/EDGE-2; engine CALLED, not modified) ---
    comp = eng._xs_rank(eng.lowvol_panel(daily, rebal))

    # --- gates 1-4 (+ D-203 flat gate-5 as CONTEXT) via the injected-score replica ---
    gate_block = run_gates_on_score(comp, pdata, rebal)
    cost_free_verdict = eng.d203_verdict(gate_block)

    # --- realistic gate-5 (D-204 Roll+Kyle, EW_FULL-relative) ---
    long_baskets = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        long_baskets.append(eng.select_top_n(d, comp, cfg.NRR007_TOP_N))

    cost = d204.per_stock_cost_panel(close, value_tl, rebal)
    free = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=None)
    roll = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_roll"])
    tier = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_tier"])

    rel_free = eng._relative(free["net"], ew_full)
    rel_roll = eng._relative(roll["net"], ew_full)   # after-cost PRIMARY (realistic gate-5)
    rel_tier = eng._relative(tier["net"], ew_full)   # after-cost cross-check
    rel_roll_mean = (float(np.nanmean([v for v in rel_roll if np.isfinite(v)]))
                     if any(np.isfinite(v) for v in rel_roll) else None)
    g5_realistic = bool(rel_roll_mean is not None and rel_roll_mean > 0)

    be = d204.breakeven_cost_bps(free["net"], ew_full, free["turnover"])
    eff_bps = d204.effective_flat_bps(roll["cost"], roll["turnover"])

    # --- turnover / holding (lowvol expected LOW turnover, unlike hi52 ~88%) ---
    hold = d204.holding_period_stats(long_baskets, rebal, cfg.NRR007_PRIMARY_CADENCE)
    sel_cost = selected_cost_summary(long_baskets, cost["cost_roll"], cost["roll_zero"], rebal)
    wf = d204.walk_forward(rel_roll, rebal, cfg.NRR007_WALKFWD_SPLIT, cfg.NRR007_DISINFLATION_WINDOW)

    verdict = nrr007_verdict(
        cost_free_verdict=cost_free_verdict, g5_realistic=g5_realistic,
        breakeven_bps=be["breakeven_bps"], realistic_cost_bps=eff_bps,
        rel_aftercost_mean=rel_roll_mean)

    out = {
        "directive": "NRR-007",
        "phase": "FAZ-1 lowvol63 ISOLATED (5-gate, gate-5 realistic Roll+Kyle)",
        "config_version": cfg.NRR007_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.NRR007_PRICE_CONTENT_HASH,
        "candidate": cfg.NRR007_CANDIDATE_LABEL,
        "benchmark": "EW_FULL (delisted-inclusive equal-weight of full eligible universe, D-203-standard)",
        "lowvol_window": cfg.NRR007_LOWVOL_WINDOW,
        "n_rebal": len(rebal),
        "prior_indicator": {
            "demo3_s1_h4_lowvol63_isolated": {"mean_monthly": 0.0056, "nw_t": 0.94,
                                              "note": "pre-cost + full-universe; below Gate-2 t>=2 bar"},
        },
        "cost": {
            "full_universe_summary": cost["summary"],
            "selected_picks_summary": sel_cost,
            "realistic_cost_flat_bps_equiv": eng._r(eff_bps),
            "breakeven": be,
            "note": ("compare selected_picks mean_round_trip_roll + roll_zero_frac to the "
                     "D-204 microcap ~340bp / roll-zero %51.9; breakeven vs realized cost is "
                     "the model-independent read"),
        },
        "edge": {
            "n_periods": len(free["net"]),
            "rel_costfree": _series_block(rel_free),
            "rel_aftercost_roll": _series_block(rel_roll),   # PRIMARY (realistic gate-5)
            "rel_aftercost_tier": _series_block(rel_tier),   # cross-check
            "long_short_costfree": gate_block["long_short"],
        },
        "gates": {
            "gate1_selection_null": gate_block["gate1_selection_null"],
            "gate2_newey_west_costfree": gate_block["gate2_newey_west"],
            "gate3_cross_regime_costfree": gate_block["gate3_cross_regime"],
            "gate4_liquidity_costfree": gate_block["gate4_liquidity"],
            "gate5_after_cost_flat_CONTEXT": gate_block["gate5_after_cost"],
            "gate5_after_cost_realistic": {"pass": g5_realistic,
                                           "rel_aftercost_mean": eng._r(rel_roll_mean),
                                           "model": "Roll(1984)+Kyle(1985), D-204 reuse"},
            "cost_free_all_pass": all(gate_block["_internal"]["gates"]),
        },
        "holding_period": hold,
        "stres3_oos_walk_forward": wf,
        "verdict": verdict,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("NRR-007 results written to %s", out_path)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = run_nrr007(out_path=_RESULTS_DIR / "nrr007_results.json")
    print(f"[nrr007] lowvol63-isolated -> {res['verdict']['headline']} "
          f"(cost-free: {res['verdict']['cost_free_verdict']['verdict']})")

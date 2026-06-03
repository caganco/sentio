"""NRR-008 value-REJIM-KOLU engine -- D-203-IDENTICAL value tilt gated ON/OFF by a
look-ahead-safe trailing-12m YoY-TUFE 6-month DIRECTION rule (Aday-A, APPROVED the project
2026-06-03, FROZEN in docs/yol1/STAGE0_nrr008.json before any edge was measured).

value-static failed twice (D-203 SERAP NW |t|=0.76, illiquid-heavy; D-Y1-001 KIRILGAN). The
ONE untested arm: turn the value tilt OFF in disinflation, ON in rising/flat inflation. This
is value's 3rd and FINAL round (N<=3 lock -- no 4th).

Strangler -- ZERO touch to the committed engine: the value signal is D-203-IDENTICAL
(eng.score_panel_for("value", ...) is CALLED, the engine is NOT modified). Gates 1-4 (+ the
flat gate-5 context) run via run_gates_on_score, a BIREBIR copy of eng.run_gates whose ONLY
structural difference is the INJECTED score panel `comp` (NRR-007 precedent). When
regime_mask=None it reproduces eng.run_gates EXACTLY (a MATCH=True test asserts this on the
value candidate). The regime gating is applied ONLY when a mask is passed:

  OFF month (regime_recent < regime_prior, affirmatively falling YoY -> disinflation): the
  strategy holds EW_FULL (EW-neutral) -> every EW_FULL-relative series is EXACTLY 0 that period
  (frozen "relative excess = 0"); the selection-null pool is emptied so gate-1 measures the
  selection skill on ON months only.

  ON month (regime_recent >= regime_prior, flat/rising; OR the regime is UNDEFINED in the
  trailing warmup): the strategy holds the D-203 value top-15.

WARMUP CONVENTION (look-ahead-safe, structural -- NOT post-hoc tuning): OFF is asserted ONLY
when both YoY(M-1) and YoY(M-7) are defined AND YoY(M-1) < YoY(M-7). When the trailing TUFE
history is insufficient (early-sample months, ~2019-07..2020), the disinflation signal CANNOT
be affirmed, so the month stays ON -- the faithful reading of the frozen "OFF if falling; ON
otherwise" semantics, and economically aligned (the 2019-21 warmup is the rising-inflation
pre_surge regime where D-Y1 found value STRONGEST, +26%).

The D-204 cost harness is REUSED READ-ONLY for the per-stock Roll+Kyle panel; the realistic
gate-5 charges cost ONLY on the 15-name tilt's entry/exit/rebalance (the frozen "into/out of
the tilt" model -- OFF->OFF incurs zero incremental turnover). MEASUREMENT-ONLY: regime rule
+ 6-month window + t-1 lag + value definition + gate thresholds + lambda_kyle all FROZEN; no
post-hoc relaxation. Refuses to run unless STAGE0_nrr008.json exists (pre-registration).
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
from src.screening import nrr008_config as cfg

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_nrr008.json"

_OOS_GAP = d204._OOS_GAP
_MICRO_RT = d204._MICRO_RT


# ===========================================================================
# Regime-direction signal (look-ahead-safe) -- the FROZEN Aday-A rule
# ===========================================================================
def _monthly_yoy(cpi: pd.Series) -> pd.Series:
    """Trailing-12m YoY of the month-end TUFE index, indexed by calendar month (Period[M]).

    TUFE_monthend(M) = last available daily observation of month M (the frozen D-187 index).
    infl_yoy(M) = TUFE_monthend(M) / TUFE_monthend(M-12) - 1. Look-ahead safety is enforced by
    the t-1 lag at the consumption site (regime_mask_for), not here."""
    if cpi is None or len(cpi) == 0:
        return pd.Series(dtype=float)
    monthly = cpi.groupby(cpi.index.to_period("M")).last().sort_index()
    return monthly / monthly.shift(cfg.NRR008_REGIME_YOY_MONTHS) - 1.0


def regime_mask_for(rebal: list[pd.Timestamp], cpi: pd.Series) -> dict:
    """Per-period (i in 0..len(rebal)-2) ON/OFF mask for the value tilt.

    At the rebalance in month M (position taken on the last trading day of M):
      regime_recent = infl_yoy(M-1)  (t-1 publication lag -> look-ahead safe)
      regime_prior  = infl_yoy(M-7)  (6-month direction window)
      OFF if (both defined) and regime_recent < regime_prior  (disinflation)
      ON  otherwise (flat/rising, or undefined warmup)
    Returns {mask, labels, n_on, n_off, on_frac, first_off_month, recent_prior}."""
    yoy = _monthly_yoy(cpi)
    lag = cfg.NRR008_REGIME_LAG_MONTHS
    win = cfg.NRR008_REGIME_WINDOW_MONTHS
    mask, labels, recent_prior = [], [], []
    for i in range(len(rebal) - 1):
        m = pd.Period(pd.Timestamp(rebal[i]), freq="M")
        m_recent = m - lag
        m_prior = m - lag - win
        recent = yoy.get(m_recent, np.nan)
        prior = yoy.get(m_prior, np.nan)
        defined = bool(pd.notna(recent) and pd.notna(prior))
        off = bool(defined and float(recent) < float(prior))
        on = not off
        mask.append(on)
        labels.append("ON" if on else "OFF")
        recent_prior.append({
            "rebal_month": str(m), "recent_month": str(m_recent), "prior_month": str(m_prior),
            "yoy_recent": eng._r(float(recent)) if pd.notna(recent) else None,
            "yoy_prior": eng._r(float(prior)) if pd.notna(prior) else None,
            "defined": defined, "label": labels[-1],
        })
    n_on = int(sum(mask))
    n_off = len(mask) - n_on
    first_off = next((recent_prior[i]["rebal_month"] for i in range(len(mask)) if not mask[i]), None)
    return {
        "mask": mask, "labels": labels, "n_periods": len(mask),
        "n_on": n_on, "n_off": n_off,
        "on_frac": eng._r(n_on / len(mask)) if mask else None,
        "first_off_month": first_off,
        "recent_prior": recent_prior,
    }


# ===========================================================================
# gates 1-4 (+ flat gate-5 context) -- injected-score replica of eng.run_gates,
# regime-gated when regime_mask is provided (regime_mask=None -> exact replica).
# ===========================================================================
def run_gates_on_score(
    comp: pd.DataFrame, data: dict, rebal: list[pd.Timestamp],
    candidate: str = cfg.NRR008_CANDIDATE, value_kind: str | None = None,
    regime_mask: list[bool] | None = None,
) -> dict:
    """BIREBIR copy of eng.run_gates -- the ONLY differences are (1) the score panel `comp`
    is INJECTED rather than dispatched through eng.score_panel_for (Strangler), and (2) an
    optional regime_mask gates OFF months to EW_FULL-neutral (relative=0). With
    regime_mask=None and comp=eng.score_panel_for(candidate,..) the output is byte-identical
    to eng.run_gates(candidate,..) (MATCH=True fidelity test)."""
    pmat, cpi = data["pmat"], data["cpi"]
    liq = data["liquidity"]

    # full-pool long + bottom baskets (D-203-IDENTICAL)
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

    # --- REGIME GATING (NRR-008): OFF months hold EW_FULL -> relative EXACTLY 0; the
    #     selection pool is emptied so gate-1 scores selection skill on ON months only. ---
    if regime_mask is not None:
        long_net = [long_net[i] if regime_mask[i] else ew_full[i] for i in range(len(long_net))]
        short_net = [short_net[i] if regime_mask[i] else ew_full[i] for i in range(len(short_net))]
        pools = [pools[i] if regime_mask[i] else [] for i in range(len(pools))]

    rel_ew = eng._relative(long_net, ew_full)
    ls = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
          for a, b in zip(long_net, short_net)]

    long_real = eng.to_real(long_net, rebal, cpi)
    if regime_mask is not None:
        long_real = [long_real[i] if regime_mask[i] else float("nan")
                     for i in range(len(long_real))]
    long_real_mean = np.nanmean([v for v in long_real if np.isfinite(v)]) if any(
        np.isfinite(v) for v in long_real) else float("nan")
    rel_ci = eng._mean_ci(rel_ew)
    ls_ci = eng._mean_ci(ls)
    long_real_ci = eng._mean_ci(long_real)

    # GATE 1 -- selection null (real terms, top-15 vs random top-15 from same pool)
    null = eng.fair_selection_null(pmat, pools, rebal, cpi, long_real_mean)
    g1 = bool(null.get("beats_fair_null"))

    # GATE 2 -- Newey-West HAC |t| on EW_FULL-relative (KEY gate; static value t=0.76)
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
    if regime_mask is not None:
        liq_net = [liq_net[i] if regime_mask[i] else ew_full[i] for i in range(len(liq_net))]
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
    if regime_mask is not None:
        illq_net = [illq_net[i] if regime_mask[i] else ew_full[i] for i in range(len(illq_net))]
    illq_rel = eng._relative(illq_net, ew_full)
    illq_rel_mean = np.nanmean([v for v in illq_rel if np.isfinite(v)]) if any(
        np.isfinite(v) for v in illq_rel) else float("nan")
    liquidity_collapse = bool(illq_rel_mean > 0 and not (liq_rel_mean > 0))

    # GATE 5 -- after-cost flat (CONTEXT; the realistic Roll+Kyle gate is the ASIL gate,
    # computed in run_nrr008). OFF months contribute 0 (EW-neutral, no active trade).
    cost_legs = {}
    g5_low = g5_high = False
    for tag, bps in (("low_20bp", eng.cfg.D203_GATE_COST_LOW_BPS),
                     ("high_100bp", eng.cfg.D203_GATE_COST_HIGH_BPS)):
        net_c = eng.basket_net_series(pmat, long_baskets, rebal, cost_bps=bps)["net"]
        if regime_mask is not None:
            net_c = [net_c[i] if regime_mask[i] else ew_full[i] for i in range(len(net_c))]
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
# Realistic gate-5 -- per-stock Roll+Kyle charged ONLY on the 15-name TILT
# (entry / exit / ON->ON rebalance). OFF->OFF incurs zero incremental turnover.
# ===========================================================================
def gated_tilt_cost_series(
    comp: pd.DataFrame, pmat: pd.DataFrame, ew_full: list[float],
    rebal: list[pd.Timestamp], cost_map: dict, regime_mask: list[bool],
    top_n: int = cfg.NRR008_TOP_N,
) -> dict:
    """EW_FULL-relative after-cost series for the regime-gated value tilt, charging realistic
    per-stock round-trip cost ONLY on the active 15-name tilt's turnover (the frozen "into/out
    of the tilt" model). ON month: hold value top-15 (gross - tilt cost - tax). OFF month: hold
    EW_FULL (relative 0), but the ON->OFF EXIT cost hits the first OFF period. Returns the
    cost-free and after-cost relative series + the active turnover/cost sequences."""
    active = [eng.select_top_n(rebal[i], comp, top_n) if regime_mask[i] else []
              for i in range(len(rebal) - 1)]

    def _tilt_cost(prev: list[str], cur: list[str], cmap: dict) -> float:
        # full round-trip on a freshly established / fully liquidated tilt; weighted
        # delta on an ON->ON rebalance (mirrors d204_basket_net_series accounting).
        if not prev and not cur:
            return 0.0
        if not prev:                       # entry: buy the whole tilt
            return sum(cmap.get(n, _MICRO_RT) for n in cur) / len(cur)
        if not cur:                        # exit: sell the whole tilt
            return sum(cmap.get(n, _MICRO_RT) for n in prev) / len(prev)
        wp = {t: 1.0 / len(prev) for t in prev}
        wc = {t: 1.0 / len(cur) for t in cur}
        return sum(0.5 * abs(wc.get(n, 0.0) - wp.get(n, 0.0)) * cmap.get(n, _MICRO_RT)
                   for n in set(wp) | set(wc))

    rel_free, rel_cost, costs, turns = [], [], [], []
    prev: list[str] = []
    for i in range(len(active)):
        cur = active[i]
        cmap = cost_map.get(rebal[i], {})
        cost = _tilt_cost(prev, cur, cmap)
        tau = eng._turnover(prev, cur) if cur else (1.0 if prev else 0.0)
        tax = eng._tax_drag(rebal[i], rebal[i + 1])
        costs.append(cost)
        turns.append(tau)
        if regime_mask[i]:
            g = eng._basket_period(pmat, i, cur)
            net_free = g - tax if np.isfinite(g) else float("nan")
            net_cost = g - cost - tax if np.isfinite(g) else float("nan")
        else:
            # OFF: hold EW_FULL -> cost-free relative 0; only the exit cost (if any) bites.
            net_free = ew_full[i]
            net_cost = (ew_full[i] - cost) if np.isfinite(ew_full[i]) else float("nan")
        rel_free.append(eng._relative([net_free], [ew_full[i]])[0])
        rel_cost.append(eng._relative([net_cost], [ew_full[i]])[0])
        prev = cur
    return {"rel_costfree": rel_free, "rel_aftercost": rel_cost,
            "active_cost": costs, "active_turnover": turns, "active_baskets": active}


# ===========================================================================
# Verdict -- cost-free 3-way (eng.d203_verdict, canonical) + realistic-cost addendum
# ===========================================================================
def nrr008_verdict(
    cost_free_verdict: dict, g5_realistic: bool, breakeven_bps,
    realistic_cost_bps: float | None, rel_aftercost_mean: float | None,
    safety_mult: float = cfg.NRR008_BREAKEVEN_SAFETY_MULT,
) -> dict:
    """Combine the canonical D-203 cost-free 3-way verdict (SERAP / GERCEK-EDGE / REJIM-TILT)
    with a realistic-cost addendum into a single headline:

      SERAP                        -> ELENDI (value thread CLOSED, N<=3 final; clean archive)
      GERCEK-EDGE/REJIM-TILT, and  -> GERCEK-EDGE (first deployable value-based Yol-1 candidate;
        g5_realistic AND breakeven >= safety_mult x cost   SURPRISE vs static-value SERAP/fragile prior -- overlay CANDIDATE)
      GERCEK-EDGE/REJIM-TILT, but  -> GERCEK-ama-tradeable-DEGIL (signal real, cost eats it)
        g5_realistic<=0 OR breakeven < safety_mult x cost

    OOS-gap attached in EVERY non-SERAP branch (inflation-normalization OOS absent; the regime
    mask is fit-free but its EFFICACY is not OOS-proven). Deployment is a separate the project
    decision, never auto-triggered."""
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
            "reasons": ["cost-free verdict SERAP -- regime-gated value sinyali maliyet-oncesi "
                        "bile gate-gecmiyor (rel<=0 / long-short<0 / gate-FAIL, gate-2 NW|t|<2 "
                        "dahil); rejim-gating value'yu kurtarmadi"],
            "close_note": ("value-regime ELENDI -> value-ipligi KAPANIR (N<=3 final): statik "
                           "D-203/D-Y1 SERAP/kirilgan idi, rejim-kollu-kol da gecemedi; temiz-arsiv"),
            "oos_gap": None,
        }

    if g5 and be_ok:
        return {
            "headline": "GERCEK-EDGE",
            "cost_free_verdict": cost_free_verdict,
            "realistic": realistic,
            "reasons": [f"cost-free {cf} AND maliyet-sonrasi EW_FULL-relatif > 0 AND "
                        f"breakeven >= {safety_mult}x gercekci-maliyet"],
            "deploy_note": ("ILK deploy-edilebilir value-temelli Yol-1 cross-sectional aday "
                            "(SURPRIZ; statik-value SERAP/kirilgan prior'unun aksine) -- overlay "
                            "ADAY, deploy ayri the project karari, otomatik-DEGIL"),
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
        "close_note": ("value-regime sinyal-GERCEK ama retail-tradeable-degil -- maliyet edge'i "
                       "yiyor; value-ipligi KAPANIR (N<=3 final), temiz-arsiv"),
        "oos_gap": _OOS_GAP,
    }


# ===========================================================================
# Orchestrator
# ===========================================================================
def _series_block(series: list[float]) -> dict:
    return {**eng._mean_ci(series), "nw_t": eng._r(eng._nw_t(series))}


def run_nrr008(
    root: Path | str = cfg.NRR008_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
) -> dict:
    """Full NRR-008 value-regime test. REFUSES to run unless STAGE0_nrr008.json exists
    (pre-registration). value signal D-203-IDENTICAL (eng.score_panel_for CALLED); regime
    gating look-ahead-safe; gates 1-4 + flat gate-5 context via run_gates_on_score replica;
    realistic gate-5 charges cost only on the 15-name tilt."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; NRR-008 must be frozen "
            "BEFORE results (pre-registration discipline).")

    data = eng.load_d202_panel(root)
    close, value_tl, cpi = data["close"], data["value_tl"], data["cpi"]

    pdata = eng._prepare_window(data, cfg.NRR008_COMMON_WINDOW_START, cfg.NRR008_COMMON_WINDOW_END)
    rebal = pdata["rebal"]
    ew_full = pdata["ew_full"]

    # --- value signal (D-203-IDENTICAL; engine CALLED, not modified) ---
    comp = eng.score_panel_for(cfg.NRR008_VALUE_DISPATCH, pdata, rebal, cfg.NRR008_VALUE_PRIMARY)

    # --- look-ahead-safe regime ON/OFF mask (FROZEN Aday-A direction rule) ---
    regime = regime_mask_for(rebal, cpi)
    mask = regime["mask"]

    # --- gates 1-4 (+ flat gate-5 context) via the injected-score replica, regime-gated ---
    gate_block = run_gates_on_score(comp, pdata, rebal, regime_mask=mask)
    cost_free_verdict = eng.d203_verdict(gate_block)

    # --- realistic gate-5 (D-204 Roll+Kyle, tilt-only cost, EW_FULL-relative) ---
    cost = d204.per_stock_cost_panel(close, value_tl, rebal)
    roll = gated_tilt_cost_series(comp, pdata["pmat"], ew_full, rebal, cost["cost_roll"], mask)
    tier = gated_tilt_cost_series(comp, pdata["pmat"], ew_full, rebal, cost["cost_tier"], mask)

    rel_free = roll["rel_costfree"]
    rel_roll = roll["rel_aftercost"]    # after-cost PRIMARY (realistic gate-5)
    rel_tier = tier["rel_aftercost"]    # after-cost cross-check
    rel_roll_mean = (float(np.nanmean([v for v in rel_roll if np.isfinite(v)]))
                     if any(np.isfinite(v) for v in rel_roll) else None)
    g5_realistic = bool(rel_roll_mean is not None and rel_roll_mean > 0)

    be = d204.breakeven_cost_bps(rel_free, [0.0] * len(rel_free), roll["active_turnover"])
    eff_bps = d204.effective_flat_bps(roll["active_cost"], roll["active_turnover"])

    # --- turnover / holding over the ACTIVE tilt (OFF months hold no tilt) ---
    active_on = [roll["active_baskets"][i] for i in range(len(mask)) if mask[i]]
    hold = d204.holding_period_stats(roll["active_baskets"], rebal, cfg.NRR008_PRIMARY_CADENCE)
    wf = d204.walk_forward(rel_roll, rebal, cfg.NRR008_WALKFWD_SPLIT, cfg.NRR008_DISINFLATION_WINDOW)

    verdict = nrr008_verdict(
        cost_free_verdict=cost_free_verdict, g5_realistic=g5_realistic,
        breakeven_bps=be["breakeven_bps"], realistic_cost_bps=eff_bps,
        rel_aftercost_mean=rel_roll_mean)

    out = {
        "directive": "NRR-008",
        "phase": "FAZ-1 value-REJIM-KOLU (5-gate, gate-5 realistic Roll+Kyle, regime-gated)",
        "config_version": cfg.NRR008_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.NRR008_PRICE_CONTENT_HASH,
        "candidate": cfg.NRR008_CANDIDATE_LABEL,
        "benchmark": "EW_FULL (delisted-inclusive equal-weight of full eligible universe, D-203-standard)",
        "value_kind": cfg.NRR008_VALUE_PRIMARY,
        "n_rebal": len(rebal),
        "regime": {
            "rule": ("Aday-A inflation-DIRECTION: ON if YoY-TUFE(M-1) >= YoY-TUFE(M-7) "
                     "(flat/rising or undefined-warmup), OFF if < (disinflation). 6-month "
                     "window + t-1 lag FROZEN; DIRECTION-not-LEVEL."),
            "n_on": regime["n_on"], "n_off": regime["n_off"], "on_frac": regime["on_frac"],
            "first_off_month": regime["first_off_month"],
            "labels": regime["labels"],
            "warmup_note": ("OFF is asserted only when YoY(M-1) & YoY(M-7) are both defined "
                            "AND falling; undefined warmup (~2019-07..2020) stays ON -- "
                            "look-ahead-safe, economically the rising pre_surge regime."),
        },
        "prior": {
            "d203_static_value": {"gate2_nw_t": 0.76, "verdict": "SERAP", "note": "illiquid-heavy"},
            "dy1_001": {"verdict": "KIRILGAN/REJIM-BAGIMLI",
                        "note": "P/B mechanical-PASS but E/P contradicts + OOS collapse"},
        },
        "cost": {
            "full_universe_summary": cost["summary"],
            "realistic_cost_flat_bps_equiv": eng._r(eff_bps),
            "breakeven": be,
            "note": ("tilt-only realistic cost (entry/exit/rebalance of the 15-name value tilt); "
                     "OFF months hold EW_FULL with zero incremental turnover. breakeven vs "
                     "realized cost is the model-independent read"),
        },
        "edge": {
            "n_periods": len(rel_free),
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
                                           "model": "Roll(1984)+Kyle(1985) tilt-only, D-204 reuse"},
            "cost_free_all_pass": all(gate_block["_internal"]["gates"]),
        },
        "holding_period": hold,
        "active_on_months": len(active_on),
        "stres3_oos_walk_forward": wf,
        "verdict": verdict,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("NRR-008 results written to %s", out_path)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = run_nrr008(out_path=_RESULTS_DIR / "nrr008_results.json")
    print(f"[nrr008] value-regime -> {res['verdict']['headline']} "
          f"(cost-free: {res['verdict']['cost_free_verdict']['verdict']}; "
          f"ON={res['regime']['n_on']}/OFF={res['regime']['n_off']})")

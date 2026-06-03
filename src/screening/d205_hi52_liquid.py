"""D-205 hi52 LIKIT-ONCE engine -- liquid-universe-first hi52 under realistic cost.

D-204 found hi52 = GERCEK-ama-tradeable-DEGIL on the naive prototype (realized realistic
cost ~340bp > breakeven ~302bp; root cause ~88% turnover x ~98% microcap). NRR-005 showed
the killer is the COST-RATE (microcap), not the turnover-LEVEL, and that the hi52 SIGNAL
lives in liquid names. D-205 restricts the UNIVERSE to absolute-liquid names FIRST (trailing-
63d-median ADV >= D205_LIQUID_ADV_MIN_TL, frozen on NRR-006 pool-feasibility), then applies
the IDENTICAL hi52 signal, and asks: does the EW_FULL_LIQUID-relative edge survive REALISTIC
per-stock cost (Roll + Kyle + tier)? This does NOT relax the D-204 verdict; it attacks its
root cause (cost-rate). N=1 candidate, D-205 = 3rd and FINAL hi52 measurement.

Strangler: REUSES the D-203 engine (panel/hi52/select/null/regime/NW/CI/real) and the D-204
cost harness (per_stock_cost_panel / d204_basket_net_series / breakeven / holding-period /
walk-forward / deploy-hurdle) READ-ONLY -- neither is modified. The ONLY new logic is the
liquid universe, the liquid-EW benchmark, the within-liquid sub-tier gate (gate-4, with
lower-half SAMPLE SIZE reported), and the 2-way verdict. Refuses to run unless
STAGE0_d205.json exists (pre-registration). MEASUREMENT-ONLY: the ADV threshold is FROZEN
(post-hoc selection FORBIDDEN), lambda_kyle FROZEN, the buffer is a reported VIEW.
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
from src.screening import d205_config as cfg

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_d205.json"


# ===========================================================================
# Liquid universe (D-205 core) -- absolute trailing-median-ADV floor
# ===========================================================================
def liquid_universe_pools(
    value_tl: pd.DataFrame, rebal: list[pd.Timestamp],
    adv_min: float = cfg.D205_LIQUID_ADV_MIN_TL,
    trailing: int = cfg.D205_LIQUID_ADV_TRAILING_DAYS,
) -> dict:
    """Per rebalance date: the list of names whose trailing-`trailing`-day median traded
    value (value_tl) is >= `adv_min`, plus that name's trailing-median ADV. Also returns a
    per-rebalance size series so feasibility (top-15 needs >= 15 names, healthy >= ~30) can
    be reported HONESTLY -- a too-narrow universe is itself a D-205 result, not forced.

    Returns {pools: {date: [names]}, adv: {date: {name: adv}}, sizes: [int,...]}.
    """
    vt = value_tl.sort_index()
    pools: dict[pd.Timestamp, list[str]] = {}
    adv_map: dict[pd.Timestamp, dict[str, float]] = {}
    sizes: list[int] = []
    for d in rebal:
        win = vt.loc[vt.index <= d].tail(trailing)
        med = win.median(skipna=True).dropna()
        med = med[med >= adv_min]
        names = sorted(med.index)
        pools[d] = names
        adv_map[d] = {n: float(med[n]) for n in names}
        sizes.append(len(names))
    return {"pools": pools, "adv": adv_map, "sizes": sizes}


def ew_liquid_benchmark(
    pmat: pd.DataFrame, pools: dict[pd.Timestamp, list[str]], rebal: list[pd.Timestamp],
) -> list[float]:
    """Equal-weight per-period return of the LIQUID universe (the honest selection bar for
    D-205): does hi52-top-15 beat just holding ALL liquid names EW? Period i uses the liquid
    pool defined at rebal[i] (the period's START), delisted-inclusive within that pool."""
    out = []
    for i in range(len(pmat)):
        names = [c for c in pools.get(rebal[i], []) if c in pmat.columns]
        vals = pmat.iloc[i][names].values if names else np.array([])
        out.append(float(np.nanmean(vals)) if len(vals) and np.isfinite(vals).any()
                   else float("nan"))
    return out


def liquid_buffer_baskets(
    comp: pd.DataFrame, pools: dict[pd.Timestamp, list[str]], rebal: list[pd.Timestamp],
    enter_n: int = cfg.D205_BUFFER_ENTER, exit_k: int = cfg.D205_BUFFER_EXIT,
) -> list[list[str]]:
    """Ratchet VIEW (secondary): hold a name if it is in the liquid-universe top-`enter_n`
    OR (held last period AND still in the liquid-universe top-`exit_k`). exit_k == enter_n
    reproduces the naive liquid-first monthly rule. Reported, NOT selected."""
    baskets: list[list[str]] = []
    prev: list[str] = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        pool = pools.get(d, [])
        if d not in comp.index or not pool:
            baskets.append([])
            prev = []
            continue
        row = comp.loc[d].dropna()
        row = row[row.index.intersection(pool)].sort_values(ascending=False)
        enter = set(row.head(enter_n).index)
        keep = set(row.head(exit_k).index)
        held = sorted(enter | (set(prev) & keep))
        baskets.append(held)
        prev = held
    return baskets


def selected_cost_summary(
    baskets: list[list[str]], cost_roll: dict, roll_zero: dict, rebal: list[pd.Timestamp],
) -> dict:
    """Cost characterization over the ACTUALLY-SELECTED (date, name) cells (vs the full-
    universe summary). Reports mean Roll-leg round-trip + the roll-zero share AMONG the names
    hi52-liquid actually trades -- the relevant 'what does it cost to trade these picks' number
    (compare to the D-204 microcap ~340bp / roll-zero %51.9)."""
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
# gate-4 -- within-liquid sub-tier consistency (upper/lower ADV half)
# ===========================================================================
def subtier_consistency(
    comp: pd.DataFrame, pmat: pd.DataFrame, rebal: list[pd.Timestamp],
    liq: dict, cost_roll: dict, split: float = cfg.D205_SUBTIER_SPLIT,
    top_n: int = cfg.D205_TOP_N,
) -> dict:
    """Split the liquid universe each period into an upper/lower ADV half (at `split`), and
    within EACH half run hi52 top-min(top_n, half) vs that half's EW, AFTER realistic cost.
    PASS (g4) if BOTH halves are relative-positive -> the edge is not concentrated only at
    the very top of liquidity. REPORTS each half's basket SAMPLE SIZE (min/median): per the
    Cagan note, a narrow lower half (few names) makes the lower-half mean noisy, so a g4-FAIL
    must be read alongside the sample size (real signal-loss vs small-sample noise)."""
    pools, adv = liq["pools"], liq["adv"]
    half_baskets = {"upper": [], "lower": []}
    half_bench = {"upper": [], "lower": []}
    half_sizes = {"upper": [], "lower": []}
    for i in range(len(rebal) - 1):
        d = rebal[i]
        names = pools.get(d, [])
        advd = adv.get(d, {})
        if len(names) < 2:
            for h in ("upper", "lower"):
                half_baskets[h].append([])
                half_bench[h].append(float("nan"))
            continue
        ser = pd.Series({n: advd[n] for n in names if n in advd}).sort_values(ascending=False)
        cut = int(round(len(ser) * split))
        cut = min(max(cut, 1), len(ser) - 1)
        halves = {"upper": list(ser.index[:cut]), "lower": list(ser.index[cut:])}
        for h, pool_h in halves.items():
            basket = eng.select_top_n(d, comp, top_n, pool=pool_h)
            half_baskets[h].append(basket)
            half_sizes[h].append(len(basket))
            vals = pmat.iloc[i][[c for c in pool_h if c in pmat.columns]].values
            vals = vals[np.isfinite(vals)]
            half_bench[h].append(float(np.mean(vals)) if len(vals) else float("nan"))
    out = {}
    for h in ("upper", "lower"):
        net = d204.d204_basket_net_series(pmat, half_baskets[h], rebal, cost_map=cost_roll)["net"]
        rel = eng._relative(net, half_bench[h])
        vals = [v for v in rel if np.isfinite(v)]
        sizes = half_sizes[h]
        out[h] = {
            "rel_aftercost_mean": eng._r(float(np.mean(vals))) if vals else None,
            "positive": bool(vals and float(np.mean(vals)) > 0),
            "basket_size_min": int(np.min(sizes)) if sizes else 0,
            "basket_size_median": float(np.median(sizes)) if sizes else 0.0,
        }
    out["pass"] = bool(out["upper"]["positive"] and out["lower"]["positive"])
    return out


# ===========================================================================
# Verdict (frozen, 2-way) -- D-205 is the FINAL hi52 question
# ===========================================================================
_OOS_GAP = d204._OOS_GAP


def d205_verdict(
    rel_aftercost_mean: float | None, nw_t: float | None,
    both_regimes_positive: bool, gate1_null: bool, gate4_subtier: bool,
    real_aftercost_mean: float | None, breakeven_bps, realistic_cost_bps: float | None,
    pool_size_min: int, top_n: int = cfg.D205_TOP_N,
    hurdle: float = cfg.D205_DEPLOY_MIN_LIQUID_NET,
    safety_mult: float = cfg.D205_BREAKEVEN_SAFETY_MULT,
    nw_t_min: float = cfg.D205_GATE_NW_T_MIN,
) -> dict:
    """Frozen 2-way verdict for the FINAL hi52 measurement.

    TRADEABLE-EDGE  (hi52's first deployable Yol-1 form, overlay CANDIDATE only): all 5 gates
      PASS (selection-null + NW|t|>=2 after-cost + both-regimes + sub-tier + after-cost>0) AND
      liquid after-cost REAL net >= TLREF deposit hurdle AND breakeven >= safety_mult x cost.
    YINE-TRADEABLE-DEGIL (hi52 CLOSES, clean archive): after-cost <= 0 OR breakeven < safety_mult
      x cost OR liquid universe too narrow (top-15 infeasible somewhere) OR any gate FAILS.
    OOS-gap attached in BOTH branches. Decision (even TRADEABLE-EDGE) is a separate O+Cagan one.
    """
    be = float("inf") if breakeven_bps == "inf" else (
        float(breakeven_bps) if breakeven_bps is not None else None)
    cost = realistic_cost_bps if (realistic_cost_bps is not None
                                  and np.isfinite(realistic_cost_bps)) else None
    g2 = bool(nw_t is not None and np.isfinite(nw_t) and abs(nw_t) >= nw_t_min)
    g5 = bool(rel_aftercost_mean is not None and rel_aftercost_mean > 0)
    gates = {"gate1_selection_null": bool(gate1_null), "gate2_newey_west": g2,
             "gate3_cross_regime": bool(both_regimes_positive),
             "gate4_subtier_consistency": bool(gate4_subtier), "gate5_after_cost": g5}
    all_gates = all(gates.values())

    reasons = []
    if pool_size_min < top_n:
        reasons.append(f"likit-evren cok-dar (min {pool_size_min} < top-{top_n})")
    if not g5:
        reasons.append("EW_FULL_LIQUID-relatif maliyet-sonrasi <= 0")
    if be is None:
        reasons.append("breakeven hesaplanamadi")
    elif cost is not None and be < safety_mult * cost:
        reasons.append(f"breakeven < {safety_mult}x gercekci-maliyet (breakeven ~ maliyet)")
    if real_aftercost_mean is None or real_aftercost_mean < hurdle:
        reasons.append("likit-long reel maliyet-sonrasi net < TLREF-mevduat-esigi")
    for gname, gok in gates.items():
        if not gok and gname not in ("gate5_after_cost",):
            reasons.append(f"{gname} FAIL")

    be_ok = bool(be is not None and (be == float("inf") or
                 (cost is not None and be >= safety_mult * cost) or cost is None))
    hurdle_ok = bool(real_aftercost_mean is not None and real_aftercost_mean >= hurdle)
    tradeable = bool(all_gates and pool_size_min >= top_n and be_ok and hurdle_ok)

    if tradeable:
        return {"verdict": "TRADEABLE-EDGE", "gates": gates,
                "reasons": [f"5-gate hepsi-PASS AND likit-long reel net >= TLREF-esik AND "
                            f"breakeven >= {safety_mult}x maliyet AND top-{top_n} fizibil"],
                "deploy_note": ("ilk deploy-edilebilir Yol-1 hi52 formu -- overlay ADAYI; "
                                "deploy ayri O+Cagan karari, otomatik-DEGIL"),
                "oos_gap": _OOS_GAP}
    return {"verdict": "YINE-TRADEABLE-DEGIL", "gates": gates,
            "reasons": reasons or ["belirsiz -- gate/maliyet kosullari saglanmadi"],
            "close_note": ("hi52 KESIN-KAPANIR (N<=3 son): gercek-fenomen ama likit-once bile "
                           "retail-tradeable-degil; temiz-arsiv, D-204-verdict ile tutarli"),
            "oos_gap": _OOS_GAP}


# ===========================================================================
# Orchestrator
# ===========================================================================
def _series_block(series: list[float]) -> dict:
    return {**eng._mean_ci(series), "nw_t": eng._r(eng._nw_t(series))}


def run_d205(
    root: Path | str = cfg.D205_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
) -> dict:
    """Full D-205 hi52 LIKIT-ONCE test. REFUSES to run unless STAGE0_d205.json exists
    (pre-registration). Reuses the D-203 engine + D-204 cost harness + frozen D-202 panel."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; D-205 must be frozen "
            "BEFORE results (pre-registration discipline).")

    data = eng.load_d202_panel(root)
    close, value_tl, cpi = data["close"], data["value_tl"], data["cpi"]
    tlref = d204._load_tlref()

    rebal = eng.monthly_rebalance_dates(close.index, cfg.D205_COMMON_WINDOW_START,
                                        cfg.D205_COMMON_WINDOW_END)
    daily = eng.clip_clean_returns(close)
    pmat = eng._period_return_matrix(daily, rebal)
    ew_full = eng.ew_full_benchmark(pmat)

    # --- liquid universe + benchmark ---
    liq = liquid_universe_pools(value_tl, rebal)
    pools = liq["pools"]
    ew_liquid = ew_liquid_benchmark(pmat, pools, rebal)
    sizes = liq["sizes"]
    pool_size_min = int(np.min(sizes)) if sizes else 0

    # --- hi52 signal (IDENTICAL to D-203) + liquid-first baskets ---
    comp = eng._xs_rank(eng.hi52_panel(close, rebal))
    long_baskets, short_baskets, pools_list = [], [], []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        pool = pools.get(d, [])
        pools_list.append(pool)
        long_baskets.append(eng.select_top_n(d, comp, cfg.D205_TOP_N, pool=pool))
        short_baskets.append(eng.select_bottom_n(d, comp, cfg.D205_TOP_N, pool=pool))

    # --- realistic cost (REUSE D-204) ---
    cost = d204.per_stock_cost_panel(close, value_tl, rebal)
    free = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=None)
    roll = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_roll"])
    tier = d204.d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_tier"])
    short_free = d204.d204_basket_net_series(pmat, short_baskets, rebal, cost_map=None)["net"]

    # EW_FULL_LIQUID-relative (PRIMARY select-edge) + EW_FULL-relative (context)
    rel_free_liq = eng._relative(free["net"], ew_liquid)
    rel_roll_liq = eng._relative(roll["net"], ew_liquid)   # after-cost, PRIMARY
    rel_tier_liq = eng._relative(tier["net"], ew_liquid)   # after-cost cross-check
    rel_roll_full = eng._relative(roll["net"], ew_full)    # context
    real_roll = eng.to_real(roll["net"], rebal, cpi)       # absolute real (deploy hurdle)
    real_roll_mean = (float(np.nanmean([v for v in real_roll if np.isfinite(v)]))
                      if any(np.isfinite(v) for v in real_roll) else None)
    ls = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
          for a, b in zip(free["net"], short_free)]

    be = d204.breakeven_cost_bps(free["net"], ew_liquid, free["turnover"])
    eff_bps = d204.effective_flat_bps(roll["cost"], roll["turnover"])

    # --- 5 gates ---
    # gate1: selection-null (cost-free real, top-15 vs random-15 from the SAME liquid pool)
    long_real_free = eng.to_real(free["net"], rebal, cpi)
    long_real_free_mean = (np.nanmean([v for v in long_real_free if np.isfinite(v)])
                           if any(np.isfinite(v) for v in long_real_free) else float("nan"))
    null = eng.fair_selection_null(pmat, pools_list, rebal, cpi, long_real_free_mean,
                                   basket_size=cfg.D205_TOP_N)
    g1 = bool(null.get("beats_fair_null"))
    # gate2: NW|t| on the after-cost EW_FULL_LIQUID-relative series
    nw_t = eng._nw_t(rel_roll_liq)
    g2 = bool(np.isfinite(nw_t) and abs(nw_t) >= cfg.D205_GATE_NW_T_MIN)
    # gate3: cross-regime on the after-cost series
    reg = eng.regime_split(rel_roll_liq, rebal, cfg.D205_REGIME_PRIMARY)
    g3 = reg["both_positive"]
    # gate4: within-liquid sub-tier consistency (+ lower-half sample size)
    sub = subtier_consistency(comp, pmat, rebal, liq, cost["cost_roll"])
    g4 = sub["pass"]
    # gate5: after-cost EW_FULL_LIQUID-relative mean > 0
    rel_roll_liq_mean = (float(np.nanmean([v for v in rel_roll_liq if np.isfinite(v)]))
                         if any(np.isfinite(v) for v in rel_roll_liq) else None)
    g5 = bool(rel_roll_liq_mean is not None and rel_roll_liq_mean > 0)

    # --- holding period + buffer VIEW + walk-forward ---
    hold = d204.holding_period_stats(long_baskets, rebal, cfg.D205_PRIMARY_CADENCE)
    buf_baskets = liquid_buffer_baskets(comp, pools, rebal)
    buf_roll = d204.d204_basket_net_series(pmat, buf_baskets, rebal, cost_map=cost["cost_roll"])
    buf_rel = eng._relative(buf_roll["net"], ew_liquid)
    wf = d204.walk_forward(rel_roll_liq, rebal, cfg.D205_WALKFWD_SPLIT, cfg.D205_DISINFLATION_WINDOW)

    # --- deploy hurdle reproducibility guard (REUSE D-204) ---
    hurdle_calc = d204.deploy_threshold_from_tlref(tlref, cpi, rebal)
    hurdle_ok = (hurdle_calc["mean_monthly_real_carry"] is not None and
                 abs(hurdle_calc["mean_monthly_real_carry"] - cfg.D205_DEPLOY_MIN_LIQUID_NET)
                 <= cfg.D205_DEPLOY_HURDLE_TOL)
    if hurdle_ok is False and hurdle_calc["mean_monthly_real_carry"] is not None:
        raise RuntimeError(
            f"D-205 deploy hurdle drift: recomputed real TLREF carry "
            f"{hurdle_calc['mean_monthly_real_carry']} != frozen "
            f"{cfg.D205_DEPLOY_MIN_LIQUID_NET} (tol {cfg.D205_DEPLOY_HURDLE_TOL}).")

    sel_cost = selected_cost_summary(long_baskets, cost["cost_roll"], cost["roll_zero"], rebal)

    verdict = d205_verdict(
        rel_aftercost_mean=rel_roll_liq_mean, nw_t=nw_t, both_regimes_positive=g3,
        gate1_null=g1, gate4_subtier=g4, real_aftercost_mean=real_roll_mean,
        breakeven_bps=be["breakeven_bps"], realistic_cost_bps=eff_bps,
        pool_size_min=pool_size_min)

    out = {
        "directive": "D-205",
        "phase": "FAZ-1 hi52 LIKIT-ONCE (liquid-universe-first hi52 under realistic cost)",
        "config_version": cfg.D205_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.D205_PRICE_CONTENT_HASH,
        "candidate": cfg.D205_CANDIDATE_LABEL,
        "liquid_universe": {
            "adv_min_tl": cfg.D205_LIQUID_ADV_MIN_TL,
            "trailing_days": cfg.D205_LIQUID_ADV_TRAILING_DAYS,
            "pool_size_min": pool_size_min,
            "pool_size_median": float(np.median(sizes)) if sizes else 0.0,
            "pool_size_max": int(np.max(sizes)) if sizes else 0,
            "top15_feasible_frac": eng._r(np.mean([s >= cfg.D205_TOP_N for s in sizes]))
            if sizes else None,
            "healthy_ge30_frac": eng._r(np.mean([s >= cfg.D205_MIN_POOL_N for s in sizes]))
            if sizes else None,
            "n_rebal": len(rebal),
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
            "rel_liquid_costfree": _series_block(rel_free_liq),
            "rel_liquid_aftercost_roll": _series_block(rel_roll_liq),   # PRIMARY
            "rel_liquid_aftercost_tier": _series_block(rel_tier_liq),   # cross-check
            "rel_full_aftercost_roll": _series_block(rel_roll_full),    # context
            "real_aftercost_roll_mean": eng._r(real_roll_mean),
            "long_short_costfree": _series_block(ls),
        },
        "gates": {
            "gate1_selection_null": {"pass": g1, **null},
            "gate2_newey_west_aftercost": {"pass": g2, "hac_t": eng._r(nw_t),
                                           "t_min": cfg.D205_GATE_NW_T_MIN},
            "gate3_cross_regime_aftercost": {"pass": g3, "primary": reg},
            "gate4_subtier_consistency": sub,
            "gate5_after_cost": {"pass": g5, "rel_liquid_aftercost_mean": eng._r(rel_roll_liq_mean)},
            "all_pass": bool(g1 and g2 and g3 and g4 and g5),
        },
        "holding_period": hold,
        "buffer_view_enter15_exit30": {
            **_series_block(buf_rel),
            "mean_turnover": eng._r(float(np.mean([t for t in buf_roll["turnover"]
                                                   if np.isfinite(t)]))),
            "note": "secondary VIEW (turnover-reduction), NOT a deploy selection",
        },
        "stres3_oos_walk_forward": wf,
        "deploy_hurdle": {
            "frozen_min_liquid_real_net": cfg.D205_DEPLOY_MIN_LIQUID_NET,
            "recomputed": hurdle_calc,
            "reproducibility_ok": hurdle_ok,
            "liquid_long_real_aftercost_mean": eng._r(real_roll_mean),
            "beats_deposit_hurdle": bool(real_roll_mean is not None
                                         and real_roll_mean >= cfg.D205_DEPLOY_MIN_LIQUID_NET),
        },
        "verdict": verdict,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("D-205 results written to %s", out_path)
    return out

"""lab-demo-goal L2: SHORT-TERM REVERSAL -- contrarian long-loser / short-winner (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L2_short_reversal.json (FROZEN before results).
Two frozen specs: REV_1M (monthly, 21d formation) and REV_1W (weekly, 5d formation).
Contrarian: LONG bottom past-return tercile (losers), SHORT top tercile (winners).
Deployable read = long-loser-tercile vs EW-full; academic = loser-minus-winner spread.
Realistic D-207 cost (= bid-ask-bounce antidote). ALL vs LIQUID. NW-t / regime / breakeven.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l2_short_reversal.py
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import src.screening.d203_clean_universe_test as eng
import src.screening.d204_hi52_stress as d204

ROOT = Path(__file__).resolve().parents[2]
CU = ROOT / "data" / "clean_universe"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L2_short_reversal.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l2_short_reversal_results.json"
PRICES = CU / "adjusted_prices_2019_2026.parquet"
QUOTED = CU / "d207_quoted_spread_panel.parquet"

SPECS = {"REV_1M": {"cal": "monthly", "formation_days": 21},
         "REV_1W": {"cal": "weekly", "formation_days": 5}}
TERCILE = 1.0 / 3.0
MIN_CANDIDATES = 9
REGIME_SPLIT = "2022-01-01"
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
START, END = "2019-01-01", "2026-05-26"


def _r(x):
    try:
        return round(float(x), 6) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE measuring.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def weekly_rebalance_dates(index: pd.DatetimeIndex, start: str, end: str) -> list:
    idx = pd.DatetimeIndex(sorted(index))
    idx = idx[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
    if len(idx) == 0:
        return []
    iso = idx.isocalendar()
    df = pd.DataFrame({"d": idx, "y": iso["year"].values, "w": iso["week"].values})
    last = df.groupby(["y", "w"])["d"].max()
    return sorted(pd.DatetimeIndex(last.values))


def formation_panel(daily: pd.DataFrame, formation_days: int) -> pd.DataFrame:
    """Trailing compounded return over formation_days ending at each date (incl. that day)."""
    logr = np.log1p(daily)
    need = max(1, math.ceil(0.6 * formation_days))
    roll = logr.rolling(formation_days, min_periods=need).sum()
    return np.expm1(roll)


def liquid_pool(value_tl: pd.DataFrame, d: pd.Timestamp) -> set:
    win = value_tl.loc[value_tl.index <= d].tail(LIQUID_TRAILING_DAYS)
    med = win.median(skipna=True)
    return set(med[med >= LIQUID_ADV_MIN_TL].index)


def terciles_contrarian(form_row: pd.Series, pool: set | None) -> tuple[list, list]:
    """LONG = bottom tercile (losers); SHORT = top tercile (winners)."""
    items = form_row.dropna()
    if pool is not None:
        items = items[items.index.intersection(pool)]
    if len(items) < MIN_CANDIDATES:
        return [], []
    ser = items.sort_values(ascending=True)  # losers first
    k = max(1, int(round(len(ser) * TERCILE)))
    losers = sorted(ser.index[:k])
    winners = sorted(ser.index[-k:])
    return losers, winners


def nw_and_stats(rel, rebal_starts) -> dict:
    ci = eng._mean_ci(rel)
    reg = eng.regime_split(rel, rebal_starts, REGIME_SPLIT)
    pm, qm = reg.get("pre_mean"), reg.get("post_mean")
    reg["sign_stable"] = bool(pm is not None and qm is not None
                              and pm != 0 and qm != 0 and (pm > 0) == (qm > 0))
    return {"n": ci["n"], "mean": ci["mean"], "nw_t": _r(eng._nw_t(rel)),
            "ci_excludes_zero": ci["ci_excludes_zero"], "regime": reg}


def spread_stats(long_g, short_g) -> dict:
    sp = [(lg - sg) if (np.isfinite(lg) and np.isfinite(sg)) else float("nan")
          for lg, sg in zip(long_g, short_g)]
    ci = eng._mean_ci(sp)
    return {"n": ci["n"], "mean": ci["mean"], "nw_t": _r(eng._nw_t(sp)),
            "ci_excludes_zero": ci["ci_excludes_zero"]}


def run_leg(pmat, baskets, rebal, cost_map, bench, rebal_starts) -> dict:
    res = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_map)
    gross, net, turn, cost = res["gross"], res["net"], res["turnover"], res["cost"]
    sizes = [len(b) for b in baskets]
    return {
        "avg_basket_size": _r(float(np.mean([s for s in sizes if s > 0]))) if any(sizes) else None,
        "mean_turnover": _r(float(np.mean([t for t in turn if np.isfinite(t)]))),
        "realized_cost_bps": _r(d204.effective_flat_bps(cost, turn)),
        "breakeven_bps": d204.breakeven_cost_bps(gross, bench, turn)["breakeven_bps"],
        "rel_costfree": nw_and_stats(eng._relative(gross, bench), rebal_starts),
        "rel_net_after_cost": nw_and_stats(eng._relative(net, bench), rebal_starts),
        "_gross": gross,
    }


def main():
    s0 = require_stage0()
    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    value_tl = px.pivot(index="date", columns="symbol", values="value_tl").sort_index()
    quoted = pd.read_parquet(QUOTED)
    quoted.index = pd.to_datetime(quoted.index)
    daily = eng.clip_clean_returns(close)

    results = {"candidate": s0["candidate"], "stage0": str(STAGE0.relative_to(ROOT)),
               "benchmark": "EW-full per-period (honest bar)", "regime_split": REGIME_SPLIT,
               "liquid_def": f">= {LIQUID_ADV_MIN_TL:.0e} TL trailing-{LIQUID_TRAILING_DAYS}d median",
               "tercile": TERCILE, "specs": {}}

    for spec_name, spec in SPECS.items():
        if spec["cal"] == "monthly":
            rebal = eng.monthly_rebalance_dates(close.index, START, END)
        else:
            rebal = weekly_rebalance_dates(close.index, START, END)
        pmat = eng._period_return_matrix(daily, rebal)
        bench = eng.ew_full_benchmark(pmat)
        rebal_starts = list(pmat.index)
        form = formation_panel(daily, spec["formation_days"])
        cp = d204.per_stock_cost_panel(close, value_tl, rebal, quoted_panel=quoted)
        cost_map = cp["cost_roll"]
        liq_pools = {d: liquid_pool(value_tl, d) for d in rebal_starts}

        spec_res = {"n_rebal": len(rebal), "n_formation_periods": len(rebal_starts),
                    "cost_summary_frac": cp["summary"]["spread_source_frac"], "scopes": {}}
        for scope in ("ALL", "LIQUID"):
            long_b, short_b = [], []
            for d in rebal_starts:
                row = form.loc[d] if d in form.index else pd.Series(dtype=float)
                pool = None if scope == "ALL" else liq_pools[d]
                losers, winners = terciles_contrarian(row, pool)
                long_b.append(losers)
                short_b.append(winners)
            longleg = run_leg(pmat, long_b, rebal, cost_map, bench, rebal_starts)
            shortleg = run_leg(pmat, short_b, rebal, cost_map, bench, rebal_starts)
            ls = spread_stats(longleg.pop("_gross"), shortleg.pop("_gross"))
            spec_res["scopes"][scope] = {"long_losers": longleg, "short_winners": shortleg,
                                         "loser_minus_winner_spread": ls}
        results["specs"][spec_name] = spec_res

    # verdict: deployable gate = LIQUID long-loser-tercile rel-net, ANY spec
    best = None
    for spec_name, sr in results["specs"].items():
        ll = sr["scopes"]["LIQUID"]["long_losers"]["rel_net_after_cost"]
        net_pos = ll["mean"] is not None and ll["mean"] > 0
        sig = ll["nw_t"] is not None and abs(ll["nw_t"]) >= 2.0
        stable = ll["regime"]["sign_stable"]
        passes = bool(net_pos and sig and stable)
        cand = {"spec": spec_name, "net_after_cost_mean": ll["mean"], "nw_t": ll["nw_t"],
                "regime_sign_stable": stable, "net_positive": net_pos,
                "significant": sig, "passes_keep_bar": passes}
        if passes and (best is None or abs(ll["nw_t"]) > abs(best["nw_t"] or 0)):
            best = cand
    results["verdict"] = ({"verdict": "TRADEABLE-EDGE-CANDIDATE (deploy-aday)", "headline": best}
                          if best else
                          {"verdict": "REVERSAL-NOT-TRADEABLE (cost/significance-wall)",
                           "gate": "LIQUID long-loser-tercile rel-net-after-cost, any spec",
                           "note": "No spec's liquid long-loser tercile clears net-after-cost>0 "
                                   "AND NW|t|>=2 AND regime sign-stable."})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("VERDICT:", results["verdict"]["verdict"])
    for spec_name, sr in results["specs"].items():
        for scope in ("ALL", "LIQUID"):
            ll = sr["scopes"][scope]["long_losers"]
            ls = sr["scopes"][scope]["loser_minus_winner_spread"]
            cf, nt = ll["rel_costfree"], ll["rel_net_after_cost"]
            print(f"  {spec_name} {scope:6s} long-losers: size~{ll['avg_basket_size']} "
                  f"turn={ll['mean_turnover']} | costfree mean={cf['mean']} t={cf['nw_t']} "
                  f"| NET mean={nt['mean']} t={nt['nw_t']} stable={nt['regime']['sign_stable']} "
                  f"| be={ll['breakeven_bps']} realized={ll['realized_cost_bps']} "
                  f"|| L-W mean={ls['mean']} t={ls['nw_t']}")


if __name__ == "__main__":
    main()

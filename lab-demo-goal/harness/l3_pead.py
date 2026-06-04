"""lab-demo-goal L3: PEAD (post-earnings-announcement drift) -- cross-sectional monthly
SUE sort (READ-ONLY research).

Stage-0: lab-demo-goal/stage0/STAGE0_L3_pead.json (FROZEN before results).
Measurement-only, look-ahead-safe (entry from consume_from_month), committed-engine ZERO-touch.

Signal = `sue` (standardized YoY de-cumulated quarterly net-profit surprise). Each month form
the long top-SUE tercile (deployable, market-relative vs EW-full) and the academic
top-minus-bottom spread; hold K months (K=3 PRIMARY; 1,2 = drift-decay profile). Realistic
D-207 per-stock cost. ALL vs LIQUID. NW-t / regime-split / breakeven.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l3_pead.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd

import src.screening.d203_clean_universe_test as eng
import src.screening.d204_hi52_stress as d204

ROOT = Path(__file__).resolve().parents[2]
CU = ROOT / "data" / "clean_universe"
SN = ROOT / "data" / "snapshots"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L3_pead.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l3_pead_results.json"

PRICES = CU / "adjusted_prices_2019_2026.parquet"
QUOTED = CU / "d207_quoted_spread_panel.parquet"
EARN = SN / "earnings_dates.parquet"

K_PRIMARY = 3
K_PROFILE = [1, 2, 3]
TERCILE = 1.0 / 3.0
MIN_CANDIDATES = 9
REGIME_SPLIT = "2022-01-01"
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
START, END = "2019-01-01", "2026-05-26"


def _r(x) -> float | None:
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


def load_data():
    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    value_tl = px.pivot(index="date", columns="symbol", values="value_tl").sort_index()
    quoted = pd.read_parquet(QUOTED)
    quoted.index = pd.to_datetime(quoted.index)
    earn = pd.read_parquet(EARN)
    earn = earn[earn["sue"].notna()].copy()
    earn["consume_p"] = pd.PeriodIndex(earn["consume_from_month"], freq="M")
    return close, value_tl, quoted, earn


def liquid_pool(value_tl: pd.DataFrame, d: pd.Timestamp) -> set:
    win = value_tl.loc[value_tl.index <= d].tail(LIQUID_TRAILING_DAYS)
    med = win.median(skipna=True)
    return set(med[med >= LIQUID_ADV_MIN_TL].index)


def candidates_at(earn: pd.DataFrame, m_period: pd.Period, k: int) -> dict:
    """Names FRESH at month m: most-recent event with consume_p in [m-k+1, m]; value = sue."""
    lo = m_period - (k - 1)
    sub = earn[(earn["consume_p"] >= lo) & (earn["consume_p"] <= m_period)]
    if sub.empty:
        return {}
    sub = sub.sort_values("consume_p")
    last = sub.groupby("symbol").tail(1)
    return dict(zip(last["symbol"], last["sue"]))


def terciles(cand: dict, pool: set | None) -> tuple[list, list]:
    items = {s: v for s, v in cand.items() if np.isfinite(v) and (pool is None or s in pool)}
    if len(items) < MIN_CANDIDATES:
        return [], []
    ser = pd.Series(items).sort_values(ascending=False)
    n = len(ser)
    k = max(1, int(round(n * TERCILE)))
    return sorted(ser.index[:k]), sorted(ser.index[-k:])


def nw_and_stats(rel: list[float], rebal_starts: list[pd.Timestamp]) -> dict:
    ci = eng._mean_ci(rel)
    reg = eng.regime_split(rel, rebal_starts, REGIME_SPLIT)
    pm, qm = reg.get("pre_mean"), reg.get("post_mean")
    reg["sign_stable"] = bool(pm is not None and qm is not None
                              and pm != 0 and qm != 0 and (pm > 0) == (qm > 0))
    return {"n": ci["n"], "mean": ci["mean"], "nw_t": _r(eng._nw_t(rel)),
            "ci95_low": ci["ci95_low"], "ci95_high": ci["ci95_high"],
            "ci_excludes_zero": ci["ci_excludes_zero"], "regime": reg}


def spread_stats(long_g: list[float], short_g: list[float]) -> dict:
    sp = [(lg - sg) if (np.isfinite(lg) and np.isfinite(sg)) else float("nan")
          for lg, sg in zip(long_g, short_g)]
    ci = eng._mean_ci(sp)
    return {"n": ci["n"], "mean": ci["mean"], "nw_t": _r(eng._nw_t(sp)),
            "ci_excludes_zero": ci["ci_excludes_zero"]}


def run_leg(pmat, baskets, rebal, cost_map, bench, rebal_starts) -> dict:
    res = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_map)
    gross, net, turn, cost = res["gross"], res["net"], res["turnover"], res["cost"]
    rel_gross = eng._relative(gross, bench)
    rel_net = eng._relative(net, bench)
    be = d204.breakeven_cost_bps(gross, bench, turn)
    eff = d204.effective_flat_bps(cost, turn)
    sizes = [len(b) for b in baskets]
    return {
        "n_periods": int(sum(1 for g in gross if np.isfinite(g))),
        "avg_basket_size": _r(float(np.mean([s for s in sizes if s > 0]))) if any(sizes) else None,
        "mean_turnover": _r(float(np.mean([t for t in turn if np.isfinite(t)]))),
        "realized_cost_bps": _r(eff),
        "breakeven_bps": be["breakeven_bps"],
        "rel_costfree": nw_and_stats(rel_gross, rebal_starts),
        "rel_net_after_cost": nw_and_stats(rel_net, rebal_starts),
        "_gross": gross,
    }


def main():
    s0 = require_stage0()
    close, value_tl, quoted, earn = load_data()
    daily = eng.clip_clean_returns(close)
    rebal = eng.monthly_rebalance_dates(close.index, START, END)
    pmat = eng._period_return_matrix(daily, rebal)
    bench = eng.ew_full_benchmark(pmat)
    rebal_starts = list(pmat.index)  # rebal[0..n-2], the formation dates
    n_form = len(rebal_starts)

    cp = d204.per_stock_cost_panel(close, value_tl, rebal, quoted_panel=quoted)
    cost_map = cp["cost_roll"]

    # precompute liquid pools per formation date
    liq_pools = {d: liquid_pool(value_tl, d) for d in rebal_starts}

    results = {"candidate": s0["candidate"], "stage0": str(STAGE0.relative_to(ROOT)),
               "benchmark": "EW-full monthly (honest bar)", "regime_split": REGIME_SPLIT,
               "n_formation_months": n_form, "cost_summary": cp["summary"],
               "liquid_def": f">= {LIQUID_ADV_MIN_TL:.0e} TL trailing-{LIQUID_TRAILING_DAYS}d median",
               "K_primary": K_PRIMARY, "tercile": TERCILE, "by_K": {}}

    for k in K_PROFILE:
        kres = {}
        for scope in ("ALL", "LIQUID"):
            long_b, short_b = [], []
            for i, d in enumerate(rebal_starts):
                m_period = pd.Period(d, freq="M")
                cand = candidates_at(earn, m_period, k)
                pool = None if scope == "ALL" else liq_pools[d]
                lt, st = terciles(cand, pool)
                long_b.append(lt)
                short_b.append(st)
            longleg = run_leg(pmat, long_b, rebal, cost_map, bench, rebal_starts)
            shortleg = run_leg(pmat, short_b, rebal, cost_map, bench, rebal_starts)
            ls = spread_stats(longleg.pop("_gross"), shortleg.pop("_gross"))
            kres[scope] = {"long_tercile": longleg, "short_tercile": shortleg,
                           "long_minus_short_spread": ls}
        results["by_K"][str(k)] = kres

    # verdict on PRIMARY K=3 LIQUID long-tercile (deployable gate)
    prim = results["by_K"][str(K_PRIMARY)]["LIQUID"]["long_tercile"]
    rn = prim["rel_net_after_cost"]
    net_pos = rn["mean"] is not None and rn["mean"] > 0
    sig = rn["nw_t"] is not None and abs(rn["nw_t"]) >= 2.0
    stable = rn["regime"]["sign_stable"]
    passes = bool(net_pos and sig and stable)
    results["verdict"] = {
        "verdict": "TRADEABLE-EDGE-CANDIDATE (deploy-aday)" if passes
        else "PEAD-NOT-TRADEABLE (significance/cost-wall)",
        "gate": "K=3 LIQUID long-tercile rel-net-after-cost",
        "net_after_cost_mean": rn["mean"], "nw_t": rn["nw_t"],
        "regime_sign_stable": stable, "net_positive": net_pos,
        "significant": sig, "passes_keep_bar": passes,
        "note": "Deployable gate = long-only liquid tercile after D-207 realistic cost. "
                "Long-short spread reported as corroboration only."}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("VERDICT:", results["verdict"]["verdict"])
    for k in K_PROFILE:
        for scope in ("ALL", "LIQUID"):
            lt = results["by_K"][str(k)][scope]["long_tercile"]
            ls = results["by_K"][str(k)][scope]["long_minus_short_spread"]
            cf, nt = lt["rel_costfree"], lt["rel_net_after_cost"]
            print(f"  K={k} {scope:6s} long-tercile: size~{lt['avg_basket_size']} "
                  f"turn={lt['mean_turnover']} | costfree mean={cf['mean']} t={cf['nw_t']} "
                  f"| NET mean={nt['mean']} t={nt['nw_t']} stable={nt['regime']['sign_stable']} "
                  f"| be={lt['breakeven_bps']} realized={lt['realized_cost_bps']} "
                  f"|| L-S mean={ls['mean']} t={ls['nw_t']}")


if __name__ == "__main__":
    main()

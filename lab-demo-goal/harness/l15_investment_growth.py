"""lab-demo-goal L15: INVESTMENT / ASSET-GROWTH cross-sectional factor (FF CMA) -- READ-ONLY research.

Stage-0: lab-demo-goal/stage0/STAGE0_L15_investment_growth.json (FROZEN before results).
Measurement-only, look-ahead-safe (1-month lag on fundamentals), committed-engine ZERO-touch.

Signal = g = equity_t / equity_{t-12mo} - 1, the trailing-12-month BOOK-EQUITY growth (a proxy
for Fama-French total-asset growth, declared in Stage-0). The LAST untested canonical FF5 leg
(market/size/value/profitability done or in graveyard; investment/CMA = THIS).
Sign convention: LOW growth = LONG (conservative), HIGH growth = SHORT (aggressive). Each month
form the long BOTTOM-growth tercile (deployable, market-relative vs EW-full) and the academic
low-minus-high spread; hold K months (K=1 PRIMARY; 3 = turnover-reduction leg).
Realistic D-207 per-stock cost. ALL vs LIQUID. NW-t / regime-split / breakeven.

Reuses the L3/L14 monthly-cross-section machinery (d203 engine + d204 cost) identically; only the
signal builder differs (trailing equity-growth with a conservative 1-month look-ahead lag).

Run:  PYTHONPATH=. python lab-demo-goal/harness/l15_investment_growth.py
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
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L15_investment_growth.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l15_investment_growth_results.json"

PRICES = CU / "adjusted_prices_2019_2026.parquet"
QUOTED = CU / "d207_quoted_spread_panel.parquet"
FUND = CU / "fundamentals_2019_2026.parquet"

K_PRIMARY = 1
K_PROFILE = [1, 3]
TERCILE = 1.0 / 3.0
MIN_CANDIDATES = 9
LAG_MONTHS = 1
GROWTH_WINDOW_MONTHS = 12
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
    fund = pd.read_parquet(FUND)
    return close, value_tl, quoted, fund


def growth_by_month(fund: pd.DataFrame) -> dict:
    """{Period(month): {symbol: g}} where g = equity_t/equity_{t-12mo}-1, both equity>0. RANK use downstream."""
    f = fund.dropna(subset=["equity"]).copy()
    f = f[f["equity"] > 0]
    f["p"] = pd.PeriodIndex(f["month"], freq="M")
    f = f.sort_values(["symbol", "p"])
    # trailing-12-month equity growth per symbol on the monthly period index
    def _grow(g: pd.DataFrame) -> pd.Series:
        s = g.set_index("p")["equity"]
        prior = s.shift(GROWTH_WINDOW_MONTHS)
        return s / prior - 1.0
    gr = f.groupby("symbol", group_keys=True).apply(_grow)
    # gr index = (symbol, period)
    out: dict = {}
    for (sym, p), val in gr.items():
        if np.isfinite(val):
            out.setdefault(p, {})[sym] = float(val)
    return out


def liquid_pool(value_tl: pd.DataFrame, d: pd.Timestamp) -> set:
    win = value_tl.loc[value_tl.index <= d].tail(LIQUID_TRAILING_DAYS)
    med = win.median(skipna=True)
    return set(med[med >= LIQUID_ADV_MIN_TL].index)


def candidates_at(growth_map: dict, m_period: pd.Period) -> dict:
    """Look-ahead-safe: growth known as of (formation month - LAG_MONTHS)."""
    return dict(growth_map.get(m_period - LAG_MONTHS, {}))


def terciles(cand: dict, pool: set | None) -> tuple[list, list]:
    """Returns (LONG = LOW-growth conservative tercile, SHORT = HIGH-growth aggressive tercile)."""
    items = {s: v for s, v in cand.items() if np.isfinite(v) and (pool is None or s in pool)}
    if len(items) < MIN_CANDIDATES:
        return [], []
    # ascending: lowest growth first -> head = conservative LONG, tail = aggressive SHORT
    ser = pd.Series(items).sort_values(ascending=True)
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


def _hold_k(baskets: list[list], k: int) -> list[list]:
    """Turnover-reduction leg: re-sort only every k months (staggered hold), carrying the last
    formation basket forward in between -- so cost accrues k-monthly, not monthly."""
    held = []
    cur: list = []
    for i, b in enumerate(baskets):
        if i % k == 0:
            cur = b
        held.append(cur)
    return held


def main():
    s0 = require_stage0()
    close, value_tl, quoted, fund = load_data()
    growth_map = growth_by_month(fund)
    daily = eng.clip_clean_returns(close)
    rebal = eng.monthly_rebalance_dates(close.index, START, END)
    pmat = eng._period_return_matrix(daily, rebal)
    bench = eng.ew_full_benchmark(pmat)
    rebal_starts = list(pmat.index)
    n_form = len(rebal_starts)

    cp = d204.per_stock_cost_panel(close, value_tl, rebal, quoted_panel=quoted)
    cost_map = cp["cost_roll"]
    liq_pools = {d: liquid_pool(value_tl, d) for d in rebal_starts}

    results = {"candidate": s0["candidate"][:90], "stage0": str(STAGE0.relative_to(ROOT)),
               "benchmark": "EW-full monthly (honest bar)", "regime_split": REGIME_SPLIT,
               "signal": "g = equity_t/equity_{t-12mo}-1 (book-equity growth proxy for FF asset-growth), "
                         "rank-tercile, LOW-growth=LONG, look-ahead lag=1mo",
               "n_formation_months": n_form, "cost_summary": cp["summary"],
               "liquid_def": f">= {LIQUID_ADV_MIN_TL:.0e} TL trailing-{LIQUID_TRAILING_DAYS}d median",
               "lag_months": LAG_MONTHS, "growth_window_months": GROWTH_WINDOW_MONTHS,
               "K_primary": K_PRIMARY, "tercile": TERCILE,
               "growth_months_available": len(growth_map), "by_K": {}}

    for k in K_PROFILE:
        kres = {}
        for scope in ("ALL", "LIQUID"):
            long_b, short_b = [], []
            for i, d in enumerate(rebal_starts):
                m_period = pd.Period(d, freq="M")
                cand = candidates_at(growth_map, m_period)
                pool = None if scope == "ALL" else liq_pools[d]
                lt, st = terciles(cand, pool)
                long_b.append(lt)
                short_b.append(st)
            if k > 1:
                long_b = _hold_k(long_b, k)
                short_b = _hold_k(short_b, k)
            longleg = run_leg(pmat, long_b, rebal, cost_map, bench, rebal_starts)
            shortleg = run_leg(pmat, short_b, rebal, cost_map, bench, rebal_starts)
            ls = spread_stats(longleg.pop("_gross"), shortleg.pop("_gross"))
            kres[scope] = {"long_tercile": longleg, "short_tercile": shortleg,
                           "long_minus_short_spread": ls}
        results["by_K"][str(k)] = kres

    prim = results["by_K"][str(K_PRIMARY)]["LIQUID"]["long_tercile"]
    rn = prim["rel_net_after_cost"]
    net_pos = rn["mean"] is not None and rn["mean"] > 0
    sig = rn["nw_t"] is not None and abs(rn["nw_t"]) >= 2.0
    stable = rn["regime"]["sign_stable"]
    passes = bool(net_pos and sig and stable)
    results["verdict"] = {
        "verdict": "TRADEABLE-EDGE-CANDIDATE (deploy-aday)" if passes
        else "INVESTMENT-NOT-TRADEABLE (significance/cost-wall or regime sign-instability); no deployable edge",
        "gate": "K=1 LIQUID long-tercile (BOTTOM-growth conservative) rel-net-after-cost",
        "net_after_cost_mean": rn["mean"], "nw_t": rn["nw_t"],
        "regime_sign_stable": stable, "net_positive": net_pos,
        "significant": sig, "passes_keep_bar": passes,
        "no_edge_claim": (not passes),
        "note": "Deployable gate = long-only liquid LOW-growth (conservative) tercile after D-207 "
                "realistic cost. Long-short (low-minus-high) spread reported as corroboration only. "
                "ONE pre-registered equity-growth definition (no variant sweep); equity-growth is a "
                "declared PROXY for FF total-asset growth (misses debt-financed growth)."}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("VERDICT:", results["verdict"]["verdict"])
    print(f"growth months available: {len(growth_map)}; formation months: {n_form}")
    for k in K_PROFILE:
        for scope in ("ALL", "LIQUID"):
            lt = results["by_K"][str(k)][scope]["long_tercile"]
            ls = results["by_K"][str(k)][scope]["long_minus_short_spread"]
            cf, nt = lt["rel_costfree"], lt["rel_net_after_cost"]
            print(f"  K={k} {scope:6s} long(low-growth)-tercile: size~{lt['avg_basket_size']} "
                  f"turn={lt['mean_turnover']} | costfree mean={cf['mean']} t={cf['nw_t']} "
                  f"| NET mean={nt['mean']} t={nt['nw_t']} stable={nt['regime']['sign_stable']} "
                  f"| be={lt['breakeven_bps']} realized={lt['realized_cost_bps']} "
                  f"|| L-S(low-high) mean={ls['mean']} t={ls['nw_t']}")


if __name__ == "__main__":
    main()

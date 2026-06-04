"""lab-demo-goal L1: BIST100/BIST30 index-rebalance event study (READ-ONLY research).

Stage-0: lab-demo-goal/stage0/STAGE0_L1_index_rebalance.json (FROZEN before results).
Measurement-only. Look-ahead-safe. Committed engine ZERO-touch (we only IMPORT helpers).

Detects membership flips (add/delete) on the POINT-IN-TIME pit_membership panel, aligns
each event to its effective date tau0, computes market-adjusted CAR (AR = r_i - r_mkt_ew)
over frozen windows, aggregates per group (BIST100/30 x add/del) with per-event t,
date-clustered t (PRIMARY), NW-t, bootstrap CI, ALL vs LIQUID, regime split, and -- for the
only look-ahead-safe tradeable window [+1,+K] -- realistic D-207 round-trip cost + net CAR.

Run:  python lab-demo-goal/harness/l1_index_rebalance.py
"""
from __future__ import annotations
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse committed helpers (import only -- no mutation of committed engine).
import src.screening.d203_clean_universe_test as eng
import src.screening.d204_hi52_stress as d204

ROOT = Path(__file__).resolve().parents[2]
CU = ROOT / "data" / "clean_universe"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L1_index_rebalance.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l1_index_rebalance_results.json"

PRICES = CU / "adjusted_prices_2019_2026.parquet"
MEMBERSHIP = CU / "pit_membership_2019_2026.parquet"
QUOTED = CU / "d207_quoted_spread_panel.parquet"

# Frozen geometry (mirrors Stage-0; numbers live here for the lab only -- repo read-only).
WINDOWS = {
    "pre_[-10,-1]": (-10, -1),
    "pre_[-5,-1]": (-5, -1),
    "event_[0]": (0, 0),
    "post_[+1,+5]": (1, 5),
    "post_[+1,+10]": (1, 10),
    "post_[+1,+21]": (1, 21),
    "around_[-1,+1]": (-1, 1),
}
TRADEABLE_WINDOWS = ["post_[+1,+5]", "post_[+1,+10]", "post_[+1,+21]"]
REGIME_SPLIT = "2022-01-01"
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
MIN_WINDOW_COVERAGE = 0.6
COST_MIDPOINT_BPS = 35.0


def _r(x) -> float | None:
    try:
        return round(float(x), 6) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE measuring (no p-hacking).")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not marked frozen_before_results=true.")
    return s0


def load_panels() -> dict:
    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    value_tl = px.pivot(index="date", columns="symbol", values="value_tl").sort_index()
    mem = pd.read_parquet(MEMBERSHIP)
    mem["date"] = pd.to_datetime(mem["date"]).dt.normalize()
    quoted = pd.read_parquet(QUOTED)
    quoted.index = pd.to_datetime(quoted.index)
    return {"close": close, "value_tl": value_tl, "mem": mem, "quoted": quoted}


def detect_events(mem: pd.DataFrame, col: str, trading_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Return events DataFrame: symbol, tau0 (effective date snapped to a trading day),
    direction in {add, del}. A flip requires a non-NaN prior observation (no panel-birth
    artifacts). tau0 is snapped FORWARD to the first trading day >= flip date."""
    m = mem[["date", "symbol", col]].dropna(subset=[col]).copy()
    m = m.sort_values(["symbol", "date"])
    g = m.groupby("symbol")[col]
    prev = g.shift(1)
    cur = m[col].astype(bool)
    prevb = prev.astype("boolean")  # keeps NaN as <NA>
    is_add = (prevb == False) & cur  # noqa: E712
    is_del = (prevb == True) & (~cur)  # noqa: E712
    m["direction"] = np.where(is_add.fillna(False), "add",
                              np.where(is_del.fillna(False), "del", ""))
    ev = m[m["direction"] != ""][["date", "symbol", "direction"]].copy()
    # snap flip date forward to a trading day present in the price index
    ti = pd.DatetimeIndex(trading_index)
    pos = ti.searchsorted(ev["date"].values, side="left")
    ev = ev[pos < len(ti)].copy()
    pos = pos[pos < len(ti)]
    ev["tau0"] = ti[pos]
    return ev.reset_index(drop=True)


def car_for_event(ar_sym: np.ndarray, tau0_pos: int, lo: int, hi: int, n_days: int) -> tuple:
    a, b = tau0_pos + lo, tau0_pos + hi
    if a < 0 or b >= n_days:
        return float("nan"), 0
    seg = ar_sym[a:b + 1]
    finite = np.isfinite(seg)
    need = max(1, math.ceil(MIN_WINDOW_COVERAGE * len(seg)))
    if finite.sum() < need:
        return float("nan"), int(finite.sum())
    return float(np.nansum(seg)), int(finite.sum())


def liquid_at(value_tl: pd.DataFrame, sym: str, tau0_pos: int) -> bool:
    if sym not in value_tl.columns:
        return False
    lo = max(0, tau0_pos - LIQUID_TRAILING_DAYS + 1)
    win = value_tl[sym].values[lo:tau0_pos + 1]
    win = win[np.isfinite(win)]
    if len(win) == 0:
        return False
    return float(np.median(win)) >= LIQUID_ADV_MIN_TL


def date_clustered_t(per_event: list[dict], key: str = "car") -> dict:
    """Collapse events to one mean per effective-date, then t across dates (PRIMARY).
    Also returns NW-t on the date-ordered series (reuse committed _nw_t)."""
    by_date: dict[pd.Timestamp, list[float]] = {}
    for e in per_event:
        v = e[key]
        if np.isfinite(v):
            by_date.setdefault(e["tau0"], []).append(v)
    dates = sorted(by_date)
    means = [float(np.mean(by_date[d])) for d in dates]
    n = len(means)
    if n < 2:
        return {"n_dates": n, "mean_of_date_means": _r(means[0]) if n else None,
                "t": None, "nw_t": None}
    arr = np.array(means, dtype=float)
    t = float(np.mean(arr) / (np.std(arr, ddof=1) / math.sqrt(n)))
    nw = eng._nw_t(list(arr))  # date-ordered series
    return {"n_dates": n, "mean_of_date_means": _r(float(np.mean(arr))),
            "t": _r(t), "nw_t": _r(nw)}


def per_event_stats(cars: list[float]) -> dict:
    arr = np.array([c for c in cars if np.isfinite(c)], dtype=float)
    n = len(arr)
    if n < 2:
        return {"n": n, "mean": _r(arr[0]) if n else None, "t": None}
    t = float(np.mean(arr) / (np.std(arr, ddof=1) / math.sqrt(n)))
    return {"n": n, "mean": _r(float(np.mean(arr))), "t": _r(t)}


def regime_means(per_event: list[dict], split: str) -> dict:
    cut = pd.Timestamp(split)
    pre = [e["car"] for e in per_event if e["tau0"] < cut and np.isfinite(e["car"])]
    post = [e["car"] for e in per_event if e["tau0"] >= cut and np.isfinite(e["car"])]
    pre_m = float(np.mean(pre)) if pre else float("nan")
    post_m = float(np.mean(post)) if post else float("nan")
    same_sign = bool(np.isfinite(pre_m) and np.isfinite(post_m)
                     and (pre_m > 0) == (post_m > 0) and pre_m != 0 and post_m != 0)
    return {"pre_mean": _r(pre_m), "post_mean": _r(post_m),
            "pre_n": len(pre), "post_n": len(post), "sign_stable": same_sign}


def analyze_group(events: pd.DataFrame, ar: dict, value_tl: pd.DataFrame,
                  trading_index: pd.DatetimeIndex, cost_map: dict) -> dict:
    """events: rows for one (index,direction) group. ar: {sym: AR np.array aligned to
    trading_index}. Returns per-window stats for ALL and LIQUID, plus net-cost for
    tradeable windows."""
    n_days = len(trading_index)
    pos_of = {d: i for i, d in enumerate(trading_index)}
    out = {"n_events": int(len(events)), "windows": {}}
    # precompute per-event CARs for each window + liquid flag + tau0
    rows = []
    for _, e in events.iterrows():
        sym, tau0 = e["symbol"], e["tau0"]
        if sym not in ar or tau0 not in pos_of:
            continue
        p = pos_of[tau0]
        rec = {"symbol": sym, "tau0": tau0, "liquid": liquid_at(value_tl, sym, p),
               "cars": {}}
        for wname, (lo, hi) in WINDOWS.items():
            c, _nd = car_for_event(ar[sym], p, lo, hi, n_days)
            rec["cars"][wname] = c
        rows.append(rec)
    for wname in WINDOWS:
        for scope in ("ALL", "LIQUID"):
            sel = [r for r in rows if (scope == "ALL" or r["liquid"])]
            cars = [r["cars"][wname] for r in sel]
            pe = [{"tau0": r["tau0"], "car": r["cars"][wname]} for r in sel]
            stats = per_event_stats(cars)
            dct = date_clustered_t(pe)
            reg = regime_means(pe, REGIME_SPLIT)
            ci = eng._mean_ci([c for c in cars if np.isfinite(c)])
            entry = {"per_event": stats, "date_clustered": dct, "regime": reg,
                     "ci": {"ci95_low": ci["ci95_low"], "ci95_high": ci["ci95_high"],
                            "excludes_zero": ci["ci_excludes_zero"]}}
            if wname in TRADEABLE_WINDOWS:
                entry["cost"] = tradeable_cost(sel, wname, cost_map)
            out["windows"].setdefault(wname, {})[scope] = entry
    return out


def tradeable_cost(sel: list[dict], wname: str, cost_map: dict) -> dict:
    """One round-trip per event (enter tau0+1, exit tau0+K). Net CAR = gross - round_trip.
    cost_map[date][sym] = realistic D-207 round-trip fraction at the ENTRY date."""
    rts, nets, gross = [], [], []
    for r in sel:
        c = r["cars"][wname]
        if not np.isfinite(c):
            continue
        # entry date = first trading day after tau0 -> use tau0's cost row as proxy
        cmap = cost_map.get(r["tau0"], {})
        rt = cmap.get(r["symbol"], np.nan)
        gross.append(c)
        if np.isfinite(rt):
            rts.append(rt)
            nets.append(c - rt)
    if not gross:
        return {"n": 0}
    net_arr = np.array(nets, dtype=float) if nets else np.array([])
    res = {
        "n": len(gross),
        "gross_mean": _r(float(np.mean(gross))),
        "median_round_trip_bps": _r(float(np.median(rts)) * 1e4) if rts else None,
        "mean_round_trip_bps": _r(float(np.mean(rts)) * 1e4) if rts else None,
        "net_mean_after_cost": _r(float(np.mean(net_arr))) if len(net_arr) else None,
        "net_positive": bool(len(net_arr) and float(np.mean(net_arr)) > 0),
    }
    if len(net_arr) >= 2:
        res["net_t"] = _r(float(np.mean(net_arr) / (np.std(net_arr, ddof=1) / math.sqrt(len(net_arr)))))
    return res


def verdict(results: dict) -> dict:
    """Keep-bar (FROZEN): TRADEABLE-aday requires, on LIQUID, a [+1,+K] window with
    net-after-cost in a deployable direction AND date-clustered |t|>=2 AND regime
    sign-stable. Else VIEW / wall."""
    best = None
    for grp, gd in results["groups"].items():
        for wname in TRADEABLE_WINDOWS:
            liq = gd["windows"].get(wname, {}).get("LIQUID")
            if not liq:
                continue
            cost = liq.get("cost", {})
            dct = liq["date_clustered"]
            reg = liq["regime"]
            t = dct.get("t")
            net_pos = cost.get("net_positive", False)
            sig = (t is not None and abs(t) >= 2.0)
            ok = bool(net_pos and sig and reg["sign_stable"])
            cand = {"group": grp, "window": wname,
                    "net_mean_after_cost": cost.get("net_mean_after_cost"),
                    "date_clustered_t": t, "regime_sign_stable": reg["sign_stable"],
                    "net_positive": net_pos, "passes_keep_bar": ok}
            if ok and (best is None or abs(t) > abs(best["date_clustered_t"] or 0)):
                best = cand
    if best:
        return {"verdict": "TRADEABLE-EDGE-CANDIDATE", "headline": best,
                "note": "look-ahead-safe [+1,+K] window clears keep-bar on liquid universe."}
    return {"verdict": "INDEX-EFFECT-VIEW (not a deployable tradeable edge)",
            "note": "No look-ahead-safe [+1,+K] liquid window clears keep-bar (net-after-cost "
                    "positive AND date-clustered |t|>=2 AND regime sign-stable). Pre-effective "
                    "windows are DESCRIPTIVE only. Consistent with honest pre-declared expectation "
                    "(index-effect MODERATE-but-decaying; volume>price; peaks effective day)."}


def main() -> None:
    s0 = require_stage0()
    P = load_panels()
    close, value_tl, mem, quoted = P["close"], P["value_tl"], P["mem"], P["quoted"]
    trading_index = close.index
    daily = eng.clip_clean_returns(close)
    mkt_ew = daily.mean(axis=1, skipna=True)  # honest EW-full daily bar
    # AR per symbol aligned to trading_index
    ar = {sym: (daily[sym] - mkt_ew).values for sym in daily.columns}

    groups = {}
    entry_dates = set()
    raw_counts = {}
    for index_col, label in (("in_bist100", "BIST100"), ("in_bist30", "BIST30")):
        ev = detect_events(mem, index_col, trading_index)
        raw_counts[label] = {"add": int((ev["direction"] == "add").sum()),
                             "del": int((ev["direction"] == "del").sum())}
        for direction in ("add", "del"):
            sub = ev[ev["direction"] == direction]
            entry_dates.update(sub["tau0"].tolist())
            groups[f"{label}-{direction}"] = sub

    # realistic D-207 cost panel at all event effective dates (entry proxy)
    rebal = sorted(entry_dates)
    cp = d204.per_stock_cost_panel(close, value_tl, rebal, quoted_panel=quoted)
    cost_map = cp["cost_roll"]

    results = {"candidate": s0["candidate"], "stage0": str(STAGE0.relative_to(ROOT)),
               "raw_event_counts": raw_counts, "cost_summary": cp["summary"],
               "benchmark": "EW-full daily (honest bar)", "regime_split": REGIME_SPLIT,
               "windows_def": {k: list(v) for k, v in WINDOWS.items()},
               "tradeable_windows": TRADEABLE_WINDOWS,
               "liquid_def": f">= {LIQUID_ADV_MIN_TL:.0e} TL trailing-{LIQUID_TRAILING_DAYS}d median value_tl",
               "groups": {}}
    for gname, gev in groups.items():
        results["groups"][gname] = analyze_group(gev, ar, value_tl, trading_index, cost_map)
    results["verdict"] = verdict(results)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("raw_event_counts:", raw_counts)
    print("VERDICT:", results["verdict"]["verdict"])
    # quick human-readable scan of the key reads
    for gname, gd in results["groups"].items():
        for wname in ["pre_[-10,-1]", "event_[0]", "post_[+1,+5]", "post_[+1,+10]"]:
            liq = gd["windows"][wname]["LIQUID"]
            alld = gd["windows"][wname]["ALL"]
            print(f"  {gname:14s} {wname:14s} "
                  f"ALL n={alld['per_event']['n']:>3} mean={alld['per_event']['mean']} "
                  f"dt={alld['date_clustered']['t']} | "
                  f"LIQ n={liq['per_event']['n']:>3} mean={liq['per_event']['mean']} "
                  f"dt={liq['date_clustered']['t']}")


if __name__ == "__main__":
    main()

"""lab-demo-goal L6: MACRO-EVENT (CPI-release) event-window study (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L6_macro_event.json (FROZEN before results).

Unconditional CPI-release event-window on XU100 (PRIMARY, investable) + EW-full (SECONDARY).
NO surprise dimension exists in the data (event DATES only) -> this is the unconditional CEILING.
FIXED windows (no search): pre[-5,-1], event[0] (contaminated/descriptive), post[+1,+5]
(look-ahead-safe tradeable, enter t0+1), post-wide[+1,+10] (absorbs +/-1-2d proxy-date smear).
Primary stat = event-clustered t on per-event CAR; NW-t (HAC) cross-check; regime split 2022-01;
Bonferroni across the 4 fixed windows; gross-first (cost only on a gross-significant positive window).

Run:  PYTHONPATH=. python lab-demo-goal/harness/l6_macro_event.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import src.screening.d203_clean_universe_test as eng

ROOT = Path(__file__).resolve().parents[2]
CU = ROOT / "data" / "clean_universe"
SN = ROOT / "data" / "snapshots"
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L6_macro_event.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l6_macro_event_results.json"
PRICES = CU / "adjusted_prices_2019_2026.parquet"
XU100 = SN / "exposure_d187_xu100.parquet"
EVENTS = SN / "macro_event_dates.parquet"

REGIME_SPLIT = "2022-01-01"
WINDOWS = {"pre": (-5, -1), "event": (0, 0), "post_tight": (1, 5), "post_wide": (1, 10)}
TRADEABLE = {"post_tight", "post_wide"}
N_HEADLINE = 4
BONF = 0.05 / N_HEADLINE
INDEX_ROUNDTRIP_BPS = 40.0  # conservative upper bound (index futures/ETF typically cheaper)


def _r(x):
    try:
        return round(float(x), 8) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE measuring.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def event_car(ar: np.ndarray, positions: np.ndarray, lo: int, hi: int) -> list[float]:
    """Per-event CAR = sum of AR over [tau0+lo, tau0+hi], dropping events that run off either end."""
    n = len(ar)
    out = []
    for p in positions:
        a, b = p + lo, p + hi
        if a < 0 or b >= n:
            continue
        seg = ar[a:b + 1]
        if np.all(np.isfinite(seg)):
            out.append(float(np.sum(seg)))
    return out


def post_daily_ar(ar: np.ndarray, positions: np.ndarray, lo: int, hi: int) -> list[float]:
    n = len(ar)
    out = []
    for p in positions:
        a, b = p + lo, p + hi
        if a < 0 or b >= n:
            continue
        for v in ar[a:b + 1]:
            if np.isfinite(v):
                out.append(float(v))
    return out


def cluster_stats(cars: list[float]) -> dict:
    arr = np.asarray(cars, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = len(arr)
    if n < 3:
        return {"n_events": n, "mean_car": None, "sd_car": None, "clustered_t": None,
                "p_raw": None, "survives_bonf": None}
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    se = sd / np.sqrt(n) if sd > 0 else float("nan")
    t = mean / se if np.isfinite(se) and se > 0 else float("nan")
    p = float(2 * stats.t.sf(abs(t), df=n - 1)) if np.isfinite(t) else float("nan")
    return {"n_events": n, "mean_car": _r(mean), "sd_car": _r(sd), "clustered_t": _r(t),
            "p_raw": _r(p), "survives_bonf": bool(np.isfinite(p) and p < BONF)}


def regime_sign(cars_pre: list[float], cars_post: list[float]) -> dict:
    def m(c):
        a = np.asarray(c, dtype=float)
        a = a[np.isfinite(a)]
        return float(np.mean(a)) if len(a) >= 3 else None
    pm, qm = m(cars_pre), m(cars_post)
    stable = bool(pm is not None and qm is not None and pm != 0 and qm != 0 and (pm > 0) == (qm > 0))
    return {"pre_mean_car": _r(pm) if pm is not None else None,
            "post_mean_car": _r(qm) if qm is not None else None, "sign_stable": stable}


def align_positions(idx: pd.DatetimeIndex, event_dates: pd.DatetimeIndex) -> np.ndarray:
    """tau0 = first trading day on-or-after each event_date in `idx`."""
    pos = idx.searchsorted(event_dates, side="left")
    return np.asarray([p for p in pos if 0 <= p < len(idx)], dtype=int)


def analyse(ret: pd.Series, label: str, ev_dates: pd.DatetimeIndex) -> dict:
    idx = ret.index
    r = ret.values.astype(float)
    mu = float(np.nanmean(r))
    ar = r - mu  # abnormal vs unconditional mean (market-timing-overlay null)
    positions = align_positions(idx, ev_dates)
    cut = pd.Timestamp(REGIME_SPLIT)
    pre_pos = positions[idx[positions] < cut]
    post_pos = positions[idx[positions] >= cut]

    out = {"series": label, "n_days": int(len(ret)), "mean_daily_return": _r(mu),
           "n_events_aligned": int(len(positions)), "windows": {}}
    vol_other_mask = np.ones(len(r), dtype=bool)
    event_day_pos = positions[(positions >= 0) & (positions < len(r))]
    vol_other_mask[event_day_pos] = False

    for wname, (lo, hi) in WINDOWS.items():
        cars = event_car(ar, positions, lo, hi)
        cs = cluster_stats(cars)
        cs["window"] = [lo, hi]
        cs["tradeable_lookaheadsafe"] = wname in TRADEABLE
        # NW-t HAC cross-check on the daily AR series within the window
        daily = post_daily_ar(ar, positions, lo, hi)
        cs["nw_t_daily_crosscheck"] = _r(eng._nw_t(daily))
        cs["regime"] = regime_sign(event_car(ar, pre_pos, lo, hi),
                                    event_car(ar, post_pos, lo, hi))
        # gross-first cost application (only meaningful for tradeable positive-significant windows)
        if wname in TRADEABLE and cs["mean_car"] is not None:
            net = cs["mean_car"] - INDEX_ROUNDTRIP_BPS / 1e4
            cs["net_car_after_index_cost"] = _r(net)
            cs["positive_and_significant_gross"] = bool(
                cs["mean_car"] > 0 and cs["clustered_t"] is not None and abs(cs["clustered_t"]) >= 2.0)
        out["windows"][wname] = cs

    # descriptive volatility signature: mean |AR| on event[0] vs other days
    abs_ar = np.abs(ar)
    out["volatility_view"] = {
        "mean_abs_ar_event_day": _r(float(np.nanmean(abs_ar[event_day_pos]))) if len(event_day_pos) else None,
        "mean_abs_ar_other_days": _r(float(np.nanmean(abs_ar[vol_other_mask]))),
        "note": "DESCRIPTIVE information-event signature; not a tradeable directional claim.",
    }
    return out


def verdict(primary: dict) -> dict:
    deployable = []
    for wname in TRADEABLE:
        w = primary["windows"].get(wname, {})
        if (w.get("mean_car") is not None and w["mean_car"] > 0
                and w.get("clustered_t") is not None and abs(w["clustered_t"]) >= 2.0
                and w.get("survives_bonf") and w.get("regime", {}).get("sign_stable")
                and w.get("net_car_after_index_cost") is not None
                and w["net_car_after_index_cost"] > 0):
            deployable.append(wname)
    if deployable:
        v = "TRADEABLE-EDGE (deploy-candidate) -- UNEXPECTED, verify before any use"
    else:
        v = "DESCRIPTIVE-VIEW (no deployable macro-event directional edge)"
    return {
        "verdict": v,
        "deployable_windows": deployable,
        "note": "Unconditional CPI-release window only -- the data carries NO surprise magnitude "
                "(dates only) and CPI dates are a +/-1-2d rule-proxy. A null bounds the unconditional "
                "effect and motivates exact-date + actual/forecast-surprise acquisition for a future "
                "surprise-conditional test. Consistent with source meta.json (edge-prior WEAK) and the "
                "program SUMMARY (value is in NEW DATA, not new factors on existing data).",
    }


def main():
    s0 = require_stage0()
    ev = pd.read_parquet(EVENTS)
    cpi = ev[ev["event_type"] == "cpi_release"].copy()
    cpi_dates = pd.to_datetime(cpi["event_date"]).sort_values()
    ppk_n = int((ev["event_type"] == "ppk_decision").sum())

    xu = pd.read_parquet(XU100)
    xu["date"] = pd.to_datetime(xu["date"])
    xser = pd.Series(xu["value"].values, index=xu["date"]).sort_index()
    xret = xser.pct_change().dropna()

    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    daily = eng.clip_clean_returns(close)
    ewret = daily.mean(axis=1, skipna=True).dropna()

    results = {
        "candidate": s0["candidate"], "stage0": str(STAGE0.relative_to(ROOT)),
        "data": {"n_cpi_events": int(len(cpi_dates)), "ppk_events_excluded_from_inference": ppk_n,
                 "event_date_exact": False, "index_roundtrip_bps_conservative": INDEX_ROUNDTRIP_BPS},
        "multiple_testing": {"n_headline_windows": N_HEADLINE, "bonferroni_p": BONF},
        "windows_fixed": {k: list(v) for k, v in WINDOWS.items()},
        "PRIMARY_xu100": analyse(xret, "XU100", cpi_dates),
        "SECONDARY_ew_full": analyse(ewret, "EW-full", cpi_dates),
    }
    results["verdict"] = verdict(results["PRIMARY_xu100"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("VERDICT:", results["verdict"]["verdict"])
    print(f"CPI events={len(cpi_dates)}  PPK(excluded)={ppk_n}  Bonferroni p<{BONF:.4f}")
    for label in ("PRIMARY_xu100", "SECONDARY_ew_full"):
        sc = results[label]
        print(f"--- {sc['series']} (n_days={sc['n_days']}, events_aligned={sc['n_events_aligned']}) ---")
        for wname in WINDOWS:
            w = sc["windows"][wname]
            flag = "*BONF*" if w.get("survives_bonf") else ""
            net = w.get("net_car_after_index_cost")
            nets = f" net={net}" if net is not None else ""
            print(f"  {wname:10s} {w['window']} CAR={w['mean_car']} t={w['clustered_t']} "
                  f"p={w['p_raw']} nwt={w['nw_t_daily_crosscheck']} stable={w['regime']['sign_stable']}{nets} {flag}")
        vv = sc["volatility_view"]
        print(f"  vol: event|AR|={vv['mean_abs_ar_event_day']} other|AR|={vv['mean_abs_ar_other_days']}")


if __name__ == "__main__":
    main()

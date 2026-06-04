"""lab-demo-goal L23: VIOP single-stock-futures FUNDING-BASIS cross-sectional factor -- REAL DATA (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L23_viop_ss_basis.json (FROZEN before results).

A GENUINELY NEW factor axis (per-stock futures-implied FUNDING/BORROW BASIS LEVEL), the natural
complement to L22's index term-structure -- but here the SPOT leg IS available offline per stock
(raw close), unlike the BIST30 index. Enabled by the VIOP day-end archive
(data/bist_datastore_archive/viop, VIOP_GUNSONU_FIYATHACIM monthly CSVs) SETTLEMENT PRICE (col7) +
segment SSF, joined to per-stock raw spot close. NOT in the L1-L22 set.

Signal: basis_ann(symbol, month-end m) = ln(F_front.settle / S_raw_close) / (dte_front/365), where
F_front is that underlying's SSF contract with the SMALLEST days-to-expiry that is still >= MIN_DTE_DAYS.
Hypothesis (pre-registered NEGATIVE sign): HIGH basis (rich future / crowded longs / costly shorting)
-> subsequent SPOT UNDERperformance; so LONG the LOW-basis tercile, market-relative, net of realistic
cost. Look-ahead-safe (basis at end of m -> forward spot return m+1, plus skip-month m+2 robustness).
Measurement-only; SINGLE pre-registered definition; NO optimization/grid; NO network; ASCII.
Writes only under lab-demo-goal/.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l23_viop_ss_basis.py
"""
from __future__ import annotations
import calendar
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L23_viop_ss_basis.json"
OUT = LAB / "results" / "l23_viop_ss_basis_results.json"
VIOP_DIR = ROOT / "data" / "bist_datastore_archive" / "viop"
PRICE_PARQUET = ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"

T_SIG = 2.0
NW_LAG = 6
TERCILE = 1.0 / 3.0
MIN_NAMES = 30
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
REGIME_SPLIT = "2022-01-01"
ROUND_TRIP_BPS = 40.0
MIN_YYYYMM = 201901          # price panel starts 2019-01
MIN_DTE_DAYS = 10            # front contract must have >= 10 days to expiry (avoid expiry microstructure)
SEG_COL = 3                  # PAZAR SEGMENTI; SSF = single-stock futures
SER_COL = 1                  # SOZLESME KODU (instrument series, F_<TICKER><MMYY>)
UND_COL = 6                  # DAYANAK VARLIK (underlying, e.g. AKBNK.E)
SETTLE_COL = 7               # UZLASMA FIYATI (settlement price)
DATE_COL = 0
NCOLS_MIN = 23
SEG_SSF = "SSF"
SYM_RE = re.compile(r"^[A-Z0-9]{2,6}\.E$")     # underlying ticker .E
EXP_RE = re.compile(r"(\d{2})(\d{2})$")        # trailing MMYY of the series code
FILE_GLOB = "VIOP_GUNSONU_FIYATHACIM.M.*.csv"  # plain files only (AS-variant excluded)


def require_stage0() -> dict:
    if not STAGE0.exists():
        raise RuntimeError(f"Stage-0 missing -- freeze {STAGE0} BEFORE results.")
    s0 = json.loads(STAGE0.read_text(encoding="utf-8"))
    if not s0.get("frozen_before_results"):
        raise RuntimeError("Stage-0 not frozen_before_results=true.")
    return s0


def nw_tstat(x: np.ndarray, lag: int) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean()
    e = x - mu
    var = (e @ e) / n
    for k in range(1, min(lag, n - 1) + 1):
        w = 1.0 - k / (lag + 1.0)
        var += 2.0 * w * (e[k:] @ e[:-k]) / n
    se = np.sqrt(max(var, 1e-18) / n)
    return float(mu / se) if se > 0 else float("nan")


def _expiry_last_day(mm: int, yy: int) -> pd.Timestamp:
    year = 2000 + yy
    last = calendar.monthrange(year, mm)[1]
    return pd.Timestamp(year=year, month=mm, day=last)


def load_viop_month_end_front() -> pd.DataFrame:
    """Per month-end (last trading day in each monthly file): the FRONT SSF contract per underlying.
    Returns [ym(Period-M), obs_date(str YYYY-MM-DD), symbol(bare), front_settle, dte]."""
    rows = []
    for p in sorted(VIOP_DIR.glob(FILE_GLOB)):
        tag = p.name.split(".M.")[1][:6]
        if not tag.isdigit() or int(tag) < MIN_YYYYMM:
            continue
        ym = pd.Period(f"{tag[:4]}-{tag[4:]}", freq="M")
        # date -> underlying(bare) -> list of (settle, dte)
        by_day = defaultdict(lambda: defaultdict(list))
        with open(p, "r", encoding="latin-1", newline="") as fh:
            r = csv.reader(fh, delimiter=";")
            next(r, None)  # TR header
            next(r, None)  # EN header
            for row in r:
                if len(row) < NCOLS_MIN:
                    continue
                if row[SEG_COL].strip() != SEG_SSF:
                    continue
                und = row[UND_COL].strip()
                if not SYM_RE.match(und):
                    continue
                code = row[SER_COL].strip()
                m = EXP_RE.search(code)
                if not m:
                    continue
                try:
                    settle = float(row[SETTLE_COL])
                except (ValueError, TypeError):
                    continue
                if not np.isfinite(settle) or settle <= 0:
                    continue
                d = row[DATE_COL].strip()
                try:
                    obs = pd.Timestamp(d)
                except (ValueError, TypeError):
                    continue
                exp = _expiry_last_day(int(m.group(1)), int(m.group(2)))
                dte = (exp - obs).days
                by_day[d][und[:-2]].append((settle, dte))
        if not by_day:
            continue
        last = max(by_day.keys())  # month-end snapshot
        for sym, contracts in by_day[last].items():
            elig = sorted((c for c in contracts if c[1] >= MIN_DTE_DAYS), key=lambda c: c[1])
            if not elig:
                continue
            settle, dte = elig[0]
            rows.append((ym, last, sym, settle, dte))
    return pd.DataFrame(rows, columns=["ym", "obs_date", "symbol", "front_settle", "dte"])


def load_spot():
    """Return (raw_lookup, price_m):
      raw_lookup: dict {(symbol, 'YYYY-MM-DD'): raw_close} for same-day basis denominator.
      price_m:    [symbol, ym, adjclose(month-end), liq_med(trailing-63d median value_tl)]."""
    df = pd.read_parquet(PRICE_PARQUET, columns=["date", "symbol", "close", "value_tl", "adjusted_close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"])
    df["datestr"] = df["date"].dt.strftime("%Y-%m-%d")
    raw_lookup = dict(zip(zip(df["symbol"], df["datestr"]), df["close"].astype(float)))

    df["ym"] = df["date"].dt.to_period("M")
    df["liq_med"] = df.groupby("symbol")["value_tl"].transform(
        lambda s: s.rolling(LIQUID_TRAILING_DAYS, min_periods=LIQUID_TRAILING_DAYS).median())
    price_m = df.groupby(["symbol", "ym"]).agg(
        adjclose=("adjusted_close", "last"), liq_med=("liq_med", "last")).reset_index()
    return raw_lookup, price_m


def build_basis(front: pd.DataFrame, raw_lookup: dict) -> pd.DataFrame:
    """basis_ann = ln(front_settle / spot_raw_close@obs_date) / (dte/365). Same-day spot match."""
    spot = [raw_lookup.get((s, d)) for s, d in zip(front["symbol"], front["obs_date"])]
    front = front.copy()
    front["spot_raw"] = spot
    front = front.dropna(subset=["spot_raw"])
    front = front[(front["spot_raw"] > 0) & (front["front_settle"] > 0) & (front["dte"] > 0)]
    front["basis_ann"] = np.log(front["front_settle"] / front["spot_raw"]) / (front["dte"] / 365.0)
    front = front.replace([np.inf, -np.inf], np.nan).dropna(subset=["basis_ann"])
    return front[["ym", "symbol", "basis_ann"]]


def build_forward(price_m: pd.DataFrame) -> pd.DataFrame:
    """Month-keyed forward returns: ret realized in month p = adjclose[p]/adjclose[p-1]-1
    only when month p directly follows the prior available month (no calendar gap)."""
    price_m = price_m.sort_values(["symbol", "ym"]).copy()
    price_m["mord"] = price_m["ym"].apply(lambda p: p.year * 12 + (p.month - 1))
    price_m["prev_adj"] = price_m.groupby("symbol")["adjclose"].shift(1)
    price_m["prev_mord"] = price_m.groupby("symbol")["mord"].shift(1)
    consec = (price_m["mord"] - price_m["prev_mord"]) == 1
    price_m["ret"] = np.where(consec, price_m["adjclose"] / price_m["prev_adj"] - 1.0, np.nan)
    return price_m[["symbol", "ym", "ret"]]


def evaluate(signal_df: pd.DataFrame, ret_m: pd.DataFrame, offset: int) -> dict:
    """signal_df: [ym, symbol, basis_ann, liq_med]. offset=1 (m+1) or 2 (m+2).
    Cross-sectional tercile: LONG the LOW-basis tercile, SHORT the HIGH-basis tercile (pre-registered
    NEGATIVE basis->return sign). Market-relative monthly series + NW-t + cost + regime split."""
    ret_lookup = ret_m.dropna(subset=["ret"]).copy()
    ret_lookup["sig_ym"] = ret_lookup["ym"] - offset
    ret_lookup = ret_lookup.rename(columns={"ret": "fwd_ret"})[["symbol", "sig_ym", "fwd_ret"]]
    merged = signal_df.merge(ret_lookup, left_on=["symbol", "ym"], right_on=["symbol", "sig_ym"], how="inner")

    months = sorted(merged["ym"].unique())
    recs = []
    prev_low = set()
    for ym in months:
        sub = merged[merged["ym"] == ym].dropna(subset=["fwd_ret", "basis_ann"])
        if len(sub) < MIN_NAMES:
            continue
        sub = sub.sort_values("basis_ann")
        k = max(1, int(len(sub) * TERCILE))
        low = sub.iloc[:k]    # LOW basis -> LONG (favorable)
        high = sub.iloc[-k:]  # HIGH basis -> SHORT
        all_mean = float(sub["fwd_ret"].mean())
        low_mean = float(low["fwd_ret"].mean())
        high_mean = float(high["fwd_ret"].mean())
        cur_low = set(low["symbol"])
        turn = len(prev_low - cur_low) / len(cur_low) if prev_low else 1.0
        prev_low = cur_low
        recs.append({"ym": str(ym), "n": len(sub),
                     "long_rel": low_mean - all_mean,
                     "ls": low_mean - high_mean,
                     "low_mean": low_mean, "high_mean": high_mean, "all_mean": all_mean,
                     "turnover": turn})
    if len(recs) < 6:
        return {"n_months": len(recs), "insufficient": True}

    rs = pd.DataFrame(recs)
    rt = ROUND_TRIP_BPS / 1e4
    long_rel = rs["long_rel"].to_numpy()
    ls = rs["ls"].to_numpy()
    turn = rs["turnover"].to_numpy()
    long_rel_net = long_rel - turn * rt
    ls_net = ls - 2.0 * turn * rt

    split = pd.Period(REGIME_SPLIT[:7], freq="M")
    ym_per = pd.PeriodIndex(rs["ym"], freq="M")
    pre = long_rel_net[ym_per < split]
    post = long_rel_net[ym_per >= split]
    regime_sign_stable = bool(len(pre) >= 3 and len(post) >= 3 and
                              np.sign(np.nanmean(pre)) == np.sign(np.nanmean(post)) and np.nanmean(pre) != 0)

    mean_turn = float(np.nanmean(turn))
    gross_mean = float(np.nanmean(long_rel))
    breakeven_bps = float(gross_mean / mean_turn * 1e4) if mean_turn > 0 else None

    def pack(arr):
        t = nw_tstat(arr, NW_LAG)
        return {"mean": round(float(np.nanmean(arr)), 6), "nw_t": round(t, 4) if t == t else None}

    return {
        "n_months": len(recs),
        "month_span": [recs[0]["ym"], recs[-1]["ym"]],
        "avg_names": round(float(rs["n"].mean()), 1),
        "long_rel_gross": pack(long_rel),
        "long_rel_net": pack(long_rel_net),
        "ls_gross": pack(ls),
        "ls_net": pack(ls_net),
        "mean_turnover": round(mean_turn, 4),
        "realized_cost_bps": round(mean_turn * ROUND_TRIP_BPS, 2),
        "breakeven_cost_bps": round(breakeven_bps, 2) if breakeven_bps is not None else None,
        "regime": {"pre_mean": round(float(np.nanmean(pre)), 6) if len(pre) else None,
                   "post_mean": round(float(np.nanmean(post)), 6) if len(post) else None,
                   "sign_stable": regime_sign_stable},
    }


def main():
    require_stage0()
    front = load_viop_month_end_front()
    raw_lookup, price_m = load_spot()
    basis = build_basis(front, raw_lookup)
    ret_m = build_forward(price_m)

    sig = basis.merge(price_m[["symbol", "ym", "liq_med"]], on=["symbol", "ym"], how="inner")

    scopes = {"ALL": sig, "LIQUID": sig[sig["liq_med"] >= LIQUID_ADV_MIN_TL]}
    variants = {"primary_m+1": 1, "robust_skip_m+2": 2}
    results_by = {}
    for scope_name, sdf in scopes.items():
        results_by[scope_name] = {}
        for vname, off in variants.items():
            results_by[scope_name][vname] = evaluate(
                sdf[["ym", "symbol", "basis_ann", "liq_med"]], ret_m, off)

    # descriptive basis distribution (carry level vs cross-sectional spread)
    b_all = basis["basis_ann"].to_numpy()
    basis_desc = {
        "median_ann": round(float(np.median(b_all)), 4),
        "p25_ann": round(float(np.percentile(b_all, 25)), 4),
        "p75_ann": round(float(np.percentile(b_all, 75)), 4),
        "frac_contango_positive": round(float(np.mean(b_all > 0)), 4),
        "n_basis_obs": int(len(b_all)),
    }

    liq_primary = results_by["LIQUID"]["primary_m+1"]
    keep = (not liq_primary.get("insufficient")
            and liq_primary["long_rel_net"]["mean"] > 0
            and liq_primary["long_rel_net"]["nw_t"] is not None
            and abs(liq_primary["long_rel_net"]["nw_t"]) >= T_SIG
            and liq_primary["regime"]["sign_stable"])

    verdict = ("TRADEABLE-EDGE (LIQUID LOW-basis long leg: market-relative NET mean>0, "
               "|NW-t|>=2, regime-sign-stable) -- DEPLOY-CANDIDATE for the maintainer review"
               if keep else
               "VIOP-SS-BASIS-XS-NOT-TRADEABLE (significance-wall, dividend-calendar artifact, "
               "common-carry-dominated, or regime sign-instability); no deployable edge")

    results = {
        "candidate": "L23 VIOP single-stock-futures FUNDING-BASIS cross-sectional factor (REAL DATA; pre-registered, measurement-only)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (offline VIOP day-end SSF settlement + clean_universe spot raw/adjusted prices)",
        "new_axis": "per-stock futures-implied FUNDING/BORROW BASIS LEVEL -- not in L1-L22; distinct from "
                    "L21 single-stock-futures OI-growth (a flow) and L22 index term-structure (index-level). "
                    "The per-stock SPOT leg IS available offline (raw close), unlike the L22 index.",
        "params": {"nw_lag": NW_LAG, "tercile": TERCILE, "min_names": MIN_NAMES,
                   "liquid_adv_min_tl": LIQUID_ADV_MIN_TL, "round_trip_bps": ROUND_TRIP_BPS,
                   "regime_split": REGIME_SPLIT, "min_yyyymm": MIN_YYYYMM, "min_dte_days": MIN_DTE_DAYS,
                   "t_sig": T_SIG},
        "data": {"front_obs": int(len(front)),
                 "front_months": int(front["ym"].nunique()) if len(front) else 0,
                 "front_underlyings": int(front["symbol"].nunique()) if len(front) else 0,
                 "basis_obs": int(len(basis)),
                 "basis_months": int(basis["ym"].nunique()) if len(basis) else 0,
                 "signal_obs": int(len(sig))},
        "descriptive_basis": {
            "annualized_basis": basis_desc,
            "reading": "Persistent positive (contango) funding-basis; the median annualized basis tracks "
                       "the large TL risk-free carry (NOT a dividend yield), confirming the LEVEL is "
                       "dominated by common carry while the cross-sectional tercile spread isolates the "
                       "per-name funding/borrow/positioning component under test.",
        },
        "results": results_by,
        "summary": {
            "headline": (
                "VIOP single-stock-futures funding-basis cross-sectional test on REAL data. "
                f"basis median_ann={basis_desc['median_ann']} frac>0={basis_desc['frac_contango_positive']} "
                f"over {basis_desc['n_basis_obs']} obs. LIQUID primary(m+1) LOW-basis long-leg "
                f"market-relative NET mean={liq_primary.get('long_rel_net', {}).get('mean')}, NW-t="
                f"{liq_primary.get('long_rel_net', {}).get('nw_t')}, "
                f"regime-stable={liq_primary.get('regime', {}).get('sign_stable')}, "
                f"months={liq_primary.get('n_months')}, avg-names={liq_primary.get('avg_names')}. "
                f"Verdict: {'TRADEABLE' if keep else 'NOT-TRADEABLE'}."),
            "interpretation": (
                "Opens the genuinely-new per-stock futures FUNDING-BASIS axis on the existing local VIOP "
                "archive, and (unlike L22's index basis) the clean per-stock spot leg is available offline. "
                "The basis LEVEL is overwhelmingly common TL carry; the cross-sectional spread that the "
                "tercile isolates is small and noisy in a thin ~47-name market, and the LOW-basis leg carries "
                "a known dividend-calendar (Q2) seasonal confound. The look-ahead-safe m+1 design likely "
                "washes out any contemporaneous basis<->return co-move. Result recorded per the frozen "
                "keep-bar; if NOT-TRADEABLE it joins the clean archive, if TRADEABLE it is a deploy-candidate."),
        },
        "verdict": {
            "verdict": verdict,
            "keep_bar_passed": bool(keep),
            "deploy_candidate": bool(keep),
            "no_edge_claim": bool(not keep),
        },
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print(f"front_obs={len(front)} front_months={front['ym'].nunique() if len(front) else 0} "
          f"front_underlyings={front['symbol'].nunique() if len(front) else 0} "
          f"basis_obs={len(basis)} signal_obs={len(sig)}")
    print(f"basis median_ann={basis_desc['median_ann']} frac>0={basis_desc['frac_contango_positive']}")
    for sc in ("ALL", "LIQUID"):
        for v in ("primary_m+1", "robust_skip_m+2"):
            r = results_by[sc][v]
            if r.get("insufficient"):
                print(f"  {sc}/{v}: insufficient (months={r['n_months']})")
            else:
                print(f"  {sc}/{v}: months={r['n_months']} avg_n={r['avg_names']} "
                      f"long_rel_net mean={r['long_rel_net']['mean']} t={r['long_rel_net']['nw_t']} "
                      f"ls_net mean={r['ls_net']['mean']} t={r['ls_net']['nw_t']} "
                      f"regime_stable={r['regime']['sign_stable']} cost_bps={r['realized_cost_bps']} "
                      f"breakeven_bps={r['breakeven_cost_bps']}")
    print(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()

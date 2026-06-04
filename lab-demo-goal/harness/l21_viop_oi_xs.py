"""lab-demo-goal L21: VIOP single-stock-futures OPEN-INTEREST cross-sectional positioning -- REAL DATA (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L21_viop_oi_xs.json (FROZEN before results).

A GENUINELY NEW factor axis (per-stock derivatives positioning via futures open interest), enabled by the
VIOP day-end archive at data/bist_datastore_archive/viop (VIOP_GUNSONU_FIYATHACIM monthly CSVs with per-contract
ACIK POZISYON / OPEN POSITION, segment SSF = single-stock futures, 2017-2026 uncompressed). NOT in the L1-L20 set.

Signal: oi_growth(symbol, month m) = total_OI_end(m)/total_OI_end(m-1) - 1, total_OI = sum of open position
across that underlying's SSF contracts on the last trading day of the month. Hypothesis: HIGH OI-growth
(positioning building) -> subsequent SPOT OUTPERFORMANCE; LONG the HIGH-OI-growth tercile, market-relative,
net of realistic cost. Look-ahead-safe (OI is same-day public; signal month m -> forward spot return month m+1,
plus a skip-month m+2 robustness). Measurement-only; NO optimization/grid-sweep; NO network; ASCII.
Writes only under lab-demo-goal/.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l21_viop_oi_xs.py
"""
from __future__ import annotations
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L21_viop_oi_xs.json"
OUT = LAB / "results" / "l21_viop_oi_xs_results.json"
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
MIN_YYYYMM = 201901  # price panel starts 2019-01
SYM_RE = re.compile(r"^[A-Z0-9]{2,6}\.E$")
SEG_COL = 3       # PAZAR SEGMENTI; SSF = single-stock futures
UND_COL = 6       # DAYANAK VARLIK (underlying, e.g. AEFES.E)
OI_COL = 21       # ACIK POZISYON (open position, contracts)
DATE_COL = 0
NCOLS_MIN = 23
SEG_SSF = "SSF"
FILE_GLOB = "VIOP_GUNSONU_FIYATHACIM.M.*.csv"


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


def load_viop_month_end_oi() -> pd.DataFrame:
    """Month-end total open interest per SSF underlying.
    Returns [ym(Period-M), symbol(bare), oi_end] using the LAST trading day in each monthly file."""
    rows = []
    for p in sorted(VIOP_DIR.glob(FILE_GLOB)):
        tag = p.name.split(".M.")[1][:6]
        if not tag.isdigit() or int(tag) < MIN_YYYYMM:
            continue
        ym = pd.Period(f"{tag[:4]}-{tag[4:]}", freq="M")
        by_day = defaultdict(lambda: defaultdict(float))  # date -> underlying(bare) -> total OI
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
                try:
                    oi = float(row[OI_COL])
                except (ValueError, TypeError):
                    continue
                if not np.isfinite(oi):
                    continue
                by_day[row[DATE_COL].strip()][und[:-2]] += oi
        if not by_day:
            continue
        last = max(by_day.keys())  # month-end snapshot
        for sym, oi in by_day[last].items():
            rows.append((ym, sym, oi))
    return pd.DataFrame(rows, columns=["ym", "symbol", "oi_end"])


def build_oi_growth(oi_df: pd.DataFrame) -> pd.DataFrame:
    """oi_growth(m) = oi_end(m)/oi_end(m-1) - 1, only for consecutive months with prev OI > 0."""
    df = oi_df.sort_values(["symbol", "ym"]).copy()
    df["mord"] = df["ym"].apply(lambda p: p.year * 12 + (p.month - 1))
    df["prev_oi"] = df.groupby("symbol")["oi_end"].shift(1)
    df["prev_mord"] = df.groupby("symbol")["mord"].shift(1)
    consec = (df["mord"] - df["prev_mord"]) == 1
    valid = consec & (df["prev_oi"] > 0)
    df["oi_growth"] = np.where(valid, df["oi_end"] / df["prev_oi"] - 1.0, np.nan)
    return df.dropna(subset=["oi_growth"])[["ym", "symbol", "oi_growth"]]


def load_price_monthly() -> pd.DataFrame:
    """Monthly per-symbol: month-end adjusted_close, trailing-63d median value_tl."""
    df = pd.read_parquet(PRICE_PARQUET, columns=["date", "symbol", "value_tl", "adjusted_close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"])
    df["ym"] = df["date"].dt.to_period("M")
    df["liq_med"] = df.groupby("symbol")["value_tl"].transform(
        lambda s: s.rolling(LIQUID_TRAILING_DAYS, min_periods=LIQUID_TRAILING_DAYS).median())
    g = df.groupby(["symbol", "ym"])
    out = g.agg(adjclose=("adjusted_close", "last"),
                liq_med=("liq_med", "last")).reset_index()
    return out


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
    """signal_df: [ym, symbol, oi_growth, liq_med]. offset=1 (m+1) or 2 (m+2).
    Cross-sectional tercile long-HIGH/short-LOW OI-growth, market-relative monthly series + NW-t + cost + regime."""
    ret_lookup = ret_m.dropna(subset=["ret"]).copy()
    ret_lookup["sig_ym"] = ret_lookup["ym"] - offset
    ret_lookup = ret_lookup.rename(columns={"ret": "fwd_ret"})[["symbol", "sig_ym", "fwd_ret"]]
    merged = signal_df.merge(ret_lookup, left_on=["symbol", "ym"], right_on=["symbol", "sig_ym"], how="inner")

    months = sorted(merged["ym"].unique())
    recs = []
    prev_high = set()
    for ym in months:
        sub = merged[merged["ym"] == ym].dropna(subset=["fwd_ret", "oi_growth"])
        if len(sub) < MIN_NAMES:
            continue
        sub = sub.sort_values("oi_growth")
        k = max(1, int(len(sub) * TERCILE))
        low = sub.iloc[:k]    # low OI-growth -> SHORT
        high = sub.iloc[-k:]  # high OI-growth -> LONG
        all_mean = float(sub["fwd_ret"].mean())
        low_mean = float(low["fwd_ret"].mean())
        high_mean = float(high["fwd_ret"].mean())
        cur_high = set(high["symbol"])
        turn = len(prev_high - cur_high) / len(cur_high) if prev_high else 1.0
        prev_high = cur_high
        recs.append({"ym": str(ym), "n": len(sub),
                     "long_rel": high_mean - all_mean,
                     "ls": high_mean - low_mean,
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
    oi = load_viop_month_end_oi()
    growth = build_oi_growth(oi)
    price_m = load_price_monthly()
    ret_m = build_forward(price_m)

    sig = growth.merge(price_m[["symbol", "ym", "liq_med"]], on=["symbol", "ym"], how="inner")

    scopes = {"ALL": sig, "LIQUID": sig[sig["liq_med"] >= LIQUID_ADV_MIN_TL]}
    variants = {"primary_m+1": 1, "robust_skip_m+2": 2}
    results_by = {}
    for scope_name, sdf in scopes.items():
        results_by[scope_name] = {}
        for vname, off in variants.items():
            results_by[scope_name][vname] = evaluate(
                sdf[["ym", "symbol", "oi_growth", "liq_med"]], ret_m, off)

    liq_primary = results_by["LIQUID"]["primary_m+1"]
    keep = (not liq_primary.get("insufficient")
            and liq_primary["long_rel_net"]["mean"] > 0
            and liq_primary["long_rel_net"]["nw_t"] is not None
            and abs(liq_primary["long_rel_net"]["nw_t"]) >= T_SIG
            and liq_primary["regime"]["sign_stable"])

    verdict = ("TRADEABLE-EDGE (LIQUID high-OI-growth long leg: market-relative NET mean>0, "
               "|NW-t|>=2, regime-sign-stable) -- DEPLOY-CANDIDATE for Cagan review"
               if keep else
               "VIOP-OI-XS-NOT-TRADEABLE (significance-wall, contemporaneous-only co-move / "
               "crowding-reversal, or regime sign-instability); no deployable edge")

    results = {
        "candidate": "L21 VIOP single-stock-futures open-interest cross-sectional positioning (REAL DATA; pre-registered, measurement-only)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (offline VIOP day-end archive + clean_universe spot prices)",
        "new_axis": "per-stock futures-market positioning (open-interest growth) -- not in L1-L20; "
                    "orthogonal to price/volume/fundamental/sentiment/short/foreign-flow",
        "params": {"nw_lag": NW_LAG, "tercile": TERCILE, "min_names": MIN_NAMES,
                   "liquid_adv_min_tl": LIQUID_ADV_MIN_TL, "round_trip_bps": ROUND_TRIP_BPS,
                   "regime_split": REGIME_SPLIT, "min_yyyymm": MIN_YYYYMM},
        "data": {"oi_obs": int(len(oi)),
                 "oi_months": int(oi["ym"].nunique()) if len(oi) else 0,
                 "oi_underlyings": int(oi["symbol"].nunique()) if len(oi) else 0,
                 "signal_obs": int(len(sig)), "signal_months": int(sig["ym"].nunique()) if len(sig) else 0},
        "results": results_by,
        "summary": {
            "headline": (
                "VIOP single-stock-futures open-interest cross-sectional test on REAL data. "
                f"LIQUID primary(m+1) high-OI-growth long-leg market-relative NET mean="
                f"{liq_primary.get('long_rel_net', {}).get('mean')}, NW-t="
                f"{liq_primary.get('long_rel_net', {}).get('nw_t')}, "
                f"regime-stable={liq_primary.get('regime', {}).get('sign_stable')}, "
                f"months={liq_primary.get('n_months')}, avg-names={liq_primary.get('avg_names')}. "
                f"Verdict: {'TRADEABLE' if keep else 'NOT-TRADEABLE'}."),
            "interpretation": (
                "Opens the genuinely-new per-stock futures-positioning axis (open-interest growth) on the "
                "existing local VIOP archive. Cross-sectional per-name OI-growth predictability is far less "
                "established than the aggregate Hong-Yogo result; OI change is contemporaneously tied to "
                "volume/volatility, so the look-ahead-safe m+1 design likely washes it out (or shows crowding-"
                "reversal), and the thin SSF cross-section is noisy. Result recorded per the frozen keep-bar; "
                "if NOT-TRADEABLE it joins the clean archive, if TRADEABLE it is a deploy-candidate."),
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
    print(f"oi_obs={len(oi)} oi_months={oi['ym'].nunique() if len(oi) else 0} "
          f"oi_underlyings={oi['symbol'].nunique() if len(oi) else 0} signal_obs={len(sig)}")
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

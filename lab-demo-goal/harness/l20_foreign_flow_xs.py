"""lab-demo-goal L20: FOREIGN-FLOW cross-sectional factor -- REAL DATA (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L20_foreign_flow_xs.json (FROZEN before results).

A GENUINELY NEW factor axis (per-stock foreign-investor net-flow positioning), enabled by a real
offline foreign-flow archive at data/bist_datastore_archive/foreign_flow (monthly per-stock foreign
buy/sell value, legacy OLE2 .xls, 1997-2026). DISTINCT from the D-211 graveyard, which was foreign-flow
INDEX-TIMING (aggregate); this is the per-stock CROSS-SECTIONAL variant.

Signal: foreign_imbalance = (buy_tl - sell_tl)/(buy_tl + sell_tl) per stock-month, bounded [-1,+1].
Hypothesis: HIGH imbalance (foreign net-buying) -> subsequent OUTPERFORMANCE; LONG the HIGH-imbalance
tercile, market-relative, net of realistic cost. Look-ahead-safe (signal month m -> forward return
month m+1, plus a skip-month m+2 robustness). Measurement-only; NO optimization/grid-sweep; NO network;
ASCII. Writes only under lab-demo-goal/.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l20_foreign_flow_xs.py
"""
from __future__ import annotations
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab-demo-goal"
STAGE0 = LAB / "stage0" / "STAGE0_L20_foreign_flow_xs.json"
OUT = LAB / "results" / "l20_foreign_flow_xs_results.json"
FOREIGN_DIR = ROOT / "data" / "bist_datastore_archive" / "foreign_flow"
PRICE_PARQUET = ROOT / "data" / "clean_universe" / "adjusted_prices_2019_2026.parquet"

T_SIG = 2.0
NW_LAG = 6
TERCILE = 1.0 / 3.0
MIN_NAMES = 30
LIQUID_ADV_MIN_TL = 1.0e7
LIQUID_TRAILING_DAYS = 63
REGIME_SPLIT = "2022-01-01"
ROUND_TRIP_BPS = 40.0
MIN_YYYYMM = 201901  # price panel starts 2019-01; earlier foreign files cannot join
SYM_RE = re.compile(r"^[A-Z0-9]{2,6}\.E$")
BUY_TL_COL = 3
SELL_TL_COL = 6


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


def load_foreign_panel() -> pd.DataFrame:
    """Monthly per-stock foreign buy/sell value TL from the legacy .xls archive.
    Returns [ym(Period-M), symbol, buy_tl, sell_tl] for months >= MIN_YYYYMM."""
    rows = []
    for p in sorted(FOREIGN_DIR.glob("*.zip")):
        m = re.search(r"yabanci(\d{6})", p.name)
        if not m:
            continue
        yyyymm = int(m.group(1))
        if yyyymm < MIN_YYYYMM:
            continue
        ym = pd.Period(f"{m.group(1)[:4]}-{m.group(1)[4:]}", freq="M")
        try:
            with zipfile.ZipFile(p) as z:
                data = z.read(z.namelist()[0])
        except Exception:
            continue
        try:
            xls = pd.ExcelFile(io.BytesIO(data), engine="xlrd")
            sheet = "TURKCE" if "TURKCE" in xls.sheet_names else xls.sheet_names[0]
            d = xls.parse(sheet, header=None)
        except Exception:
            continue
        if d.shape[1] <= SELL_TL_COL:
            continue
        for i in range(len(d)):
            c0 = str(d.iloc[i, 0]).strip()
            if not SYM_RE.match(c0):
                continue
            try:
                buy_tl = float(d.iloc[i, BUY_TL_COL])
                sell_tl = float(d.iloc[i, SELL_TL_COL])
            except (ValueError, TypeError):
                continue
            if not np.isfinite(buy_tl) or not np.isfinite(sell_tl):
                continue
            if (buy_tl + sell_tl) <= 0:
                continue
            rows.append((ym, c0[:-2], buy_tl, sell_tl))
    return pd.DataFrame(rows, columns=["ym", "symbol", "buy_tl", "sell_tl"])


def load_price_monthly() -> pd.DataFrame:
    """Monthly per-symbol: month-end adjusted_close, monthly total traded TL, trailing-63d median value_tl."""
    df = pd.read_parquet(PRICE_PARQUET, columns=["date", "symbol", "value_tl", "adjusted_close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"])
    df["ym"] = df["date"].dt.to_period("M")
    df["liq_med"] = df.groupby("symbol")["value_tl"].transform(
        lambda s: s.rolling(LIQUID_TRAILING_DAYS, min_periods=LIQUID_TRAILING_DAYS).median())
    g = df.groupby(["symbol", "ym"])
    out = g.agg(adjclose=("adjusted_close", "last"),
                total_tl=("value_tl", "sum"),
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
    """signal_df: [ym, symbol, imbalance, liq_med]. offset=1 (m+1) or 2 (m+2).
    Cross-sectional tercile long-HIGH/short-LOW imbalance, market-relative monthly series + NW-t + cost + regime."""
    ret_lookup = ret_m.dropna(subset=["ret"]).copy()
    ret_lookup["sig_ym"] = ret_lookup["ym"] - offset  # forward ret realized at ym maps back to signal month
    ret_lookup = ret_lookup.rename(columns={"ret": "fwd_ret"})[["symbol", "sig_ym", "fwd_ret"]]
    merged = signal_df.merge(ret_lookup, left_on=["symbol", "ym"], right_on=["symbol", "sig_ym"], how="inner")

    months = sorted(merged["ym"].unique())
    recs = []
    prev_high = set()
    for ym in months:
        sub = merged[merged["ym"] == ym].dropna(subset=["fwd_ret", "imbalance"])
        if len(sub) < MIN_NAMES:
            continue
        sub = sub.sort_values("imbalance")
        k = max(1, int(len(sub) * TERCILE))
        low = sub.iloc[:k]    # low imbalance (foreign net-selling) -> SHORT
        high = sub.iloc[-k:]  # high imbalance (foreign net-buying) -> LONG
        all_mean = float(sub["fwd_ret"].mean())
        low_mean = float(low["fwd_ret"].mean())
        high_mean = float(high["fwd_ret"].mean())
        cur_high = set(high["symbol"])
        turn = len(prev_high - cur_high) / len(cur_high) if prev_high else 1.0
        prev_high = cur_high
        recs.append({"ym": str(ym), "n": len(sub),
                     "long_rel": high_mean - all_mean,        # market-relative long (HIGH) leg
                     "ls": high_mean - low_mean,              # high minus low spread
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
    ls_net = ls - 2.0 * turn * rt  # long+short legs both rebalance

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
    foreign = load_foreign_panel()
    price_m = load_price_monthly()
    ret_m = build_forward(price_m)

    # signal table: imbalance = (buy_tl - sell_tl)/(buy_tl + sell_tl), with liq_med for the liquid filter
    sig = foreign.merge(price_m[["symbol", "ym", "liq_med"]], on=["symbol", "ym"], how="inner")
    denom = sig["buy_tl"] + sig["sell_tl"]
    sig = sig[denom > 0].copy()
    sig["imbalance"] = (sig["buy_tl"] - sig["sell_tl"]) / (sig["buy_tl"] + sig["sell_tl"])

    scopes = {"ALL": sig, "LIQUID": sig[sig["liq_med"] >= LIQUID_ADV_MIN_TL]}
    variants = {"primary_m+1": 1, "robust_skip_m+2": 2}
    results_by = {}
    for scope_name, sdf in scopes.items():
        results_by[scope_name] = {}
        for vname, off in variants.items():
            results_by[scope_name][vname] = evaluate(
                sdf[["ym", "symbol", "imbalance", "liq_med"]], ret_m, off)

    liq_primary = results_by["LIQUID"]["primary_m+1"]
    keep = (not liq_primary.get("insufficient")
            and liq_primary["long_rel_net"]["mean"] > 0
            and liq_primary["long_rel_net"]["nw_t"] is not None
            and abs(liq_primary["long_rel_net"]["nw_t"]) >= T_SIG
            and liq_primary["regime"]["sign_stable"])

    verdict = ("TRADEABLE-EDGE (LIQUID high-foreign-imbalance long leg: market-relative NET mean>0, "
               "|NW-t|>=2, regime-sign-stable) -- DEPLOY-CANDIDATE for Cagan review"
               if keep else
               "FOREIGN-FLOW-XS-NOT-TRADEABLE (significance-wall, contemporaneous-only co-move, or "
               "regime sign-instability); no deployable edge")

    results = {
        "candidate": "L20 foreign-flow cross-sectional factor (REAL DATA; pre-registered, measurement-only)",
        "stage0": str(STAGE0.relative_to(ROOT)),
        "mode": "REAL (offline foreign-flow archive + clean_universe prices)",
        "new_axis": "per-stock foreign-investor net-flow positioning (buy/sell imbalance) -- not in L1-L19 "
                    "graveyard; distinct from D-211 aggregate index-timing",
        "params": {"nw_lag": NW_LAG, "tercile": TERCILE, "min_names": MIN_NAMES,
                   "liquid_adv_min_tl": LIQUID_ADV_MIN_TL, "round_trip_bps": ROUND_TRIP_BPS,
                   "regime_split": REGIME_SPLIT, "min_yyyymm": MIN_YYYYMM},
        "data": {"foreign_obs": int(len(foreign)),
                 "foreign_months": int(foreign["ym"].nunique()) if len(foreign) else 0,
                 "signal_obs": int(len(sig)), "signal_months": int(sig["ym"].nunique()) if len(sig) else 0},
        "results": results_by,
        "summary": {
            "headline": (
                "Foreign-flow cross-sectional test on REAL data. "
                f"LIQUID primary(m+1) high-imbalance long-leg market-relative NET mean="
                f"{liq_primary.get('long_rel_net', {}).get('mean')}, NW-t="
                f"{liq_primary.get('long_rel_net', {}).get('nw_t')}, "
                f"regime-stable={liq_primary.get('regime', {}).get('sign_stable')}, "
                f"months={liq_primary.get('n_months')}, avg-names={liq_primary.get('avg_names')}. "
                f"Verdict: {'TRADEABLE' if keep else 'NOT-TRADEABLE'}."),
            "interpretation": (
                "Opens the genuinely-new per-stock foreign-flow axis on a freshly-discovered local archive, "
                "distinct from the D-211 aggregate index-timing graveyard. Foreign flow direction is partly "
                "mechanically tied to contemporaneous month-m returns (performance-chasing); the look-ahead-safe "
                "m+1 design excludes that co-move, so a weak or reversed forward signal is plausible. Monthly "
                "granularity also weakens timing. Result recorded per the frozen keep-bar; if NOT-TRADEABLE it "
                "joins the clean archive, if TRADEABLE it is a deploy-candidate."),
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
    print(f"foreign_obs={len(foreign)} months={foreign['ym'].nunique() if len(foreign) else 0} "
          f"signal_obs={len(sig)}")
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

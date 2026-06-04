"""lab-demo-goal L4: CALENDAR/SEASONALITY descriptive scan (READ-ONLY).

Stage-0: lab-demo-goal/stage0/STAGE0_L4_calendar.json (FROZEN before results).
FIXED canonical effect set (NO data-driven search): turn-of-month, day-of-week, month-of-year,
pre-holiday. XU100 daily returns PRIMARY, EW-full SECONDARY. OLS+Newey-West HAC differential
(effect-day mean minus other-day mean), Bonferroni multiple-testing, regime sign-stability,
and a hold-only-on-effect-days vs buy-and-hold tradeability frame. DESCRIPTIVE VIEW by design.

Run:  PYTHONPATH=. python lab-demo-goal/harness/l4_calendar.py
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
STAGE0 = ROOT / "lab-demo-goal" / "stage0" / "STAGE0_L4_calendar.json"
OUT = ROOT / "lab-demo-goal" / "results" / "l4_calendar_results.json"
PRICES = CU / "adjusted_prices_2019_2026.parquet"
XU100 = SN / "exposure_d187_xu100.parquet"

HAC_LAGS = 5
REGIME_SPLIT = "2022-01-01"
N_HEADLINE = 4
N_TOTAL = 19
BONF_HEADLINE = 0.05 / N_HEADLINE
BONF_TOTAL = 0.05 / N_TOTAL
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


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


def ols_hac_diff(y: np.ndarray, d: np.ndarray, lags: int = HAC_LAGS) -> tuple:
    """y = returns, d = 0/1 dummy. Fit y = a + b*d ; return b (=mean(d=1)-mean(d=0)) and HAC-t."""
    m = np.isfinite(y) & np.isfinite(d)
    y, d = y[m], d[m].astype(float)
    if d.sum() < 3 or (1 - d).sum() < 3:
        return float("nan"), float("nan")
    X = np.column_stack([np.ones_like(d), d])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    u = X * resid[:, None]
    S = u.T @ u
    n = len(y)
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1)
        G = u[l:].T @ u[:-l]
        S += w * (G + G.T)
    cov = XtX_inv @ S @ XtX_inv
    se = float(np.sqrt(cov[1, 1]))
    if not np.isfinite(se) or se <= 0:
        return float(beta[1]), float("nan")
    return float(beta[1]), float(beta[1] / se)


def effect_record(ret: pd.Series, mask: np.ndarray, name: str, headline: bool) -> dict:
    y = ret.values
    d = mask.astype(float)
    b, t = ols_hac_diff(y, d)
    p = float(2 * (1 - stats.norm.cdf(abs(t)))) if np.isfinite(t) else float("nan")
    # regime sign stability of the differential
    cut = pd.Timestamp(REGIME_SPLIT)
    pre = ret.index < cut
    post = ~pre
    b_pre, _ = ols_hac_diff(y[pre], d[pre])
    b_post, _ = ols_hac_diff(y[post], d[post])
    sign_stable = bool(np.isfinite(b_pre) and np.isfinite(b_post)
                       and b_pre != 0 and b_post != 0 and (b_pre > 0) == (b_post > 0))
    return {
        "name": name, "headline": headline,
        "mean_effect_day": _r(float(np.nanmean(y[mask]))),
        "mean_other_day": _r(float(np.nanmean(y[~mask]))),
        "differential": _r(b), "hac_t": _r(t), "p_raw": _r(p),
        "n_effect_days": int(mask.sum()), "n_other_days": int((~mask).sum()),
        "survives_bonf_headline": bool(np.isfinite(p) and p < BONF_HEADLINE) if headline else None,
        "survives_bonf_total": bool(np.isfinite(p) and p < BONF_TOTAL),
        "regime_diff_pre": _r(b_pre), "regime_diff_post": _r(b_post),
        "regime_sign_stable": sign_stable,
    }


def turn_of_month_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    """Last trading day of month + first 3 trading days of next month."""
    s = pd.Series(np.arange(len(idx)), index=idx)
    ym = idx.to_period("M")
    is_last = np.zeros(len(idx), dtype=bool)
    is_first3 = np.zeros(len(idx), dtype=bool)
    for _, grp in s.groupby(ym):
        pos = grp.values
        is_last[pos[-1]] = True
        for j in pos[:3]:
            is_first3[j] = True
    return is_last | is_first3


def pre_holiday_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    """Trading day immediately before a calendar gap >= 3 days to the next trading day."""
    gaps = np.diff(idx.values).astype("timedelta64[D]").astype(int)
    mask = np.zeros(len(idx), dtype=bool)
    mask[:-1] = gaps >= 3
    return mask


def annualized(ret: pd.Series, mask: np.ndarray | None) -> float:
    r = ret.values.copy()
    if mask is not None:
        r = np.where(mask, r, 0.0)  # cash (0%) on non-effect days
    r = r[np.isfinite(ret.values)]
    if len(r) == 0:
        return float("nan")
    total = np.prod(1.0 + r)
    yrs = len(ret) / 252.0
    return float(total ** (1.0 / yrs) - 1.0) if total > 0 else float("nan")


def scan(ret: pd.Series, label: str) -> dict:
    idx = ret.index
    out = {"series": label, "n_days": int(len(ret)), "effects": {}}
    tom = turn_of_month_mask(idx)
    out["effects"]["turn_of_month"] = effect_record(ret, tom, "turn_of_month", True)
    dow = np.asarray(idx.dayofweek)
    for i, wd in enumerate(WEEKDAYS):
        out["effects"][f"dow_{wd}"] = effect_record(ret, dow == i, f"dow_{wd}", wd == "Mon")
    moy = np.asarray(idx.month)
    for i, mo in enumerate(MONTHS, start=1):
        out["effects"][f"month_{mo}"] = effect_record(ret, moy == i, f"month_{mo}", mo == "Jan")
    ph = pre_holiday_mask(idx)
    out["effects"]["pre_holiday"] = effect_record(ret, ph, "pre_holiday", True)
    out["tradeability"] = {
        "buy_and_hold_annualized": _r(annualized(ret, None)),
        "tom_overlay_annualized_cashOnOffDays": _r(annualized(ret, tom)),
        "note": "overlay sits in CASH (0%) on non-TOM days -> forgoes the strong inflation drift; "
                "before any trade cost. Gap vs buy-and-hold = opportunity cost of the overlay.",
    }
    return out


def main():
    s0 = require_stage0()
    xu = pd.read_parquet(XU100)
    xu["date"] = pd.to_datetime(xu["date"])
    xser = pd.Series(xu["value"].values, index=xu["date"]).sort_index()
    xret = xser.pct_change().dropna()

    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    daily = eng.clip_clean_returns(close)
    ewret = daily.mean(axis=1, skipna=True).dropna()

    results = {"candidate": s0["candidate"], "stage0": str(STAGE0.relative_to(ROOT)),
               "multiple_testing": {"n_headline": N_HEADLINE, "n_total": N_TOTAL,
                                    "bonf_headline_p": BONF_HEADLINE, "bonf_total_p": BONF_TOTAL},
               "PRIMARY_xu100": scan(xret, "XU100"),
               "SECONDARY_ew_full": scan(ewret, "EW-full")}

    # verdict: any effect surviving full-family Bonferroni AND regime-sign-stable on XU100
    noteworthy = [e for e in results["PRIMARY_xu100"]["effects"].values()
                  if e["survives_bonf_total"] and e["regime_sign_stable"]]
    results["verdict"] = {
        "verdict": "DESCRIPTIVE-VIEW (no deployable calendar edge)",
        "noteworthy_effects": [{"name": e["name"], "differential": e["differential"],
                                "hac_t": e["hac_t"], "p_raw": e["p_raw"]} for e in noteworthy],
        "note": "Calendar effects are a market characteristic, not a tradeable edge: harvesting "
                "needs frequent index in/out trades and sits out of the strong inflation drift "
                "(see tradeability gap). Reported VIEW regardless of statistical noteworthiness.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"WROTE {OUT.relative_to(ROOT)}")
    print("VERDICT:", results["verdict"]["verdict"])
    print(f"Bonferroni: headline p<{BONF_HEADLINE:.4f}, full-family p<{BONF_TOTAL:.5f}")
    for label in ("PRIMARY_xu100", "SECONDARY_ew_full"):
        sc = results[label]
        print(f"--- {sc['series']} (n={sc['n_days']}) ---")
        for key in ["turn_of_month", "dow_Mon", "dow_Tue", "dow_Fri", "month_Jan", "pre_holiday"]:
            e = sc["effects"][key]
            flag = "*BONF*" if e["survives_bonf_total"] else ("hl" if e.get("survives_bonf_headline") else "")
            print(f"  {key:14s} diff={e['differential']} hac_t={e['hac_t']} p={e['p_raw']} "
                  f"stable={e['regime_sign_stable']} {flag}")
        tr = sc["tradeability"]
        print(f"  B&H ann={tr['buy_and_hold_annualized']} | TOM-overlay ann={tr['tom_overlay_annualized_cashOnOffDays']}")


if __name__ == "__main__":
    main()

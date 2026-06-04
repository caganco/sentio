"""D-213 (RR-Y1-003) engine -- ex-ante real-rate -> forward XU100 TL-real return.

Cerceve-B continuous time-series forecast (single-asset timing; NOT stock selection).
PRICE-ORTHOGONAL axis. MEASUREMENT-ONLY. Geometry/thresholds frozen at STAGE0_d213.json
+ d213_config.py + thresholds.py D213_* block. The engine REFUSES to run unless
STAGE0_d213.json exists and the input snapshot content-hashes match (reproducibility
guard -> RAISE on drift).

Pipeline:
  1. r_ex_ante(t) = nominal(t) - expected_inf(t)   [APIFON4 - ENFBEK.PKA12ENF, annual pct]
  2. XU100 (price-only) -> monthly nominal return -> TL-real = r_nom - TUFE_MoM
  3. align forward_real_ret_t  ~  r_ex_ante(t-1)    (~t+15g knowable, look-ahead-safe)
  4. primary OLS slope + Newey-West HAC t (lag=6)
  5. regime stability (2022-01 split) + leave-one-regime-out concentration test
  6. deployable leg (r_ex_ante(t-1) < 0 -> XU100 long; else APIFON4 cash carry) vs
     buy-and-hold, post-cost (D207 MEGA one-way per index entry/exit), cumulative TL-real
  7. diagnosis: contemporaneous lag-0 (NON-DEPLOYABLE) + ex-post lag-2 control (secondary)
  8. keep-bar[1..4] -> verdict TRADEABLE / TRADEABLE-DEGIL

STRANGLER: new module; zero edit to committed motors. HTTP-free at run time (reads frozen
snapshots). EVDS raw data does NOT enter CI; the real run is a local artifact.

Dayanak: STAGE0_d213.json (frozen); docs/yol1/RR-Y1-003-asama0-veri.md (D-212 data facts);
realistic_cost.py (D-207 cost constants); NW stats ported from d211_foreign_flow.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.screening import d213_config as cfg


# ===========================================================================
# Guards
# ===========================================================================
def _assert_stage0() -> None:
    if not cfg.D213_STAGE0.exists():
        raise RuntimeError(
            "D-213 REFUSES to run: STAGE0_d213.json (pre-registration) is missing. "
            "Freeze + commit the Stage-0 lock BEFORE measuring (anti-post-hoc guard)."
        )


def _hash16(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _assert_hash(name: str, expected: str):
    path = cfg.D213_SNAPSHOT_DIR / f"{name}.parquet"
    got = _hash16(path)
    if got != expected:
        raise RuntimeError(
            f"D-213 snapshot drift: {name} hash {got} != frozen {expected}. "
            "Inputs changed since Stage-0 -> RAISE (reproducibility guard)."
        )
    return path


# ===========================================================================
# Statistics (PORTED frozen, bit-for-bit from d211) + NW-HAC OLS slope
# ===========================================================================
def nw_mean_tstat(x, lag: int = cfg.D213_NW_LAG):
    """Newey-West HAC t-stat of the MEAN of series x (H0: mean=0)."""
    a = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    n = len(a)
    if n < lag + 3:
        return float("nan"), (float(a.mean()) if n else float("nan")), n
    m = a.mean()
    e = a - m
    gamma0 = (e @ e) / n
    s = gamma0
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1.0)
        s += 2.0 * w * (e[L:] @ e[:-L]) / n
    se = np.sqrt(s / n) if s > 0 else float("nan")
    return (m / se if se and se > 0 else float("nan")), m, n


def nw_ols_slope(x, y, lag: int = cfg.D213_NW_LAG) -> dict:
    """Simple OLS y = a + b*x with Newey-West HAC standard error on the SLOPE b.

    meat S = sum u_t^2 + 2*sum_{L=1..lag} w_L * sum_t u_t u_{t-L}, u_t = (x_t-xbar)*e_t.
    Var(b) = S / S_xx^2 ; t = b / sqrt(Var(b)). Bartlett weights. Returns slope, t, n, r2.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < lag + 3:
        return {"slope": float("nan"), "t": float("nan"), "n": n, "r2": float("nan"),
                "intercept": float("nan")}
    xbar, ybar = x.mean(), y.mean()
    xc = x - xbar
    s_xx = float(xc @ xc)
    if s_xx <= 0:
        return {"slope": float("nan"), "t": float("nan"), "n": n, "r2": float("nan"),
                "intercept": float("nan")}
    b = float((xc @ (y - ybar)) / s_xx)
    a = float(ybar - b * xbar)
    e = y - a - b * x
    u = xc * e
    S = float(u @ u)
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1.0)
        S += 2.0 * w * float(u[L:] @ u[:-L])
    var_b = S / (s_xx ** 2)
    se_b = np.sqrt(var_b) if var_b > 0 else float("nan")
    t = b / se_b if se_b and se_b > 0 else float("nan")
    ss_tot = float((y - ybar) @ (y - ybar))
    r2 = 1.0 - float(e @ e) / ss_tot if ss_tot > 0 else float("nan")
    return {"slope": b, "t": float(t), "n": n, "r2": r2, "intercept": a}


def _ar1(x) -> float:
    a = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    if len(a) < 4:
        return float("nan")
    a0, a1 = a[:-1], a[1:]
    c0, c1 = a0 - a0.mean(), a1 - a1.mean()
    denom = np.sqrt((c0 @ c0) * (c1 @ c1))
    return float((c0 @ c1) / denom) if denom > 0 else float("nan")


def _zscore(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=1)
    return (s - s.mean()) / sd if sd and sd > 0 else s * 0.0


# ===========================================================================
# Data loaders
# ===========================================================================
def _month_end_series(path) -> pd.Series:
    df = pd.read_parquet(path)
    s = pd.Series(df["value"].values, index=pd.to_datetime(df["date"]))
    s = s.sort_index()
    me = s.resample("ME").last()
    me.index = me.index.to_period("M")
    return me


def _cpi_yoy_pct(tufe_me: pd.Series) -> pd.Series:
    """12-month CPI change in annual percentage points (to match nominal annual-pct)."""
    return tufe_me.pct_change(12) * 100.0


# ===========================================================================
# Main measurement
# ===========================================================================
def run() -> dict:
    _assert_stage0()
    nom_path = _assert_hash(cfg.D213_NOMINAL_SNAPSHOT, cfg.D213_NOMINAL_HASH)
    exp_path = _assert_hash(cfg.D213_EXPINF_SNAPSHOT, cfg.D213_EXPINF_HASH)
    xu_path = _assert_hash(cfg.D213_XU100_SNAPSHOT, cfg.D213_XU100_HASH)
    tufe_path = _assert_hash(cfg.D213_TUFE_SNAPSHOT, cfg.D213_TUFE_HASH)

    # --- predictor legs + dependent ---
    nominal = _month_end_series(nom_path)        # annual pct
    expinf = _month_end_series(exp_path)         # annual pct
    xu = _month_end_series(xu_path)
    tufe = _month_end_series(tufe_path)

    r_ex_ante = (nominal - expinf).dropna()                      # annual pct points (LEVEL)
    cpi_yoy = _cpi_yoy_pct(tufe).dropna()
    r_ex_post = (nominal - cpi_yoy).dropna()                     # ex-post real rate (annual pct)

    r_nom = xu.pct_change()
    infl = tufe.pct_change()
    real_ret = (r_nom - infl).dropna()                          # TL-real index return (subtraction lock)

    # cash leg = APIFON4-derived monthly real carry (STAGE0 lock; T+0 within-month accrual)
    cash_nom = (1.0 + nominal / 100.0) ** (1.0 / 12.0) - 1.0
    cash_real = (cash_nom - infl).dropna()

    w0 = pd.Period(cfg.D213_WINDOW_START[:7], "M")
    w1 = pd.Period(cfg.D213_WINDOW_END[:7], "M")

    df = pd.DataFrame({"real_ret": real_ret})
    df = df[(df.index >= w0) & (df.index <= w1)]
    lag = cfg.D213_LOOKAHEAD_LAG_MONTHS                          # 1
    elag = cfg.D213_EXPOST_LAG_MONTHS                            # 2
    df["rea_lag1"] = r_ex_ante.reindex(df.index - lag).values   # r_ex_ante(t-1) deployable
    df["rea_lag0"] = r_ex_ante.reindex(df.index).values         # contemporaneous (diagnosis)
    df["rep_lag2"] = r_ex_post.reindex(df.index - elag).values  # ex-post control (secondary)
    df["cash_real"] = cash_real.reindex(df.index).values
    df_primary = df.dropna(subset=["real_ret", "rea_lag1"]).copy()

    # --- 1. primary regression (ex-ante lag-1) ---
    primary = nw_ols_slope(df_primary["rea_lag1"], df_primary["real_ret"])
    primary["rea_ar1"] = _ar1(r_ex_ante.reindex(df_primary.index - lag))
    primary["nonoverlap"] = "monthly forward return vs lag-1 predictor -> non-overlapping by construction"

    # --- 2. regime stability + concentration ---
    split = pd.Period(cfg.D213_REGIME_SPLIT[:7], "M")
    A = df_primary[df_primary.index < split]
    B = df_primary[df_primary.index >= split]
    regA = nw_ols_slope(A["rea_lag1"], A["real_ret"])
    regB = nw_ols_slope(B["rea_lag1"], B["real_ret"])
    full_sign = np.sign(primary["slope"]) if np.isfinite(primary["slope"]) else 0
    loo_drop_A_sign = np.sign(regB["slope"]) if np.isfinite(regB["slope"]) else 0
    loo_drop_B_sign = np.sign(regA["slope"]) if np.isfinite(regA["slope"]) else 0
    same_sign_AB = (np.isfinite(regA["slope"]) and np.isfinite(regB["slope"])
                    and np.sign(regA["slope"]) == np.sign(regB["slope"]) and full_sign != 0
                    and np.sign(regA["slope"]) == full_sign)
    not_concentrated = (full_sign != 0
                        and loo_drop_A_sign == full_sign and loo_drop_B_sign == full_sign)
    regime = {
        "split": cfg.D213_REGIME_SPLIT,
        "A_2019_2021": {"slope": regA["slope"], "t": regA["t"], "n": regA["n"]},
        "B_2022_2026": {"slope": regB["slope"], "t": regB["t"], "n": regB["n"]},
        "full_sign": int(full_sign),
        "same_sign_AB": bool(same_sign_AB),
        "leave_one_regime_out_keeps_sign": bool(not_concentrated),
    }

    # --- 3. deployable leg vs buy-and-hold (post-cost, cumulative TL-real) ---
    # economic prior LOCK: r_ex_ante(t-1) < 0 -> XU100 long; else cash.
    dleg = df_primary.dropna(subset=["cash_real"]).copy()
    thr = cfg.D213_SIGNAL_THRESHOLD                             # 0.0
    onew = cfg.D213_INDEX_ONEWAY_COST
    pos = (dleg["rea_lag1"] < thr).astype(int).values          # 1=index, 0=cash
    rr = dleg["real_ret"].values
    cr = dleg["cash_real"].values
    strat_gross = np.where(pos == 1, rr, cr)
    prev = np.concatenate([[0], pos[:-1]])                      # baseline prev position = cash (0)
    switch = (pos != prev).astype(float)
    strat_net = strat_gross - switch * onew
    bh_net = rr.copy().astype(float)
    if len(bh_net):
        bh_net[0] -= onew                                      # buy-and-hold pays one entry cost
    strat_cum = float(np.prod(1.0 + strat_net) - 1.0)
    bh_cum = float(np.prod(1.0 + bh_net) - 1.0)
    rel = strat_net - bh_net
    rel_t, rel_mean, rel_n = nw_mean_tstat(rel)
    deployable = {
        "n_months": int(len(dleg)),
        "deploy_rule": "r_ex_ante(t-1) < 0 -> XU100 long; else APIFON4 cash carry",
        "share_index_long": float(pos.mean()) if len(pos) else float("nan"),
        "n_switches": int(switch.sum()),
        "oneway_cost_bps": onew * 1e4,
        "strat_net_cum_real": strat_cum,
        "buyhold_net_cum_real": bh_cum,
        "strat_beats_buyhold": bool(strat_cum > bh_cum),
        "rel_monthly_mean": rel_mean,
        "rel_monthly_nw_t": rel_t,
        "cash_leg_note": "APIFON4-derived real carry (NOT TLREF -- silent-NaN until 2022-07); clean 2019-01.",
    }

    # --- 4. look-ahead safety + contemporaneous diagnosis (NON-DEPLOYABLE) ---
    contemp_df = df.dropna(subset=["real_ret", "rea_lag0"])
    contemp = nw_ols_slope(contemp_df["rea_lag0"], contemp_df["real_ret"])
    contemp["status"] = "NON-DEPLOYABLE (uses end-of-month-t rate level, not knowable at start of t)"

    # --- ex-post control (secondary, report-only, cannot rescue) ---
    expost_df = df_primary.dropna(subset=["rep_lag2"]).copy()
    expost_reg = nw_ols_slope(expost_df["rep_lag2"], expost_df["real_ret"])
    secondary = {
        "ex_post_lag2": {"slope": expost_reg["slope"], "t": expost_reg["t"], "n": expost_reg["n"],
                         "status": "report-only, verdict-immutable (lag-2 staler; CPI also enters deflator -> caution)"},
        "change_form_delta_rea": "NOT RUN as primary -- secondary/forbidden-to-rescue; LEVEL is the locked primary.",
    }

    # --- keep-bar ---
    kb1 = bool(np.isfinite(primary["t"]) and abs(primary["t"]) >= cfg.D213_KEEP_NW_T_MIN)
    kb2 = bool(same_sign_AB and not_concentrated)
    kb3 = bool(deployable["strat_beats_buyhold"])
    kb4 = True  # lag-1 applied throughout; contemporaneous + ex-post excluded by construction
    keep_bar = {"1_primary_nw_t_ge_2": kb1,
                "2_regime_stable_not_concentrated": kb2,
                "3_deployable_beats_buyhold": kb3,
                "4_lookahead_safe": kb4}
    verdict = "TRADEABLE" if (kb1 and kb2 and kb3 and kb4) else "TRADEABLE-DEGIL"

    results = {
        "directive": "D-213",
        "config_version": cfg.D213_CONFIG_VERSION,
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": cfg.D213_WINDOW_START, "end": cfg.D213_WINDOW_END,
                   "n_forward_months": int(primary["n"])},
        "predictor": "r_ex_ante(t-1) = APIFON4(t-1) - ENFBEK.PKA12ENF(t-1), LEVEL, lag-1 (~t+15g)",
        "dependent": "XU100 price-only monthly nominal - TUFE_MoM = TL-real",
        "r_ex_ante_summary": {"mean": float(df_primary["rea_lag1"].mean()),
                              "std": float(df_primary["rea_lag1"].std(ddof=1)),
                              "min": float(df_primary["rea_lag1"].min()),
                              "max": float(df_primary["rea_lag1"].max()),
                              "ar1": primary["rea_ar1"],
                              "share_negative": float((df_primary["rea_lag1"] < 0).mean())},
        "1_primary_regression": primary,
        "2_regime_stability": regime,
        "3_deployable_leg": deployable,
        "4_contemporaneous_diagnosis": contemp,
        "secondary_report_only": secondary,
        "keep_bar": keep_bar,
        "verdict": verdict,
        "oos_gap_note": ("2019-2026 is one long high-inflation regime; a true "
                         "inflation-normalization OOS is ABSENT. Real rates swung from "
                         "deeply negative (2021-23 repression) to positive (2024+). "
                         "Deployment is a separate the project decision."),
    }
    return results


def _to_jsonable(o):
    if isinstance(o, dict):
        return {k: _to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_to_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


if __name__ == "__main__":
    res = run()
    cfg.D213_RESULTS.write_text(json.dumps(_to_jsonable(res), indent=2), encoding="ascii")
    print(json.dumps(_to_jsonable(res), indent=2))
    print(f"\n[written] {cfg.D213_RESULTS}")

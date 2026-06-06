"""D-211 (RR-Y1-002) engine -- foreign-flow aggregate -> forward BIST-index TL-real return.

Cerceve-B continuous time-series forecast (single-asset timing; NOT stock selection).
MEASUREMENT-ONLY. Geometry/thresholds frozen at STAGE0_d211.json + d211_config.py +
thresholds.py D211_* block. The engine REFUSES to run unless STAGE0_d211.json exists
and the input snapshot content-hashes match (reproducibility guard -> RAISE on drift).

Pipeline:
  1. foreign_flow monthly .xls -> NF_pct(m) = SUM(buy-sell)_usd / SUM(buy+sell)_usd
  2. XU100 (price-only) -> monthly nominal return -> TL-real = r_nom - TUFE_MoM
  3. align forward_real_ret_t  ~  NF_pct(t-2)   (~6wk publication lag, look-ahead-safe)
  4. primary OLS slope + Newey-West HAC t (lag=6)
  5. regime stability (2022-01 split) + leave-one-regime-out concentration test
  6. deployable leg (NF_pct(t-2)>0 -> XU100 long; else TLREF cash) vs buy-and-hold,
     post-cost (D207 MEGA one-way spread per index entry/exit), cumulative TL-real
  7. keep-bar[1..4] -> verdict TRADEABLE / TRADEABLE-DEGIL

STRANGLER: new module; zero edit to committed motors. HTTP-free, offline. The
foreign_flow archive does NOT enter CI; the real run is a local artifact.

Dayanak: STAGE0_d211.json (frozen); D-210/RR-Y1-002-asama0-veri.md sec1-2/sec4 (data
facts); realistic_cost.py (D-207 cost constants); ff parser geometry ported from
edge-arastirma/lab/ff_data.py.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from src.screening import d211_config as cfg

_TICKER_RE = re.compile(cfg.D211_TICKER_REGEX)
_FF_COLS = ["buy_nom", "buy_tl", "buy_usd", "sell_nom", "sell_tl", "sell_usd"]


# ===========================================================================
# Guards
# ===========================================================================
def _assert_stage0() -> None:
    if not cfg.D211_STAGE0.exists():
        raise RuntimeError(
            "D-211 REFUSES to run: STAGE0_d211.json (pre-registration) is missing. "
            "Freeze + commit the Stage-0 lock BEFORE measuring (anti-post-hoc guard)."
        )


def _hash16(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _assert_hash(name: str, expected: str):
    path = cfg.D211_SNAPSHOT_DIR / f"{name}.parquet"
    got = _hash16(path)
    if got != expected:
        raise RuntimeError(
            f"D-211 snapshot drift: {name} hash {got} != frozen {expected}. "
            "Inputs changed since Stage-0 -> RAISE (reproducibility guard)."
        )
    return path


# ===========================================================================
# Statistics (PORTED frozen, bit-for-bit) + NW-HAC OLS slope
# ===========================================================================
def nw_mean_tstat(x, lag: int = cfg.D211_NW_LAG):
    """Newey-West HAC t-stat of the MEAN of series x (H0: mean=0). PORT (edge-arastirma)."""
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


def nw_ols_slope(x, y, lag: int = cfg.D211_NW_LAG) -> dict:
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
def _read_ff_zip(fp) -> pd.DataFrame | None:
    try:
        z = zipfile.ZipFile(fp)
    except Exception:
        return None
    inner = [x for x in z.namelist() if x.lower().endswith((".xls", ".xlsx"))]
    if not inner:
        return None
    try:
        raw = pd.read_excel(io.BytesIO(z.read(inner[0])), header=None)
    except Exception:
        return None
    c0 = raw[0].astype(str).str.strip()
    df = raw.loc[c0.str.match(_TICKER_RE)].copy()
    if df.empty or df.shape[1] < 8:
        return None
    df = df.iloc[:, :8]
    df.columns = ["ticker", "name"] + _FF_COLS
    for c in _FF_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    ym = re.search(r"(\d{6})", fp.stem).group(1)
    df["month"] = pd.Period(f"{ym[:4]}-{ym[4:]}", freq="M")
    return df[["month", "ticker"] + _FF_COLS]


def load_nf_pct() -> pd.DataFrame:
    """Monthly aggregate foreign-flow series. Returns DataFrame indexed by Period[M]
    with columns: net_usd, gross_usd, nf_pct."""
    rows = []
    for fp in sorted(cfg.D211_FOREIGN_FLOW_DIR.glob("yabanci*.zip")):
        one = _read_ff_zip(fp)
        if one is not None:
            rows.append(one)
    if not rows:
        raise RuntimeError("D-211: no foreign-flow files parsed.")
    long = pd.concat(rows, ignore_index=True)
    g = long.groupby("month")
    net = g["buy_usd"].sum() - g["sell_usd"].sum()
    gross = g["buy_usd"].sum() + g["sell_usd"].sum()
    out = pd.DataFrame({"net_usd": net, "gross_usd": gross})
    out["nf_pct"] = out["net_usd"] / out["gross_usd"].replace(0, np.nan)
    return out.sort_index()


def _month_end_series(path) -> pd.Series:
    df = pd.read_parquet(path)
    s = pd.Series(df["value"].values, index=pd.to_datetime(df["date"]))
    s = s.sort_index()
    me = s.resample("ME").last()
    me.index = me.index.to_period("M")
    return me


# ===========================================================================
# Main measurement
# ===========================================================================
def run() -> dict:
    _assert_stage0()
    xu_path = _assert_hash(cfg.D211_XU100_SNAPSHOT, cfg.D211_XU100_HASH)
    tufe_path = _assert_hash(cfg.D211_TUFE_SNAPSHOT, cfg.D211_TUFE_HASH)
    tlref_path = _assert_hash(cfg.D211_TLREF_SNAPSHOT, cfg.D211_TLREF_HASH)

    # --- predictor + dependent ---
    nf = load_nf_pct()
    xu = _month_end_series(xu_path)
    tufe = _month_end_series(tufe_path)
    tlref = _month_end_series(tlref_path)

    r_nom = xu.pct_change()
    infl = tufe.pct_change()
    real_ret = (r_nom - infl).dropna()                       # TL-real index return (subtraction lock)
    tlref_real = (tlref.pct_change() - infl).dropna()        # cash leg real return

    w0 = pd.Period(cfg.D211_WINDOW_START[:7], "M")
    w1 = pd.Period(cfg.D211_WINDOW_END[:7], "M")

    df = pd.DataFrame({"real_ret": real_ret})
    df = df[(df.index >= w0) & (df.index <= w1)]
    lag = cfg.D211_LOOKAHEAD_LAG_MONTHS
    df["nf_lag"] = nf["nf_pct"].reindex(df.index - lag).values   # NF_pct(t-2)
    df["nf_lag0"] = nf["nf_pct"].reindex(df.index).values        # contemporaneous (diagnosis)
    df["tlref_real"] = tlref_real.reindex(df.index).values
    df["net_usd_lag"] = nf["net_usd"].reindex(df.index - lag).values
    df_primary = df.dropna(subset=["real_ret", "nf_lag"]).copy()

    # --- 1. primary regression (lag-2) ---
    primary = nw_ols_slope(df_primary["nf_lag"], df_primary["real_ret"])
    primary["nf_ar1"] = _ar1(nf["nf_pct"].reindex(df_primary.index - lag))
    primary["nonoverlap"] = "monthly forward return vs lag-2 predictor -> non-overlapping by construction"

    # --- 2. regime stability + concentration ---
    split = pd.Period(cfg.D211_REGIME_SPLIT[:7], "M")
    A = df_primary[df_primary.index < split]
    B = df_primary[df_primary.index >= split]
    regA = nw_ols_slope(A["nf_lag"], A["real_ret"])
    regB = nw_ols_slope(B["nf_lag"], B["real_ret"])
    full_sign = np.sign(primary["slope"]) if np.isfinite(primary["slope"]) else 0
    # leave-one-regime-out: removing A leaves B, removing B leaves A
    loo_drop_A_sign = np.sign(regB["slope"]) if np.isfinite(regB["slope"]) else 0
    loo_drop_B_sign = np.sign(regA["slope"]) if np.isfinite(regA["slope"]) else 0
    same_sign_AB = (np.isfinite(regA["slope"]) and np.isfinite(regB["slope"])
                    and np.sign(regA["slope"]) == np.sign(regB["slope"]) and full_sign != 0
                    and np.sign(regA["slope"]) == full_sign)
    not_concentrated = (full_sign != 0
                        and loo_drop_A_sign == full_sign and loo_drop_B_sign == full_sign)
    regime = {
        "split": cfg.D211_REGIME_SPLIT,
        "A_2019_2021": {"slope": regA["slope"], "t": regA["t"], "n": regA["n"]},
        "B_2022_2026": {"slope": regB["slope"], "t": regB["t"], "n": regB["n"]},
        "full_sign": int(full_sign),
        "same_sign_AB": bool(same_sign_AB),
        "leave_one_regime_out_keeps_sign": bool(not_concentrated),
    }

    # --- 3. deployable leg vs buy-and-hold (post-cost, cumulative TL-real) ---
    dleg = df_primary.dropna(subset=["tlref_real"]).copy()
    thr = cfg.D211_SIGNAL_THRESHOLD
    onew = cfg.D211_INDEX_ONEWAY_COST
    pos = (dleg["nf_lag"] > thr).astype(int).values          # 1=index, 0=cash
    rr = dleg["real_ret"].values
    cr = dleg["tlref_real"].values
    strat_gross = np.where(pos == 1, rr, cr)
    # cost: charge one-way on each index entry/exit; baseline prev position = cash (0)
    prev = np.concatenate([[0], pos[:-1]])
    switch = (pos != prev).astype(float)
    strat_net = strat_gross - switch * onew
    # buy-and-hold: always index; one entry cost in first month
    bh_net = rr.copy().astype(float)
    if len(bh_net):
        bh_net[0] -= onew
    strat_cum = float(np.prod(1.0 + strat_net) - 1.0)
    bh_cum = float(np.prod(1.0 + bh_net) - 1.0)
    rel = strat_net - bh_net
    rel_t, rel_mean, rel_n = nw_mean_tstat(rel)
    deployable = {
        "n_months": int(len(dleg)),
        "share_index_long": float(pos.mean()) if len(pos) else float("nan"),
        "n_switches": int(switch.sum()),
        "oneway_cost_bps": onew * 1e4,
        "strat_net_cum_real": strat_cum,
        "buyhold_net_cum_real": bh_cum,
        "strat_beats_buyhold": bool(strat_cum > bh_cum),
        "rel_monthly_mean": rel_mean,
        "rel_monthly_nw_t": rel_t,
        "tlref_proxy_note": "TLREF real-data starts 2022-07; pre-2022-07 cash leg is D-187 proxy-extended (flagged).",
    }

    # --- 4. look-ahead safety + contemporaneous diagnosis (NON-DEPLOYABLE) ---
    contemp_df = df.dropna(subset=["real_ret", "nf_lag0"])
    contemp = nw_ols_slope(contemp_df["nf_lag0"], contemp_df["real_ret"])
    contemp["status"] = "NON-DEPLOYABLE (uses same-month flow, not knowable at decision time)"

    # --- secondary (report-only, cannot rescue) ---
    alt = df_primary.dropna(subset=["net_usd_lag"]).copy()
    alt_reg = nw_ols_slope(_zscore(alt["net_usd_lag"]), alt["real_ret"])
    secondary = {
        "zscore_net_usd_lag2": {"slope_sign": int(np.sign(alt_reg["slope"])) if np.isfinite(alt_reg["slope"]) else 0,
                                "t": alt_reg["t"], "n": alt_reg["n"],
                                "status": "report-only, verdict-immutable"},
        "net_usd_over_mcap": "NOT RUN -- optional secondary; requires aggregate market-cap join; verdict-immutable.",
    }

    # --- keep-bar ---
    kb1 = bool(np.isfinite(primary["t"]) and abs(primary["t"]) >= cfg.D211_KEEP_NW_T_MIN)
    kb2 = bool(same_sign_AB and not_concentrated)
    kb3 = bool(deployable["strat_beats_buyhold"])
    kb4 = True  # lag-2 applied throughout; contemporaneous leg excluded by construction
    keep_bar = {"1_primary_nw_t_ge_2": kb1,
                "2_regime_stable_not_concentrated": kb2,
                "3_deployable_beats_buyhold": kb3,
                "4_lookahead_safe": kb4}
    verdict = "TRADEABLE" if (kb1 and kb2 and kb3 and kb4) else "TRADEABLE-DEGIL"

    results = {
        "directive": "D-211",
        "config_version": cfg.D211_CONFIG_VERSION,
        "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": cfg.D211_WINDOW_START, "end": cfg.D211_WINDOW_END,
                   "n_forward_months": int(primary["n"])},
        "predictor": "NF_pct(t-2) = SUM(buy-sell)_usd / SUM(buy+sell)_usd, lag-2 (~6wk pub lag)",
        "dependent": "XU100 price-only monthly nominal - TUFE_MoM = TL-real",
        "nf_pct_summary": {"mean": float(df_primary["nf_lag"].mean()),
                           "std": float(df_primary["nf_lag"].std(ddof=1)),
                           "min": float(df_primary["nf_lag"].min()),
                           "max": float(df_primary["nf_lag"].max()),
                           "ar1": primary["nf_ar1"]},
        "1_primary_regression": primary,
        "2_regime_stability": regime,
        "3_deployable_leg": deployable,
        "4_contemporaneous_diagnosis": contemp,
        "secondary_report_only": secondary,
        "keep_bar": keep_bar,
        "verdict": verdict,
        "oos_gap_note": ("2019-2026 is one long high-inflation regime; a true "
                         "inflation-normalization OOS is ABSENT. Foreign participation "
                         "at multi-year lows. Deployment is a separate maintainer decision."),
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
    cfg.D211_RESULTS.write_text(json.dumps(_to_jsonable(res), indent=2), encoding="ascii")
    print(json.dumps(_to_jsonable(res), indent=2))
    print(f"\n[written] {cfg.D211_RESULTS}")

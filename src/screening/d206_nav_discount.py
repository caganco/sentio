"""D-206 NAV-iskonto-Z mean-reversion engine -- TIME-SERIES, measurement-ONLY.

A NEW paradigm after cross-sectional factor selection was EXHAUSTED (hi52 KAPANDI D-205,
lowvol63 ELENDI NRR-007, value-regime ELENDI NRR-008/PR#177 -- 3/3 closed). Each holding has
its OWN NAV-discount time-series and is standardized against its OWN history (NOT cross-
sectional). HYPOTHESIS (Pontiff 1995, CEF premia mean-revert): a HIGH discount-Z (discount wide
-> holding cheap) predicts a POSITIVE forward return.

DISCIPLINE (frozen at Stage-0 docs/yol1/STAGE0_d206.json; the engine REFUSES to run without it):
  * MEASUREMENT-ONLY (optimization FORBIDDEN). committed-engine ZERO touch -- this module CALLS
    D-203/D-204 helpers read-only and computes its OWN panel; it does NOT modify them.
  * GEOMETRY frozen (trailing=36m, horizon=6m, lag conventions); DECISION constants live in
    src/signals/thresholds.py (D206_*) via d206_config.py. NO grid sweep (= p-hacking).
  * LOOK-AHEAD-safe: discount_z(t) standardized on discount<=t-1; NAV subsidiary mktval lagged 1
    month; the holding's OWN market cap is same-month (a live observable price). Asymmetry is
    intentional + documented.
  * Constant-share-bias + rights-issue-bias OPENLY DECLARED. discount is a WITHIN-MONTH ratio so
    the SIGNAL is unit-robust; cross-month RETURNS use a frozen power-of-10 redenomination
    harmonization (the source files carry market-wide unit breaks). A FIDELITY-GUARD validates
    the mktval-implied total-return proxy against the frozen adjusted total-return index on the
    2019-2026 overlap and RAISES if it fails.
  * N<=3 (NAV first round = 1). Honest expectation UNCERTAIN; elimination is a clean result.

The 5 TIME-SERIES gates: G1 pooled FE-panel coefficient sign/content; G2 significance (Driscoll-
Kraay SE PRIMARY + wild-cluster bootstrap + per-holding NW + same-sign); G3 per-holding circular-
shift null (preserves autocorrelation); G4 regime split (low-inflation vs high-inflation); G5
realistic D-204 cost. Controls: carry-trap (real-TLREF), LOHO (single-holding dominance), per-
holding linear-time detrend (constant-share-bias TREND).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import clean_universe_fundamentals as cuf
from src.screening import d203_clean_universe_test as eng
from src.screening import d204_hi52_stress as d204
from src.screening import d206_config as cfg

logger = logging.getLogger(__name__)

_STAGE0_DEFAULT = Path(__file__).parent.parent.parent / "docs" / "yol1" / "STAGE0_d206.json"


# ===========================================================================
# Stage-0 pre-registration (require_stage0 guard)
# ===========================================================================
def load_stage0(stage0_path: Path | str = _STAGE0_DEFAULT,
                require_stage0: bool = True) -> dict:
    """Read the FROZEN Stage-0 pre-registration. RAISES if missing (pre-registration discipline:
    the geometry + universe must be frozen BEFORE results)."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; D-206 must be frozen BEFORE "
            "results (measurement-only pre-registration discipline).")
    if not stage0_path.exists():
        return {}
    return json.loads(stage0_path.read_text(encoding="utf-8"))


def stage0_holdings(stage0: dict) -> dict[str, dict[str, float]]:
    """{holding: {subsidiary: stake, ...}} from the frozen composition."""
    comp = stage0.get("universe_composition_FROZEN", {}).get("holdings", {})
    return {h: dict(v.get("listed_subsidiaries", {})) for h, v in comp.items()}


# ===========================================================================
# Data layer: monthly market-cap panel + unit harmonization
# ===========================================================================
def harmonize_mktval_units(mk: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Undo market-wide power-of-10 redenomination breaks (FROZEN preprocessing).

    discount is a within-month ratio (unit-robust), but cross-month RETURNS are not. The source
    degoran files carry occasional market-wide unit jumps (e.g. ~1000x at 2026-02). Per month,
    take the cross-sectional MEDIAN month-over-month market-cap ratio; if |log10(median)| > 0.7
    (a >5x / <0.2x market-wide move -- impossible for a real one-month return), treat it as a
    power-of-10 redenomination and adjust a cumulative scale by 10^round(log10(median)). Data
    cleaning, NOT optimization."""
    months = sorted(mk.index)
    cum = 1.0
    scale: dict = {months[0]: 1.0}
    breaks: list = []
    for i in range(1, len(months)):
        r = (mk.loc[months[i]] / mk.loc[months[i - 1]]).replace([np.inf, -np.inf], np.nan).dropna()
        med = float(np.median(r)) if len(r) else 1.0
        if med > 0 and abs(np.log10(med)) > 0.7:
            factor = 10.0 ** round(np.log10(med))
            cum *= factor
            breaks.append({"month": str(months[i]), "median_ratio": round(med, 3),
                           "applied_factor": factor})
        scale[months[i]] = cum
    out = mk.copy()
    for m in months:
        out.loc[m] = mk.loc[m] / scale[m]
    return out, {"n_breaks": len(breaks), "breaks": breaks}


def build_monthly_panels() -> dict:
    """Load extended degoran fundamentals (2009-2026), pivot harmonized market cap + dividend
    yield -> {mktval (Period[M] x symbol, harmonized), dyld, harmonize_meta}."""
    funds = cuf.load_degoran_fundamentals(
        archive_fr_dir=cfg.D206_ARCHIVE_FR_DIR, start=cfg.D206_FUND_START,
        end=cfg.D206_FUND_END, file_glob=cfg.D206_FUND_FILE_GLOB)
    funds = funds.copy()
    funds["month"] = funds["month"].astype("period[M]")
    mk_raw = funds.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last")
    dyld = funds.pivot_table(index="month", columns="symbol", values="dy", aggfunc="last") / 100.0
    mk_raw = mk_raw.sort_index()
    dyld = dyld.sort_index().reindex(mk_raw.index)
    mk, hmeta = harmonize_mktval_units(mk_raw)
    return {"mktval": mk, "dyld": dyld, "harmonize_meta": hmeta}


# ===========================================================================
# Signal: per-holding NAV, discount, look-ahead-safe discount-Z
# ===========================================================================
def nav_discount_panel(mk: pd.DataFrame, holdings: dict[str, dict[str, float]],
                       lag: int = cfg.D206_PUBLICATION_LAG_MONTHS) -> pd.DataFrame:
    """discount(t) = (NAV(t) - holding_mktcap(t)) / NAV(t), per holding.

    NAV(t) = sum_i stake_i * subsidiary_mktval(t-lag)  [subsidiary side lagged `lag` months].
    The holding's OWN market cap is same-month t (live price; no lag). Listed subs absent at t
    simply do not contribute that month (NAV from whatever subs have data)."""
    out = {}
    for h, subs in holdings.items():
        if h not in mk.columns or not subs:
            continue
        nav = pd.Series(0.0, index=mk.index)
        any_sub = pd.Series(False, index=mk.index)
        for s, stake in subs.items():
            if s not in mk.columns:
                continue
            sub_lagged = mk[s].shift(lag)
            contrib = stake * sub_lagged
            nav = nav.add(contrib.fillna(0.0), fill_value=0.0)
            any_sub = any_sub | contrib.notna()
        nav = nav.where(any_sub & (nav > 0))
        hold_mc = mk[h]
        out[h] = (nav - hold_mc) / nav
    return pd.DataFrame(out)


def trailing_z(discount: pd.DataFrame, window: int = cfg.D206_TRAILING_WINDOW_MONTHS,
               min_periods: int = cfg.D206_TRAILING_MIN_PERIODS) -> pd.DataFrame:
    """Look-ahead-safe per-holding discount-Z: standardize discount(t) by the trailing mean/std
    of discount over [t-window, t-1] (the current month is NOT in its own standardization
    window). min_periods starts the series."""
    mean = discount.rolling(window, min_periods=min_periods).mean().shift(1)
    std = discount.rolling(window, min_periods=min_periods).std().shift(1)
    return (discount - mean) / std.replace(0.0, np.nan)


def detrend_discount(discount: pd.DataFrame) -> pd.DataFrame:
    """Per-holding linear-time detrend of discount BEFORE standardization (trap-1 remedy: removes
    the deterministic listed-fraction drift that the constant-share-bias TREND would leave)."""
    out = {}
    for h in discount.columns:
        s = discount[h]
        valid = s.dropna()
        if len(valid) < 3:
            out[h] = s
            continue
        t = np.arange(len(s), dtype=float)
        mask = s.notna().values
        b, a = np.polyfit(t[mask], s.values[mask], 1)
        out[h] = s - (a + b * t)
    return pd.DataFrame(out, index=discount.index)


def forward_returns(mk: pd.DataFrame, dyld: pd.DataFrame,
                    horizon: int = cfg.D206_PRIMARY_HORIZON_MONTHS) -> pd.DataFrame:
    """mktval-implied TOTAL forward return per holding: mktcap(t+h)/mktcap(t)-1 + dyld(t)*h/12.
    Market cap is split/bonus-continuous; the dividend term uses trailing degoran div yield."""
    price_ret = mk.shift(-horizon) / mk - 1.0
    div_term = dyld.reindex_like(mk).fillna(0.0) * (horizon / 12.0)
    return price_ret + div_term


# ===========================================================================
# Driscoll-Kraay within (fixed-effects) estimator -- single regressor, numpy
# ===========================================================================
def dk_within(x, y, gid, tid, lags: int) -> tuple[float, float, float]:
    """FE (within) slope of y on x with Driscoll-Kraay SE (HAC over time, Bartlett kernel,
    robust to cross-holding contemporaneous correlation; leans on T not on few-N). Returns
    (beta, se, t)."""
    df = pd.DataFrame({"x": np.asarray(x, float), "y": np.asarray(y, float),
                       "g": np.asarray(gid), "t": np.asarray(tid)}).dropna()
    if len(df) < 3:
        return float("nan"), float("nan"), float("nan")
    df["xd"] = df["x"] - df.groupby("g")["x"].transform("mean")
    df["yd"] = df["y"] - df.groupby("g")["y"].transform("mean")
    sxx = float((df["xd"] ** 2).sum())
    if sxx <= 0:
        return float("nan"), float("nan"), float("nan")
    beta = float((df["xd"] * df["yd"]).sum() / sxx)
    df["e"] = df["yd"] - beta * df["xd"]
    df["s"] = df["xd"] * df["e"]
    h = df.groupby("t")["s"].sum().sort_index().values
    T = len(h)
    S = float(np.sum(h * h))
    for lag in range(1, lags + 1):
        if lag >= T:
            break
        w = 1.0 - lag / (lags + 1)
        S += 2.0 * w * float(np.sum(h[lag:] * h[:-lag]))
    var = S / (sxx ** 2)
    se = float(np.sqrt(var)) if var > 0 else float("nan")
    t = beta / se if (np.isfinite(se) and se > 0) else float("nan")
    return beta, se, t


def _panel_long(z: pd.DataFrame, fwd: pd.DataFrame) -> pd.DataFrame:
    """Stack aligned (holding, month) rows with finite z and fwd. month kept as Period and as
    an integer time id (for DK time-aggregation)."""
    rows = []
    months = z.index
    tid_map = {m: i for i, m in enumerate(sorted(months))}
    for h in z.columns:
        if h not in fwd.columns:
            continue
        for m in months:
            zv = z.at[m, h] if h in z.columns else np.nan
            fv = fwd.at[m, h] if (m in fwd.index and h in fwd.columns) else np.nan
            if np.isfinite(zv) and np.isfinite(fv):
                rows.append((h, m, tid_map[m], float(zv), float(fv)))
    return pd.DataFrame(rows, columns=["holding", "month", "tid", "z", "fwd"])


# ===========================================================================
# Gate 2 corroboration: wild cluster bootstrap (Rademacher, null-imposed)
# ===========================================================================
def wild_cluster_bootstrap(panel: pd.DataFrame, lags: int,
                           n: int = cfg.D206_WILD_BOOT_N,
                           seed: int = cfg.D206_NULL_SEED) -> dict:
    """Cameron-Gelbach-Miller wild cluster bootstrap, cluster = holding, Rademacher weights,
    null imposed (beta=0). p = P(|t*| >= |t_obs|). t computed by dk_within for self-consistency."""
    g = panel["holding"].values
    x = panel["z"].values.astype(float)
    tid = panel["tid"].values
    # within-demean for the restricted (FE-only, beta=0) residual = yd
    df = panel.copy()
    df["yd"] = df["y_for_demean"] = df["fwd"] - df.groupby("holding")["fwd"].transform("mean")
    holding_mean = df.groupby("holding")["fwd"].transform("mean").values
    u = df["yd"].values
    _, _, t_obs = dk_within(x, panel["fwd"].values, g, tid, lags)
    if not np.isfinite(t_obs):
        return {"p": None, "t_obs": None, "n": 0}
    rng = np.random.default_rng(seed)
    holdings = list(pd.unique(g))
    hidx = {h: i for i, h in enumerate(holdings)}
    gpos = np.array([hidx[h] for h in g])
    cnt = 0
    valid = 0
    for _ in range(n):
        w = rng.choice([-1.0, 1.0], size=len(holdings))
        y_star = holding_mean + w[gpos] * u
        _, _, t_star = dk_within(x, y_star, g, tid, lags)
        if np.isfinite(t_star):
            valid += 1
            if abs(t_star) >= abs(t_obs):
                cnt += 1
    p = cnt / valid if valid else None
    return {"p": round(p, 4) if p is not None else None,
            "t_obs": eng._r(t_obs), "n": valid}


# ===========================================================================
# Gate 3: per-holding circular-shift null (preserves autocorrelation)
# ===========================================================================
def circular_shift_null(z: pd.DataFrame, fwd: pd.DataFrame, lags: int,
                        n: int = cfg.D206_NULL_N_RESAMPLES,
                        seed: int = cfg.D206_NULL_SEED) -> dict:
    """Hold the fwd-return panel FIXED; independently circular-shift each holding's discount-Z
    series by a random offset (autocorrelation fully preserved, signal-return alignment broken);
    re-fit the FE within-beta each draw. pctile = P(null beta < real beta)."""
    panel = _panel_long(z, fwd)
    if panel.empty:
        return {"n_resamples": 0, "real_beta": None, "pctile": None, "beats_null": False}
    real_beta, _, _ = dk_within(panel["z"].values, panel["fwd"].values,
                                panel["holding"].values, panel["tid"].values, lags)
    holdings = [h for h in z.columns if h in fwd.columns]
    months = list(z.index)
    tid_map = {m: i for i, m in enumerate(sorted(months))}
    zcols = {h: z[h].values for h in holdings}
    fcols = {h: fwd[h].reindex(z.index).values for h in holdings}
    rng = np.random.default_rng(seed)
    null_betas = []
    for _ in range(n):
        xs, ys, gs, ts = [], [], [], []
        for h in holdings:
            zv = zcols[h]
            k = int(rng.integers(1, len(zv))) if len(zv) > 1 else 0
            zsh = np.roll(zv, k)
            fv = fcols[h]
            mask = np.isfinite(zsh) & np.isfinite(fv)
            if mask.any():
                xs.append(zsh[mask])
                ys.append(fv[mask])
                gs.append(np.full(mask.sum(), h))
                ts.append(np.array([tid_map[months[i]] for i in np.where(mask)[0]]))
        if not xs:
            continue
        b, _, _ = dk_within(np.concatenate(xs), np.concatenate(ys),
                            np.concatenate(gs), np.concatenate(ts), lags)
        if np.isfinite(b):
            null_betas.append(b)
    if not null_betas or not np.isfinite(real_beta):
        return {"n_resamples": len(null_betas), "real_beta": eng._r(real_beta),
                "pctile": None, "beats_null": False}
    arr = np.array(null_betas)
    pctile = float(np.mean(arr < real_beta))
    return {"n_resamples": len(null_betas), "real_beta": eng._r(real_beta),
            "pctile": round(pctile, 4),
            "null_p95": eng._r(float(np.percentile(arr, 95))),
            "beats_null": bool(pctile >= cfg.D206_GATE_NULL_PCTILE)}


# ===========================================================================
# Per-holding NW |t| context (lags = horizon)
# ===========================================================================
def per_holding_nw(z: pd.DataFrame, fwd: pd.DataFrame, lags: int) -> dict:
    """Per-holding OLS slope of fwd on z with Newey-West |t| (lags=horizon) + same-sign count."""
    from src.screening.factor_ic_harness import newey_west_se
    out = {}
    n_pos = 0
    n_def = 0
    for h in z.columns:
        if h not in fwd.columns:
            continue
        s = pd.DataFrame({"z": z[h], "f": fwd[h].reindex(z.index)}).dropna()
        if len(s) < lags + 3:
            out[h] = {"n": len(s), "beta": None, "nw_t": None}
            continue
        x = s["z"].values
        y = s["f"].values
        xc = x - x.mean()
        sxx = float((xc ** 2).sum())
        if sxx <= 0:
            out[h] = {"n": len(s), "beta": None, "nw_t": None}
            continue
        beta = float((xc * (y - y.mean())).sum() / sxx)
        resid = (y - y.mean()) - beta * xc
        score = xc * resid
        se_score = newey_west_se(score, lags=lags)
        se_beta = se_score / sxx * np.sqrt(len(score)) if (np.isfinite(se_score) and sxx > 0) else np.nan
        nw_t = beta / se_beta if (np.isfinite(se_beta) and se_beta > 0) else float("nan")
        out[h] = {"n": len(s), "beta": eng._r(beta), "nw_t": eng._r(nw_t)}
        n_def += 1
        if beta > 0:
            n_pos += 1
    frac = (n_pos / n_def) if n_def else 0.0
    return {"per_holding": out, "n_positive": n_pos, "n_defined": n_def,
            "same_sign_frac": round(frac, 4),
            "same_sign_pass": bool(frac >= cfg.D206_GATE_SAME_SIGN_FRAC)}


# ===========================================================================
# LOHO (leave-one-holding-out) + regime split + carry-trap
# ===========================================================================
def loho(z: pd.DataFrame, fwd: pd.DataFrame, lags: int, full_beta: float) -> dict:
    """Drop each holding, re-fit FE within-beta + DK-t. FAIL if any single drop flips the sign
    or drops DK|t| below the gate threshold."""
    holdings = [h for h in z.columns if h in fwd.columns]
    fits = []
    max_db = 0.0
    flips = False
    weak = False
    for drop in holdings:
        sub = [h for h in holdings if h != drop]
        panel = _panel_long(z[sub], fwd[sub])
        if panel.empty:
            continue
        b, _, t = dk_within(panel["z"].values, panel["fwd"].values,
                            panel["holding"].values, panel["tid"].values, lags)
        fits.append({"dropped": drop, "beta": eng._r(b), "dk_t": eng._r(t)})
        if np.isfinite(b):
            max_db = max(max_db, abs(b - full_beta))
            if np.sign(b) != np.sign(full_beta):
                flips = True
        if not (np.isfinite(t) and abs(t) >= cfg.D206_GATE_NW_T_MIN):
            weak = True
    return {"fits": fits, "max_abs_delta_beta": eng._r(max_db),
            "sign_flips": flips, "any_weak_dk_t": weak,
            "robust": bool(not flips and not weak)}


def regime_betas(panel: pd.DataFrame, lags: int) -> dict:
    """FE within-beta in the low-inflation (<REGIME_LOWINFL_END) and high-inflation
    (>=REGIME_PRIMARY) sub-periods. PASS if MR coefficient positive in BOTH."""
    ts = panel["month"].apply(lambda p: p.to_timestamp())
    low_end = pd.Timestamp(cfg.D206_REGIME_LOWINFL_END)
    hi_start = pd.Timestamp(cfg.D206_REGIME_PRIMARY)
    low = panel[ts < low_end]
    hi = panel[ts >= hi_start]
    out = {}
    for name, sub in (("low_inflation_pre2017", low), ("high_inflation_2022plus", hi)):
        if len(sub) < 5:
            out[name] = {"n": len(sub), "beta": None, "dk_t": None}
            continue
        b, _, t = dk_within(sub["z"].values, sub["fwd"].values,
                            sub["holding"].values, sub["tid"].values, lags)
        out[name] = {"n": len(sub), "beta": eng._r(b), "dk_t": eng._r(t)}
    bl = out["low_inflation_pre2017"]["beta"]
    bh = out["high_inflation_2022plus"]["beta"]
    out["both_positive"] = bool(bl is not None and bh is not None and bl > 0 and bh > 0)
    return out


def carry_trap(panel: pd.DataFrame, tlref_real: pd.Series, lags: int) -> dict:
    """Add real-TLREF (TLREF - YoY-TUFE) as a 2nd regressor (overlap 2022-07+). The trap is
    REJECTED only if discount_z stays POSITIVE and DK-significant AFTER the carry control.
    Cross-check: fwd ~ real-TLREF alone."""
    import statsmodels.api as sm
    p = panel.copy()
    p["real_tlref"] = p["month"].apply(
        lambda m: float(tlref_real.get(m.to_timestamp("M"), np.nan)) if tlref_real is not None else np.nan)
    p = p.dropna(subset=["z", "fwd", "real_tlref"])
    if len(p) < 10 or p["holding"].nunique() < 2:
        return {"n": len(p), "available": False,
                "note": "real-TLREF overlap too short for the carry control"}
    dummies = pd.get_dummies(p["holding"], prefix="h", drop_first=True).astype(float)
    X = pd.concat([p[["z", "real_tlref"]].reset_index(drop=True),
                   dummies.reset_index(drop=True)], axis=1)
    X = sm.add_constant(X)
    try:
        m = sm.OLS(p["fwd"].values, X.values).fit(
            cov_type="hac-groupsum",
            cov_kwds={"time": p["tid"].values.astype(int), "maxlags": lags})
        names = list(X.columns)
        zi = names.index("z")
        beta_z = float(m.params[zi])
        t_z = float(m.tvalues[zi])
    except Exception as exc:  # noqa: BLE001
        return {"n": len(p), "available": False, "note": f"carry regression failed: {exc}"}
    survives = bool(beta_z > 0 and abs(t_z) >= cfg.D206_GATE_NW_T_MIN)
    return {"n": int(len(p)), "available": True,
            "beta_z_controlled": eng._r(beta_z), "dk_t_z_controlled": eng._r(t_z),
            "trap_rejected_signal_survives": survives}


# ===========================================================================
# FIDELITY-GUARD: mktval-implied TR vs frozen adjusted total-return index (2019-2026)
# ===========================================================================
def fidelity_guard(mk: pd.DataFrame, dyld: pd.DataFrame, holdings: list[str],
                   horizon: int = cfg.D206_PRIMARY_HORIZON_MONTHS) -> dict:
    """Validate the uniform mktval-implied total-return proxy against the frozen adjusted_close
    total-return index (tr_index_net) on the 2019-2026 overlap. RAISES if median corr < min_corr
    OR median MAE > max_mae (the proxy is broken -> test STOPS)."""
    daily = pd.read_parquet(
        Path(cfg.D206_CLEAN_UNIVERSE_ROOT) / "adjusted_prices_2019_2026.parquet",
        columns=["date", "symbol", "tr_index_net"])
    daily = daily[daily["symbol"].isin(holdings)].copy()
    daily["month"] = pd.to_datetime(daily["date"]).dt.to_period("M")
    tr = daily.sort_values("date").groupby(["month", "symbol"])["tr_index_net"].last().unstack()
    idx = sorted(set(mk.index) & set(tr.index))
    corrs, maes, per = {}, [], {}
    for s in holdings:
        if s not in mk.columns or s not in tr.columns:
            continue
        mks = mk[s].reindex(idx)
        dys = dyld[s].reindex(idx) if s in dyld.columns else pd.Series(np.nan, index=idx)
        trs = tr[s].reindex(idx)
        impl, true = [], []
        for i in range(len(idx) - horizon):
            a, b = mks.iloc[i], mks.iloc[i + horizon]
            ta, tb = trs.iloc[i], trs.iloc[i + horizon]
            if not (np.isfinite(a) and np.isfinite(b) and a > 0 and np.isfinite(ta)
                    and np.isfinite(tb) and ta > 0):
                continue
            d = dys.iloc[i] if np.isfinite(dys.iloc[i]) else 0.0
            impl.append(b / a - 1.0 + d * horizon / 12.0)
            true.append(tb / ta - 1.0)
        if len(impl) < 10:
            continue
        impl, true = np.array(impl), np.array(true)
        c = float(np.corrcoef(impl, true)[0, 1])
        mae = float(np.mean(np.abs(impl - true)))
        corrs[s] = c
        maes.append(mae)
        per[s] = {"n": len(impl), "corr": eng._r(c), "mae": eng._r(mae)}
    med_corr = float(np.median(list(corrs.values()))) if corrs else float("nan")
    med_mae = float(np.median(maes)) if maes else float("nan")
    ok = bool(np.isfinite(med_corr) and np.isfinite(med_mae)
              and med_corr >= cfg.D206_FIDELITY_MIN_CORR and med_mae <= cfg.D206_FIDELITY_MAX_MAE)
    result = {"per_holding": per, "median_corr": eng._r(med_corr), "median_mae": eng._r(med_mae),
              "min_corr": cfg.D206_FIDELITY_MIN_CORR, "max_mae": cfg.D206_FIDELITY_MAX_MAE,
              "pass": ok}
    if not ok:
        raise RuntimeError(
            f"FIDELITY-GUARD FAILED: median_corr={med_corr:.3f} (need >= {cfg.D206_FIDELITY_MIN_CORR}), "
            f"median_mae={med_mae:.4f} (need <= {cfg.D206_FIDELITY_MAX_MAE}). The mktval-implied "
            "total-return proxy does not match the frozen adjusted total-return index; test STOPS.")
    return result


# ===========================================================================
# Gate 5: realistic D-204 cost (entry/exit discount-Z strategy, 2019-2026 daily)
# ===========================================================================
def gate5_realistic_cost(z: pd.DataFrame, holdings: list[str]) -> dict:
    """Low-turnover discount-Z strategy (enter when z>=ENTRY_Z, exit when z<=EXIT_Z; hysteresis),
    priced with the D-204 realistic per-stock Roll+Kyle cost on 2019-2026 daily prices. Reports
    after-cost mean, breakeven bps vs realized cost, turnover/holding-period."""
    daily = pd.read_parquet(
        Path(cfg.D206_CLEAN_UNIVERSE_ROOT) / "adjusted_prices_2019_2026.parquet",
        columns=["date", "symbol", "adjusted_close", "value_tl"])
    daily = daily[daily["symbol"].isin(holdings)].copy()
    daily["date"] = pd.to_datetime(daily["date"])
    close = daily.pivot_table(index="date", columns="symbol", values="adjusted_close").sort_index()
    value_tl = daily.pivot_table(index="date", columns="symbol", values="value_tl").sort_index()
    rebal = eng.monthly_rebalance_dates(close.index, str(cfg.D206_OVERLAP_START),
                                        str(cfg.D206_OVERLAP_END))
    if len(rebal) < 4:
        return {"available": False, "note": "insufficient rebalance dates"}
    # in-position state per holding from discount-Z (hysteresis), look-ahead-safe (z known at t)
    baskets = []
    state = {h: False for h in holdings}
    for i in range(len(rebal) - 1):
        m = pd.Period(rebal[i], freq="M")
        cur = []
        for h in holdings:
            zv = z.at[m, h] if (m in z.index and h in z.columns) else np.nan
            if np.isfinite(zv):
                if zv >= cfg.D206_STRATEGY_ENTRY_Z:
                    state[h] = True
                elif zv <= cfg.D206_STRATEGY_EXIT_Z:
                    state[h] = False
            if state[h]:
                cur.append(h)
        baskets.append(cur)
    daily_ret = eng.clip_clean_returns(close)
    pmat = eng._period_return_matrix(daily_ret, rebal)
    cost = d204.per_stock_cost_panel(close, value_tl, rebal)
    net = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=cost["cost_roll"])
    free = d204.d204_basket_net_series(pmat, baskets, rebal, cost_map=None)
    bench = [float(np.nanmean(pmat.iloc[i].values)) if np.isfinite(pmat.iloc[i].values).any()
             else float("nan") for i in range(len(pmat))]
    rel_after = eng._relative(net["net"], bench)
    rel_free = eng._relative(free["net"], bench)
    be = d204.breakeven_cost_bps(free["net"], bench, free["turnover"])
    eff = d204.effective_flat_bps(net["cost"], net["turnover"])
    hp = d204.holding_period_stats(baskets, rebal, cadence_months=1)
    after_mean = float(np.nanmean([v for v in rel_after if np.isfinite(v)])) if rel_after else float("nan")
    return {"available": True,
            "n_periods": len(baskets),
            "after_cost_rel_mean": eng._r(after_mean),
            "cost_free_rel_mean": eng._r(float(np.nanmean([v for v in rel_free if np.isfinite(v)]))),
            "breakeven_bps": be["breakeven_bps"],
            "realistic_cost_bps": eng._r(eff),
            "mean_turnover": eng._r(float(np.nanmean([t for t in net["turnover"] if np.isfinite(t)]))),
            "holding_period": hp.get("summary", hp),
            "after_cost_positive": bool(np.isfinite(after_mean) and after_mean > 0)}


# ===========================================================================
# Combined verdict
# ===========================================================================
def d206_verdict(g1_sign_ok: bool, gate2: dict, gate3: dict, gate4: dict,
                 carry: dict, loho_res: dict, gate5: dict) -> dict:
    """SERAP / GERCEK-SINYAL / GERCEK-ama-tradeable-DEGIL, per the FROZEN combined rule."""
    g2_pass = bool(gate2.get("dk_t_pass") and gate2.get("wild_boot_pass")
                   and gate2.get("same_sign_pass"))
    g3_pass = bool(gate3.get("beats_null"))
    g4_pass = bool(gate4.get("both_positive"))
    carry_ok = bool(carry.get("trap_rejected_signal_survives")) if carry.get("available") else None
    loho_ok = bool(loho_res.get("robust"))
    cost_free_real = bool(g1_sign_ok and g2_pass and g3_pass and g4_pass and loho_ok
                          and (carry_ok is not False))
    reasons = []
    if not g1_sign_ok:
        reasons.append("gate1 coefficient sign WRONG (no mean-reversion)")
    if not g2_pass:
        reasons.append("gate2 significance FAIL (DK|t|/wild-boot/same-sign)")
    if not g3_pass:
        reasons.append("gate3 circular-shift null not beaten")
    if not g4_pass:
        reasons.append("gate4 not positive in both regimes")
    if not loho_ok:
        reasons.append("LOHO fragile (single-holding dominance)")
    if carry_ok is False:
        reasons.append("carry-trap: signal does not survive real-TLREF control")
    g5_after = bool(gate5.get("after_cost_positive")) if gate5.get("available") else False
    be = gate5.get("breakeven_bps")
    rc = gate5.get("realistic_cost_bps")
    tradeable = False
    if isinstance(be, (int, float)) and isinstance(rc, (int, float)) and rc and rc > 0:
        tradeable = bool(g5_after and be >= cfg.D206_BREAKEVEN_SAFETY_MULT * rc)
    elif be == "inf":
        tradeable = bool(g5_after)
    if not cost_free_real:
        headline = "SERAP"
        note = ("NAV-discount mean-reversion is NOT a real signal cost-free; the NAV-discount "
                "FIRST round (N<=3) is SERAP. Clean archive; honest elimination; NO celebration.")
    elif tradeable:
        headline = "GERCEK-SINYAL"
        note = ("Cost-free signal real AND retail-tradeable after realistic cost; a deploy "
                "CANDIDATE for the FULL RR-013 architecture (SEPARATE the project decision, NOT "
                "auto-deployed). SURPRISE vs the UNCERTAIN prior.")
    else:
        headline = "GERCEK-ama-tradeable-DEGIL"
        note = ("Cost-free signal real but not retail-tradeable (after-cost <= 0 or breakeven < "
                "2x realistic cost). Archive honestly.")
    return {"headline": headline, "reasons": reasons,
            "cost_free_real": cost_free_real, "tradeable": tradeable, "close_note": note,
            "oos_caveat": ("The 2009-2026 sample is dominated by high inflation with one short "
                           "disinflation episode; a true regime-normalization OOS is weak. N=6 "
                           "holdings, today-surviving = a selection. Time-series only; NO cross-"
                           "sectional generalization claimed.")}


# ===========================================================================
# Orchestrator
# ===========================================================================
def run_d206(stage0_path: Path | str = _STAGE0_DEFAULT, require_stage0: bool = True) -> dict:
    """Full D-206 measurement. RAISES without Stage-0 (pre-registration) and RAISES if the
    FIDELITY-GUARD fails. Returns the results dict (also written by the report step)."""
    stage0 = load_stage0(stage0_path, require_stage0=require_stage0)
    holdings = stage0_holdings(stage0)
    holding_names = list(holdings.keys())
    lags = cfg.D206_PRIMARY_HORIZON_MONTHS

    panels = build_monthly_panels()
    mk, dyld = panels["mktval"], panels["dyld"]

    fidelity = fidelity_guard(mk, dyld, holding_names)  # RAISES on failure

    discount = nav_discount_panel(mk, holdings)
    z = trailing_z(discount)
    fwd = forward_returns(mk, dyld)
    panel = _panel_long(z, fwd)

    # Gate 1 -- signal content (FE within coefficient)
    beta, se, dk_t = dk_within(panel["z"].values, panel["fwd"].values,
                               panel["holding"].values, panel["tid"].values, lags)
    g1_sign_ok = bool(np.isfinite(beta) and beta > 0)

    # Gate 2 -- significance (DK primary + wild-cluster bootstrap + per-holding NW + same-sign)
    boot = wild_cluster_bootstrap(panel, lags)
    phnw = per_holding_nw(z, fwd, lags)
    gate2 = {
        "driscoll_kraay_beta": eng._r(beta), "driscoll_kraay_se": eng._r(se),
        "driscoll_kraay_t": eng._r(dk_t), "dk_lags": lags,
        "dk_t_pass": bool(np.isfinite(dk_t) and abs(dk_t) >= cfg.D206_GATE_NW_T_MIN),
        "wild_boot_p": boot["p"], "wild_boot_n": boot["n"],
        "wild_boot_pass": bool(boot["p"] is not None and boot["p"] < 0.05),
        "per_holding_nw": phnw["per_holding"],
        "same_sign_frac": phnw["same_sign_frac"], "same_sign_pass": phnw["same_sign_pass"],
        "n_positive": phnw["n_positive"], "n_defined": phnw["n_defined"],
    }

    # Gate 3 -- circular-shift null
    gate3 = circular_shift_null(z, fwd, lags)

    # Gate 4 -- regime split
    gate4 = regime_betas(panel, lags)

    # Controls
    tlref_real = _load_real_tlref(panels)
    carry = carry_trap(panel, tlref_real, lags)
    loho_res = loho(z, fwd, lags, beta)
    z_detr = trailing_z(detrend_discount(discount))
    panel_detr = _panel_long(z_detr, fwd)
    b_detr, _, t_detr = dk_within(panel_detr["z"].values, panel_detr["fwd"].values,
                                  panel_detr["holding"].values, panel_detr["tid"].values, lags)
    detrend = {"beta_with_detrend": eng._r(b_detr), "dk_t_with_detrend": eng._r(t_detr),
               "beta_without_detrend": eng._r(beta),
               "sign_stable": bool(np.isfinite(b_detr) and np.sign(b_detr) == np.sign(beta))}

    # Cross-holding residual correlation (trap-5 transparency)
    xcorr = _avg_pairwise_residual_corr(z, fwd, beta)

    # Gate 5 -- realistic cost
    gate5 = gate5_realistic_cost(z, holding_names)

    verdict = d206_verdict(g1_sign_ok, gate2, gate3, gate4, carry, loho_res, gate5)

    # statsmodels DK cross-check (single regressor)
    dk_xcheck = _statsmodels_dk_crosscheck(panel, lags)

    coverage = {h: int(z[h].notna().sum()) for h in z.columns}
    return {
        "directive": "D-206", "phase": "NAV-discount mean-reversion (time-series, measurement-only)",
        "config_version": cfg.D206_CONFIG_VERSION,
        "candidate": cfg.D206_CANDIDATE, "candidate_label": cfg.D206_CANDIDATE_LABEL,
        "holdings": holding_names, "n_holdings": len(holding_names),
        "discount_z_coverage_months": coverage,
        "panel_n_obs": int(len(panel)),
        "harmonize_meta": panels["harmonize_meta"],
        "fidelity_guard": fidelity,
        "gate1_signal_content": {"fe_within_beta": eng._r(beta), "sign_positive": g1_sign_ok,
                                 "dk_t": eng._r(dk_t)},
        "gate2_significance": gate2,
        "gate2_dk_statsmodels_crosscheck": dk_xcheck,
        "gate3_circular_shift_null": gate3,
        "gate4_regime_split": gate4,
        "carry_trap_control": carry,
        "loho": loho_res,
        "detrend_trap1": detrend,
        "cross_holding_residual_corr": xcorr,
        "gate5_realistic_cost": gate5,
        "verdict": verdict,
    }


def _avg_pairwise_residual_corr(z: pd.DataFrame, fwd: pd.DataFrame, beta: float) -> dict:
    """Average pairwise correlation of per-holding FE residuals -- shows how much the Driscoll-
    Kraay SE leans on T vs on the (few, BIST-co-moving) N."""
    resid = {}
    for h in z.columns:
        if h not in fwd.columns:
            continue
        s = pd.DataFrame({"z": z[h], "f": fwd[h].reindex(z.index)}).dropna()
        if len(s) < 3:
            continue
        resid[h] = (s["f"] - s["f"].mean()) - beta * (s["z"] - s["z"].mean())
    rdf = pd.DataFrame(resid)
    if rdf.shape[1] < 2:
        return {"avg_pairwise_corr": None, "n_holdings": rdf.shape[1]}
    cm = rdf.corr()
    vals = cm.values[np.triu_indices_from(cm.values, k=1)]
    vals = vals[np.isfinite(vals)]
    return {"avg_pairwise_corr": eng._r(float(np.mean(vals))) if len(vals) else None,
            "n_holdings": rdf.shape[1]}


def _statsmodels_dk_crosscheck(panel: pd.DataFrame, lags: int) -> dict:
    """Independent Driscoll-Kraay via statsmodels cov_type='hac-groupsum' (FE dummies)."""
    if panel.empty or panel["holding"].nunique() < 2:
        return {"available": False}
    import statsmodels.api as sm
    dummies = pd.get_dummies(panel["holding"], prefix="h", drop_first=True).astype(float)
    X = sm.add_constant(pd.concat([panel[["z"]].reset_index(drop=True),
                                   dummies.reset_index(drop=True)], axis=1))
    try:
        m = sm.OLS(panel["fwd"].values, X.values).fit(
            cov_type="hac-groupsum",
            cov_kwds={"time": panel["tid"].values.astype(int), "maxlags": lags})
        zi = list(X.columns).index("z")
        return {"available": True, "beta": eng._r(float(m.params[zi])),
                "dk_t": eng._r(float(m.tvalues[zi]))}
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "note": str(exc)}


def _load_real_tlref(panels: dict) -> pd.Series | None:
    """Monthly real-TLREF = TLREF - YoY-TUFE (Timestamp-indexed month-end). None if snapshots
    are unavailable (carry control is then reported as unavailable)."""
    root = Path(__file__).parent.parent.parent / "data" / "snapshots"
    tlref_fp = root / f"{cfg.D206_TLREF_SNAPSHOT}.parquet"
    tufe_fp = root / f"{cfg.D206_TUFE_SNAPSHOT}.parquet"
    if not (tlref_fp.exists() and tufe_fp.exists()):
        return None
    try:
        tlref = pd.read_parquet(tlref_fp)
        tufe = pd.read_parquet(tufe_fp)
    except Exception:  # noqa: BLE001
        return None
    def _monthly(df):
        c = df.select_dtypes("number").columns
        s = df[c[0]] if len(c) else df.iloc[:, 0]
        s.index = pd.to_datetime(df.index if df.index.dtype.kind == "M" else df.iloc[:, 0])
        return s.groupby(s.index.to_period("M")).last()
    try:
        tl = _monthly(tlref)
        tf = _monthly(tufe)
        tufe_yoy = tf / tf.shift(12) - 1.0
        real = (tl / 100.0 if tl.median() > 1 else tl) - tufe_yoy
        real.index = real.index.to_timestamp("M")
        return real
    except Exception:  # noqa: BLE001
        return None

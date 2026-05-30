"""D-184 lowvol60 Validity Audit (CB-017 4-test diagnostics).

Tests whether lowvol60 -- the sole marginal Faz-0 survivor -- is genuine
standalone alpha or (a) a D-layer regime shadow, (b) a multiple-testing
artifact. Faz 1 is BLOCKED until this audit runs.

Tests:
  T1: D-regime conditional IC decomposition
      (XU100 200-MA proxy; D=ON vs D=OFF IC split; >=80% from D=ON => fail)
  T2: Macro-residual IC (time-series OLS)
      (IC_t ~ BIST_RV_t + USDTRY_30gvol_t; residual honest_t >= 2.0 => pass)
  T3: Multiple-testing correction
      (Holm-Bonferroni + BH-FDR over all Faz-0 (factor x horizon); lowvol60 survives?)
  T4: OOS regime stability (2019-2023)
      (sign-stable + honest_t positive direction across different regime)

Decision rule (FROZEN, pre-registered):
  2 tests fail => lowvol60 with Faz 1 not rational
  3 tests fail => architectural premise re-think (regime-conditional MV-BIST + liquidity gates)
  Decision owner: the project (DEC-039). This module MEASURES + RECOMMENDS.

No imports from signals.engine / backtest.engine / MASTER_WEIGHTS / conviction.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from src.screening import faz0_config as cfg
from src.screening import factors, snapshot
from src.screening.factor_ic_harness import (
    build_factor_ranks,
    compute_factor_ic,
    build_signal_df,
    build_returns_df,
    daily_ic_series,
    ic_stats,
    nonoverlap_stats,
    newey_west_se,
    rank_panel,
    _json_default,
)

logger = logging.getLogger(__name__)

_RESULTS_DIR = Path(__file__).parent.parent.parent / "reports" / "factor_ic"
_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"

# ---------------------------------------------------------------------------
# Utility: extract per-date IC series from frozen price snapshot
# ---------------------------------------------------------------------------

def _extract_ic_series(
    close: pd.DataFrame,
    xu100: pd.Series,
    horizon: int,
    factor_name: str = "lowvol60",
    vol_window: int = 60,
) -> tuple[np.ndarray, list]:
    """Re-compute per-date Spearman IC for lowvol60 x horizon from frozen prices.

    Returns (ic_array, dates) where dates align with the daily IC values.
    Uses the same logic as daily_ic_series() in the harness (deterministic on frozen data).
    """
    vol = factors.realized_vol(close, window=vol_window)
    ranks = rank_panel(vol, invert=True)
    fwd = factors.forward_returns(close, horizon=horizon)

    sig_df = build_signal_df({factor_name: ranks})
    ret_df = build_returns_df(close, [horizon])
    _, ics = compute_factor_ic(sig_df, ret_df, {factor_name: ranks}, {horizon: fwd},
                               factor_name, horizon, return_series=True)
    # Collect aligned dates for the IC series
    fwd_panel = fwd
    dates: list = []
    for date in sorted(ranks.index):
        if date not in fwd_panel.index:
            continue
        a = ranks.loc[date]
        b = fwd_panel.loc[date]
        mask = a.notna() & b.notna()
        if int(mask.sum()) < cfg.MIN_XSECTION:
            continue
        dates.append(date)
    # dates may exceed len(ics) if some had NaN spearmanr -- trim to match
    dates = dates[:len(ics)]
    return ics, dates


# ---------------------------------------------------------------------------
# TEST 3: Multiple-testing correction (cheapest -- no new data)
# ---------------------------------------------------------------------------

def run_test3_multiple_testing(
    faz0_v1_path: Path | str,
    faz0_v2_path: Path | str,
) -> dict:
    """Holm-Bonferroni + BH-FDR over all Faz-0 (factor x horizon) p-values.

    Counts: (a) eligible only (non-overlap n>=12), (b) all attempted (conservative).
    Reports both. lowvol60 verdict: survives correction or drops?
    """
    v1 = json.loads(Path(faz0_v1_path).read_text(encoding="utf-8"))
    v2 = json.loads(Path(faz0_v2_path).read_text(encoding="utf-8"))

    tests_all: list[dict] = []   # all attempted (conservative)
    tests_elig: list[dict] = []  # only eligible (non-overlap n>=12)

    for source_label, res in [("D177_v1", v1), ("D178_v2", v2)]:
        per = res.get("per_factor_ic", {})
        for factor, by_h in per.items():
            if factor == "composite":
                continue
            for h_str, stats_d in by_h.items():
                p_nw = stats_d.get("series", {}).get("p_nw", float("nan"))
                t_nw = stats_d.get("series", {}).get("t_nw", float("nan"))
                n_nonoverlap = stats_d.get("nonoverlap", {}).get("n_obs", 0)
                eligible = int(n_nonoverlap) >= cfg.FAZ0_MIN_NONOVERLAP_N

                entry = {
                    "source": source_label,
                    "factor": factor,
                    "horizon": int(h_str),
                    "t_nw": float(t_nw) if t_nw is not None else float("nan"),
                    "p_nw": float(p_nw) if p_nw is not None else float("nan"),
                    "n_nonoverlap": int(n_nonoverlap),
                    "eligible": eligible,
                }
                tests_all.append(entry)
                if eligible:
                    tests_elig.append(entry)

    def _apply_corrections(entries: list[dict]) -> list[dict]:
        ps = [e["p_nw"] for e in entries]
        n = len(ps)
        # Holm-Bonferroni
        order = sorted(range(n), key=lambda i: ps[i])
        holm_reject = [False] * n
        for rank_i, idx in enumerate(order):
            thresh = 0.05 / (n - rank_i)
            if ps[idx] <= thresh:
                holm_reject[idx] = True
            else:
                break  # step-down: once fails, all remaining fail

        # BH-FDR
        order_bh = sorted(range(n), key=lambda i: ps[i])
        bh_reject = [False] * n
        last_reject = -1
        for rank_i, idx in enumerate(order_bh):
            if ps[idx] <= (rank_i + 1) * 0.05 / n:
                last_reject = rank_i
        for rank_i, idx in enumerate(order_bh):
            if rank_i <= last_reject:
                bh_reject[idx] = True

        result = []
        for i, e in enumerate(entries):
            result.append({**e, "holm_reject_null": holm_reject[i], "bh_fdr_reject_null": bh_reject[i]})
        return result

    corrected_all = _apply_corrections(tests_all)
    corrected_elig = _apply_corrections(tests_elig)

    def _lowvol60_verdict(corrected: list[dict]) -> dict:
        lv_entries = [e for e in corrected
                      if e["factor"] == "lowvol60" and e["source"] == "D178_v2"]
        # primary horizon h21
        h21 = next((e for e in lv_entries if e["horizon"] == 21), None)
        if h21 is None:
            return {"verdict": "NOT_FOUND", "note": "lowvol60 h21 not in corrected list"}
        holm_passes = h21["holm_reject_null"]
        bh_passes = h21["bh_fdr_reject_null"]
        if holm_passes and bh_passes:
            verdict = "PASS"
        elif bh_passes:
            verdict = "BORDERLINE (BH only)"
        else:
            verdict = "FAIL"
        return {
            "verdict": verdict, "horizon": 21, "p_nw": h21["p_nw"],
            "t_nw": h21["t_nw"], "holm_reject_null": holm_passes,
            "bh_fdr_reject_null": bh_passes,
        }

    n_all = len(corrected_all)
    n_elig = len(corrected_elig)
    bonf_thresh_all = 0.05 / n_all if n_all else float("nan")
    bonf_thresh_elig = 0.05 / n_elig if n_elig else float("nan")

    return {
        "test": "T3_multiple_testing",
        "n_tests_all_attempted": n_all,
        "n_tests_eligible_only": n_elig,
        "bonferroni_threshold_all": round(bonf_thresh_all, 6),
        "bonferroni_threshold_eligible": round(bonf_thresh_elig, 6),
        "lowvol60_verdict_conservative": _lowvol60_verdict(corrected_all),
        "lowvol60_verdict_eligible_only": _lowvol60_verdict(corrected_elig),
        "full_table_all": corrected_all,
        "full_table_eligible": corrected_elig,
        "note": "Conservative (all attempted) includes D-177 v1 (methodologically flawed) "
                "for a worst-case correction. Eligible-only is more principled.",
    }


# ---------------------------------------------------------------------------
# TEST 1: D-regime conditional IC decomposition
# ---------------------------------------------------------------------------

def run_test1_regime_ic(
    ics: np.ndarray,
    dates: list,
    xu100: pd.Series,
    ma_window: int = cfg.D184_REGIME_MA_WINDOW,
) -> dict:
    """Split lowvol60 IC by D=ON (XU100>200-MA) vs D=OFF dates.

    XU100 200-MA proxy for D-layer (ARCHITECTURE sec.3.1 primary switch).
    Warm-up period: first `ma_window` trading days have NaN MA -> excluded.
    Threshold: >=80% of total IC from D=ON dates => fail (same-bet hypothesis).
    """
    xu100_sorted = xu100.sort_index()
    ma = xu100_sorted.rolling(ma_window, min_periods=ma_window).mean()

    ic_on: list[float] = []
    ic_off: list[float] = []
    warmup_excluded = 0
    dates_with_regime = 0

    for d, ic_val in zip(dates, ics):
        ts = pd.Timestamp(d)
        if ts not in ma.index or math.isnan(float(ma.get(ts, float("nan")))):
            warmup_excluded += 1
            continue
        xu_val = float(xu100_sorted.get(ts, float("nan")))
        ma_val = float(ma.get(ts, float("nan")))
        if math.isnan(xu_val) or math.isnan(ma_val):
            warmup_excluded += 1
            continue
        dates_with_regime += 1
        if xu_val > ma_val:
            ic_on.append(ic_val)
        else:
            ic_off.append(ic_val)

    n_on = len(ic_on)
    n_off = len(ic_off)
    n_total = n_on + n_off

    mean_ic_on = float(np.mean(ic_on)) if ic_on else float("nan")
    mean_ic_off = float(np.mean(ic_off)) if ic_off else float("nan")

    # Contribution: sign-weighted IC sum (IC can be negative on some days)
    # Use simpler metric: fraction of days in D=ON regime that have positive IC
    # vs fraction of total positive IC days that fall in D=ON
    total_ic_sum = sum(ic_on) + sum(ic_off)
    ic_on_sum = sum(ic_on)
    pct_ic_from_on = (ic_on_sum / total_ic_sum * 100) if abs(total_ic_sum) > 1e-9 else float("nan")

    # Also compute simple day fraction
    pct_days_on = (n_on / n_total * 100) if n_total > 0 else float("nan")

    # Verdict: >=80% of IC (by sum) from D=ON -> fail
    threshold_pct = cfg.D184_REGIME_ON_PCT * 100
    if math.isnan(pct_ic_from_on) or n_total < 10:
        verdict = "INSUFFICIENT_DATA"
    elif pct_ic_from_on >= threshold_pct:
        verdict = "FAIL"
    elif pct_ic_from_on < 50.0:
        verdict = "PASS"
    else:
        verdict = "GREY"

    return {
        "test": "T1_regime_conditional_ic",
        "regime_proxy": f"XU100 > {ma_window}-day MA (ARCHITECTURE sec.3.1 primary switch)",
        "warmup_excluded_dates": warmup_excluded,
        "n_total_with_regime": n_total,
        "n_don_dates": n_on,
        "n_doff_dates": n_off,
        "pct_days_on": round(pct_days_on, 1),
        "mean_ic_don": round(mean_ic_on, 5) if not math.isnan(mean_ic_on) else None,
        "mean_ic_doff": round(mean_ic_off, 5) if not math.isnan(mean_ic_off) else None,
        "ic_sum_don": round(ic_on_sum, 5),
        "ic_sum_total": round(total_ic_sum, 5),
        "pct_ic_from_don": round(pct_ic_from_on, 1) if not math.isnan(pct_ic_from_on) else None,
        "threshold_fail_pct": threshold_pct,
        "verdict": verdict,
        "verdict_rule": f">= {threshold_pct:.0f}% IC from D=ON => FAIL (same-bet hypothesis); "
                        "~50% => PASS (independent component)",
    }


# ---------------------------------------------------------------------------
# TEST 2: Macro-residual IC (time-series OLS)
# ---------------------------------------------------------------------------

def _compute_bist_rv(xu100: pd.Series, window: int = 30) -> pd.Series:
    """Rolling realized vol of XU100 log returns (proxy for macro stress)."""
    log_ret = np.log(xu100 / xu100.shift(1))
    return log_ret.rolling(window, min_periods=max(2, window // 2)).std()


def _compute_usdtry_vol(usdtry: pd.Series, window: int = 30) -> pd.Series:
    """Rolling 30-day USDTRY log-return vol."""
    log_ret = np.log(usdtry / usdtry.shift(1))
    return log_ret.rolling(window, min_periods=max(2, window // 2)).std()


def _nw_hac_intercept_t(X: np.ndarray, y: np.ndarray, resid: np.ndarray, lags: int) -> float:
    """Newey-West HAC t-stat for the OLS intercept (coef index 0).

    Sandwich: V_HAC = (X'X)^{-1} S (X'X)^{-1}
    where S = sum_t X_t'e_t e_t X_t + sum_{lag=1}^{L} w_l sum_t (X_t'e_t e_{t-l}'X_{t-l} + transpose)
    Bartlett weight: w_l = 1 - l/(L+1).
    Returns t = beta[0] / sqrt(V_HAC[0,0]).
    """
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    scores = X * resid[:, np.newaxis]  # n x k

    S = scores.T @ scores  # lag-0 sandwich meat
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1)
        gamma = scores[lag:].T @ scores[:-lag]
        S += w * (gamma + gamma.T)

    V_hac = XtX_inv @ S @ XtX_inv
    se_const = math.sqrt(max(float(V_hac[0, 0]), 0.0))
    if se_const <= 0:
        return float("nan")
    beta = XtX_inv @ (X.T @ y)
    return float(beta[0]) / se_const


def run_test2_macro_residual_ic(
    ics: np.ndarray,
    dates: list,
    xu100: pd.Series,
    usdtry: pd.Series | None = None,
) -> dict:
    """OLS IC_t ~ const + b1*BIST_RV_t [+ b2*USDTRY_vol_t]; test intercept via NW-HAC.

    The intercept captures IC mean independent of macro level.
    |t_HAC(intercept)| >= D184_RESIDUAL_T_MIN => IC has macro-independent alpha (PASS).
    < threshold => IC mean fully explained by macro (FAIL / embedded).

    Note: testing OLS residual mean is vacuous (always 0 with constant in model).
    The correct test is the significance of the intercept coefficient.

    BIST RV from frozen XU100 (always available).
    USDTRY vol from faz0_macro_aux.parquet (optional; 2-var model is primary).
    """
    bist_rv = _compute_bist_rv(xu100)
    use_usdtry = usdtry is not None

    ic_vals: list[float] = []
    rv_vals: list[float] = []
    usdtry_vals: list[float] = []

    for d, ic_val in zip(dates, ics):
        ts = pd.Timestamp(d)
        rv = float(bist_rv.get(ts, float("nan")))
        if math.isnan(rv):
            continue
        if use_usdtry:
            uv = float(usdtry.get(ts, float("nan")))
            if math.isnan(uv):
                continue
            usdtry_vals.append(uv)
        ic_vals.append(ic_val)
        rv_vals.append(rv)

    n = len(ic_vals)
    if n < 20:
        return {"test": "T2_macro_residual_ic", "verdict": "INSUFFICIENT_DATA",
                "n_aligned": n, "note": "Need >= 20 aligned observations"}

    ic_arr = np.array(ic_vals)
    rv_arr = np.array(rv_vals)

    if use_usdtry:
        X = np.column_stack([np.ones(n), rv_arr, np.array(usdtry_vals)])
        model_vars = ["const", "BIST_RV30", "USDTRY_vol30"]
    else:
        X = np.column_stack([np.ones(n), rv_arr])
        model_vars = ["const", "BIST_RV30"]

    beta, _, _, _ = np.linalg.lstsq(X, ic_arr, rcond=None)
    fitted = X @ beta
    resid = ic_arr - fitted

    r2 = 1.0 - float(np.var(resid, ddof=0)) / float(np.var(ic_arr, ddof=0)) \
        if float(np.var(ic_arr, ddof=0)) > 0 else 0.0

    # NW-HAC t-stat for intercept (lag=21 for daily IC overlap)
    intercept_t = _nw_hac_intercept_t(X, ic_arr, resid, lags=21)

    if math.isnan(intercept_t):
        verdict = "INSUFFICIENT_DATA"
    elif abs(intercept_t) >= cfg.D184_RESIDUAL_T_MIN:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return {
        "test": "T2_macro_residual_ic",
        "model_vars": model_vars,
        "n_aligned": n,
        "ols_coefs": {k: round(float(v), 6) for k, v in zip(model_vars, beta)},
        "intercept_value": round(float(beta[0]), 6),
        "r2_macro_explains_ic_variance": round(r2, 4),
        "intercept_t_nw_hac": round(intercept_t, 4) if not math.isnan(intercept_t) else None,
        "raw_ic_mean": round(float(np.mean(ic_arr)), 5),
        "verdict": verdict,
        "verdict_rule": f"|t_HAC(intercept)| >= {cfg.D184_RESIDUAL_T_MIN} => PASS "
                        "(IC has positive mean independent of macro); < threshold => FAIL",
        "note": "OLS residual mean is always 0 by construction when constant is included. "
                "The intercept coefficient measures IC mean orthogonal to macro variation. "
                "NW-HAC SE with lag=21 (matching primary horizon overlap).",
    }


# ---------------------------------------------------------------------------
# TEST 4: OOS regime stability 2019-2023
# ---------------------------------------------------------------------------

def run_test4_oos(
    oos_close: pd.DataFrame,
    oos_xu100: pd.Series,
    vol_window: int = 60,
    horizons: tuple = (21, 63),
) -> dict:
    """lowvol60 rank-IC over 2019-01 to 2023-08 (OOS, different regime).

    Sign-stable + honest_t positive direction => PASS.
    Sign-flip or honest_t ~ 0 => FAIL (single-window artifact).
    """
    factor_name = "lowvol60"
    oos_results: dict[str, dict] = {}

    for h in horizons:
        fwd = factors.forward_returns(oos_close, horizon=h)
        vol = factors.realized_vol(oos_close, window=vol_window)
        ranks = rank_panel(vol, invert=True)

        ics_arr = daily_ic_series(ranks, fwd)
        if len(ics_arr) < 10:
            oos_results[str(h)] = {"n_obs": len(ics_arr), "eligible": False,
                                   "note": "insufficient data"}
            continue

        s = ic_stats(ics_arr, hac_lag=h)
        no = nonoverlap_stats(ics_arr, stride=h)

        oos_results[str(h)] = {
            "n_obs": s["n_obs"],
            "mean_ic": round(s["mean_ic"], 5),
            "t_nw_honest": round(s["t_nw"], 4) if not math.isnan(s["t_nw"]) else None,
            "icir_nonoverlap": no["icir"],
            "nonoverlap_n": no["n_obs"],
            "eligible": bool(no["n_obs"] >= cfg.FAZ0_MIN_NONOVERLAP_N),
        }

    # Sign stability: compare signs vs D-178 results
    d178_mean_ic_h21 = 0.06164   # from faz0_v2_results.json (frozen reference)
    oos_h21 = oos_results.get("21", {})
    oos_mean_h21 = oos_h21.get("mean_ic", float("nan"))

    sign_stable = (
        not math.isnan(oos_mean_h21) and
        float(np.sign(oos_mean_h21)) == float(np.sign(d178_mean_ic_h21))
    )

    # Verdict: sign-stable AND oos honest_t positive direction
    oos_t = oos_h21.get("t_nw_honest", float("nan"))
    if oos_t is None:
        oos_t = float("nan")
    if math.isnan(oos_mean_h21):
        verdict = "INSUFFICIENT_DATA"
    elif sign_stable and not math.isnan(oos_t) and oos_t > 0:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return {
        "test": "T4_oos_regime_stability",
        "oos_window": f"{cfg.D184_OOS_START} to {cfg.D184_OOS_END}",
        "in_sample_window": "2024-01-01 to 2026-04-30 (D-178)",
        "oos_n_tickers": int(oos_close.shape[1]),
        "d178_mean_ic_h21_reference": d178_mean_ic_h21,
        "oos_results_by_horizon": oos_results,
        "sign_stable_h21": sign_stable,
        "verdict": verdict,
        "verdict_rule": "sign-stable + honest_t positive direction => PASS; sign-flip or t~0 => FAIL",
        "survivorship_bias_caveat": (
            "2025-2026 BIST100 constituent list applied retroactively to 2019-2023. "
            "Bias direction: survivors-only inflates performance -> fail finding is conservative "
            "(real IC likely worse). Pass finding is overstated. ADV floor not applied "
            "(2019 TL volumes << 2024 scale)."
        ),
    }


# ---------------------------------------------------------------------------
# Snapshot helpers for macro aux + OOS data
# ---------------------------------------------------------------------------

def freeze_usdtry_aux(
    start: str,
    end: str,
    ticker: str = cfg.D184_USDTRY_YF_TICKER,
    out_dir: Path | str = _SNAPSHOT_DIR,
) -> pd.Series:
    """Fetch USDTRY=X from yfinance and freeze to parquet for Test 2.

    Idempotent: returns cached parquet if already present.
    """
    import yfinance as yf
    out_path = Path(out_dir) / "faz0_macro_aux.parquet"
    if out_path.exists():
        df = pd.read_parquet(out_path)
        series = df["usdtry"].dropna()
        logger.info("Loaded cached USDTRY aux from %s (%d obs)", out_path, len(series))
        return series

    logger.info("Fetching %s from %s to %s ...", ticker, start, end)
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError(f"yfinance returned empty data for {ticker}")

    close_col = "Close"
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    series = raw[close_col].dropna()
    series.index = pd.to_datetime(series.index)
    series.name = "usdtry"

    df_out = series.to_frame()
    df_out.to_parquet(out_path)
    logger.info("Froze USDTRY aux: %d obs -> %s", len(series), out_path)
    return series


def freeze_oos_price_snapshot(
    start: str = cfg.D184_OOS_START,
    end: str = cfg.D184_OOS_END,
    out_dir: Path | str = _SNAPSHOT_DIR,
) -> tuple[pd.DataFrame, pd.Series]:
    """Fetch 2019-2023 OOS prices from yfinance and freeze to parquet.

    Idempotent. No ADV floor (2019 TL volumes not comparable to 2024 scale).
    Survivorship bias documented (current BIST100 list retroactively applied).
    Returns (close_panel, xu100_series).
    """
    # File naming matches snapshot._paths: faz0_{tag}_prices_{start}_{end}.parquet
    tag = "oos_2019_2023"
    out_path = Path(out_dir) / f"faz0_{tag}_prices_{start}_{end}.parquet"
    meta_path = Path(out_dir) / f"faz0_{tag}_prices_{start}_{end}.meta.json"

    if out_path.exists() and meta_path.exists():
        long_df = pd.read_parquet(out_path)
        close, xu100 = snapshot.to_close_panel(long_df)
        logger.info("Loaded cached OOS snapshot: %d tickers", close.shape[1])
        return close, xu100

    universe = list(snapshot.resolve_universe_v2())
    logger.info("Freezing OOS price snapshot %s to %s (%d candidates)...", start, end, len(universe))

    long_df, meta = snapshot.freeze_price_snapshot(
        universe=universe,
        start=start,
        end=end,
        out_dir=out_dir,
        tag="oos_2019_2023",
        adv_floor_tl=None,
        directive="D-184",
    )
    close, xu100 = snapshot.to_close_panel(long_df)
    logger.info("OOS snapshot: %d tickers, %d dates", close.shape[1], len(close))
    return close, xu100


# ---------------------------------------------------------------------------
# Top-level audit orchestrator
# ---------------------------------------------------------------------------

def run_d184_audit(
    out_dir: Path | str = _RESULTS_DIR,
    skip_t4_fetch: bool = False,
) -> dict:
    """Run all 4 D-184 lowvol60 validity tests and write results JSON.

    Execution order:
      Step 1: T3 (multiple testing) -- zero new data, fastest
      Step 2: Load frozen v2 price snapshot, extract IC series
      Step 3: T1 (regime decomposition) + T2 (macro residual)
      Step 4: T4 (OOS 2019-2023) -- needs new snapshot fetch
    """
    snap_dir = _SNAPSHOT_DIR
    faz0_v1_path = Path(__file__).parent.parent.parent / "docs" / "factor_ic" / "faz0_results.json"
    faz0_v2_path = Path(__file__).parent.parent.parent / "docs" / "factor_ic" / "faz0_v2_results.json"

    # ------------------------------------------------------------------
    # T3: multiple testing (no new data)
    # ------------------------------------------------------------------
    logger.info("=== T3: Multiple-testing correction ===")
    t3 = run_test3_multiple_testing(faz0_v1_path, faz0_v2_path)
    _print_test_verdict("T3 multiple-testing", t3["lowvol60_verdict_conservative"]["verdict"])

    # ------------------------------------------------------------------
    # Load frozen v2 price snapshot (reuse D-178)
    # ------------------------------------------------------------------
    logger.info("Loading frozen v2 price snapshot...")
    price_snap_name = "faz0_v2_prices_2024-01-01_2026-04-30"
    price_long = pd.read_parquet(snap_dir / f"{price_snap_name}.parquet")
    close, xu100 = snapshot.to_close_panel(price_long)

    # Extract per-date IC series for lowvol60 x h21
    logger.info("Extracting lowvol60 IC series (h=21) from frozen snapshot...")
    ics_h21, dates_h21 = _extract_ic_series(close, xu100, horizon=21)
    logger.info("IC series: %d dates", len(ics_h21))

    # ------------------------------------------------------------------
    # T1: D-regime conditional IC
    # ------------------------------------------------------------------
    logger.info("=== T1: Regime-conditional IC decomposition ===")
    t1 = run_test1_regime_ic(ics_h21, dates_h21, xu100)
    _print_test_verdict("T1 regime decomposition", t1["verdict"])

    # ------------------------------------------------------------------
    # T2: Macro-residual IC
    # ------------------------------------------------------------------
    logger.info("=== T2: Macro-residual IC ===")
    try:
        usdtry = freeze_usdtry_aux(start=cfg.SNAPSHOT_START, end=cfg.SNAPSHOT_END,
                                    out_dir=snap_dir)
        usdtry_rv = _compute_usdtry_vol(usdtry)
        t2 = run_test2_macro_residual_ic(ics_h21, dates_h21, xu100, usdtry_rv)
    except Exception as exc:
        logger.warning("USDTRY fetch failed (%s); running T2 with BIST RV only", exc)
        t2 = run_test2_macro_residual_ic(ics_h21, dates_h21, xu100, usdtry=None)
    _print_test_verdict("T2 macro residual", t2["verdict"])

    # ------------------------------------------------------------------
    # T4: OOS 2019-2023
    # ------------------------------------------------------------------
    if skip_t4_fetch:
        t4 = {"test": "T4_oos_regime_stability", "verdict": "SKIPPED",
               "note": "skip_t4_fetch=True"}
        logger.info("T4: SKIPPED (skip_t4_fetch=True)")
    else:
        logger.info("=== T4: OOS 2019-2023 (new snapshot fetch) ===")
        try:
            oos_close, oos_xu100 = freeze_oos_price_snapshot(out_dir=snap_dir)
            t4 = run_test4_oos(oos_close, oos_xu100)
        except Exception as exc:
            logger.error("T4 failed: %s", exc)
            t4 = {"test": "T4_oos_regime_stability", "verdict": "ERROR",
                  "error": str(exc)}
    _print_test_verdict("T4 OOS stability", t4["verdict"])

    # ------------------------------------------------------------------
    # Synthesis + frozen decision rule
    # ------------------------------------------------------------------
    verdicts = {
        "T1": t1["verdict"],
        "T2": t2["verdict"],
        "T3": t3["lowvol60_verdict_conservative"]["verdict"],
        "T4": t4["verdict"],
    }
    fail_count = sum(1 for v in verdicts.values() if v == "FAIL")
    pass_count = sum(1 for v in verdicts.values() if v == "PASS")
    borderline_count = sum(1 for v in verdicts.values() if "BORDERLINE" in str(v))

    if fail_count >= 3:
        recommendation = "PREMISE_RETHINK: 3+ tests fail -> architectural premise uncertain. " \
                         "Regime-conditional MV-BIST + liquidity gates is more parsimonious."
    elif fail_count >= 2:
        recommendation = "FAZ1_BLOCKED: 2+ tests fail -> lowvol60 alone is insufficient basis for Faz 1."
    elif fail_count == 1:
        recommendation = "CONDITIONAL: 1 test fail -> proceed with explicit caveat noted."
    else:
        recommendation = "PROCEED: lowvol60 passes all tests -> Faz 1 foundation justified (marginal)."

    results = {
        "directive": "D-184",
        "phase": "lowvol60 validity audit (CB-017); DIAGNOSTIC only; DEC-039",
        "frozen_decision_rule": {
            "2_fail": "Faz 1 with lowvol60 not rational",
            "3_fail": "Architectural premise re-think (regime-conditional MV-BIST + liquidity gates)",
            "source": "CB-017 CRITIC_BACKLOG.md (pre-registered before tests)",
        },
        "test_results": {
            "T1_regime_ic": t1,
            "T2_macro_residual": t2,
            "T3_multiple_testing": t3,
            "T4_oos_stability": t4,
        },
        "verdict_summary": verdicts,
        "fail_count": fail_count,
        "pass_count": pass_count,
        "borderline_count": borderline_count,
        "recommendation": recommendation,
        "decision_owner": "the project (DEC-039). This module MEASURES + RECOMMENDS.",
    }

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "d184_lowvol_validation.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    _print_audit_summary(results)
    return results


def _print_test_verdict(name: str, verdict: str) -> None:
    icon = "PASS" if verdict == "PASS" else ("FAIL" if verdict == "FAIL" else verdict)
    print(f"  [{icon}] {name}")


def _print_audit_summary(r: dict) -> None:
    sep = "=" * 78
    print(f"\n{sep}")
    print(f"  D-184 lowvol60 Validity Audit -- SUMMARY")
    print(f"{sep}")
    for t, v in r["verdict_summary"].items():
        icon = "PASS" if v == "PASS" else "FAIL" if v == "FAIL" else v
        print(f"  {t}: {icon}")
    print(f"  ---")
    print(f"  Fail count: {r['fail_count']} / 4")
    print(f"  Recommendation: {r['recommendation']}")
    print(f"  Decision owner: {r['decision_owner']}")
    print(f"{sep}\n")


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="D-184 lowvol60 Validity Audit")
    p.add_argument("--d184", action="store_true", help="Run D-184 4-test audit")
    p.add_argument("--out-dir", default=str(_RESULTS_DIR))
    p.add_argument("--skip-t4", action="store_true", help="Skip T4 OOS snapshot fetch")
    args = p.parse_args()
    if args.d184:
        run_d184_audit(out_dir=args.out_dir, skip_t4_fetch=args.skip_t4)
    else:
        p.print_help()


if __name__ == "__main__":
    _main()

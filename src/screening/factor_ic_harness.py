"""Faz 0 Factor IC Validation Harness. D-177 / SPEC_PIVOT_ARCHITECTURE_1 sec.4.

MEASUREMENT only -- validates candidate factors (RS-vs-XU100, low-vol) by
standalone cross-sectional Spearman rank-IC BEFORE they enter any composite.
Does not produce signals, open trades, or finalize the factor set (DEC-039:
decision is the project's; the harness RECOMMENDS).

Reuses (green-field NOT allowed, ARCHITECTURE sec.3.5):
- ic_calculator.ICCalculator.compute_ic  -> authoritative Spearman rank-IC/ICIR/t/p
- short_interest_normalizer.compute_universe_percentiles -> cross-sectional rank
- screening.factors / screening.snapshot

IC = SPEARMAN (rank), not Pearson: Pearson absorbs tail magnitude and would
double-count with TEST 2; Spearman is tail-insensitive so TEST 2 stays
orthogonal. The harness re-derives the daily IC series locally (for Newey-West
HAC + CI) and ASSERTS equivalence with ICCalculator at its reporting precision
(5 decimals); ic_source records "primitive" (or "fallback" if it ever diverges).

No composite/conviction/MASTER_WEIGHTS or signal/backtest engine imports.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.analytics.ic_calculator import ICCalculator
from src.data.short_interest_normalizer import compute_universe_percentiles
from src.screening import faz0_config as cfg
from src.screening import factors, snapshot

logger = logging.getLogger(__name__)

_RESULTS_DIR = Path(__file__).parent.parent.parent / "reports" / "factor_ic"


# ---------------------------------------------------------------------------
# Pure helpers (unit-testable, deterministic)
# ---------------------------------------------------------------------------

def rank_panel(factor: pd.DataFrame, invert: bool = False) -> pd.DataFrame:
    """Per-date cross-sectional rank [0,1] via compute_universe_percentiles.

    invert=True (low-vol): low value -> high rank (rank = 1 - percentile).
    """
    out = pd.DataFrame(index=factor.index, columns=factor.columns, dtype=float)
    for date in factor.index:
        row = factor.loc[date].dropna()
        if row.empty:
            continue
        pct = compute_universe_percentiles(row.to_dict())
        for sym, p in pct.items():
            out.at[date, sym] = (1.0 - p) if invert else p
    return out


def daily_ic_series(
    signal: pd.DataFrame,
    fwd: pd.DataFrame,
    min_xsection: int = cfg.MIN_XSECTION,
) -> np.ndarray:
    """Daily cross-sectional Spearman IC of `signal` vs `fwd` (same panels).

    Mirrors ic_calculator's per-day rule (>= min_xsection symbols/day). Returns
    the array of per-date ICs (NaN days dropped). Deterministic.
    """
    dates = sorted(signal.index)
    ics: list[float] = []
    for date in dates:
        if date not in fwd.index:
            continue
        a = signal.loc[date]
        b = fwd.loc[date]
        mask = a.notna() & b.notna()
        if int(mask.sum()) < min_xsection:
            continue
        ic, _ = stats.spearmanr(a[mask].to_numpy(), b[mask].to_numpy())
        if not np.isnan(ic):
            ics.append(float(ic))
    return np.array(ics, dtype=float)


def newey_west_se(ics: np.ndarray, lags: int = cfg.NW_LAGS) -> float:
    """HAC standard error of the mean of an IC series (Bartlett kernel).

    Mirrors statistical_validation.sharpe_newey_west variance logic.
    """
    n = len(ics)
    if n < lags + 2:
        return float("nan")
    mu = float(np.mean(ics))
    var_nw = float(np.var(ics, ddof=1))
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1)  # bartlett kernel
        cov = float(np.mean((ics[lag:] - mu) * (ics[:-lag] - mu)))
        var_nw += 2.0 * weight * cov
    if var_nw <= 0:
        return float("nan")
    return math.sqrt(var_nw / n)


def ic_stats(ics: np.ndarray, lags: int = cfg.NW_LAGS, hac_lag: int | None = None) -> dict:
    """Aggregate IC series -> mean/std/ICIR/naive-t/p/CI + Newey-West HAC t/p.

    hac_lag (D-178): Bartlett bandwidth for the HONEST (overlap-corrected) t.
    For an h-day forward return the daily IC series is autocorrelated up to ~h;
    pass hac_lag=h so honest_t deflates the overlap-inflated naive_t.
    """
    n = int(len(ics))
    if n == 0:
        return {"n_obs": 0, "mean_ic": float("nan"), "std_ic": float("nan"),
                "icir": float("nan"), "t_naive": float("nan"), "p_naive": float("nan"),
                "ci95_low": float("nan"), "ci95_high": float("nan"),
                "t_nw": float("nan"), "p_nw": float("nan"), "hac_lag": hac_lag or lags}
    mean_ic = float(np.mean(ics))
    std_ic = float(np.std(ics, ddof=1)) if n > 1 else 0.0
    icir = mean_ic / std_ic if std_ic > 0 else 0.0
    if std_ic > 0 and n > 1:
        se = std_ic / math.sqrt(n)
        t_naive = mean_ic / se
        p_naive = float(2 * (1 - stats.t.cdf(abs(t_naive), df=n - 1)))
        tcrit = float(stats.t.ppf(0.975, df=n - 1))
        ci_low, ci_high = mean_ic - tcrit * se, mean_ic + tcrit * se
    else:
        t_naive = p_naive = 0.0
        ci_low = ci_high = mean_ic
    eff_lag = hac_lag if hac_lag is not None else lags
    se_nw = newey_west_se(ics, eff_lag)
    if not math.isnan(se_nw) and se_nw > 0 and n > 1:
        t_nw = mean_ic / se_nw
        p_nw = float(2 * (1 - stats.t.cdf(abs(t_nw), df=n - 1)))
    else:
        t_nw = p_nw = float("nan")
    return {
        "n_obs": n, "mean_ic": mean_ic, "std_ic": std_ic, "icir": icir,
        "t_naive": t_naive, "p_naive": p_naive,
        "ci95_low": ci_low, "ci95_high": ci_high,
        "t_nw": t_nw, "p_nw": p_nw, "hac_lag": eff_lag,
    }


def nonoverlap_stats(ics: np.ndarray, stride: int) -> dict:
    """Subsample the daily IC series at stride=h (disjoint forward windows) ->
    independent-ish ICs. Reveals whether a horizon's ICIR rise is real or a
    mechanical overlap artifact (smoother long-horizon returns shrink IC std).
    """
    if stride < 1:
        stride = 1
    sub = np.asarray(ics, dtype=float)[::stride]
    n = int(len(sub))
    if n < 2:
        return {"n_obs": n, "mean_ic": float("nan"), "icir": float("nan"),
                "t": float("nan"), "stride": stride}
    mean_ic = float(np.mean(sub))
    std_ic = float(np.std(sub, ddof=1))
    icir = mean_ic / std_ic if std_ic > 0 else 0.0
    t = mean_ic / (std_ic / math.sqrt(n)) if std_ic > 0 else 0.0
    return {"n_obs": n, "mean_ic": round(mean_ic, 5), "icir": round(icir, 4),
            "t": round(t, 4), "stride": stride}


def _round_dict(d: dict, nd: int = 5) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, float) and not math.isnan(v):
            out[k] = round(v, nd)
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# Panel / long-frame builders
# ---------------------------------------------------------------------------

def build_factor_ranks(close: pd.DataFrame, xu100: pd.Series) -> dict[str, pd.DataFrame]:
    """Compute oriented cross-sectional rank panels for all Faz 0 factors.

    RS: higher RS -> higher rank (momentum hypothesis; if BIST contrarian, IC<0).
    low-vol: lower vol -> higher rank (invert). Positive IC => hypothesis holds.
    """
    ranks: dict[str, pd.DataFrame] = {}
    for name, lb in cfg.RS_LOOKBACKS_DAYS.items():
        rs = factors.rs_vs_xu100(close, xu100, lookback=lb, skip=cfg.RS_SKIP_DAYS)
        ranks[name] = rank_panel(rs, invert=False)
    for name, w in cfg.VOL_WINDOWS_DAYS.items():
        vol = factors.realized_vol(close, window=w)
        ranks[name] = rank_panel(vol, invert=True)
    # equal-weight composite (invariant 4): mean of family representatives
    comp = (ranks[cfg.COMPOSITE_RS] + ranks[cfg.COMPOSITE_VOL]) / 2.0
    ranks["composite"] = comp
    return ranks


def build_signal_df(ranks: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Rank panels -> ic_calculator signal_df [date, symbol, <factor cols>]."""
    cols = []
    for name, panel in ranks.items():
        s = panel.stack(future_stack=True).dropna()
        s.name = name
        s.index.names = ["date", "symbol"]
        cols.append(s)
    sig = pd.concat(cols, axis=1).reset_index()
    return sig.sort_values(["date", "symbol"]).reset_index(drop=True)


def build_returns_df(close: pd.DataFrame, horizons) -> pd.DataFrame:
    """Forward-return panels -> ic_calculator returns_df [signal_date, symbol,
    horizon, forward_return]."""
    parts = []
    for h in horizons:
        fwd = factors.forward_returns(close, horizon=h)
        s = fwd.stack(future_stack=True).dropna()
        s.name = "forward_return"
        s.index.names = ["signal_date", "symbol"]
        part = s.reset_index()
        part["horizon"] = h
        parts.append(part)
    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["signal_date", "symbol", "horizon"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# IC per factor x horizon (primitive + equivalence)
# ---------------------------------------------------------------------------

def compute_factor_ic(
    signal_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    ranks: dict[str, pd.DataFrame],
    fwd_panels: dict[int, pd.DataFrame],
    col: str,
    horizon: int,
) -> dict:
    """Primitive IC (ICCalculator) + local series + honest_t (NW lag=h) +
    non-overlapping ICIR (overlap-artifact diagnosis) + equivalence check."""
    prim = ICCalculator(signal_df, returns_df).compute_ic(col, horizon)
    ics = daily_ic_series(ranks[col], fwd_panels[horizon])
    # D-178: honest t uses Newey-West HAC bandwidth = horizon (overlap-corrected).
    local = ic_stats(ics, hac_lag=horizon)
    nonoverlap = nonoverlap_stats(ics, stride=horizon)
    # equivalence at ic_calculator reporting precision (5 decimals).
    # n-match guard (adversarial review): ICCalculator falls back to a single
    # POOLED ic (n_obs=1) when < IC_MIN_OBSERVATIONS daily cross-sections exist.
    # Require prim.n_obs == local n so a pooled value can never be mislabeled
    # "primitive" by a coincidental rounded-mean match.
    prim_mean = prim.mean_ic
    local_mean_5 = round(local["mean_ic"], 5) if local["n_obs"] else float("nan")
    n_match = prim.n_obs == local["n_obs"]
    if isinstance(prim_mean, float) and not math.isnan(prim_mean) and local["n_obs"]:
        equiv_ok = n_match and abs(local_mean_5 - prim_mean) < 1e-9
    else:
        equiv_ok = False
    ic_source = "primitive" if equiv_ok else "fallback"
    return {
        "factor": col, "horizon": horizon, "ic_source": ic_source,
        "equivalence_ok": bool(equiv_ok),
        "primitive": {"mean_ic": prim.mean_ic, "icir": prim.ir,
                      "t_stat": prim.t_stat, "p_value": prim.p_value,
                      "n_obs": prim.n_obs, "is_investable": prim.is_investable},
        "series": _round_dict(local),                 # series.t_naive + series.t_nw (honest, lag=h)
        "nonoverlap": nonoverlap,                      # overlap'siz ICIR/t (artifact check)
    }


# ---------------------------------------------------------------------------
# TEST 2 -- group-conditional skewness (DIAGNOSTIC, not gating)
# ---------------------------------------------------------------------------

def _xsec_skew_deltas(
    close: pd.DataFrame,
    vol_window: int,
    fwd_horizon: int,
    frac: float,
) -> tuple[np.ndarray, np.ndarray, list]:
    """Per-date [skew(high-vol fwd) - skew(low-vol fwd)] and realized-skew diff.

    Groups split by trailing realized vol (bottom/top `frac`). Returns
    (fwd_skew_deltas, realized_skew_deltas, dates) aligned arrays.
    """
    vol = factors.realized_vol(close, vol_window)
    fwd = factors.forward_returns(close, fwd_horizon)
    log_ret = np.log(close / close.shift(1))
    fwd_deltas: list[float] = []
    real_deltas: list[float] = []
    used_dates: list = []
    for date in sorted(close.index):
        v = vol.loc[date].dropna() if date in vol.index else pd.Series(dtype=float)
        f = fwd.loc[date].dropna() if date in fwd.index else pd.Series(dtype=float)
        common = v.index.intersection(f.index)
        if len(common) < 9:  # need >=3 per group across thirds
            continue
        v = v.loc[common].sort_values()
        k = max(3, int(len(v) * frac))
        low_syms = v.index[:k]
        high_syms = v.index[-k:]
        f_low, f_high = f.loc[low_syms], f.loc[high_syms]
        if len(f_low) < 3 or len(f_high) < 3:
            continue
        fwd_deltas.append(float(stats.skew(f_high.to_numpy(), bias=False)
                                - stats.skew(f_low.to_numpy(), bias=False)))
        # ex-ante realized skewness (Amaya): trailing daily-return skew per stock
        win = log_ret.loc[:date].tail(vol_window)
        rs_low = win[low_syms].apply(lambda c: stats.skew(c.dropna().to_numpy(), bias=False)
                                     if c.dropna().size >= 3 else np.nan)
        rs_high = win[high_syms].apply(lambda c: stats.skew(c.dropna().to_numpy(), bias=False)
                                       if c.dropna().size >= 3 else np.nan)
        real_deltas.append(float(np.nanmean(rs_high) - np.nanmean(rs_low)))
        used_dates.append(date)
    return np.array(fwd_deltas), np.array(real_deltas), used_dates


def block_bootstrap_ci(
    series: np.ndarray,
    block: int = cfg.BOOTSTRAP_BLOCK,
    n_boot: int = cfg.BOOTSTRAP_N,
    seed: int = cfg.BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Circular block-bootstrap 95% CI for the mean of an autocorrelated series."""
    n = len(series)
    if n < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nblocks = math.ceil(n / block)
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        idx: list[int] = []
        for _ in range(nblocks):
            start = int(rng.integers(0, n))
            idx.extend((start + j) % n for j in range(block))
        idx = idx[:n]
        means[i] = float(np.mean(series[idx]))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def run_test2(close: pd.DataFrame) -> dict:
    """TEST 2 diagnostic: group-conditional skewness with block-bootstrap CI."""
    fwd_d, real_d, dates = _xsec_skew_deltas(
        close, cfg.TEST2_VOL_WINDOW, cfg.TEST2_FWD_HORIZON, cfg.VOL_GROUP_FRACTION,
    )
    if len(fwd_d) < 2:
        return {"status": "insufficient_data", "n_dates": int(len(fwd_d))}
    delta_skew = float(np.mean(fwd_d))
    ci_lo, ci_hi = block_bootstrap_ci(fwd_d)
    realized_skew_diff = float(np.nanmean(real_d)) if len(real_d) else float("nan")
    return {
        "metric": "delta_skew = mean_t[skew(high_vol_fwd) - skew(low_vol_fwd)]",
        "delta_skew": round(delta_skew, 5),
        "block_bootstrap_ci95": [round(ci_lo, 5), round(ci_hi, 5)],
        "realized_skew_diff_amaya": round(realized_skew_diff, 5),
        "n_dates": int(len(fwd_d)),
        "status": "DIAGNOSTIC (not gating)",
        "warnings": [
            "Diagnostic, not gating. low-vol keep/drop rests on standalone "
            "rank-IC (IC>0 + ICIR>=0.5), not on this test.",
            "T~24 months + EM tails: tail measurement unreliable (SE large); "
            "not-detected != absent; read with the wide bootstrap CI.",
            "SURVIVORSHIP: survivors-only snapshot drops the delisting left tail "
            "-> skewness biased UP -> high-vol group looks falsely good; read "
            "delta_skew skewed in that direction.",
            "LITERATURE: 'low-vol misses multi-baggers' is likely invalid for an "
            "IR-maximizing screen (lottery/IVOL/MAX right-tail proxies negatively "
            "predict forward returns); valid for convex-targeted portfolios, not ours.",
        ],
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_faz0(
    start: str = cfg.SNAPSHOT_START,
    end: str = cfg.SNAPSHOT_END,
    universe: list[str] | None = None,
    out_dir: Path | str = _RESULTS_DIR,
    tag: str = "",
    adv_floor_tl: float | None = None,
    directive: str = "D-177",
    results_filename: str = "faz0_results.json",
) -> dict:
    """Full Faz 0 measurement. Returns results dict and writes results JSON.

    D-178 v2 (tag="v2"): mechanical BIST100 candidate pool + ADV floor; keep
    decision on OVERLAP-CORRECTED honest_t (NW lag=h) + non-overlapping ICIR
    over the pre-registered PRIMARY_HORIZONS.
    """
    is_v2 = bool(tag == "v2" or adv_floor_tl is not None)
    if universe is None:
        universe = snapshot.resolve_universe_v2() if is_v2 else snapshot.resolve_universe()
    long_df, meta = snapshot.freeze_price_snapshot(
        universe, start, end, adv_floor_tl=adv_floor_tl, tag=tag, directive=directive,
    )
    close, xu100 = snapshot.to_close_panel(long_df)

    ranks = build_factor_ranks(close, xu100)
    fwd_panels = {h: factors.forward_returns(close, h) for h in cfg.IC_HORIZONS}
    signal_df = build_signal_df(ranks)
    returns_df = build_returns_df(close, cfg.IC_HORIZONS)

    singles = list(cfg.RS_LOOKBACKS_DAYS) + list(cfg.VOL_WINDOWS_DAYS)
    factor_cols = singles + ["composite"]
    per_factor: dict[str, dict] = {}
    for col in factor_cols:
        per_factor[col] = {
            str(h): compute_factor_ic(signal_df, returns_df, ranks, fwd_panels, col, h)
            for h in cfg.IC_HORIZONS
        }

    ph = "21"  # reference horizon for TEST 1 + RS sign (comparable to D-177)

    def _mean(col: str, h: str = ph) -> float:
        return per_factor[col][h]["series"]["mean_ic"]

    # TEST 1 -- dilution (new universe): composite IC vs best single-factor IC
    best_single = max(singles, key=lambda c: _mean(c))
    test1 = {
        "primary_horizon": int(ph),
        "composite_ic": _mean("composite"),
        "best_single_factor": best_single,
        "best_single_ic": _mean(best_single),
        "dilution_flag": bool(_mean("composite") < _mean(best_single)),
        "note": "composite < best single => equal-weight rank average dilutes; "
                "narrow the factor SET (do not optimize weights, invariant 4).",
    }

    test2 = run_test2(close)

    # ----- KEEP decision: OVERLAP-CORRECTED honest_t + non-overlap ICIR -----
    # Pre-registered rule (STAGE0_v2): keep if ANY h in PRIMARY_HORIZONS has
    # |honest_t| >= KEEP_HONEST_T_MIN AND non-overlap ICIR >= KEEP_ICIR_NONOVERLAP_MIN.
    keep_drop: dict[str, dict] = {}
    for col in singles:
        by_h = {}
        keep_any = False
        for h in cfg.PRIMARY_HORIZONS:
            s = per_factor[col][str(h)]["series"]
            no = per_factor[col][str(h)]["nonoverlap"]
            honest_t = s["t_nw"]            # NW HAC, lag = h
            icir_no = no["icir"]
            # eligibility: enough independent obs for ICIR to be trustworthy
            # (guards the tiny-n ICIR artifact at long horizons, e.g. h63 ~4 obs).
            eligible = bool(no["n_obs"] >= cfg.FAZ0_MIN_NONOVERLAP_N)
            ok = bool(
                eligible
                and honest_t is not None and not math.isnan(honest_t)
                and abs(honest_t) >= cfg.KEEP_HONEST_T_MIN
                and icir_no is not None and not math.isnan(icir_no)
                and icir_no >= cfg.KEEP_ICIR_NONOVERLAP_MIN
            )
            keep_any = keep_any or ok
            by_h[str(h)] = {
                "mean_ic": s["mean_ic"], "t_naive": s["t_naive"],
                "honest_t_nw_lag_h": honest_t, "icir_overlap": s["icir"],
                "icir_nonoverlap": icir_no, "nonoverlap_n": no["n_obs"],
                "eligible": eligible, "passes": ok,
            }
        keep_drop[col] = {"keep": keep_any, "by_horizon": by_h}

    rs_recos = {}
    for col in cfg.RS_LOOKBACKS_DAYS:
        ic = _mean(col)
        if ic is None or math.isnan(ic):
            reco = "insufficient_data"
        elif ic <= 0.0:
            reco = "DROP or convert to short-term REVERSAL (Bildik-Gulay contrarian)"
        else:
            reco = "positive standalone IC (direction ok); keep gated on honest_t + non-overlap ICIR"
        rs_recos[col] = {"mean_ic_h21": ic, "recommendation": reco}

    faz1_set = [c for c, v in keep_drop.items() if v["keep"]]
    results = {
        "directive": directive,
        "phase": "FAZ 0 v2 -- Factor IC (overlap-corrected; MEASUREMENT only; DEC-039)",
        "window": {"start": start, "end": end},
        "snapshot": {
            "content_hash": meta.get("content_hash"),
            "timestamp_utc": meta.get("timestamp_utc"),
            "loaded_universe_n": meta.get("loaded_universe_n"),
            "adv_filter": meta.get("adv_filter"),
            "survivorship": meta.get("survivorship"),
        },
        "config_version": cfg.CONFIG_VERSION,
        "ic_metric": "Spearman rank-IC (NOT Pearson; keeps TEST 2 orthogonal)",
        "horizons": list(cfg.IC_HORIZONS),
        "keep_rule": {
            "primary_horizons": list(cfg.PRIMARY_HORIZONS),
            "honest_t_min": cfg.KEEP_HONEST_T_MIN,
            "icir_nonoverlap_min": cfg.KEEP_ICIR_NONOVERLAP_MIN,
            "min_nonoverlap_n": cfg.FAZ0_MIN_NONOVERLAP_N,
            "honest_t_method": "Newey-West HAC, Bartlett bandwidth = horizon h",
            "rule": "keep if ANY ELIGIBLE primary horizon (non-overlap n>=min_n) has "
                    "|honest_t|>=honest_t_min AND non-overlap ICIR>=icir_min",
            "bar_justification": "honest_t_min=IC_INVESTABLE_TSTAT_MIN (pre-D-177, result-independent) "
                                 "+ classic t~=2; icir_min=ARCHITECTURE 7.1; min_nonoverlap_n guards "
                                 "the tiny-sample ICIR artifact (result-independent, STRICTER). "
                                 "Measured not estimated; below bar => drop, no rescue (DEC-039).",
        },
        "per_factor_ic": per_factor,
        "test1_dilution": test1,
        "test2_groupcond_skew": test2,
        "keep_drop_decision": keep_drop,
        "rs_decision_rule": rs_recos,
        "faz1_recommended_factor_set": faz1_set,
        "decision_owner": "the project (harness recommends only, DEC-039)",
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / results_filename).write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    _print_summary(results)
    return results


def run_faz0b(
    out_dir: Path | str = _RESULTS_DIR,
    price_snapshot: str = "faz0_v2_prices_2024-01-01_2026-04-30",
    fund_fetch_fn=None,
) -> dict:
    """Faz 0b value-factor IC (P/B + EV/EBITDA, standalone). D-183. N=3/3.

    Reuses D-178 machinery (compute_factor_ic / honest_t NW lag=h / non-overlap
    ICIR / min-n eligibility / keep rule). Price forward-returns reuse the frozen
    faz0_v2 snapshot; value comes from the frozen MaliTablo fundamentals.
    """
    snap_dir = snapshot._SNAPSHOT_DIR
    price_long = pd.read_parquet(snap_dir / f"{price_snapshot}.parquet")
    close, _xu = snapshot.to_close_panel(price_long)
    universe = sorted(close.columns)

    funds, fmeta = snapshot.freeze_fundamental_snapshot(universe, fetch_fn=fund_fetch_fn)
    null_set = set(snapshot.load_par_guard_null())

    start = pd.Timestamp(cfg.FAZ0B_WINDOW_START)
    end = pd.Timestamp(cfg.FAZ0B_WINDOW_END)
    dates = close.index[(close.index >= start) & (close.index <= end)]
    pb, ev = factors.value_ratios(funds, close, dates, par=cfg.FAZ0B_PAR_VALUE)
    for tkr in null_set:                          # par-guard NULL (the maintainer)
        if tkr in pb.columns:
            pb[tkr] = float("nan")
        if tkr in ev.columns:
            ev[tkr] = float("nan")

    ranks = {"pb": rank_panel(pb, invert=True), "ev_ebitda": rank_panel(ev, invert=True)}
    horizons = cfg.FAZ0B_HORIZONS
    fwd_panels = {h: factors.forward_returns(close, h) for h in horizons}
    signal_df = build_signal_df(ranks)
    returns_df = build_returns_df(close, horizons)

    factor_cols = ["pb", "ev_ebitda"]
    per_factor: dict[str, dict] = {}
    for col in factor_cols:
        per_factor[col] = {
            str(h): compute_factor_ic(signal_df, returns_df, ranks, fwd_panels, col, h)
            for h in horizons
        }

    # keep: ANY eligible h (non-overlap n>=min) with |honest_t|>=min AND ICIRno>=min
    keep_drop: dict[str, dict] = {}
    for col in factor_cols:
        by_h, keep_any = {}, False
        for h in horizons:
            s = per_factor[col][str(h)]["series"]
            no = per_factor[col][str(h)]["nonoverlap"]
            ht, icir_no = s["t_nw"], no["icir"]
            eligible = bool(no["n_obs"] >= cfg.FAZ0_MIN_NONOVERLAP_N)
            ok = bool(eligible and ht is not None and not math.isnan(ht)
                      and abs(ht) >= cfg.KEEP_HONEST_T_MIN
                      and icir_no is not None and not math.isnan(icir_no)
                      and icir_no >= cfg.KEEP_ICIR_NONOVERLAP_MIN)
            keep_any = keep_any or ok
            by_h[str(h)] = {"mean_ic": s["mean_ic"], "t_naive": s["t_naive"],
                            "honest_t_nw_lag_h": ht, "icir_overlap": s["icir"],
                            "icir_nonoverlap": icir_no, "nonoverlap_n": no["n_obs"],
                            "eligible": eligible, "passes": ok}
        keep_drop[col] = {"keep": keep_any, "by_horizon": by_h}

    usd_sanity = _usd_rank_sanity(pb, dates)
    coverage = {
        "fundamental_loaded_n": fmeta.get("coverage", {}).get("loaded_n"),
        "fundamental_null_tickers": fmeta.get("coverage", {}).get("null_tickers"),
        "banks_n": fmeta.get("coverage", {}).get("banks_n"),
        "par_guard_null": sorted(null_set),
        "pb_names_per_date_median": int(pb.notna().sum(axis=1).median()) if len(pb) else 0,
        "ev_names_per_date_median": int(ev.notna().sum(axis=1).median()) if len(ev) else 0,
    }
    value_keepers = [c for c, v in keep_drop.items() if v["keep"]]
    faz1_set = (["lowvol60"] if True else []) + value_keepers  # lowvol60 from D-178

    results = {
        "directive": "D-183",
        "phase": "FAZ 0b -- Value IC (P/B + EV/EBITDA, standalone; MEASUREMENT only; DEC-039; N=3/3)",
        "window": {"start": cfg.FAZ0B_WINDOW_START, "end": cfg.FAZ0B_WINDOW_END},
        "fundamental_snapshot_hash": fmeta.get("content_hash"),
        "price_snapshot": price_snapshot,
        "ic_metric": "Spearman rank-IC (TL ratios; USD rank-invariant per D-180)",
        "horizons": list(horizons),
        "keep_rule": {
            "primary_horizons": list(horizons),
            "honest_t_min": cfg.KEEP_HONEST_T_MIN,
            "icir_nonoverlap_min": cfg.KEEP_ICIR_NONOVERLAP_MIN,
            "min_nonoverlap_n": cfg.FAZ0_MIN_NONOVERLAP_N,
            "rule": "keep if ANY eligible h has |honest_t(NW lag=h)|>=min AND non-overlap ICIR>=min",
        },
        "per_factor_ic": per_factor,
        "keep_drop_decision": keep_drop,
        "usd_rank_sanity": usd_sanity,
        "coverage": coverage,
        "value_keepers": value_keepers,
        "faz1_recommended_factor_set": faz1_set,
        "note": "Banks: F/DD only, EV/EBITDA NULL (D-182). Point-in-time annual, "
                "conservative +120d lag, latest-public restated (RR-036).",
        "decision_owner": "the project (harness recommends only, DEC-039)",
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "faz0b_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8")
    _print_faz0b_summary(results)
    return results


def _usd_rank_sanity(pb_tl: pd.DataFrame, dates: pd.DatetimeIndex) -> dict:
    """TL-rank == USD-rank sanity. FX(t) is common across tickers on date t, so
    dividing every ratio by fx(t) cannot change the cross-sectional rank ->
    Spearman rho == 1.0 by construction (D-180). Verified literally on a sample."""
    try:
        fx, _ = snapshot.freeze_fx_snapshot()
        fxd = fx.reindex(pd.DatetimeIndex(sorted(set(fx.index) | set(dates)))).ffill()
    except Exception:                              # noqa: BLE001
        return {"checked": False, "note": "FX unavailable; rank-invariance holds by construction"}
    rhos = []
    sample = list(dates)[::5]
    for t in sample:
        row = pb_tl.loc[t].dropna()
        if len(row) < 5:
            continue
        f = float(fxd.get(t, float("nan")))
        if math.isnan(f) or f <= 0:
            continue
        usd = row / f
        rho, _ = stats.spearmanr(row.to_numpy(), usd.to_numpy())
        if not math.isnan(rho):
            rhos.append(float(rho))
    return {"checked": True, "n_dates": len(rhos),
            "mean_spearman_rho": round(float(np.mean(rhos)), 6) if rhos else None,
            "min_spearman_rho": round(float(np.min(rhos)), 6) if rhos else None,
            "expected": 1.0, "note": "rho==1.0 confirms USD conversion is rank-invariant (D-180)"}


def _print_faz0b_summary(r: dict) -> None:
    sep = "=" * 78
    print(f"\n{sep}\n  {r['phase']}\n{sep}")
    print(f"  Window     : {r['window']['start']} -> {r['window']['end']}")
    cov = r["coverage"]
    print(f"  Coverage   : fundamentals {cov['fundamental_loaded_n']} loaded; "
          f"par-guard NULL {cov['par_guard_null']}; banks {cov['banks_n']} (EV/EBITDA NULL)")
    print(f"  Names/date : P/B~{cov['pb_names_per_date_median']}  EV/EBITDA~{cov['ev_names_per_date_median']}")
    hs = [str(h) for h in r["keep_rule"]["primary_horizons"]]
    print(f"  {'-'*74}")
    print(f"  {'factor':<11}" + "".join(f"  h{h}:naive/honest/ICIRno(n)" for h in hs) + "  keep")
    for col, v in r["keep_drop_decision"].items():
        cells = ""
        for h in hs:
            b = v["by_horizon"][h]
            cells += f"  {b['t_naive']:+.2f}/{b['honest_t_nw_lag_h']:+.2f}/{b['icir_nonoverlap']:+.2f}(n{b['nonoverlap_n']})"
        print(f"  {col:<11}{cells}  {v['keep']}")
    us = r["usd_rank_sanity"]
    print(f"  {'-'*74}")
    print(f"  USD sanity : TL-rank==USD-rank mean_rho={us.get('mean_spearman_rho')} (beklenen 1.0)")
    print(f"  value keepers: {r['value_keepers']}")
    print(f"  FAZ 1 set  : {r['faz1_recommended_factor_set']}  (lowvol60 D-178 + value)")
    print(f"{sep}\n")


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def _print_summary(r: dict) -> None:
    sep = "=" * 78
    print(f"\n{sep}\n  {r['phase']}\n{sep}")
    print(f"  Window     : {r['window']['start']} -> {r['window']['end']}")
    sv = r["snapshot"]["survivorship"]
    advf = r["snapshot"].get("adv_filter")
    print(f"  Universe   : {r['snapshot']['loaded_universe_n']} loaded"
          + (f" (ADV-passed of {advf['candidates_n']} candidates, floor "
             f"{advf['adv_floor_tl']:.0f} TL)" if advf else ""))
    print(f"  Keep rule  : ANY h in {r['keep_rule']['primary_horizons']} with "
          f"|honest_t|>={r['keep_rule']['honest_t_min']} AND non-overlap ICIR"
          f">={r['keep_rule']['icir_nonoverlap_min']}  (honest_t = NW HAC lag=h)")
    print(f"  {'-'*74}")
    hs = [str(h) for h in r["keep_rule"]["primary_horizons"]]
    hdr = "".join(f"  h{h}: naive_t/honest_t/ICIRno" for h in hs)
    print(f"  {'factor':<10}{hdr}   keep")
    for col, v in r["keep_drop_decision"].items():
        cells = ""
        for h in hs:
            b = v["by_horizon"][h]
            tn = b["t_naive"]; ht = b["honest_t_nw_lag_h"]; io = b["icir_nonoverlap"]
            cells += f"  {tn:+.2f}/{ht:+.2f}/{io:+.2f}"
        print(f"  {col:<10}{cells}   {v['keep']}")
    t1 = r["test1_dilution"]
    print(f"  {'-'*74}")
    print(f"  TEST1 dilution(@h{t1['primary_horizon']}): composite={t1['composite_ic']:.4f} vs "
          f"best({t1['best_single_factor']})={t1['best_single_ic']:.4f} -> dilution={t1['dilution_flag']}")
    t2 = r["test2_groupcond_skew"]
    if "delta_skew" in t2:
        print(f"  TEST2 (diag) : delta_skew={t2['delta_skew']:.4f} "
              f"CI95={t2['block_bootstrap_ci95']} (gating DEGIL)")
    print(f"  Faz1 set   : {r['faz1_recommended_factor_set']}")
    print(f"  SURVIVORSHIP BIAS: {sv.get('bias_direction')}")
    print(f"{sep}\n")


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Faz 0 Factor IC Validation Harness")
    p.add_argument("--start", default=cfg.SNAPSHOT_START)
    p.add_argument("--end", default=cfg.SNAPSHOT_END)
    p.add_argument("--out-dir", default=str(_RESULTS_DIR))
    p.add_argument("--tag", default="", help="v2 -> mechanical universe + ADV + overlap-corrected keep")
    p.add_argument("--adv-floor", type=float, default=None)
    p.add_argument("--faz0b", action="store_true", help="D-183 value factor IC (MaliTablo)")
    args = p.parse_args()
    if args.faz0b:
        run_faz0b(out_dir=args.out_dir)
        return
    is_v2 = args.tag == "v2" or args.adv_floor is not None
    adv_floor = args.adv_floor if args.adv_floor is not None else (
        cfg.FAZ0_ADV_FLOOR_TL if is_v2 else None)
    run_faz0(
        start=args.start, end=args.end, out_dir=args.out_dir,
        tag=args.tag, adv_floor_tl=adv_floor,
        directive="D-178" if is_v2 else "D-177",
        results_filename="faz0_v2_results.json" if is_v2 else "faz0_results.json",
    )


if __name__ == "__main__":
    _main()

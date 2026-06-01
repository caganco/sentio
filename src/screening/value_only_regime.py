"""Value-only REGIME-RESILIENCE backtest engine. D-Y1-001 (Yol-1 Asama-1).

Resolves the Faz-0 (D-183) <-> D-191 conflict for the VALUE factor in isolation
and tests whether any value-only tilt is REGIME-RESILIENT (not a single-subperiod
artifact). THREE legs (RR-Y1.md sec.SORU-1 + Recommendations Soru-1 #1/#3):

  AYAK-1  rank-IC AND tilt on the SAME sample (diagnostic): daily Spearman rank-IC
          (Faz-0 method, honest_t = Newey-West HAC lag=h) reported next to the
          rebalance tercile tilt (D-191 method). Exposes the "weak IC + strong
          tilt" signature on identical data -> conflict is methodological, not a bug.
  AYAK-2  decile monotonicity (Gate-4): D1..D10 by value rank, per-decile net
          TL-real. Is the premium concentrated at the cheap end (explainable) or
          noise in the middle?
  AYAK-3  regime resilience (Gate-3, MOST CRITICAL): per-period TL-real split by
          frozen 3-way INFLATION_REGIMES (decision gate) + 2-way pre/post-2023
          (robustness). Consistent-positive in >=2 independent subperiods?

Armored backtest (5-test lessons): TL-real PRIMARY gate, XU100-relative + USD-real
reported, fair random-selection null, survivorship optimistic-upper-bound declared,
cost+tax+slippage, Stage-0 pre-registration, N<=3, look-ahead safe, NO composite.

Strangler: reuses k2_factor_tilt (rebalance_dates, select_basket, period_net_returns,
to_real/to_relative/to_usd_real, mean_ci, split_in_out, fair_random_null_portfolio,
daily_equity_curve, max_drawdown), factors (value_ratios, PIT helpers, forward_returns),
factor_ic_harness (rank_panel, daily_ic_series, ic_stats, block_bootstrap_ci),
trend_config (INFLATION_REGIMES) read-only. Does NOT touch them. No composite/
conviction/MASTER_WEIGHTS or signal/backtest engine imports (architecture invariant).

Decision owner: the project (DEC-039). Harness MEASURES + RECOMMENDS.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.screening import factors
from src.screening import k2_factor_tilt as k2
from src.screening import value_only_regime_config as cfg
from src.screening.factor_ic_harness import daily_ic_series, ic_stats, rank_panel

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"
_RESULTS_DIR = Path(__file__).parent.parent.parent / "docs" / "yol1"


def _r(x) -> float | None:
    try:
        return round(float(x), 6) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# ===========================================================================
# Value metric panels (PRIMARY P/B-inverse, ROBUSTNESS E/P) -- look-ahead safe
# ===========================================================================
def earnings_yield(
    funds: pd.DataFrame,
    close: pd.DataFrame,
    dates: pd.DatetimeIndex,
    par: float = cfg.VOR_PAR_VALUE,
) -> pd.DataFrame:
    """Point-in-time E/P = net_income / market_cap (TL). Robustness value metric.

    market_cap = (issued_capital / par) * close(t). For each (date, ticker) use the
    latest annual with pub_date <= t (reuse factors PIT helpers -> no look-ahead).
    Loss-makers (net_income <= 0) -> NaN (earnings yield defined for profitable
    firms; rank handles the rest). Higher E/P = cheaper = higher rank (invert=False).
    """
    pit = factors._pit_index(funds)
    cols = sorted(close.columns)
    ep = pd.DataFrame(index=dates, columns=cols, dtype=float)
    for t in dates:
        asof = pd.Timestamp(t).strftime("%Y-%m-%d")
        for tkr in cols:
            recs = pit.get(tkr)
            if not recs:
                continue
            row = factors._latest_as_of(recs, asof)
            if row is None:
                continue
            price = close.at[t, tkr] if tkr in close.columns else np.nan
            ic = row.get("issued_capital")
            ni = row.get("net_income")
            if price is None or np.isnan(price) or ic is None or ni is None or float(par) <= 0:
                continue
            mcap = (float(ic) / float(par)) * float(price)
            if mcap > 0 and float(ni) > 0:
                ep.at[t, tkr] = float(ni) / mcap
    return ep


def value_rank_panel(funds: pd.DataFrame, close: pd.DataFrame, dates: pd.DatetimeIndex, kind: str) -> pd.DataFrame:
    """Cross-sectional value rank panel (date x ticker). kind in {'pb','ep'}.

    pb: book-to-market = 1/(P/B) -> low P/B (cheap) gets HIGH rank (invert P/B).
    ep: earnings yield E/P     -> high E/P (cheap) gets HIGH rank (no invert).
    """
    if kind == "pb":
        pb, _ev = factors.value_ratios(funds, close, dates, par=cfg.VOR_PAR_VALUE)
        return rank_panel(pb, invert=True)
    if kind == "ep":
        ep = earnings_yield(funds, close, dates, par=cfg.VOR_PAR_VALUE)
        return rank_panel(ep, invert=False)
    raise ValueError(f"unknown value kind: {kind}")


# ===========================================================================
# Tilt block (Gate-1 / Gate-2) -- assembled from PUBLIC k2 building blocks
# ===========================================================================
def _pool(value_rank: pd.DataFrame, date: pd.Timestamp) -> list[str]:
    row = value_rank.loc[date].dropna() if date in value_rank.index else pd.Series(dtype=float)
    return sorted(row.index)


def tilt_block(
    close_ff: pd.DataFrame,
    value_rank: pd.DataFrame,
    rebal: list[pd.Timestamp],
    cpi: pd.Series | None,
    xu100: pd.Series,
    fx: pd.Series | None,
    us_cpi: pd.Series | None,
    variant: str,
    null_resamples: int = cfg.VOR_NULL_N_RESAMPLES,
) -> dict:
    """Long-only top-fraction value tilt over the holding periods (single factor).

    variant 'tercile' -> top 1/3, 'quintile' -> top 1/5 by value rank. Mirrors the
    D-191 single-factor value block (same cost/tax/null machinery) so the result is
    directly comparable; reuses k2 PUBLIC functions only.
    """
    k2variant = "composite_quintile" if variant == "quintile" else "composite_tercile"
    n = len(rebal) - 1
    baskets = [k2.select_basket(rebal[i], value_rank, {"value": value_rank}, k2variant) for i in range(n)]
    sizes = [len(b) for b in baskets]
    pr = k2.period_net_returns(close_ff, baskets, rebal)
    net = pr["net"]
    real = k2.to_real(net, rebal, cpi)
    rel = k2.to_relative(net, rebal, xu100)
    usd, usd_is_real = k2.to_usd_real(net, rebal, fx, us_cpi)
    real_ci = k2.mean_ci(real)
    pools = [_pool(value_rank, rebal[i]) for i in range(n)]
    null = k2.fair_random_null_portfolio(
        close_ff, pools, sizes, rebal, cpi, real_ci.get("mean", float("nan")),
        n_resamples=null_resamples,
    )
    eq = k2.daily_equity_curve(close_ff, baskets, rebal, pr["cost"])
    return {
        "variant": variant,
        "basket_sizes": sizes,
        "mean_turnover": _r(np.nanmean(pr["turnover"])) if sizes else None,
        "mean_cost": _r(np.nanmean(pr["cost"])) if sizes else None,
        "tl_real": real_ci,
        "tl_real_inout": k2.split_in_out(real, rebal),
        "xu100_relative": k2.mean_ci(rel),
        "usd_real": {**k2.mean_ci(usd), "is_real": usd_is_real,
                     "basis": "usd_real" if usd_is_real else "usd_nominal"},
        "fair_null": null,
        "max_drawdown": _r(k2.max_drawdown(eq)),
        "n_periods": len(net),
        "per_period": {"net": [_r(v) for v in net], "tl_real": [_r(v) for v in real],
                       "relative": [_r(v) for v in rel], "periods": pr["periods"]},
    }


# ===========================================================================
# AYAK-1 -- rank-IC (Faz-0 method) on the same sample as the tilt
# ===========================================================================
def rank_ic_leg(
    value_rank_daily: pd.DataFrame,
    close: pd.DataFrame,
    horizons: tuple[int, ...] = cfg.VOR_IC_HORIZONS,
) -> dict:
    """Daily cross-sectional Spearman rank-IC of the value rank vs forward returns.

    Reproduces the Faz-0 (D-183) value-IC measurement: honest_t = Newey-West HAC
    bandwidth = horizon (overlap-corrected). Reported next to the tilt so the
    "weak IC + strong tilt on identical data" conflict signature is explicit.
    """
    out: dict[str, dict] = {}
    for h in horizons:
        fwd = factors.forward_returns(close, h)
        ics = daily_ic_series(value_rank_daily, fwd, min_xsection=cfg.VOR_IC_MIN_XSECTION)
        s = ic_stats(ics, hac_lag=h)
        out[str(h)] = {
            "n_obs": s["n_obs"], "mean_ic": _r(s["mean_ic"]), "icir": _r(s["icir"]),
            "t_naive": _r(s["t_naive"]), "honest_t_nw_lag_h": _r(s["t_nw"]),
            "p_nw": _r(s["p_nw"]), "hac_lag": s["hac_lag"],
        }
    return out


# ===========================================================================
# AYAK-2 -- decile monotonicity (Gate-4)
# ===========================================================================
def decile_leg(
    close_ff: pd.DataFrame,
    value_rank: pd.DataFrame,
    rebal: list[pd.Timestamp],
    cpi: pd.Series | None,
    n_deciles: int = cfg.VOR_N_DECILES,
) -> dict:
    """Per-decile net TL-real return (D1=expensive .. D10=cheapest) + monotonicity.

    At each rebalance, split the value-ranked eligible names into n_deciles equal
    buckets (cheapest = highest rank = top decile). Per-decile equal-weight net
    TL-real over the holding period, averaged across rebalances. Monotonicity =
    Spearman(decile_index_cheap_high, mean_return); spread = cheap - expensive.
    Diagnostic for whether the premium is concentrated at the cheap extreme.
    """
    n = len(rebal) - 1
    dec_baskets: list[list[list[str]]] = [[[] for _ in range(n)] for _ in range(n_deciles)]
    filled_periods = 0
    for i in range(n):
        d = rebal[i]
        row = value_rank.loc[d].dropna() if d in value_rank.index else pd.Series(dtype=float)
        if len(row) < n_deciles:
            continue
        try:
            labels = pd.qcut(row.rank(method="first"), n_deciles, labels=False)
        except ValueError:
            continue
        filled_periods += 1
        for tkr, lab in labels.items():
            dec_baskets[int(lab)][i].append(tkr)

    dec_means: list[float] = []
    dec_n_periods: list[int] = []
    for didx in range(n_deciles):
        baskets = dec_baskets[didx]
        pr = k2.period_net_returns(close_ff, baskets, rebal)
        real = k2.to_real(pr["net"], rebal, cpi)
        vals = [v for v in real if np.isfinite(v)]
        dec_means.append(float(np.mean(vals)) if vals else float("nan"))
        dec_n_periods.append(len(vals))

    finite = [(i, dec_means[i]) for i in range(n_deciles) if np.isfinite(dec_means[i])]
    if len(finite) >= 3:
        idxs = [i for i, _ in finite]
        vals = [v for _, v in finite]
        rho, _ = stats.spearmanr(idxs, vals)
        monotonicity = float(rho) if not np.isnan(rho) else float("nan")
    else:
        monotonicity = float("nan")
    spread = (dec_means[-1] - dec_means[0]) if (np.isfinite(dec_means[-1]) and np.isfinite(dec_means[0])) else float("nan")

    gate4 = bool(
        np.isfinite(spread) and spread > cfg.VOR_GATE4_MIN_DECILE_SPREAD
        and np.isfinite(monotonicity) and monotonicity > cfg.VOR_GATE4_MIN_MONOTONICITY
    )
    return {
        "n_deciles": n_deciles,
        "decile_labels": "index 0 = most expensive (lowest value rank) .. index N-1 = cheapest",
        "decile_mean_tl_real": [_r(v) for v in dec_means],
        "decile_n_periods": dec_n_periods,
        "filled_periods": filled_periods,
        "cheap_minus_expensive_spread": _r(spread),
        "monotonicity_spearman_cheap_high": _r(monotonicity),
        "gate4_decile_profile_explainable": gate4,
        "thin_decile_caveat": "survivors-only pool / ~10-12 names per decile, "
                              "semi-annual rebalance -> wide noise; diagnostic, not over-interpret",
    }


# ===========================================================================
# AYAK-3 -- regime resilience (Gate-3): 3-way primary + 2-way robustness
# ===========================================================================
def _regime_stats(vals: list[float]) -> dict:
    arr = np.array([v for v in vals if np.isfinite(v)], dtype=float)
    n = int(len(arr))
    if n == 0:
        return {"n": 0, "mean": None, "sign_positive": False,
                "ci95_low": None, "ci95_high": None, "ci_excludes_zero": False}
    mean = float(np.mean(arr))
    if n >= 2:
        lo, hi = k2.block_bootstrap_ci(arr, block=cfg.VOR_SIG_BLOCK,
                                       n_boot=cfg.VOR_SIG_N_BOOT, seed=cfg.VOR_SIG_SEED)
        excl = bool(lo > 0 or hi < 0)
    else:
        lo = hi = float("nan")
        excl = False
    return {"n": n, "mean": _r(mean), "sign_positive": bool(mean > 0),
            "ci95_low": _r(lo), "ci95_high": _r(hi), "ci_excludes_zero": excl}


def regime_leg(
    per_period_tl_real: list[float | None],
    periods: list[tuple[str, str]],
    regimes_3way: tuple[tuple[str, str, str], ...] = cfg.VOR_INFLATION_REGIMES,
    split_date_2way: str = cfg.VOR_REGIME_SPLIT_DATE,
) -> dict:
    """Split the tilt's per-period TL-real series by macro regime (start date of
    each holding period). 3-way frozen INFLATION_REGIMES = decision gate; 2-way
    pre/post split = robustness. ALIGNMENT read: if the two splits agree the
    decision is STRONG; if they diverge, value is regime-definition-sensitive
    (FRAGILE) -- itself an honest finding (not a stable premium).
    """
    series = [v if (v is not None and np.isfinite(v)) else float("nan") for v in per_period_tl_real]

    def assign_3way(start: str) -> str | None:
        ts = pd.Timestamp(start)
        for name, a, b in regimes_3way:
            if pd.Timestamp(a) <= ts <= pd.Timestamp(b):
                return name
        return None

    groups3: dict[str, list[float]] = {name: [] for name, _a, _b in regimes_3way}
    for val, (s, _e) in zip(series, periods):
        g = assign_3way(s)
        if g is not None:
            groups3[g].append(val)
    regime3 = {name: _regime_stats(vals) for name, vals in groups3.items()}
    n_pos_3 = sum(1 for r in regime3.values() if r["n"] > 0 and r["mean"] is not None and r["mean"] > 0)
    n_active_3 = sum(1 for r in regime3.values() if r["n"] > 0)
    gate3 = bool(n_pos_3 >= cfg.VOR_GATE3_MIN_POSITIVE_REGIMES)

    cut = pd.Timestamp(split_date_2way)
    pre: list[float] = []
    post: list[float] = []
    for val, (s, _e) in zip(series, periods):
        (pre if pd.Timestamp(s) < cut else post).append(val)
    regime2 = {f"pre_{split_date_2way}": _regime_stats(pre), f"post_{split_date_2way}": _regime_stats(post)}
    pos2 = [r for r in regime2.values() if r["n"] > 0 and r["mean"] is not None and r["mean"] > 0]
    active2 = [r for r in regime2.values() if r["n"] > 0]
    twoway_consistent_positive = bool(len(active2) == 2 and len(pos2) == 2)

    aligned = bool(gate3 == twoway_consistent_positive)
    return {
        "primary_3way": {
            "regimes": regime3,
            "n_active_regimes": n_active_3,
            "n_positive_regimes": n_pos_3,
            "min_positive_required": cfg.VOR_GATE3_MIN_POSITIVE_REGIMES,
            "gate3_regime_resilient": gate3,
        },
        "robustness_2way": {
            "split_date": split_date_2way,
            "groups": regime2,
            "both_subperiods_positive": twoway_consistent_positive,
        },
        "alignment": {
            "aligned": aligned,
            "reading": ("ALIGNED -> decision strong" if aligned else
                        "DIVERGENT -> value regime-definition-sensitive (FRAGILE); "
                        "not a stable premium (honest-closure direction)"),
        },
        "note": "single-subperiod t>2 is INSUFFICIENT (RR-Y1 Recommendations Soru-1 #3); "
                "regime-dependent effect != stable premium",
    }


# ===========================================================================
# Verdict DEC-Y1 (four frozen gates)
# ===========================================================================
def value_only_verdict(tilt_real_ci: dict, fair_null: dict, regime: dict, decile: dict) -> dict:
    g1 = bool(tilt_real_ci.get("mean") is not None and tilt_real_ci.get("mean", 0) > 0
              and tilt_real_ci.get("ci_excludes_zero")
              and tilt_real_ci.get("ci95_low") is not None and tilt_real_ci.get("ci95_low", -1) > 0)
    g2 = bool(fair_null.get("beats_fair_null_95"))
    g3 = bool(regime.get("primary_3way", {}).get("gate3_regime_resilient"))
    g4 = bool(decile.get("gate4_decile_profile_explainable"))
    cpi_ok = tilt_real_ci.get("n", 0) >= 2 and tilt_real_ci.get("mean") is not None

    passes = bool(cpi_ok and g1 and g2 and g3 and g4)
    if passes:
        classification = "PASS -> Yol-2 OVERLAY candidate (<=10-20%, ana-sisteme degil; the project karari)"
    elif g1 and g2 and g4 and not g3:
        classification = ("PARTIAL -> value REGIME-DEPENDENT: conflict explained (tilt+null+decile) "
                          "but NOT regime-resilient. Consistent with D-191 in/out collapse. "
                          "Not a stable premium -> do NOT allocate.")
    else:
        classification = "FAIL -> value-only eliminated (tried-and-refuted archive)"

    fails = []
    if not cpi_ok:
        fails.append("tl_real_unavailable_INCONCLUSIVE")
    if not g1:
        fails.append("gate1_tl_real_not_sig_positive")
    if not g2:
        fails.append("gate2_fails_fair_null")
    if not g3:
        fails.append("gate3_not_regime_resilient")
    if not g4:
        fails.append("gate4_decile_profile_not_explainable")
    return {
        "passes_DEC_Y1": passes,
        "classification": classification,
        "gate1_tl_real_sig_positive": g1,
        "gate2_beats_fair_null_95": g2,
        "gate3_regime_resilient_3way": g3,
        "gate4_decile_profile_explainable": g4,
        "regime_alignment_aligned": bool(regime.get("alignment", {}).get("aligned")),
        "tl_real_available": bool(cpi_ok),
        "failures": fails,
    }


# ===========================================================================
# Orchestrator
# ===========================================================================
def _value_block(close_ff, funds, rebal, dates, win_dates, cpi, xu100, fx, us_cpi, kind, null_resamples):
    """All three legs + verdict for one value metric (kind in {'pb','ep'})."""
    rank_rebal = value_rank_panel(funds, close_ff, dates, kind)          # at rebalance dates (tilt/decile)
    rank_daily = value_rank_panel(funds, close_ff, win_dates, kind)      # daily (AYAK-1 IC)

    tercile = tilt_block(close_ff, rank_rebal, rebal, cpi, xu100, fx, us_cpi, "tercile", null_resamples)
    quintile = tilt_block(close_ff, rank_rebal, rebal, cpi, xu100, fx, us_cpi, "quintile", null_resamples)
    ayak1_ic = rank_ic_leg(rank_daily, close_ff)
    ayak2_decile = decile_leg(close_ff, rank_rebal, rebal, cpi)
    ayak3_regime = regime_leg(tercile["per_period"]["tl_real"], tercile["per_period"]["periods"])
    verdict = value_only_verdict(tercile["tl_real"], tercile["fair_null"], ayak3_regime, ayak2_decile)
    return {
        "value_metric": kind,
        "tilt_tercile": tercile,
        "tilt_quintile": quintile,
        "ayak1_rank_ic": ayak1_ic,
        "ayak2_decile_monotonicity": ayak2_decile,
        "ayak3_regime_resilience": ayak3_regime,
        "verdict_DEC_Y1": verdict,
    }


def run_value_only_regime(
    close: pd.DataFrame,
    xu100: pd.Series,
    funds: pd.DataFrame,
    cpi: pd.Series | None = None,
    fx: pd.Series | None = None,
    us_cpi: pd.Series | None = None,
    snapshot_meta: dict | None = None,
    out_path: Path | str | None = None,
    null_resamples: int = cfg.VOR_NULL_N_RESAMPLES,
) -> dict:
    """Full D-Y1-001 measurement. Returns the results dict (and writes JSON if out_path).

    PRIMARY = book-to-market (1/(P/B)); ROBUSTNESS = E/P. Verdict keyed on PRIMARY.
    """
    close_ff = close.sort_index().ffill()
    rebal = k2.rebalance_dates(close_ff.index, anchors=cfg.VOR_REBALANCE_ANCHORS,
                               start=cfg.VOR_WINDOW_START, end=cfg.VOR_WINDOW_END)
    if len(rebal) < 3:
        raise ValueError(f"need >=3 rebalance dates, got {len(rebal)}")
    dates = pd.DatetimeIndex(rebal)
    start = pd.Timestamp(cfg.VOR_WINDOW_START)
    end = pd.Timestamp(cfg.VOR_WINDOW_END)
    win_dates = close_ff.index[(close_ff.index >= start) & (close_ff.index <= end)]

    primary = _value_block(close_ff, funds, rebal, dates, win_dates, cpi, xu100, fx, us_cpi,
                           cfg.VOR_VALUE_PRIMARY, null_resamples)
    robust = _value_block(close_ff, funds, rebal, dates, win_dates, cpi, xu100, fx, us_cpi,
                          cfg.VOR_VALUE_ROBUST, null_resamples)

    results = {
        "directive": "D-Y1-001",
        "title": "Value-only tilt -- REGIME-RESILIENCE test (Yol-1 Asama-1) -- results",
        "config_version": cfg.VOR_CONFIG_VERSION,
        "basis": "RR-Y1.md sec.SORU-1 (conflict resolution) + Recommendations Soru-1 #1/#3",
        "window": {"start": cfg.VOR_WINDOW_START, "end": cfg.VOR_WINDOW_END},
        "rebalance_dates": [d.strftime("%Y-%m-%d") for d in rebal],
        "n_rebalances": len(rebal),
        "value_primary": cfg.VOR_VALUE_PRIMARY,
        "value_robust": cfg.VOR_VALUE_ROBUST,
        "decision_owner": "the project (DEC-039)",
        "survivorship_bias": cfg.VOR_SURVIVORSHIP_BIAS,
        "tl_real_available": cpi is not None,
        "usd_real_available": (fx is not None and us_cpi is not None),
        "single_factor_only": True,
        "primary_value_metric": primary,
        "robustness_value_metric": robust,
        "verdict_DEC_Y1": primary["verdict_DEC_Y1"],
        "snapshot_meta": snapshot_meta or {},
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("D-Y1-001 results written: %s (passes=%s)",
                    out_path, results["verdict_DEC_Y1"]["passes_DEC_Y1"])
    return results


# ===========================================================================
# Offline frozen-snapshot loaders + CLI
# ===========================================================================
def _load_series(parquet_name: str, value_col: str) -> pd.Series:
    df = pd.read_parquet(_SNAPSHOT_DIR / f"{parquet_name}.parquet")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[value_col].sort_index()


def _run_from_frozen(out_path: Path | str | None = None, null_resamples: int = cfg.VOR_NULL_N_RESAMPLES) -> dict:
    """Load D-191 / D-187 frozen snapshots (offline, no network) and run."""
    from src.screening import snapshot as snap

    price_long = pd.read_parquet(_SNAPSHOT_DIR / f"{cfg.VOR_PRICE_SNAPSHOT}.parquet")
    close, xu100 = snap.to_close_panel(price_long)
    funds = pd.read_parquet(_SNAPSHOT_DIR / f"{cfg.VOR_FUND_SNAPSHOT}.parquet")
    cpi = _load_series(cfg.VOR_TUFE_SNAPSHOT, "value")
    try:
        fx = _load_series(cfg.VOR_FX_SNAPSHOT, "usdtry")
    except (FileNotFoundError, KeyError):
        fx = None
    meta = {
        "price_snapshot": cfg.VOR_PRICE_SNAPSHOT,
        "fund_snapshot": cfg.VOR_FUND_SNAPSHOT,
        "tufe_snapshot": cfg.VOR_TUFE_SNAPSHOT,
        "fx_snapshot": cfg.VOR_FX_SNAPSHOT,
        "fx_coverage_start": str(fx.index.min().date()) if fx is not None and len(fx) else None,
        "us_cpi": "None -> USD-nominal (labeled, non-gating)",
        "offline": True,
    }
    return run_value_only_regime(close, xu100, funds, cpi=cpi, fx=fx, us_cpi=None,
                                 snapshot_meta=meta, out_path=out_path, null_resamples=null_resamples)


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Value-only regime-resilience backtest (D-Y1-001)")
    p.add_argument("--run", action="store_true", help="run from frozen snapshots (offline)")
    args = p.parse_args()
    if args.run:
        _run_from_frozen(out_path=_RESULTS_DIR / "value_only_regime_results.json")
        return
    p.print_help()


if __name__ == "__main__":
    _main()

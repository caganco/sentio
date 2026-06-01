"""K2 factor-tilt PORTFOLIO backtest engine. D-191.

Long-only, equal-weight, semi-annual-rebalanced tilt over VALUE + PROFITABILITY +
LOW-VOL, measured net of cost/tax/slippage in TL-real (PRIMARY gate), XU100-relative
and USD-real (reported), against a portfolio-level FAIR random-selection null, with
an in-sample/out-of-sample split. Tests SPEC_YOL2 KATMAN 2.

Strangler: reuses factors.py (value_ratios, realized_vol, PIT helpers),
factor_ic_harness.py (rank_panel, block_bootstrap_ci), snapshot.py (freeze/load,
content_hash), transaction_cost.py, macro_sources.py read-only. Does NOT touch them.
No composite/conviction/MASTER_WEIGHTS or signal/backtest engine imports.

Decision owner: Orchestrator+Cagan (DEC-039). Harness MEASURES + RECOMMENDS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import unicodedata
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import k2_tilt_config as cfg
from src.screening.factor_ic_harness import block_bootstrap_ci, rank_panel
from src.screening.factors import realized_vol, value_ratios
from src.screening.k2_profitability import profitability_panel

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "snapshots"
_RESULTS_DIR = Path(__file__).parent.parent.parent / "docs" / "k2_test"

K2_FUND_COLS = [
    "ticker", "fiscal_year", "period_end", "pub_date", "is_bank",
    "book_eaoop", "issued_capital", "gross_profit", "total_assets", "net_income",
]


# ===========================================================================
# Calendar
# ===========================================================================
def rebalance_dates(
    close_index: pd.DatetimeIndex,
    anchors: tuple[int, ...] = cfg.K2_REBALANCE_ANCHORS,
    start: str = cfg.K2_WINDOW_START,
    end: str = cfg.K2_WINDOW_END,
) -> list[pd.Timestamp]:
    """Last trading day on/before each (year, anchor-month-end) within [start, end].

    Semi-annual anchors (6, 12) -> last trading day <= Jun-30 and <= Dec-31 each
    year. Deterministic, look-ahead safe (uses only the trading calendar).
    """
    idx = pd.DatetimeIndex(sorted(close_index))
    idx = idx[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
    if len(idx) == 0:
        return []
    out: list[pd.Timestamp] = []
    years = range(idx[0].year, idx[-1].year + 1)
    for yr in years:
        for m in anchors:
            anchor = pd.Timestamp(yr, m, 1) + pd.offsets.MonthEnd(0)
            elig = idx[idx <= anchor]
            if len(elig):
                d = elig[-1]
                if d not in out and pd.Timestamp(start) <= d <= pd.Timestamp(end):
                    out.append(d)
    return sorted(set(out))


# ===========================================================================
# Factor rank panels at rebalance dates
# ===========================================================================
def factor_rank_panels(
    funds: pd.DataFrame,
    close: pd.DataFrame,
    dates: pd.DatetimeIndex,
    profit_kind: str = cfg.K2_PROFITABILITY_PRIMARY,
) -> dict[str, pd.DataFrame]:
    """Cross-sectional rank panels (date x ticker) for value / profitability / lowvol.

    value = 1/(P/B) -> low P/B (cheap) gets HIGH rank (invert=True on P/B).
    profitability -> high GP/TA (or ROE) gets HIGH rank (invert=False).
    lowvol -> low realized vol gets HIGH rank (invert=True on vol).
    All look-ahead safe (PIT fundamentals + trailing vol).
    """
    pb, _ev = value_ratios(funds, close, dates, par=cfg.K2_PAR_VALUE)
    prof = profitability_panel(funds, close, dates, kind=profit_kind)
    vol_full = realized_vol(close, cfg.K2_LOWVOL_WINDOW)
    vol = vol_full.reindex(dates)
    return {
        "value": rank_panel(pb, invert=True),
        "profitability": rank_panel(prof, invert=False),
        "lowvol": rank_panel(vol, invert=True),
    }


def composite_rank(ranks: dict[str, pd.DataFrame], require_all: bool = cfg.K2_REQUIRE_ALL_FACTORS) -> pd.DataFrame:
    """Equal-weight average of per-factor rank panels (invariant 4: no weights).

    require_all=True: a (date, ticker) is eligible only if ALL factors are present
    -> the composite is well-defined (NULL where any factor missing).
    """
    keys = list(ranks)
    aligned = [ranks[k] for k in keys]
    idx = aligned[0].index
    cols = sorted(set().union(*[set(r.columns) for r in aligned]))
    stacked = np.stack([r.reindex(index=idx, columns=cols).to_numpy(float) for r in aligned])
    if require_all:
        present = ~np.isnan(stacked).any(axis=0)
        mean = np.nanmean(stacked, axis=0)
        comp = np.where(present, mean, np.nan)
    else:
        comp = np.nanmean(stacked, axis=0)
    return pd.DataFrame(comp, index=idx, columns=cols)


# ===========================================================================
# Selection
# ===========================================================================
def select_basket(
    date: pd.Timestamp,
    comp: pd.DataFrame,
    ranks: dict[str, pd.DataFrame],
    variant: str,
) -> list[str]:
    """Return the selected ticker basket at `date` for a selection variant.

    composite_tercile / composite_quintile: top fraction by composite rank.
    tercile_intersection: names in the top tercile of EVERY factor rank.
    """
    if variant == "tercile_intersection":
        sets = []
        for rp in ranks.values():
            row = rp.loc[date].dropna() if date in rp.index else pd.Series(dtype=float)
            if row.empty:
                return []
            cut = row.quantile(1.0 - cfg.K2_TERCILE)
            sets.append(set(row[row >= cut].index))
        names = set.intersection(*sets) if sets else set()
        return sorted(names)

    row = comp.loc[date].dropna() if date in comp.index else pd.Series(dtype=float)
    if row.empty:
        return []
    frac = cfg.K2_QUINTILE if variant == "composite_quintile" else cfg.K2_TERCILE
    cut = row.quantile(1.0 - frac)
    return sorted(row[row >= cut].index)


# ===========================================================================
# Per-period portfolio returns + cost + tax
# ===========================================================================
def _round_trip(basket: list[str], tier: str = cfg.K2_BROKER_TIER) -> float:
    from src.risk.transaction_cost import round_trip_cost_pct
    if not basket:
        return 0.0
    return float(np.mean([round_trip_cost_pct(t, tier) for t in basket]))


def _turnover(prev: list[str], cur: list[str]) -> float:
    """One-way turnover 0.5*sum|w_new - w_old| in [0,1] for equal-weight baskets."""
    if not cur:
        return 0.0
    if not prev:
        return 1.0
    wp = {t: 1.0 / len(prev) for t in prev}
    wc = {t: 1.0 / len(cur) for t in cur}
    names = set(wp) | set(wc)
    return 0.5 * sum(abs(wc.get(n, 0.0) - wp.get(n, 0.0)) for n in names)


def _basket_gross(close_ff: pd.DataFrame, basket: list[str], d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    """Equal-weight gross simple return of `basket` over (d0, d1] (NaN names dropped)."""
    if not basket:
        return float("nan")
    p0 = close_ff.loc[d0, basket]
    p1 = close_ff.loc[d1, basket]
    r = (p1 / p0 - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
    return float(r.mean()) if len(r) else float("nan")


def _tax_drag(d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    """Frozen dividend-withholding drag over the holding period (caveat: assumed yield)."""
    days = max(0, (pd.Timestamp(d1) - pd.Timestamp(d0)).days)
    return cfg.K2_DIV_WITHHOLDING * cfg.K2_ASSUMED_ANNUAL_DIV_YIELD * (days / 365.0)


def period_net_returns(
    close_ff: pd.DataFrame,
    baskets: list[list[str]],
    rebal: list[pd.Timestamp],
    tier: str = cfg.K2_BROKER_TIER,
) -> dict:
    """Per-holding-period gross/net returns + turnover/cost arrays.

    net_i = gross_i - cost_i - tax_i, where
      cost_i = turnover_i * (avg_round_trip + slippage_round_trip),
      tax_i  = dividend-withholding drag over the period.
    """
    slip_rt = 2.0 * cfg.K2_SLIPPAGE_BPS / 10_000.0
    n = len(rebal) - 1
    gross, net, costs, turns = [], [], [], []
    prev: list[str] = []
    for i in range(n):
        d0, d1 = rebal[i], rebal[i + 1]
        b = baskets[i]
        g = _basket_gross(close_ff, b, d0, d1)
        tau = _turnover(prev, b)
        c = tau * (_round_trip(b, tier) + slip_rt)
        tax = _tax_drag(d0, d1)
        gross.append(g)
        turns.append(tau)
        costs.append(c)
        net.append(g - c - tax if np.isfinite(g) else float("nan"))
        prev = b
    return {"gross": gross, "net": net, "cost": costs, "turnover": turns,
            "periods": [(rebal[i].strftime("%Y-%m-%d"), rebal[i + 1].strftime("%Y-%m-%d"))
                        for i in range(n)]}


# ===========================================================================
# Return-basis transforms (portfolio level)
# ===========================================================================
def _ratio_over(series: pd.Series | None, d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    if series is None or len(series) == 0:
        return float("nan")
    a = series.asof(d0)
    b = series.asof(d1)
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
        return float("nan")
    return float(b / a)


def to_real(net: list[float], rebal: list[pd.Timestamp], cpi: pd.Series | None) -> list[float]:
    """TL-real per-period net return: (1+net)/(cpi1/cpi0) - 1. cpi None -> all NaN."""
    out = []
    for i, r in enumerate(net):
        if cpi is None or not np.isfinite(r):
            out.append(float("nan"))
            continue
        infl = _ratio_over(cpi, rebal[i], rebal[i + 1])
        out.append((1.0 + r) / infl - 1.0 if np.isfinite(infl) else float("nan"))
    return out


def to_relative(net: list[float], rebal: list[pd.Timestamp], xu100: pd.Series) -> list[float]:
    """XU100-relative per-period net return: (1+net)/(1+xu_ret) - 1 (geometric excess)."""
    out = []
    for i, r in enumerate(net):
        if not np.isfinite(r):
            out.append(float("nan"))
            continue
        ratio = _ratio_over(xu100, rebal[i], rebal[i + 1])
        out.append((1.0 + r) / ratio - 1.0 if np.isfinite(ratio) else float("nan"))
    return out


def to_usd_real(
    net: list[float], rebal: list[pd.Timestamp],
    fx: pd.Series | None, us_cpi: pd.Series | None,
) -> tuple[list[float], bool]:
    """USD per-period return: (1+net)*(fx0/fx1) - 1, optionally US-CPI-deflated.

    Returns (series, is_real). is_real=False -> values are USD-NOMINAL (labeled).
    """
    out, is_real = [], us_cpi is not None
    for i, r in enumerate(net):
        if fx is None or not np.isfinite(r):
            out.append(float("nan"))
            continue
        fxr = _ratio_over(fx, rebal[i], rebal[i + 1])      # fx1/fx0
        if not np.isfinite(fxr) or fxr <= 0:
            out.append(float("nan"))
            continue
        usd = (1.0 + r) * (1.0 / fxr) - 1.0                 # multiply by fx0/fx1
        if is_real:
            infl = _ratio_over(us_cpi, rebal[i], rebal[i + 1])
            usd = (1.0 + usd) / infl - 1.0 if np.isfinite(infl) else float("nan")
        out.append(usd)
    return out, is_real


# ===========================================================================
# Daily equity + drawdown (reporting)
# ===========================================================================
def daily_equity_curve(
    close_ff: pd.DataFrame, baskets: list[list[str]],
    rebal: list[pd.Timestamp], costs: list[float],
) -> pd.Series:
    """Daily mark-to-market equity (nominal), cost charged as a discrete drop at rebalance."""
    rets = close_ff.pct_change()
    eq = 1.0
    dates = [rebal[0]]
    vals = [eq]
    for i in range(len(rebal) - 1):
        d0, d1 = rebal[i], rebal[i + 1]
        eq *= (1.0 - costs[i])
        win = rets.loc[(rets.index > d0) & (rets.index <= d1)]
        b = baskets[i]
        for day, row in win.iterrows():
            pr = row[b].replace([np.inf, -np.inf], np.nan).dropna() if b else pd.Series(dtype=float)
            day_ret = float(pr.mean()) if len(pr) else 0.0
            eq *= (1.0 + day_ret)
            dates.append(day)
            vals.append(eq)
    return pd.Series(vals, index=pd.DatetimeIndex(dates))


def max_drawdown(equity: pd.Series) -> float:
    arr = np.asarray(equity, dtype=float)
    if len(arr) < 2:
        return 0.0
    peak = np.maximum.accumulate(arr)
    dd = (arr - peak) / peak
    return float(np.min(dd))


# ===========================================================================
# Fair portfolio random null
# ===========================================================================
def fair_random_null_portfolio(
    close_ff: pd.DataFrame,
    eligible_pools: list[list[str]],
    basket_sizes: list[int],
    rebal: list[pd.Timestamp],
    cpi: pd.Series | None,
    strategy_real_mean: float,
    tier: str = cfg.K2_BROKER_TIER,
    seed: int = cfg.K2_NULL_SEED,
    n_resamples: int = cfg.K2_NULL_N_RESAMPLES,
) -> dict:
    """Null distribution of full-window mean per-period net TL-real return for
    matched random baskets.

    Matched: same rebalance dates / holding / cost+tax, same per-rebalance basket
    size N, same eligible pool. Randomized: ONLY name selection (uniform w/o
    replacement) -> isolates factor-selection skill. random_pctile = P(null <
    strategy); beats iff >= K2_DECISION_RANDOM_PCTILE_MIN.
    """
    n = len(rebal) - 1
    bad = {"n_resamples": 0, "pool_ok": False, "null_mean": float("nan"),
           "null_p95": float("nan"), "strategy_real_mean": _r(strategy_real_mean),
           "random_pctile": float("nan"), "beats_fair_null_95": False}
    if not np.isfinite(strategy_real_mean) or cpi is None or n <= 0:
        return bad
    # Mirror the strategy: periods where the strategy basket is empty (e.g. lowvol
    # undefined in the first ~252 days) are dropped from BOTH the strategy mean and
    # the null -> matched periods. Only periods with a non-empty strategy basket
    # must have a pool large enough to draw N names without replacement.
    active = [i for i in range(n) if basket_sizes[i] > 0]
    if not active:
        return bad
    for i in active:
        if len(eligible_pools[i]) < basket_sizes[i]:
            return bad
    rng = np.random.default_rng(seed)
    null_means = np.empty(n_resamples, dtype=float)
    for r in range(n_resamples):
        baskets = []
        for i in range(n):
            k = basket_sizes[i]
            if k <= 0:                       # empty period -> empty basket (matched drop)
                baskets.append([])
                continue
            pool = eligible_pools[i]
            pick = rng.choice(len(pool), size=k, replace=False)
            baskets.append([pool[j] for j in pick])
        pr = period_net_returns(close_ff, baskets, rebal, tier)
        real = to_real(pr["net"], rebal, cpi)
        vals = [v for v in real if np.isfinite(v)]
        null_means[r] = float(np.mean(vals)) if vals else float("nan")
    finite = null_means[np.isfinite(null_means)]
    if len(finite) == 0:
        pctile = float("nan")
        beats = False
    else:
        pctile = float(np.mean(finite < strategy_real_mean))
        beats = bool(pctile >= cfg.K2_DECISION_RANDOM_PCTILE_MIN)
    return {
        "n_resamples": int(len(finite)), "pool_ok": True,
        "null_mean": _r(float(np.mean(finite))) if len(finite) else float("nan"),
        "null_p95": _r(float(np.percentile(finite, 95))) if len(finite) else float("nan"),
        "strategy_real_mean": _r(strategy_real_mean),
        "random_pctile": round(pctile, 4) if np.isfinite(pctile) else None,
        "beats_fair_null_95": beats,
    }


# ===========================================================================
# Significance + in/out + verdict
# ===========================================================================
def mean_ci(series: list[float]) -> dict:
    """Block-bootstrap (block=1, near-independent semi-annual periods) mean + 95% CI."""
    arr = np.array([v for v in series if np.isfinite(v)], dtype=float)
    if len(arr) < 2:
        return {"n": int(len(arr)), "mean": float("nan"),
                "ci95_low": float("nan"), "ci95_high": float("nan"), "ci_excludes_zero": False}
    lo, hi = block_bootstrap_ci(arr, block=cfg.K2_SIG_BLOCK, n_boot=cfg.K2_SIG_N_BOOT, seed=cfg.K2_SIG_SEED)
    return {"n": int(len(arr)), "mean": _r(float(np.mean(arr))),
            "ci95_low": _r(lo), "ci95_high": _r(hi),
            "ci_excludes_zero": bool(lo > 0 or hi < 0)}


def split_in_out(series: list[float], rebal: list[pd.Timestamp]) -> dict:
    """Split per-period series into in-sample (rebalance < K2_INSAMPLE_END) / out."""
    cut = pd.Timestamp(cfg.K2_INSAMPLE_END)
    ins = [series[i] for i in range(len(series)) if rebal[i] < cut]
    out = [series[i] for i in range(len(series)) if rebal[i] >= cut]
    return {
        "insample_end": cfg.K2_INSAMPLE_END,
        "in": mean_ci(ins), "out": mean_ci(out),
        "thin_n_caveat": "semi-annual -> ~6-7 periods/slice; wide CIs / low power, do not over-interpret one slice",
    }


def k2_verdict(real_ci: dict, null_block: dict, inout: dict, factor_significance: dict) -> dict:
    """Frozen DEC-K2: all four gates. USD-real / relative are reported, not gates."""
    g1 = bool(real_ci.get("mean", float("nan")) > 0 and real_ci.get("ci_excludes_zero")
              and real_ci.get("ci95_low", float("-inf")) > 0)
    g2 = bool(null_block.get("beats_fair_null_95"))
    out_mean = inout.get("out", {}).get("mean", float("nan"))
    g3 = bool(np.isfinite(out_mean) and out_mean > 0)
    g4 = bool(factor_significance.get("any_factor_significant"))
    cpi_ok = real_ci.get("n", 0) >= 2 and np.isfinite(real_ci.get("mean", float("nan")))
    fails = []
    if not cpi_ok:
        fails.append("tl_real_unavailable_INCONCLUSIVE")
    if not g1:
        fails.append("tl_real_expectation_not_sig_positive")
    if not g2:
        fails.append("fails_fair_portfolio_null")
    if not g3:
        fails.append("out_of_sample_not_positive")
    if not g4:
        fails.append("no_factor_independently_significant")
    return {
        "passes_DEC_K2": bool(cpi_ok and g1 and g2 and g3 and g4),
        "gate1_tl_real_sig_positive": g1,
        "gate2_beats_fair_null_95": g2,
        "gate3_out_of_sample_positive": g3,
        "gate4_factor_independently_significant": g4,
        "tl_real_available": bool(cpi_ok),
        "failures": fails,
    }


# ===========================================================================
# Orchestrator
# ===========================================================================
def _r(x) -> float | None:
    try:
        return round(float(x), 6) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _eligible_pools(comp: pd.DataFrame, rebal: list[pd.Timestamp]) -> list[list[str]]:
    pools = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        row = comp.loc[d].dropna() if d in comp.index else pd.Series(dtype=float)
        pools.append(sorted(row.index))
    return pools


def _variant_block(
    close_ff, comp, ranks, rebal, cpi, xu100, fx, us_cpi, variant,
    null_resamples: int = cfg.K2_NULL_N_RESAMPLES,
) -> dict:
    baskets = [select_basket(rebal[i], comp, ranks, variant) for i in range(len(rebal) - 1)]
    sizes = [len(b) for b in baskets]
    pr = period_net_returns(close_ff, baskets, rebal)
    net = pr["net"]
    real = to_real(net, rebal, cpi)
    rel = to_relative(net, rebal, xu100)
    usd, usd_is_real = to_usd_real(net, rebal, fx, us_cpi)
    real_ci = mean_ci(real)
    pools = _eligible_pools(comp, rebal)
    null = fair_random_null_portfolio(close_ff, pools, sizes, rebal, cpi,
                                      real_ci.get("mean", float("nan")),
                                      n_resamples=null_resamples)
    eq = daily_equity_curve(close_ff, baskets, rebal, pr["cost"])
    return {
        "variant": variant,
        "basket_sizes": sizes,
        "mean_turnover": _r(np.nanmean(pr["turnover"])) if sizes else None,
        "mean_cost": _r(np.nanmean(pr["cost"])) if sizes else None,
        "tl_real": real_ci,
        "tl_real_inout": split_in_out(real, rebal),
        "xu100_relative": mean_ci(rel),
        "usd_real": {**mean_ci(usd), "is_real": usd_is_real,
                     "basis": "usd_real" if usd_is_real else "usd_nominal"},
        "fair_null": null,
        "max_drawdown": _r(max_drawdown(eq)),
        "n_periods": len(net),
        "per_period": {"net": [_r(v) for v in net], "tl_real": [_r(v) for v in real],
                       "relative": [_r(v) for v in rel], "periods": pr["periods"]},
    }


def run_k2(
    close: pd.DataFrame,
    xu100: pd.Series,
    funds: pd.DataFrame,
    cpi: pd.Series | None = None,
    fx: pd.Series | None = None,
    us_cpi: pd.Series | None = None,
    snapshot_meta: dict | None = None,
    out_path: Path | str | None = None,
    null_resamples: int = cfg.K2_NULL_N_RESAMPLES,
) -> dict:
    """Full K2 measurement. Returns the results dict (and writes JSON if out_path)."""
    close_ff = close.sort_index().ffill()
    rebal = rebalance_dates(close_ff.index)
    if len(rebal) < 3:
        raise ValueError(f"need >=3 rebalance dates, got {len(rebal)}")
    dates = pd.DatetimeIndex(rebal)
    ranks = factor_rank_panels(funds, close_ff, dates, profit_kind=cfg.K2_PROFITABILITY_PRIMARY)
    comp = composite_rank(ranks)

    # Composite selection variants (N<=3).
    variants = {v: _variant_block(close_ff, comp, ranks, rebal, cpi, xu100, fx, us_cpi, v,
                                  null_resamples=null_resamples)
                for v in cfg.K2_SELECTION_VARIANTS}

    # Single-factor diagnostic portfolios (gate 4): tercile on each single factor.
    single = {}
    for f in cfg.K2_SINGLE_FACTORS:
        if f == "profitability":
            rmap = {"profitability": ranks["profitability"]}
        elif f == "value":
            rmap = {"value": ranks["value"]}
        else:
            rmap = {"lowvol": ranks["lowvol"]}
        sc = composite_rank(rmap, require_all=True)
        single[f] = _variant_block(close_ff, sc, rmap, rebal, cpi, xu100, fx, us_cpi,
                                   "composite_tercile", null_resamples=null_resamples)

    def _factor_sig(fb: dict) -> bool:
        return bool(fb["tl_real"].get("ci_excludes_zero") and fb["tl_real"].get("mean", 0) > 0
                    and fb["fair_null"].get("beats_fair_null_95"))

    factor_significance = {
        "by_factor": {f: {"tl_real_sig_positive": bool(single[f]["tl_real"].get("ci_excludes_zero")
                                                       and single[f]["tl_real"].get("mean", 0) > 0),
                          "beats_fair_null_95": bool(single[f]["fair_null"].get("beats_fair_null_95"))}
                      for f in single},
        "profitability_significant": _factor_sig(single["profitability"]),
        "any_factor_significant": any(_factor_sig(single[f]) for f in single),
    }

    primary = variants[cfg.K2_PRIMARY_VARIANT]
    verdict = k2_verdict(primary["tl_real"], primary["fair_null"],
                         primary["tl_real_inout"], factor_significance)

    results = {
        "directive": "D-191",
        "title": "K2 factor-tilt portfolio backtest -- results",
        "config_version": cfg.K2_CONFIG_VERSION,
        "window": {"start": cfg.K2_WINDOW_START, "end": cfg.K2_WINDOW_END},
        "rebalance_dates": [d.strftime("%Y-%m-%d") for d in rebal],
        "n_rebalances": len(rebal),
        "profitability_primary": cfg.K2_PROFITABILITY_PRIMARY,
        "primary_variant": cfg.K2_PRIMARY_VARIANT,
        "decision_owner": "Orchestrator+Cagan (DEC-039)",
        "survivorship_bias": cfg.K2_SURVIVORSHIP_BIAS,
        "tl_real_available": cpi is not None,
        "usd_real_available": (fx is not None and us_cpi is not None),
        "variants": variants,
        "single_factor": single,
        "factor_significance": factor_significance,
        "verdict_DEC_K2": verdict,
        "snapshot_meta": snapshot_meta or {},
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("K2 results written: %s (verdict passes=%s)",
                    out_path, verdict["passes_DEC_K2"])
    return results


# ===========================================================================
# Fundamental snapshot (additive; K2 column set, 8 fiscal years)
# ===========================================================================
def freeze_k2_fundamentals(
    universe: list[str],
    out_dir: Path | str = _SNAPSHOT_DIR,
    fetch_fn: Callable | None = None,
    timestamp: str | None = None,
    tag: str = "k2",
) -> tuple[pd.DataFrame, dict]:
    """Freeze (or load) per-ticker annual fundamentals with the K2 column set. D-191.

    Idempotent parquet+meta. K2_FUND_COLS adds gross_profit/total_assets/net_income
    (profitability) to the value fields. 8 fiscal years (K2_FISCAL_YEARS) via two
    4-period MaliTablo calls (default fetch). pub_date = period_end + lag (PIT).
    fetch_fn(ticker, fiscal_years, is_bank) -> {field: [v1..v8]} (injectable for tests).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pq = out_dir / f"{tag}_fundamentals.parquet"
    mj = out_dir / f"{tag}_fundamentals.meta.json"
    if pq.exists() and mj.exists():
        df = pd.read_parquet(pq)
        meta = json.loads(mj.read_text(encoding="utf-8"))
        logger.info("K2 fundamental snapshot frozen-load: %s (%d rows)", pq.name, len(df))
        return df, meta

    if fetch_fn is None:
        fetch_fn = _default_k2_malitablo_fetch

    years = list(cfg.K2_FISCAL_YEARS)
    rows: list[dict] = []
    null_tickers: list[str] = []
    bank_n = 0
    for ticker in sorted(set(universe)):
        is_bank = ticker in cfg.K2_BANKS
        if is_bank:
            bank_n += 1
        try:
            fields = fetch_fn(ticker, years, is_bank)
        except Exception as exc:  # noqa: BLE001 - one ticker must not break the snapshot
            logger.warning("K2 MaliTablo fetch failed ticker=%s: %s", ticker, exc)
            null_tickers.append(ticker)
            continue
        if not fields or fields.get("book_eaoop") is None:
            null_tickers.append(ticker)
            continue
        for i, yr in enumerate(years):
            book = _nth(fields, "book_eaoop", i)
            if book is None:
                continue
            period_end = f"{yr}-12-31"
            pub = (pd.Timestamp(period_end) + pd.Timedelta(days=cfg.K2_ANNUAL_LAG_DAYS)).strftime("%Y-%m-%d")
            rows.append({
                "ticker": ticker, "fiscal_year": int(yr), "period_end": period_end,
                "pub_date": pub, "is_bank": bool(is_bank), "book_eaoop": book,
                "issued_capital": _nth(fields, "issued_capital", i),
                "gross_profit": None if is_bank else _nth(fields, "gross_profit", i),
                "total_assets": _nth(fields, "total_assets", i),
                "net_income": _nth(fields, "net_income", i),
            })

    df = pd.DataFrame(rows, columns=K2_FUND_COLS)
    chash = _hash_df(df) if len(df) else "empty"
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "directive": "D-191", "source": "Is Yatirim MaliTablo (XI_29 / UFRS)",
        "n_rows": int(len(df)), "content_hash": chash, "timestamp_utc": ts,
        "fiscal_years": years, "annual_lag_days": cfg.K2_ANNUAL_LAG_DAYS,
        "itemcodes_value": cfg.K2_MALITABLO_ITEMCODES_VALUE,
        "itemcodes_profit": cfg.K2_MALITABLO_ITEMCODES_PROFIT,
        "coverage": {
            "requested_n": len(set(universe)),
            "loaded_n": int(df["ticker"].nunique()) if len(df) else 0,
            "null_tickers": sorted(null_tickers), "banks_n": bank_n,
        },
        "config_version": cfg.K2_CONFIG_VERSION,
    }
    df.to_parquet(pq, index=False)
    mj.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("K2 fundamental snapshot frozen: %s rows=%d hash=%s null=%d",
                pq.name, len(df), chash[:12], len(null_tickers))
    return df, meta


def _nth(fields: dict, key: str, i: int):
    seq = fields.get(key)
    if not isinstance(seq, (list, tuple)) or i >= len(seq):
        return None
    return seq[i]


def _hash_df(df: pd.DataFrame) -> str:
    canon = df.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)
    return hashlib.sha256(canon.to_csv(index=False, float_format="%.10g").encode("utf-8")).hexdigest()


def _default_k2_malitablo_fetch(ticker: str, fiscal_years: list[int], is_bank: bool) -> dict:
    """Live MaliTablo fetch (two 4-period calls merged) for one ticker, K2 fields."""
    from src.data.isyatirim_malitablo_fetcher import fetch_malitablo, parse_values

    group = cfg.K2_MALITABLO_GROUP_BANK if is_bank else cfg.K2_MALITABLO_GROUP_NONBANK
    codes = {**cfg.K2_MALITABLO_ITEMCODES_VALUE, **cfg.K2_MALITABLO_ITEMCODES_PROFIT}
    years = list(fiscal_years)
    out: dict[str, list] = {f: [] for f in codes}
    for s in range(0, len(years), 4):
        chunk = years[s:s + 4]
        if len(chunk) < 4:                       # pad to the mandatory 4 periods
            chunk = chunk + [chunk[-1]] * (4 - len(chunk))
        periods = [(int(y), 12) for y in chunk]
        rows = fetch_malitablo(ticker, periods, financial_group=group)
        parsed = parse_values(rows, codes)
        for f in codes:
            out[f].extend(parsed[f][:len(years[s:s + 4])])
    return out


# ===========================================================================
# Item-code discovery (Stage-0 Faz B; result-independent)
# ===========================================================================
def _ascii_fold(s: str) -> str:
    """Lowercase + strip Turkish diacritics for accent-insensitive name matching."""
    # Turkish-specific folds (dotless-i and others do NOT NFKD-decompose cleanly).
    # Built from hex code points to keep this source file pure ASCII (cp1254/ASCII rule):
    #   0131 i-dotless 0130 I-dot  015F/015E s-cedilla  00E7/00C7 c-cedilla
    #   00F6/00D6 o-umlaut  011F/011E g-breve  00FC/00DC u-umlaut
    repl = {chr(0x0131): "i", chr(0x0130): "i",
            chr(0x015F): "s", chr(0x015E): "s",
            chr(0x00E7): "c", chr(0x00C7): "c",
            chr(0x00F6): "o", chr(0x00D6): "o",
            chr(0x011F): "g", chr(0x011E): "g",
            chr(0x00FC): "u", chr(0x00DC): "u"}
    s = "".join(repl.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def discover_profit_itemcodes(company_code: str = "EREGL", financial_group: str = "XI_29") -> dict:
    """Live discovery: print all (code, name) rows + auto-match profit patterns.

    Used ONCE at Stage-0 (Faz B) to freeze gross_profit/total_assets/net_income
    itemCodes by ascii-folded Turkish name. Result-independent (name->code map).
    """
    from src.data.isyatirim_malitablo_fetcher import discover_item_codes
    pairs = discover_item_codes(company_code, financial_group=financial_group)
    matched: dict[str, list[tuple[str, str]]] = {f: [] for f in cfg.K2_PROFIT_ITEMNAME_PATTERNS}
    for code, name in pairs:
        folded = _ascii_fold(name)
        for field, pats in cfg.K2_PROFIT_ITEMNAME_PATTERNS.items():
            if any(p in folded for p in pats):
                matched[field].append((code, name))
    return {"company": company_code, "group": financial_group,
            "all_rows": pairs, "matched": matched}


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="K2 factor-tilt backtest (D-191)")
    p.add_argument("--discover-itemcodes", action="store_true",
                   help="live MaliTablo discovery to freeze profit itemCodes (Faz B)")
    p.add_argument("--discover-company", default="EREGL")
    p.add_argument("--run", action="store_true", help="run the backtest from frozen snapshots")
    args = p.parse_args()

    if args.discover_itemcodes:
        res = discover_profit_itemcodes(args.discover_company)
        print("=== ALL ROWS (code | name) ===")
        for code, name in res["all_rows"]:
            print(f"{code} | {name}")
        print("\n=== AUTO-MATCHED ===")
        print(json.dumps(res["matched"], ensure_ascii=False, indent=2))
        return

    if args.run:
        from src.data.macro_sources import fetch_tufe_series
        from src.screening import snapshot as snap
        long_df, pmeta = snap.freeze_price_snapshot(
            snap.resolve_universe_v2(), cfg.K2_WINDOW_START, cfg.K2_WINDOW_END,
            adv_floor_tl=cfg.K2_ADV_FLOOR_TL, tag="k2", directive="D-191")
        close, xu100 = snap.to_close_panel(long_df)
        funds, fmeta = freeze_k2_fundamentals(snap.resolve_universe_v2())
        cpi = fetch_tufe_series(cfg.K2_WINDOW_START, cfg.K2_WINDOW_END)
        fx, _ = snap.freeze_fx_snapshot(cfg.K2_WINDOW_START, cfg.K2_WINDOW_END, tag="k2")
        meta = {"price": {k: pmeta.get(k) for k in ("content_hash", "loaded_universe_n", "window")},
                "fundamentals": {k: fmeta.get(k) for k in ("content_hash", "coverage")}}
        run_k2(close, xu100, funds, cpi=cpi, fx=fx, us_cpi=None,
               snapshot_meta=meta, out_path=_RESULTS_DIR / "factor_tilt_results.json")
        return

    p.print_help()


if __name__ == "__main__":
    _main()

"""Faz 0 Factor IC Validation Harness. D-177 / SPEC_PIVOT_ARCHITECTURE_1 sec.4.

MEASUREMENT only -- validates candidate factors (RS-vs-XU100, low-vol) by
standalone cross-sectional Spearman rank-IC BEFORE they enter any composite.
Does not produce signals, open trades, or finalize the factor set (DEC-039:
decision is Orchestrator+Cagan's; the harness RECOMMENDS).

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


def ic_stats(ics: np.ndarray, lags: int = cfg.NW_LAGS) -> dict:
    """Aggregate IC series -> mean/std/ICIR/naive-t/p/CI + Newey-West HAC t/p."""
    n = int(len(ics))
    if n == 0:
        return {"n_obs": 0, "mean_ic": float("nan"), "std_ic": float("nan"),
                "icir": float("nan"), "t_naive": float("nan"), "p_naive": float("nan"),
                "ci95_low": float("nan"), "ci95_high": float("nan"),
                "t_nw": float("nan"), "p_nw": float("nan")}
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
    se_nw = newey_west_se(ics, lags)
    if not math.isnan(se_nw) and se_nw > 0 and n > 1:
        t_nw = mean_ic / se_nw
        p_nw = float(2 * (1 - stats.t.cdf(abs(t_nw), df=n - 1)))
    else:
        t_nw = p_nw = float("nan")
    return {
        "n_obs": n, "mean_ic": mean_ic, "std_ic": std_ic, "icir": icir,
        "t_naive": t_naive, "p_naive": p_naive,
        "ci95_low": ci_low, "ci95_high": ci_high,
        "t_nw": t_nw, "p_nw": p_nw,
    }


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
    """Primitive IC (ICCalculator) + local series (NW/CI) + equivalence check."""
    prim = ICCalculator(signal_df, returns_df).compute_ic(col, horizon)
    ics = daily_ic_series(ranks[col], fwd_panels[horizon])
    local = ic_stats(ics)
    # equivalence at ic_calculator reporting precision (5 decimals)
    prim_mean = prim.mean_ic
    local_mean_5 = round(local["mean_ic"], 5) if local["n_obs"] else float("nan")
    if isinstance(prim_mean, float) and not math.isnan(prim_mean) and local["n_obs"]:
        equiv_ok = abs(local_mean_5 - prim_mean) < 1e-9
    else:
        equiv_ok = False
    ic_source = "primitive" if equiv_ok else "fallback"
    return {
        "factor": col, "horizon": horizon, "ic_source": ic_source,
        "equivalence_ok": bool(equiv_ok),
        "primitive": {"mean_ic": prim.mean_ic, "icir": prim.ir,
                      "t_stat": prim.t_stat, "p_value": prim.p_value,
                      "n_obs": prim.n_obs, "is_investable": prim.is_investable},
        "series": _round_dict(local),
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
    snapshot_kwargs: dict | None = None,
) -> dict:
    """Full Faz 0 measurement. Returns results dict and writes faz0_results.json."""
    universe = universe or snapshot.resolve_universe()
    long_df, meta = snapshot.freeze_price_snapshot(
        universe, start, end, **(snapshot_kwargs or {})
    )
    close, xu100 = snapshot.to_close_panel(long_df)

    ranks = build_factor_ranks(close, xu100)
    fwd_panels = {h: factors.forward_returns(close, h) for h in cfg.IC_HORIZONS}
    signal_df = build_signal_df(ranks)
    returns_df = build_returns_df(close, cfg.IC_HORIZONS)

    factor_cols = list(cfg.RS_LOOKBACKS_DAYS) + list(cfg.VOL_WINDOWS_DAYS) + ["composite"]
    per_factor: dict[str, dict] = {}
    for col in factor_cols:
        per_factor[col] = {
            str(h): compute_factor_ic(signal_df, returns_df, ranks, fwd_panels, col, h)
            for h in cfg.IC_HORIZONS
        }

    # primary horizon for decisions (T21 ~ 1 month)
    ph = "21"

    def _series_mean(col: str, h: str = ph) -> float:
        return per_factor[col][h]["series"]["mean_ic"]

    def _series_icir(col: str, h: str = ph) -> float:
        return per_factor[col][h]["series"]["icir"]

    # TEST 1 -- dilution: composite IC vs best single-factor IC (primary horizon)
    singles = list(cfg.RS_LOOKBACKS_DAYS) + list(cfg.VOL_WINDOWS_DAYS)
    best_single = max(singles, key=lambda c: _series_mean(c))
    test1 = {
        "primary_horizon": int(ph),
        "composite_ic": _series_mean("composite"),
        "best_single_factor": best_single,
        "best_single_ic": _series_mean(best_single),
        "dilution_flag": bool(_series_mean("composite") < _series_mean(best_single)),
        "note": "composite < best single => equal-weight rank average dilutes; "
                "narrow the factor SET (do not optimize weights, invariant 4).",
    }

    # TEST 2 -- group-conditional skewness diagnostic
    test2 = run_test2(close)

    # keep/drop + RS rule (decision on STANDALONE rank-IC)
    keep_drop = {}
    for col in singles:
        ic = _series_mean(col)
        icir = _series_icir(col)
        keep = bool(ic is not None and not math.isnan(ic)
                    and ic > cfg.KEEP_IC_MIN and icir >= cfg.KEEP_ICIR_MIN)
        keep_drop[col] = {"mean_ic": ic, "icir": icir, "keep": keep}
    rs_recos = {}
    for col in cfg.RS_LOOKBACKS_DAYS:
        ic = _series_mean(col)
        if ic is None or math.isnan(ic):
            reco = "insufficient_data"
        elif ic <= 0.0:
            reco = "DROP or convert to short-term REVERSAL (Bildik-Gulay contrarian)"
        else:
            reco = "KEEP (positive standalone IC)"
        rs_recos[col] = {"mean_ic": ic, "recommendation": reco}

    faz1_set = [c for c, v in keep_drop.items() if v["keep"]]
    results = {
        "directive": "D-177",
        "phase": "FAZ 0 -- Factor IC Validation (MEASUREMENT only; DEC-039)",
        "window": {"start": start, "end": end},
        "snapshot": {
            "content_hash": meta.get("content_hash"),
            "timestamp_utc": meta.get("timestamp_utc"),
            "loaded_universe_n": meta.get("loaded_universe_n"),
            "survivorship": meta.get("survivorship"),
        },
        "config_version": cfg.CONFIG_VERSION,
        "ic_metric": "Spearman rank-IC (NOT Pearson; keeps TEST 2 orthogonal)",
        "horizons": list(cfg.IC_HORIZONS),
        "per_factor_ic": per_factor,
        "test1_dilution": test1,
        "test2_groupcond_skew": test2,
        "keep_drop_decision": keep_drop,
        "rs_decision_rule": rs_recos,
        "faz1_recommended_factor_set": faz1_set,
        "decision_owner": "Orchestrator+Cagan (harness recommends only, DEC-039)",
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "faz0_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    _print_summary(results)
    return results


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


def _print_summary(r: dict) -> None:
    sep = "=" * 70
    print(f"\n{sep}\n  FAZ 0 -- Factor IC (MEASUREMENT; karar Orchestrator+Cagan)\n{sep}")
    print(f"  Window     : {r['window']['start']} -> {r['window']['end']}")
    sv = r["snapshot"]["survivorship"]
    print(f"  Universe   : {r['snapshot']['loaded_universe_n']} loaded; "
          f"excluded delisted: {sv.get('excluded_delisted')}")
    print(f"  IC metric  : {r['ic_metric']}")
    print(f"  {'-'*66}")
    print(f"  {'factor':<12}{'meanIC@21':>12}{'ICIR@21':>10}{'keep':>7}")
    for col, v in r["keep_drop_decision"].items():
        mic = v["mean_ic"]; icir = v["icir"]
        print(f"  {col:<12}{mic:>12.4f}{icir:>10.3f}{str(v['keep']):>7}")
    t1 = r["test1_dilution"]
    print(f"  {'-'*66}")
    print(f"  TEST1 dilution: composite={t1['composite_ic']:.4f} vs "
          f"best({t1['best_single_factor']})={t1['best_single_ic']:.4f} "
          f"-> dilution={t1['dilution_flag']}")
    t2 = r["test2_groupcond_skew"]
    if "delta_skew" in t2:
        print(f"  TEST2 (diag) : delta_skew={t2['delta_skew']:.4f} "
              f"CI95={t2['block_bootstrap_ci95']} (gating DEGIL)")
    print(f"  RS rule    : " + "; ".join(
        f"{k}:{v['recommendation'].split('(')[0].strip()}" for k, v in r["rs_decision_rule"].items()))
    print(f"  Faz1 set   : {r['faz1_recommended_factor_set']}")
    print(f"  SURVIVORSHIP BIAS: {sv.get('bias_direction')}")
    print(f"{sep}\n")


def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(description="Faz 0 Factor IC Validation Harness (D-177)")
    p.add_argument("--start", default=cfg.SNAPSHOT_START)
    p.add_argument("--end", default=cfg.SNAPSHOT_END)
    p.add_argument("--out-dir", default=str(_RESULTS_DIR))
    args = p.parse_args()
    run_faz0(start=args.start, end=args.end, out_dir=args.out_dir)


if __name__ == "__main__":
    _main()

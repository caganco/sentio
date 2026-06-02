"""D-203 KESIN-TEST engine -- 5-gate measurement on the D-202 clean universe. FAZ-1.

Re-measures three edge candidates (ADAY-A VALUE / ADAY-B EDGE-2 composite / ADAY-C
52wk-high) on the SAME corrected D-202 681-symbol clean universe with the SAME 5-gate
methodology, to resolve the demo-edge <-> demo_smart_money contradiction (the EDGE-6
"+12.9pp above EW" claim ran on the BROKEN D-200 universe -> invalid here).

MEASUREMENT-ONLY (optimization FORBIDDEN). Strangler: reuses k2_factor_tilt.to_real /
max_drawdown and factor_ic_harness.block_bootstrap_ci / newey_west_se READ-ONLY; does
NOT import signals.engine / MASTER_WEIGHTS / backtest.engine. Gate decision thresholds
come from thresholds.py (D203_* via d203_config); measurement geometry from d203_config.

The 5 gates (all must pass for GERCEK-EDGE), all on the honest EW_FULL-relative series
unless noted:
  1. selection-null : top-15 real return beats >=95th pctile of matched random baskets.
  2. newey-west     : HAC |t| >= 2.0 on the EW_FULL-relative per-period series.
  3. cross-regime   : EW_FULL-relative positive on BOTH sides of the PRIMARY 2022-01 split.
  4. liquidity      : within the LIQUID value_tl tercile, relative edge survives (>0).
  5. after-cost     : relative edge stays > 0 at 20bp AND 100bp per-turnover cost.

Verdict (frozen): SERAP if EW_FULL-relative<=0 OR long-short<0 OR liquidity collapse;
GERCEK-EDGE if 5 gates AND both regimes positive; REJIM-TILT if 4 gates pass but only
the post-2022 regime is positive.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import d203_config as cfg
from src.screening.factor_ic_harness import block_bootstrap_ci, newey_west_se
from src.screening.k2_factor_tilt import max_drawdown, to_real

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_SNAPSHOT_DIR = _REPO_ROOT / "data" / "snapshots"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_d203.json"


# ===========================================================================
# Data loading
# ===========================================================================
def load_d202_panel(root: Path | str = cfg.D203_CLEAN_UNIVERSE_ROOT) -> dict:
    """Load the frozen D-202 clean-universe panel + fundamentals + TUFE.

    Asserts the price + fundamentals content-hash prefixes match the frozen Stage-0
    values (reproducibility guard). Returns pivots used by the rest of the engine.
    """
    root = _REPO_ROOT / root if not Path(root).is_absolute() else Path(root)
    px = pd.read_parquet(root / cfg.D203_PRICE_PARQUET)
    px["date"] = pd.to_datetime(px["date"])
    meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    if not str(meta.get("content_hash_prices", "")).startswith(cfg.D203_PRICE_CONTENT_HASH):
        raise RuntimeError(
            f"D-202 price content-hash mismatch: meta={meta.get('content_hash_prices','')[:16]} "
            f"expected={cfg.D203_PRICE_CONTENT_HASH} (frozen snapshot drift)")

    close = px.pivot(index="date", columns="symbol", values="adjusted_close").sort_index()
    value_tl = px.pivot(index="date", columns="symbol", values="value_tl").sort_index()
    bist100 = px.pivot(index="date", columns="symbol", values="bist100").sort_index()

    funds = pd.read_parquet(root / cfg.D203_FUND_PARQUET)
    fmeta = json.loads((root / "_meta_fundamentals.json").read_text(encoding="utf-8"))
    if not str(fmeta.get("content_hash_fundamentals", "")).startswith(cfg.D203_FUND_CONTENT_HASH):
        raise RuntimeError(
            f"D-203 fundamentals content-hash mismatch: meta="
            f"{fmeta.get('content_hash_fundamentals','')[:16]} expected={cfg.D203_FUND_CONTENT_HASH}")

    cpi = _load_tufe()
    return {"close": close, "value_tl": value_tl, "bist100": bist100,
            "funds": funds, "cpi": cpi, "price_meta": meta, "fund_meta": fmeta}


def _load_tufe() -> pd.Series | None:
    fp = _SNAPSHOT_DIR / f"{cfg.D203_TUFE_SNAPSHOT}.parquet"
    if not fp.exists():
        return None
    t = pd.read_parquet(fp)
    s = pd.Series(t["value"].values, index=pd.to_datetime(t["date"]), dtype=float).sort_index()
    return s


# ===========================================================================
# Calendar + return cleaning
# ===========================================================================
def monthly_rebalance_dates(
    index: pd.DatetimeIndex, start: str, end: str,
) -> list[pd.Timestamp]:
    """Last trading day of each calendar month within [start, end], sorted/unique."""
    idx = pd.DatetimeIndex(sorted(index))
    idx = idx[(idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))]
    if len(idx) == 0:
        return []
    df = pd.DataFrame({"d": idx}, index=idx)
    last = df.groupby([idx.year, idx.month])["d"].max()
    return sorted(pd.DatetimeIndex(last.values))


def clip_clean_returns(close: pd.DataFrame, cap: float = cfg.D203_DAILY_RETURN_CLIP) -> pd.DataFrame:
    """Daily simple returns from adjusted close, clipped to +/- cap (honest +/-10%,
    NOT the broken D-200 +/-50%). NaN where price absent (delisting handled naturally)."""
    rets = close.sort_index().pct_change(fill_method=None)
    return rets.clip(lower=-cap, upper=cap)


def _period_return_matrix(daily: pd.DataFrame, rebal: list[pd.Timestamp]) -> pd.DataFrame:
    """P[i, symbol] = buy-and-hold compounded clipped daily return over (rebal[i], rebal[i+1]].

    Delisted-inclusive: a name that goes NaN mid-period contributes its partial
    compounded return up to delisting (min_count=1 -> NaN only if no day at all)."""
    rows = []
    for i in range(len(rebal) - 1):
        d0, d1 = rebal[i], rebal[i + 1]
        win = daily.loc[(daily.index > d0) & (daily.index <= d1)]
        comp = (1.0 + win).prod(min_count=1) - 1.0
        rows.append(comp)
    return pd.DataFrame(rows, index=pd.DatetimeIndex([rebal[i] for i in range(len(rebal) - 1)]))


# ===========================================================================
# Benchmarks (honest bar)
# ===========================================================================
def ew_full_benchmark(pmat: pd.DataFrame) -> list[float]:
    """Equal-weight per-period return of the ENTIRE eligible universe (delisted-inclusive).

    This is the honest bar: every name with any data in the period contributes."""
    return [float(np.nanmean(pmat.iloc[i].values)) if np.isfinite(pmat.iloc[i].values).any()
            else float("nan") for i in range(len(pmat))]


def _constituent_ew(pmat: pd.DataFrame, flag: pd.DataFrame, rebal: list[pd.Timestamp]) -> list[float]:
    """EW per-period return of the index-constituent (bist100-flagged) names -- XU100 proxy."""
    out = []
    for i in range(len(pmat)):
        d = rebal[i]
        names = flag.loc[d][flag.loc[d] == 1].index if d in flag.index else []
        names = [c for c in names if c in pmat.columns]
        vals = pmat.iloc[i][names].values if names else np.array([])
        out.append(float(np.nanmean(vals)) if len(vals) and np.isfinite(vals).any() else float("nan"))
    return out


# ===========================================================================
# Liquidity terciles
# ===========================================================================
def liquidity_tercile_pools(
    value_tl: pd.DataFrame, rebal: list[pd.Timestamp],
    trailing_days: int = cfg.D203_LIQUIDITY_TRAILING_DAYS,
) -> dict[pd.Timestamp, dict[str, list[str]]]:
    """Per rebalance date: split eligible names into liquid/mid/illiquid terciles by
    trailing-median value_tl. Disjoint; their union is the full eligible pool."""
    vt = value_tl.sort_index()
    out: dict[pd.Timestamp, dict[str, list[str]]] = {}
    q = cfg.D203_LIQUIDITY_TERCILE
    for d in rebal:
        win = vt.loc[vt.index <= d].tail(trailing_days)
        med = win.median(skipna=True).dropna()
        med = med[med > 0]
        if med.empty:
            out[d] = {"liquid": [], "mid": [], "illiquid": []}
            continue
        lo_cut = med.quantile(q)
        hi_cut = med.quantile(1.0 - q)
        illiquid = sorted(med[med <= lo_cut].index)
        liquid = sorted(med[med >= hi_cut].index)
        mid = sorted(set(med.index) - set(illiquid) - set(liquid))
        out[d] = {"liquid": liquid, "mid": mid, "illiquid": illiquid}
    return out


# ===========================================================================
# Factor score panels (higher score = preferred long)
# ===========================================================================
def _xs_rank(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-row cross-sectional rank in [0,1] (higher value -> higher rank)."""
    return panel.rank(axis=1, pct=True)


def momentum_panel(close: pd.DataFrame, rebal: list[pd.Timestamp]) -> pd.DataFrame:
    """120d momentum skipping the most recent ~21d (close[d-skip]/close[d-lookback]-1)."""
    idx = close.index
    rows, dates = [], []
    for d in rebal:
        pos = idx.searchsorted(d, side="right") - 1
        if pos - cfg.D203_MOM_LOOKBACK < 0:
            continue
        p_recent = close.iloc[pos - cfg.D203_MOM_SKIP]
        p_old = close.iloc[pos - cfg.D203_MOM_LOOKBACK]
        rows.append(p_recent / p_old - 1.0)
        dates.append(d)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def hi52_panel(close: pd.DataFrame, rebal: list[pd.Timestamp]) -> pd.DataFrame:
    """52wk-high proximity = close[d] / rolling-252d-max (in (0,1], higher = nearer high)."""
    idx = close.index
    rows, dates = [], []
    for d in rebal:
        pos = idx.searchsorted(d, side="right") - 1
        if pos < 0:
            continue
        lo = max(0, pos - cfg.D203_HI52_LOOKBACK + 1)
        window = close.iloc[lo:pos + 1]
        roll_max = window.max(skipna=True)
        cur = close.iloc[pos]
        prox = cur / roll_max.replace(0, np.nan)
        rows.append(prox)
        dates.append(d)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def lowvol_panel(daily: pd.DataFrame, rebal: list[pd.Timestamp]) -> pd.DataFrame:
    """Inverted 63d realized vol (score = -std of daily returns -> low vol = high score)."""
    idx = daily.index
    rows, dates = [], []
    for d in rebal:
        pos = idx.searchsorted(d, side="right") - 1
        if pos - cfg.D203_LOWVOL_WINDOW < 0:
            continue
        window = daily.iloc[pos - cfg.D203_LOWVOL_WINDOW + 1:pos + 1]
        vol = window.std(skipna=True)
        rows.append(-vol)
        dates.append(d)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def value_factor_panel(
    funds: pd.DataFrame, rebal: list[pd.Timestamp], kind: str = cfg.D203_VALUE_PRIMARY,
    lag_months: int = cfg.D203_FUND_PUBLICATION_LAG_MONTHS,
) -> pd.DataFrame:
    """Value score (bm or ey) at each rebalance, using the latest fundamentals month
    <= (rebalance month - lag_months) -> look-ahead safe. Higher = cheaper = long."""
    f = funds.copy()
    f["month"] = f["month"].astype("period[M]")
    piv = f.pivot_table(index="month", columns="symbol", values=kind, aggfunc="last")
    piv = piv.sort_index()
    rows, dates = [], []
    for d in rebal:
        cutoff = pd.Period(pd.Timestamp(d), freq="M") - lag_months
        avail = piv.loc[piv.index <= cutoff]
        if avail.empty:
            continue
        rows.append(avail.ffill().iloc[-1])
        dates.append(d)
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def composite_edge2_panel(
    close: pd.DataFrame, daily: pd.DataFrame, rebal: list[pd.Timestamp],
) -> pd.DataFrame:
    """ADAY-B EDGE-2: EQUAL-WEIGHT average of the mom120 / hi52 / lowvol63 cross-sectional
    ranks. A name needs all three present (require-all) to get a composite score."""
    mom_r = _xs_rank(momentum_panel(close, rebal))
    hi_r = _xs_rank(hi52_panel(close, rebal))
    lv_r = _xs_rank(lowvol_panel(daily, rebal))
    common = mom_r.index.intersection(hi_r.index).intersection(lv_r.index)
    mom_r, hi_r, lv_r = mom_r.loc[common], hi_r.loc[common], lv_r.loc[common]
    cols = mom_r.columns.union(hi_r.columns).union(lv_r.columns)
    mom_r = mom_r.reindex(columns=cols)
    hi_r = hi_r.reindex(columns=cols)
    lv_r = lv_r.reindex(columns=cols)
    stacked = np.stack([mom_r.values, hi_r.values, lv_r.values])
    if cfg.D203_REQUIRE_ALL_FACTORS:
        present = np.isfinite(stacked).all(axis=0)
        comp = np.where(present, stacked.sum(axis=0) / stacked.shape[0], np.nan)
    else:
        with np.errstate(invalid="ignore"):
            comp = np.nanmean(stacked, axis=0)
    return pd.DataFrame(comp, index=common, columns=cols)


def score_panel_for(candidate: str, data: dict, rebal: list[pd.Timestamp],
                    value_kind: str | None = None) -> pd.DataFrame:
    """Dispatch: return the higher-is-long score panel for a candidate."""
    close, daily, funds = data["close"], data["daily"], data["funds"]
    if candidate == "value":
        return _xs_rank(value_factor_panel(funds, rebal, value_kind or cfg.D203_VALUE_PRIMARY))
    if candidate == "edge2":
        return composite_edge2_panel(close, daily, rebal)
    if candidate == "hi52":
        return _xs_rank(hi52_panel(close, rebal))
    raise ValueError(f"unknown candidate {candidate}")


# ===========================================================================
# Selection
# ===========================================================================
def select_top_n(date: pd.Timestamp, comp: pd.DataFrame, n: int = cfg.D203_TOP_N,
                 pool: list[str] | None = None) -> list[str]:
    """Top-n names by score at `date` (within `pool` if given). EW basket = min(n, pool)."""
    if date not in comp.index:
        return []
    row = comp.loc[date].dropna()
    if pool is not None:
        row = row[row.index.intersection(pool)]
    if row.empty:
        return []
    return sorted(row.sort_values(ascending=False).head(n).index)


def select_bottom_n(date: pd.Timestamp, comp: pd.DataFrame, n: int = cfg.D203_TOP_N,
                    pool: list[str] | None = None) -> list[str]:
    """Bottom-n names by score (the short leg of the long-short spread)."""
    if date not in comp.index:
        return []
    row = comp.loc[date].dropna()
    if pool is not None:
        row = row[row.index.intersection(pool)]
    if row.empty:
        return []
    return sorted(row.sort_values(ascending=True).head(n).index)


# ===========================================================================
# Portfolio period returns + flat-bps cost
# ===========================================================================
def _basket_period(pmat: pd.DataFrame, i: int, basket: list[str]) -> float:
    if not basket:
        return float("nan")
    vals = pmat.iloc[i][[c for c in basket if c in pmat.columns]].values
    vals = vals[np.isfinite(vals)]
    return float(np.mean(vals)) if len(vals) else float("nan")


def _turnover(prev: list[str], cur: list[str]) -> float:
    if not cur:
        return 0.0
    if not prev:
        return 1.0
    wp = {t: 1.0 / len(prev) for t in prev}
    wc = {t: 1.0 / len(cur) for t in cur}
    names = set(wp) | set(wc)
    return 0.5 * sum(abs(wc.get(n, 0.0) - wp.get(n, 0.0)) for n in names)


def _tax_drag(d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    days = max(0, (pd.Timestamp(d1) - pd.Timestamp(d0)).days)
    return cfg.D203_DIV_WITHHOLDING * cfg.D203_ASSUMED_ANNUAL_DIV_YIELD * (days / 365.0)


def _cpi_ratio(cpi: pd.Series, d0: pd.Timestamp, d1: pd.Timestamp) -> float:
    """cpi(d1)/cpi(d0) via as-of lookup (matches k2.to_real inflation deflator)."""
    if cpi is None or len(cpi) == 0:
        return float("nan")
    a, b = cpi.asof(d0), cpi.asof(d1)
    if not (np.isfinite(a) and np.isfinite(b)) or a <= 0:
        return float("nan")
    return float(b / a)


def basket_net_series(
    pmat: pd.DataFrame, baskets: list[list[str]], rebal: list[pd.Timestamp],
    cost_bps: float = 0.0,
) -> dict:
    """Per-period gross/net/turnover for an EW basket sequence with FLAT per-turnover cost.

    net_i = gross_i - turnover_i * (cost_bps/1e4) - tax_drag_i. cost_bps is the flat
    round-trip cost in bps applied to one-way turnover (gate-5 uses 20 and 100)."""
    cost_frac = cost_bps / 10_000.0
    gross, net, turns = [], [], []
    prev: list[str] = []
    for i in range(len(baskets)):
        g = _basket_period(pmat, i, baskets[i])
        tau = _turnover(prev, baskets[i])
        tax = _tax_drag(rebal[i], rebal[i + 1])
        gross.append(g)
        turns.append(tau)
        net.append(g - tau * cost_frac - tax if np.isfinite(g) else float("nan"))
        prev = baskets[i]
    return {"gross": gross, "net": net, "turnover": turns}


def _relative(long_net: list[float], bench: list[float]) -> list[float]:
    """Geometric per-period excess of the long portfolio over a benchmark series."""
    out = []
    for r, b in zip(long_net, bench):
        if not (np.isfinite(r) and np.isfinite(b)):
            out.append(float("nan"))
            continue
        out.append((1.0 + r) / (1.0 + b) - 1.0)
    return out


def _mean_ci(series: list[float]) -> dict:
    arr = np.array([v for v in series if np.isfinite(v)], dtype=float)
    if len(arr) < 2:
        return {"n": int(len(arr)), "mean": None, "ci95_low": None,
                "ci95_high": None, "ci_excludes_zero": False}
    lo, hi = block_bootstrap_ci(arr, block=cfg.D203_SIG_BLOCK,
                                n_boot=cfg.D203_SIG_N_BOOT, seed=cfg.D203_SIG_SEED)
    return {"n": int(len(arr)), "mean": _r(float(np.mean(arr))),
            "ci95_low": _r(lo), "ci95_high": _r(hi),
            "ci_excludes_zero": bool(lo > 0 or hi < 0)}


def _nw_t(series: list[float]) -> float:
    arr = np.array([v for v in series if np.isfinite(v)], dtype=float)
    if len(arr) < cfg.D203_NW_LAGS + 2:
        return float("nan")
    se = newey_west_se(arr, lags=cfg.D203_NW_LAGS)
    if not np.isfinite(se) or se <= 0:
        return float("nan")
    return float(np.mean(arr) / se)


def _r(x) -> float | None:
    try:
        return round(float(x), 6) if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


# ===========================================================================
# Fair selection null (top-N random baskets from the same pool, real terms)
# ===========================================================================
def fair_selection_null(
    pmat: pd.DataFrame, pools: list[list[str]], rebal: list[pd.Timestamp],
    cpi: pd.Series | None, strategy_real_mean: float, basket_size: int = cfg.D203_TOP_N,
    seed: int = cfg.D203_NULL_SEED, n_resamples: int = cfg.D203_NULL_N_RESAMPLES,
) -> dict:
    """Null: draw `basket_size` names uniformly (no replacement) from the SAME pool each
    period, same dates/cost(0)/tax -> isolates SELECTION skill. pctile = P(null < strat)."""
    bad = {"n_resamples": 0, "random_pctile": None, "beats_fair_null": False,
           "null_p95": None, "strategy_real_mean": _r(strategy_real_mean)}
    if cpi is None or not np.isfinite(strategy_real_mean):
        return bad
    n = len(rebal) - 1
    active = [i for i in range(n) if len(pools[i]) >= basket_size]
    if not active:
        return bad
    # Precompute per-period inflation ratio + tax drag (cost_bps=0 in the null).
    col_pos = {c: j for j, c in enumerate(pmat.columns)}
    M = pmat.values.astype(float)
    rng = np.random.default_rng(seed)
    # Accumulate per-resample mean of real returns over active periods (vectorized
    # per period: draw n_resamples x basket_size indices without replacement).
    real_sum = np.zeros(n_resamples, dtype=float)
    real_cnt = np.zeros(n_resamples, dtype=int)
    for i in active:
        pool_idx = np.array([col_pos[c] for c in pools[i] if c in col_pos])
        if len(pool_idx) < basket_size:
            continue
        sub = M[i, pool_idx]                                   # (pool,)
        rand = rng.random((n_resamples, len(pool_idx)))        # pick k smallest -> uniform subset
        pick = np.argpartition(rand, basket_size - 1, axis=1)[:, :basket_size]
        gathered = sub[pick]                                   # (n_resamples, k)
        gross = np.nanmean(gathered, axis=1)                   # (n_resamples,)
        infl = _cpi_ratio(cpi, rebal[i], rebal[i + 1])
        tax = _tax_drag(rebal[i], rebal[i + 1])
        if not np.isfinite(infl) or infl <= 0:
            continue
        real_p = (1.0 + gross - tax) / infl - 1.0
        ok = np.isfinite(real_p)
        real_sum[ok] += real_p[ok]
        real_cnt[ok] += 1
    means = np.where(real_cnt > 0, real_sum / np.maximum(real_cnt, 1), np.nan)
    finite = means[np.isfinite(means)]
    if len(finite) == 0:
        return bad
    pctile = float(np.mean(finite < strategy_real_mean))
    return {"n_resamples": int(len(finite)),
            "random_pctile": round(pctile, 4),
            "beats_fair_null": bool(pctile >= cfg.D203_GATE_NULL_PCTILE),
            "null_p95": _r(float(np.percentile(finite, 95))),
            "strategy_real_mean": _r(strategy_real_mean)}


# ===========================================================================
# Regime split
# ===========================================================================
def regime_split(series: list[float], rebal: list[pd.Timestamp], split: str) -> dict:
    """Split per-period series at `split` by each period's START date; mean each side."""
    cut = pd.Timestamp(split)
    pre = [series[i] for i in range(len(series)) if rebal[i] < cut and np.isfinite(series[i])]
    post = [series[i] for i in range(len(series)) if rebal[i] >= cut and np.isfinite(series[i])]
    pre_m = float(np.mean(pre)) if pre else float("nan")
    post_m = float(np.mean(post)) if post else float("nan")
    return {"split": split, "pre_mean": _r(pre_m), "post_mean": _r(post_m),
            "pre_n": len(pre), "post_n": len(post),
            "both_positive": bool(pre_m > 0 and post_m > 0),
            "only_post_positive": bool(post_m > 0 and not (pre_m > 0))}


# ===========================================================================
# Gates + verdict
# ===========================================================================
def run_gates(candidate: str, data: dict, rebal: list[pd.Timestamp],
              value_kind: str | None = None) -> dict:
    """Run all 5 gates for one candidate on one window. Returns the full gate dict."""
    pmat, cpi = data["pmat"], data["cpi"]
    comp = score_panel_for(candidate, data, rebal, value_kind)
    liq = data["liquidity"]

    # full-pool long + bottom baskets
    long_baskets, short_baskets, pools = [], [], []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        pool = sorted(comp.loc[d].dropna().index) if d in comp.index else []
        pools.append(pool)
        long_baskets.append(select_top_n(d, comp, cfg.D203_TOP_N))
        short_baskets.append(select_bottom_n(d, comp, cfg.D203_TOP_N))

    long_net = basket_net_series(pmat, long_baskets, rebal, cost_bps=0.0)["net"]
    short_net = basket_net_series(pmat, short_baskets, rebal, cost_bps=0.0)["net"]
    ew_full = data["ew_full"]
    rel_ew = _relative(long_net, ew_full)
    ls = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
          for a, b in zip(long_net, short_net)]

    long_real = to_real(long_net, rebal, cpi)
    long_real_mean = np.nanmean([v for v in long_real if np.isfinite(v)]) if any(
        np.isfinite(v) for v in long_real) else float("nan")
    rel_ci = _mean_ci(rel_ew)
    ls_ci = _mean_ci(ls)
    long_real_ci = _mean_ci(long_real)

    # GATE 1 -- selection null (real terms, top-15 vs random top-15 from same pool)
    null = fair_selection_null(pmat, pools, rebal, cpi, long_real_mean)
    g1 = bool(null.get("beats_fair_null"))

    # GATE 2 -- Newey-West HAC |t| on EW_FULL-relative
    nw_t = _nw_t(rel_ew)
    g2 = bool(np.isfinite(nw_t) and abs(nw_t) >= cfg.D203_GATE_NW_T_MIN)

    # GATE 3 -- cross-regime (PRIMARY split decides; SECONDARY reported)
    reg_primary = regime_split(rel_ew, rebal, cfg.D203_REGIME_PRIMARY)
    reg_secondary = regime_split(rel_ew, rebal, cfg.D203_REGIME_SECONDARY)
    g3 = reg_primary["both_positive"]

    # GATE 4 -- liquidity-tercile survival (LIQUID tercile relative edge > 0)
    liq_long = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        lpool = liq.get(d, {}).get("liquid", [])
        liq_long.append(select_top_n(d, comp, cfg.D203_TOP_N, pool=lpool))
    liq_net = basket_net_series(pmat, liq_long, rebal, cost_bps=0.0)["net"]
    liq_rel = _relative(liq_net, ew_full)
    liq_rel_mean = np.nanmean([v for v in liq_rel if np.isfinite(v)]) if any(
        np.isfinite(v) for v in liq_rel) else float("nan")
    g4 = bool(np.isfinite(liq_rel_mean) and liq_rel_mean > 0)

    # illiquid tercile (for liquidity-collapse / mirage detection)
    illq_long = []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        ipool = liq.get(d, {}).get("illiquid", [])
        illq_long.append(select_top_n(d, comp, cfg.D203_TOP_N, pool=ipool))
    illq_net = basket_net_series(pmat, illq_long, rebal, cost_bps=0.0)["net"]
    illq_rel = _relative(illq_net, ew_full)
    illq_rel_mean = np.nanmean([v for v in illq_rel if np.isfinite(v)]) if any(
        np.isfinite(v) for v in illq_rel) else float("nan")
    liquidity_collapse = bool(illq_rel_mean > 0 and not (liq_rel_mean > 0))

    # GATE 5 -- after-cost (relative edge stays > 0 at 20bp AND 100bp)
    cost_legs = {}
    g5_low = g5_high = False
    for tag, bps in (("low_20bp", cfg.D203_GATE_COST_LOW_BPS),
                     ("high_100bp", cfg.D203_GATE_COST_HIGH_BPS)):
        net_c = basket_net_series(pmat, long_baskets, rebal, cost_bps=bps)["net"]
        rel_c = _relative(net_c, ew_full)
        m = np.nanmean([v for v in rel_c if np.isfinite(v)]) if any(
            np.isfinite(v) for v in rel_c) else float("nan")
        cost_legs[tag] = {"bps": bps, "rel_ew_mean": _r(m), "positive": bool(m > 0)}
        if tag == "low_20bp":
            g5_low = bool(m > 0)
        else:
            g5_high = bool(m > 0)
    g5 = bool(g5_low and g5_high)

    eq = _equity_curve(pmat, long_baskets)
    return {
        "candidate": candidate,
        "value_kind": value_kind,
        "n_periods": len(long_net),
        "long_real": long_real_ci,
        "ew_full_relative": rel_ci,
        "long_short": ls_ci,
        "max_drawdown": _r(max_drawdown(eq)) if len(eq) > 1 else None,
        "gate1_selection_null": {"pass": g1, **null},
        "gate2_newey_west": {"pass": g2, "hac_t": _r(nw_t), "t_min": cfg.D203_GATE_NW_T_MIN},
        "gate3_cross_regime": {"pass": g3, "primary": reg_primary, "secondary": reg_secondary},
        "gate4_liquidity": {"pass": g4, "liquid_rel_mean": _r(liq_rel_mean),
                            "illiquid_rel_mean": _r(illq_rel_mean),
                            "liquidity_collapse": liquidity_collapse},
        "gate5_after_cost": {"pass": g5, **cost_legs},
        "_internal": {"rel_ew_mean": _r(rel_ci.get("mean")), "ls_mean": _r(ls_ci.get("mean")),
                      "liquidity_collapse": liquidity_collapse,
                      "only_post_positive": reg_primary["only_post_positive"],
                      "gates": [g1, g2, g3, g4, g5]},
    }


def _equity_curve(pmat: pd.DataFrame, baskets: list[list[str]]) -> pd.Series:
    eq, vals, idx = 1.0, [1.0], [0]
    for i in range(len(baskets)):
        r = _basket_period(pmat, i, baskets[i])
        eq *= (1.0 + (r if np.isfinite(r) else 0.0))
        vals.append(eq)
        idx.append(i + 1)
    return pd.Series(vals, index=idx)


def d203_verdict(gate_block: dict) -> dict:
    """Frozen 3-way decision rule. SERAP > GERCEK-EDGE > REJIM-TILT precedence."""
    internal = gate_block["_internal"]
    g1, g2, g3, g4, g5 = internal["gates"]
    rel_mean = internal["rel_ew_mean"]
    ls_mean = internal["ls_mean"]
    collapse = internal["liquidity_collapse"]
    only_post = internal["only_post_positive"]

    rel_nonpos = rel_mean is None or rel_mean <= 0
    ls_neg = ls_mean is not None and ls_mean < 0
    if rel_nonpos or ls_neg or collapse:
        reasons = []
        if rel_nonpos:
            reasons.append("ew_full_relative<=0")
        if ls_neg:
            reasons.append("long_short_negative")
        if collapse:
            reasons.append("liquidity_collapse_edge_only_in_illiquid")
        return {"verdict": "SERAP", "reasons": reasons}

    if g1 and g2 and g3 and g4 and g5:
        return {"verdict": "GERCEK-EDGE", "reasons": ["all_5_gates_pass_both_regimes_positive"]}

    other4 = g1 and g2 and g4 and g5
    if other4 and only_post:
        return {"verdict": "REJIM-TILT",
                "reasons": ["gates_1_2_4_5_pass_but_only_post_2022_regime_positive"]}

    failed = [f"gate{i+1}" for i, g in enumerate(internal["gates"]) if not g]
    return {"verdict": "SERAP", "reasons": ["gates_failed:" + ",".join(failed)]}


# ===========================================================================
# Orchestrator
# ===========================================================================
def _prepare_window(data: dict, start: str, end: str) -> dict:
    close = data["close"]
    rebal = monthly_rebalance_dates(close.index, start, end)
    daily = clip_clean_returns(close)
    pmat = _period_return_matrix(daily, rebal)
    ew_full = ew_full_benchmark(pmat)
    bist100_ew = _constituent_ew(pmat, data["bist100"], rebal)
    liquidity = liquidity_tercile_pools(data["value_tl"], rebal)
    return {**data, "daily": daily, "rebal": rebal, "pmat": pmat,
            "ew_full": ew_full, "bist100_ew": bist100_ew, "liquidity": liquidity}


def run_d203(
    root: Path | str = cfg.D203_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
    null_resamples: int | None = None,
) -> dict:
    """Full D-203 measurement: 3 candidates x their windows -> 5 gates + verdict each.

    REFUSES to run unless the Stage-0 pre-registration JSON exists (pre-registration
    discipline: gates are frozen BEFORE results are computed)."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; D-203 gates must be "
            "frozen BEFORE results (pre-registration discipline).")
    if null_resamples is not None:
        cfg.D203_NULL_N_RESAMPLES = null_resamples  # test-only fast path

    data = load_d202_panel(root)
    windows = {
        "common": (cfg.D203_COMMON_WINDOW_START, cfg.D203_COMMON_WINDOW_END),
        "extended": (cfg.D203_EXTENDED_WINDOW_START, cfg.D203_EXTENDED_WINDOW_END),
    }
    prepared = {w: _prepare_window(data, *windows[w]) for w in windows}

    results: dict = {}
    for cand in cfg.D203_CANDIDATES:
        results[cand] = {"label": cfg.D203_CANDIDATE_LABELS[cand], "windows": {}}
        for win in cfg.D203_CANDIDATE_WINDOWS[cand]:
            pdata = prepared[win]
            gate_block = run_gates(cand, pdata, pdata["rebal"])
            verdict = d203_verdict(gate_block)
            block = {k: v for k, v in gate_block.items() if k != "_internal"}
            block["verdict"] = verdict
            block["window"] = {"name": win, "start": windows[win][0], "end": windows[win][1]}
            results[cand]["windows"][win] = block
            # ADAY-A robustness leg: E/P value variant on the common window
            if cand == "value" and win == "common":
                rob = run_gates("value", pdata, pdata["rebal"], value_kind=cfg.D203_VALUE_ROBUST)
                rob_v = d203_verdict(rob)
                rob_block = {k: v for k, v in rob.items() if k != "_internal"}
                rob_block["verdict"] = rob_v
                results[cand]["robustness_ep"] = rob_block

    out = {
        "directive": "D-203",
        "phase": "FAZ-1 5-gate clean-universe measurement",
        "config_version": cfg.D203_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.D203_PRICE_CONTENT_HASH,
        "fund_content_hash": cfg.D203_FUND_CONTENT_HASH,
        "regime_splits": list(cfg.D203_REGIME_SPLITS),
        "regime_primary": cfg.D203_REGIME_PRIMARY,
        "windows": windows,
        "benchmark": "EW_FULL (delisted-inclusive equal-weight of full eligible universe)",
        "results": results,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
        logger.info("[d203] results written: %s", out_path)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = run_d203(out_path=_RESULTS_DIR / "d203_results.json")
    for cand, blk in res["results"].items():
        for win, wb in blk["windows"].items():
            print(f"[d203] {cand:6s} {win:8s} -> {wb['verdict']['verdict']}")

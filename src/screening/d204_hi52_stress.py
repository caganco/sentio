"""D-204 hi52 stress test engine -- realistic-cost + vade + OOS + mechanism + H1.

D-203 found ADAY-C hi52 = GERCEK-EDGE (strongest). D-204 stress-tests deploy-readiness
WITHOUT re-running the data: it REUSES the D-203 engine (price/rebalance/return/liquidity/
hi52/select/null/regime/NW/CI) READ-ONLY and the SAME frozen D-202 panel (same content
hash), and layers five stresses on top (Strangler -- D-203 engine NOT modified):

  STRES-1  realistic per-stock cost (Roll 1984 + Kyle 1985 + RR-015 tier floor) + the
           model-independent BREAKEVEN bps (the main verdict). EKLEME-A: report the
           share of names where Roll=0 (tier-floor engaged).
  STRES-2  holding period + 1/2/3-month cadence (turnover -> cost) views.
  STRES-3  walk-forward (2019-22 / 2023-26) + disinflation 2024-26 weak proxy. The OOS
           GAP (real inflation-normalization OOS is ABSENT) is stated in EVERY verdict.
  STRES-4  mechanism: hi52-vs-mom120 factor overlap + bist100/mktval concentration.
  EKLEME-3 (H1) liquidity paradox: liquid/mid/illiquid hi52 edge pre- AND post-cost --
           does the illiquid > liquid ordering (RR-043's opposite) survive realistic cost?

MEASUREMENT-ONLY (optimization FORBIDDEN). Cadences + breakeven grid are reporting VIEWS,
not selected. lambda_kyle FROZEN. EKLEME-B: the DEPLOY hurdle is the real TLREF deposit
carry, RECOMPUTED from frozen snapshots and asserted == the frozen thresholds value.
Refuses to run unless STAGE0_d204.json exists (pre-registration discipline).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import d203_clean_universe_test as eng
from src.screening import d204_config as cfg
from src.screening import realistic_cost as rc

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_SNAPSHOT_DIR = _REPO_ROOT / "data" / "snapshots"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_d204.json"
_MICRO_RT = 2.0 * cfg._th.D207_TIER_MICRO_HALF_SPREAD  # conservative cost fallback (round-trip, D-207)


# ===========================================================================
# TLREF deposit hurdle (EKLEME-B) -- derived + reproducibility-asserted
# ===========================================================================
def _load_tlref(snapshot: str = cfg.D204_TLREF_SNAPSHOT) -> pd.Series | None:
    fp = _SNAPSHOT_DIR / f"{snapshot}.parquet"
    if not fp.exists():
        return None
    t = pd.read_parquet(fp)
    return pd.Series(t["value"].values, index=pd.to_datetime(t["date"]), dtype=float).sort_index()


def deploy_threshold_from_tlref(
    tlref: pd.Series | None, cpi: pd.Series | None, rebal: list[pd.Timestamp],
) -> dict:
    """Mean monthly REAL TLREF carry over the rebalance pairs where TLREF+TUFE are both
    available -- the deposit/repo real return the strategy must beat (EKLEME-B). TLREF
    return-index begins 2022-07, so coverage is the 2022-07+ subperiod (reported)."""
    if tlref is None or cpi is None:
        return {"mean_monthly_real_carry": None, "n_periods": 0, "coverage_start": None}
    carries, starts = [], []
    for i in range(len(rebal) - 1):
        d0, d1 = rebal[i], rebal[i + 1]
        t0, t1 = tlref.asof(d0), tlref.asof(d1)
        infl = eng._cpi_ratio(cpi, d0, d1)
        if not (np.isfinite(t0) and np.isfinite(t1) and t0 > 0 and np.isfinite(infl) and infl > 0):
            continue
        carries.append((t1 / t0) / infl - 1.0)
        starts.append(d0)
    if not carries:
        return {"mean_monthly_real_carry": None, "n_periods": 0, "coverage_start": None}
    return {"mean_monthly_real_carry": eng._r(float(np.mean(carries))),
            "n_periods": len(carries),
            "coverage_start": str(min(starts).date())}


# ===========================================================================
# Cadence (STRES-2) -- 1/2/3-month rebalance VIEWS
# ===========================================================================
def multi_cadence_rebalance_dates(
    index: pd.DatetimeIndex, start: str, end: str, months: int,
) -> list[pd.Timestamp]:
    """Month-end rebalance dates at a `months`-month cadence (1 -> D-203 monthly baseline).

    Subsamples the monthly last-trading-day calendar every `months`-th month -> sorted,
    unique. months=2 yields ~half as many dates as months=1 (turnover lower -> cost lower)."""
    monthly = eng.monthly_rebalance_dates(index, start, end)
    if months <= 1:
        return monthly
    return monthly[::months]


# ===========================================================================
# Per-stock realistic cost panel (STRES-1) + EKLEME-A roll-zero accounting
# ===========================================================================
def per_stock_cost_panel(
    close: pd.DataFrame, value_tl: pd.DataFrame, rebal: list[pd.Timestamp],
    order_value: float = cfg.D204_ORDER_VALUE_TL, window: int = cfg.D204_ROLL_WINDOW,
    adv_window: int = cfg.D204_ADV_WINDOW, lambda_kyle: float = cfg.D204_LAMBDA_KYLE,
    quoted_panel: pd.DataFrame | None = None,
    fallback_roll_window: int = cfg._th.D207_FALLBACK_ROLL_WINDOW,
) -> dict:
    """Per rebalance date x eligible name -> realistic round-trip cost (D-207 source
    hierarchy: EOD quoted -> long-window Roll fallback -> tier floor). Precomputes
    Roll/ADV/sigma (+ optional quoted) panels ONCE (vectorized) then combines per name.

    D-207 FIX-2: the SPREAD leg prefers the injected EOD `quoted_panel` (vol-robust,
    observed). Where a name has no quote in the trailing window the cell is NaN and we
    fall back to a LONG-window Roll (`fallback_roll_window`, de-inflated vs the 21d
    vol-meter); if Roll is also undefined the re-scaled tier floor fires. The Kyle impact
    sigma still uses the SHORT `window` (Kyle is frozen, out of D-207 scope).

    quoted_panel is INJECTED (CI-safe): engines build it locally from the archive
    (src.screening.quoted_spread); tests pass a synthetic panel or None. quoted_panel=None
    reproduces the quote-free path (Roll fallback -> tier).

    EKLEME-A (kept): n_roll_zero / roll_zero_frac now count cells that fell ALL the way to
    the tier floor (spread_source=="tier"). D-207 ADDS spread_source_counts / _frac, the
    full quoted/roll/tier breakdown. Returns {cost_roll, cost_tier, roll_zero, summary}.
    """
    roll_panel = rc.roll_spread_panel(close, fallback_roll_window)
    adv_panel = value_tl.astype(float).rolling(adv_window, min_periods=1).mean()
    log_ret = np.log(close.astype(float) / close.astype(float).shift(1))
    sigma_panel = log_ret.rolling(window).std()
    q_panel = quoted_panel.reindex(close.index).ffill() if quoted_panel is not None else None

    cost_roll: dict[pd.Timestamp, dict[str, float]] = {}
    cost_tier: dict[pd.Timestamp, dict[str, float]] = {}
    roll_zero: dict[pd.Timestamp, dict[str, bool]] = {}
    n_eval = n_zero = 0
    sum_rtc_roll = sum_rtc_tier = 0.0
    src_counts = {"quoted": 0, "roll": 0, "tier": 0}
    for d in rebal:
        if d not in close.index:
            cost_roll[d], cost_tier[d], roll_zero[d] = {}, {}, {}
            continue
        roll_row = roll_panel.loc[d]
        adv_row = adv_panel.loc[d]
        sig_row = sigma_panel.loc[d]
        q_row = q_panel.loc[d] if q_panel is not None and d in q_panel.index else None
        cr, ct, rz = {}, {}, {}
        for sym in close.columns:
            adv = adv_row.get(sym, np.nan)
            if not (np.isfinite(adv) and adv > 0):
                continue
            roll = roll_row.get(sym, np.nan)
            sig = sig_row.get(sym, np.nan)
            quoted = q_row.get(sym, np.nan) if q_row is not None else np.nan
            tier = rc.tier_spread_floor(adv)
            impact = (lambda_kyle * sig * np.sqrt(order_value / adv)) if np.isfinite(sig) else np.nan
            cd = rc.combine_round_trip(roll, impact, tier, quoted_spread=quoted)
            cr[sym] = cd["round_trip_roll"]
            ct[sym] = cd["round_trip_tier"]
            rz[sym] = cd["roll_is_zero"]
            n_eval += 1
            n_zero += int(cd["roll_is_zero"])
            src_counts[cd["spread_source"]] += 1
            sum_rtc_roll += cd["round_trip_roll"]
            sum_rtc_tier += cd["round_trip_tier"]
        cost_roll[d], cost_tier[d], roll_zero[d] = cr, ct, rz
    summary = {
        "n_evaluated": n_eval,
        "n_roll_zero": n_zero,
        "roll_zero_frac": eng._r(n_zero / n_eval) if n_eval else None,
        "spread_source_counts": dict(src_counts),
        "spread_source_frac": {k: eng._r(v / n_eval) for k, v in src_counts.items()}
        if n_eval else None,
        "mean_round_trip_roll": eng._r(sum_rtc_roll / n_eval) if n_eval else None,
        "mean_round_trip_tier": eng._r(sum_rtc_tier / n_eval) if n_eval else None,
    }
    return {"cost_roll": cost_roll, "cost_tier": cost_tier, "roll_zero": roll_zero,
            "summary": summary}


# ===========================================================================
# Per-stock-cost net series (generalizes eng.basket_net_series flat -> per-stock)
# ===========================================================================
def d204_basket_net_series(
    pmat: pd.DataFrame, baskets: list[list[str]], rebal: list[pd.Timestamp],
    cost_map: dict[pd.Timestamp, dict[str, float]] | None = None,
) -> dict:
    """Per-period gross/net/turnover/cost for an EW basket sequence with PER-STOCK
    round-trip cost. cost_map[date][symbol] = round-trip cost fraction; missing names
    fall back to the conservative micro tier round-trip. First entry (no prior basket)
    is charged a FULL round trip on the whole basket (matches D-203 first-entry=1.0).
    cost_map=None -> cost-free (gross net of tax only)."""
    gross, net, turns, costs = [], [], [], []
    prev: list[str] = []
    for i in range(len(baskets)):
        g = eng._basket_period(pmat, i, baskets[i])
        cur = baskets[i]
        tau = eng._turnover(prev, cur)
        d = rebal[i]
        cmap = (cost_map or {}).get(d, {})
        if cost_map is None:
            cost = 0.0
        elif not prev:
            cost = (sum(cmap.get(n, _MICRO_RT) for n in cur) / len(cur)) if cur else 0.0
        else:
            wp = {t: 1.0 / len(prev) for t in prev}
            wc = {t: 1.0 / len(cur) for t in cur} if cur else {}
            cost = 0.0
            for n in set(wp) | set(wc):
                dw = wc.get(n, 0.0) - wp.get(n, 0.0)
                if dw != 0.0:
                    cost += 0.5 * abs(dw) * cmap.get(n, _MICRO_RT)
        tax = eng._tax_drag(rebal[i], rebal[i + 1])
        gross.append(g)
        turns.append(tau)
        costs.append(cost)
        net.append(g - cost - tax if np.isfinite(g) else float("nan"))
        prev = cur
    return {"gross": gross, "net": net, "turnover": turns, "cost": costs}


# ===========================================================================
# Breakeven (STRES-1 main verdict) -- flat round-trip bps that zeroes the edge
# ===========================================================================
def breakeven_cost_bps(
    long_net_costfree: list[float], bench: list[float], turnover: list[float],
    grid: tuple[float, ...] = cfg.D204_BREAKEVEN_BPS_GRID,
) -> dict:
    """Flat per-turnover round-trip cost (bps) at which the mean EW_FULL-relative edge
    crosses 0 (model-INDEPENDENT main verdict). Scans `grid`, linearly interpolates the
    first downward zero crossing. inf -> never zeroed on the grid; 0 -> already <=0."""
    pts = []
    for c in grid:
        cf = c / 10_000.0
        net_c = [(g - t * cf) if (np.isfinite(g) and np.isfinite(t)) else float("nan")
                 for g, t in zip(long_net_costfree, turnover)]
        rel_c = eng._relative(net_c, bench)
        vals = [v for v in rel_c if np.isfinite(v)]
        pts.append((float(c), float(np.mean(vals)) if vals else float("nan")))
    be = None
    for j in range(1, len(pts)):
        (c0, m0), (c1, m1) = pts[j - 1], pts[j]
        if np.isfinite(m0) and np.isfinite(m1) and m0 > 0 >= m1:
            be = c0 + (c1 - c0) * (m0 / (m0 - m1))
            break
    if be is None:
        if pts and np.isfinite(pts[0][1]) and pts[0][1] <= 0:
            be = 0.0
        elif pts and np.isfinite(pts[-1][1]) and pts[-1][1] > 0:
            be = float("inf")
    return {"breakeven_bps": eng._r(be) if (be is not None and np.isfinite(be)) else
            ("inf" if be == float("inf") else None),
            "grid": [{"bps": c, "rel_mean": eng._r(m)} for c, m in pts]}


def effective_flat_bps(cost: list[float], turnover: list[float]) -> float:
    """Realized realistic cost expressed as an equivalent flat round-trip bps (so it is
    directly comparable to the breakeven): sum(cost) / sum(turnover) * 1e4."""
    sc = sum(c for c in cost if np.isfinite(c))
    st = sum(t for t in turnover if np.isfinite(t))
    return float(sc / st * 10_000.0) if st > 0 else float("nan")


# ===========================================================================
# Holding period (STRES-2)
# ===========================================================================
def holding_period_stats(
    baskets: list[list[str]], rebal: list[pd.Timestamp], cadence_months: int,
) -> dict:
    """Per-name average consecutive holding (in periods -> months via cadence) + turnover
    distribution. A 'hold' is a run of consecutive periods a name stays in the basket."""
    runs = []
    open_run: dict[str, int] = {}
    prev: set[str] = set()
    for cur_list in baskets:
        cur = set(cur_list)
        for n in cur:
            open_run[n] = open_run.get(n, 0) + 1
        for n in prev - cur:
            runs.append(open_run.pop(n, 0))
        prev = cur
    runs.extend(open_run.values())
    runs = [r for r in runs if r > 0]
    turns = [eng._turnover(baskets[i - 1] if i else [], baskets[i]) for i in range(len(baskets))]
    fin_t = [t for t in turns if np.isfinite(t)]
    avg_periods = float(np.mean(runs)) if runs else float("nan")
    return {
        "avg_holding_periods": eng._r(avg_periods),
        "avg_holding_months": eng._r(avg_periods * cadence_months),
        "median_holding_periods": eng._r(float(np.median(runs))) if runs else None,
        "mean_turnover": eng._r(float(np.mean(fin_t))) if fin_t else None,
        "median_turnover": eng._r(float(np.median(fin_t))) if fin_t else None,
        "n_holds": len(runs),
    }


# ===========================================================================
# Liquidity paradox decompose (EKLEME-3 / H1)
# ===========================================================================
def liquidity_paradox_decompose(
    comp: pd.DataFrame, pmat: pd.DataFrame, ew_full: list[float], rebal: list[pd.Timestamp],
    liq: dict, cost_roll: dict, cpi: pd.Series | None, top_n: int = cfg.D204_TOP_N,
) -> dict:
    """Per liquidity tercile (liquid/mid/illiquid): hi52 top-N EW_FULL-relative edge
    BEFORE and AFTER realistic cost (+ real after-cost). Tests whether the D-203 illiquid >
    liquid ordering (the RR-043 reversal) SURVIVES realistic cost -- illiquid names get hit
    hardest, so a pre-cost illiquid edge can collapse post-cost."""
    out = {}
    for tercile in ("liquid", "mid", "illiquid"):
        baskets = []
        for i in range(len(rebal) - 1):
            d = rebal[i]
            pool = liq.get(d, {}).get(tercile, [])
            baskets.append(eng.select_top_n(d, comp, top_n, pool=pool))
        free = d204_basket_net_series(pmat, baskets, rebal, cost_map=None)["net"]
        cost = d204_basket_net_series(pmat, baskets, rebal, cost_map=cost_roll)["net"]
        rel_free = eng._relative(free, ew_full)
        rel_cost = eng._relative(cost, ew_full)
        real_cost = eng.to_real(cost, rebal, cpi)
        out[tercile] = {
            "rel_costfree_mean": eng._mean_ci(rel_free).get("mean"),
            "rel_aftercost_mean": eng._mean_ci(rel_cost).get("mean"),
            "real_aftercost_mean": eng._mean_ci(real_cost).get("mean"),
        }
    lq = out["liquid"]["rel_aftercost_mean"]
    il = out["illiquid"]["rel_aftercost_mean"]
    out["illiquid_still_dominates_after_cost"] = bool(
        lq is not None and il is not None and il > lq)
    out["liquid_positive_after_cost"] = bool(lq is not None and lq > 0)
    return out


# ===========================================================================
# Mechanism (STRES-4): factor overlap + concentration
# ===========================================================================
def factor_overlap(
    hi52_rank: pd.DataFrame, mom_rank: pd.DataFrame, pmat: pd.DataFrame,
    rebal: list[pd.Timestamp], top_n: int = cfg.D204_TOP_N,
) -> dict:
    """hi52 vs mom120 top-N basket overlap (mean |A∩B|/N) + long-short series correlation
    ('is hi52 just momentum?'). Identical panels -> overlap=1.0, correlation=1.0."""
    overlaps, hi_ls, mom_ls = [], [], []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        a = set(eng.select_top_n(d, hi52_rank, top_n))
        b = set(eng.select_top_n(d, mom_rank, top_n))
        if a and b:
            overlaps.append(len(a & b) / float(top_n))
        ha = eng._basket_period(pmat, i, eng.select_top_n(d, hi52_rank, top_n))
        hb = eng._basket_period(pmat, i, eng.select_bottom_n(d, hi52_rank, top_n))
        ma = eng._basket_period(pmat, i, eng.select_top_n(d, mom_rank, top_n))
        mb = eng._basket_period(pmat, i, eng.select_bottom_n(d, mom_rank, top_n))
        hi_ls.append(ha - hb if (np.isfinite(ha) and np.isfinite(hb)) else np.nan)
        mom_ls.append(ma - mb if (np.isfinite(ma) and np.isfinite(mb)) else np.nan)
    pair = [(x, y) for x, y in zip(hi_ls, mom_ls) if np.isfinite(x) and np.isfinite(y)]
    corr = None
    if len(pair) >= 2:
        xs, ys = np.array([p[0] for p in pair]), np.array([p[1] for p in pair])
        if xs.std() > 0 and ys.std() > 0:
            corr = float(np.corrcoef(xs, ys)[0, 1])
    return {"mean_basket_overlap": eng._r(float(np.mean(overlaps))) if overlaps else None,
            "long_short_correlation": eng._r(corr) if corr is not None else None}


def concentration_stats(
    baskets: list[list[str]], bist100: pd.DataFrame, funds: pd.DataFrame,
    rebal: list[pd.Timestamp], lag_months: int = cfg._d203.D203_FUND_PUBLICATION_LAG_MONTHS,
) -> dict:
    """Concentration proxies (no formal sector data): mean fraction of the hi52 basket that
    is (a) a bist100 constituent and (b) in the top mktval tercile (large-cap tilt?)."""
    mv = funds.copy()
    mv["month"] = mv["month"].astype("period[M]")
    mv_piv = mv.pivot_table(index="month", columns="symbol", values="mktval", aggfunc="last").sort_index()
    bist_fracs, mv_fracs, sizes = [], [], []
    for i in range(len(baskets)):
        d = rebal[i]
        b = baskets[i]
        if not b:
            continue
        sizes.append(len(b))
        if d in bist100.index:
            flag = bist100.loc[d]
            bist_fracs.append(np.mean([1.0 if flag.get(n, 0) == 1 else 0.0 for n in b]))
        cutoff = pd.Period(pd.Timestamp(d), freq="M") - lag_months
        avail = mv_piv.loc[mv_piv.index <= cutoff]
        if not avail.empty:
            row = avail.ffill().iloc[-1].dropna()
            row = row[row > 0]
            if len(row) >= 3:
                hi_cut = row.quantile(1.0 - cfg._d203.D203_LIQUIDITY_TERCILE)
                top = set(row[row >= hi_cut].index)
                mv_fracs.append(np.mean([1.0 if n in top else 0.0 for n in b]))
    return {"mean_bist100_frac": eng._r(float(np.mean(bist_fracs))) if bist_fracs else None,
            "mean_top_mktval_frac": eng._r(float(np.mean(mv_fracs))) if mv_fracs else None,
            "mean_basket_size": eng._r(float(np.mean(sizes))) if sizes else None}


# ===========================================================================
# OOS / walk-forward (STRES-3)
# ===========================================================================
def walk_forward(
    rel_series: list[float], rebal: list[pd.Timestamp], split: str,
    disinflation_window: tuple[str, str],
) -> dict:
    """Honest in-sample walk-forward: train (start < split) vs holdout (start >= split)
    means + the disinflation sub-window mean (WEAK regime-change proxy). NOT a true OOS."""
    sp = eng.regime_split(rel_series, rebal, split)
    lo, hi = pd.Timestamp(disinflation_window[0]), pd.Timestamp(disinflation_window[1])
    dis = [rel_series[i] for i in range(len(rel_series))
           if lo <= rebal[i] <= hi and np.isfinite(rel_series[i])]
    return {
        "split": split,
        "train_mean": sp["pre_mean"], "train_n": sp["pre_n"],
        "holdout_mean": sp["post_mean"], "holdout_n": sp["post_n"],
        "both_positive": sp["both_positive"],
        "disinflation_window": list(disinflation_window),
        "disinflation_mean": eng._r(float(np.mean(dis))) if dis else None,
        "disinflation_n": len(dis),
    }


# ===========================================================================
# Verdict (frozen)
# ===========================================================================
_OOS_GAP = (
    "OOS-BOSLUK: ornek (2019-2026) tek-uzun yuksek-enflasyon rejimi. Gercek enflasyon-"
    "normallesme OOS YOK -> rejim-degisim dayanikligi KANITLANAMAZ. Walk-forward in-sample; "
    "disinflasyon 2024-26 YALNIZCA zayif-proxy. pre-2019 acquisition reddedildi (corp-action-"
    "yok -> kirli, D-185-riski). Bu bir olcumdur; deployment ayri maintainer karari."
)


def d204_verdict(
    liquid_aftercost_real_mean: float | None, breakeven_bps, realistic_cost_bps: float | None,
    illiquid_dominates_after_cost: bool, liquid_positive_after_cost: bool,
    hurdle: float = cfg.D204_DEPLOY_MIN_LIQUID_NET,
    safety_mult: float = cfg.D204_BREAKEVEN_SAFETY_MULT,
) -> dict:
    """Frozen 3-way deploy decision. Precedence: tradeable-DEGIL > KIRILGAN > DEPLOY-ADAY.
    breakeven_bps may be the string 'inf' (never zeroed on the grid -> treated as +inf)."""
    be = float("inf") if breakeven_bps == "inf" else (
        float(breakeven_bps) if breakeven_bps is not None else None)
    cost = realistic_cost_bps if (realistic_cost_bps is not None and np.isfinite(realistic_cost_bps)) else None
    lar = liquid_aftercost_real_mean

    reasons = []
    # 1) GERCEK-fenomen ama tradeable-DEGIL: liquid edge gone after cost, OR breakeven < cost.
    if lar is None or lar <= 0 or not liquid_positive_after_cost or be is None or (cost is not None and be < cost):
        if lar is None or lar <= 0 or not liquid_positive_after_cost:
            reasons.append("likit-tercil maliyet-sonrasi reel net <= 0")
        if be is not None and cost is not None and be < cost:
            reasons.append("breakeven < gercekci-maliyet")
        if be is None:
            reasons.append("breakeven hesaplanamadi")
        return {"verdict": "GERCEK-ama-tradeable-DEGIL", "reasons": reasons, "oos_gap": _OOS_GAP}
    # 2) KIRILGAN: breakeven ~ cost (within safety mult), OR below deposit hurdle, OR illiquid-concentrated.
    if (cost is not None and be < safety_mult * cost) or (lar < hurdle) or illiquid_dominates_after_cost:
        if cost is not None and be < safety_mult * cost:
            reasons.append(f"breakeven < {safety_mult}x gercekci-maliyet (breakeven ~ maliyet)")
        if lar < hurdle:
            reasons.append("likit-tercil reel net < TLREF-mevduat-esigi")
        if illiquid_dominates_after_cost:
            reasons.append("edge illikit-tercilde yogun (maliyet-sonrasi bile)")
        return {"verdict": "KIRILGAN", "reasons": reasons, "oos_gap": _OOS_GAP}
    # 3) DEPLOY-ADAY
    return {"verdict": "DEPLOY-ADAY",
            "reasons": ["likit-tercil maliyet-sonrasi reel net mevduat-esigini gecti AND "
                        f"breakeven >= {safety_mult}x maliyet AND illikit-yogun degil"],
            "oos_gap": _OOS_GAP}


# ===========================================================================
# maintainer
# ===========================================================================
def _series_block(series: list[float]) -> dict:
    return {**eng._mean_ci(series), "nw_t": eng._r(eng._nw_t(series))}


def _run_window_cadence(data: dict, start: str, end: str, cadence: int, tlref) -> dict:
    close, value_tl, cpi = data["close"], data["value_tl"], data["cpi"]
    rebal = multi_cadence_rebalance_dates(close.index, start, end, cadence)
    daily = eng.clip_clean_returns(close)
    pmat = eng._period_return_matrix(daily, rebal)
    ew_full = eng.ew_full_benchmark(pmat)
    liq = eng.liquidity_tercile_pools(value_tl, rebal)
    comp = eng._xs_rank(eng.hi52_panel(close, rebal))

    long_baskets, short_baskets = [], []
    for i in range(len(rebal) - 1):
        d = rebal[i]
        long_baskets.append(eng.select_top_n(d, comp, cfg.D204_TOP_N))
        short_baskets.append(eng.select_bottom_n(d, comp, cfg.D204_TOP_N))

    cost = per_stock_cost_panel(close, value_tl, rebal)
    free = d204_basket_net_series(pmat, long_baskets, rebal, cost_map=None)
    roll = d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_roll"])
    tier = d204_basket_net_series(pmat, long_baskets, rebal, cost_map=cost["cost_tier"])
    short_free = d204_basket_net_series(pmat, short_baskets, rebal, cost_map=None)["net"]

    rel_free = eng._relative(free["net"], ew_full)
    rel_roll = eng._relative(roll["net"], ew_full)
    rel_tier = eng._relative(tier["net"], ew_full)
    real_roll = eng.to_real(roll["net"], rebal, cpi)
    ls = [(a - b) if (np.isfinite(a) and np.isfinite(b)) else float("nan")
          for a, b in zip(free["net"], short_free)]
    be = breakeven_cost_bps(free["net"], ew_full, free["turnover"])
    eff_bps = effective_flat_bps(roll["cost"], roll["turnover"])

    return {
        "rebal": rebal, "pmat": pmat, "ew_full": ew_full, "liq": liq, "comp": comp,
        "long_baskets": long_baskets, "cost": cost,
        "rel_free": rel_free, "rel_roll": rel_roll, "real_roll": real_roll,
        "block": {
            "n_periods": len(free["net"]),
            "rel_ew_costfree": _series_block(rel_free),
            "rel_ew_aftercost_roll": _series_block(rel_roll),
            "rel_ew_aftercost_tier": _series_block(rel_tier),
            "real_aftercost_roll": _series_block(real_roll),
            "long_short_costfree": _series_block(ls),
            "breakeven": be,
            "realistic_cost_flat_bps_equiv": eng._r(eff_bps),
            "roll_zero_accounting": cost["summary"],
            "holding_period": holding_period_stats(long_baskets, rebal, cadence),
            "max_drawdown": eng._r(eng.max_drawdown(eng._equity_curve(pmat, long_baskets))),
        },
    }


def run_d204(
    root: Path | str = cfg.D204_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
) -> dict:
    """Full D-204 hi52 stress-test. REFUSES to run unless STAGE0_d204.json exists
    (pre-registration). Reuses the D-203 engine + frozen D-202 panel verbatim."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; D-204 must be frozen "
            "BEFORE results (pre-registration discipline).")

    data = eng.load_d202_panel(root)
    tlref = _load_tlref()

    windows = {
        "common": (cfg.D204_COMMON_WINDOW_START, cfg.D204_COMMON_WINDOW_END),
        "extended": (cfg.D204_EXTENDED_WINDOW_START, cfg.D204_EXTENDED_WINDOW_END),
    }
    # EKLEME-B reproducibility guard: recompute the TLREF deposit hurdle, assert == frozen.
    hurdle_reb = multi_cadence_rebalance_dates(
        data["close"].index, cfg.D204_COMMON_WINDOW_START, cfg.D204_COMMON_WINDOW_END, 1)
    hurdle_calc = deploy_threshold_from_tlref(tlref, data["cpi"], hurdle_reb)
    hurdle_ok = (hurdle_calc["mean_monthly_real_carry"] is not None and
                 abs(hurdle_calc["mean_monthly_real_carry"] - cfg.D204_DEPLOY_MIN_LIQUID_NET)
                 <= cfg.D204_DEPLOY_HURDLE_TOL)
    if not hurdle_ok:
        raise RuntimeError(
            f"D-204 deploy hurdle drift: recomputed real TLREF carry "
            f"{hurdle_calc['mean_monthly_real_carry']} != frozen "
            f"{cfg.D204_DEPLOY_MIN_LIQUID_NET} (tol {cfg.D204_DEPLOY_HURDLE_TOL}).")

    results: dict = {"windows": {}}
    primary = {}
    for win, (s, e) in windows.items():
        results["windows"][win] = {"cadences": {}}
        for cad in cfg.D204_REBALANCE_CADENCES:
            wc = _run_window_cadence(data, s, e, cad, tlref)
            results["windows"][win]["cadences"][f"{cad}m"] = wc["block"]
            if win == "common" and cad == cfg.D204_PRIMARY_CADENCE:
                primary = wc

    # Primary (common, monthly): the deep STRES-3/4/5 analyses + verdict.
    rebal = primary["rebal"]
    para = liquidity_paradox_decompose(
        primary["comp"], primary["pmat"], primary["ew_full"], rebal,
        primary["liq"], primary["cost"]["cost_roll"], data["cpi"])
    mom_rank = eng._xs_rank(eng.momentum_panel(data["close"], rebal))
    overlap = factor_overlap(primary["comp"], mom_rank, primary["pmat"], rebal)
    conc = concentration_stats(primary["long_baskets"], data["bist100"], data["funds"], rebal)
    wf = walk_forward(primary["rel_roll"], rebal, cfg.D204_WALKFWD_SPLIT, cfg.D204_DISINFLATION_WINDOW)

    liquid_real = para["liquid"]["real_aftercost_mean"]
    pblock = results["windows"]["common"]["cadences"]["1m"]
    verdict = d204_verdict(
        liquid_aftercost_real_mean=liquid_real,
        breakeven_bps=pblock["breakeven"]["breakeven_bps"],
        realistic_cost_bps=pblock["realistic_cost_flat_bps_equiv"],
        illiquid_dominates_after_cost=para["illiquid_still_dominates_after_cost"],
        liquid_positive_after_cost=para["liquid_positive_after_cost"])

    out = {
        "directive": "D-204",
        "phase": "FAZ-1 hi52 stress-test (realistic-cost + vade + OOS + mechanism + H1)",
        "config_version": cfg.D204_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.D204_PRICE_CONTENT_HASH,
        "candidate": cfg.D204_CANDIDATE_LABEL,
        "deploy_hurdle": {
            "frozen_min_liquid_real_net": cfg.D204_DEPLOY_MIN_LIQUID_NET,
            "recomputed": hurdle_calc,
            "reproducibility_ok": hurdle_ok,
            "rationale": "real TLREF deposit carry (project principle real > max(TUFE,TLREF))",
        },
        "stress_results": results,
        "stres3_oos_walk_forward": wf,
        "stres4_mechanism": {"factor_overlap_vs_mom120": overlap, "concentration": conc},
        "ekleme3_liquidity_paradox": para,
        "verdict": verdict,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("D-204 results written to %s", out_path)
    return out

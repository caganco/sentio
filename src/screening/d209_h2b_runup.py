"""D-209 H2b TEMETTU-RUNUP engine -- frozen demo-goal signal, D-207 corrected cost.

Re-runs the FROZEN demo-goal H2/H2b dividend pre-ex run-up signal (detection + book PORTED
bit-for-bit, NO new definition) under the D-207 corrected per-stock realistic cost, replacing
the demo-goal FLAT 20/100bp-per-side cost that originally eliminated it. Decides: is H2b still
tradeable on a fair (de-inflated) cost ground, or a significance wall like hi52 (D-208)?

Two FROZEN demo-goal variants (NO "best" selected; both gated, best is headline):
  V1 daily-churn basket (demo-goal h2b_runup_basket.py BIREBIR): EW long-only daily book; a
     name is HELD on day t iff its ex-date is in [t+1, t+5] (window [-5,-1]); exit before ex
     -> no dividend, no 15% tax. PRIMARY = invested-day market-RELATIVE arithmetic series
     (strat_net - EW_FULL), carry-immune. NW HAC t (lag=5) on that series.
  V2 low-turnover discrete capture (demo-goal H2 "RUNUP_capture" leg BIREBIR): per (symbol,
     ex) event ONE round-trip, compound return over [-10,-1] (10 trading days = "hold-10g"),
     EW-combined per ex-month, exit before ex (add_div=False -> no tax). Simple t on the
     monthly cohort relative series (frozen significance metric for the aggregated leg).

COST ADAPTATION (faithful generalization, NOT a new model): the frozen FLAT drag
`cost_turn[t] * bp/1e4` (per-side bp; a round trip = 2*bp/1e4) is replaced by the D-207
per-name round-trip `rt[sym]`: each entry OR exit charges a ONE-WAY 0.5*rt[sym], so a full
round trip costs rt[sym]. When rt is uniform == 2*bp/1e4 this reduces EXACTLY to the frozen
FLAT model (verified by test). The frozen turnover STRUCTURE (enter/exit bodies, /n_held) is
preserved verbatim -- only the per-name cost rate changes. Cost panel = D-204/D-207
per_stock_cost_panel (Roll+Kyle, EOD-quoted-primary), REUSED read-only.

Strangler: PORTS the frozen demo-goal detection/book (cannot drift; a reproduction guard
asserts ~1108 events / 265 symbols on the local frozen panel) and REUSES the committed D-204
cost harness + D-205 liquid-universe threshold (>=1e7 absolute ADV). Refuses to run unless
STAGE0_d209.json exists (pre-registration). MEASUREMENT-ONLY: optimization/grid-sweep
FORBIDDEN; look-ahead-safe (exit before ex); committed engines ZERO-touch.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.screening import d203_clean_universe_test as eng
from src.screening import d204_hi52_stress as d204
from src.screening import d209_config as cfg

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RESULTS_DIR = _REPO_ROOT / "docs" / "yol1"
_STAGE0_PATH = _RESULTS_DIR / "STAGE0_d209.json"
_MICRO_RT = d204._MICRO_RT   # conservative micro-tier round-trip fallback (shared with D-204)


# ===========================================================================
# PORTED frozen statistics + detection + windowing (demo-goal H2 lab, BIREBIR)
# ===========================================================================
def tstat(arr):
    """Frozen demo-goal simple t-stat of the mean (H0: mean=0). PORT (bit-for-bit)."""
    a = np.array([x for x in arr if np.isfinite(x)], dtype=float)
    if len(a) < 3:
        return np.nan, np.nan, len(a)
    se = a.std(ddof=1) / np.sqrt(len(a))
    return (a.mean() / se if se > 0 else np.nan), a.mean(), len(a)


def nw_tstat(x, lag=cfg.D209_NW_LAG):
    """Frozen demo-goal Newey-West HAC t-stat of the mean of series x. PORT (bit-for-bit).

    Committed eng._nw_t is FIXED at lag=3 (D203_NW_LAGS); H2b's daily series needs lag=5,
    so the frozen estimator is ported rather than reused."""
    a = np.asarray([v for v in x if np.isfinite(v)], dtype=float)
    n = len(a)
    if n < lag + 3:
        return np.nan, (float(a.mean()) if n else np.nan), n
    m = a.mean()
    e = a - m
    gamma0 = (e @ e) / n
    s = gamma0
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1.0)
        cov = (e[L:] @ e[:-L]) / n
        s += 2.0 * w * cov
    se = np.sqrt(s / n) if s > 0 else np.nan
    return (m / se if se and se > 0 else np.nan), m, n


def detect_exdates(px: pd.DataFrame, ex_gap_min: float = cfg.D209_EX_GAP_MIN):
    """Frozen demo-goal ex-date detection. PORT (bit-for-bit).

    Ex-date where the gross-TR-index return exceeds the price-only (adjusted_close) return by
    more than `ex_gap_min` (the reinvested dividend). Returns [(symbol, ex_date, est_yield)]."""
    px = px.sort_values(["symbol", "date"])
    g = px.groupby("symbol")
    rg = g["tr_index_gross"].pct_change()
    rc = g["adjusted_close"].pct_change()
    px = px.assign(exgap=(rg - rc))
    ex = px[px["exgap"] > ex_gap_min]
    return [(r.symbol, r.date, float(r.exgap)) for r in ex.itertuples()]


def compound_ret(daily, idx, sym, d, lo, hi):
    """Frozen demo-goal per-event compound return over [d+lo, d+hi]. PORT (bit-for-bit)."""
    pos = idx.searchsorted(d, side="left")
    if pos >= len(idx) or idx[pos] != d:
        return np.nan
    a, b = pos + lo, pos + hi
    if a < 0 or b >= len(idx):
        return np.nan
    seg = daily[sym].iloc[a:b + 1].values
    seg = seg[np.isfinite(seg)]
    return float(np.prod(1.0 + seg) - 1.0) if len(seg) else np.nan


def compound_window_mkt(mkt, idx, d, lo, hi):
    """Frozen demo-goal EW-market compound return over [d+lo, d+hi]. PORT (bit-for-bit)."""
    pos = idx.searchsorted(d, side="left")
    if pos >= len(idx) or idx[pos] != d:
        return np.nan
    a, b = pos + lo, pos + hi
    if a < 0 or b >= len(idx):
        return np.nan
    seg = mkt.iloc[a:b + 1].values
    seg = seg[np.isfinite(seg)]
    return float(np.prod(1.0 + seg) - 1.0) if len(seg) else np.nan


def _cpi_ratio(cpi, idx, d, lo, hi):
    """Frozen demo-goal CPI ratio over the event window (real-return deflator). PORT."""
    if cpi is None or len(cpi) == 0:
        return np.nan
    pos = idx.searchsorted(d, side="left")
    if pos >= len(idx) or idx[pos] != d:
        return np.nan
    a, b = max(0, pos + lo), min(len(idx) - 1, pos + hi)
    x, y = cpi.asof(idx[a]), cpi.asof(idx[b])
    if not (np.isfinite(x) and np.isfinite(y)) or x <= 0:
        return np.nan
    return float(y / x)


def build_holdings(events_cols, idx, lo=cfg.D209_HOLD_LO, hi=cfg.D209_HOLD_HI):
    """Frozen demo-goal V1 holdings. PORT (bit-for-bit).

    Returns held: list (len=ndays) of column-int lists held that day; a name (col,ex) is held
    on day t iff its ex-date is in [t-lo .. t-hi] forward, i.e. ex in [t+1, t+5] for [-5,-1].
    Look-ahead-safe: the position is established lo..hi trading days BEFORE the ex-date and
    exited before ex (so no dividend is captured)."""
    n = len(idx)
    held = [[] for _ in range(n)]
    for col, d in events_cols:
        pos = idx.searchsorted(d, side="left")
        if pos >= n or idx[pos] != d:
            continue
        a, b = pos + lo, pos + hi
        a, b = max(0, a), min(n - 1, b)
        for t in range(a, b + 1):
            held[t].append(col)
    return held


# ===========================================================================
# D-209 helpers: absolute-ADV liquid flag, arithmetic breakeven
# ===========================================================================
def liquid_at(value_tl, idx, sym, d, adv_min=cfg.D209_LIQUID_ADV_MIN_TL,
              trailing=cfg.D209_LIQUID_ADV_TRAILING_DAYS) -> bool:
    """D-205 ABSOLUTE liquidity test (NOT tercile): is `sym`'s trailing-`trailing`-day median
    traded value (value_tl) >= `adv_min` (1e7 TL) as of date d? Look-ahead-safe (trailing)."""
    pos = idx.searchsorted(d, side="left")
    if pos >= len(idx) or idx[pos] != d:
        return False
    win = value_tl.iloc[max(0, pos - trailing + 1):pos + 1]
    if sym not in win.columns:
        return False
    med = win[sym].median(skipna=True)
    return bool(np.isfinite(med) and med >= adv_min)


def _arith_breakeven_roundtrip_bps(gross, bench, turnover_oneside,
                                   grid=cfg.D209_BREAKEVEN_BPS_GRID):
    """Round-trip bps at which the mean ARITHMETIC relative (gross - bench) crosses 0, given a
    per-period one-sided turnover series (so cost = turnover_oneside * roundtrip/2 * /1e4 ...
    expressed directly: drag = turnover_oneside * (bp/1e4) makes bp the ONE-SIDE rate; a round
    trip = 2x). Scans `grid` (round-trip bps), reports the first downward zero crossing.

    This is the model-INDEPENDENT cost ceiling, in the SAME arithmetic frame as the frozen V1
    primary metric (not the geometric eng._relative)."""
    g = np.asarray(gross, float)
    b = np.asarray(bench, float)
    t = np.asarray(turnover_oneside, float)
    pts = []
    for rt_bp in grid:
        side = (rt_bp / 2.0) / 1e4            # one-side fraction
        net = g - t * side
        rel = net - b
        rel = rel[np.isfinite(rel)]
        pts.append((float(rt_bp), float(rel.mean()) if len(rel) else float("nan")))
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
    return (eng._r(be) if (be is not None and np.isfinite(be))
            else ("inf" if be == float("inf") else None))


def _regime_split_dates(values, dates, split):
    """Pre/post mean + sign-stability of `values` indexed by `dates`, split at `split`."""
    split = pd.Timestamp(split)
    vals = np.asarray(values, float)
    dts = pd.DatetimeIndex(dates)
    pre = vals[(dts < split) & np.isfinite(vals)]
    post = vals[(dts >= split) & np.isfinite(vals)]
    pm = float(pre.mean()) if len(pre) else np.nan
    qm = float(post.mean()) if len(post) else np.nan
    return {"pre": eng._r(pm), "post": eng._r(qm),
            "sign_stable": bool(np.isfinite(pm) and np.isfinite(qm)
                                and np.sign(pm) == np.sign(qm))}


# ===========================================================================
# V1 -- daily-churn basket [-5,-1] under D-207 per-name cost
# ===========================================================================
def run_v1(events, daily, ew, idx, cost_roll, label="ALL"):
    """events = [(sym, ex_date, yield)] (already restricted to the desired universe).
    daily = clean-return panel; ew = EW_FULL daily array; cost_roll[date][sym] = round-trip."""
    col_of = {c: i for i, c in enumerate(daily.columns)}
    events_cols = [(col_of[s], d) for (s, d, _y) in events if s in col_of]
    inv_col = {i: s for s, i in col_of.items()}
    daily_vals = daily.values
    n = len(idx)
    held = build_holdings(events_cols, idx)

    strat_gross = np.full(n, np.nan)
    drag = np.zeros(n)
    cost_turn = np.zeros(n)          # frozen two-sided turnover (enter+exit)/n_held
    n_held = np.zeros(n, dtype=int)
    prev = set()
    for t in range(n):
        cur = held[t]
        cs = set(cur)
        n_held[t] = len(cur)
        if cur:
            vals = daily_vals[t, cur]
            vals = vals[np.isfinite(vals)]
            if len(vals):
                strat_gross[t] = float(vals.mean())
            enter = cs - prev
            exit_ = prev - cs
            cmap = cost_roll.get(idx[t], {})
            day_cost = 0.0
            for c in enter:
                day_cost += 0.5 * cmap.get(inv_col[c], _MICRO_RT)
            for c in exit_:
                day_cost += 0.5 * cmap.get(inv_col[c], _MICRO_RT)
            drag[t] = day_cost / max(len(cur), 1)
            cost_turn[t] = (len(enter) + len(exit_)) / max(len(cur), 1)
        prev = cs

    invested = np.isfinite(strat_gross) & (n_held > 0)
    inv_days = int(invested.sum())
    strat_net = strat_gross - drag
    dts = idx[invested]
    gross_rel = (strat_gross - ew)[invested]
    net_rel = (strat_net - ew)[invested]

    # realized realistic round-trip bps: sum(drag)/sum(cost_turn) = one-side rate; x2 = round-trip
    sc = float(np.nansum(drag[invested]))
    st = float(np.nansum(cost_turn[invested]))
    realized_rt_bps = (sc / st * 2.0 * 1e4) if st > 0 else None
    be_bps = _arith_breakeven_roundtrip_bps(strat_gross[invested], ew[invested],
                                            cost_turn[invested])

    nt_net, mnet, nn = nw_tstat(net_rel)
    nt_gross, mgross, _ = nw_tstat(gross_rel)
    conc = n_held[invested]
    reg = _regime_split_dates(net_rel, dts, cfg.D209_REGIME_SPLIT)
    return {
        "label": label, "variant": "V1-daily-churn", "hold_window": [cfg.D209_HOLD_LO, cfg.D209_HOLD_HI],
        "n_events": len(events_cols), "invested_days": inv_days, "total_days": int(n),
        "invested_frac": eng._r(inv_days / n if n else None),
        "concurrency_mean": eng._r(float(conc.mean()) if len(conc) else None),
        "concurrency_median": eng._r(float(np.median(conc)) if len(conc) else None),
        "concurrency_max": int(conc.max()) if len(conc) else 0,
        "mean_turnover_twoSide": eng._r(st / inv_days if inv_days else None),
        "gross_rel_mean": eng._r(float(mgross)), "gross_rel_nw_t": eng._r(nt_gross),
        "net_rel_mean": eng._r(float(mnet)), "net_rel_nw_t": eng._r(nt_net),
        "net_rel_n": nn,
        "realized_cost_roundtrip_bps": eng._r(realized_rt_bps),
        "breakeven_roundtrip_bps": be_bps,
        "regime": reg,
        "nw_lag": cfg.D209_NW_LAG,
    }


# ===========================================================================
# V2 -- low-turnover discrete capture [-10,-1] under D-207 per-name cost
# ===========================================================================
def run_v2(events, daily, mkt, idx, cpi, cost_roll, label="ALL"):
    """Frozen demo-goal RUNUP_capture leg [-10,-1] (per-event, EW-per-ex-month), with the FLAT
    2*bp cost replaced by the D-207 per-event round-trip rt[sym] (evaluated at the entry day).
    rel_t = simple t on the monthly cohort series (frozen significance metric for this leg)."""
    lo, hi = cfg.D209_V2_HOLD_LO, cfg.D209_V2_HOLD_HI
    per_month: dict[pd.Period, list] = {}
    rt_vals = []
    for s, d, _y in events:
        if s not in daily.columns:
            continue
        r = compound_ret(daily, idx, s, d, lo, hi)
        b = compound_window_mkt(mkt, idx, d, lo, hi)
        if not (np.isfinite(r) and np.isfinite(b)):
            continue
        pos = idx.searchsorted(d, side="left")
        entry_day = idx[max(0, pos + lo)]
        rt = cost_roll.get(entry_day, {}).get(s, _MICRO_RT)
        rt_vals.append(rt)
        ym = d.to_period("M")
        per_month.setdefault(ym, []).append((r, b, d, rt))

    gross, rel, rel_net, months, reals_net = [], [], [], [], []
    for ym, lst in sorted(per_month.items()):
        g = float(np.mean([x[0] for x in lst]))
        bm = float(np.mean([x[1] for x in lst]))
        gnet = float(np.mean([x[0] - x[3] for x in lst]))   # per-event gross minus round-trip rt
        d0 = lst[0][2]
        gross.append(g)
        rel.append((1 + g) / (1 + bm) - 1)
        rel_net.append((1 + gnet) / (1 + bm) - 1)
        months.append(pd.Timestamp(ym.start_time))
        infl = _cpi_ratio(cpi, idx, d0, lo, hi)
        if np.isfinite(infl) and infl > 0:
            reals_net.append((1 + gnet) / infl - 1)

    n_events = sum(len(v) for v in per_month.values())
    t_relfree = tstat(rel)[0]
    t_relnet, m_relnet, n_relnet = tstat(rel_net)
    reg = _regime_split_dates(rel_net, months, cfg.D209_REGIME_SPLIT)
    realized_rt_bps = (float(np.mean(rt_vals)) * 1e4) if rt_vals else None
    # breakeven: round-trip bp at which the monthly net cohort relative crosses 0.
    be = None
    for rt_bp in cfg.D209_BREAKEVEN_BPS_GRID:
        cf = rt_bp / 1e4
        rn = []
        for ym, lst in sorted(per_month.items()):
            gnet = float(np.mean([x[0] - cf for x in lst]))
            bm = float(np.mean([x[1] for x in lst]))
            rn.append((1 + gnet) / (1 + bm) - 1)
        if np.mean([v for v in rn if np.isfinite(v)]) <= 0:
            be = float(rt_bp)
            break
    return {
        "label": label, "variant": "V2-discrete-capture", "hold_window": [lo, hi],
        "hold_days": hi - lo + 1, "n_events": n_events, "n_months": len(per_month),
        "gross_mean": eng._r(float(np.mean(gross))) if gross else None,
        "rel_costfree_mean": eng._r(float(np.mean(rel))) if rel else None,
        "rel_costfree_t": eng._r(t_relfree),
        "net_rel_mean": eng._r(float(m_relnet)) if rel_net else None,
        "net_rel_t": eng._r(t_relnet), "net_rel_n": n_relnet,
        "realized_cost_roundtrip_bps": eng._r(realized_rt_bps),
        "breakeven_roundtrip_bps": eng._r(be) if be is not None else "inf",
        "regime": reg,
    }


# ===========================================================================
# Verdict (2-way, frozen keep-bar)
# ===========================================================================
def _keep_bar(variant_all: dict, variant_liq: dict, t_key: str) -> dict:
    """keep-bar (frozen): cost-after rel mean > 0 AND |t| >= 2 AND regime sign-stable (ALL)
    AND survives in the liquid universe (liquid cost-after rel > 0 AND |t| >= 2)."""
    rel_pos = bool(variant_all.get("net_rel_mean") is not None
                   and variant_all["net_rel_mean"] > 0)
    t_all = variant_all.get(t_key)
    t_ok = bool(t_all is not None and np.isfinite(t_all) and abs(t_all) >= cfg.D209_GATE_NW_T_MIN)
    reg_ok = bool(variant_all.get("regime", {}).get("sign_stable"))
    liq_rel_pos = bool(variant_liq.get("net_rel_mean") is not None
                       and variant_liq["net_rel_mean"] > 0)
    t_liq = variant_liq.get(t_key)
    liq_t_ok = bool(t_liq is not None and np.isfinite(t_liq) and abs(t_liq) >= cfg.D209_GATE_NW_T_MIN)
    liq_ok = liq_rel_pos and liq_t_ok
    passed = rel_pos and t_ok and reg_ok and liq_ok
    return {"rel_after_cost_positive": rel_pos, "nw_t_ge_2": t_ok,
            "regime_sign_stable": reg_ok, "survives_liquid": liq_ok, "pass": passed}


def d209_verdict(v1_all, v1_liq, v2_all, v2_liq) -> dict:
    """2-way verdict: TRADEABLE-EDGE (deploy candidate) if EITHER frozen variant clears the
    full keep-bar on its FROZEN significance metric (V1 NW-t lag5, V2 simple-t); else
    YINE-TRADEABLE-DEGIL -> H2b clean-archived (significance OR cost wall, N<=3 SON)."""
    kb_v1 = _keep_bar(v1_all, v1_liq, "net_rel_nw_t")
    kb_v2 = _keep_bar(v2_all, v2_liq, "net_rel_t")
    any_pass = kb_v1["pass"] or kb_v2["pass"]
    headline = "V1" if kb_v1["pass"] else ("V2" if kb_v2["pass"] else (
        "V1" if (v1_liq.get("net_rel_nw_t") or 0) >= (v2_liq.get("net_rel_t") or 0) else "V2"))
    if any_pass:
        verdict = "TRADEABLE-EDGE"
        note = ("H2b duzeltilmis-maliyette TRADEABLE -> deploy-aday (the project "
                "sonraki-adim). beklenti-disi: onceden-ilan-edilen anlamlilik-duvari ASILDI.")
    else:
        verdict = "YINE-TRADEABLE-DEGIL"
        note = ("H2b duzeltilmis-maliyette de tradeable-DEGIL -> KAPANIR, temiz-arsiv (N<=3 SON, "
                "4.tur YOK). onceden-ilan-edilen beklenti (anlamlilik-duvari, hi52-ikizi) "
                "OLCUMLE-dogrulandi; maliyet-bahanesi kalkti, kutlama-yok.")
    return {
        "verdict": verdict, "headline_variant": headline,
        "keep_bar_v1": kb_v1, "keep_bar_v2": kb_v2,
        "keep_bar_def": ("cost-after rel mean>0 AND |t|>=2 (V1 NW lag5 / V2 simple-t) AND "
                         "regime sign-stable AND survives liquid (>=1e7 ADV)"),
        "note": note,
    }


# ===========================================================================
# Orchestrator
# ===========================================================================
def run_d209(
    root: Path | str = cfg.D209_CLEAN_UNIVERSE_ROOT,
    out_path: Path | str | None = None,
    stage0_path: Path | str = _STAGE0_PATH,
    require_stage0: bool = True,
    quoted_panel: pd.DataFrame | None = None,
) -> dict:
    """Full D-209 H2b re-test. REFUSES to run unless STAGE0_d209.json exists (pre-registration).
    PORTS the frozen demo-goal detection/book; REUSES the D-204/D-207 cost harness + D-203 panel.

    `quoted_panel` (default None) is forwarded to the cost harness; injecting the D-207 EOD
    quoted-spread panel reproduces the corrected quoted-primary cost (the D-208/D-209 fix)."""
    stage0_path = Path(stage0_path)
    if require_stage0 and not stage0_path.exists():
        raise RuntimeError(
            f"Stage-0 pre-registration missing at {stage0_path}; D-209 must be frozen "
            "BEFORE results (pre-registration discipline).")

    data = eng.load_d202_panel(root)
    close, value_tl, cpi = data["close"], data["value_tl"], data["cpi"]
    idx = close.index
    daily = eng.clip_clean_returns(close)
    mkt = daily.mean(axis=1, skipna=True)
    ew = mkt.values

    px = pd.read_parquet(Path(root) / cfg.D209_PRICE_PARQUET)
    px["date"] = pd.to_datetime(px["date"])
    raw = detect_exdates(px)
    events = [(s, d, y) for (s, d, y) in raw if s in daily.columns]
    n_ev = len(events)
    n_sym = len(set(s for s, _, _ in events))
    # frozen-detection reproduction guard (demo-goal H2 lab ~1108/265 on this panel)
    if not (900 <= n_ev <= 1300 and 220 <= n_sym <= 300):
        raise RuntimeError(
            f"D-209 detection drift: {n_ev} events / {n_sym} symbols outside the frozen "
            f"demo-goal band (~1108/265). Detection must reproduce BIT-FOR-BIT.")

    # liquid-restricted event set (D-205 absolute >=1e7 ADV at the ex-date)
    liq_events = [(s, d, y) for (s, d, y) in events if liquid_at(value_tl, idx, s, d)]

    # per-stock D-207 cost panel: restrict to event symbols + the trading days the books touch
    event_syms = sorted(set(s for s, _, _ in events))
    close_ev = close[event_syms]
    value_tl_ev = value_tl[event_syms]
    cost_dates = _book_touch_dates(events, idx)
    cost = d204.per_stock_cost_panel(close_ev, value_tl_ev, cost_dates, quoted_panel=quoted_panel)
    cost_roll = cost["cost_roll"]

    v1_all = run_v1(events, daily, ew, idx, cost_roll, "ALL")
    v1_liq = run_v1(liq_events, daily, ew, idx, cost_roll, "LIQUID")
    v2_all = run_v2(events, daily, mkt, idx, cpi, cost_roll, "ALL")
    v2_liq = run_v2(liq_events, daily, mkt, idx, cpi, cost_roll, "LIQUID")

    verdict = d209_verdict(v1_all, v1_liq, v2_all, v2_liq)

    out = {
        "directive": "D-209",
        "phase": "H2b TEMETTU-RUNUP re-test (frozen demo-goal signal, D-207 corrected cost)",
        "config_version": cfg.D209_CONFIG_VERSION,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_content_hash": cfg.D209_PRICE_CONTENT_HASH,
        "candidate": cfg.D209_CANDIDATE_LABEL,
        "detection": {
            "ex_gap_min": cfg.D209_EX_GAP_MIN, "n_events": n_ev, "n_symbols": n_sym,
            "median_est_div_yield": eng._r(float(np.median([y for _, _, y in events]))),
            "n_liquid_events": len(liq_events),
            "reproduction_band": "demo-goal H2 lab ~1108 events / 265 symbols (BIREBIR)",
        },
        "cost_model": {
            "model": "D-207 per-stock realistic (Roll+Kyle, EOD-quoted-primary)",
            "quoted_injected": bool(quoted_panel is not None),
            "summary": cost["summary"],
            "note": ("FLAT 2*bp/side REPLACED by per-name round-trip rt[sym]; reduces EXACTLY "
                     "to FLAT when rt is uniform. commission Midas=0."),
        },
        "v1_daily_churn": {"ALL": v1_all, "LIQUID": v1_liq},
        "v2_discrete_capture": {"ALL": v2_all, "LIQUID": v2_liq},
        "verdict": verdict,
        "honest_framing": (
            "ONCEDEN-ilan: demo-goal FLAT 20bp/side sutununda ZATEN NW-t=0.86(ALL)/1.16(likit); "
            "20bp/side~=40bp round-trip~=D-207 duzeltilmis(~42bp). beklenti=anlamlilik-duvari "
            "(hi52-ikizi), kutlama-YOK. sonuc-ne-olursa kaydedilir. N<=3-SON."),
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=True), encoding="utf-8")
        logger.info("D-209 results written to %s", out_path)
    return out


def _book_touch_dates(events, idx):
    """Sorted set of trading days the V1 daily book and V2 entry legs touch (cost-panel rebal).

    Restricting the cost panel to these days keeps the per-(date,sym) combine loop small
    WITHOUT changing any cost value (per-name cost is looked up by exact day, and any day NOT
    in this set has no enter/exit and so is never queried). Per event, an enter lands at the
    START of its held run (earliest pos+V2_LO=-10 or pos+V1_LO=-5) and an exit at the run END+1
    (V1's last held day is pos-1 -> exit charged on the ex-date pos = pos+V1_HI+1). With
    overlapping events these boundaries can fall anywhere in [pos-10, pos]; include the whole
    inclusive span per event so every possible enter/exit day is covered exactly."""
    n = len(idx)
    lo = min(cfg.D209_V2_HOLD_LO, cfg.D209_HOLD_LO)        # widest entry offset (-10)
    hi_exit = cfg.D209_HOLD_HI + 1                          # V1 exit day offset (ex-date, 0)
    touch = set()
    for s, d, _y in events:
        pos = idx.searchsorted(d, side="left")
        if pos >= n or idx[pos] != d:
            continue
        for j in range(max(0, pos + lo), min(n, pos + hi_exit + 1)):
            touch.add(idx[j])
    return sorted(touch)

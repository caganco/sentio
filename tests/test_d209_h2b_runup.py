"""Behavior tests for the D-209 H2b TEMETTU-RUNUP harness. Synthetic, no network.

The real measurement needs the gitignored price + quoted-spread parquets (CI-absent), so
these tests exercise the PORTED frozen mechanics + the D-207 cost adaptation on small
synthetic inputs: ex-gap detection (>0.005), V1 build_holdings look-ahead-safety (held on day
t iff ex in [t+1,t+5], exit BEFORE ex), V2 discrete window never crosses the ex-date, the
FLAT-cost reduction guarantee (per-name drag == frozen FLAT when rt is uniform 2*bp/side),
cost monotonicity, the nw_tstat(lag=5) mechanic, the absolute-ADV liquid flag, the frozen
2-way verdict, and the Stage-0 pre-registration guard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.screening import d209_config as cfg
from src.screening import d209_h2b_runup as d209


# ---------------------------------------------------------------------------
# ex-date detection (tr_index_gross vs adjusted_close gap > 0.005)
# ---------------------------------------------------------------------------
def test_detect_exdates_flags_only_the_gross_minus_price_gap():
    dates = pd.bdate_range("2021-01-04", periods=4)
    # AAA: on day 3 the gross index jumps +2% while price is flat -> ex-gap ~0.02 (> 0.005).
    # BBB: gross and price move together (no dividend) -> no ex-date.
    rows = []
    tr_a = [100.0, 101.0, 102.0, 104.04]      # last step +2% gross
    px_a = [100.0, 101.0, 102.0, 102.00]      # price flat on the ex-day
    tr_b = [50.0, 50.5, 51.0, 51.51]          # +1% gross
    px_b = [50.0, 50.5, 51.0, 51.51]          # price +1% too -> gap 0
    for i, d in enumerate(dates):
        rows.append({"date": d, "symbol": "AAA", "tr_index_gross": tr_a[i], "adjusted_close": px_a[i]})
        rows.append({"date": d, "symbol": "BBB", "tr_index_gross": tr_b[i], "adjusted_close": px_b[i]})
    px = pd.DataFrame(rows)
    ev = d209.detect_exdates(px)
    syms = {s for s, _, _ in ev}
    assert syms == {"AAA"}
    s, d, y = ev[0]
    assert d == dates[3]
    assert y > cfg.D209_EX_GAP_MIN


# ---------------------------------------------------------------------------
# V1 build_holdings -- look-ahead-safe [-5,-1] window, exit BEFORE the ex-date
# ---------------------------------------------------------------------------
def test_build_holdings_holds_only_in_runup_window_and_exits_before_ex():
    idx = pd.bdate_range("2021-01-04", periods=30)
    ex_pos = 20
    events_cols = [(0, idx[ex_pos])]
    held = d209.build_holdings(events_cols, idx)        # default [-5,-1]
    # held on the five days before ex: positions 15..19
    for t in range(15, 20):
        assert 0 in held[t], f"expected held at offset {t-ex_pos}"
    # NOT held on the ex-date itself (exit before ex -> no dividend, no tax) or after
    assert 0 not in held[ex_pos]
    assert 0 not in held[ex_pos + 1]
    # NOT held before the window opens (t-6)
    assert 0 not in held[14]


# ---------------------------------------------------------------------------
# V2 discrete capture -- compound window [-10,-1] never includes the ex-date drop
# ---------------------------------------------------------------------------
def test_v2_compound_window_excludes_exdate():
    idx = pd.bdate_range("2021-01-04", periods=40)
    ex_pos = 25
    # daily returns: small positive run-up, then a huge -50% mechanical drop ON the ex-date.
    ret = np.full(40, 0.01)
    ret[ex_pos] = -0.50
    daily = pd.DataFrame({"AAA": ret}, index=idx)
    g = d209.compound_ret(daily, idx, "AAA", idx[ex_pos], cfg.D209_V2_HOLD_LO, cfg.D209_V2_HOLD_HI)
    # window is positions 15..24 (inclusive), all +1% -> (1.01)^10 - 1; the -50% ex-day excluded
    assert g == pytest.approx(1.01 ** 10 - 1.0, rel=1e-9)
    # mutating the ex-date return must NOT change the captured run-up (proves exclusion)
    ret2 = ret.copy(); ret2[ex_pos] = +9.99
    daily2 = pd.DataFrame({"AAA": ret2}, index=idx)
    g2 = d209.compound_ret(daily2, idx, "AAA", idx[ex_pos], cfg.D209_V2_HOLD_LO, cfg.D209_V2_HOLD_HI)
    assert g2 == pytest.approx(g, rel=1e-12)


# ---------------------------------------------------------------------------
# Cost adaptation -- per-name drag reduces EXACTLY to frozen FLAT when rt is uniform
# ---------------------------------------------------------------------------
def _toy_v1_inputs():
    idx = pd.bdate_range("2021-01-04", periods=30)
    rng = np.random.default_rng(7)
    a = rng.normal(0.002, 0.01, 30)
    b = rng.normal(0.001, 0.01, 30)
    daily = pd.DataFrame({"AAA": a, "BBB": b}, index=idx)
    ew = daily.mean(axis=1).values
    # AAA ex at pos 20 (held 15..19); BBB ex at pos 22 (held 17..21) -> overlap 17..19 (conc=2)
    events = [("AAA", idx[20], 0.03), ("BBB", idx[22], 0.04)]
    return events, daily, ew, idx


def _flat_v1_net_rel_mean(events, daily, ew, idx, bp_per_side):
    """Reference: the frozen edge-arastirma run_book FLAT net relative mean (per-side bp)."""
    col_of = {c: i for i, c in enumerate(daily.columns)}
    events_cols = [(col_of[s], d) for (s, d, _y) in events if s in col_of]
    daily_vals = daily.values
    n = len(idx)
    held = d209.build_holdings(events_cols, idx)
    strat_gross = np.full(n, np.nan)
    cost_turn = np.zeros(n)
    n_held = np.zeros(n, dtype=int)
    prev = set()
    for t in range(n):
        cur = held[t]; cs = set(cur); n_held[t] = len(cur)
        if cur:
            vals = daily_vals[t, cur]; vals = vals[np.isfinite(vals)]
            if len(vals):
                strat_gross[t] = float(vals.mean())
            cost_turn[t] = (len(cs - prev) + len(prev - cs)) / max(len(cur), 1)
        prev = cs
    invested = np.isfinite(strat_gross) & (n_held > 0)
    strat_net = strat_gross - cost_turn * (bp_per_side / 1e4)
    return float(np.mean((strat_net - ew)[invested]))


def test_v1_per_name_cost_reduces_to_flat_when_uniform():
    events, daily, ew, idx = _toy_v1_inputs()
    bp = 20.0
    uniform_rt = 2.0 * bp / 1e4                          # round-trip == 2*per-side
    syms = list(daily.columns)
    cost_roll = {d: {s: uniform_rt for s in syms} for d in idx}
    out = d209.run_v1(events, daily, ew, idx, cost_roll, "ALL")
    ref = _flat_v1_net_rel_mean(events, daily, ew, idx, bp)
    # net_rel_mean is rounded to 6dp (eng._r); equivalence is exact within that rounding
    assert out["net_rel_mean"] == pytest.approx(ref, abs=1e-6)
    # realized round-trip bps recovers the uniform rt (~40bp)
    assert out["realized_cost_roundtrip_bps"] == pytest.approx(2.0 * bp, rel=1e-6)


def test_v1_higher_cost_lowers_net():
    events, daily, ew, idx = _toy_v1_inputs()
    syms = list(daily.columns)
    lo = {d: {s: 0.001 for s in syms} for d in idx}
    hi = {d: {s: 0.02 for s in syms} for d in idx}
    out_lo = d209.run_v1(events, daily, ew, idx, lo, "ALL")
    out_hi = d209.run_v1(events, daily, ew, idx, hi, "ALL")
    assert out_hi["net_rel_mean"] < out_lo["net_rel_mean"]
    assert out_hi["gross_rel_mean"] == pytest.approx(out_lo["gross_rel_mean"], rel=1e-9)


# ---------------------------------------------------------------------------
# nw_tstat(lag=5) mechanic
# ---------------------------------------------------------------------------
def test_nw_tstat_short_series_returns_nan():
    t, m, n = d209.nw_tstat([0.1, -0.2, 0.3, 0.0, 0.1], lag=5)   # n=5 < lag+3=8
    assert np.isnan(t)
    assert n == 5


def test_nw_tstat_positive_mean_series_is_positive_and_finite():
    rng = np.random.default_rng(1)
    x = rng.normal(0.5, 0.1, 200)                                # strongly positive mean
    t, m, n = d209.nw_tstat(x, lag=5)
    assert np.isfinite(t) and t > 0
    assert m == pytest.approx(x.mean(), rel=1e-9)


# ---------------------------------------------------------------------------
# Absolute-ADV liquid flag (D-205 >=1e7, NOT tercile)
# ---------------------------------------------------------------------------
def test_liquid_at_absolute_threshold():
    idx = pd.bdate_range("2021-01-04", periods=80)
    value_tl = pd.DataFrame(
        {"HI": np.full(80, 5e7), "LO": np.full(80, 2e6)}, index=idx)
    d = idx[-1]
    assert d209.liquid_at(value_tl, idx, "HI", d, adv_min=1e7) is True
    assert d209.liquid_at(value_tl, idx, "LO", d, adv_min=1e7) is False
    # off-grid date -> False (look-ahead-safe, never fabricates)
    assert d209.liquid_at(value_tl, idx, "HI", pd.Timestamp("2030-01-01"), adv_min=1e7) is False


# ---------------------------------------------------------------------------
# Verdict (frozen 2-way keep-bar)
# ---------------------------------------------------------------------------
def _variant(net_rel_mean, t, sign_stable, t_key):
    return {"net_rel_mean": net_rel_mean, t_key: t,
            "regime": {"sign_stable": sign_stable}}


def test_verdict_tradeable_when_a_variant_clears_keep_bar():
    v1_all = _variant(0.004, 3.1, True, "net_rel_nw_t")
    v1_liq = _variant(0.003, 2.4, True, "net_rel_nw_t")
    v2_all = _variant(-0.001, 0.5, False, "net_rel_t")
    v2_liq = _variant(-0.001, 0.4, False, "net_rel_t")
    out = d209.d209_verdict(v1_all, v1_liq, v2_all, v2_liq)
    assert out["verdict"] == "TRADEABLE-EDGE"
    assert out["headline_variant"] == "V1"
    assert out["keep_bar_v1"]["pass"] is True


def test_verdict_closes_on_significance_wall():
    # positive after-cost rel but |t| < 2 everywhere -> significance wall (the expected case)
    v1_all = _variant(0.002, 1.1, True, "net_rel_nw_t")
    v1_liq = _variant(0.002, 1.2, True, "net_rel_nw_t")
    v2_all = _variant(0.001, 0.9, True, "net_rel_t")
    v2_liq = _variant(0.001, 0.8, True, "net_rel_t")
    out = d209.d209_verdict(v1_all, v1_liq, v2_all, v2_liq)
    assert out["verdict"] == "YINE-TRADEABLE-DEGIL"
    assert out["keep_bar_v1"]["nw_t_ge_2"] is False


def test_verdict_closes_when_liquid_does_not_survive():
    # ALL passes significance but the liquid subset does not -> not retail-tradeable
    v1_all = _variant(0.004, 3.0, True, "net_rel_nw_t")
    v1_liq = _variant(-0.001, 0.5, True, "net_rel_nw_t")
    v2_all = _variant(0.0, 0.2, False, "net_rel_t")
    v2_liq = _variant(0.0, 0.1, False, "net_rel_t")
    out = d209.d209_verdict(v1_all, v1_liq, v2_all, v2_liq)
    assert out["verdict"] == "YINE-TRADEABLE-DEGIL"
    assert out["keep_bar_v1"]["survives_liquid"] is False


# ---------------------------------------------------------------------------
# Stage-0 pre-registration guard
# ---------------------------------------------------------------------------
def test_run_d209_refuses_without_stage0(tmp_path):
    missing = tmp_path / "no_stage0.json"
    with pytest.raises(RuntimeError, match="pre-registration"):
        d209.run_d209(stage0_path=missing, require_stage0=True)

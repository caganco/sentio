"""K2 factor-tilt backtest tests (D-191). Network-free, synthetic, deterministic.

Tests BEHAVIOUR through the public functions (not private internals where avoidable):
calendar, look-ahead guard, composite = mean-of-ranks, selection counts, basket
return + turnover/cost math, equity/drawdown bounds, fair-null determinism +
matched-N, return-basis transforms, in/out split boundary, verdict gating,
additive fundamental freeze, ascii-folding, and the architecture invariant.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import k2_factor_tilt as k2
from src.screening import k2_tilt_config as cfg
from src.screening.k2_profitability import profitability_panel


# ---------------------------------------------------------------------------
# Synthetic data builders
# ---------------------------------------------------------------------------
def _close_panel(start="2018-01-01", end="2022-06-30", tickers=None, seed=7):
    tickers = tickers or [f"T{i}" for i in range(8)]
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    data = {}
    for k, t in enumerate(tickers):
        steps = rng.normal(0.0005 + k * 0.0001, 0.01 + k * 0.001, len(idx))
        data[t] = 100.0 * np.exp(np.cumsum(steps))
    close = pd.DataFrame(data, index=idx)
    xu = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.009, len(idx)))), index=idx)
    return close, xu


def _funds(tickers, fiscal_years=(2021, 2020, 2019, 2018, 2017), banks=()):
    rows = []
    for k, t in enumerate(tickers):
        is_bank = t in banks
        for yr in fiscal_years:
            rows.append({
                "ticker": t, "fiscal_year": yr,
                "period_end": f"{yr}-12-31",
                "pub_date": (pd.Timestamp(f"{yr}-12-31") + pd.Timedelta(days=120)).strftime("%Y-%m-%d"),
                "is_bank": is_bank,
                "book_eaoop": 1000.0 + 50 * k,
                "issued_capital": 100.0 + k,
                "gross_profit": None if is_bank else (200.0 + 30 * k),
                "total_assets": 2000.0 + 100 * k,
                "net_income": 80.0 + 10 * k,
            })
    return pd.DataFrame(rows, columns=k2.K2_FUND_COLS)


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------
def test_rebalance_dates_semiannual_within_window():
    close, _ = _close_panel()
    rebal = k2.rebalance_dates(close.index)
    assert len(rebal) >= 5
    assert rebal == sorted(rebal)
    assert all(pd.Timestamp(cfg.K2_WINDOW_START) <= d <= pd.Timestamp(cfg.K2_WINDOW_END) for d in rebal)
    # semi-annual: months are only June or December
    assert {d.month for d in rebal} <= {6, 12}
    # no rebalance before the window start even though data starts 2018
    assert all(d >= pd.Timestamp(cfg.K2_WINDOW_START) for d in rebal)


# ---------------------------------------------------------------------------
# Turnover + cost + basket return math
# ---------------------------------------------------------------------------
def test_turnover_bounds():
    assert k2._turnover([], ["A", "B"]) == 1.0          # initial buy
    assert k2._turnover(["A", "B"], ["A", "B"]) == 0.0   # no change
    assert k2._turnover(["A", "B"], ["C", "D"]) == pytest.approx(1.0)  # full replace
    # half replace: {A,B} -> {A,C}
    assert 0.0 < k2._turnover(["A", "B"], ["A", "C"]) <= 1.0


def test_basket_gross_equal_weight():
    idx = pd.bdate_range("2020-01-01", periods=10)
    close = pd.DataFrame({"A": np.linspace(100, 110, 10), "B": np.linspace(100, 90, 10)}, index=idx)
    g = k2._basket_gross(close, ["A", "B"], idx[0], idx[-1])
    # A: +10%, B: -10% -> equal weight ~0
    assert g == pytest.approx(((110 / 100 - 1) + (90 / 100 - 1)) / 2, abs=1e-9)


def test_period_net_subtracts_cost_and_tax():
    idx = pd.bdate_range("2020-01-01", periods=200)
    close = pd.DataFrame({"A": np.linspace(100, 120, 200), "B": np.linspace(100, 120, 200)}, index=idx)
    rebal = [idx[0], idx[-1]]
    pr = k2.period_net_returns(close, [["A", "B"]], rebal)
    assert pr["net"][0] < pr["gross"][0]                 # cost + tax drag reduce gross
    assert pr["turnover"][0] == 1.0                       # first rebalance = full buy


# ---------------------------------------------------------------------------
# Composite + selection
# ---------------------------------------------------------------------------
def _rank_dict(idx, cols, fill):
    return {k: pd.DataFrame(v, index=idx, columns=cols) for k, v in fill.items()}


def test_composite_is_mean_of_ranks():
    idx = pd.DatetimeIndex(["2020-06-30"])
    cols = ["A", "B"]
    ranks = _rank_dict(idx, cols, {
        "value": [[0.2, 0.8]], "profitability": [[0.4, 0.6]], "lowvol": [[0.6, 0.4]],
    })
    comp = k2.composite_rank(ranks, require_all=True)
    assert comp.loc["2020-06-30", "A"] == pytest.approx((0.2 + 0.4 + 0.6) / 3)
    assert comp.loc["2020-06-30", "B"] == pytest.approx((0.8 + 0.6 + 0.4) / 3)


def test_composite_require_all_nulls_missing():
    idx = pd.DatetimeIndex(["2020-06-30"])
    cols = ["A", "B"]
    ranks = _rank_dict(idx, cols, {
        "value": [[0.2, np.nan]], "profitability": [[0.4, 0.6]], "lowvol": [[0.6, 0.4]],
    })
    comp = k2.composite_rank(ranks, require_all=True)
    assert np.isnan(comp.loc["2020-06-30", "B"])         # B missing value -> excluded
    assert np.isfinite(comp.loc["2020-06-30", "A"])


def test_select_tercile_count():
    idx = pd.DatetimeIndex(["2020-06-30"])
    cols = [f"T{i}" for i in range(9)]
    comp = pd.DataFrame([np.linspace(0.05, 0.95, 9)], index=idx, columns=cols)
    basket = k2.select_basket(idx[0], comp, {}, "composite_tercile")
    assert len(basket) == 3                               # top third of 9
    assert "T8" in basket and "T0" not in basket


def test_select_intersection_needs_top_in_all():
    idx = pd.DatetimeIndex(["2020-06-30"])
    cols = ["A", "B", "C"]
    ranks = _rank_dict(idx, cols, {
        "value": [[0.9, 0.5, 0.1]], "profitability": [[0.9, 0.1, 0.5]], "lowvol": [[0.9, 0.1, 0.5]],
    })
    basket = k2.select_basket(idx[0], None, ranks, "tercile_intersection")
    assert basket == ["A"]                                # only A is top-tercile in all three


# ---------------------------------------------------------------------------
# Look-ahead guard
# ---------------------------------------------------------------------------
def test_profitability_lookahead_guard():
    tickers = ["A", "B"]
    close, _ = _close_panel(tickers=tickers)
    funds = _funds(tickers, fiscal_years=(2021,))
    # 2021 annual pub_date = 2022-04-30; a date BEFORE that must see no data
    before = pd.DatetimeIndex(["2022-01-01"])
    after = pd.DatetimeIndex(["2022-06-30"])
    pb_before = profitability_panel(funds, close, before, kind="gpa")
    pb_after = profitability_panel(funds, close, after, kind="gpa")
    assert pb_before.isna().all().all()                   # not yet published
    assert pb_after.notna().any().any()                   # published by 2022-06-30


def test_profitability_banks_gpa_null_roe_ok():
    tickers = ["A", "BANKX"]
    close, _ = _close_panel(tickers=tickers)
    funds = _funds(tickers, fiscal_years=(2020,), banks=("BANKX",))
    dates = pd.DatetimeIndex(["2021-12-31"])
    gpa = profitability_panel(funds, close, dates, kind="gpa")
    roe = profitability_panel(funds, close, dates, kind="roe")
    assert np.isnan(gpa.loc["2021-12-31", "BANKX"])       # bank GP/TA undefined
    assert np.isfinite(roe.loc["2021-12-31", "BANKX"])    # bank ROE defined (net_income/book)


# ---------------------------------------------------------------------------
# Return-basis transforms
# ---------------------------------------------------------------------------
def test_to_real_deflates():
    rebal = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31")]
    cpi = pd.Series([100.0, 110.0], index=pd.DatetimeIndex(["2020-01-01", "2020-12-31"]))
    real = k2.to_real([0.20], rebal, cpi)                 # 20% nominal, 10% inflation
    assert real[0] == pytest.approx((1.20 / 1.10) - 1.0, abs=1e-9)
    assert k2.to_real([0.20], rebal, None)[0] != k2.to_real([0.20], rebal, None)[0]  # NaN


def test_to_relative_excess_over_index():
    rebal = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31")]
    xu = pd.Series([100.0, 115.0], index=pd.DatetimeIndex(["2020-01-01", "2020-12-31"]))
    rel = k2.to_relative([0.20], rebal, xu)               # index +15%
    assert rel[0] == pytest.approx((1.20 / 1.15) - 1.0, abs=1e-9)


def test_to_usd_nominal_when_no_uscpi():
    rebal = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31")]
    fx = pd.Series([10.0, 12.0], index=pd.DatetimeIndex(["2020-01-01", "2020-12-31"]))  # TRY weakens
    usd, is_real = k2.to_usd_real([0.20], rebal, fx, None)
    assert is_real is False
    assert usd[0] == pytest.approx((1.20) * (10.0 / 12.0) - 1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Equity / drawdown
# ---------------------------------------------------------------------------
def test_max_drawdown_known():
    eq = pd.Series([1.0, 1.2, 0.9, 1.1], index=pd.bdate_range("2020-01-01", periods=4))
    # peak 1.2 -> trough 0.9 = -0.25
    assert k2.max_drawdown(eq) == pytest.approx(-0.25, abs=1e-9)
    assert k2.max_drawdown(pd.Series([1.0])) == 0.0


# ---------------------------------------------------------------------------
# Fair null: determinism + matched N
# ---------------------------------------------------------------------------
def test_fair_null_deterministic_and_matched_n():
    tickers = [f"T{i}" for i in range(10)]
    close, _ = _close_panel(tickers=tickers)
    close_ff = close.ffill()
    rebal = k2.rebalance_dates(close.index)[:4]
    cpi = pd.Series(np.linspace(100, 130, len(close_ff)), index=close_ff.index)
    pools = [tickers for _ in range(len(rebal) - 1)]
    sizes = [3 for _ in range(len(rebal) - 1)]
    a = k2.fair_random_null_portfolio(close_ff, pools, sizes, rebal, cpi, 0.05, n_resamples=200)
    b = k2.fair_random_null_portfolio(close_ff, pools, sizes, rebal, cpi, 0.05, n_resamples=200)
    assert a["random_pctile"] == b["random_pctile"]       # same seed -> identical
    assert a["pool_ok"] is True
    # pool too small for requested N -> not ok
    bad = k2.fair_random_null_portfolio(close_ff, [["T0", "T1"]], [5], rebal[:2], cpi, 0.05)
    assert bad["pool_ok"] is False


# ---------------------------------------------------------------------------
# In/out split + verdict gating
# ---------------------------------------------------------------------------
def test_split_in_out_boundary():
    rebal = [pd.Timestamp("2021-06-30"), pd.Timestamp("2022-06-30"),
             pd.Timestamp("2023-06-30"), pd.Timestamp("2024-06-30")]
    series = [0.01, 0.02, 0.03]                            # 3 periods (len rebal-1)
    res = k2.split_in_out(series, rebal)
    # insample_end=2022-12-31: periods starting 2021-06,2022-06 -> in; 2023-06 -> out
    assert res["in"]["n"] == 2
    assert res["out"]["n"] == 1


def test_verdict_passes_only_when_all_gates_true():
    good_real = {"mean": 0.03, "ci_excludes_zero": True, "ci95_low": 0.01, "n": 12}
    good_null = {"beats_fair_null_95": True}
    good_inout = {"out": {"mean": 0.02}}
    good_fac = {"any_factor_significant": True}
    v = k2.k2_verdict(good_real, good_null, good_inout, good_fac)
    assert v["passes_DEC_K2"] is True
    # flip each gate -> fails
    assert k2.k2_verdict({**good_real, "ci_excludes_zero": False}, good_null, good_inout, good_fac)["passes_DEC_K2"] is False
    assert k2.k2_verdict(good_real, {"beats_fair_null_95": False}, good_inout, good_fac)["passes_DEC_K2"] is False
    assert k2.k2_verdict(good_real, good_null, {"out": {"mean": -0.01}}, good_fac)["passes_DEC_K2"] is False
    assert k2.k2_verdict(good_real, good_null, good_inout, {"any_factor_significant": False})["passes_DEC_K2"] is False


def test_verdict_inconclusive_when_no_cpi():
    no_real = {"mean": float("nan"), "ci_excludes_zero": False, "n": 0}
    v = k2.k2_verdict(no_real, {"beats_fair_null_95": True}, {"out": {"mean": 0.02}},
                      {"any_factor_significant": True})
    assert v["passes_DEC_K2"] is False
    assert "tl_real_unavailable_INCONCLUSIVE" in v["failures"]


# ---------------------------------------------------------------------------
# Additive fundamental freeze (injected fetch -> no network)
# ---------------------------------------------------------------------------
def test_freeze_k2_fundamentals_injected(tmp_path: Path):
    def fake_fetch(ticker, fiscal_years, is_bank):
        n = len(fiscal_years)
        return {
            "book_eaoop": [1000.0] * n, "issued_capital": [100.0] * n,
            "gross_profit": [None] * n if is_bank else [200.0] * n,
            "total_assets": [2000.0] * n, "net_income": [80.0] * n,
        }
    df, meta = k2.freeze_k2_fundamentals(["AAA", "GARAN"], out_dir=tmp_path, fetch_fn=fake_fetch)
    assert list(df.columns) == k2.K2_FUND_COLS
    assert set(df["ticker"]) == {"AAA", "GARAN"}
    # GARAN is in K2_BANKS -> gross_profit NULL
    assert df[df["ticker"] == "GARAN"]["gross_profit"].isna().all()
    assert meta["content_hash"] != "empty"
    # idempotent reload returns identical hash
    _, meta2 = k2.freeze_k2_fundamentals(["AAA", "GARAN"], out_dir=tmp_path, fetch_fn=fake_fetch)
    assert meta2["content_hash"] == meta["content_hash"]


# ---------------------------------------------------------------------------
# ascii-fold
# ---------------------------------------------------------------------------
def test_ascii_fold():
    folded = k2._ascii_fold("BR" + chr(0x00DC) + "T KAR (ZARAR)")   # "BRUT KAR (ZARAR)"
    assert folded == "brut kar (zarar)"
    assert "toplam varlik" in k2._ascii_fold("Toplam Varl" + chr(0x0131) + "klar")


# ---------------------------------------------------------------------------
# End-to-end run on synthetic data (injected cpi/fx -> no network)
# ---------------------------------------------------------------------------
def test_run_k2_end_to_end_synthetic():
    tickers = [f"T{i}" for i in range(10)]
    close, xu = _close_panel(tickers=tickers)
    funds = _funds(tickers, fiscal_years=(2021, 2020, 2019, 2018, 2017))
    cpi = pd.Series(np.linspace(100, 160, len(close)), index=close.index)
    fx = pd.Series(np.linspace(6.0, 18.0, len(close)), index=close.index)
    res = k2.run_k2(close, xu, funds, cpi=cpi, fx=fx, us_cpi=None, null_resamples=100)
    assert res["directive"] == "D-191"
    assert set(res["variants"]) == set(cfg.K2_SELECTION_VARIANTS)
    prim = res["variants"][cfg.K2_PRIMARY_VARIANT]
    # per-period arrays consistent with number of periods
    assert prim["n_periods"] == len(res["rebalance_dates"]) - 1
    assert len(prim["per_period"]["net"]) == prim["n_periods"]
    assert "passes_DEC_K2" in res["verdict_DEC_K2"]
    assert res["verdict_DEC_K2"]["tl_real_available"] is True
    assert set(res["single_factor"]) == set(cfg.K2_SINGLE_FACTORS)


# ---------------------------------------------------------------------------
# Architecture invariant
# ---------------------------------------------------------------------------
def test_no_forbidden_imports_and_ascii_safe():
    import ast
    forbidden = ("signals.engine", "signals.conviction", "MASTER_WEIGHTS",
                 "backtest.engine", "signals.thresholds")
    for mod in ("k2_factor_tilt.py", "k2_profitability.py", "k2_tilt_config.py"):
        path = Path(__file__).parent.parent / "src" / "screening" / mod
        src = path.read_text(encoding="utf-8")
        # import-level check via AST (docstring mentions of these words are allowed)
        imported: list[str] = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                imported += [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                imported.append(base)
                imported += [f"{base}.{n.name}" for n in node.names]
        for bad in forbidden:
            assert not any(bad in imp for imp in imported), f"{mod} must not import {bad}"
        assert src.isascii(), f"{mod} must be ASCII-safe (cp1254/ASCII rule)"

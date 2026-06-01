"""Value-only REGIME-RESILIENCE backtest tests (D-Y1-001). Network-free, synthetic.

Behaviour tests through the public engine: look-ahead-safe E/P, value-rank
ordering, the three legs (rank-IC / decile-monotonicity / regime-resilience),
the frozen DEC-Y1 4-gate verdict logic, fair-null determinism, and the
architecture invariant (ASCII-safe + no forbidden imports).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import k2_factor_tilt as k2
from src.screening import value_only_regime as vor
from src.screening import value_only_regime_config as cfg


# ---------------------------------------------------------------------------
# Synthetic data builders
# ---------------------------------------------------------------------------
def _close_panel(start="2018-06-01", end="2021-12-31", n_tickers=12, seed=11):
    tickers = [f"T{i}" for i in range(n_tickers)]
    idx = pd.bdate_range(start, end)
    rng = np.random.default_rng(seed)
    data = {}
    for k, t in enumerate(tickers):
        steps = rng.normal(0.0005 + k * 0.00005, 0.012, len(idx))
        data[t] = 100.0 * np.exp(np.cumsum(steps))
    close = pd.DataFrame(data, index=idx)
    xu = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0.0004, 0.009, len(idx)))), index=idx)
    return close, xu


def _funds(tickers, fiscal_years=(2021, 2020, 2019, 2018, 2017)):
    rows = []
    for k, t in enumerate(tickers):
        for yr in fiscal_years:
            rows.append({
                "ticker": t, "fiscal_year": yr, "period_end": f"{yr}-12-31",
                "pub_date": (pd.Timestamp(f"{yr}-12-31") + pd.Timedelta(days=120)).strftime("%Y-%m-%d"),
                "is_bank": False,
                "book_eaoop": 1000.0 + 50 * k, "issued_capital": 100.0 + k,
                "gross_profit": 200.0 + 30 * k, "total_assets": 2000.0 + 100 * k,
                "net_income": 50.0 + 20 * k,
            })
    return pd.DataFrame(rows, columns=k2.K2_FUND_COLS)


# ---------------------------------------------------------------------------
# Look-ahead safety: E/P uses only annuals with pub_date <= signal date
# ---------------------------------------------------------------------------
def test_earnings_yield_is_point_in_time():
    funds = pd.DataFrame([
        {"ticker": "A", "fiscal_year": 2019, "period_end": "2019-12-31",
         "pub_date": "2020-04-29", "is_bank": False, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "gross_profit": 200.0, "total_assets": 2000.0,
         "net_income": 100.0},
        {"ticker": "A", "fiscal_year": 2020, "period_end": "2020-12-31",
         "pub_date": "2021-04-30", "is_bank": False, "book_eaoop": 1200.0,
         "issued_capital": 100.0, "gross_profit": 220.0, "total_assets": 2100.0,
         "net_income": 200.0},
    ], columns=k2.K2_FUND_COLS)
    dates = pd.DatetimeIndex(["2020-01-01", "2020-06-01", "2021-06-01"])
    close = pd.DataFrame({"A": [50.0, 50.0, 50.0]}, index=dates)
    ep = vor.earnings_yield(funds, close, dates, par=1.0)
    # 2020-01-01: no annual published yet -> NaN (no look-ahead)
    assert np.isnan(ep.at[dates[0], "A"])
    # 2020-06-01: only FY2019 known. mcap = (100/1)*50 = 5000 -> 100/5000 = 0.02
    assert ep.at[dates[1], "A"] == pytest.approx(0.02)
    # 2021-06-01: FY2020 now known -> 200/5000 = 0.04
    assert ep.at[dates[2], "A"] == pytest.approx(0.04)


def test_value_rank_ep_ranks_cheaper_higher():
    funds = pd.DataFrame([
        {"ticker": "A", "fiscal_year": 2019, "period_end": "2019-12-31",
         "pub_date": "2020-04-29", "is_bank": False, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "gross_profit": 200.0, "total_assets": 2000.0,
         "net_income": 100.0},   # higher E/P -> cheaper
        {"ticker": "B", "fiscal_year": 2019, "period_end": "2019-12-31",
         "pub_date": "2020-04-29", "is_bank": False, "book_eaoop": 1000.0,
         "issued_capital": 100.0, "gross_profit": 200.0, "total_assets": 2000.0,
         "net_income": 50.0},    # lower E/P -> richer
    ], columns=k2.K2_FUND_COLS)
    dates = pd.DatetimeIndex(["2020-06-01"])
    close = pd.DataFrame({"A": [50.0], "B": [50.0]}, index=dates)
    ranks = vor.value_rank_panel(funds, close, dates, kind="ep")
    assert ranks.at[dates[0], "A"] > ranks.at[dates[0], "B"]


# ---------------------------------------------------------------------------
# AYAK-3 regime_leg: boundary assignment + alignment reading
# ---------------------------------------------------------------------------
def test_regime_leg_aligned_when_all_positive():
    periods = [
        ("2019-06-30", "2019-12-31"),   # pre_surge, pre-2023
        ("2020-06-30", "2020-12-31"),   # pre_surge, pre-2023
        ("2022-06-30", "2022-12-31"),   # high_inflation, pre-2023
        ("2023-06-30", "2023-12-31"),   # high_inflation, post-2023
        ("2024-12-31", "2025-06-30"),   # disinflation, post-2023
    ]
    vals = [0.1, 0.1, 0.1, 0.1, 0.1]
    res = vor.regime_leg(vals, periods)
    assert res["primary_3way"]["n_positive_regimes"] == 3
    assert res["primary_3way"]["gate3_regime_resilient"] is True
    assert res["robustness_2way"]["both_subperiods_positive"] is True
    assert res["alignment"]["aligned"] is True


def test_regime_leg_divergent_flags_fragile():
    periods = [
        ("2019-06-30", "2019-12-31"),   # pre_surge
        ("2020-06-30", "2020-12-31"),   # pre_surge
        ("2022-06-30", "2022-12-31"),   # high_inflation, pre-2023
        ("2023-06-30", "2023-12-31"),   # high_inflation, post-2023
        ("2024-12-31", "2025-06-30"),   # disinflation, post-2023
    ]
    vals = [0.1, 0.1, 0.1, 0.1, -0.5]
    res = vor.regime_leg(vals, periods)
    # 3-way: pre_surge + high_inflation positive (>=2) -> gate3 True
    assert res["primary_3way"]["gate3_regime_resilient"] is True
    # 2-way: post-2023 dragged negative by disinflation -> not both positive
    assert res["robustness_2way"]["both_subperiods_positive"] is False
    # divergence -> regime-definition-sensitive (fragile)
    assert res["alignment"]["aligned"] is False
    assert "FRAGILE" in res["alignment"]["reading"]


# ---------------------------------------------------------------------------
# DEC-Y1 4-gate verdict logic
# ---------------------------------------------------------------------------
def _verdict_inputs(g1=True, g2=True, g3=True, g4=True, n=6):
    tilt = {"n": n, "mean": 0.05 if g1 else -0.01,
            "ci_excludes_zero": g1, "ci95_low": 0.01 if g1 else -0.02}
    null = {"beats_fair_null_95": g2}
    regime = {"primary_3way": {"gate3_regime_resilient": g3}, "alignment": {"aligned": True}}
    decile = {"gate4_decile_profile_explainable": g4}
    return tilt, null, regime, decile


def test_verdict_pass_when_all_gates_true():
    v = vor.value_only_verdict(*_verdict_inputs())
    assert v["passes_DEC_Y1"] is True
    assert v["classification"].startswith("PASS")
    assert v["failures"] == []


def test_verdict_partial_when_only_regime_fails():
    v = vor.value_only_verdict(*_verdict_inputs(g3=False))
    assert v["passes_DEC_Y1"] is False
    assert v["classification"].startswith("PARTIAL")
    assert "gate3_not_regime_resilient" in v["failures"]


def test_verdict_fail_when_tilt_not_significant():
    v = vor.value_only_verdict(*_verdict_inputs(g1=False))
    assert v["passes_DEC_Y1"] is False
    assert v["classification"].startswith("FAIL")


def test_verdict_inconclusive_when_tl_real_unavailable():
    tilt, null, regime, decile = _verdict_inputs()
    tilt = {"n": 1, "mean": None, "ci_excludes_zero": False, "ci95_low": None}
    v = vor.value_only_verdict(tilt, null, regime, decile)
    assert v["passes_DEC_Y1"] is False
    assert "tl_real_unavailable_INCONCLUSIVE" in v["failures"]


# ---------------------------------------------------------------------------
# End-to-end smoke: structure, array consistency, determinism
# ---------------------------------------------------------------------------
def test_run_value_only_regime_offline_smoke():
    close, xu = _close_panel()
    funds = _funds(list(close.columns))
    cpi = pd.Series(np.linspace(100.0, 160.0, len(close)), index=close.index)
    res = vor.run_value_only_regime(close, xu, funds, cpi=cpi, fx=None, us_cpi=None,
                                    null_resamples=50)
    assert res["directive"] == "D-Y1-001"
    assert res["single_factor_only"] is True
    prim = res["primary_value_metric"]
    assert prim["value_metric"] == cfg.VOR_VALUE_PRIMARY
    assert res["robustness_value_metric"]["value_metric"] == cfg.VOR_VALUE_ROBUST
    # per-period arrays consistent with number of periods
    t = prim["tilt_tercile"]
    assert t["n_periods"] == len(res["rebalance_dates"]) - 1
    assert len(t["per_period"]["tl_real"]) == t["n_periods"]
    # three legs present
    assert set(prim["ayak1_rank_ic"].keys()) == {str(h) for h in cfg.VOR_IC_HORIZONS}
    assert prim["ayak2_decile_monotonicity"]["n_deciles"] == cfg.VOR_N_DECILES
    assert "alignment" in prim["ayak3_regime_resilience"]
    # verdict surfaced + 4 gates
    v = res["verdict_DEC_Y1"]
    for g in ("gate1_tl_real_sig_positive", "gate2_beats_fair_null_95",
              "gate3_regime_resilient_3way", "gate4_decile_profile_explainable"):
        assert g in v
    # determinism: identical inputs/seed -> identical verdict
    res2 = vor.run_value_only_regime(close, xu, funds, cpi=cpi, fx=None, us_cpi=None,
                                     null_resamples=50)
    assert res2["verdict_DEC_Y1"] == v
    assert res2["primary_value_metric"]["tilt_tercile"]["fair_null"] == t["fair_null"]


# ---------------------------------------------------------------------------
# Architecture invariant
# ---------------------------------------------------------------------------
def test_no_forbidden_imports_and_ascii_safe():
    import ast
    forbidden = ("signals.engine", "signals.conviction", "MASTER_WEIGHTS",
                 "backtest.engine", "signals.thresholds")
    for mod in ("value_only_regime.py", "value_only_regime_config.py"):
        path = Path(__file__).parent.parent / "src" / "screening" / mod
        src = path.read_text(encoding="utf-8")
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

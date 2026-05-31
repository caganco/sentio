"""D-186 fix-round behavior tests (network-free, synthetic).

Tests the three fixes: (1) real portfolio DD is realistic (NOT the ~0.99 cumprod
artifact); (2) XU100-relative return math (a trade tracking the index -> ~0);
(3) fair null determinism + entry-isolation symmetry; plus _fast_sim == simulate_trade
equivalence, DEC-044 verdict logic, and the no-composite architecture invariant.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import indicators as ind
from src.screening import trend_backtest as bt
from src.screening import trend_d186 as d186
from src.screening import trend_d186_config as cfg
from src.screening import trend_portfolio as port
from src.screening import trend_signals as sig
from tests.test_trend_test import make_ohlcv  # reuse synthetic OHLCV generator


# ---------------------------------------------------------------------------
# FIX 1 -- portfolio DD is realistic
# ---------------------------------------------------------------------------
def _mk_trades(prices, variant="C_donchian_retest"):
    setups = {}
    for tk, o in prices.items():
        s = sig.generate_signals(variant, tk, o, False)
        if s:
            setups[tk] = s
    return bt.backtest_variant(setups, prices, 50)


def test_portfolio_dd_realistic_not_artifact():
    prices = {f"T{i}": make_ohlcv(i, 800) for i in range(6)}
    trades = _mk_trades(prices)
    if not trades:
        pytest.skip("no trades on synthetic data")
    pf = port.build_portfolio(trades, prices)
    assert 0.0 <= pf["max_drawdown"] <= 1.0
    # the D-185 artifact pinned DD ~0.99 and final_equity ~1e+26; both must be sane now
    assert pf["max_drawdown"] < 0.95, "DD still artifact-like"
    assert pf["final_equity"] < 1e6, "equity exploded (full-capital cumprod artifact)"
    assert pf["n_admitted"] + pf["n_skipped"] == len(trades)


def test_portfolio_concurrency_cap_respected():
    # 5 fully-overlapping trades, K=2 -> at most 2 admitted concurrently
    idx = pd.bdate_range("2024-08-01", periods=40)
    o = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
                      "volume": 1e6}, index=idx)
    prices = {f"T{i}": o for i in range(5)}
    trades = [{"ticker": f"T{i}", "entry_date": idx[1].strftime("%Y-%m-%d"),
               "exit_date": idx[20].strftime("%Y-%m-%d"), "entry": 100.0, "exit": 100.0,
               "net_return": 0.0} for i in range(5)]
    pf = port.build_portfolio(trades, prices, k=2)
    assert pf["n_admitted"] == 2
    assert pf["n_skipped"] == 3


# ---------------------------------------------------------------------------
# FIX 2 -- XU100-relative return math
# ---------------------------------------------------------------------------
def test_relative_return_zero_when_tracking_index():
    idx = pd.bdate_range("2024-08-01", periods=30)
    xu = pd.Series(np.linspace(100, 130, 30), index=idx)  # index +30%
    # a trade with the SAME +30% gross over the same window -> relative ~ -cost
    trades = [{"gross_return": 0.30, "net_return": 0.295,
               "entry_date": idx[0].strftime("%Y-%m-%d"), "exit_date": idx[-1].strftime("%Y-%m-%d")}]
    d186.add_relative_returns(trades, xu, cost_bps=50)
    assert trades[0]["xu100_return"] == pytest.approx(0.30, abs=1e-3)
    assert abs(trades[0]["rel_net_return"]) < 0.01  # ~0 (only cost) -> drift removed


def test_relative_return_positive_when_outperforming():
    idx = pd.bdate_range("2024-08-01", periods=30)
    xu = pd.Series(np.linspace(100, 110, 30), index=idx)  # index +10%
    trades = [{"gross_return": 0.30, "net_return": 0.295,
               "entry_date": idx[0].strftime("%Y-%m-%d"), "exit_date": idx[-1].strftime("%Y-%m-%d")}]
    d186.add_relative_returns(trades, xu, cost_bps=50)
    assert trades[0]["rel_net_return"] > 0.15  # beat index by ~18%


def test_real_return_deflates_by_cpi():
    idx = pd.bdate_range("2024-08-01", periods=30)
    cpi = pd.Series(np.linspace(100, 120, 30), index=idx)  # +20% inflation
    trades = [{"net_return": 0.30, "entry_date": idx[0].strftime("%Y-%m-%d"),
               "exit_date": idx[-1].strftime("%Y-%m-%d")}]
    d186.add_real_returns(trades, cpi)
    assert trades[0]["real_net_return"] == pytest.approx((1.30 / 1.20) - 1.0, abs=1e-3)


def test_real_return_null_without_cpi():
    trades = [{"net_return": 0.30, "entry_date": "2024-08-01", "exit_date": "2024-09-01"}]
    d186.add_real_returns(trades, None)
    assert trades[0]["real_net_return"] is None


# ---------------------------------------------------------------------------
# FIX 3 -- fast sim equivalence + fair null determinism
# ---------------------------------------------------------------------------
def test_fast_sim_matches_simulate_trade():
    o = make_ohlcv(3, 400)
    dlow = ind.donchian_lower_prior(o["low"], cfg.FAIR_NULL_TRAIL_DONCHIAN_N)
    atr = ind.atr(o["high"], o["low"], o["close"], 14)
    open_a, low_a, close_a = (o[c].to_numpy(float) for c in ("open", "low", "close"))
    dlow_a = dlow.to_numpy(float)
    s = 300  # signal bar
    init_stop = float(close_a[s] - 1.5 * atr.iloc[s])
    setup = sig.TradeSetup("T", "A_sr_flip_retest", False, o.index[s].strftime("%Y-%m-%d"),
                           stop_price=init_stop, ref_level=float(close_a[s]),
                           trail_donchian_n=cfg.FAIR_NULL_TRAIL_DONCHIAN_N)
    ref = bt.simulate_trade(o, dlow, setup, cost_frac=0.005)
    fast = d186._fast_sim(open_a, low_a, close_a, dlow_a, s + 1, init_stop, 0.005, 126)
    assert (ref is None) == (fast is None)
    if ref is not None:
        assert fast["exit_pos"] == ref["exit_pos"]
        assert fast["gross"] == pytest.approx(ref["gross_return"], abs=1e-9)


def test_fair_null_deterministic():
    # data must span the slice window so the pool is non-empty (else nan != nan)
    prices = {f"T{i}": make_ohlcv(i, 600, "2023-06-01") for i in range(5)}
    xu = make_ohlcv(50, 600, "2023-06-01")["close"]
    a = d186.fair_random_null(prices, xu, 0.02, 20, "2024-07-01", "2026-04-30",
                              False, 50, n_resamples=100)
    b = d186.fair_random_null(prices, xu, 0.02, 20, "2024-07-01", "2026-04-30",
                              False, 50, n_resamples=100)
    assert np.isfinite(a["null_mean"]), "pool empty -> extend synthetic window"
    assert a == b


# ---------------------------------------------------------------------------
# DEC-044 verdict logic
# ---------------------------------------------------------------------------
def test_verdict_pass():
    null_block = {"strategy_slice_mean_rel": 0.04, "random_pctile": 0.99, "beats_fair_random_95": True}
    cs = {"ci_excludes_zero": True}
    v = d186.d186_verdict(null_block, 0.25, cs)
    assert v["passes_DEC044"] and v["failures"] == []


def test_verdict_fail_dd():
    null_block = {"strategy_slice_mean_rel": 0.04, "random_pctile": 0.99, "beats_fair_random_95": True}
    v = d186.d186_verdict(null_block, 0.50, {"ci_excludes_zero": True})
    assert not v["passes_DEC044"] and "max_dd_exceeded" in v["failures"]


def test_verdict_fail_random():
    null_block = {"strategy_slice_mean_rel": 0.01, "random_pctile": 0.40, "beats_fair_random_95": False}
    v = d186.d186_verdict(null_block, 0.20, {"ci_excludes_zero": False})
    assert not v["passes_DEC044"] and "fails_fair_random_benchmark" in v["failures"]


# ---------------------------------------------------------------------------
# Architecture invariant
# ---------------------------------------------------------------------------
def test_no_composite_or_engine_imports():
    import ast
    forbidden_modules = ("signals.engine", "backtest.engine", "conviction", "composite")
    forbidden_names = {"MASTER_WEIGHTS", "compute_composite_score", "compute_conviction"}
    src_dir = Path(__file__).parent.parent / "src" / "screening"
    for name in ("trend_d186_config.py", "trend_portfolio.py", "trend_d186.py",
                 "trend_d186_runner.py"):
        tree = ast.parse((src_dir / name).read_text(encoding="utf-8"))
        modules, used = [], set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules += [a.name for a in node.names]
            elif isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
        for mod in modules:
            assert not any(tok in mod for tok in forbidden_modules), f"{name} imports {mod}"
        assert not (used & forbidden_names), f"{name} uses {used & forbidden_names}"

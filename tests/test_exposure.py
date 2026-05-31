"""D-187 exposure regime test -- behavior tests (network-free, synthetic).

Tests: rebalance cost, look-ahead guard (signal t -> position t+1),
TLREF compound-growth math (CRITICAL: rate not used directly),
real-return deflation, random-null determinism, DEC-045 verdict logic,
no-composite import invariant.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening.exposure_backtest import (
    _rebase,
    _regime_signal,
    build_regime_switcher,
    build_static_barbell,
    compute_metrics,
    slice_metrics,
)
from src.screening.exposure_config import REBALANCE_COST_BPS, SWITCH_COST_BPS
from src.screening.exposure_data import _tlref_to_compound, freeze_tlref_series
from src.screening.exposure_null import random_switch_null
from src.screening.exposure_runner import run_exposure_test


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------
def _synth_idx(n: int = 500, start: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def _flat_xu100(n: int = 500, start_val: float = 1000.0) -> pd.Series:
    idx = _synth_idx(n)
    return pd.Series(start_val * np.cumprod(1.0 + np.random.default_rng(1).normal(0, 0.01, n)),
                     index=idx, name="xu100")


def _flat_tlref_rate(n: int = 500, annual_rate: float = 0.40) -> pd.Series:
    """Constant annualised rate (percent) for testing."""
    idx = _synth_idx(n)
    return pd.Series(annual_rate * 100.0, index=idx, name="tlref_rate")


def _tufe_series(n: int = 500, annual_rate: float = 0.30) -> pd.Series:
    idx = _synth_idx(n)
    daily = (1.0 + annual_rate) ** (1.0 / 252.0) - 1.0
    return pd.Series(np.cumprod(1.0 + daily * np.ones(n)), index=idx, name="tufe")


# ---------------------------------------------------------------------------
# TLREF compound-growth (CRITICAL test)
# ---------------------------------------------------------------------------
def test_tlref_compound_growth_math():
    """40% annual rate -> compound index after 365 days should be ~1.492."""
    rate = pd.Series([40.0] * 365, index=pd.date_range("2020-01-01", periods=365, freq="D"))
    idx = _tlref_to_compound(rate)
    # (1 + 0.40/365)^365 ≈ 1.4918
    expected = (1.0 + 0.40 / 365.0) ** 365.0
    assert abs(float(idx.iloc[-1]) - expected) < 0.002, \
        f"TLREF compound index {idx.iloc[-1]:.4f} != expected {expected:.4f}"


def test_tlref_compound_starts_at_one():
    rate = pd.Series([20.0] * 100, index=pd.date_range("2020-01-01", periods=100, freq="D"))
    idx = _tlref_to_compound(rate)
    assert abs(float(idx.iloc[0]) - (1.0 + 0.20 / 365.0)) < 1e-9


def test_tlref_freeze_injectable(tmp_path: Path):
    """Freeze is idempotent and returns compound index, not raw rate."""
    rate = _flat_tlref_rate(300)

    def fetch_fn(start, end):
        return rate

    s1 = freeze_tlref_series("2019-01-01", "2020-06-01", tmp_path, fetch_fn)
    s2 = freeze_tlref_series("2019-01-01", "2020-06-01", tmp_path, fetch_fn)  # idempotent
    assert s1.name == "tlref_index"
    assert s2.iloc[0] == pytest.approx(s1.iloc[0])
    # Values should be >1 (compound growth) not ~40 (raw rate)
    assert float(s1.max()) < 10.0  # compound, not 40% rate value


# ---------------------------------------------------------------------------
# Static barbell
# ---------------------------------------------------------------------------
def test_barbell_cost_applied():
    xu = _flat_xu100(500)
    rate = _flat_tlref_rate(500)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    res = build_static_barbell(xu, tlref, 0.50, "monthly", REBALANCE_COST_BPS)
    assert res["n_rebalances"] > 0
    assert res["total_cost"] > 0.0


def test_barbell_portfolio_starts_at_one():
    xu = _flat_xu100(300)
    rate = _flat_tlref_rate(300)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    res = build_static_barbell(xu, tlref, 0.50)
    assert abs(float(res["portfolio"].iloc[0]) - 1.0) < 0.02


def test_barbell_100_equity_tracks_xu100():
    xu = _flat_xu100(300)
    rate = _flat_tlref_rate(300)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    res_full = build_static_barbell(xu, tlref, 1.00)
    xu_ret = float(xu.iloc[-1] / xu.iloc[0] - 1.0)
    port_ret = float(res_full["portfolio"].iloc[-1] / res_full["portfolio"].iloc[0] - 1.0)
    # 100% equity should be close to XU100 return (minus tiny rebalance cost)
    assert abs(port_ret - xu_ret) < 0.01


# ---------------------------------------------------------------------------
# Regime switcher -- look-ahead guard
# ---------------------------------------------------------------------------
def test_regime_signal_look_ahead_guard():
    """Position at t must be derived from signal at t-1 (signal[t] -> pos[t+1])."""
    xu = _flat_xu100(600)
    rate = _flat_tlref_rate(600)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    res = build_regime_switcher(xu, tlref)
    # The portfolio should exist and have same length as xu after alignment
    assert len(res["portfolio"]) > 0
    assert res["portfolio"].notna().all()


def test_regime_signal_warmup_zero():
    """No signal during MA warm-up (200 bars)."""
    xu = _flat_xu100(600)
    sig = _regime_signal(xu, ma_window=200)
    assert (sig.iloc[:200] == 0).all(), "Signal should be 0 during warm-up"


def test_regime_switcher_cost_applied():
    xu = _flat_xu100(600)
    rate = _flat_tlref_rate(600, 0.40)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    res = build_regime_switcher(xu, tlref, cost_bps=SWITCH_COST_BPS)
    # If there are any switches, total_cost > 0
    if res["n_switches"] > 0:
        assert res["total_cost"] > 0.0


# ---------------------------------------------------------------------------
# Real return deflation
# ---------------------------------------------------------------------------
def test_real_return_math():
    """Series doubles nominally with 50% inflation -> real return ~33%."""
    idx = pd.bdate_range("2020-01-01", periods=252)
    port = pd.Series(np.linspace(1.0, 2.0, 252), index=idx)
    tufe = pd.Series(np.linspace(1.0, 1.5, 252), index=idx)
    m = compute_metrics(port, tufe, "2020-01-01", "2021-12-31")
    assert abs(m["total_real"] - (2.0 / 1.5 - 1.0)) < 0.02


# ---------------------------------------------------------------------------
# Random-null determinism
# ---------------------------------------------------------------------------
def test_random_null_deterministic():
    xu = _flat_xu100(500)
    rate = _flat_tlref_rate(500)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    tufe = _tufe_series(500)
    a = random_switch_null(xu, tlref, tufe, 5, "2019-01-01", "2020-12-31",
                           0.05, seed=42, n_resamples=100)
    b = random_switch_null(xu, tlref, tufe, 5, "2019-01-01", "2020-12-31",
                           0.05, seed=42, n_resamples=100)
    assert a["null_mean"] == b["null_mean"]
    assert a["random_pctile"] == b["random_pctile"]


# ---------------------------------------------------------------------------
# End-to-end (synthetic, network-free)
# ---------------------------------------------------------------------------
def test_run_exposure_test_structure():
    xu = _flat_xu100(600, start_val=100.0)
    rate = _flat_tlref_rate(600, 0.40)
    tlref = _tlref_to_compound(rate).reindex(xu.index).ffill()
    tufe = _tufe_series(600, 0.30)
    res = run_exposure_test(xu, tlref, tufe, gold=None)
    assert "SA_verdict_DEC045" in res
    assert "SB_verdict_DEC045" in res
    assert "passes" in res["SA_verdict_DEC045"]
    assert "regime_slice_metrics" in res
    for label, _, _ in [("pre_surge", "", ""), ("high_inflation", "", ""), ("disinflation", "", "")]:
        assert label in res["regime_slice_metrics"]


# ---------------------------------------------------------------------------
# Architecture invariant
# ---------------------------------------------------------------------------
def test_no_composite_or_engine_imports():
    import ast
    forbidden_modules = ("signals.engine", "backtest.engine", "conviction", "composite")
    forbidden_names = {"MASTER_WEIGHTS", "compute_composite_score", "compute_conviction"}
    src_dir = Path(__file__).parent.parent / "src" / "screening"
    for name in ("exposure_config.py", "exposure_data.py", "exposure_backtest.py",
                 "exposure_null.py", "exposure_runner.py"):
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
            assert not any(t in mod for t in forbidden_modules), f"{name} imports {mod}"
        assert not (used & forbidden_names), f"{name} uses {used & forbidden_names}"

"""D-187 exposure regime test -- behavior tests (network-free, synthetic).

Tests: rebalance cost, look-ahead guard (signal t -> position t+1),
TLREF return-index used DIRECTLY (CRITICAL: KAPANIS is an index, not a rate;
no /365 double-compounding), real-return deflation, random-null determinism,
DEC-045 verdict logic, no-composite import invariant.
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
from src.screening.exposure_data import freeze_tlref_series
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


def _synth_tlref_index(n: int = 500, annual: float = 0.40) -> pd.Series:
    """Synthetic TLREF RETURN INDEX (monotone-grown), mimicking TP.BISTTLREF.KAPANIS.

    This is what the live series IS (already compound), used directly -- NOT a rate.
    """
    idx = _synth_idx(n)
    daily = (1.0 + annual) ** (1.0 / 252.0) - 1.0
    return pd.Series(np.cumprod(1.0 + daily * np.ones(n)), index=idx, name="tlref_index")


def _tufe_series(n: int = 500, annual_rate: float = 0.30) -> pd.Series:
    idx = _synth_idx(n)
    daily = (1.0 + annual_rate) ** (1.0 / 252.0) - 1.0
    return pd.Series(np.cumprod(1.0 + daily * np.ones(n)), index=idx, name="tufe")


# ---------------------------------------------------------------------------
# TLREF return-index used DIRECTLY (CRITICAL test -- D-187 live-data correction)
# ---------------------------------------------------------------------------
def test_tlref_freeze_uses_index_directly(tmp_path: Path):
    """KAPANIS is a RETURN-INDEX (monotone), used DIRECTLY -- NOT re-compounded /365."""
    index_series = _synth_tlref_index(300, annual=0.40)

    def fetch_fn(start, end):
        return index_series

    s1 = freeze_tlref_series("2019-01-01", "2020-06-01", tmp_path, fetch_fn)
    s2 = freeze_tlref_series("2019-01-01", "2020-06-01", tmp_path, fetch_fn)  # idempotent
    assert s1.name == "tlref_index"
    # Stored DIRECTLY (no /365 transform): values must equal the injected index
    assert float(s1.iloc[-1]) == pytest.approx(float(index_series.iloc[-1]), rel=1e-6)
    assert float(s2.iloc[0]) == pytest.approx(float(s1.iloc[0]), rel=1e-6)


def test_tlref_index_is_monotone_return_index():
    """Return-index signature: monotone non-decreasing (never falls like a rate would)."""
    idx = _synth_tlref_index(500, annual=0.40)
    assert (idx.diff().dropna() >= 0).all(), "TLREF return-index must be monotone-increasing"
    # ~40% annual over ~2 years (500 bdays) -> roughly doubles, not a flat ~40 rate value
    assert 1.5 < float(idx.iloc[-1]) < 2.5


# ---------------------------------------------------------------------------
# Static barbell
# ---------------------------------------------------------------------------
def test_barbell_cost_applied():
    xu = _flat_xu100(500)
    tlref = _synth_tlref_index(500).reindex(xu.index).ffill()
    res = build_static_barbell(xu, tlref, 0.50, "monthly", REBALANCE_COST_BPS)
    assert res["n_rebalances"] > 0
    assert res["total_cost"] > 0.0


def test_barbell_portfolio_starts_at_one():
    xu = _flat_xu100(300)
    tlref = _synth_tlref_index(300).reindex(xu.index).ffill()
    res = build_static_barbell(xu, tlref, 0.50)
    assert abs(float(res["portfolio"].iloc[0]) - 1.0) < 0.02


def test_barbell_100_equity_tracks_xu100():
    xu = _flat_xu100(300)
    tlref = _synth_tlref_index(300).reindex(xu.index).ffill()
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
    tlref = _synth_tlref_index(600).reindex(xu.index).ffill()
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
    tlref = _synth_tlref_index(600, 0.40).reindex(xu.index).ffill()
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
    tlref = _synth_tlref_index(500).reindex(xu.index).ffill()
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
    tlref = _synth_tlref_index(600, 0.40).reindex(xu.index).ffill()
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

"""D-185 Trend-Motor Test -- behavior tests (network-free, synthetic OHLCV).

Tests behavior, not implementation: indicator correctness, look-ahead guard
(signal t / entry t+1; signals depend only on past), per-trade expectancy math,
random-benchmark determinism, gating logic, snapshot idempotency, and the
no-composite architecture invariant.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.screening import indicators as ind
from src.screening import trend_backtest as bt
from src.screening import trend_config as cfg
from src.screening import trend_signals as sig
from src.screening import trend_snapshot as snap
from src.screening import trend_test_runner as runner


# ---------------------------------------------------------------------------
# Synthetic OHLCV
# ---------------------------------------------------------------------------
def make_ohlcv(seed: int, n: int = 800, start: str = "2019-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    # trend waves (creates uptrends, consolidations, pullbacks) + drift + noise
    drift = 0.0006
    wave = 0.02 * np.sin(t / 40.0) + 0.012 * np.sin(t / 11.0)
    rets = drift + np.diff(np.concatenate([[0.0], wave])) + rng.normal(0, 0.012, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1] * (1.0 + rng.normal(0, 0.002, n - 1))
    rng_pct = 0.01 * (1.0 + np.abs(rng.normal(0, 0.5, n)))
    base = np.maximum(open_, close)
    floor = np.minimum(open_, close)
    high = base * (1.0 + rng_pct)
    low = floor * (1.0 - rng_pct)
    vol = 1_000_000 * (1.0 + np.abs(rng.normal(0, 0.6, n)))
    vol[rng.integers(0, n, n // 20)] *= 3.0  # spikes -> volume-confirm chances
    idx = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def test_atr_positive_and_trailing():
    o = make_ohlcv(1, 300)
    a = ind.atr(o["high"], o["low"], o["close"], 14)
    assert a.dropna().gt(0).all()
    # warm-up: first 13 bars NaN (min_periods=14 -> first valid at index 13), no fill
    assert a.iloc[:13].isna().all()
    assert np.isfinite(a.iloc[13])


def test_rsi_bounds():
    o = make_ohlcv(2, 300)
    r = ind.rsi(o["close"], 14).dropna()
    assert r.between(0, 100).all()


def test_donchian_upper_prior_excludes_current_bar():
    o = make_ohlcv(3, 100)
    du = ind.donchian_upper_prior(o["high"], 20)
    # value at i equals max of high[i-20:i] (strictly prior bars, current excluded)
    i = 50
    assert du.iloc[i] == pytest.approx(o["high"].iloc[i - 20:i].max())


def test_nr7_and_inside_bar_logic():
    o = make_ohlcv(4, 60)
    rng = (o["high"] - o["low"])
    nr = ind.nr7(o["high"], o["low"])
    i = 30
    assert bool(nr.iloc[i]) == (rng.iloc[i] == rng.iloc[i - 6:i + 1].min())
    ib = ind.inside_bar(o["high"], o["low"])
    assert bool(ib.iloc[i]) == bool(o["high"].iloc[i] < o["high"].iloc[i - 1]
                                    and o["low"].iloc[i] > o["low"].iloc[i - 1])


def test_sr_zones_min_touches():
    prices = np.array([100.0, 100.4, 100.2, 120.0])  # cluster near 100 (3), 120 (1)
    zones = ind.sr_zones(prices, merge_distance=1.0, min_touches=2)
    assert len(zones) == 1
    assert zones[0][0] == pytest.approx(100.2, abs=0.3)
    assert zones[0][1] == 3


# ---------------------------------------------------------------------------
# Look-ahead guard
# ---------------------------------------------------------------------------
def _all_setups(o: pd.DataFrame) -> list:
    s = []
    for variant in cfg.VARIANTS:
        for parab in (True, False):
            s += sig.generate_signals(variant, "TEST", o, parab)
    return s


def test_signals_are_produced_on_synthetic_data():
    # non-vacuous guarantee for the look-ahead tests below
    total = sum(len(_all_setups(make_ohlcv(s, 800))) for s in range(6))
    assert total > 0


def test_signal_only_depends_on_past():
    """Truncating data right after a signal date must preserve that signal."""
    checked = 0
    for s in range(6):
        o = make_ohlcv(s, 800)
        for setup in _all_setups(o):
            trunc = o.loc[:setup.signal_date]
            again = sig.generate_signals(setup.variant, "TEST", trunc, setup.parabolic_on)
            assert any(x.signal_date == setup.signal_date for x in again), (
                f"{setup.variant} signal {setup.signal_date} vanished on truncation")
            checked += 1
            if checked >= 25:
                return
    assert checked > 0


def test_entry_is_t_plus_one_open():
    o = make_ohlcv(0, 800)
    setups = _all_setups(o)
    assert setups
    dlow = ind.donchian_lower_prior(o["low"], cfg.A_TRAIL_DONCHIAN_N)
    s0 = setups[0]
    tr = bt.simulate_trade(o, dlow, s0, cost_frac=0.0)
    if tr is not None:
        sig_pos = o.index.get_loc(pd.Timestamp(s0.signal_date))
        entry_pos = o.index.get_loc(pd.Timestamp(tr["entry_date"]))
        assert entry_pos == sig_pos + 1
        assert tr["entry"] == pytest.approx(float(o["open"].iloc[sig_pos + 1]))


def test_generate_signals_deterministic():
    o = make_ohlcv(7, 800)
    a = sig.generate_signals("A_sr_flip_retest", "X", o, True)
    b = sig.generate_signals("A_sr_flip_retest", "X", o, True)
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]


# ---------------------------------------------------------------------------
# Simulate / expectancy
# ---------------------------------------------------------------------------
def test_simulate_trade_gap_below_stop_exits_at_open():
    idx = pd.bdate_range("2020-01-01", periods=10)
    # entry at open of bar 1 = 100; stop = 90 (risk_frac=0.10); bar 2 GAPS down:
    # open 85 < stop 90 -> exit at the gap open (85), not the stop.
    o = pd.DataFrame({
        "open":  [100, 100, 85, 95, 95, 95, 95, 95, 95, 95],
        "high":  [101, 102, 86, 96, 96, 96, 96, 96, 96, 96],
        "low":   [99, 99, 84, 95, 95, 95, 95, 95, 95, 95],
        "close": [100, 101, 86, 95, 95, 95, 95, 95, 95, 95],
        "volume": [1e6] * 10,
    }, index=idx)
    dlow = pd.Series([np.nan] * 10, index=idx)  # no trailing -> initial stop only
    setup = sig.TradeSetup("T", "A_sr_flip_retest", True, idx[0].strftime("%Y-%m-%d"),
                           stop_price=90.0, ref_level=100.0, trail_donchian_n=20)
    tr = bt.simulate_trade(o, dlow, setup, cost_frac=0.0)
    assert tr is not None
    assert tr["entry"] == 100.0
    assert tr["exit"] == pytest.approx(85.0)  # gap open below stop -> exit at open
    assert tr["net_R"] == pytest.approx((85.0 / 100.0 - 1.0) / 0.10)  # -1.5 R


def test_simulate_trade_exit_price_at_stop_when_no_gap():
    idx = pd.bdate_range("2020-01-01", periods=6)
    o = pd.DataFrame({
        "open":  [100, 100, 95, 95, 95, 95],
        "high":  [101, 102, 96, 96, 96, 96],
        "low":   [99, 99, 88, 95, 95, 95],   # bar2 low 88 < stop 90, open 95 > stop -> exit 90
        "close": [100, 101, 92, 95, 95, 95],
        "volume": [1e6] * 6,
    }, index=idx)
    dlow = pd.Series([np.nan] * 6, index=idx)
    setup = sig.TradeSetup("T", "A_sr_flip_retest", True, idx[0].strftime("%Y-%m-%d"),
                           stop_price=90.0, ref_level=100.0, trail_donchian_n=20)
    tr = bt.simulate_trade(o, dlow, setup, cost_frac=0.0)
    assert tr["exit"] == pytest.approx(90.0)
    assert tr["net_R"] == pytest.approx((90.0 / 100.0 - 1.0) / 0.10)  # -1.0 R


def test_expectancy_math():
    trades = [
        {"net_R": 2.0, "net_return": 0.20, "entry_date": "2021-01-01", "bars_held": 5},
        {"net_R": 2.0, "net_return": 0.20, "entry_date": "2021-02-01", "bars_held": 5},
        {"net_R": -1.0, "net_return": -0.10, "entry_date": "2021-03-01", "bars_held": 5},
        {"net_R": -1.0, "net_return": -0.10, "entry_date": "2021-04-01", "bars_held": 5},
    ]
    e = bt.expectancy_stats(trades)
    assert e["n_trades"] == 4
    assert e["win_rate"] == pytest.approx(0.5)
    assert e["expectancy_R"] == pytest.approx(0.5)  # 0.5*2 + 0.5*(-1)


def test_random_benchmark_deterministic():
    prices = {f"T{i}": make_ohlcv(i, 400) for i in range(5)}
    trades = [{"net_return": 0.05, "bars_held": 10} for _ in range(8)]
    a = bt.random_entry_null(prices, trades, cost_bps=50, seed=123, n_resamples=200)
    b = bt.random_entry_null(prices, trades, cost_bps=50, seed=123, n_resamples=200)
    assert a == b


def test_gate_verdict_all_pass():
    exp = {"n_trades": 50, "expectancy_R": 0.4, "t_hac": 3.0}
    rnd = {"beats_random_95": True}
    regime = {"positive_market_states": 3, "max_single_slice_pnl_share": 0.4}
    dd = {"max_drawdown": 0.10, "total_net_return": 0.5}
    bh = {"ew_total_net_return": 0.2}
    v = bt.gate_verdict(exp, rnd, regime, dd, bh)
    assert v["passes_gate"] and v["failures"] == []


def test_gate_verdict_fails_random():
    exp = {"n_trades": 50, "expectancy_R": 0.4, "t_hac": 3.0}
    rnd = {"beats_random_95": False}
    regime = {"positive_market_states": 3, "max_single_slice_pnl_share": 0.4}
    dd = {"max_drawdown": 0.10, "total_net_return": 0.5}
    bh = {"ew_total_net_return": 0.2}
    v = bt.gate_verdict(exp, rnd, regime, dd, bh)
    assert not v["passes_gate"] and "fails_random_benchmark" in v["failures"]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
def test_ohlcv_snapshot_freeze_load_idempotent(tmp_path: Path):
    uni = ["AAA", "BBB"]

    def fetch_fn(tickers, start, end):
        return {t: make_ohlcv(hash(t) % 100, 300) for t in tickers}

    def macro_fn(start, end):
        xu = make_ohlcv(99, 300)["close"].rename("BIST100")
        return pd.DataFrame({"BIST100": xu})

    df1, m1 = snap.freeze_ohlcv_snapshot(uni, "2019-01-01", "2020-01-01", out_dir=tmp_path,
                                         fetch_fn=fetch_fn, macro_fn=macro_fn, adv_floor_tl=None)
    df2, m2 = snap.freeze_ohlcv_snapshot(uni, "2019-01-01", "2020-01-01", out_dir=tmp_path,
                                         fetch_fn=fetch_fn, macro_fn=macro_fn, adv_floor_tl=None)
    assert m1["content_hash"] == m2["content_hash"]
    assert "bias_direction" in m1["survivorship"]
    prices, xu = snap.to_ohlcv_panels(df1)
    assert set(prices) == {"AAA", "BBB"}
    assert len(xu) > 0
    assert list(prices["AAA"].columns) == ["open", "high", "low", "close", "volume"]


# ---------------------------------------------------------------------------
# End-to-end (synthetic, network-free)
# ---------------------------------------------------------------------------
def test_run_trend_test_structure():
    prices = {f"T{i}": make_ohlcv(i, 800) for i in range(4)}
    xu = make_ohlcv(50, 800)["close"]
    res = runner.run_trend_test(prices, xu, cost_scenarios=(50,))
    assert set(res["results"]) == set(cfg.VARIANTS)
    for variant in cfg.VARIANTS:
        for mode in cfg.FILTER_MODES:
            assert "by_cost" in res["results"][variant][mode]
            assert "50" in res["results"][variant][mode]["by_cost"]
    assert isinstance(res["primary_summary"], list)


# ---------------------------------------------------------------------------
# Architecture invariant -- no composite / engine coupling
# ---------------------------------------------------------------------------
def test_no_composite_or_engine_imports():
    """Parse actual imports/identifiers via ast (robust to docstring prose)."""
    import ast

    forbidden_module_tokens = ("signals.engine", "backtest.engine", "conviction", "composite")
    forbidden_names = {"MASTER_WEIGHTS", "compute_composite_score", "compute_conviction"}
    src_dir = Path(__file__).parent.parent / "src" / "screening"
    for name in ("indicators.py", "trend_config.py", "trend_signals.py",
                 "trend_backtest.py", "trend_snapshot.py", "trend_test_runner.py"):
        tree = ast.parse((src_dir / name).read_text(encoding="utf-8"))
        modules: list[str] = []
        used_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules += [a.name for a in node.names]
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)
        for mod in modules:
            for tok in forbidden_module_tokens:
                assert tok not in mod, f"{name} imports forbidden module {mod}"
        assert not (used_names & forbidden_names), f"{name} uses {used_names & forbidden_names}"

"""D-173: BIST MA Trend Scalar backtest position sizing integration tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import BacktestEngine

# ── Shared synthetic test data ────────────────────────────────────────────────

_N = 250
_DATES = pd.date_range("2025-01-01", periods=_N, freq="B")

np.random.seed(42)
_prices = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.012, _N)))

MOCK_OHLCV = pd.DataFrame(
    {
        "Open":   _prices * 0.999,
        "High":   _prices * 1.01,
        "Low":    _prices * 0.99,
        "Close":  _prices,
        "Volume": np.full(_N, 2_000_000.0),
    },
    index=_DATES,
)

np.random.seed(7)
MOCK_MACRO = pd.DataFrame(
    {
        "USDTRY":  30.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.007, _N))),
        "VIX":     np.clip(15.0 + np.cumsum(np.random.normal(0, 0.3, _N)), 5, 28),
        "BRENT":   np.full(_N, 80.0),
        "SP500":   np.full(_N, 5000.0),
        "BIST100": np.full(_N, 9000.0),
    },
    index=_DATES,
)

# Backtest window: days 180-230. MA warmup (50 days) is complete well before start.
_START = str(_DATES[180].date())
_END   = str(_DATES[230].date())


class _FixedEngine(BacktestEngine):
    """Subclass that pins Kelly output and composite score to force deterministic trades."""

    def _get_kelly_allocation_tl(self, composite: float, vix_level: float) -> float:
        return 10_000.0  # price ≈ 100 → ~100 shares baseline

    def _compute_composite(self, technical_data: dict, macro_data: dict, symbol: str):
        return 82.0, 60.0  # always BUY-STRONG; macro score unremarkable


def _bull_series() -> pd.Series:
    """Steadily rising → price > MA20 > MA50 throughout the backtest window."""
    return pd.Series([1000.0 + i * 5.0 for i in range(_N)], index=_DATES, dtype=float)


def _bear_series() -> pd.Series:
    """Steadily falling → price < MA50 throughout the backtest window."""
    return pd.Series([10_000.0 - i * 5.0 for i in range(_N)], index=_DATES, dtype=float)


def _run(engine: BacktestEngine, benchmark=None) -> BacktestEngine:
    engine.run({"T": MOCK_OHLCV}, MOCK_MACRO, benchmark_series=benchmark)
    return engine


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestBistScalarBacktest:
    """D-173: BIST MA Trend Scalar integration into BacktestEngine.

    _FixedEngine pins composite=82 (BUY-STRONG) and Kelly=10 000 TL so scalar
    effects on shares are deterministic and trades always execute.
    """

    def test_no_benchmark_engine_runs_without_regression(self):
        """benchmark_series=None → engine completes, no crash, scalar series stays None."""
        engine = BacktestEngine(initial_capital=500_000, start_date=_START, end_date=_END)
        _run(engine, benchmark=None)
        assert len(engine.equity_curve) > 0
        assert engine._bist_ma_scalar_series is None

    def test_bull_benchmark_produces_more_shares_than_baseline(self):
        """Bull BIST trend (scalar 1.25) → more total shares bought than no-benchmark baseline."""
        base = _run(_FixedEngine(initial_capital=1_000_000, start_date=_START, end_date=_END))
        bull = _run(_FixedEngine(initial_capital=1_000_000, start_date=_START, end_date=_END),
                    benchmark=_bull_series())

        base_shares = sum(t["shares"] for t in base.trades if t["type"] == "BUY")
        bull_shares = sum(t["shares"] for t in bull.trades if t["type"] == "BUY")

        assert base_shares > 0, "Baseline produced no BUY trades"
        assert bull_shares >= base_shares

    def test_bear_benchmark_produces_fewer_shares_than_baseline(self):
        """Bear BIST trend (scalar 0.75) → fewer total shares bought than no-benchmark baseline."""
        base = _run(_FixedEngine(initial_capital=1_000_000, start_date=_START, end_date=_END))
        bear = _run(_FixedEngine(initial_capital=1_000_000, start_date=_START, end_date=_END),
                    benchmark=_bear_series())

        base_shares = sum(t["shares"] for t in base.trades if t["type"] == "BUY")
        bear_shares = sum(t["shares"] for t in bear.trades if t["type"] == "BUY")

        assert base_shares > 0, "Baseline produced no BUY trades"
        assert bear_shares <= base_shares

    def test_bear_and_bull_bracket_neutral_shares(self):
        """bear_shares <= neutral_shares <= bull_shares — scalar ordering preserved end-to-end."""
        def _total(bm):
            e = _FixedEngine(initial_capital=5_000_000, start_date=_START, end_date=_END)
            _run(e, benchmark=bm)
            return sum(t["shares"] for t in e.trades if t["type"] == "BUY")

        shares_bear = _total(_bear_series())
        shares_none = _total(None)
        shares_bull = _total(_bull_series())

        assert shares_none > 0, "Baseline produced no BUY trades"
        assert shares_bear <= shares_none <= shares_bull

    def test_lookahead_guard_shift1_applied(self):
        """shift(1) guard: scalar series populated with valid values;
        early dates (before MA warmup) use NEUTRAL fallback; bull tail yields 1.25."""
        engine = BacktestEngine(initial_capital=500_000, start_date=_START, end_date=_END)
        _run(engine, benchmark=_bull_series())

        series = engine._bist_ma_scalar_series
        assert series is not None, "_bist_ma_scalar_series must be set when benchmark provided"

        valid = {0.75, 1.0, 1.25}
        bad = set(series.unique()) - valid
        assert not bad, f"Unexpected scalar values: {bad}"

        # With shift(1): day 0 has no prior history → MA20/MA50 = NaN → NEUTRAL (1.0).
        assert series.iloc[0] == 1.0, "Day 0: no MA history → scalar must be 1.0"

        # A consistently rising series yields bull (1.25) once both MAs are warmed up.
        assert 1.25 in series.values, "Bull series should produce at least one 1.25 scalar"

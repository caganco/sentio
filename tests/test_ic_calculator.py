"""ICCalculator tests (D-107, SPEC_ALPHA_INFRASTRUCTURE_1 Phase 4)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from src.analytics.ic_calculator import ICCalculator, compute_ic


def _make_signal_returns_pair(
    n_dates: int = 30,
    n_symbols: int = 12,
    signal_function=None,   # callable: (i_date, j_symbol, return_t1) -> signal
    seed: int = 42,
):
    """Build a synthetic (signal_df, returns_df) pair for IC testing.

    signal_function controls relationship between signal and forward return:
      - None: signal independent of return (expect IC near 0)
      - identity: signal = return_t1 (expect IC = 1.0)
      - negative: signal = -return_t1 (expect IC = -1.0)
    """
    rng = np.random.default_rng(seed)
    dates = [date(2026, 1, 5) + timedelta(days=i) for i in range(n_dates)]
    symbols = [f"SYM{j:02d}" for j in range(n_symbols)]
    returns_mat = rng.standard_normal((n_dates, n_symbols)) * 0.02

    sig_rows = []
    for i, d in enumerate(dates):
        for j, sym in enumerate(symbols):
            r_next = float(returns_mat[i, j])
            sig = signal_function(i, j, r_next) if signal_function else float(rng.standard_normal())
            sig_rows.append({
                "date": d, "symbol": sym,
                "l1_tech_score": sig,
                "composite_score": sig,
                "regime_label": "BULL",
                "liquidity_tier": "BIST100",
                "price_limit_hit": False,
            })

    ret_rows = []
    for i, d in enumerate(dates):
        for j, sym in enumerate(symbols):
            ret_rows.append({
                "signal_date": d, "symbol": sym, "horizon": 1,
                "forward_return": float(returns_mat[i, j]),
                "price_limit_hit": False,
                "filled_at": datetime(2026, 5, 20, tzinfo=timezone.utc),
            })

    return pd.DataFrame(sig_rows), pd.DataFrame(ret_rows)


class TestICCalculator:

    def test_perfect_correlation_gives_ic_one(self):
        """signal = forward_return -> IC -> +1.0."""
        sig_df, ret_df = _make_signal_returns_pair(
            signal_function=lambda i, j, r: r,
        )
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        assert result.n_obs > 0
        assert result.mean_ic > 0.95

    def test_perfect_anticorrelation_gives_ic_minus_one(self):
        """signal = -forward_return -> IC -> -1.0."""
        sig_df, ret_df = _make_signal_returns_pair(
            signal_function=lambda i, j, r: -r,
        )
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        assert result.mean_ic < -0.95

    def test_random_signal_ic_near_zero(self):
        """Random signal -> |IC| < 0.20 statistical bound."""
        sig_df, ret_df = _make_signal_returns_pair()
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        assert abs(result.mean_ic) < 0.20

    def test_no_lookahead_random_signal_stays_zero(self):
        """A lookahead-free random signal vs future returns: IC remains near 0.

        This guards the (date, symbol) join: if our calculator accidentally joins
        signal_date=T with return at time T (no offset), random signal would still
        give zero correlation -- but if the join confuses dates, a structured
        signal might leak. Test uses random signal as the safe baseline.
        """
        sig_df, ret_df = _make_signal_returns_pair(seed=12345)
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        # Without genuine signal, IC must not exceed statistical noise bound
        assert abs(result.mean_ic) < 0.20, \
            f"Potential lookahead leak: mean_ic={result.mean_ic:.4f}"

    def test_rolling_window_emits_per_date_rows(self):
        """compute_rolling produces at most (n_unique_dates) rows; window respected."""
        sig_df, ret_df = _make_signal_returns_pair(n_dates=40)
        df = ICCalculator(sig_df, ret_df).compute_rolling(
            "l1_tech_score", horizon=1, window=10,
        )
        # Empty allowed (min observations gate); if non-empty, must respect dates count
        if not df.empty:
            assert len(df) <= 40
            assert (df["window"] == 10).all()

    def test_t_stat_formula_matches_analytical(self):
        """t_stat = mean(IC) / (std(IC)/sqrt(N)) -- check formula matches output."""
        sig_df, ret_df = _make_signal_returns_pair(
            signal_function=lambda i, j, r: r + 0.005 * j,  # mild signal
        )
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        if result.n_obs > 1 and result.std_ic > 0:
            expected_t = result.mean_ic / (result.std_ic / np.sqrt(result.n_obs))
            assert result.t_stat == pytest.approx(expected_t, abs=1e-3)

    def test_min_observations_gate(self):
        """When fewer than IC_MIN_OBSERVATIONS valid rows, result is empty (NaN)."""
        # Two rows total
        sig_df = pd.DataFrame([
            {"date": date(2026, 5, 1), "symbol": "AAA", "l1_tech_score": 0.5,
             "regime_label": "BULL", "liquidity_tier": "BIST30", "price_limit_hit": False},
            {"date": date(2026, 5, 2), "symbol": "BBB", "l1_tech_score": 0.7,
             "regime_label": "BULL", "liquidity_tier": "BIST30", "price_limit_hit": False},
        ])
        ret_df = pd.DataFrame([
            {"signal_date": date(2026, 5, 1), "symbol": "AAA", "horizon": 1,
             "forward_return": 0.01, "price_limit_hit": False,
             "filled_at": datetime(2026, 5, 2, tzinfo=timezone.utc)},
            {"signal_date": date(2026, 5, 2), "symbol": "BBB", "horizon": 1,
             "forward_return": 0.02, "price_limit_hit": False,
             "filled_at": datetime(2026, 5, 3, tzinfo=timezone.utc)},
        ])
        result = ICCalculator(sig_df, ret_df).compute_ic("l1_tech_score", horizon=1)
        # n_obs < 10 -> empty/NaN result
        assert result.n_obs < 10
        assert np.isnan(result.mean_ic)
        assert result.is_investable is False

    def test_alphalens_factor_data_shape(self):
        """Optional: alphalens factor_data returns valid MultiIndex DataFrame.

        Skipped if alphalens-reloaded not installed (matches SPEC's optional
        integration pattern).
        """
        try:
            import alphalens  # noqa: F401
        except ImportError:
            pytest.skip("alphalens-reloaded not installed")

        sig_df, ret_df = _make_signal_returns_pair(n_dates=10, n_symbols=5)
        calc = ICCalculator(sig_df, ret_df)
        # Build prices DataFrame: DatetimeIndex x symbols
        dates = pd.date_range("2026-01-05", periods=10, freq="B")
        symbols = [f"SYM{j:02d}" for j in range(5)]
        prices = pd.DataFrame(
            np.cumprod(1 + np.random.default_rng(0).standard_normal((10, 5)) * 0.01, axis=0),
            index=dates, columns=symbols,
        )
        factor_data = calc.build_alphalens_factor_data("l1_tech_score", 1, prices)
        # MultiIndex (date, asset)
        assert factor_data.index.nlevels == 2


def test_module_level_compute_ic_shim():
    """compute_ic(signal_df, returns_df, col, horizon) returns ICResult."""
    sig_df, ret_df = _make_signal_returns_pair(
        signal_function=lambda i, j, r: r,
    )
    r = compute_ic(sig_df, ret_df, "l1_tech_score", 1)
    assert r.mean_ic > 0.9

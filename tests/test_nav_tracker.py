"""Tests for D-143 NAV Discount Tracker (nav_calculator + nav_zscore).

Coverage:
  TestHoldingsYaml   -- yaml parse, missing file, unknown ticker
  TestNAVCalculator  -- Tier-1 NAV computation with mocked yfinance
  TestNAVZScore      -- z-score computation, 5 signal zones, COLLECTING
  TestNAVAlerts      -- Kademe-1 / Kademe-2 threshold boundary checks
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml

from src.analytics.nav_calculator import NAVCalculator, NAVDataError
from src.analytics.nav_zscore import NAV_MIN_OBS_SIGNAL, NAVZScoreTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_holdings(path: Path, net_cash: float = 0.0) -> None:
    """Write minimal holdings.yaml with 2 KCHOL subsidiaries for tests."""
    data = {
        "kchol": {
            "source": "test",
            "last_verified": "2026-01-01",
            "listed_subsidiaries": [
                {"ticker": "FROTO.IS", "stake_pct": 0.387, "note": "test"},
                {"ticker": "YKBNK.IS", "stake_pct": 0.202, "note": "test"},
            ],
            "net_cash_holdco_tl": net_cash,
            "private_book_value_tl": 0.0,
        }
    }
    path.write_text(yaml.dump(data), encoding="utf-8")


def _make_mock_ticker(last_price: float, shares: float, market_cap: float) -> MagicMock:
    """Return a mock yfinance Ticker whose fast_info contains the given values."""
    mock = MagicMock()
    mock.fast_info = {
        "last_price": last_price,
        "shares": shares,
        "market_cap": market_cap,
    }
    return mock


def _write_nav_history(
    path: Path,
    ticker: str,
    n_days: int,
    discount_base: float = 0.30,
    slope: float = 0.0,
) -> None:
    """Write synthetic nav_history.parquet with deterministic discount series."""
    rows = []
    for i in range(n_days):
        disc = discount_base + slope * i
        rows.append(
            {
                "date": date(2025, 1, 1) + timedelta(days=i),
                "ticker": ticker,
                "nav_per_share": 300.0,
                "price": 300.0 * (1 - disc),
                "discount_pct": disc,
                "mean_252d": float("nan"),
                "std_252d": float("nan"),
                "z_score": float("nan"),
                "signal": "COLLECTING",
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False, compression="snappy")


# ---------------------------------------------------------------------------
# TestHoldingsYaml
# ---------------------------------------------------------------------------

class TestHoldingsYaml:

    def test_holdings_yaml_parse(self, tmp_path):
        """holdings.yaml loads and contains required fields."""
        hp = tmp_path / "holdings.yaml"
        _write_holdings(hp)
        calc = NAVCalculator(holdings_path=str(hp))
        cfg = calc._load_holdings("KCHOL")
        assert "listed_subsidiaries" in cfg
        assert len(cfg["listed_subsidiaries"]) == 2
        assert cfg["listed_subsidiaries"][0]["ticker"] == "FROTO.IS"
        assert cfg["listed_subsidiaries"][0]["stake_pct"] == pytest.approx(0.387)

    def test_holdings_yaml_missing_raises(self, tmp_path):
        """Missing holdings.yaml raises FileNotFoundError."""
        calc = NAVCalculator(holdings_path=str(tmp_path / "nonexistent.yaml"))
        with pytest.raises(FileNotFoundError, match="holdings.yaml bulunamadi"):
            calc._load_holdings("KCHOL")

    def test_holdings_yaml_unknown_ticker_raises(self, tmp_path):
        """Unknown ticker key in holdings.yaml raises KeyError."""
        hp = tmp_path / "holdings.yaml"
        _write_holdings(hp)
        calc = NAVCalculator(holdings_path=str(hp))
        with pytest.raises(KeyError, match="bulunamadi"):
            calc._load_holdings("UNKNOWN")


# ---------------------------------------------------------------------------
# TestNAVCalculator
# ---------------------------------------------------------------------------

class TestNAVCalculator:

    def test_tier1_nav_returns_expected_keys(self, tmp_path):
        """compute_tier1_nav result dict has all required keys."""
        hp = tmp_path / "holdings.yaml"
        _write_holdings(hp)
        calc = NAVCalculator(holdings_path=str(hp))

        universal_mock = _make_mock_ticker(100.0, 1_000_000.0, 5_000_000.0)
        with patch("src.analytics.nav_calculator.yf.Ticker", return_value=universal_mock):
            result = calc.compute_tier1_nav("KCHOL")

        required = {
            "ticker", "nav_per_share", "price", "discount_pct",
            "listed_subs_value", "net_cash", "shares_outstanding", "source_date",
        }
        assert required.issubset(result.keys())

    def test_tier1_nav_compute_discount(self, tmp_path):
        """compute_tier1_nav returns correct discount_pct with mocked yfinance.

        Setup:
          FROTO.IS market_cap=100M, stake=38.7% -> 38.7M contribution
          YKBNK.IS market_cap= 50M, stake=20.2% -> 10.1M contribution
          listed_subs_value = 48.8M
          shares = 200_000
          nav_per_share = 48_800_000 / 200_000 = 244
          price = 150
          discount = 1 - 150/244 = ~38.5%
        """
        hp = tmp_path / "holdings.yaml"
        _write_holdings(hp)
        calc = NAVCalculator(holdings_path=str(hp))

        parent_mock = _make_mock_ticker(150.0, 200_000.0, 0.0)
        froto_mock = _make_mock_ticker(0.0, 0.0, 100_000_000.0)
        ykbnk_mock = _make_mock_ticker(0.0, 0.0, 50_000_000.0)

        def ticker_factory(sym: str):
            if sym == "KCHOL.IS":
                return parent_mock
            if sym == "FROTO.IS":
                return froto_mock
            return ykbnk_mock

        with patch("src.analytics.nav_calculator.yf.Ticker", side_effect=ticker_factory):
            result = calc.compute_tier1_nav("KCHOL")

        expected_listed = 100e6 * 0.387 + 50e6 * 0.202
        expected_nav = expected_listed / 200_000
        expected_disc = 1 - 150.0 / expected_nav

        assert result["ticker"] == "KCHOL"
        assert result["price"] == pytest.approx(150.0, abs=0.01)
        assert result["listed_subs_value"] == pytest.approx(expected_listed, rel=1e-4)
        assert result["nav_per_share"] == pytest.approx(expected_nav, rel=1e-4)
        assert result["discount_pct"] == pytest.approx(expected_disc, abs=0.001)

    def test_tier1_nav_net_cash_included(self, tmp_path):
        """net_cash_holdco_tl from yaml is added to NAV."""
        hp = tmp_path / "holdings.yaml"
        _write_holdings(hp, net_cash=10_000_000.0)  # 10M TL net cash
        calc = NAVCalculator(holdings_path=str(hp))

        parent_mock = _make_mock_ticker(100.0, 100_000.0, 0.0)
        sub_mock = _make_mock_ticker(0.0, 0.0, 0.0)  # subs contribute 0

        def ticker_factory(sym: str):
            return parent_mock if sym == "KCHOL.IS" else sub_mock

        with patch("src.analytics.nav_calculator.yf.Ticker", side_effect=ticker_factory):
            result = calc.compute_tier1_nav("KCHOL")

        # nav_per_share = (0 + 10_000_000) / 100_000 = 100
        assert result["nav_per_share"] == pytest.approx(100.0, rel=1e-3)
        assert result["net_cash"] == pytest.approx(10_000_000.0, rel=1e-3)


# ---------------------------------------------------------------------------
# TestNAVZScore
# ---------------------------------------------------------------------------

class TestNAVZScore:

    def _make_nav_result(
        self, ticker: str = "KCHOL", disc: float = 0.30,
        price: float = 100.0, nav: float = 143.0,
    ) -> dict:
        return {"ticker": ticker, "discount_pct": disc, "price": price, "nav_per_share": nav}

    # --- Signal label unit tests (no parquet I/O needed) ---

    def test_signal_buy(self, tmp_path):
        """z > 2.0 -> BUY."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(2.5, 100) == "BUY"

    def test_signal_buy_lean(self, tmp_path):
        """1.0 < z <= 2.0 -> BUY-LEAN."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(1.5, 100) == "BUY-LEAN"

    def test_signal_hold(self, tmp_path):
        """-1.0 <= z <= +1.0 -> HOLD."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(0.0, 100) == "HOLD"

    def test_signal_trim(self, tmp_path):
        """-2.0 < z < -1.0 -> TRIM."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(-1.5, 100) == "TRIM"

    def test_signal_avoid(self, tmp_path):
        """z < -2.0 -> AVOID."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(-2.5, 100) == "AVOID"

    def test_signal_collecting_low_obs(self, tmp_path):
        """< 60 observations -> COLLECTING regardless of z-score."""
        tracker = NAVZScoreTracker(history_path=str(tmp_path / "h.parquet"))
        assert tracker._signal_label(5.0, NAV_MIN_OBS_SIGNAL - 1) == "COLLECTING"
        assert tracker._signal_label(float("nan"), 0) == "COLLECTING"

    # --- Integration: compute from synthetic history ---

    def test_zscore_computed_from_history(self, tmp_path):
        """Z-score is non-NaN and positive when today's discount > historical mean.

        Uses slope=0.001 so discount varies 0.30..0.40 over 100 days,
        giving std > 0 and a well-defined z-score.
        today's disc=0.50 is above the mean (~0.35) -> z > 0.
        """
        hp = tmp_path / "nav_history.parquet"
        _write_nav_history(hp, "KCHOL", n_days=100, discount_base=0.30, slope=0.001)

        tracker = NAVZScoreTracker(history_path=str(hp))
        result = tracker.update(
            self._make_nav_result(disc=0.50), as_of_date=date(2026, 5, 20)
        )

        assert result["signal"] != "COLLECTING"
        assert not np.isnan(result["z_score"])
        assert result["z_score"] > 0  # 0.50 > mean ~0.35

    def test_append_only_idempotency(self, tmp_path):
        """Same date+ticker written twice -> no duplicate row in parquet."""
        hp = tmp_path / "nav_history.parquet"
        tracker = NAVZScoreTracker(history_path=str(hp))
        today = date(2026, 5, 24)

        tracker.update(self._make_nav_result(), as_of_date=today)
        tracker.update(self._make_nav_result(), as_of_date=today)  # second write

        df = pd.read_parquet(hp)
        dupes = df[
            (df["ticker"] == "KCHOL") & (df["date"].astype(str) == str(today))
        ]
        assert len(dupes) == 1  # exactly one row, not two


# ---------------------------------------------------------------------------
# TestNAVAlerts
# ---------------------------------------------------------------------------

class TestNAVAlerts:

    def test_kademe1_boundary(self):
        """NAV_DISCOUNT_KADEME1_KAPATMA == 0.30: discount 0.25 is below boundary."""
        from src.signals.thresholds import NAV_DISCOUNT_KADEME1_KAPATMA
        assert NAV_DISCOUNT_KADEME1_KAPATMA == pytest.approx(0.30)
        assert 0.25 < NAV_DISCOUNT_KADEME1_KAPATMA  # triggers TRIM/KAPATMA alert

    def test_kademe2_boundary(self):
        """NAV_DISCOUNT_KADEME2_ALIM == 0.45: discount 0.50 is above boundary."""
        from src.signals.thresholds import NAV_DISCOUNT_KADEME2_ALIM
        assert NAV_DISCOUNT_KADEME2_ALIM == pytest.approx(0.45)
        assert 0.50 > NAV_DISCOUNT_KADEME2_ALIM  # triggers EK ALIM alert

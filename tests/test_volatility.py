"""
Test: src.risk.volatility — RR-016 §5.1 Sanity Tests + unit tests.
D-147: Vol-targeting Faz 1 (Gözlem Modu).
"""
import math
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.risk.volatility import (
    compute_vol_scalar,
    realized_vol_portfolio,
    vol_contribution,
)
from src.signals.thresholds import VOL_SCALAR_CAP, VOL_SCALAR_FLOOR


class TestRealizedVolTicker:
    """realized_vol_ticker: yfinance mock ile birim testler."""

    def test_constant_price_returns_zero(self):
        """Sabit fiyat serisi → log return std = 0 → σ = 0.0 (Sanity: sabit getiri)."""
        from src.risk.volatility import realized_vol_ticker

        mock_df = pd.DataFrame(
            {"Close": [100.0] * 25},
            index=pd.date_range("2024-01-01", periods=25),
        )
        with patch("yfinance.download", return_value=mock_df):
            result = realized_vol_ticker("TEST", lookback=20)
        assert result == 0.0

    def test_known_std_annualizes_correctly(self):
        """Bilinen günlük std → yıllık vol = daily_std × sqrt(252), makul aralıkta."""
        from src.risk.volatility import realized_vol_ticker

        np.random.seed(42)
        log_returns = np.random.normal(0, 0.01, 25)  # daily std ≈ 1%
        prices = 100.0 * np.exp(np.cumsum(log_returns))
        mock_df = pd.DataFrame(
            {"Close": prices},
            index=pd.date_range("2024-01-01", periods=25),
        )
        with patch("yfinance.download", return_value=mock_df):
            result = realized_vol_ticker("TEST", lookback=20)
        # Yaklaşık %15–20 yıllık vol bekliyoruz (0.01 × sqrt(252) ≈ 0.159)
        assert 0.05 < result < 1.0

    def test_empty_data_returns_zero(self):
        """Boş DataFrame → 0.0 (güvenli fallback)."""
        from src.risk.volatility import realized_vol_ticker

        with patch("yfinance.download", return_value=pd.DataFrame()):
            result = realized_vol_ticker("TEST", lookback=20)
        assert result == 0.0

    def test_insufficient_data_returns_zero(self):
        """Tek satır veri → shift sonrası return yok → 0.0."""
        from src.risk.volatility import realized_vol_ticker

        mock_df = pd.DataFrame(
            {"Close": [100.0]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        with patch("yfinance.download", return_value=mock_df):
            result = realized_vol_ticker("TEST", lookback=20)
        assert result == 0.0


class TestRealizedVolPortfolio:
    """realized_vol_portfolio: korelasyonsuz yaklaşım testleri."""

    def test_single_holding_weight_one(self):
        """Tek hisse, ağırlık=1 → portfolio_vol = ticker_vol."""
        with patch("src.risk.volatility.realized_vol_ticker", return_value=0.30):
            result = realized_vol_portfolio({"TTKOM": 1.0}, lookback=20)
        assert abs(result - 0.30) < 1e-9

    def test_equal_weight_two_holdings(self):
        """İki eşit ağırlıklı hisse (w=0.5 her biri), σ=0.30 → korelasyonsuz toplam."""
        with patch("src.risk.volatility.realized_vol_ticker", return_value=0.30):
            result = realized_vol_portfolio({"A": 0.5, "B": 0.5}, lookback=20)
        expected = math.sqrt(0.5 ** 2 * 0.30 ** 2 + 0.5 ** 2 * 0.30 ** 2)
        assert abs(result - expected) < 1e-9

    def test_empty_holdings_returns_zero(self):
        """Boş holdings → 0.0."""
        assert realized_vol_portfolio({}) == 0.0

    def test_portfolio_vol_less_than_max_ticker_vol(self):
        """Korelasyonsuz yaklaşımda port vol < en yüksek ticker vol (diversifikasyon etkisi)."""
        side_effects = [0.50, 0.30, 0.20]
        call_count = [0]

        def mock_ticker_vol(ticker, lookback=20):
            val = side_effects[call_count[0]]
            call_count[0] += 1
            return val

        with patch("src.risk.volatility.realized_vol_ticker", side_effect=mock_ticker_vol):
            result = realized_vol_portfolio(
                {"ENERY": 0.16, "TTKOM": 0.20, "KCHOL": 0.18}, lookback=20
            )
        # Portföy vol, ENERY'nin 0.50'sinden küçük olmalı
        assert result < 0.50


class TestVolContribution:
    """vol_contribution: normalize katkı oranı testleri."""

    def test_enery_critical_threshold(self):
        """ENERY §9.4: 0.16 × 0.50 / 0.20 = 0.40 → tam eşik (kritik bulgu)."""
        result = vol_contribution("ENERY", 0.16, 0.50, 0.20)
        assert abs(result - 0.40) < 1e-9

    def test_zero_port_sigma_returns_zero(self):
        """Port sigma = 0 → sıfıra bölme koruması → 0.0."""
        assert vol_contribution("X", 0.5, 0.3, 0.0) == 0.0

    def test_contribution_proportional_to_weight(self):
        """Ağırlık iki katına çıkınca katkı iki katına çıkar."""
        c1 = vol_contribution("X", 0.10, 0.30, 0.20)
        c2 = vol_contribution("X", 0.20, 0.30, 0.20)
        assert abs(c2 - 2 * c1) < 1e-9


class TestVolScalar:
    """compute_vol_scalar: clip testleri (RR-016 §5.1 Sanity Tests 1–4)."""

    def test_vol_scalar_cap(self):
        """Sanity Test 2: σ=0.05 (düşük vol) → clip üst sınır = VOL_SCALAR_CAP (1.50)."""
        result = compute_vol_scalar(realized_vol=0.05)
        assert result == VOL_SCALAR_CAP

    def test_vol_scalar_floor(self):
        """Sanity Test 3: σ=0.75 (COVID), target=0.15 → 0.20 (floor)."""
        result = compute_vol_scalar(realized_vol=0.75)
        assert result == VOL_SCALAR_FLOOR

    def test_vol_scalar_normal(self):
        """Sanity Test 1: σ=0.30, target=0.15 → 0.50."""
        result = compute_vol_scalar(realized_vol=0.30, target_vol=0.15)
        assert abs(result - 0.50) < 1e-9

    def test_vol_scalar_at_target(self):
        """Sanity Test 4: σ = target → scalar = 1.00."""
        result = compute_vol_scalar(realized_vol=0.15, target_vol=0.15)
        assert abs(result - 1.0) < 1e-9

    def test_vol_scalar_zero_realized_returns_cap(self):
        """σ = 0 → sıfıra bölme koruması → CAP döner."""
        result = compute_vol_scalar(realized_vol=0.0)
        assert result == VOL_SCALAR_CAP

    def test_vol_scalar_always_in_range(self):
        """Her gerçekçi vol için sonuç [FLOOR, CAP] aralığında."""
        for vol in [0.0, 0.01, 0.15, 0.30, 0.50, 1.0, 2.0]:
            result = compute_vol_scalar(vol)
            assert VOL_SCALAR_FLOOR <= result <= VOL_SCALAR_CAP

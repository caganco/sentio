"""ADX computation tests for build_technical_data() — D-156.

Mevcut data_loader testleri tests/test_backtest.py::TestDataLoader'da.
Bu dosya SADECE ADX-spesifik testleri içerir.
"""
from __future__ import annotations

import pandas as pd

from src.backtest.data_loader import build_technical_data

# ── Test fixtures ─────────────────────────────────────────────────────────────
_DATES_250 = pd.date_range("2024-01-01", periods=250, freq="B")

MOCK_OHLCV_250 = pd.DataFrame(
    {
        "Open":   [99.5  + i * 0.05 for i in range(250)],
        "High":   [101.0 + i * 0.05 for i in range(250)],
        "Low":    [98.5  + i * 0.05 for i in range(250)],
        "Close":  [100.0 + i * 0.05 for i in range(250)],
        "Volume": [1_000_000] * 250,
    },
    index=_DATES_250,
)

_DATES_20 = pd.date_range("2024-01-01", periods=20, freq="B")

MOCK_OHLCV_20 = pd.DataFrame(
    {
        "Open":   [99.5  + i * 0.05 for i in range(20)],
        "High":   [101.0 + i * 0.05 for i in range(20)],
        "Low":    [98.5  + i * 0.05 for i in range(20)],
        "Close":  [100.0 + i * 0.05 for i in range(20)],
        "Volume": [1_000_000] * 20,
    },
    index=_DATES_20,
)

_AS_OF_250 = _DATES_250[200]   # 201 rows available — well above 28 threshold
_AS_OF_20  = _DATES_20[19]     # 20 rows — below 28 threshold


class TestADXComputation:
    """14-period Wilder ADX, build_technical_data() output — D-156."""

    def test_adx_key_present_and_float(self):
        """>28-günlük veri → 'adx' anahtarı mevcut ve float."""
        result = build_technical_data(MOCK_OHLCV_250, _AS_OF_250)
        assert result is not None
        assert "adx" in result
        assert isinstance(result["adx"], float)

    def test_adx_none_on_insufficient_data(self):
        """20-günlük veri (< 28 min) → adx=None; dict döner (None değil)."""
        result = build_technical_data(MOCK_OHLCV_20, _AS_OF_20)
        assert result is not None          # dict döner (14 RSI gereksinimi karşılandı)
        assert result["adx"] is None       # ADX warmup yetersiz → None

    def test_adx_value_in_valid_range(self):
        """ADX değeri 0-100 arasında (Wilder formülü invariant)."""
        result = build_technical_data(MOCK_OHLCV_250, _AS_OF_250)
        assert result is not None
        adx = result["adx"]
        assert adx is not None
        assert 0.0 <= adx <= 100.0

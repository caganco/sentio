"""L1 ADX-based regime-aware sub-score weighting tests — D-155.

5 test:
  TestL1RegimeAwareWeighting (5)
    - test_trend_regime_promotes_ma_momentum
    - test_range_regime_promotes_rsi
    - test_transition_regime_stores_regime_in_detail
    - test_no_adx_defaults_to_transition_regime
    - test_all_regime_weight_dicts_sum_to_one

Kısıtlar:
  - Sub-score hesaplama fonksiyonları değişmedi — sadece ağırlıklar
  - Canlı API çağrısı yok (unit test)
  - adx=None → transition → basit ortalama (geriye dönük uyumluluk)

Dayanak: D-155 SPEC (ADX rejim-aware L1 ağırlıklandırma)
Not: D-156 ADX data feed ekleyene kadar production'da adx=None → transition.
"""
from __future__ import annotations

import pytest

from src.signals.layers.technical_layer import score_technical
from src.signals.thresholds import (
    L1_WEIGHTS_RANGE,
    L1_WEIGHTS_TRANSITION,
    L1_WEIGHTS_TREND,
)


def _data(**overrides) -> dict:
    """Default neutral technical_data; override any key with kwargs."""
    base = {
        "rsi":               50.0,
        "close":            100.0,
        "ma20":              95.0,
        "ma50":              90.0,
        "ma200":             85.0,
        "momentum_score":     0.0,
        "volume_surge":     False,
        "proximity_52w_high": 0.10,
        "adx":               None,
    }
    base.update(overrides)
    return base


class TestL1RegimeAwareWeighting:
    """ADX-conditional sub-score weighting — 3 senaryo: trend/range/transition (D-155)."""

    def test_trend_regime_promotes_ma_momentum(self):
        """ADX=30 (TREND): MA×0.40 + mom×0.30 dominant → score > transition when MA/mom bullish.

        Test durumu:
          RSI=85 → extreme_overbought → 10.0 (bearish, küçük ağırlık ister)
          MA: close(100) > ma20(95), ma50(90), ma200(85) → 3/3 → 80.0
          momentum=0.5 → (0.5+1)/2×100 = 75.0
          volume_surge=True → 65.0
          proximity=0.02 → price_ratio=0.98 > 0.95 → 70.0

        TREND:      80×0.40 + 75×0.30 + 65×0.15 + 70×0.10 + 10×0.05 = 71.75
        TRANSITION: (80+75+65+70+10)/5 = 60.0 → trend_score > transition_score ✓
        """
        trend_data = _data(
            adx=30.0, rsi=85.0, close=100.0,
            ma20=95.0, ma50=90.0, ma200=85.0,
            momentum_score=0.5, volume_surge=True, proximity_52w_high=0.02,
        )
        transition_data = _data(
            adx=22.0, rsi=85.0, close=100.0,
            ma20=95.0, ma50=90.0, ma200=85.0,
            momentum_score=0.5, volume_surge=True, proximity_52w_high=0.02,
        )
        trend_result      = score_technical(trend_data)
        transition_result = score_technical(transition_data)
        assert trend_result.score > transition_result.score
        assert trend_result.detail["regime"] == "trend"

    def test_range_regime_promotes_rsi(self):
        """ADX=15 (RANGE): RSI×0.40 dominant → score > transition when RSI oversold + MA bearish.

        Test durumu:
          RSI=28 → oversold → 65.0 (bullish mean-reversion sinyali)
          MA: close(80) < ma20(90), ma50(95), ma200(100) → 0/3 → 20.0 (bearish)
          momentum=-0.1 → (-0.1+1)/2×100 = 45.0
          volume=False → 50.0
          proximity=0.20 → price_ratio=0.80 < 0.95, 0.20 > 0.05 → 50.0

        RANGE:      65×0.40 + 50×0.20 + 50×0.15 + 20×0.15 + 45×0.10 = 50.0
        TRANSITION: (65+20+45+50+50)/5 = 46.0 → range_score >= transition_score ✓
        """
        range_data = _data(
            adx=15.0, rsi=28.0, close=80.0,
            ma20=90.0, ma50=95.0, ma200=100.0,
            momentum_score=-0.1, volume_surge=False, proximity_52w_high=0.20,
        )
        transition_data = _data(
            adx=22.0, rsi=28.0, close=80.0,
            ma20=90.0, ma50=95.0, ma200=100.0,
            momentum_score=-0.1, volume_surge=False, proximity_52w_high=0.20,
        )
        range_result      = score_technical(range_data)
        transition_result = score_technical(transition_data)
        assert range_result.score >= transition_result.score
        assert range_result.detail["regime"] == "range"

    def test_transition_regime_stores_regime_in_detail(self):
        """ADX=22 (TRANSITION): detail['regime']=='transition', detail['adx']==22."""
        result = score_technical(_data(adx=22.0))
        assert result.detail["regime"] == "transition"
        assert result.detail["adx"] == 22.0

    def test_no_adx_defaults_to_transition_regime(self):
        """adx anahtarı yok → transition; score adx=22 ile aynı (geriye dönük uyumluluk).

        D-156 ADX data feed ekleyene kadar production adx=None → transition mod.
        Mevcut test_engine.py::TestTechnicalLayer fixture'ları adx içermiyor
        — bu test backward-compat'ı garanti eder.
        """
        data_no_adx    = _data(adx=None)
        data_transition = _data(adx=22.0)
        no_adx_result    = score_technical(data_no_adx)
        transition_result = score_technical(data_transition)
        assert no_adx_result.detail["regime"] == "transition"
        assert no_adx_result.score == transition_result.score

    def test_all_regime_weight_dicts_sum_to_one(self):
        """Her 3 rejim ağırlık dict'i toplamı 1.0 (thresholds.py invariant)."""
        assert sum(L1_WEIGHTS_TREND.values())      == pytest.approx(1.0, abs=1e-9)
        assert sum(L1_WEIGHTS_RANGE.values())      == pytest.approx(1.0, abs=1e-9)
        assert sum(L1_WEIGHTS_TRANSITION.values()) == pytest.approx(1.0, abs=1e-9)

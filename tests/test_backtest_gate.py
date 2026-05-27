"""D-166: Macro Gate binary removal — crisis-only entry block.

4 test (TestMacroGateCrisisOnly):
  - test_vix_panic_blocks_entry        VIX=40 > 35 → gated=True
  - test_elevated_vix_does_not_block   VIX=28 < 35 → gated=False
  - test_usdtry_spike_blocks_entry     USDTRY=0.04 > 0.03 → gated=True
  - test_low_l2_no_longer_blocks       VIX=25, L2_benzer → gated=False (L2 gate kaldirildi)

Kisitlar:
  - _is_entry_gated_by_macro() dogrudan test edilir (public davranis)
  - Canli API yok (unit test)
  - Macro Gate V2 scaling mantigi bu testin kapsaminda degil

Dayanak: D-166 SPEC (BACKTEST_MACRO_CRISIS_VIX=35.0, BACKTEST_MACRO_CRISIS_USDTRY_SPIKE=0.03)
"""
from __future__ import annotations

import pytest

from src.backtest.engine import BacktestEngine
from src.signals.thresholds import (
    BACKTEST_MACRO_CRISIS_USDTRY_SPIKE,
    BACKTEST_MACRO_CRISIS_VIX,
)


@pytest.fixture
def engine() -> BacktestEngine:
    return BacktestEngine()


class TestMacroGateCrisisOnly:
    """D-166: Sadece VIX panigi ve EM stresi girisi engeller — L2 skor gate kaldirildi."""

    def test_vix_panic_blocks_entry(self, engine: BacktestEngine) -> None:
        """VIX=40 > BACKTEST_MACRO_CRISIS_VIX(35) → gated=True."""
        snap = {"vix_level": 40.0, "USDTRY_1d_change": 0.001}
        assert engine._is_entry_gated_by_macro(snap) is True

    def test_elevated_vix_does_not_block(self, engine: BacktestEngine) -> None:
        """VIX=28 < 35 → gated=False (elevated ama kriz degil, Macro Gate V2 kucultuer)."""
        snap = {"vix_level": 28.0, "USDTRY_1d_change": 0.001}
        assert engine._is_entry_gated_by_macro(snap) is False

    def test_usdtry_spike_blocks_entry(self, engine: BacktestEngine) -> None:
        """USDTRY_1d_change=0.04 > BACKTEST_MACRO_CRISIS_USDTRY_SPIKE(0.03) → gated=True."""
        snap = {"vix_level": 20.0, "USDTRY_1d_change": 0.04}
        assert engine._is_entry_gated_by_macro(snap) is True

    def test_low_l2_no_longer_blocks(self, engine: BacktestEngine) -> None:
        """VIX=25, USDTRY normal → gated=False. L2<45 binary gate kaldirildi (D-166)."""
        snap = {"vix_level": 25.0, "USDTRY_1d_change": 0.005}
        assert engine._is_entry_gated_by_macro(snap) is False

    def test_crisis_vix_threshold_constant(self) -> None:
        """BACKTEST_MACRO_CRISIS_VIX sabiti 35.0 (panic threshold)."""
        assert BACKTEST_MACRO_CRISIS_VIX == 35.0

    def test_crisis_usdtry_threshold_constant(self) -> None:
        """BACKTEST_MACRO_CRISIS_USDTRY_SPIKE sabiti 0.03 (%3/gun EM stress)."""
        assert BACKTEST_MACRO_CRISIS_USDTRY_SPIKE == 0.03

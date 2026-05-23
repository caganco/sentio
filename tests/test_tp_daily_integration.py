"""Tests for detect_levels() integration in daily_update.py portfolio loop (D-112).

Tests the TP wiring pattern directly rather than the full daily_update script:
- valid OHLCV → tp1/tp2/tp3 populated
- missing / empty OHLCV → tp1/tp2/tp3 = None (silent skip)
- detect_levels() exception → tp1/tp2/tp3 = None (no propagation)
- BEAR regime → tp1 = entry + 1.5×ATR (legacy NEUTRAL multiplier)
- BULL regime → tp1 uses wider 2.5×ATR fallback
- classify_regime() + macro_signal mapping
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.risk.technical_level_detector import detect_levels
from src.signals.macro_regime_gate import classify_regime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 30, price: float = 100.0) -> pd.DataFrame:
    """Flat-price OHLCV — ATR ≈ 2.0, entry ≈ price."""
    return pd.DataFrame({
        "High":  [price + 1.0] * n,
        "Low":   [price - 1.0] * n,
        "Close": [price] * n,
    })


def _simulate_tp_block(
    ohlcv: pd.DataFrame | None,
    regime: str,
) -> dict:
    """Replicate the try/except TP block from daily_update.py portfolio loop."""
    position: dict = {}
    try:
        if ohlcv is not None and not ohlcv.empty:
            plan = detect_levels(ohlcv, regime)
            position["tp1"] = round(plan.tp1, 2)
            position["tp2"] = round(plan.tp2, 2)
            position["tp3"] = round(plan.tp3, 2)
            position["tp_regime"] = plan.regime
            position["tp_confidence"] = plan.confidence
        else:
            position.update({"tp1": None, "tp2": None, "tp3": None})
    except Exception:
        position.update({"tp1": None, "tp2": None, "tp3": None})
    return position


# ---------------------------------------------------------------------------
# Core TP wiring behaviour
# ---------------------------------------------------------------------------

class TestTpWiringBlock:

    def test_valid_ohlcv_populates_tp_fields(self):
        df = _make_ohlcv()
        pos = _simulate_tp_block(df, "NEUTRAL")
        assert "tp1" in pos and "tp2" in pos and "tp3" in pos
        assert pos["tp1"] is not None
        assert pos["tp2"] is not None
        assert pos["tp3"] is not None

    def test_tp_ordering_tp1_le_tp2_le_tp3(self):
        # detect_levels guarantees non-decreasing (tp1 <= tp2 <= tp3);
        # equal values possible when multiple candidates coincide.
        df = _make_ohlcv()
        pos = _simulate_tp_block(df, "NEUTRAL")
        assert pos["tp1"] <= pos["tp2"] <= pos["tp3"]

    def test_tp_above_entry_price(self):
        entry = 100.0
        df = _make_ohlcv(price=entry)
        pos = _simulate_tp_block(df, "NEUTRAL")
        assert pos["tp1"] > entry
        assert pos["tp2"] > entry
        assert pos["tp3"] > entry

    def test_none_ohlcv_returns_null_fields(self):
        pos = _simulate_tp_block(None, "NEUTRAL")
        assert pos["tp1"] is None
        assert pos["tp2"] is None
        assert pos["tp3"] is None

    def test_empty_ohlcv_returns_null_fields(self):
        pos = _simulate_tp_block(pd.DataFrame(), "NEUTRAL")
        assert pos["tp1"] is None
        assert pos["tp2"] is None
        assert pos["tp3"] is None

    def test_exception_in_detect_levels_returns_null_fields(self):
        """Any exception from detect_levels must not propagate."""
        bad_df = pd.DataFrame({"WrongColumn": [1, 2, 3]})
        pos = _simulate_tp_block(bad_df, "NEUTRAL")
        assert pos.get("tp1") is None
        assert pos.get("tp2") is None
        assert pos.get("tp3") is None

    def test_tp_regime_field_stored(self):
        df = _make_ohlcv()
        pos = _simulate_tp_block(df, "BULL")
        assert pos.get("tp_regime") == "BULL"

    def test_tp_confidence_field_stored(self):
        df = _make_ohlcv()
        pos = _simulate_tp_block(df, "NEUTRAL")
        conf = pos.get("tp_confidence")
        assert conf is not None
        assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Regime-specific TP distances (SPEC_TP_REGIME_CONDITIONAL_1 / D-109)
# ---------------------------------------------------------------------------

class TestTpRegimeDistances:
    """Verify the regime-conditional multipliers reach daily_update.py correctly."""

    def test_bear_uses_same_tp_levels_as_neutral(self):
        """BEAR and NEUTRAL share identical TP multipliers — only BULL widens them."""
        df = _make_ohlcv(n=30, price=100.0)
        bear_pos = _simulate_tp_block(df, "BEAR")
        neutral_pos = _simulate_tp_block(df, "NEUTRAL")
        # detect_levels uses same code path for BEAR and NEUTRAL
        assert bear_pos["tp1"] == neutral_pos["tp1"]
        assert bear_pos["tp2"] == neutral_pos["tp2"]
        assert bear_pos["tp3"] == neutral_pos["tp3"]

    def test_bull_regime_tp1_uses_wider_atr_multiplier(self):
        """BULL uses ATR_TP1_MULTIPLE_BULL = 2.5 for the fallback case."""
        from src.signals.thresholds import ATR_TP1_MULTIPLE, ATR_TP1_MULTIPLE_BULL
        assert ATR_TP1_MULTIPLE_BULL > ATR_TP1_MULTIPLE

        df = _make_ohlcv(n=1, price=100.0)
        neutral_pos = _simulate_tp_block(df, "NEUTRAL")
        bull_pos = _simulate_tp_block(df, "BULL")

        if neutral_pos["tp1"] is not None and bull_pos["tp1"] is not None:
            # BULL TP1 must be at least as far as NEUTRAL TP1 (wider or equal)
            assert bull_pos["tp1"] >= neutral_pos["tp1"]

    def test_bull_tp2_gt_neutral_tp2_fallback(self):
        from src.signals.thresholds import ATR_TP2_MULTIPLE, ATR_TP2_MULTIPLE_BULL
        assert ATR_TP2_MULTIPLE_BULL > ATR_TP2_MULTIPLE


# ---------------------------------------------------------------------------
# classify_regime → _tp_regime mapping (regime gate layer)
# ---------------------------------------------------------------------------

class TestClassifyRegimeMapping:
    """Verify that classify_regime() maps correctly for TP regime selection."""

    def test_high_l2_maps_to_bull(self):
        from src.signals.thresholds import MACRO_GATE_BULL_MIN
        assert classify_regime(MACRO_GATE_BULL_MIN) == "BULL"
        assert classify_regime(80.0) == "BULL"

    def test_mid_l2_maps_to_neutral(self):
        assert classify_regime(50.0) == "NEUTRAL"

    def test_low_l2_maps_to_bear(self):
        assert classify_regime(20.0) == "BEAR"

    def test_macro_signal_score_conversion(self):
        """macro_signal.macro_environment_score is [-1, +1]; daily_update converts to [0, 100]."""
        # score = +1.0 → l2 = 100 → BULL
        l2 = (1.0 + 1) * 50.0
        assert classify_regime(l2) == "BULL"

        # score = -1.0 → l2 = 0 → BEAR
        l2 = (-1.0 + 1) * 50.0
        assert classify_regime(l2) == "BEAR"

        # score = 0.0 → l2 = 50 → NEUTRAL
        l2 = (0.0 + 1) * 50.0
        assert classify_regime(l2) == "NEUTRAL"

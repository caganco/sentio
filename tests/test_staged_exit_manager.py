"""Tests for the staged exit manager (SPEC_STAGED_TP_1, D-052)."""
import pytest

from src.order_engine.staged_exit_manager import (
    STAGE_TP1,
    STAGE_TP2,
    STAGE_TP3,
    evaluate_exit,
)
from src.risk.technical_level_detector import LevelPlan
from src.signals.thresholds import TP1_PCT_EXIT, TP2_PCT_EXIT, TP3_PCT_EXIT

LEVELS = LevelPlan(
    entry_price=100.0,
    tp1=110.0,
    tp2=125.0,
    tp3=150.0,
    tp1_type="pivot_r1",
    tp2_type="fib_0.618",
    tp3_type="fib_1.618",
    support_1=95.0,
    support_2=90.0,
    confidence=0.9,
)


def _stages(ev):
    return {e.stage for e in ev.exits}


class TestLadder:
    def test_tp1_fires_at_level(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=111.0,
            highest_price_since_entry=111.0, days_held=1,
            days_since_new_high=0, conviction_score=0.70,
            regime="BULL", levels=LEVELS,
        )
        assert STAGE_TP1 in _stages(ev)
        tp1 = next(e for e in ev.exits if e.stage == STAGE_TP1)
        assert tp1.pct_of_position == TP1_PCT_EXIT

    def test_tp2_requires_profit_over_15pct(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=126.0,
            highest_price_since_entry=126.0, days_held=4,
            days_since_new_high=0, conviction_score=0.70,
            regime="BULL", levels=LEVELS, tp1_done=True,
        )
        assert STAGE_TP2 in _stages(ev)
        assert next(e for e in ev.exits if e.stage == STAGE_TP2).pct_of_position == TP2_PCT_EXIT

    def test_tp3_trailing_stop(self):
        # Past tp3, price pulled back below the 2% bull trail off the high.
        ev = evaluate_exit(
            entry_price=100.0, current_price=150.0,
            highest_price_since_entry=160.0, days_held=5,
            days_since_new_high=1, conviction_score=0.70,
            regime="BULL", levels=LEVELS, tp1_done=True, tp2_done=True,
        )
        assert ev.trailing_stop_price == pytest.approx(160.0 * 0.98)
        assert STAGE_TP3 in _stages(ev)
        assert next(e for e in ev.exits if e.stage == STAGE_TP3).pct_of_position == TP3_PCT_EXIT


class TestForcedExits:
    def test_conviction_collapse_fires_tp1(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=101.0,
            highest_price_since_entry=105.0, days_held=2,
            days_since_new_high=0, conviction_score=0.30,
            regime="BULL", levels=LEVELS,
        )
        assert STAGE_TP1 in _stages(ev)

    def test_sustained_collapse_closes_all(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=101.0,
            highest_price_since_entry=105.0, days_held=3,
            days_since_new_high=2, conviction_score=0.20,
            regime="BULL", levels=LEVELS,
        )
        assert _stages(ev) == {STAGE_TP1, STAGE_TP2, STAGE_TP3}

    def test_regime_to_bear_exits_all(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=120.0,
            highest_price_since_entry=120.0, days_held=4,
            days_since_new_high=0, conviction_score=0.70,
            regime="BEAR", prior_regime="BULL", levels=LEVELS,
        )
        assert _stages(ev) == {STAGE_TP1, STAGE_TP2, STAGE_TP3}

    def test_drawdown_20pct_full_liquidation(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=105.0,
            highest_price_since_entry=108.0, days_held=2,
            days_since_new_high=1, conviction_score=0.70,
            regime="BULL", levels=LEVELS, portfolio_drawdown=0.20,
        )
        assert _stages(ev) == {STAGE_TP1, STAGE_TP2, STAGE_TP3}

    def test_no_duplicate_stage_when_forced_and_ladder_agree(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=111.0,
            highest_price_since_entry=111.0, days_held=1,
            days_since_new_high=0, conviction_score=0.30,
            regime="BULL", levels=LEVELS,
        )
        tp1_count = sum(1 for e in ev.exits if e.stage == STAGE_TP1)
        assert tp1_count == 1

    def test_protective_stop_approach_flag(self):
        ev = evaluate_exit(
            entry_price=100.0, current_price=94.0,
            highest_price_since_entry=100.0, days_held=2,
            days_since_new_high=2, conviction_score=0.70,
            regime="BULL", levels=LEVELS,
        )
        assert ev.protective_stop_approaching is True

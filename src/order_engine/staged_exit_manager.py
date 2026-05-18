"""Staged take-profit / forced-exit decisions (SPEC_STAGED_TP_1, D-052).

Stateless evaluator. Given a position's current state + a LevelPlan (from
technical_level_detector) it returns the list of stage exits to execute now.

Ladder: TP1 50% -> TP2 30% -> TP3 20%.
Forced exits override the ladder:
  * conviction collapse (< CONVICTION_COLLAPSE)        -> TP1 now; full exit if sustained
  * macro regime BULL/NEUTRAL -> BEAR                  -> exit all remaining
  * portfolio drawdown >= MAX_DRAWDOWN_HARD_STOP       -> TP1 now (full if >20%)

Protective stop reuses src.portfolio.monitor (no duplication).
All constants from src.signals.thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.portfolio.monitor import check_stop_loss_approach
from src.risk.technical_level_detector import LevelPlan
from src.signals.macro_regime_gate import REGIME_BEAR
from src.signals.thresholds import (
    CONVICTION_COLLAPSE,
    MAX_DRAWDOWN_HARD_STOP,
    TP1_PCT_EXIT,
    TP2_PCT_EXIT,
    TP2_DAYS_HOLD,
    TP3_DAYS_HOLD,
    TP3_PCT_EXIT,
    TP3_TRAIL_BEAR,
    TP3_TRAIL_BULL,
    TP3_TRAIL_NEUTRAL,
)

STAGE_TP1 = "TP1"
STAGE_TP2 = "TP2"
STAGE_TP3 = "TP3"

# Drawdown beyond which even TP2/TP3 are force-closed (SPEC_STAGED_TP_1 3.x).
_DD_FULL_LIQUIDATION = 0.20


@dataclass(frozen=True)
class StageExit:
    stage: str
    pct_of_position: float
    reason: str


@dataclass(frozen=True)
class ExitEvaluation:
    exits: list[StageExit] = field(default_factory=list)
    trailing_stop_price: float | None = None
    protective_stop_approaching: bool = False

    @property
    def total_pct(self) -> float:
        return round(sum(e.pct_of_position for e in self.exits), 6)


def _trail_pct(regime: str) -> float:
    if regime == REGIME_BEAR:
        return TP3_TRAIL_BEAR
    if regime == "NEUTRAL":
        return TP3_TRAIL_NEUTRAL
    return TP3_TRAIL_BULL


def evaluate_exit(
    *,
    entry_price: float,
    current_price: float,
    highest_price_since_entry: float,
    days_held: int,
    days_since_new_high: int,
    conviction_score: float,
    regime: str,
    levels: LevelPlan,
    portfolio_drawdown: float = 0.0,
    tp1_done: bool = False,
    tp2_done: bool = False,
    tp3_done: bool = False,
    prior_regime: str | None = None,
) -> ExitEvaluation:
    """Decide which stage exits fire now. Pure function (no side effects)."""
    exits: list[StageExit] = []
    gain = (current_price - entry_price) / entry_price if entry_price > 0 else 0.0

    def fire_tp1(reason: str) -> None:
        if not tp1_done:
            exits.append(StageExit(STAGE_TP1, TP1_PCT_EXIT, reason))

    def fire_tp2(reason: str) -> None:
        if not tp2_done:
            exits.append(StageExit(STAGE_TP2, TP2_PCT_EXIT, reason))

    def fire_tp3(reason: str) -> None:
        if not tp3_done:
            exits.append(StageExit(STAGE_TP3, TP3_PCT_EXIT, reason))

    # ---- Forced exits (override ladder) -------------------------------------
    regime_to_bear = regime == REGIME_BEAR and prior_regime not in (None, REGIME_BEAR)
    if regime_to_bear:
        fire_tp1("macro regime -> BEAR: exit all")
        fire_tp2("macro regime -> BEAR: exit all")
        fire_tp3("macro regime -> BEAR: exit all")
        return ExitEvaluation(exits=exits)

    if portfolio_drawdown >= _DD_FULL_LIQUIDATION:
        fire_tp1(f"drawdown {portfolio_drawdown:.0%} >= 20%: liquidate")
        fire_tp2(f"drawdown {portfolio_drawdown:.0%} >= 20%: liquidate")
        fire_tp3(f"drawdown {portfolio_drawdown:.0%} >= 20%: liquidate")
        return ExitEvaluation(exits=exits)

    if portfolio_drawdown >= MAX_DRAWDOWN_HARD_STOP:
        fire_tp1(f"drawdown {portfolio_drawdown:.0%} >= hard stop: TP1")

    if conviction_score < CONVICTION_COLLAPSE:
        fire_tp1("conviction collapse: TP1 now")
        # Sustained collapse (held past the 24h recovery window) → close rest.
        if days_since_new_high >= 2:
            fire_tp2("conviction collapse sustained: TP2")
            fire_tp3("conviction collapse sustained: TP3")

    # ---- Normal ladder ------------------------------------------------------
    if current_price >= levels.tp1 or days_since_new_high >= TP2_DAYS_HOLD - 1:
        fire_tp1(f"TP1 {levels.tp1_type} reached")

    if current_price >= levels.tp2 and gain > 0.15:
        fire_tp2(f"TP2 {levels.tp2_type} + gain {gain:.0%}")

    trailing_stop = None
    if current_price >= levels.tp3 or days_held >= TP3_DAYS_HOLD:
        trail = _trail_pct(regime)
        trailing_stop = round(highest_price_since_entry * (1.0 - trail), 4)
        if current_price <= trailing_stop:
            fire_tp3(f"TP3 trailing stop hit ({trail:.0%})")

    # De-dup (a stage may be requested by both a forced rule and the ladder).
    seen: set[str] = set()
    deduped: list[StageExit] = []
    for e in exits:
        if e.stage not in seen:
            seen.add(e.stage)
            deduped.append(e)

    alert = check_stop_loss_approach(
        symbol="", current_price=current_price, entry_price=entry_price
    )
    return ExitEvaluation(
        exits=deduped,
        trailing_stop_price=trailing_stop,
        protective_stop_approaching=alert.is_approaching_stop,
    )

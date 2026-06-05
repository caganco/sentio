"""Tier-A tests for the verdict-confidence qualifier (RR-Y1-009).

``assess_agreement_confidence`` is a pure function: it grades how trustworthy a
Mod-A conjugate measurement is, with precedence confounded > low > high. These
tests pin every branch and the precedence, and prove the residual_corr_flag
trigger fires on its own (the branch the synthetic moda fixtures cannot reach
after market-neutralization).
"""
from __future__ import annotations

from src.engine.confidence import assess_agreement_confidence
from src.engine.contracts import AgreementConfidence

_ARM_FLOOR = 50
_R_FLOOR = 50


def _assess(
    *,
    min_arm_size: int = 60,
    n_splits: int = 50,
    residual_corr_flag: bool = False,
    single_regime: bool = False,
) -> tuple[AgreementConfidence, tuple[str, ...]]:
    return assess_agreement_confidence(
        min_arm_size=min_arm_size,
        n_splits=n_splits,
        residual_corr_flag=residual_corr_flag,
        single_regime=single_regime,
        arm_floor=_ARM_FLOOR,
        r_floor=_R_FLOOR,
    )


class TestHigh:
    def test_adequate_breadth_and_r_no_confound(self):
        grade, reasons = _assess(min_arm_size=60, n_splits=50)
        assert grade is AgreementConfidence.HIGH
        assert reasons == ()

    def test_exactly_at_floors_is_high(self):
        # the floor check is strict (< floor), so arm == floor and R == floor pass
        grade, reasons = _assess(min_arm_size=_ARM_FLOOR, n_splits=_R_FLOOR)
        assert grade is AgreementConfidence.HIGH
        assert reasons == ()


class TestLow:
    def test_arm_below_floor(self):
        grade, reasons = _assess(min_arm_size=37, n_splits=50)
        assert grade is AgreementConfidence.LOW
        assert len(reasons) == 1
        assert "arm=37 < 50" in reasons[0]

    def test_r_below_floor(self):
        grade, reasons = _assess(min_arm_size=60, n_splits=40)
        assert grade is AgreementConfidence.LOW
        assert len(reasons) == 1
        assert "R=40 < 50" in reasons[0]

    def test_both_breadth_and_r_low_enumerated(self):
        grade, reasons = _assess(min_arm_size=37, n_splits=40)
        assert grade is AgreementConfidence.LOW
        assert len(reasons) == 2
        assert any("arm=37 < 50" in r for r in reasons)
        assert any("R=40 < 50" in r for r in reasons)

    def test_one_below_floor_is_low(self):
        grade, _ = _assess(min_arm_size=_ARM_FLOOR - 1, n_splits=_R_FLOOR)
        assert grade is AgreementConfidence.LOW


class TestConfounded:
    def test_residual_corr_flag_alone(self):
        # the branch the post-neutralization moda fixtures cannot reach.
        grade, reasons = _assess(residual_corr_flag=True)
        assert grade is AgreementConfidence.CONFOUNDED
        assert len(reasons) == 1
        assert "residual_corr_flag" in reasons[0]

    def test_single_regime_alone(self):
        grade, reasons = _assess(single_regime=True)
        assert grade is AgreementConfidence.CONFOUNDED
        assert len(reasons) == 1
        assert "single-regime" in reasons[0]

    def test_both_confounded_triggers_enumerated(self):
        grade, reasons = _assess(residual_corr_flag=True, single_regime=True)
        assert grade is AgreementConfidence.CONFOUNDED
        assert len(reasons) == 2
        assert any("residual_corr_flag" in r for r in reasons)
        assert any("single-regime" in r for r in reasons)


class TestPrecedence:
    def test_confounded_beats_low_via_residual_flag(self):
        # underpowered AND confounded -> confounded wins (the stronger warning).
        grade, reasons = _assess(min_arm_size=10, n_splits=10, residual_corr_flag=True)
        assert grade is AgreementConfidence.CONFOUNDED
        assert all("residual_corr_flag" in r or "single-regime" in r for r in reasons)
        assert not any("arm=" in r for r in reasons)

    def test_confounded_beats_low_via_single_regime(self):
        grade, _ = _assess(min_arm_size=10, n_splits=10, single_regime=True)
        assert grade is AgreementConfidence.CONFOUNDED

    def test_degenerate_zero_breadth_is_low(self):
        # the _guard_result path feeds (0, 0, False, False) -> naturally low.
        grade, reasons = _assess(min_arm_size=0, n_splits=0)
        assert grade is AgreementConfidence.LOW
        assert len(reasons) == 2

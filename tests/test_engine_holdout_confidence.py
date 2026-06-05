"""Exhaustive branch-table for the Mod-C holdout-confidence qualifier (RR-Y1-010).

The helper is pure (no I/O, no global state), so every branch of its precedence
ladder (confounded > low > high) is unit-testable from plain inputs. The semantics
are the OPPOSITE-but-consistent mirror of RR-Y1-009's agreement qualifier: for Mod-C
single-regime is the DESIGN, and the holdout window CROSSING REGIME_SPLIT is the
confound (see the module docstring of src/engine/holdout_confidence.py).
"""
from __future__ import annotations

from src.engine.contracts import HoldoutConfidence
from src.engine.holdout_confidence import assess_holdout_confidence

_FLOOR = 60


def _grade(*, obs, crosses, resid):
    return assess_holdout_confidence(
        n_holdout_obs=obs,
        holdout_crosses_regime=crosses,
        residual_corr_flag=resid,
        obs_floor=_FLOOR,
    )


class TestHigh:
    def test_adequate_obs_no_confound(self):
        grade, reasons = _grade(obs=_FLOOR, crosses=False, resid=False)
        assert grade is HoldoutConfidence.HIGH
        assert reasons == ()

    def test_well_above_floor(self):
        grade, reasons = _grade(obs=500, crosses=False, resid=False)
        assert grade is HoldoutConfidence.HIGH
        assert reasons == ()


class TestLow:
    def test_below_floor(self):
        grade, reasons = _grade(obs=_FLOOR - 1, crosses=False, resid=False)
        assert grade is HoldoutConfidence.LOW
        assert len(reasons) == 1
        assert "structurally underpowered" in reasons[0]
        assert f"< {_FLOOR}" in reasons[0]

    def test_zero_obs(self):
        grade, reasons = _grade(obs=0, crosses=False, resid=False)
        assert grade is HoldoutConfidence.LOW


class TestConfounded:
    def test_crosses_regime_alone(self):
        grade, reasons = _grade(obs=500, crosses=True, resid=False)
        assert grade is HoldoutConfidence.CONFOUNDED
        assert reasons == ("holdout window crosses REGIME_SPLIT (train/holdout span different regimes)",)

    def test_residual_flag_alone(self):
        grade, reasons = _grade(obs=500, crosses=False, resid=True)
        assert grade is HoldoutConfidence.CONFOUNDED
        assert reasons == ("residual_corr_flag (shared common-factor on the holdout window)",)

    def test_both_confounds_ordered(self):
        grade, reasons = _grade(obs=500, crosses=True, resid=True)
        assert grade is HoldoutConfidence.CONFOUNDED
        assert len(reasons) == 2
        assert "crosses REGIME_SPLIT" in reasons[0]
        assert "residual_corr_flag" in reasons[1]


class TestPrecedence:
    def test_confounded_beats_low(self):
        # below the obs floor AND crosses regime -> confounded wins (precedence 1).
        grade, reasons = _grade(obs=0, crosses=True, resid=False)
        assert grade is HoldoutConfidence.CONFOUNDED
        assert all("structurally underpowered" not in r for r in reasons)

    def test_residual_confound_beats_low(self):
        grade, _ = _grade(obs=1, crosses=False, resid=True)
        assert grade is HoldoutConfidence.CONFOUNDED

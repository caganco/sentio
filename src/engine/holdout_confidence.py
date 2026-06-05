"""Verdict-confidence qualifier for the Mod-C intra-regime time-holdout (RR-Y1-010).

Additive ONLY: this grades the trustworthiness of a forward-persistence read; it
never alters ``holdout_persistence_pass`` or any keep-bar. The grade is a SEPARATE
signal that downstream consumers read alongside the verdict. See
docs/research/RR-Y1-010-*.

Kept deliberately SEPARATE from the RR-Y1-009 ``assess_agreement_confidence`` (which
stays byte-untouched) because the regime semantics are OPPOSITE-but-consistent:

- Mod-A: a single-regime eval window is SUSPECT -- a within-regime common-factor
  artifact can fake a clean conjugate PASS, so single-regime -> ``confounded``.
- Mod-C: single-regime is the DESIGN, not a confound (the question is precisely "does
  it persist forward WITHIN one regime"). The confound here is the holdout window
  CROSSING ``REGIME_SPLIT``: if train sits in one regime and the holdout spills into
  another, the same-regime-persistence question is polluted.
"""
from __future__ import annotations

from .contracts import HoldoutConfidence


def assess_holdout_confidence(
    *,
    n_holdout_obs: int,
    holdout_crosses_regime: bool,
    residual_corr_flag: bool,
    obs_floor: int,
) -> tuple[HoldoutConfidence, tuple[str, ...]]:
    """Grade how trustworthy a Mod-C intra-regime time-holdout measurement is.

    Precedence: confounded > low > high.

    - ``confounded``: the holdout window crosses ``REGIME_SPLIT`` (train and holdout
      land in different regimes, so a within-one-regime persistence claim is polluted),
      OR a shared common-factor flag fired on the holdout window (the same detector
      RR-Y1-008 used, applied to the held-out segment).
    - ``low``: holdout IC observations below ``obs_floor`` -- structurally
      underpowered (the honest mandatory declaration: BIST has scarce non-overlapping
      within-regime forward holdouts).
    - ``high``: none of the above tripped (adequate holdout breadth + no confound).

    Note the contrast with Mod-A's ``assess_agreement_confidence``: single-regime is
    NOT a confound here (it is the design); crossing the regime boundary IS.

    Returns the grade plus an ordered tuple of every tripped reason (empty for
    ``high``). Pure: no I/O, no global state -- exhaustively unit-testable.
    """
    confounded_reasons: list[str] = []
    if holdout_crosses_regime:
        confounded_reasons.append(
            "holdout window crosses REGIME_SPLIT (train/holdout span different regimes)"
        )
    if residual_corr_flag:
        confounded_reasons.append("residual_corr_flag (shared common-factor on the holdout window)")
    if confounded_reasons:
        return HoldoutConfidence.CONFOUNDED, tuple(confounded_reasons)

    if n_holdout_obs < obs_floor:
        return (
            HoldoutConfidence.LOW,
            (f"holdout_obs={n_holdout_obs} < {obs_floor} (structurally underpowered)",),
        )

    return HoldoutConfidence.HIGH, ()

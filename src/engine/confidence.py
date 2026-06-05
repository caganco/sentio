"""Verdict-confidence qualifier for the Mod-A conjugate verdict (RR-Y1-009).

Additive ONLY: this grades the trustworthiness of a conjugate measurement; it
never alters ``agreement_pass`` or any keep-bar (DEC-049 untouched). The grade is
a SEPARATE signal that downstream consumers (and the operator guide) read
alongside the verdict. See docs/research/RR-Y1-009-*.

Closes the silent-confounded-PASS gap surfaced by RR-Y1-008: a known-dead
momentum-proxy produced ``agreement_pass=True`` on a small-arm, single-regime
window. The conjugate's narrow question ("no name-specific overfit") was answered
correctly, but the result was a within-regime common-factor artifact, not a
deployable edge -- and the engine emitted a bare ``True`` with no qualifier.
"""
from __future__ import annotations

from .contracts import AgreementConfidence


def assess_agreement_confidence(
    *,
    min_arm_size: int,
    n_splits: int,
    residual_corr_flag: bool,
    single_regime: bool,
    arm_floor: int,
    r_floor: int,
) -> tuple[AgreementConfidence, tuple[str, ...]]:
    """Grade how trustworthy a Mod-A conjugate measurement is.

    Precedence: confounded > low > high.

    - ``confounded``: a shared common-factor flag fired (``residual_corr_flag``;
      Section 4.2), OR the eval window spans a single declared regime -- the
      conjugate's "no name-specific overfit" answer can then be a within-regime
      common-factor artifact, not a deployable edge (RR-Y1-008 hi52 false-PASS).
    - ``low``: per-arm eligible names below ``arm_floor`` OR effective name-splits
      below ``r_floor`` -- the measurement is underpowered.
    - ``high``: none of the above tripped (adequate breadth + adequate R + no
      confounded trigger).

    Returns the grade plus an ordered tuple of every tripped reason (empty for
    ``high``). Pure: no I/O, no global state -- exhaustively unit-testable.
    """
    confounded_reasons: list[str] = []
    if residual_corr_flag:
        confounded_reasons.append("residual_corr_flag (shared common-factor; Section 4.2)")
    if single_regime:
        confounded_reasons.append("single-regime eval window (within-regime common-factor risk)")
    if confounded_reasons:
        return AgreementConfidence.CONFOUNDED, tuple(confounded_reasons)

    low_reasons: list[str] = []
    if min_arm_size < arm_floor:
        low_reasons.append(f"arm={min_arm_size} < {arm_floor} (underpowered breadth)")
    if n_splits < r_floor:
        low_reasons.append(f"R={n_splits} < {r_floor} (too few name-splits)")
    if low_reasons:
        return AgreementConfidence.LOW, tuple(low_reasons)

    return AgreementConfidence.HIGH, ()

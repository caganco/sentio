"""MASTER_WEIGHTS integrity validation (D-052, Phase 4.5).

Centralizes the architecture-safety invariant previously inlined in
tests/test_architecture.py. The STATIC MASTER_WEIGHTS sum must stay within the
safety band [0.85, 1.05] (here it sums to exactly 1.00). The 0.78 figure that
Phase 4.5 / SPEC_SIGNAL_CONVICTION_1 calls a "normalizer" is NOT a static sum —
it is the EMERGENT runtime floor of Σ(effective weights) once L4 (sentiment,
suspended) and L5 (smart_money, confidence-scaled) contribute 0. The engine's
dynamic normalizer is preserved. See docs/decisions/DEC-009.
"""
from __future__ import annotations

from src.signals.thresholds import (
    MASTER_WEIGHTS,
    MASTER_WEIGHTS_SUM_MAX,
    MASTER_WEIGHTS_SUM_MIN,
    RUNTIME_NORMALIZER_FLOOR,
)

# Layers permitted to carry weight 0 without being treated as a misconfiguration.
# sentiment (L4) is intentionally suspended (no Turkish news source); its base
# weight is non-zero but it is confidence-scaled to 0 at runtime in engine.py.
_ZERO_ALLOWED: frozenset[str] = frozenset({"sentiment"})

# Layers whose runtime weight is multiplied by their layer confidence at
# LayerScore creation (engine.py). Excluded from the emergent-floor calculation.
_CONFIDENCE_SCALED: frozenset[str] = frozenset({"sentiment", "smart_money"})


def static_weight_sum() -> float:
    """Sum of the static MASTER_WEIGHTS dict (confidence not applied)."""
    return round(sum(MASTER_WEIGHTS.values()), 10)


def emergent_normalizer_floor() -> float:
    """Σ of weights that survive when every confidence-scaled layer → 0.

    This is the floor the engine's dynamic normalizer reaches when L4/L5
    contribute nothing; by construction it equals RUNTIME_NORMALIZER_FLOOR.
    """
    return round(
        sum(w for k, w in MASTER_WEIGHTS.items() if k not in _CONFIDENCE_SCALED),
        10,
    )


def validate_master_weights() -> dict[str, float]:
    """Validate the MASTER_WEIGHTS invariant. Raises ValueError on violation.

    Returns a small report dict (static_sum, emergent_floor) for callers/tests.
    """
    total = static_weight_sum()
    if not (MASTER_WEIGHTS_SUM_MIN <= total <= MASTER_WEIGHTS_SUM_MAX):
        raise ValueError(
            f"MASTER_WEIGHTS static sum is {total:.4f}, must be in "
            f"[{MASTER_WEIGHTS_SUM_MIN}, {MASTER_WEIGHTS_SUM_MAX}]. "
            f"Weights: {MASTER_WEIGHTS}"
        )

    for layer, weight in MASTER_WEIGHTS.items():
        if weight < 0:
            raise ValueError(f"Layer '{layer}' has negative weight: {weight}")
        if weight == 0 and layer not in _ZERO_ALLOWED:
            raise ValueError(
                f"Active layer '{layer}' has non-positive weight: {weight}"
            )

    floor = emergent_normalizer_floor()
    if abs(floor - RUNTIME_NORMALIZER_FLOOR) > 1e-9:
        raise ValueError(
            f"Emergent normalizer floor is {floor:.4f}, but "
            f"RUNTIME_NORMALIZER_FLOOR is {RUNTIME_NORMALIZER_FLOOR}. "
            f"Non confidence-scaled weights changed without updating DEC-009."
        )

    return {"static_sum": total, "emergent_floor": floor}

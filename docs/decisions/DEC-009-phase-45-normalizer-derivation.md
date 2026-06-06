---
id: DEC-009
title: Phase 4.5 Normalizer — Emergent 0.78 Floor, Not a Hardcoded Divisor
date: 2026-05-18
area: Signal Engine
status: decided
priority: CRITICAL
affects:
  - src/signals/thresholds.py
  - src/signals/engine.py
  - src/utils/weight_validator.py
  - tests/test_architecture.py
rationale: "Phase 4.5 requires a 0.78 normalizer; CLAUDE.md immutable rule forbids a hardcoded normalizer and pins MASTER_WEIGHTS sum to [0.85,1.05]. Resolved by deriving 0.78 as the emergent runtime floor of the existing dynamic normalizer."
implementation_status: 100%
test_coverage: tests/test_architecture.py::TestWeightSumValid, tests/test_conviction_validator.py
---

# DEC-009: Phase 4.5 Normalizer — Emergent 0.78 Floor, Not a Hardcoded Divisor

**Decision Date:** 18 May 2026
**Decided By:** Strategist (maintainer)
**Status:** ✅ DECIDED

---

## CONTEXT

SPEC_SIGNAL_CONVICTION_1 specifies the reweighted composite divided by a
`normalizer = 0.78`. The CLAUDE.md "Dokunulmaz Prensipler" (immutable
principles) mandate the opposite:

- `MASTER_WEIGHTS` sum must stay in the architecture-safety band [0.85, 1.05].
- No hardcoded normalizer — the engine divides by the dynamic Σ(weights).

A literal `/0.78` divisor would violate both rules and break graceful
degradation when layers go missing.

---

## DECISION

**The dynamic normalizer is preserved. 0.78 is the EMERGENT runtime floor of
Σ(effective weights), not a hardcoded divisor.**

- Static `MASTER_WEIGHTS` (Phase 4.5): technical 0.25, macro 0.20, kap 0.30,
  sentiment 0.12, smart_money 0.10, risk 0.03 → **sum = 1.00** (in band).
- L4 (sentiment) and L5 (smart_money) weights are multiplied by their layer
  confidence at `LayerScore` creation in `engine.py`.
- When L4 is suspended (no Turkish news → confidence 0) and L5 is in data
  collection (confidence ≈ 0), the surviving weights sum to
  `0.25 + 0.20 + 0.30 + 0.03 = 0.78` — the engine's dynamic normalizer
  naturally divides by exactly 0.78. No code path hardcodes it.

---

## RATIONALE

- `_compute_weighted_sum` already divides by Σ(effective weights). Making
  L4/L5 confidence-scaled is the minimal change that makes the SPEC's 0.78
  fall out for free, with zero change to the normalizer mechanic and zero
  change to L1/L2/L3 computation.
- Static sum stays 1.00 → the immutable [0.85,1.05] invariant is untouched;
  `weight_validator.validate_master_weights()` enforces it and additionally
  asserts the emergent floor equals `RUNTIME_NORMALIZER_FLOOR = 0.78`.

---

## CONSEQUENCES

- Effective runtime Σ ∈ **[0.78, 1.00]**.
- The engine result equals the SPEC's `/0.78` ONLY at the L4=L5=0 floor —
  which is today's production state (L4 suspended, L5 conf≈0). Divergence
  begins as L5 confidence rises (~Gün 10–20); this is intentional and
  superior to a fixed divisor because missing layers no longer distort scale.
- Any future change to a non-confidence-scaled weight that moves the floor
  off 0.78 will fail `weight_validator` and must update this decision.

---

## ALTERNATIVES REJECTED

1. **Hardcoded `/0.78` divisor.** Rejected: violates the no-hardcoded-
   normalizer rule and breaks dynamic degradation — a missing layer would
   wrongly deflate the composite instead of being excluded.
2. **Override the immutable rule / widen the band below 0.85.** Rejected:
   sacrifices the architecture-safety invariant for a number that can be
   derived without touching it.

---

## RELATED DECISIONS

- **DEC-007:** Ruthless Alpha Philosophy (reweighting motivation)
- **DEC-008:** VERDA independence (L5 confidence-scaling source)

---

**Status:** ✅ DECIDED (18 May 2026)
**Approved By:** maintainer (Strategist)
**Implementation Owner:** arastirma katmani (D-052)

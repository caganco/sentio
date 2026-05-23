---
id: DEC-010
title: Strategist Advisory Boundary — LLM Output is Read-Only Narrative
date: 2026-05-19
area: Signal Architecture
status: decided
priority: HIGH
affects:
  - src/signals/strategist.py
  - src/signals/engine.py
  - src/signals/macro_regime_gate.py
  - src/signals/conviction_validator.py
rationale: "Strategist (Claude API) produces narrative for human review only. No LLM output path reaches signal computation, conviction scoring, or order execution. Python hard-gates enforce this boundary independent of LLM behavior."
implementation_status: 100%
test_coverage: tests/test_strategist.py
---

# DEC-010: Strategist Advisory Boundary — LLM Output is Read-Only Narrative

**Decision Date:** 19 May 2026  
**Decided By:** Cagan (Strategist)  
**Status:** ✅ DECIDED

---

## CONTEXT

The `StrategistAgent` (`src/signals/strategist.py`) wraps the Claude API to
generate a daily equity market narrative (~300–500 words) from the Builder
report dict. It receives macro data, signal scores, portfolio positions, and
momentum rankings as compact encoded input, then returns free-form markdown
text.

LLM outputs carry two irreducible risks in this context:

1. **Ticker hallucination** — the model may reference tickers outside the
   BIST100 universe, invent corporate events, or misidentify sectors.
2. **Sizing hallucination** — the model may suggest position sizes or
   conviction levels that contradict the quantitative signal engine.
3. **Scope drift** — as Strategist prompts evolve, future versions may be
   asked to produce structured recommendations that inadvertently couple LLM
   output to execution logic.

At the time of this decision, the output validation in `strategist.py` is
minimal:

```python
# strategist.py:175-179
if not notes or len(notes) < _MIN_RESPONSE_CHARS:  # 100 char floor
    raise StrategistError(
        f"Response too short ({len(notes)} chars); minimum {_MIN_RESPONSE_CHARS}"
    )
```

No JSON schema validation, no ticker scope check, no numeric bounds check.
This is acceptable **only because** no downstream code path consumes
Strategist output as a decision input.

---

## DECISION

**Strategist output is permanently classified as read-only advisory narrative.
It has zero write-path access to any of the following:**

| Boundary | Enforcement |
|----------|-------------|
| Signal computation (L1–L6 scores) | Strategist never calls layer functions |
| Conviction score / tier assignment | `conviction_validator.py` runs on engine output only |
| Macro regime classification | `macro_regime_gate.py` reads L2 score directly |
| RISK_OFF override | `_apply_regime_filter()` reads `macro_data` dict, not LLM text |
| Order / position sizing | No broker API call path exists from `strategist.py` |

This boundary is **not** negotiable without a superseding ADR. Any future
feature that routes Strategist output into a decision path — structured
recommendations, auto-generated orders, weight suggestions — requires a new
decision record and explicit Cagan approval.

---

## IMPLEMENTATION GUARANTEES

The following Python-side hard-gates enforce the advisory boundary independent
of any LLM behavior, including total hallucination or API failure:

### Gate 1 — `src/signals/macro_regime_gate.py`

```python
def calculate_macro_regime_scaling(l2_macro_score: float) -> float:
    """Position sizing multiplier in {1.0, 0.8, 0.0} from the L2 macro score."""
    regime = classify_regime(l2_macro_score)
    ...
```

Input: `l2_macro_score` (float from `score_macro()`). Strategist has no
write access to this value. A hallucinated "BEAR market" narrative does not
lower the L2 score — the macro layer reads live data from
`src/signals/local/` clients.

### Gate 2 — `src/signals/conviction_validator.py`

```python
def compute_conviction(composite_score: float, l2_macro_score: float) -> tuple[float, str]:
```

Input: two floats from `engine.compute_signal()`. Strategist output is not
an argument to this function and cannot be injected into it.

### Gate 3 — `src/signals/engine.py:_apply_regime_filter()`

```python
def _apply_regime_filter(
    signal: FinalSignal,
    regime: MacroRegime,
    macro_data: dict,
) -> tuple[FinalSignal, bool, str | None]:
    """RISK_OFF — all BUY signals become HOLD."""
```

RISK_OFF is derived from `macro_data` (live feed), not from Strategist text.
A narrative saying "risk is elevated today" produces zero signal effect.

### Gate 4 — `src/signals/strategist.py` call graph

`StrategistAgent.analyze_report()` calls only:
- `self.client.messages.create(...)` — Claude API write
- Returns `str` — narrative text

It does not import from `src/signals/engine`, `src/signals/thresholds`,
`src/risk/`, or `src/order_engine/`. There is no import path from
`strategist.py` that reaches conviction or execution logic.

### Gate 5 — Output validation (current, intentionally minimal)

Current validation: length floor (100 chars) + API exception handling.
Schema validation is absent. This is accepted because the absence of an
action-trigger path makes schema errors financially neutral. If a future
change adds a structured output path, schema validation becomes mandatory
and this ADR must be superseded.

---

## CONSEQUENCES

**Positive:**

- LLM hallucination → zero financial impact. Worst case is misleading
  narrative text that a human disregards. The quantitative pipeline is
  unaffected.
- Strategist can be upgraded, replaced, or suspended without touching
  any signal computation code.
- API outage or authentication failure raises `StrategistError` and is
  handled gracefully; no signal is blocked.

**Negative (accepted trade-off):**

- Strategist insight cannot be fed back into the signal engine. If the
  narrative identifies a macro regime shift before L2 scores update, that
  insight is not captured quantitatively. This is a deliberate choice:
  LLM judgment does not override systematic quant signals at any phase
  prior to Phase 5+.

---

## ALTERNATIVES REJECTED

1. **Structured output with Pydantic schema validation.** Not rejected
   permanently — deferred to Phase 5+. Would enable ticker validation and
   numeric bounds checking. Requires a new ADR when adopted.

2. **Strategist vote as a soft L7 signal layer.** Rejected at this phase.
   L4 (sentiment) is already SUSPENDED due to data quality. Adding an LLM
   text-derived score without calibration history would be an uncalibrated
   input to the weighted composite. Institutional-grade signal engineering
   requires a demonstrated track record before a new layer is weighted.

3. **No Strategist at all.** Rejected. The narrative layer serves a real
   function: it synthesizes macro + signal + portfolio state into human-
   readable context that the Orchestrator and Cagan review before session
   decisions. It earns its API cost as an advisory tool.

---

## FUTURE SCOPE (Phase 5+)

When broker API integration is introduced, the following must be resolved
before Strategist output approaches any execution path:

- Structured output format (Pydantic schema with field-level validation)
- BIST ticker whitelist validation (reject any ticker not in `config.yaml`
  universe)
- Numeric bounds check (position size suggestions bounded by
  `position_sizer_v2` output, not LLM free text)
- Confidence scoring for LLM-derived signals (separate track record from
  quant layers)
- A new ADR superseding this one

Until those conditions are met, this boundary stands.

---

## RELATED DECISIONS

- **DEC-007:** Ruthless Alpha Philosophy — conviction-based sizing
  (establishes the quant pipeline that Strategist cannot override)
- **DEC-009:** Phase 4.5 Normalizer — emergent 0.78 floor
  (the composite formula Strategist has zero access to)

---

**Status:** ✅ DECIDED (19 May 2026)  
**Approved By:** Cagan (Architect directive D-061 follow-up)  
**Implementation Owner:** N/A — no code change required; this ADR documents
existing architecture. Future scope items require new Builder SPECs.

# DEC-017 — Macro Gate Softening (CDS Percentile Overlay)

**Status:** Implemented
**Date:** 2026-05-20
**Directive:** D-108
**SPEC:** `SPEC_MACRO_GATE_SOFTENING_1`
**Area:** Signal Architecture / Risk Management

---

## Context

Before D-108, the macro regime gate produced a binary veto: any L2 macro score
below 45 → `scaling = 0.0` (all entries blocked). In bull periods where the L2
dip was driven by global factors (DXY / VIX) while local sovereign credit risk
(CDS spread) remained normal, this over-gated — blocking entries that subsequent
forward returns vindicated.

Reference: Longstaff, Pan, Pedersen, Singleton (2011) *"How Sovereign is
Sovereign Credit Risk?"* (NBER 16563) — sovereign credit risk is driven primarily
by global factors; CDS percentile is the most reliable local stress signal.

## Decision

Add a parallel `calculate_macro_regime_scaling_v2()` to
`src/signals/macro_regime_gate.py` with three concurrent layers:

1. **Hard exit overrides** — unconditional `0.0×` if any of:
   - CDS ≥ 600 bps (`MACRO_GATE_HARD_EXIT_CDS_BPS`)
   - USDTRY z-score ≥ +3σ (`MACRO_GATE_HARD_EXIT_USDTRY_SIGMA`) — **placeholder
     in Phase 1**; pipeline not yet implemented
   - Portfolio drawdown ≥ 15% (`MAX_DRAWDOWN_HARD_STOP`) — already enforced in
     `position_sizer_v2`; mirrored here for symmetry, not redundantly enforced.

2. **Base regime scaling** — same thresholds as v1 (BULL ≥ 60, NEUTRAL 45–59,
   BEAR < 45), but BEAR base becomes `MACRO_GATE_SOFT_BEAR_BASE = 0.25` instead
   of hard `0.0`.

3. **CDS percentile overlay** — `_cds_overlay(cds_percentile)` returns a
   multiplier in `[CDS_SCALING_HIGH, 1.0]`:
   - CDS ≤ 50th percentile → 1.0 (no dampening)
   - CDS 50th–90th → linear 1.0 → 0.25
   - CDS ≥ 90th → 0.25 (max dampening)

   In BEAR, the CDS ≥ 90th percentile case is special: it overrides the soft
   path back to `0.0×` (sovereign stress confirmed).

The v1 function `calculate_macro_regime_scaling()` and `classify_regime()`
remain unchanged. Existing callers and tests continue to pass.

## SPEC reconciliation (resolved with user)

| SPEC assumption | Reality | Decision |
|---|---|---|
| `engine.py` calls macro scaling | engine.py doesn't call v1 either | v2 wired at daily_update.py briefing layer; `position_sizer_v2` keeps its `macro_scaling: float` param for future consumers |
| `cds_percentile`, `cds_history` already exist | Not present | Built in Phase A: `LocalMacroCache.get_cds_history()` + `macro_layer._compute_cds_percentile()` |
| `usdtry_zscore` already exists | Not present | `HardExitFlags.usdtry_zscore = 0.0` placeholder (always false); USDTRY rolling-history pipeline deferred to Faz 1.5 |

## Out of scope (deferred)

- **USDTRY z-score pipeline** — Phase 1.5: needs USDTRY 30d rolling history
  pipeline (no current source). Until then, `HardExitFlags.usdtry_zscore`
  defaults to `0.0`, never triggering the hard exit.
- **`position_sizer_v2.size_position()` invocation** — that function already
  accepts `macro_scaling: float`, but isn't currently called from production
  (`scripts/daily_update.py` still uses `KellySizer`). Wiring it in is a
  separate directive.
- **Hard exit unification with `position_sizer_v2`** — DD ≥ 15% gate lives in
  `position_sizer_v2`; here it's mirrored for symmetry but not re-enforced.

## Survivorship of v1

`calculate_macro_regime_scaling(l2)` returns `float` exactly as before.
`tests/test_macro_regime_gate.py` (14 tests) all pass unchanged. Any caller
that uses v1 stays binary {1.0, 0.8, 0.0}.

## Verification

- Phase A: 5 new tests in `tests/test_cds_percentile.py`.
- Phase B: 10 new tests in `tests/test_macro_gate_softening.py`, 3 architecture
  tests added to `tests/test_architecture.py` (constants ordered, v2 returns
  unit-range float, v1 unchanged).
- Smoke: `python -c "from src.signals.macro_regime_gate import
  calculate_macro_regime_scaling_v2; print(calculate_macro_regime_scaling_v2(40.0, 0.30))"`
  → `MacroScalingResult(scaling=0.25, regime='BEAR', ...)`.
- Daily update wiring: `briefing["macro_gate_v2"]` populated; log line
  `"Macro gate v2: ..."` emitted per run.

## Affected files

- `src/signals/thresholds.py` (+7 constants in macro gate block)
- `src/signals/macro_regime_gate.py` (+`HardExitFlags`, `MacroScalingResult`,
  `_cds_overlay`, `calculate_macro_regime_scaling_v2`)
- `src/signals/local/cache_store.py` (+`get_cds_history(days)`)
- `src/signals/layers/macro_layer.py` (+`_compute_cds_percentile`, exposes
  `cds_percentile` in `detail["local_macro"]["cds"]`)
- `scripts/daily_update.py` (briefing-layer v2 wiring, fully try/except guarded)
- `tests/test_cds_percentile.py` (NEW, 5 tests)
- `tests/test_macro_gate_softening.py` (NEW, 10 tests)
- `tests/test_architecture.py` (+3 tests in `TestMacroGateSofteningConstants`)

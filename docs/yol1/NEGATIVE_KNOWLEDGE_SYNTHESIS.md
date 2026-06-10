# Negative-Knowledge Synthesis (RR-Y1-015, Phase 4)

> This document **organizes** existing elimination findings; it makes no new
> claim and reinterprets no verdict. It does **not** re-frame the graveyard as
> "actually there is hope." Elimination is elimination. What is documented here is
> the **value** of that elimination (negative knowledge + Yol-2 ground
> validation), not a softening of it. Machine-readable companions:
> `data/registry/graveyard_registry.json`, `data/registry/cross_references.json`.

---

## Section A — Elimination map (exhausted-axis taxonomy)

Five axes were tested. Each closed for one of a small set of common reasons.

### A.1 Cross-sectional (factor-selection) — 3/3 exhausted, then a 4th paradigm also failed
| candidate | verdict | carrier reason | common payoff |
|-----------|---------|----------------|---------------|
| value_static (D-203) | SERAP | Gate-2 NW-t 0.76; illiquidity-concentrated | known-anomaly priced / liquidity-mirage |
| value_regime_arm (NRR-008) | SERAP | regime-gating added 0 significance (0.759≈0.76) | mis-timing was never the problem |
| value_only_regime (D-Y1-001) | FRAGILE | P/B mechanical-pass but E/P + OOS fail | regime-dependent, not a stable premium |
| hi52 (D-203→208) | KESIN-KAPANDI | fair-cost Gate-2 t=1.17 (pre-cost 1.70) | significance wall on fair ground |
| lowvol63 (NRR-007) | SERAP | Gate-4 liquidity_collapse (illiq +1.20% vs liq −0.31%) | liquidity premium, not edge |
| mom120 | SERAP | never passed isolated (t=1.76, agree=False) | composite-hidden, no standalone edge |
| edge2_composite (D-203) | REAL-but-NOT-DEPLOYED | real ~0.54%/mo liquid but post-2022 narrowing; all constituents closed | no deployable component left |
| h2b_dividend_runup (D-209) | KESIN-KAPANDI | liquid cost-free t=0.61 (famous 2.565 is illiquid-driven) | liquidity-mirage / significance wall |
| nav_discount_z (D-206) | SERAP | FE-within-beta −0.0185 (wrong sign), 0/5 gates | no mean-reversion in measured window |

**Common payoffs:** *retail-inaccessible (liquidity-premium)* and
*sub-significance*. The cross-sectional factor program is exhausted: the three
core factors closed, the last t≥2 candidate (H2b) closed on fair ground, and the
new time-series paradigm (NAV-discount) also returned SERAP.

### A.2 Orthogonal-timing (price axis) — both axes lost
| candidate | verdict | carrier reason | common payoff |
|-----------|---------|----------------|---------------|
| foreign_flow_timing (D-211) | TRADEABLE-DEGIL | lag-2 knowable t=0.73 (lag-0 t=3.68 is co-movement) | knowable content absent |
| real_rate_timing (D-213) | TRADEABLE-DEGIL | lag-1 t=1.82, correct sign, weak content | knowable content weak |

**Common payoff:** *the knowable-lag form is weak/empty.* A strong
contemporaneous (lag-0) relationship is co-movement, not a lead (DISC-2, timing
defeat — now confirmed 3×). RR-038's "index-foreign-flow leads" thesis is
refuted in the knowable form.

### A.3 Derivative-OI — unsigned by construction
| candidate | verdict | carrier reason | common payoff |
|-----------|---------|----------------|---------------|
| viop_ssf_oi_k2 | FAIL | NW-t −0.073 (≈0); unsigned OI, thin 63-name cross-section, post-2022 flip | noise / detection-not-direction |

### A.4 Mechanical-flow — priced at the public window
| candidate | verdict | carrier reason | common payoff |
|-----------|---------|----------------|---------------|
| index_recon_xu030_in (RR-Y1-011-E) | SERAP | KB1 NW-t 0.052; sign-flip half-A +3.79% / half-B −3.58% | priced at 11-19-day public announcement |

### A.5 Event-tilt — PEAD pending; C7/C8/C9 not in this branch
PEAD (RR-Y1-013/-014) is **PENDING** (parallel task; excluded from closures).
C7 (falling-knife) / C8 (core-satellite) / C9 (sector-tilt) referenced by the
directive are **absent from this repository's master** (see CONSISTENCY_AUDIT §C) and
are therefore neither claimed nor counted.

---

## Section B — Positive knowledge produced (elimination → law)

The graveyard is not empty: each major FAIL produced a permanent, reusable rule.

1. **PM-1 — forgone-beta invariant.** Idle capital is benchmarked as
   fully-invested equal-weight; a tilt earns no free credit for sitting in cash.
   *Graveyard code that became a design law*, enforced by the validation engine
   (`pm1_compliant`). (← pm1_forgone_beta)
2. **Cost-premise audit.** A tradeability verdict must run on a fidelity-checked
   cost model. The hi52 chain exposed a ~12–25× inflated cost model (NRR-010 →
   D-207 calibration → D-208 fair re-test), which *moved the wall from "cost
   kills" to "significance kills"* — the honest conclusion only emerges once the
   cost premise is audited. (← hi52)
3. **Sign-flip / post-hoc rescue ban.** A frozen-before-results Stage-0 split is
   not re-opened; sub-sampling, tier-widening, outlier-removal, and window-mining
   are forbidden. Whatever a re-run shows, a grave stays a grave (no clean X_2).
   (← index_recon_xu030_in, viop_ssf_oi_k2; directive DEC-053/DISC-9)
4. **Liquidity-premium mirage.** Cross-sectional "edges" living only in the
   illiquid tail (Gate-4 liquidity_collapse) are a liquidity premium; the
   apparent ALL-universe significance dies in the deployable liquid universe.
   (← lowvol63, H2b, value)
5. **N≤3 measurement lock.** A thread closes after ≤3 measurements; a
   premise-change (e.g. corrected cost) is a REVISIT, not a 4th round.
   (← value 3/3; D-208 revisit)
6. **Timing defeat (DISC-2).** Co-movement (lag-0) is not prediction; the
   knowable lag is the only honest test. (← D-211, D-213)

These laws are now the scope-guard that future candidate evaluation runs against
(DISC-5), instead of re-scanning scattered records.

---

## Section C — Yol-2 ground validation (argument synthesis, not a new claim)

Across **four** completed elimination axes — cross-sectional, orthogonal-timing,
derivative-OI, mechanical-flow — **no deployable retail edge was confirmed**, each
on a recorded, frozen-before-results basis. (Event-tilt/PEAD is pending and
excluded.)

This independently validates the Yol-2 ground (static-exposure + cost/tax
discipline + quality; passive smart base) — **not** because prediction was
untried, but because it was tried across four axes and failed each one on its
own honest terms:

- factor-selection → liquidity-mirage / sub-significance;
- price-orthogonal timing → knowable content weak/absent;
- derivative-OI → unsigned noise;
- mechanical-flow → priced at the public window.

The elimination map *is* the evidence that a passive, cost-disciplined base is
the rational architecture for this universe. This restates and organizes the
existing RR-038 thesis ("cost/exposure discipline > prediction") that three
independent test families already confirmed; it introduces no new claim.

---

## Section D — Open doors (save/wait, honest)

Distinguishing **permanently dead** from **eliminated-in-this-universe but
re-warrantable under a future clean regime**:

### D.1 PERMANENT graves (revival forbidden)
value_static, value_regime_arm, value_only_regime, hi52, lowvol63, mom120,
edge2_composite, h2b_dividend_runup, foreign_flow_timing, viop_ssf_oi_k2,
index_recon_xu030_in. Post-hoc chains are blocked; the conclusion is
universe-structural, not power-limited.

### D.2 save/wait (a future clean regime could re-warrant a *fresh* Stage-0)
- **real_rate_timing (D-213).** Weak-but-**correctly-signed** (slope −0.00100,
  lag-1 t=1.82). The recorded report itself flags a future **regime-change OOS**
  re-examination rationale: 2019–2026 is a single high-inflation regime with no
  real disinflation OOS. This is a deploy-candidate **NO** today, a clean-regime
  **re-measure** later — via a new frozen Stage-0, never a post-hoc revival.
- **nav_discount_z (D-206).** SERAP in the measured window under an N≤3 lock
  (1/3) with an open-declared OOS-weak + N=6 survivorship caveat. The *distinct*
  fund/CEF NAV-arb mechanism (RR-045 → **NRR-009**, currently **absent from
  master**) is a separate, not-yet-measured axis — feasibility-resolved
  (weekly-KAP NAV) but N=9-binding.
- **corp-action / event-level calibration** and **data-walled classes** (the
  KAP day-stamp / VIOP / foreign-flow depth limits recorded across RR-031/042/
  Y1-013-B) remain feasibility-gated rather than edge-refuted.

### D.3 PENDING (active, not a door)
**PEAD (RR-Y1-013/-014)** — feasibility CONDITIONAL→PASS; Stage-0 decision
pending; parallel task. Recorded as PENDING; no result asserted here.

---

## Section E — Honesty note

Two save/wait doors (D-213, NAV-arb axis) are **not** the graveyard "leaving the
door open to hope." They are the honest distinction between *universe-structural
refutation* (permanent) and *single-regime / feasibility-gated* (re-measurable
under a fresh frozen Stage-0). Every save/wait remains a candidate-only, MEASURE-
first item — never an auto-deploy, never a post-hoc revival of a closed grave.
The elimination is not softened; its boundary is just drawn precisely.

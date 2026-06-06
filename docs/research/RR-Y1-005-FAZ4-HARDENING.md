# RR-Y1-005-FAZ4 — Validation-Engine Hardening Report

**Status:** Applied (one PR, `feature/rry1005-faz4-hardening`).
**Scope:** the N2 hardening backlog recorded at RR-Y1-005 Faz-3 close, authorized as
GÖREV-1 of the post-motor task package. These are *mechanical / diagnostic* hardenings
of an already-complete engine (`src/engine/`) — **not** an edge hunt.

**Conflict priority:** TASARIM v0.2 > math-spec v1.1 (RR-Y1-005B) > task-package > arastirma katmani.
**Strangler invariants honored:** committed motors (`src/backtest/*`, lab, clib) UNCHANGED;
`src/engine` additive only; `compute_dsr` is *called* (with `benchmark_sr`), never rewritten;
`tests/test_engine_no_lab_import.py` AST-covers the new `src/engine/dsr.py`; C12 golden
byte-repro stays green (gross 6.928414 / net −6.274774, n=1375); zero regression.

The three deliverables differ deliberately in what they persist (output-transparency
principle): **(a)** and **(b)** are *applied mechanisms* whose behavior/inputs must be
visible, so they touch the engine + output vector; **(c)** is an *unverified diagnostic
hypothesis*, so it is measure-and-report only — NO engine-logic change, NO keep-bar change,
NO new permanent output field. Persisting a diagnostic finding before the finding justifies
it would be "factor-inflation's output-vector version."

---

## (a) — NW near-zero-variance floor-guard

**Problem.** `stats.nw_tstat` (`src/engine/stats.py`) guarded only the exactly-degenerate
case `s <= 0.0 -> NaN`. A *numerically*-constant input (e.g. `np.full(50, 0.7)`: `0.7` is
not FP-exact, so rounding leaves dispersion ~1e-32) produces a tiny-but-positive HAC
variance and therefore an **explosive spurious t** — the value looks hugely significant but
is pure floating-point noise.

**Fix (additive).** Replace the guard with a relative variance floor:

```python
if s <= 0.0 or s <= config.NW_VAR_FLOOR_EPS * m * m:
    return float("nan")
```

`NW_VAR_FLOOR_EPS = 1e-12` (new constant in `src/engine/config.py`). `m` is the
already-computed mean; the floor is relative (`eps · mean²`) so it scales with the signal
level rather than an absolute cutoff.

**Why this separates degenerate from legitimate (verified numerically):**

| input | relative variance `s/m²` | vs floor `eps=1e-12` | result |
|---|---|---|---|
| `np.full(50, 0.7)` (degenerate) | ~1e-32 | ≪ | **NaN** (explosive-t killed) |
| `test_perfect_signal` (0.05 + 1e-6 noise) | ~1e-10 | 100× above | stays `t > 50` |
| C12 golden (gross/net pooled) | ~1e2 | ~14 decades above | byte-identical |
| d211 / d213 random-normal | O(1) | far above | byte-identical |
| `np.ones(50)` (exact, e≡0 → s=0) | — | caught by `s<=0` | NaN (unchanged) |

The floor sits two decades below the smallest *legitimate* relative dispersion in the test
suite and ~14 decades below the golden's, so it fires **only** on degenerate input. The
contract is unchanged: `nw_tstat` stays a pure `float -> NaN` (no signature/return-type
change); all three callers (`harness`, `moda`, `modb`) already handle NaN-where-undefined.
This is a guard *beyond* the d211/d213 precedent — identical on every non-degenerate input,
diverging only where the precedent would emit a spurious explosive t.

**Tests** (`tests/test_engine_stats.py`): added `test_near_constant_is_nan`
(`np.full(50, 0.7) -> NaN`); refreshed the now-stale comment in `test_zero_variance_is_nan`.
Kept green: `test_perfect_signal_is_large_t` (>50), the d211/d213 NW-equivalence pin, and
`test_nw_reproduces_c9_golden`.

---

## (b) — DSR trial-count binding (Stage-0 → N → deflation)

**Concept** (math-spec §5; task-package L14). Multiple-test / search-overfit is the job of
**DSR's N-deflation**, NOT of bucket-PBO (which measures single-prototype-*internal* overfit
— a different layer). The engine previously called `compute_dsr` with the implicit
`benchmark_sr = 0` (no trial deflation). This binds the **honest** tried-config count
`N = Stage0.denenen_konfig_sayisi` into the deflation.

**Strangler-clean path** — the engine computes the López de Prado benchmark and feeds the
**existing, unchanged** `compute_dsr`:

- **New `src/engine/dsr.py`:**
  - `expected_max_sharpe(n_trials)` = `(1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))`, γ = Euler-Mascheroni.
    **Returns 0.0 for N ≤ 1** (no deflation; also avoids `Φ⁻¹(0) = −∞`). This is the same
    closed form already committed in `statistical_validation.min_btl_days` — *reimplemented*
    engine-side, NOT edited in place (strangler).
  - `deflation_benchmark_sr(sr_obs, T, skew, kurt, n_trials)` =
    `se_SR · E[max_N]`, with `se_SR = sqrt(denom_sq/(T−1))`,
    `denom_sq = 1 − skew·sr_obs + (kurt−1)/4·sr_obs²`. Returns 0.0 at N≤1, T≤1, or
    `denom_sq ≤ 0` (degenerate — `compute_dsr` bails on the same condition). Feeding this as
    `compute_dsr`'s `benchmark_sr` yields the canonical Bailey-LdP deflated
    DSR = `Φ(sr_obs/se_SR − E[max_N])`.
- **`src/engine/modb.py`:** `run_modb(..., *, n_trials=1)` (additive). Computes the benchmark,
  passes it to `compute_dsr`, and surfaces `dsr_n_trials` + `dsr_deflation_benchmark_sr` in
  the result dict.
- **`src/engine/harness.py`:** captures the `Stage0` doc from `require_stage0` (previously
  discarded), passes `n_trials = stage0.denenen_konfig_sayisi` to `run_modb` (else
  `DSR_DEFAULT_N_TRIALS = 1`), populates `EngineOutput.dsr_n_trials`, and appends a note when
  N > 1 (the note states this is the DSR layer's job, NOT bucket-PBO).
- **`src/engine/contracts.py`:** `dsr_n_trials: int | None = None` added to `EngineOutput`
  (additive). This field IS persisted on purpose: N is the load-bearing input to the
  deflation strength, so it must be visible/auditable, not buried in free text.

**Zero-regression.** Every current run/test that supplies no Stage-0 → N=1 → benchmark_sr=0 →
DSR **byte-identical**. The committed lab/backtest `run_cpcv_validation` DSR call is not
touched.

**Tests:** new `tests/test_engine_dsr.py` (13 tests) pins `expected_max_sharpe` at
hand-computed N=2/10/100 values, the canonical `Φ(sr/se − E[max_N])` identity through the
committed `compute_dsr`, the N=1 zero-regression byte-identity, and N≫1 strictly-lower DSR.
`tests/test_engine_modb.py` adds `TestTrialDeflation`; `tests/test_engine_harness.py` adds
`TestStage0TrialBinding` (Stage-0 fixture with N=25 surfaces on `dsr_n_trials` + note;
no-Stage-0 defaults to 1).

---

## (c) — bucket-PBO ↔ agreement-condition double-count: MEASUREMENT + verdict

**Question.** The Section-4.1 Mod-A PASS bar (`moda.conjugate_agreement`) is a 3-way AND:
- **cond1** `agreement_t_cross_median` — min over arms of the median residual rank-IC t (>2);
- **cond2** `sign_consistency` — cross-arm mean-IC sign agreement, fraction of name-splits (≥0.90);
- **cond3** `pbo` — real CSCV bucket-transfer PBO (<0.50, LOW is good).

All three consume the **same** `resid_fwd` + `scores` + `splits`, so they are *expected* to
correlate. The diagnostic asks whether each condition still carries **independent**
information once the common cause — the latent factor strength — is controlled. If the
partials collapse to ~0, the 3-way AND is effectively counting one piece of evidence
multiple times.

**Design** (`tests/test_engine_pbo_agreement_corr.py`, diagnostic — no gate). Drive
`run_moda` over an embedded-factor-loading sweep `alpha ∈ {0, 0.0006, 0.0012, 0.0025, 0.0050}`
(noise → strong) × seeds `{0..4}` = 25 runs, reusing the Faz-2 `factor` panel construction
with a tunable loading; the scorer IS the static market-neutral loading vector. Collect
`(cond1, cond2, cond3)` per run; compute the raw Pearson matrix and two partial-correlation
matrices (residualize-then-correlate via least squares): controlling for (i) the **third**
metric, and (ii) the **latent alpha** (the common cause). The test asserts only that the
sweep runs, spans weak→strong (`pearson(cond1,alpha) > 0.3`, `pearson(cond3,alpha) < −0.3`),
and reproduces deterministically. (The module fixture temporarily shrinks
`config.RESIDUAL_NULL_RESAMPLES` 200→8 via save/restore; that null feeds ONLY the
`residual_corr` field which this diagnostic ignores — the three agreement metrics are
computed upstream of it, so runtime changes, the measured numbers never do.)

### Measured matrices (25 of 25 runs finite, deterministic)

```
                                    Pearson    | third      | latent alpha
                                    (raw)      controlled    controlled
  cond1_t_cross ~ cond2_sign        +0.517       −0.187        −0.033
  cond1_t_cross ~ cond3_pbo         −0.664       −0.514        −0.101
     cond2_sign ~ cond3_pbo         −0.879       −0.837        −0.833
```

### Verdict: PARTIAL double-count, localized to cond2 ↔ cond3

Reading the **latent-alpha-controlled** column (the clean test of "is the raw correlation
just the common cause?"):

- **cond1 ↔ cond2** collapses **+0.517 → −0.033** — co-movement was entirely the shared
  factor strength; conditionally independent given alpha. **No double-count.**
- **cond1 ↔ cond3** collapses **−0.664 → −0.101** — same; the residual rank-IC t carries
  information the other two do not. **No double-count.**
- **cond2 ↔ cond3 survives −0.879 → −0.833** — `sign_consistency` and `pbo` share strong
  variance **beyond** what factor strength explains. They are substantially measuring the
  same thing. **Double-count confirmed.**

The "third-metric-controlled" column corroborates: cond2~cond3 stays −0.837 even with cond1
held fixed, while cond1's pairs weaken.

**So the nominal 3-way AND is effectively a 2-way AND:** `[cond1] AND [cond2 ≈ cond3]`.
The bar is two genuinely-independent hurdles, not three.

**Mechanism (why this is structural, not a fixture artifact).** Both cond2 and cond3 are
functions of cross-arm IC-sign stability. `sign_consistency` = fraction of name-splits where
the cross-arm mean-IC sign agrees; CSCV bucket-transfer PBO = fraction of splits where the
IS-best decile bucket lands OOS-below-median. When the cross-arm IC sign is stable, the
IS-best bucket stays OOS-above-median → low PBO. The two metrics are mechanically linked
through the same cross-arm sign behavior, so measuring both largely measures sign-stability
twice. cond1, by contrast, is a *magnitude* (median t of the residual rank-IC), not a
sign-agreement count — which is why it stays independent.

**Severity.** This is a mild *overconfidence* risk, not a correctness bug: an AND can only be
stricter, so the bar remains conservative. But its evidentiary weight is overstated by
~one condition — passing "three independent checks" is really passing ~two.

### Deferred proposal (NOT applied — maintainer decision)

Because double-count IS found, a condition-independence refinement is *proposed* — explicitly
**NOT** a keep-bar loosening, explicitly **deferred**:

- **Option 1 — orthogonalize.** Residualize cond3 (PBO) against cond2 (sign_consistency)
  before the `< 0.50` test, so the third hurdle measures only the overfit PBO carries
  *beyond* sign-stability.
- **Option 2 — combine + add an axis.** Fold cond2 + cond3 into a single cross-arm-stability
  statistic (one hurdle) and keep cond1 as the second, restoring a real multi-axis AND;
  optionally add a genuinely orthogonal third axis.
- **Option 3 — relabel, no logic change.** Accept the bar as a 2-hurdle bar (magnitude +
  cross-arm stability) and document that the third condition is corroborative, not
  independent. Honest accounting, zero code change.

**Caveats on the measurement.** Synthetic single-static-factor fixtures, one scorer family.
The cond2↔cond3 mechanical link is structural (so the *direction* of the finding should
transfer), but its *magnitude* on real, richer signals is unmeasured. **Recommendation: do
NOT change the keep-bar on this diagnostic alone.** The choice among Options 1/2/3 belongs to
maintainer.

---

## Verification (this PR)

1. Targeted: `pytest tests/test_engine_stats.py tests/test_engine_dsr.py
   tests/test_engine_harness.py tests/test_engine_modb.py
   tests/test_engine_pbo_agreement_corr.py` — green.
2. C12 golden byte-repro (`test_nw_reproduces_c9_golden`) — green (6.928414 / −6.274774): the
   (a) floor does not move the golden; (b) is Mod-B-only.
3. `tests/test_engine_no_lab_import.py` — new `src/engine/dsr.py` AST-clean (no lab/clib import).
4. `ruff check src/engine tests/test_engine_*.py` + `mypy src/engine` — clean.
5. `lint-imports` — no new `src/engine` → lab edge.
6. Full regression `pytest tests/ -q` — zero regression vs the 2004+ baseline.

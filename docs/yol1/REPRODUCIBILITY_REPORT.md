# Reproducibility Report — Negative-Knowledge Registry (RR-Y1-015, Phase 3)

> **Discipline boundary (critical).** This phase verifies that each graveyard
> result **still reproduces the same recorded behaviour** — it does **not** search
> for a different result. A candidate that re-ran to a different number would be a
> **code-drift finding** (reported, verdict unchanged), **not** a revival
> opportunity (DEC-053 / DISC-9: whatever the re-run shows, a grave stays a grave;
> there is no clean X_2). **`no_new_edge_metrics: true`** — no CAR / return /
> Sharpe / NW-t was computed here. Only committed deterministic vectors and
> harness/verdict logic were exercised.

**Run:** `python -m pytest <candidate tests> + tests/test_engine_stats.py`
**Result:** **145 passed, 1 skipped, 0 failed** (10.99 s).
**Environment:** committed code only; no candidate source touched.

---

## 1. Determinism-anchor inventory

| anchor | what it pins | present? |
|--------|--------------|----------|
| C12 golden end-to-end (`tests/fixtures/c12_golden_meta.json`) | full engine byte-repro from a real-data snapshot | fixture meta present; **snapshot git-ignored** → e2e test `skipif`-gated |
| C12 NW-scalar anchors | engine NW-t gross **6.928414** / net **−6.274774** @ lag10, n=1375 | **VERIFIED** via `TestNeweyWestEquivalence` (pins the same scalars the C12 e2e would assert) |
| C9 golden | NW reproduction on a frozen vector | **VERIFIED** (`test_nw_reproduces_c9_golden`) |
| d211 / d213 NW-equivalence pins | committed NW-stat == engine NW-stat | **VERIFIED** (`test_matches_committed_d213_and_d211[3,6,10]`) |
| per-candidate Stage-0 content-hash | frozen pre-registration not silently mutated | **VERIFIED** where wired (e.g. viop `34d312edf5b3c27b`, d211/d213 hash-drift guards) |

---

## 2. Per-candidate reproducibility status

| candidate | test module | result | `reproducible` | what was verified |
|-----------|-------------|--------|----------------|-------------------|
| value_static (D-203) | test_d203_clean_universe_test | 13 passed | **VERIFIED** | clean-universe harness + verdict logic |
| edge2_composite (D-203) | test_d203_clean_universe_test | (same) | **VERIFIED** | composite gate logic |
| hi52 (D-204/205/208) | test_d204_hi52_stress (19) · test_d205_hi52_liquid (12) | 31 passed | **VERIFIED** | stress harness, liquid re-test, cost-model dispatch |
| lowvol63 (NRR-007) | test_nrr007_lowvol63 | 11 passed | **VERIFIED** | engine-dispatch-untouched + verdict branches + Stage-0 refusal |
| mom120 | test_engine_stats (rank-IC/IR/NW) | 18 passed | **VERIFIED** | NW + conjugate-agreement primitives (RR-Y1-008 example tier) |
| value_regime_arm (NRR-008) | test_nrr008_value_regime | 12 passed | **VERIFIED** | `run_gates_on_score == engine` replica MATCH + regime-mask logic |
| value_only_regime (D-Y1-001) | — | n/a | **NO-FIXTURE** | no committed test/determinism vector in master |
| h2b_dividend_runup (D-209) | test_d209_h2b_runup | 12 passed | **VERIFIED** | detection reproduction + verdict logic |
| nav_discount_z (D-206) | test_d206_nav_discount | 18 passed | **VERIFIED** | FE-within-beta / DK logic + verdict branches |
| foreign_flow_timing (D-211) | test_d211_foreign_flow | 10 passed | **VERIFIED** | NW-OLS slope recovery + hash-drift guard + Stage-0 refusal |
| real_rate_timing (D-213) | test_d213_real_rate | 11 passed | **VERIFIED** | deploy-rule sign + ex-ante lag-1 alignment + hash guard |
| viop_ssf_oi_k2 | test_viop_k2_harness | 9 passed | **VERIFIED** | Stage-0 content-hash stable + PM-1 compliance + signal scoring |
| index_recon_xu030_in (RR-Y1-011-E) | — | n/a | **NO-FIXTURE** | standalone scratch script; Stage-0 asserts data hashes but panels git-ignored |
| pm1_forgone_beta | test_engine_contracts | (passes) | **VERIFIED** | PM-1 guard + Stage-0 `pm1_compliant` flag |

**Tally:** VERIFIED = 12 · NO-FIXTURE = 2 · STALE = 0 · NOT-CHECKED = 0.

---

## 3. Honest scope of "VERIFIED"

The committed per-candidate tests pin the **harness machinery, verdict logic,
Stage-0 hash stability, and the engine's core statistics** — and they are all
green and deterministic. They do **not** re-derive the recorded edge metric
(e.g. NW-t=0.76) against the original real-data panels, because those panels
(`data/processed/*.parquet`, `data/clean_universe/*.parquet`,
`data/snapshots/*.parquet`) are **git-ignored**. So:

- **What is proven:** the elimination machinery has not drifted — the same code
  still produces the same verdict logic and the same pinned NW scalars
  (C12/C9/d211/d213 anchors hold byte/numeric-exact).
- **What is not re-run (by design):** the end-to-end edge metric on real panels.
  Re-running it would (a) require restoring git-ignored data and (b) risk
  crossing into "compute a new metric", which Phase 3 forbids. The two
  `NO-FIXTURE` candidates (value_only_regime, index_recon_xu030_in) have **no**
  committed determinism vector at all; their verdict artifacts (Stage-0 +
  results + graveyard) are present and internally consistent (Phase-2 audit).

**No STALE / code-drift was found.** No candidate re-ran to a different
behaviour. Had any test failed an assertion, it would be reported here as a
code-drift finding with the verdict left untouched — none did.

---

## 4. Carry-forward to Phase-4 recommendations (not actioned here)

- Wire a committed determinism vector for **value_only_regime (D-Y1-001)** and
  **index_recon_xu030_in** so their `NO-FIXTURE` status can become `VERIFIED`
  without restoring git-ignored data (e.g. a tiny frozen synthetic fixture that
  pins the verdict-logic path, mirroring the C12/C9 golden pattern).
- The **C12 e2e** byte-repro remains `skipif`-snapshot-gated; its scalar anchors
  are independently pinned, so engine determinism is covered, but the full
  snapshot path is only exercised in a local tier.

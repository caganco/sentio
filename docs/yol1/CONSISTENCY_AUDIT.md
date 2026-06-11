# Consistency Audit — Negative-Knowledge Registry (RR-Y1-015, Phase 2)

**Scope:** cross-check every consolidated graveyard candidate across its
artifacts — graveyard doc ↔ Stage-0 JSON ↔ results JSON ↔ RESEARCH_REGISTRY ↔
FEATURE_INDEX ↔ git history. **Report-only.** No contradiction is fixed here;
any correction is left to the maintainer. This document records what is
consistent, what is missing, and what conflicts.

---

## A. Cross-artifact consistency (per candidate)

| candidate | Stage-0 | results | graveyard doc | committed test | metric agrees across artifacts? |
|-----------|---------|---------|---------------|----------------|--------------------------------|
| value_static (D-203) | ✅ | ✅ | — (none) | ✅ | ✅ NW-t 0.76 (registry ↔ report) |
| edge2_composite (D-203) | ✅ | ✅ | — | ✅ | ✅ real-but-narrowing, components closed |
| hi52 (D-203/204/205/208) | ✅ (d204) | ✅ (d208) | — | ✅ | ✅ D-208 gate2 t=1.17 (pre-cost 1.70) |
| lowvol63 (NRR-007) | ✅ | ✅ | — | ✅ | ✅ NW-t 0.94, gate4 collapse |
| mom120 | ✅ (rry1008 example) | — | — | ✅ (stats) | ✅ Mod-A t=1.76 agree=False |
| value_regime_arm (NRR-008) | ✅ | ✅ | — | ✅ | ✅ NW-t 0.759 ≈ static 0.76 |
| value_only_regime (D-Y1-001) | ✅ | ✅ | — | ❌ no test | ✅ FRAGILE (P/B pass, E/P+OOS fail) |
| h2b_dividend_runup (D-209) | ✅ | ✅ | — | ✅ | ✅ liquid cost-free 0.61 / ALL 2.565 |
| nav_discount_z (D-206) | ✅ | ✅ | — | ✅ | ✅ FE-beta −0.0185, 0/5 |
| foreign_flow_timing (D-211) | ✅ | ✅ | — | ✅ | ✅ lag-2 t=0.73 / lag-0 t=3.68 |
| real_rate_timing (D-213) | ✅ | ✅ | — | ✅ | ✅ lag-1 t=1.82 |
| viop_ssf_oi_k2 | ✅ | git-ignored | ✅ | ✅ | ✅ NW-t −0.073, hash 34d312edf5b3c27b |
| index_recon_xu030_in (RR-Y1-011-E) | ✅ | ✅ | ✅ | — no test | ✅ KB1 0.052, sign-flip, KB3 pass |
| pm1_forgone_beta | — (law) | — | — | ✅ | n/a (invariant, not a metric) |

No metric contradiction was found between the recorded artifacts and the
RESEARCH_REGISTRY verdict text. Where a value differs in framing (e.g. H2b's
ALL-universe 2.565 vs liquid 0.61) the artifacts agree it is the same finding
viewed at two universes; that is recorded as a `note`, not a conflict.

---

## B. Missing artifacts (eliminated candidates lacking a record class)

These candidates **are** consolidated in the registry but lack one expected
artifact class. Not a defect per se (early threads predate the dedicated
graveyard-doc convention), recorded for completeness:

1. **Dedicated graveyard markdown missing for all cross-sectional + timing
   candidates** (D-203/204/205/206/208/209, NRR-007/008, D-Y1-001, D-211/213).
   Only `viop_ssf_oi_k2` and `index_recon_xu030_in` have a `docs/yol1/graveyard/*.md`.
   The verdict text lives in the per-directive report under `docs/research/` and in
   RESEARCH_REGISTRY instead. → **Phase-4 recommendation:** consider whether the
   graveyard-doc convention should be backfilled (maintainer; not done here).
2. **value_only_regime (D-Y1-001) has no committed test module** in master.
   Stage-0 + results JSON are present, but no determinism vector is wired into CI
   → `reproducible: NO-FIXTURE` (see Phase-3 report).
3. **index_recon_xu030_in has no committed test module** (standalone scratch
   script, CI-impact zero) → `reproducible: NO-FIXTURE`.

---

## C. Directive-referenced candidates ABSENT from master (the material finding)

RR-Y1-015 §1 enumerates axes whose artifacts are **not present in this
repository's master branch**. Verified by repo-wide search (docs, src, tests, git log):

| referenced item | directive framing | status in master | evidence |
|-----------------|-------------------|------------------|----------|
| **C7** | event-tilt "düşen-bıçak", S#13 | **ABSENT** | no report/Stage-0/results/code; the only `C7` tokens in master are the unrelated RR-Y1-005 validation-engine contract namespace |
| **C8** | event-tilt "core-satellite", S#13 | **ABSENT** | no artifact; "core-satellite" appears only as prose in RR-Y1.md |
| **C9** | event-tilt "sektör-tilt", S#13 | **ABSENT** | no artifact |
| **NRR-009** | fon-arb (fund/CEF NAV-arb) | **ABSENT** | RR-045 records "NRR-009 ucuz-on-bakis TETIKLENDI" but no `docs/research/NRR-009*` report / Stage-0 / results exist |
| **DEC-053** | sign-flip ban | **ABSENT** | not in `docs/decisions/` nor inline in `docs/DECISIONS.md` (which ends at DEC-046); referenced by RR-Y1-015 and by the index-recon graveyard discipline |
| **DEC-054** | index-recon decision | **ABSENT** | not in `docs/decisions/` nor `docs/DECISIONS.md` |
| **S#13 / S#15 / S#16** | session labels | **ABSENT** | session labels are not recorded in master docs (used in registry from the directive's framing only) |

**Interpretation (report-only):** the directive was authored with knowledge of
the broader program (multiple parallel branches). These items most
likely live in an unmerged feature branch. They are recorded
in `graveyard_registry.json → absent_from_master` (C7/C8/C9, NRR-009) and flagged
inline (DEC-053/054) rather than fabricated. **No metric or verdict was invented
for any absent item.**

`docs/DECISIONS.md` itself notes (lines 42–45) that DEC-035..DEC-045 are
allocated in other feature/research branches not yet merged — DEC-053/054 are
consistent with that same pattern.

---

## D. Minor internal-record drift (non-blocking, report-only)

1. **FEATURE_INDEX.md is stale relative to the graveyard.** It is dated
   "Session #11 closure (1 June 2026)" and predates every RR-Y1 graveyard axis
   (hi52/viop/index-recon/D-211/D-213/D-206 etc.). It carries **no "MEZARLIK ✅"
   rows** that RR-Y1-015 §2 Adım 1.1 anticipated. The graveyard knowledge is
   instead spread across `docs/yol1/`, `docs/research/`, and RESEARCH_REGISTRY.
   → Not fixed here (FEATURE_INDEX is outside this task's affected files).
2. **DECISIONS.md "Total Decisions" counters are internally inconsistent**
   (header says 21; the metrics table near line 130 says 13). Pre-existing,
   unrelated to the graveyard. Recorded, not fixed.
3. **DEC-053 is referenced as a discipline by the index-recon graveyard** (sign-flip
   ban) but the index-recon graveyard markdown itself does not cite the DEC id —
   the DEC linkage comes from the RR-Y1-015 directive. Recorded as a dangling
   decision reference (B/C above).

---

## E. Audit verdict

- **Consistent:** all 14 present candidates' recorded metrics agree across their
  available artifacts and the RESEARCH_REGISTRY. No metric contradiction found.
- **Gaps (report-only):** missing graveyard-docs for early threads (B1); two
  candidates without committed tests (B2/B3); seven directive-referenced items
  absent from master (C).
- **No fixes applied.** Per RR-Y1-015 §3 Adım 2.2 and §6, contradictions and gaps
  are reported; correction is a maintainer decision.

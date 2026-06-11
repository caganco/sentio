# Localization Report — Negative-Knowledge Registry (RR-Y1-015, Phase 5)

**Scope:** Phase-2 (`CONSISTENCY_AUDIT.md` §C) flagged a set of directive-referenced
graveyard candidates and decision records as **absent from master**. This phase
searches **all accessible local repositories and branches** to localize each item
and **verify its real status** — confirming a measured closure where one exists, or
**downgrading** the claim where the record is partial / prose-only / unlocated.

**This is localization + status verification, NOT revival.** No candidate was
re-run, re-parametrized, or sign-flipped (DEC-053 / DISC-9). A "downgrade" is a
**finding about record quality**, never a proposal to re-open a grave. All metrics
and rulings below are **transcribed** from located artifacts; none was recomputed
or fabricated. UNLOCATED items are marked honestly (no invented locations).

All repositories were read **read-only**; only this branch's
`graveyard_registry.json` + docs were written.

---

## A. Search surface

| surface | branches covered | edge-discovery lab present |
|---------|------------------|----------------------------|
| Main repo (master) | master + all `origin/*` | yes (`lab-demo-goal/`) |
| Parallel local working copies (shared origin) | full `origin/*` + all local feature/research branches (rr-y1-011-*, rr-y1-013/014, viop-*, rry1009/1010, rr-y1-010, ...) | yes (`lab-demo-goal/`) |
| Edge-discovery lab branch (`research/edge-discovery-lab`, PR #189) | lab tracks L1-L23 | n/a |
| Yol-2 repos | their `main` + chore branches | no |
| Flow/insider repo | master + 2 branches | no |
| Historical git backups + a dated backup folder | snapshot | partial |

The directive's repo aliases (`lab-demo-clone1`, `fizibilite-lab-1`, `ballast-bist`)
do not exist verbatim on disk; the lab they point to is the `lab-demo-goal/`
directory (present in the local working copies, tracked on `research/edge-discovery-lab`).
Search method per item: filename + content grep across each branch tree
(`git grep -i`), commit-message search (`git log --all -i --grep`), and the
`docs/research/`, `docs/yol1/`, `docs/decisions/`, `RESEARCH_REGISTRY.md` paths.

---

## B. Per-item status

### Status taxonomy
- **LOCATED-VERIFIED** — found with a measured-elimination (or decision) artifact, internally consistent.
- **LOCATED-PARTIAL** — found but incomplete (rule embedded but no ledger entry; preview but no full test; code but no results).
- **LOCATED-PROSE-ONLY** — only a narrative mention, no measurement/decision artifact.
- **UNLOCATED** — not found in any accessible repo/branch/backup.

| item | group | status | location | transcribed evidence |
|------|-------|--------|----------|----------------------|
| **C7** falling-knife / dusen-bicak | A (event-tilt) | **UNLOCATED** | — | No report/Stage-0/results/code anywhere. Lab L1-L23 has no falling-knife track. Bare `C7` tokens = unrelated RR-Y1-005 contract namespace. |
| **C8** core-satellite | A (event-tilt) | **UNLOCATED** | — | Prose only in `RR-Y1.md`; no artifact in any repo/branch. |
| **C9** sektor-tilt | A (event-tilt) | **UNLOCATED** | — | No artifact in any repo/branch/backup. |
| **NRR-009** fund/CEF NAV-arb | A (cross-sectional) | **LOCATED-PARTIAL** | this repo's local working tree, git-excluded `investigate/NRR-009-mkyo-nav-prob.md` (uncommitted scratch) | Observational preview, self-labelled *tam-test-DEGIL*; **PROB-HUKMU OLUMSUZ / SERAP-flag**; 8/8 MKYO median PBV **2.0-6.9 = persistent 2x-7x premium** (thesis-opposite); long-only discount-MR absent. No Stage-0 / results / test committed. |
| **DEC-053** sign-flip ban | B (decision) | **LOCATED-PARTIAL** | `cross_references.json -> LAW-sign-flip-ban` (master) + `STAGE0_PEAD_SUE1_TERCILE.json` on the unmerged PEAD branch `feature/rr-y1-014-pead-stage0` (read-only) | Operative rule frozen in PEAD Stage-0 *fail_tanimi*: "... -> MEZAR (DEC-053). Sign-flip yasak ...". Enforced; only a standalone DEC-053 ledger row is missing (ledger tops at DEC-046). |
| **DEC-054** index-recon decision | B (decision) | **UNLOCATED** | — (only a `dec_ref` pointer) | No decision text in any repo/branch. The closure it would formalize IS a master artifact: `docs/yol1/graveyard/INDEX_RECON_XU030_IN.md` (KB1 NW-t 0.052, KB2 sign-flip, SERAP). |
| **D-185 / D-186 / D-187 + PA-/TA-paradigm** | C | **LOCATED-VERIFIED** | `RESEARCH_REGISTRY.md` rows RR-038 / RR-039 / RR-Y1 (master) | D-185 INCONCLUSIVE -> **D-186 KESIN: GECMEZ** (entry-alpha, multi-agent verified) -> **D-187 active-timing GECMEZ** (200-MA switch real -5.7%, random-null pctile 0.17). 3rd prediction-failure; RR-038 thesis confirmed. |
| **edge2_composite** | C | **LOCATED-VERIFIED** | already a registry entry (`REAL-EDGE-NOT-DEPLOYED`) | Sourced from D-203; constituents individually closed. No gap. |
| **S#13 / S#15 / S#16** | D (session labels) | **UNLOCATED** | — | Never committed; conversational / directive-framing labels only (S#14 appears once inline in an RR-Y1-005 narrative). Not a record-keeping gap. |

---

## C. Material findings (report-only)

1. **C7 / C8 / C9 are not merely "unmerged" — they are UNLOCATED across every
   accessible repository, branch, backup, and the L1-L23 lab.** Phase-2 recorded
   them as "likely lives in an unmerged branch"; Phase-5 hardens that to
   *no falling-knife / core-satellite / sector-tilt measurement artifact exists
   anywhere reachable*. The graveyard claim for these three is **undocumented** —
   but note there was never a recorded metric to lose; nothing is contradicted,
   only confirmed-absent.

2. **NRR-009 was previewed locally and leans MORE negative, not less.** The
   RR-045-triggered "ucuz-on-bakis" was actually run as a git-excluded local
   scratch preview. Its own verdict is **SERAP-flag (paradigm closes)**: BIST
   closed-end-style funds (MKYO) trade at a large **persistent premium** — the
   *opposite* of the cheap-discount thesis — and any "reversion" would require
   shorting a premium, which is long-only-incompatible and short-constrained on
   these thin names. This is a **double-elimination** (RR-045 N=9-weak **plus**
   wrong-sign premium). The localization therefore **reinforces** the closure; it
   is **not** a revival warrant, and the preview is **not** a committed measured
   grave (no frozen Stage-0 / 5-gate).

3. **DEC-053 is enforced-without-a-ledger-row; DEC-054 has no text at all.**
   DEC-053's sign-flip ban is operative — frozen into the PEAD Stage-0
   fail-definition and codified in master's `cross_references.json` — but the
   numbered ledger entry is unwritten (ledger ends at DEC-046, with DEC-035...045
   themselves allocated to unmerged branches per `DECISIONS.md`). DEC-054 exists
   only as a `dec_ref` pointer; the index-recon verdict it would formalize is
   already fully documented as a master graveyard artifact. **Whether to backfill
   either DEC row is a maintainer decision.**

4. **S#13 / S#15 / S#16 are conversational-only**, confirmed never committed in
   any repo. They are directive-framing labels, not a missing record class.

---

## D. Localization verdict

- **UNLOCATED (5):** C7, C8, C9, DEC-054, S#13/15/16 — confirmed absent everywhere
  searched; no fabrication, no invented location.
- **LOCATED-PARTIAL (2):** NRR-009 (uncommitted preview, leans more negative),
  DEC-053 (rule enforced, ledger row missing).
- **LOCATED-VERIFIED (Grup-C):** D-185/186/187 + PA-/TA-paradigm + edge2_composite
  — verdict sources present in master; no gap.
- **No status was upgraded toward "tradeable"; no grave was re-opened.** Every
  change recorded here is a record-quality finding. Correction (e.g. writing the
  DEC-053/054 ledger rows, or committing the NRR-009 preview) is left to the
  maintainer.

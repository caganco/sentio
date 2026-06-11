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
| **Construction-as-edge lab (`lab-demo-clone1/`)** — git-excluded sibling lab, present in one working copy; source of the committed C9/C12 golden fixtures | C-series tracks C1-C12 (frozen Stage-0 each) | **the C7/C8/C9 home** |
| Yol-2 repos | their `main` + chore branches | no |
| Flow/insider repo | master + 2 branches | no |
| Historical git backups + a dated backup folder | snapshot | partial |

The directive's repo aliases (`fizibilite-lab-1`, `ballast-bist`) do not exist
verbatim on disk. **`lab-demo-clone1` IS real** — a repo-root sibling lab (like
`lab-demo-goal/`), git-excluded and present in one working copy; the engine
references it directly (`tests/test_engine_stats.py` →
`lab-demo-clone1/harness/dump_c12_golden_fixture.py`). It is the "CONSTRUCTION-as-EDGE"
lab whose C-series (C1-C12) produced the committed C9/C12 golden determinism anchors.
Search method per item: filename + content grep across each branch tree
(`git grep -i`), commit-message search (`git log --all -i --grep`), the
`docs/research/`, `docs/yol1/`, `docs/decisions/`, `RESEARCH_REGISTRY.md` paths,
and the on-disk `lab-demo-goal/` and `lab-demo-clone1/` lab trees.

---

## B. Per-item status

### Status taxonomy
- **LOCATED-VERIFIED** — found with a measured-elimination (or decision) artifact, internally consistent.
- **LOCATED-PARTIAL** — found but incomplete (rule embedded but no ledger entry; preview but no full test; code but no results).
- **LOCATED-PROSE-ONLY** — only a narrative mention, no measurement/decision artifact.
- **UNLOCATED** — not found in any accessible repo/branch/backup.

| item | group | status | location | transcribed evidence |
|------|-------|--------|----------|----------------------|
| **C7** falling-knife / negative-veto | A (event-tilt) | **LOCATED-VERIFIED** | `lab-demo-clone1` `harness/c7_negative_veto.py` + Stage-0 + results + `notes/C7_negative_veto.md` | `deployable_veto_edge=FALSE` / `identifiable_not_monetizable=TRUE`. V3 falling-knife: LIQUID 4/5 (fails regime-stability; +1.13%/yr, precision 0.573 NW-t 2.58); ALL 5/5 but ALL-universe = liquidity-mirage, **not** tradeable LIQUID. Measured-NEGATIVE. |
| **C8** core-satellite | A (event-tilt) | **LOCATED-VERIFIED** | `lab-demo-clone1` `harness/c8_core_satellite.py` (+c8b/c8c) + Stage-0 + results + notes | `deployable_smarter_beta_liquid=FALSE` (4/5; fails only decisiveness vs random 80/20 tilt, 91.4th < 95th). RISK-REDUCING-BUT-NOT-FREE (+0.26%/yr, DD −34.04% vs EW −34.31%). Measured-NEGATIVE. |
| **C9** sektor-tilt / event sector-tilt | A (event-tilt) | **LOCATED-VERIFIED** | `lab-demo-clone1` `harness/c9_event_sector_tilt.py` + `stage0/STAGE0_C9.json` + results + notes | `keep_bar.PASS=FALSE`, D1 sign-test FAIL (3/9, p=0.910), net_t_nw +0.629, net rel-EW [T+1,+20] +1.26% (driven by 2-3 shocks), N=9. VERDICT NEGATIVE (already priced). |
| **NRR-009** fund/CEF NAV-arb | A (cross-sectional) | **LOCATED-PARTIAL** | this repo's local working tree, git-excluded `investigate/NRR-009-mkyo-nav-prob.md` (uncommitted scratch) | Observational preview, self-labelled *tam-test-DEGIL*; **PROB-HUKMU OLUMSUZ / SERAP-flag**; 8/8 MKYO median PBV **2.0-6.9 = persistent 2x-7x premium** (thesis-opposite); long-only discount-MR absent. No Stage-0 / results / test committed. |
| **DEC-053** sign-flip ban | B (decision) | **LOCATED-PARTIAL** | `cross_references.json -> LAW-sign-flip-ban` (master) + `STAGE0_PEAD_SUE1_TERCILE.json` on the unmerged PEAD branch `feature/rr-y1-014-pead-stage0` (read-only) | Operative rule frozen in PEAD Stage-0 *fail_tanimi*: "... -> MEZAR (DEC-053). Sign-flip yasak ...". Enforced; only a standalone DEC-053 ledger row is missing (ledger tops at DEC-046). |
| **DEC-054** index-recon decision | B (decision) | **UNLOCATED** | — (only a `dec_ref` pointer) | No decision text in any repo/branch. The closure it would formalize IS a master artifact: `docs/yol1/graveyard/INDEX_RECON_XU030_IN.md` (KB1 NW-t 0.052, KB2 sign-flip, SERAP). |
| **D-185 / D-186 / D-187 + PA-/TA-paradigm** | C | **LOCATED-VERIFIED** | `RESEARCH_REGISTRY.md` rows RR-038 / RR-039 / RR-Y1 (master) | D-185 INCONCLUSIVE -> **D-186 KESIN: GECMEZ** (entry-alpha, multi-agent verified) -> **D-187 active-timing GECMEZ** (200-MA switch real -5.7%, random-null pctile 0.17). 3rd prediction-failure; RR-038 thesis confirmed. |
| **edge2_composite** | C | **LOCATED-VERIFIED** | already a registry entry (`REAL-EDGE-NOT-DEPLOYED`) | Sourced from D-203; constituents individually closed. No gap. |
| **S#13 / S#15 / S#16** | D (session labels) | **UNLOCATED** | — | Never committed; conversational / directive-framing labels only (S#14 appears once inline in an RR-Y1-005 narrative). Not a record-keeping gap. |

---

## C. Material findings (report-only)

1. **C7 / C8 / C9 ARE located — in `lab-demo-clone1`, fully measured (CORRECTION).**
   Phase-2 read them as "absent from master"; a first Phase-5 pass wrongly hardened
   that to "UNLOCATED" because it searched the *other* sibling lab (`lab-demo-goal`)
   under an event-tilt token frame. The correction (prompted by the observation that
   C7/C8/C9 sit in the same C-series as C11/C12) found them in **`lab-demo-clone1/`**,
   the CONSTRUCTION-as-EDGE lab — each a committed-motor C-series track with a frozen
   Stage-0 + results + notes, the directive's labels exactly right:
   - **C7 `c7_negative_veto`** (düşen-bıçak / falling-knife): `deployable_veto_edge=FALSE`,
     `identifiable_not_monetizable=TRUE`. The best lens (V3 falling-knife) clears 5/5
     only in the ALL universe — a liquidity-mirage — and 4/5 in tradeable LIQUID
     (fails regime-stability). Not deployable.
   - **C8 `c8_core_satellite`**: `deployable_smarter_beta_liquid=FALSE` (4/5; fails
     only statistical decisiveness vs a generic random 80/20 tilt). Risk-reducing but
     not free.
   - **C9 `c9_event_sector_tilt`** (sektör-tilt): `keep_bar.PASS=FALSE`, sign-test
     3/9 p=0.910, NW-t +0.629. Winner-sector drift already priced. Negative.

   All three are **measured-NEGATIVE** — they belong squarely in the negative-knowledge
   set, fully consistent with the rest of the graveyard (liquidity-mirage /
   sub-significance). LOCATED-VERIFIED, **no revival**: the V3 ALL-universe 5/5 is
   reported honestly as a non-tradeable liquidity-mirage, not a deployable edge. The
   lab is git-excluded local by design (production repo read-only, committed engine
   zero-touch), like `lab-demo-goal`; that is why they are absent from master yet not
   "missing."

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

- **LOCATED-VERIFIED (C7, C8, C9 + Grup-C):** C7/C8/C9 are committed-motor C-series
  tracks in `lab-demo-clone1`, each measured-NEGATIVE with a frozen Stage-0 + results;
  Grup-C (D-185/186/187 + PA-/TA-paradigm + edge2_composite) verdict sources are in
  master. No gap.
- **LOCATED-PARTIAL (2):** NRR-009 (uncommitted preview, leans more negative),
  DEC-053 (rule enforced, ledger row missing).
- **UNLOCATED (2):** DEC-054 (no decision text; underlying verdict is a master
  artifact), S#13/15/16 (conversational-only). No fabrication, no invented location.
- **No status was upgraded toward "tradeable"; no grave was re-opened.** C7/C8/C9 are
  located *as measured-negatives* — the localization confirms their elimination, it
  does not soften it (the V3 ALL-universe 5/5 is a non-tradeable liquidity-mirage,
  reported as such). Every change here is a record-quality finding. Correction (e.g.
  writing the DEC-053/054 ledger rows, committing the NRR-009 preview, or formally
  consolidating the `lab-demo-clone1` C-series into the registry) is left to the
  maintainer.

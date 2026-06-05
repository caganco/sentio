# RR-Y1-010 — TASK: Intra-regime time-holdout evaluation mode

**Type:** validation-engine capability extension (additive mode). Plan-first (plan → approval → build).
**Purpose.** Directly test the core research question — *does a cross-sectional factor, frozen on a training window, exhibit similar forward cross-sectional behavior on a later held-out window WITHIN THE SAME regime?* The existing modes do not answer this: name-split (Mod-A) tests "is this name-specific overfit" at a single time; embargoed-CPCV (Mod-B) tests timing signals. Neither tests forward-in-time persistence of a cross-sectional factor within one regime. This mode fills that gap.
**Scope basis:** the synthesis document §3/§4.8 ("aynı-rejimde-ileri-tutar-mı" channel) and DEC-046 (split in the dimension where overfit hides — here the dimension is forward-time within a fixed regime). Conflict priority: TASARIM v0.2 > math-spec v1.1 > this task.
**Invariants:** additive only; committed motors and existing modes (Mod-A/Mod-B), keep-bars, the three agreement conditions, and the C12 golden are UNCHANGED; `tests/test_engine_no_lab_import.py` auto-covers any new module; zero regression. C10-safe: infrastructure, not edge-discovery.

---

## Mechanics (to be detailed in plan)
- Operate within a single declared regime window (regime is a manual input per Section 4.3 / DEC S#14-rejim).
- Split that window into a training segment and a later held-out segment, separated by an **embargo** equal to the signal construction window (forward-return horizon), so no construction-period leakage crosses the boundary (the look-ahead-safe discipline already used in Mod-B).
- Fit/freeze the cross-sectional factor on the training segment; measure cross-sectional rank-IC (and the §7 vector quantities) on the held-out segment only.
- Pre-registered (Stage-0): regime window, train/holdout boundary, embargo, expected verdict. Honest UNDERPOWERED declaration is mandatory — a single-regime small-market window yields few non-overlapping holdouts; this is a directional check, not a high-confidence verdict.

## Critical design fork to resolve in plan — interaction with the RR-Y1-009 confidence qualifier
The RR-Y1-009 qualifier downgrades to `confounded` when the evaluation window is single-regime. **This mode is intentionally single-regime by construction** — so the existing trigger would fire `confounded` on every run, which is semantically wrong here: the question is not "is this regime-independent" (it deliberately is not) but "does it persist forward within this one regime". The plan must reconcile this without weakening RR-Y1-009 for the other modes. Options to weigh (do not silently pick):
- a mode-aware confidence semantics: in intra-regime-holdout mode, single-regime is the design (not a confound); the confound in THIS mode is different — e.g. train/holdout too close (embargo violation), the holdout spanning a hidden sub-regime break, or a shared common-factor flag.
- keep RR-1009 untouched and have this mode emit its own confidence field with mode-appropriate triggers.
Decision deferred to review; the chosen reconciliation must be explicit and pre-registered, and must NOT relax the single-regime→confounded trigger for Mod-A.

## Honest limit (state in the deliverable doc)
BIST 2019–2026 is dominated by few regimes with limited within-regime length; non-overlapping forward holdouts inside one regime are scarce → this mode is structurally underpowered on current data. Its value is (a) the conceptually-correct instrument for the core question and (b) readiness for when more within-regime data (or the 2026–2027 forward period) is available. It does not overcome the data wall; it aligns the test with the question.

## Deliverables
- New evaluation mode wired into the engine (additive contracts/dispatch); pre-registration support; the §7 output vector populated for the holdout segment; the confidence-qualifier reconciliation above.
- Tests: synthetic fixture with a planted persistent cross-sectional factor → holdout reproduces (directional pass); a planted non-persistent / train-only-fitted factor → holdout fails; embargo-violation guard; confidence-semantics test for the mode. Additive-only proof that Mod-A/Mod-B verdicts are unchanged. C12 golden green; zero regression.
- `docs/research/RR-Y1-010-*.md`: design, the confidence reconciliation decision + rationale, the underpowered-limit statement tying to the synthesis document, pre-registration protocol.
- RESEARCH_REGISTRY row.

## Verification
Plan → approval → feature branch → full regression (golden green, zero regression) → ruff/mypy/no-lab-import → PR. Author attribution per project convention; no internal identifiers; ASCII-only in engine/tests, Turkish allowed in the RR doc.

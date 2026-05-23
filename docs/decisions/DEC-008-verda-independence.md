---
id: DEC-008
title: VERDA Independence — L5 Core Decoupled from VERDA Vendor
date: 2026-05-18
area: Signal Architecture
status: decided
priority: HIGH
affects:
  - src/signals/layers/smart_money_layer.py
  - src/signals/layers/connectors/
  - tests/test_architecture.py
rationale: "Phase 4.5 build must not block on an external vendor (VERDA) response; L5 core runs on direct İş Yatırım + BIST DataStore endpoints"
implementation_status: 100%
test_coverage: tests/test_architecture.py::TestL5VerdaIndependence::test_l5_no_verda_dependency
---

# DEC-008: VERDA Independence — L5 Core Decoupled from VERDA Vendor

**Decision Date:** 18 May 2026
**Decided By:** Strategist (Cagan)
**Status:** ✅ DECIDED

---

## CONTEXT

L5 Smart Money was originally scoped against a VERDA data feed. VERDA is a
paid vendor whose contract/RFP response is still pending (see backlog
"Finnet/Matriks RFP"). The Phase 4.5 Ruthless Alpha build (D-052) consumes
L5 (foreign ratio + short interest) and could not be allowed to block on an
external commercial negotiation.

D-059 (commit b0c9aae) physically cut the L5 → VERDA import path. This
decision records the rationale and the architectural guarantee that keeps it
cut.

---

## DECISION

- **L5 Core is VERDA-FREE.** Foreign ratio + short interest sub-signals are
  sourced from direct endpoints: İş Yatırım screener (criterion 40) and the
  BIST DataStore weekly CSV. No VERDA dependency in the core path.
- **L5 Extended remains intentionally VERDA-deferred.** VIOP (L5b) and the
  Sentiment news feed (L4) are separate, independently-blocked initiatives;
  they may use VERDA later without re-coupling the core.
- **Architectural guarantee:** `test_l5_no_verda_dependency()` runs in Tier 1
  on every bootstrap and fails the build if the string `verda` reappears in
  any L5 core connector.

---

## RATIONALE

1. **Unblock D-052.** Phase 4.5 is the highest-priority initiative; a vendor
   negotiation timeline is not an acceptable critical-path dependency.
2. **Free, direct data is sufficient for the core.** İş Yatırım + BIST
   DataStore cover foreign ratio and short interest at the cadence L5 needs
   (progressive build: momentum ~Gün 10, full composite ~Gün 20).
3. **Optionality preserved.** Deferring (not banning) VERDA for L5 Extended
   keeps the door open for VIOP/sentiment without re-introducing core risk.

---

## CONSEQUENCES

- L5 core data quality is bounded by free endpoints; Finnet/VERDA upgrade
  criterion (AUM ≥ 5M TL AND L5 ≥ 1.5% annual alpha) governs any future move.
- The independence is enforced by a test, not just convention — any
  regression is caught at bootstrap, not in production.
- L5b VIOP stays blocked on VERDA; that is a separate decision surface.

---

## RELATED DECISIONS

- **DEC-007:** Ruthless Alpha Philosophy (Phase 4.5 consumes L5)
- **DEC-009:** Phase 4.5 normalizer derivation (L5 confidence-scaling)

---

**Status:** ✅ DECIDED (18 May 2026)
**Approved By:** Cagan (Strategist)
**Implementation Owner:** Builder (D-059 cut, D-052 documents)

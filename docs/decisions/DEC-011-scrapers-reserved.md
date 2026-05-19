---
id: DEC-011
title: src/scrapers/ — Financial-Statement Parser Intentionally Preserved (Not Wired)
date: 2026-05-19
area: Signal Architecture
status: decided
priority: LOW
affects:
  - src/scrapers/__init__.py
  - src/scrapers/kap_models.py
  - src/scrapers/kap_parser.py
  - src/scrapers/kap_scraper.py
rationale: "src/scrapers/ is a self-contained financial-statement parser (KAPScraper) used only by its own test. It does not overlap src/data/kap_parser.py (event classification) and is reserved for a future L3 financial-table integration; not dead code."
implementation_status: n/a (no code change — ADR documents existing state)
test_coverage: tests/test_kap_scraper.py
---

# DEC-011: src/scrapers/ — Financial-Statement Parser Intentionally Preserved

**Decision Date:** 19 May 2026
**Decided By:** Cagan (Orchestrator, D-066 Sprint 3 follow-up)
**Status:** ✅ DECIDED

---

## CONTEXT

D-066 BLOK 2 analyzed `src/scrapers/` (KAP financial-statement scraper):

- `__init__.py` (3 ln) → exports `KAPScraper`
- `kap_models.py` (39 ln) → pydantic `FinancialDisclosure`, `SpecialDisclosure`,
  `FinancialTables`
- `kap_parser.py` (112 ln) → `normalize_value`, `detect_currency_unit`,
  `parse_balance_sheet`, `parse_income_statement`, `parse_cash_flow`,
  `parse_special_disclosure`
- `kap_scraper.py` (291 ln) → `class KAPScraper`

**Usage:** imported only inside `src/scrapers/` itself and by
`tests/test_kap_scraper.py`. Zero imports from non-scrapers `src/` or
`agents/` — not wired into the live signal/data pipeline.

**No overlap with `src/data/kap_parser.py`** (230 ln): that module does KAP
*event* classification (`classify_category`, `parse_disclosure`,
`_parse_dividend`, `_parse_capital_increase`, `class KapEvent`). `scrapers/`
does *financial-table* parsing (balance sheet / income / cash flow). The only
superficial similarity is a string→float helper (`normalize_value` vs
`_parse_number`) — different name/signature, not duplicated logic. Model
classes are disjoint.

---

## DECISION

**`src/scrapers/` is intentionally preserved.** It is a self-contained
financial-statement parser **reserved for a future L3 financial-table
integration**. It is not dead code and must not be removed as "unused":

- It is covered by `tests/test_kap_scraper.py` (part of the 741-test suite).
- It is functionally distinct from `src/data/kap_parser.py`; no merge/dedup
  is warranted.
- Removal or consolidation requires a superseding decision.

---

## CONSEQUENCES

- The module stays in the tree and the test suite, with no live-pipeline
  coupling — zero runtime cost.
- A future L3 financial-table sub-signal can adopt `KAPScraper` without
  re-implementing balance-sheet/income/cash-flow parsing.
- Any "delete unused module" sweep must skip `src/scrapers/` and cite this
  decision.

---

## ALTERNATIVES REJECTED

1. **Delete as unused.** Rejected — it is reserved for L3 financial-table
   work and is test-covered; deletion would discard a usable parser.
2. **Merge into `src/data/kap_parser.py`.** Rejected — different domain
   (financial tables vs disclosure events); no real code overlap.

---

## RELATED DECISIONS

- **DEC-008:** VERDA independence (L5 data sourcing) — adjacent data-layer
  scope; L3 financial-table integration is a separate future track.

---

**Status:** ✅ DECIDED (19 May 2026)
**Approved By:** Cagan (Orchestrator)
**Implementation Owner:** N/A — no code change; future L3 integration
requires a new Builder SPEC.

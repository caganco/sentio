# Architecture Decision Log

**System:** BIST Trading OS v5.0  
**Location:** `docs/decisions/`  
**Last Updated:** 16 May 2026  
**Purpose:** Centralized machine-readable log of all architectural decisions

> **For Claude Code users:** Query decisions by `area`, `status`, or `affected_files` to understand context for code changes.

---

## QUICK INDEX

| ID | Title | Area | Status | Date | Affects |
|---|---|---|---|---|---|
| **DEC-001** | KAP Edge Cases & Holiday Handling | Data Sources | ✅ Implemented | 2026-05-14 | `src/data/kap.py`, `tests/test_kap.py` |
| **DEC-002** | CDS iShares Proxy Fallback | Data Sources | ✅ Implemented | 2026-05-13 | `src/data/macro.py`, `tests/test_cds.py` |
| **DEC-003** | Macro-Equity Correlation Layer | Signal Architecture | ✅ Implemented | 2026-05-12 | `src/signals/layer2_macro.py` |
| **DEC-004** | Report Token Optimization (≤600) | Efficiency | ✅ Implemented | 2026-05-11 | `src/reporting/report_generator.py` |
| **DEC-005** | Signal Layer Weights (4-Layer Stack) | Signal Architecture | ✅ Implemented | 2026-05-10 | `src/signals/signal_combination.py`, `config.yaml` |
| **DEC-006** | Kelly Criterion Position Sizing | Risk Management | 💡 Pending | TBD | `src/risk/kelly_criterion.py` |
| **DEC-007** | Ruthless Alpha Philosophy — Remove Defensive Constraints | Signal Engine | ✅ Decided | 2026-05-16 | `src/signals/engine.py`, `src/signals/thresholds.py`, `tests/test_engine.py` |
| **DEC-008** | VERDA Independence — L5 Core Decoupled from Vendor | Signal Architecture | ✅ Decided | 2026-05-18 | `src/signals/layers/smart_money_layer.py`, `tests/test_architecture.py` |
| **DEC-009** | Phase 4.5 Normalizer — Emergent 0.78 Floor (not hardcoded) | Signal Engine | ✅ Decided | 2026-05-18 | `src/signals/thresholds.py`, `src/signals/engine.py`, `src/utils/weight_validator.py` |

---

## DECISION CATEGORIES

### By Area

**Data Sources** (2 implemented)
- [DEC-001](decisions/DEC-001.md) – KAP holiday handling + bulk queue
- [DEC-002](decisions/DEC-002.md) – CDS fallback to iShares model

**Signal Architecture** (3 implemented)
- [DEC-003](decisions/DEC-003.md) – Correlation scoring per stock
- [DEC-005](decisions/DEC-005.md) – Weight distribution (20%, 33%, 27%, 20%)
- [DEC-007](decisions/DEC-007.md) – Conviction-based scoring (Phase 4.2.3)

**Efficiency** (1 implemented)
- [DEC-004](decisions/DEC-004.md) – Token budget optimization

**Risk Management** (1 pending)
- [DEC-006](decisions/DEC-006.md) – Position sizing (Kelly Criterion)

### By Status

**✅ Implemented (5)**
- DEC-001, DEC-002, DEC-003, DEC-004, DEC-005

**✅ Decided (1)**
- DEC-007

**💡 Pending (1)**
- DEC-006

---

## QUICK REFERENCE

### Find decisions affecting a file:

```bash
# Example: What decisions affect src/signals/signal_combination.py?
grep -r "signal_combination.py" docs/decisions/DEC-*.md
# Answer: DEC-005
```

### Search by area:

```bash
# Data source decisions
grep -l "area: Data Sources" docs/decisions/DEC-*.md
# Answer: DEC-001, DEC-002

# Signal architecture
grep -l "area: Signal Architecture" docs/decisions/DEC-*.md
# Answer: DEC-003, DEC-005
```

### Find pending decisions:

```bash
grep -l "status: pending" docs/decisions/DEC-*.md
# Answer: DEC-006
```

---

## DECISION METRICS

**Current State (16 May 2026):**

| Metric | Count |
|---|---|
| Total Decisions | 7 |
| Implemented | 5 (71%) |
| Decided | 1 (14%) |
| Pending | 1 (14%) |
| High Priority | 6 |
| Data Source | 2 |
| Signal Architecture | 3 |
| Efficiency | 1 |
| Risk Management | 1 |

---

## FOR CLAUDE CODE AGENTS

When modifying code, check for related decisions:

**Step 1:** Find decisions affecting your file
```bash
grep -r "your_file.py" docs/decisions/DEC-*.md
```

**Step 2:** Read the decision file for context
```bash
cat docs/decisions/DEC-XXX.md
```

**Step 3:** Reference in commit message
```
git commit -m "Implement feature (DEC-XXX)

- Change 1
- Change 2

Implements: DEC-XXX
Tests: +N passing"
```

---

## RELATED DOCUMENTATION

- `docs/DEPENDENCY_MAP.md` – System architecture & dependencies
- `docs/BOOT_ARCHITECT.md` – Architecture overview
- `docs/BOOT_BUILDER.md` – Builder development guidelines
- `CLAUDE.md` – Project instructions & bootstrap protocol
- `memory/MEMORY.md` – Session state & context

---

**Owner:** Architect  
**Maintained By:** Architect  
**Last Review:** 16 May 2026

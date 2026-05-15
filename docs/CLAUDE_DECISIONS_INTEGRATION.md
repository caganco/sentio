# Claude Code Integration: Decision Log System

**For:** Claude Code agents working on BIST trading system  
**Purpose:** Query architectural decisions to understand code change context  
**Updated:** 15 May 2026

---

## QUICK START

### Query 1: "What decisions affect my code changes?"

**Command:**
```bash
# Find decisions that mention your file
grep -r "signal_combination.py" docs/decisions/DEC-*.md

# Result:
# docs/decisions/DEC-005.md: affects: src/signals/signal_combination.py
```

**Action:** Read `docs/decisions/DEC-005.md` for context before modifying.

---

### Query 2: "Why was this architectural choice made?"

**Command:**
```bash
# Read decision file
cat docs/decisions/DEC-005.md

# Look for sections: CONTEXT → OPTIONS CONSIDERED → DECISION
```

---

### Query 3: "What decisions are pending implementation?"

**Command:**
```bash
# Find pending decisions
grep -l "status: pending" docs/decisions/DEC-*.md
```

---

## HOW TO USE WHEN CODING

### Scenario 1: Modifying Signal Weights

```python
# You're about to change src/signals/signal_combination.py

# Step 1: Check what decisions affect this file
grep -r "signal_combination.py" docs/decisions/DEC-*.md
# Result: DEC-005

# Step 2: Read the decision
cat docs/decisions/DEC-005.md
# You discover: Weights are L1(20%), L2(33%), L3(27%), L6(20%)
# These were chosen based on Sharpe ratio 0.81 backtest

# Step 3: Reference in commit message
git commit -m "Update signal weights per DEC-005"
```

---

### Scenario 2: Emergency Code Break

```
Error: Portfolio score calculation changed unexpectedly

// Step 1: Check what decision governs this
grep -r "portfolio.*score" docs/decisions/DEC-*.md
# Result: DEC-005 (Signal Layer Weights)

// Step 2: Review DEC-005 to understand expected behavior
cat docs/decisions/DEC-005.md
# Formula should be: (L1×0.20 + L2×0.33 + L3×0.27 + L6×0.20) / 0.80

// Step 3: Debug based on decision
// Did you accidentally change weights?
// Did you add a new layer without normalizing?

// Step 4: Restore behavior to match DEC-005
```

---

## DECISION SEARCH PATTERNS

### Pattern 1: Find Decisions by Area

```bash
# Data Sources decisions
grep -l "area: Data Sources" docs/decisions/DEC-*.md
# Result: DEC-001, DEC-002

# Signal Architecture decisions
grep -l "area: Signal Architecture" docs/decisions/DEC-*.md
# Result: DEC-003, DEC-005

# Risk Management decisions
grep -l "area: Risk Management" docs/decisions/DEC-*.md
# Result: DEC-006
```

---

### Pattern 2: Find Decisions by Status

```bash
# Implemented decisions
grep -l "status: implemented" docs/decisions/DEC-*.md
# Result: DEC-001 through DEC-005

# Pending decisions
grep -l "status: pending" docs/decisions/DEC-*.md
# Result: DEC-006
```

---

### Pattern 3: Find Decisions by Affected Files

```bash
# What decisions touch config.yaml?
grep -l "config.yaml" docs/decisions/DEC-*.md
# Result: DEC-001, DEC-002, DEC-005

# What decisions affect tests?
grep -l "test_" docs/decisions/DEC-*.md
# Result: DEC-001 (+42), DEC-002 (+14), DEC-003 (+25)
```

---

## READING A DECISION FILE

### Frontmatter (Machine-Readable)

```yaml
---
id: DEC-005
title: Signal Layer Weights (4-Layer Stack)
date: 2026-05-10
area: Signal Architecture
status: implemented
priority: HIGH
affects:
  - src/signals/signal_combination.py
  - config.yaml
---
```

| Field | Purpose |
|---|---|
| `id` | Unique identifier (DEC-NNN) |
| `area` | Category for grouping |
| `status` | Implementation stage |
| `affects` | Files impacted (query these!) |
| `rationale` | Why this choice was made |

### Body Structure

Each decision file contains:

1. **CONTEXT** – What problem was this solving?
2. **OPTIONS CONSIDERED** – What alternatives were evaluated?
3. **DECISION** – What was chosen and why?
4. **IMPLEMENTATION** – Code changes made
5. **TEST COVERAGE** – Tests added/affected
6. **RISKS & MITIGATIONS** – Known issues and safeguards

---

## REFERENCING DECISIONS IN CODE

### In Commit Messages

```bash
git commit -m "Implement KAP holiday detection (DEC-001)

- Add BIST holiday calendar to config
- Detect closure before API fetch
- Add 42 edge case tests

Implements: DEC-001
Regression: Zero ✅"
```

### In Code Comments

```python
# See decisions/DEC-001.md for KAP holiday handling logic
if self.is_bist_closed(date):
    return self.fetch_from_cache(ticker)
```

### In PR Descriptions

```markdown
## Implements DEC-005: Signal Layer Weights

### Changes
- Update signal weights to L1(20%), L2(33%), L3(27%), L6(20%)
- Add validation for weight normalization

### Decision Reference
See [docs/decisions/DEC-005.md](../decisions/DEC-005.md)

### Test Results
- All 372 tests passing ✅
- Zero regression ✅
```

---

## ADDING A NEW DECISION

### When to Log a Decision

✅ **Log these:**
- Architectural changes affecting 2+ files
- Breaking API changes
- New data sources or signal layers
- Risk/reliability changes
- Performance optimizations (>20% impact)

❌ **Skip these:**
- Bug fixes
- Documentation updates
- Small performance tweaks (<10%)
- Refactoring (same behavior)

---

### How to Create a Decision

**Step 1:** Create new file
```bash
cp docs/decisions/DEC-TEMPLATE.md docs/decisions/DEC-NNN.md
```

**Step 2:** Fill frontmatter
```yaml
id: DEC-NNN
title: "Decision Title"
date: 2026-05-15
area: "Data Sources | Signal Architecture | Risk Management | Efficiency"
status: pending
affects:
  - src/path/to/file.py
  - tests/test_file.py
```

**Step 3:** Write sections
- CONTEXT (1-2 paragraphs)
- OPTIONS CONSIDERED (evaluated alternatives)
- DECISION (chosen option + why)
- IMPLEMENTATION (code changes)
- TEST COVERAGE (test cases)

**Step 4:** Update DECISIONS.md index

**Step 5:** Reference in commit message
```
git commit -m "Add DEC-NNN: Decision title description"
```

---

## CURRENT DECISION STATUS

**Total:** 6 decisions  
**Implemented:** 5 (DEC-001 through DEC-005)  
**Pending:** 1 (DEC-006 Kelly Criterion – June 2026)  

### By Area

| Area | Decisions | Status |
|---|---|---|
| Data Sources | DEC-001, DEC-002 | ✅ Done |
| Signal Architecture | DEC-003, DEC-005 | ✅ Done |
| Efficiency | DEC-004 | ✅ Done |
| Risk Management | DEC-006 | 💡 Pending |

---

## KEY DECISIONS AT A GLANCE

**DEC-001: KAP Holiday Handling**
- Holiday detection + 72h incident cache
- +42 tests, zero regression

**DEC-002: CDS iShares Proxy**
- 3-tier fallback: scraper → proxy → cache
- +14 tests, 0.78 correlation

**DEC-003: Macro-Equity Correlation**
- Per-stock sensitivity matrix
- +25 tests, sector-aware signals

**DEC-004: Report Token Optimization**
- Compressed to ≤600 tokens
- -40% token cost

**DEC-005: Signal Layer Weights**
- L1: 20%, L2: 33%, L3: 27%, L6: 20%
- Sharpe ratio 0.81 backtest

**DEC-006: Kelly Criterion (Pending)**
- Dynamic position sizing by signal strength
- Target: June 2026

---

**Last Updated:** 15 May 2026  
**For Questions:** See DECISIONS.md index

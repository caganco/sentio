# Claude Code Integration: Decision Log System

**For:** Claude Code agents, Architects, Builders working on BIST trading system  
**Purpose:** Query architectural decisions to understand context for code changes  
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
# docs/decisions/DEC-003.md: affects: src/signals/layer2_macro.py
```

**Action:** Read `docs/decisions/DEC-005.md` and `DEC-003.md` for context

---

### Query 2: "Why was this architectural choice made?"

**Command:**
```bash
# Read decision file
cat docs/decisions/DEC-005.md

# Look for section: "CONTEXT" + "DECISION" + "RATIONALE"
```

**Example Output:**
```
Decision: Signal Layer Weights (4-Layer Stack)
Rationale: "BIST sensitivity to macro regime; empirical tuning"
Context: Layer 2 (Macro) weighted 33% because backtests show 0.81 Sharpe ratio
```

---

### Query 3: "What decisions are pending implementation?"

**Command:**
```bash
# Find pending decisions
grep -l "status: pending" docs/decisions/DEC-*.md

# Result:
# docs/decisions/DEC-006.md (Kelly Criterion Position Sizing)
```

---

## DECISION DIRECTORY STRUCTURE

```
docs/decisions/
├─ DEC-001.md  ✅ KAP Edge Cases & Holiday Handling
├─ DEC-002.md  ✅ CDS iShares Proxy Fallback
├─ DEC-003.md  ✅ Macro-Equity Correlation Layer
├─ DEC-004.md  ✅ Report Token Optimization
├─ DEC-005.md  ✅ Signal Layer Weights (4-Layer Stack)
└─ DEC-006.md  🟡 Kelly Criterion Position Sizing (Pending)

DECISIONS.md   📋 Index + Search Guide
```

---

## HOW TO USE WHEN CODING

### Scenario 1: Modifying `src/signals/signal_combination.py`

```python
# You're about to change the signal weighting formula

# Step 1: Check what decisions affect this file
grep -r "signal_combination.py" docs/decisions/DEC-*.md
# Result: DEC-005

# Step 2: Read the decision
cat docs/decisions/DEC-005.md
# You discover:
# - Weights are: L1(20%), L2(33%), L3(27%), L6(20%)
# - These were chosen based on Sharpe ratio 0.81 backtest
# - Layer 5 (Smart Money) will change weights to L5(10%) + L6(10%)

# Step 3: Implement accordingly
# Example change:
# ✅ GOOD: Update formula to accommodate L5 when available
# ❌ BAD: Hardcode new weights without referencing DEC-005

# Step 4: Reference in commit message
git commit -m "Integrate L5 weights per DEC-005"
```

---

### Scenario 2: Adding KAP Data Source Tests

```python
# You're adding tests for KAP API

# Step 1: Understand KAP's architectural constraints
grep -r "kap.py" docs/decisions/DEC-*.md
# Result: DEC-001 (KAP Edge Cases)

# Step 2: Read DEC-001 for test requirements
cat docs/decisions/DEC-001.md
# You find section: "TEST COVERAGE: 42 New Tests"
# Including:
# - Holiday detection tests
# - WAF resilience tests
# - Cache integration tests
# - Bulk processing tests

# Step 3: Write tests that match DEC-001 spec
# Don't invent new test categories!
# Follow the documented test plan

# Step 4: Validate against existing tests
pytest tests/test_kap.py -v
# Should see 42 tests passing (not 100+)
```

---

### Scenario 3: Emergency: Code Breaks After Change

```
Error: Portfolio score calculation changed unexpectedly

// Step 1: Check what decision governs this area
grep -r "portfolio.*score" docs/decisions/DEC-*.md
# Result: DEC-005 (Signal Layer Weights)

// Step 2: Review DEC-005 to understand expected behavior
cat docs/decisions/DEC-005.md
# Formula should be:
# composite = (L1×0.20 + L2×0.33 + L3×0.27 + L6×0.20) / 0.80

// Step 3: Debug based on decision
// Check: Did you accidentally change weights?
// Check: Did you add a new layer without normalizing?
// Check: Are you testing against baseline from DEC-005?

// Step 4: Restore behavior to match DEC-005
git diff docs/decisions/DEC-005.md signal_combination.py
# Should align perfectly
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

# Blocked decisions (if any)
grep -l "status: blocked" docs/decisions/DEC-*.md
# Result: (none currently)
```

---

### Pattern 3: Find Decisions by Affected Files

```bash
# What decisions touch config.yaml?
grep -l "config.yaml" docs/decisions/DEC-*.md
# Result: DEC-001, DEC-002, DEC-004, DEC-005

# What decisions affect tests?
grep -l "test_" docs/decisions/DEC-*.md
# Result: DEC-001 (+42), DEC-002 (+14), DEC-003 (+25), DEC-004 (+5)
```

---

## READING A DECISION FILE

### Frontmatter (Machine-Readable Metadata)

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
  - tests/test_signal_combination.py
rationale: "BIST sensitivity to macro regime; weights from empirical testing"
implementation_status: 100%
test_coverage: Included in baseline tests
---
```

**What Each Field Means:**
| Field | Purpose |
|---|---|
| `id` | Unique identifier (DEC-NNN) |
| `title` | Decision name |
| `date` | When decided |
| `area` | Category (for grouping) |
| `status` | Implementation stage (pending/implemented/blocked) |
| `priority` | Urgency (HIGH/MED/LOW) |
| `affects` | Files impacted (query these!) |
| `rationale` | Why this choice was made |
| `implementation_status` | % complete (0-100%) |
| `test_coverage` | Test count or reference |

---

### Body (Human-Readable Details)

Each decision file contains:

1. **CONTEXT** — What problem was this solving?
2. **OPTIONS CONSIDERED** — What alternatives were evaluated?
3. **DECISION** — What was chosen and why?
4. **IMPLEMENTATION** — How was it coded?
5. **TEST COVERAGE** — What tests were added?
6. **RISKS & MITIGATIONS** — Known issues and safeguards
7. **INTEGRATION POINTS** — Where does this touch the system?

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

**Step 1:** Copy template
```bash
cp docs/decisions/DEC-TEMPLATE.md docs/decisions/DEC-NNN.md
```

**Step 2:** Fill frontmatter
```yaml
id: DEC-NNN
title: "Your Decision Title"
date: YYYY-MM-DD
area: "Pick one: Data Sources | Signal Architecture | Risk Management | Efficiency"
status: pending  # or implemented
affects:
  - src/path/to/file.py
  - tests/test_file.py
```

**Step 3:** Write sections
- CONTEXT (1-2 paragraphs)
- OPTIONS CONSIDERED (list of options)
- DECISION (which chosen + why)
- IMPLEMENTATION (code changes)
- TEST COVERAGE (test cases added)

**Step 4:** Update DECISIONS.md index
- Add row to quick table
- Add link in category section

**Step 5:** Reference in code
- Commit message: "Implements DEC-NNN: decision title"
- Code comment: `# See decisions/DEC-NNN.md for context`

---

## QUERYING DECISIONS FROM CODE

### In Python

```python
import json

def get_affected_decisions(file_path):
    """Find all decisions affecting a specific file."""
    import glob
    decisions = []
    
    for dec_file in glob.glob('docs/decisions/DEC-*.md'):
        with open(dec_file) as f:
            content = f.read()
            if file_path in content:
                # Extract ID from filename
                dec_id = dec_file.split('/')[-1].replace('.md', '')
                decisions.append(dec_id)
    
    return decisions

# Usage:
affected = get_affected_decisions('src/signals/signal_combination.py')
print(f"Decisions affecting this file: {affected}")
# Output: Decisions affecting this file: ['DEC-005', 'DEC-003']
```

---

### In Shell

```bash
#!/bin/bash
# Find all decisions affecting a file

FILE=$1

echo "Decisions affecting: $FILE"
grep -l "$FILE" docs/decisions/DEC-*.md | while read dec_file; do
    dec_id=$(basename "$dec_file" .md)
    echo "  - $dec_id: $(grep '^title:' "$dec_file" | cut -d: -f2)"
done
```

**Usage:**
```bash
./find_decisions.sh src/signals/signal_combination.py
# Output:
# Decisions affecting: src/signals/signal_combination.py
#   - DEC-005: Signal Layer Weights (4-Layer Stack)
#   - DEC-003: Macro-Equity Correlation Layer
```

---

## DECISION METRICS & REPORTING

### Current State (15 May 2026)

```
Total Decisions: 6
├─ Implemented: 5 (83%)
├─ Pending: 1 (17%)
└─ Blocked: 0 (0%)

By Area:
├─ Data Sources: 3 decisions
├─ Signal Architecture: 2 decisions
├─ Risk Management: 1 decision
└─ Efficiency: 1 decision

Test Coverage Added:
├─ DEC-001: +42 tests (KAP)
├─ DEC-002: +14 tests (CDS)
├─ DEC-003: +25 tests (Macro-Equity)
├─ DEC-004: +5 tests (Report)
└─ Total: +86 new tests
```

### Timeline

```
2026-05-10 ─ DEC-005, DEC-006 (decisions made)
2026-05-11 ─ DEC-004 (implemented)
2026-05-12 ─ DEC-003 (implemented)
2026-05-13 ─ DEC-002 (implemented)
2026-05-14 ─ DEC-001 (implemented)
2026-05-15 ─ Today (Decision log system documented)
```

---

## FREQUENTLY ASKED QUESTIONS

### Q: Can I change weights in DEC-005?

**A:** No, not without new decision. If you want different weights:
1. Create new decision DEC-007 (or update DEC-005)
2. Justify with new backtest (Sharpe ratio, max drawdown)
3. Get Architect approval
4. Update tests to match new weights

**Bad approach:** Changing weights without documentation = introduces regression risk

---

### Q: What if a decision is outdated?

**A:** Mark as `status: deprecated` or create a superseding decision:
- DEC-005-v2: "Signal Layer Weights (Updated)"
- Keep old decision for historical reference
- Note in commit: "Supersedes DEC-005 (backtest shows L5 weight should be 15%)"

---

### Q: How do I reference a decision in a PR?

**A:** Use GitHub commit messages and PR description:

```markdown
## Implements DEC-005: Signal Layer Weights

### Changes
- Update signal combination weights to L1(20%), L2(33%), L3(27%), L6(20%)
- Add tests validating Sharpe ratio >0.80

### Decision Reference
See [docs/decisions/DEC-005.md](../decisions/DEC-005.md)

### Test Results
- All 372 tests passing ✅
- Zero regression vs baseline ✅
```

---

## INTEGRATION WITH CI/CD

### Pre-commit Hook (Optional)

```bash
#!/bin/bash
# Check commit message references a decision if code changes >5 files

FILES_CHANGED=$(git diff --cached --name-only | wc -l)

if [ $FILES_CHANGED -gt 5 ]; then
    COMMIT_MSG=$(git diff --cached --cached-tree | head -1)
    
    if ! echo "$COMMIT_MSG" | grep -q "DEC-[0-9][0-9][0-9]"; then
        echo "Error: Large change (>5 files) requires decision reference (DEC-NNN)"
        exit 1
    fi
fi
```

---

## REFERENCES

| Document | Purpose |
|---|---|
| `docs/DECISIONS.md` | Main index + search guide |
| `docs/decisions/DEC-*.md` | Individual decision files |
| `docs/BOOT_ARCHITECT.md` | High-level architecture overview |
| `docs/PROJECT/MASTERPLAN.md` | Phase timeline |
| This file (`CLAUDE_DECISIONS_INTEGRATION.md`) | How to use decisions in code |

---

**Last Updated:** 15 May 2026  
**Owner:** Architect  
**For Questions:** See DECISIONS.md index

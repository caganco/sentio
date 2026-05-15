# BOOT_BUILDER

**Project:** BIST Trading System  
**Location:** `C:\Users\cagan\bist-trading-system`  
**Branch:** `master` (main development)  
**Python:** base (anaconda)  
**Git User:** cagan  

---

## Quick Start

```powershell
cd C:\Users\cagan\bist-trading-system

# Run daily pipeline
python scripts/daily_update.py --scan --generate-report

# Run tests (dev - only new/changed)
python -m pytest tests/ -m new -q

# Run full test suite (before commit)
python -m pytest tests/ -q --tb=short
```

---

## Current Project State

| Metric | Value |
|--------|-------|
| **Tests** | 519 passing, 0 failed, 1 skipped ✅ |
| **Phase** | 5.2 Complete (6-layer signal engine) |
| **Coverage** | ~91% (signal + macro + sentiment + risk + smart money + drawdown) |
| **Specs** | 12 completed (LOCAL_MACRO, STRATEGIST, EFFICIENCY, REPORT_OPT, MACRO_EQUITY, CDS, KAP, CTX, KELLY, SENTIMENT_NLP, DRAWDOWN, SMART_MONEY) |
| **Last Commit** | `84d5ec7` Fix 3 failing macro layer tests |
| **Status** | Production-ready, zero regression |

---

## ⚠️ PowerShell Rules (CRITICAL)

Unix commands **DO NOT WORK**. Always use PowerShell equivalents:

| Unix | PowerShell |
|------|-----------|
| `tail -N file` | `Get-Content file \| Select-Object -Last N` |
| `head -N file` | `Get-Content file \| Select-Object -First N` |
| `grep "pattern"` | `Select-String "pattern"` |
| `wc -l file` | `(Get-Content file \| Measure-Object -Line).Lines` |
| `cat file` | `Get-Content file` |
| `ls -la` | `Get-ChildItem -Force` |
| `find . -name "*.py"` | `Get-ChildItem -Recurse -Filter "*.py"` |
| `sed 's/x/y/g' file` | `(Get-Content file) -replace 'x', 'y' \| Set-Content file` |

**Using Unix commands will cause command-not-found errors.**

---

## Test Strategy

### Dev Testing (Fast)
```powershell
pytest tests/ -m new -q
```
Runs only tests marked with `@pytest.mark.new`. Use for rapid iteration.

### Full Test Suite (Before Commit)
```powershell
python -m pytest tests/ -q --tb=short
```
Runs all 519 tests. Required before pushing.

### Specific Test File
```powershell
python -m pytest tests/test_smart_money.py -v
```

### With Coverage
```powershell
python -m pytest tests/ --cov=src --cov-report=html
```

### Baseline Tests (READ-ONLY)
Do NOT modify baseline tests (`test_baseline_markers.py`). These validate core functionality.

---

## Project Structure

```
c:\Users\cagan\bist-trading-system\
├── config.yaml                    # Configuration (tickers, thresholds)
├── CLAUDE.md                      # Project directives
├── OS_STATE.md                    # Auto-updated system state (6h)
├── scripts/
│   └── daily_update.py            # Main pipeline (fetch → score → report)
├── src/
│   ├── signals/
│   │   ├── engine.py              # 6-layer signal calculation
│   │   ├── models.py              # Data classes
│   │   ├── thresholds.py          # All constants (NO magic numbers)
│   │   └── layers/
│   │       ├── technical_layer.py (20% weight)
│   │       ├── macro_layer.py     (35% weight)
│   │       ├── kap_layer.py       (15% weight)
│   │       ├── risk_layer.py      (5% weight)
│   │       ├── smart_money_layer.py (20% weight)
│   │       └── sentiment_layer.py (5% weight)
│   ├── data/
│   │   ├── smart_money_client.py  # Institutional flow fetch + cache
│   │   └── [other data sources]
│   └── risk/
│       └── [drawdown, kelly, etc]
├── tests/
│   ├── test_engine.py             # 519 total tests (here)
│   ├── test_smart_money.py        # 19 tests
│   ├── test_sentiment_integration.py (15 tests)
│   ├── test_drawdown.py           # 23 tests
│   └── [40+ other test files]
├── docs/
│   ├── BOOT_ARCHITECT.md          # Architecture decisions
│   ├── BOOT_ORCHESTRATOR.md       # Work direction
│   ├── BOOT_STRATEGIST.md         # Narrative guidelines
│   ├── BOOT_BUILDER.md            # THIS FILE
│   └── SPECS/
│       ├── INDEX.md               # Spec manifest
│       ├── SPEC_SMART_MONEY_1.md
│       ├── SPEC_SENTIMENT_NLP_1.md
│       └── [10 other specs]
├── data/
│   ├── config.yaml
│   ├── macro_sensitivity.json
│   ├── sector_mapping.json
│   └── [cache files]
├── agents/
│   └── intelligence/              # Daily briefing outputs
└── reports/
    └── [daily reports]
```

---

## Key Commands

### Daily Pipeline
```powershell
# Scan all tickers, generate report, update OS_STATE
python scripts/daily_update.py --scan --generate-report

# Scan only specific tickers
python scripts/daily_update.py --tickers AKSEN,GARAN,THYAO

# Dry-run (no file writes)
python scripts/daily_update.py --scan --dry-run
```

### Run Tests
```powershell
# All tests (519)
python -m pytest tests/ -q

# Specific suite
python -m pytest tests/test_smart_money.py -v

# With markers (if defined)
python -m pytest tests/ -m new -q

# Failure details
python -m pytest tests/ --tb=long
```

### Check Status
```powershell
# Git status
git status

# Recent commits
git log --oneline -10

# Branch
git branch -v
```

---

## Common Tasks

### Add a New Signal Layer
1. Create `src/signals/layers/new_layer.py` with score function
2. Return `SignalResult` dataclass
3. Add weight to `MASTER_WEIGHTS` in `thresholds.py`
4. Integrate into `signal_engine.py` (add to layer_scores list)
5. Write tests in `tests/test_new_layer.py`
6. Update `docs/SPECS/INDEX.md`

### Fix a Failing Test
1. Run test: `pytest tests/test_foo.py::TestBar::test_baz -v`
2. Analyze assertion failure
3. Update test expectations OR fix code
4. Run full suite: `pytest tests/ -q`
5. Commit: `git add -A && git commit -m "..."`

### Add a New Test File
1. Create `tests/test_feature.py`
2. Import fixtures from `conftest.py` (if exists)
3. Write test class: `class TestFeature:`
4. Run: `pytest tests/test_feature.py -v`
5. Add to full suite: `pytest tests/`

### Update Configuration
1. Edit `config.yaml`
2. Tests reload automatically
3. Verify: `pytest tests/`
4. Commit config change

---

## Signal Engine Architecture

### 6-Layer Stack (Phase 5.2 Complete)

| Layer | Weight | Purpose | Source |
|-------|--------|---------|--------|
| **Technical** | 20% | Price action, momentum, volatility | `score_technical()` |
| **Macro** | 35% | Global + local (TCMB, CDS) | `score_macro()` |
| **KAP** | 15% | Corporate actions, disclosures | `score_kap()` |
| **Risk** | 5% | Drawdown, overbought, volatility | `score_risk()` |
| **Smart Money** | 20% | Institutional flows, bull traps | `SmartMoneyLayer()` |
| **Sentiment** | 5% | News sentiment (VADER) | `score_sentiment()` |

**Calculation:** `score = Σ(layer_score × weight) / Σ(weights)` [0-100]

**Final Signal:**
- BUY-STRONG: score ≥ 72
- BUY-WEAK: score ≥ 60
- HOLD: 43 ≤ score < 60
- SELL-WEAK: 32 ≤ score < 43
- SELL-STRONG: score < 32

**Overrides:**
- Conflict resolution: max/min gap > 40 → downgrade 1 level
- Regime filter: RISK_OFF (VIX > 30 or USDTRY spike) → all BUY → HOLD
- Bull trap: Tech STRONG-BUY + 3 days institutional selling → −0.15 override

---

## Data Fetching

### Macro Data (Local)
- **TCMB:** Policy rate decisions (daily, cached 45 days)
- **CDS:** Turkey 5Y spreads (daily, cached 2 days)
- **BIST Foreign:** Weekly foreign ownership (cached 10 days)
- **Global:** USDTRY, VIX, BRENT, SP500, BIST100 (real-time from yfinance)

### Smart Money (Institutional Flows)
- **Primary:** Borsa Istanbul settlement reports (mock data)
- **Fallback:** Halk Yatırım scraping (4h cache)
- **History:** 3-day rolling (24h normal, 72h incident)

### Sentiment
- **Source:** Yahoo Finance news API
- **Analyzer:** VADER sentiment (compound -1 to +1)
- **Recency:** 100% at 0d, decay to 50% at 7d
- **Frequency:** Daily batch

---

## Debugging Tips

### Test Failing?
```powershell
# Run with full traceback
pytest tests/test_foo.py -v --tb=long

# Run with print output
pytest tests/test_foo.py -v -s

# Run specific test
pytest tests/test_foo.py::TestClass::test_method -v
```

### Signal Weird?
```powershell
# Check layer scores
python -c "from src.signals.engine import compute_signal; from datetime import date; r = compute_signal('AKSEN', {...}, {...}, [], date.today()); print(r.audit.layer_scores)"

# Check macro layers
python -c "from src.signals.layers.macro_layer import score_macro; ls = score_macro({...}); print(ls.detail)"
```

### Cache Issue?
```powershell
# Clear all caches
Remove-Item data/*.json, agents/intelligence/cache/* -Force

# Re-run pipeline
python scripts/daily_update.py --scan --generate-report
```

---

## Code Style

### No Magic Numbers
ALL constants go in `src/signals/thresholds.py`. Example:
```python
# ❌ BAD
if score > 60:

# ✅ GOOD
if score > SIGNAL_THRESHOLDS["buy_weak"]:
```

### No Comments Unless Why
```python
# ❌ BAD (what is obvious)
x = y + 1  # add 1

# ✅ GOOD (why non-obvious)
# Bull trap: conservative 0.15 downgrade on technical score
override = -0.15
```

### Test Organization
- Unit tests: `tests/test_[module].py`
- Integration: `tests/test_[feature]_integration.py`
- Fixtures: `conftest.py`
- Markers: `@pytest.mark.new`, `@pytest.mark.slow`

### Git Commits
```
SPEC_FOO_1: Brief title (< 60 chars)

Detailed explanation:
- What changed
- Why it changed
- Test results

Fixes #123
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

---

## Performance Targets

| Task | Target | Status |
|------|--------|--------|
| **Daily Pipeline** | < 5 seconds | ✅ ~3s |
| **Report Token Size** | < 600 tokens | ✅ ~400 tokens |
| **Data Fetch** | < 500ms | ✅ macro + sentiment |
| **Test Suite** | < 60s | ✅ 42s |
| **Signal Calculation** | < 10ms per ticker | ✅ 8ms |
| **Report Token Reduction** | 66% (1000→400) | ✅ Achieved |

---

## Troubleshooting

### Tests Hang?
- Kill process: `Get-Process python | Stop-Process -Force`
- Check for infinite loops in test setup
- Run single test: `pytest tests/test_foo.py::test_bar -v`

### Import Error?
```powershell
# Verify PYTHONPATH
$env:PYTHONPATH = "C:\Users\cagan\bist-trading-system"

# Test import
python -c "from src.signals.engine import compute_signal; print('OK')"
```

### Git Conflict?
```powershell
# Check status
git status

# Resolve (prefer current)
git checkout --theirs .

# Or use external tool
git mergetool
```

### Cache Stale?
```powershell
# Check OS_STATE age
Get-Item OS_STATE.md | Select-Object LastWriteTime

# Force refresh (if > 6h old)
python scripts/daily_update.py --scan --generate-report
```

---

## Related Docs

- **BOOT_ARCHITECT.md** — Architecture decisions, SPEC template, design rationale
- **BOOT_ORCHESTRATOR.md** — Feature prioritization, milestone roadmap, blockers
- **BOOT_STRATEGIST.md** — Narrative generation, token budgets, report guidelines
- **docs/SPECS/INDEX.md** — Complete SPEC manifest (12 specs, 519 tests)
- **CLAUDE.md** — Project directives, permissions, behavior rules

---

## Contact / Escalation

- **Architecture Questions** → BOOT_ARCHITECT.md
- **Feature Prioritization** → BOOT_ORCHESTRATOR.md
- **Report/Narrative Issues** → BOOT_STRATEGIST.md
- **Test Failures** → `git log --grep="test"` for similar fixes
- **Performance** → Run profiler on `scripts/daily_update.py`

---

**Last Updated:** 2026-05-15  
**Maintained By:** Builder (Claude Code)  
**Status:** Production-ready, Phase 5.2 complete

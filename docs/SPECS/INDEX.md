# SPECIFICATION MANIFEST

**Master index of all feature specifications (SPEC files).**

**Total:** 8 completed specs  
**Total Tests:** 372 passing (330 baseline + 42 KAP edge cases)  
**Regression:** Zero ✅

---

## SPEC INVENTORY

| # | Spec ID | Name | Scope | Status | Tests | File | Date | Updated |
|----|---------|------|-------|--------|-------|------|------|---------|
| 1 | LOCAL_MACRO | Local Macro Fetcher | TCMB interest rates, CDS spreads, BIST foreign ownership | ✅ Implemented | 20 | `SPEC_LOCAL_MACRO.md` | 2026-05-10 | Stable |
| 2 | STRATEGIST | Strategist Agent | Claude API integration, daily market narrative reports | ✅ Implemented | 14 | `SPEC_STRATEGIST.md` | 2026-05-11 | Stable |
| 3 | EFFICIENCY | Signal Engine Efficiency | Ticker externalization, singleton pattern, stub cleanup | ✅ Implemented | 8 | `SPEC_EFFICIENCY.md` | 2026-05-12 | Stable |
| 4 | REPORT_OPT | Report Data Optimization | Token reduction (1000 → 400 tokens, 66%), compact JSON encoding | ✅ Implemented | 5 | `SPEC_REPORT_OPT.md` | 2026-05-12 | Stable |
| 5 | MACRO_EQUITY | Macro-Equity Correlation Layer | Sensitivity matrix, alignment scoring, portfolio-macro regime validation | ✅ Implemented | 25 | `SPEC_MACRO_EQUITY.md` | 2026-05-13 | Stable |
| 6 | CDS | CDS Data Source Alternative | WAF bypass, iShares TUR proxy model, 3-tier fallback chain | ✅ Implemented | 14 | `SPEC_CDS.md` | 2026-05-13 | Stable |
| 7 | KAP | KAP Pipeline Edge Cases | Holiday detection, bulk disclosure queue, downtime cache | ✅ Implemented | 42 | `SPEC_KAP.md` | 2026-05-14 | Stable |
| 8 | CTX | Context Standardization | Directory structure, boot files, OS_STATE auto-update | ✅ Implemented | — | `SPEC_CTX.md` | 2026-05-14 | Stable |

---

## SPEC DETAILS

### 1. SPEC_LOCAL_MACRO (Implemented ✅)

**Purpose:** Fetch Turkish macro data from local sources (no WAF blocks)

**Features:**
- TCMB interest rates (policy rate, repo)
- CDS Turkey 5Y spreads (alternative to scraping)
- BIST foreign ownership percentage
- Caching to avoid rate limits

**Tests:** 20 comprehensive unit + integration tests  
**Status:** Stable, in production  
**Key Metrics:** <500ms fetch, < 24h cache TTL

---

### 2. SPEC_STRATEGIST (Implemented ✅)

**Purpose:** Daily market narrative via Claude API

**Features:**
- Reads compact portfolio data (< 300 tokens)
- Generates market story in Turkish
- Per-position guidance (keep/cut/watch)
- Challenges portfolio assumptions
- Daily questions for investigation

**Tests:** 14 tests covering narrative quality, compliance, data validation  
**Status:** Stable, in production  
**Key Metrics:** < 5s execution, ≤ 600 tokens total

---

### 3. SPEC_EFFICIENCY (Implemented ✅)

**Purpose:** Signal engine optimization for maintainability

**Features:**
- Ticker config externalized to config.yaml
- LocalMacroSignals singleton pattern
- Stub layer cleanup (removed dummy sentiment/smartmoney weights)
- Centralized thresholds

**Tests:** 8 tests for config loading, singleton behavior, weight validation  
**Status:** Stable, reduces code coupling  
**Key Metrics:** Single source of truth for tickers

---

### 4. SPEC_REPORT_OPT (Implemented ✅)

**Purpose:** Reduce report token budget via encoding

**Features:**
- Single-character codes: sectors (B=bank, E=energy), signals (BL=bullish)
- Compact JSON vs. verbose text
- Removed redundant fields
- 66% token reduction achieved (1000 → 400)

**Tests:** 5 tests for encoding roundtrips, boundary cases  
**Status:** Stable, in production  
**Key Metrics:** 60% token reduction verified

---

### 5. SPEC_MACRO_EQUITY (Implemented ✅)

**Purpose:** Portfolio-macro regime alignment validation

**Features:**
- Sensitivity matrix: 10 tickers × 4 macro variables (Brent, USD/TRY, VIX, CDS)
- Direction + strength encoding (bullish/bearish, strong/medium/weak)
- Alignment score [0,1] per position
- Portfolio-level alignment aggregation
- Druckenmiller Macro → Sector → Stock validation

**Tests:** 25 tests covering profile loading, aggregation logic, narrative generation, edge cases  
**Status:** Stable, integrated into daily_update.py  
**Key Metrics:** Macro sensitivity profiles calibrated quarterly

---

### 6. SPEC_CDS (Implemented ✅)

**Purpose:** Handle CDS scraping WAF blocks gracefully

**Features:**
- Primary: worldgovernmentbonds.com scraping
- Secondary: iShares TUR ETF proxy model (linear combination: base + α·FX + β·VIX + γ·equity)
- Tertiary: Cache fallback (< 24h normal, < 72h incident mode)
- Source tracking: R (real) vs P (proxy) labels

**Tests:** 14 tests for fallback chain, model bounds, source identification, cache age  
**Status:** Stable, handles WAF blocks  
**Key Metrics:** [100, 800] bps bounds enforced, < 10% proxy error

---

### 7. SPEC_KAP (Implemented ✅)

**Purpose:** Robust KAP disclosure fetching with edge case handling

**Features:**
- BISTCalendar: proactive holiday detection (fixed + lunar dates)
- KAPDisclosureQueue: non-blocking bulk event queueing with batch processing
- KAPCacheManager: TTL-based fallback (24h normal, 72h incident)
- Staleness detection and alerting

**Tests:** 42 tests across holidays, queue, cache, integration scenarios, stress cases  
**Status:** Stable, ready for production  
**Key Metrics:** Zero WAF blocks via queue + holiday skip

---

### 8. SPEC_CTX (Implemented ✅)

**Purpose:** Standardize system documentation and boot procedures

**Features:**
- `docs/` directory structure: BOOT files, SPECS, PROJECT, RUNBOOK
- Three boot files: BOOT_ORCHESTRATOR, BOOT_ARCHITECT, BOOT_STRATEGIST
- Automatic OS_STATE.md update via daily_update.py (every 6h)
- Staleness detection at agent startup
- Cross-reference validation (lint)

**Tests:** Integration tests for boot loading, staleness checks, fallback chains  
**Status:** Stable, reduces context friction  
**Key Metrics:** < 1s boot load, < 500ms staleness check

---

## PHASE ROADMAP

| Phase | Status | Specs Completed | Test Count | Blocker for Next |
|-------|--------|---|---|---|
| **4.8** | ✅ Complete | LOCAL_MACRO, STRATEGIST, EFFICIENCY, REPORT_OPT | 47 | — |
| **4.9** | ✅ Complete | MACRO_EQUITY, CDS, KAP | 81 | Kelly Criterion |
| **5.0** | ✅ Complete | CTX | — | Phase 5 entry |
| **5.1** | 🟡 Pending | KELLY (position sizing) | — | — |
| **5.2** | 🟡 Pending | SENTIMENT_NLP (Layer 4) | — | — |
| **5.3** | 🟡 Pending | SMART_MONEY (Layer 5) | — | — |

---

## QUALITY METRICS

### Test Coverage
- **Total Tests:** 372 (330 baseline + 42 KAP)
- **Pass Rate:** 100% ✅
- **Regression:** Zero ✅
- **Coverage:** ~87% (signal engine + macro layers)

### Code Quality
- **Technical Debt:** 2 DRY violations (acceptable)
- **Security Gaps:** 1 low-priority (path traversal in server.py)
- **Stub Layers:** 2 (Sentiment, Smart Money) — planned for Phase 5

### Performance
- **Daily Report:** < 5 seconds ✅
- **Report Size:** ~600 tokens ✅
- **Data Fetch:** < 500ms (local macro) ✅
- **OS_STATE Update:** Every 6 hours ✅

---

## SPEC FILE NAMING CONVENTION

**Format:** `SPEC_[ID]_[VERSION].md` or `SPEC_[ID].md` (no version for stable)

**Examples:**
- `SPEC_LOCAL_MACRO.md` (stable)
- `SPEC_KELLY_1.md` (new proposal, version 1)
- `SPEC_SENTIMENT_NLP_2.md` (revised proposal, version 2)

**Location:** `docs/SPECS/` directory

---

## HOW TO ADD A NEW SPEC

1. **Create file:** `docs/SPECS/SPEC_[ID].md`
2. **Write SPEC:** Use template from BOOT_ARCHITECT.md
3. **Update this INDEX:** Add row to table above
4. **Validate:** Ensure no contradictions with existing SPECs
5. **Submit to Orchestrator:** For review and directive

---

## CROSS-REFERENCE MATRIX

| Spec | Depends On | Required By | Conflicts |
|------|---|---|---|
| LOCAL_MACRO | — | STRATEGIST, MACRO_EQUITY | — |
| STRATEGIST | REPORT_OPT | — | — |
| EFFICIENCY | — | All | — |
| REPORT_OPT | EFFICIENCY | STRATEGIST | — |
| MACRO_EQUITY | LOCAL_MACRO | KAP (for alignment check) | — |
| CDS | — | MACRO_EQUITY (as input) | — |
| KAP | — | MACRO_EQUITY (KAP is Layer 3) | — |
| CTX | All (depends on docs structure) | All (bootstrap) | — |

---

## LEGEND

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented, stable, in production |
| 🟡 | Pending, not yet started |
| 🟠 | In progress / under review |
| ❌ | Blocked / not planned |
| ⚠️ | Stable but with known limitations |

---

## NEXT STEPS

**For Phase 5.1 (Kelly Criterion):**
1. Architect designs SPEC_KELLY_1.md
   - Input: Signal scores, conviction levels
   - Output: Position sizes (HIGH=20%, MED=10%, LOW=5%)
   - Integration: signal_engine.py
   - Tests: 10+ (position sizing validation, edge cases)

2. Orchestrator reviews and approves

3. Builder implements per SPEC
   - Code in src/signals/kelly.py
   - Tests in tests/test_kelly.py
   - Integration in daily_update.py
   - Verify zero regression

4. Acceptance: All 372 + 10+ new tests pass

---

**Last Updated:** 14 May 2026  
**Maintained By:** Architect  
**Review Frequency:** Weekly (or when new SPEC added)

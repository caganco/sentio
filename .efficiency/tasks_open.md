# Open Tasks Registry

**Last Updated:** 14 May 2026  
**Scope:** Phase 4.8 → Phase 5 Transition

---

## CRITICAL (Days 1-2)

### 1. Macro Alignment Calculator (SPEC_M_1.MD)
- **Status:** Spec ready, implementation pending
- **Description:** Sector+hisse makro rejime uyum analizi
- **Inputs:** TCMB (hike/cut/hold), CDS (100-400-600 bps thresholds), Brent price, BIST foreign
- **Outputs:**
  - Sector compliance score (0-100)
  - Per-hisse alignment rating (perfect/good/neutral/conflicting)
  - Macro risk flag (compatible/caution/misaligned)
- **Integration:** Signal engine context, daily_update.py report
- **Effort:** ~4-6 hours
- **Tests:** 8-10 unit tests

### 2. CDS WAF Blockage Resolution
- **Status:** Urgent, impacting daily cache quality
- **Current:** `worldgovernmentbonds.com` scraper → 403 Forbidden (WAF)
- **Fallback:** YAML cache (stale data, 5+ days old)
- **Options:**
  - Option A: investing.com CDS Turkey endpoint
  - Option B: tradingeconomics.com CDS feed
  - Option C: iShares bond ETF price inversion (indirect proxy)
- **Effort:** ~2-3 hours (research + pivot)
- **Tests:** 4-5 unit tests (mock response variants)

---

## HIGH (Days 2-4)

### 3. KAP Edge Case Tests
- **Status:** Coverage gap, no explicit edge case handling
- **Scenarios:**
  - National holidays (no trading, no KAP events)
  - Bulk announcement day (10+ events same company)
  - System downtime (API 500s, retry logic)
  - Disclosure index conflicts (duplicate vs update)
- **Integration:** `src/data/kap_client.py` + tests
- **Effort:** ~3-4 hours
- **Tests:** 6-8 new unit tests

### 4. EVDS Batch Call Optimization
- **Status:** Performance concern, two separate API calls daily
- **Current:** `TCMBClient.fetch_and_store()` + `BistForeignClient.fetch_and_store()` → 2 requests
- **Goal:** Merge into single EVDS batch call (CBRT API supports bulk series)
- **Effort:** ~2 hours
- **Tests:** 2-3 unit tests (batch format validation)

---

## MEDIUM (Days 4-7)

### 5. Kelly Criterion Position Sizing
- **Status:** Risk framework pending
- **Logic:** Position size = (win% × win_amount - loss% × loss_amount) / loss_amount
- **Application:** High/medium/low conviction → %15-20 / %5-10 / 0% portfolio
- **Integration:** Orchestrator decision logic
- **Effort:** ~3 hours
- **Tests:** 5-6 unit tests

### 6. Drawdown Management
- **Status:** Risk thresholds not yet enforced
- **Rules:**
  - -10% portfolio → risk-off mode (reduce position sizes 50%)
  - -15% portfolio → flatten all positions (exit)
- **Integration:** Portfolio.py + orchestrator
- **Effort:** ~2 hours
- **Tests:** 4 unit tests (scenario-based)

### 7. News Sentiment NLP Pipeline (Layer 4)
- **Status:** Blocked on architecture (topic modeling vs keyword scoring)
- **Sources:** Bloomberg HT, Investing.com TR, Hürriyet Finans
- **Effort:** ~12-16 hours (NLP + scraping + caching)
- **Backlog:** Phase 5, after macro alignment + CDS resolved

---

## Priority Decision Tree

```
Day 1 (start):
├─ CRITICAL: SPEC_M_1 implementation (start immediately)
└─ CRITICAL: CDS WAF research (parallel, 1 hour initial spike)

Day 2-3:
├─ SPEC_M_1 testing + integration
├─ CDS WAF pivot + testing
└─ KAP edge case tests (if capacity)

Day 4+:
├─ EVDS batch optimization (if time)
├─ Kelly criterion (medium priority)
└─ Drawdown management (medium priority)
```

---

## Success Metrics

- [ ] SPEC_M_1: Sector alignment score in daily report
- [ ] CDS: Real-time data (not fallback) for 7+ consecutive days
- [ ] KAP: Edge case tests pass, no gaps in coverage
- [ ] Overall: 291+ tests pass (zero regression)

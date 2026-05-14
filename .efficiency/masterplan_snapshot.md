# Masterplan Snapshot — Phase 4.8

**Last Updated:** 14 May 2026  
**Status:** Active Development

## Project Info
- Path: C:\Users\cagan\bist-trading-system
- Branch: master
- Python env: base (anaconda)
- Key commands:
  - Run: python scripts/daily_update.py --scan --generate-report
  - Test: python -m pytest tests/ -q
  - Report: type reports\report_2026-05-14.md

---

## Current Phase: 4.9 — Macro-Equity Correlation + CDS Resilience

### Completed This Session (14 May 2026)
- **SPEC_E_1:** Signal Engine Efficiency (3 tasks) ✅
  - Task 1: Ticker externalization (ALREADY in config.yaml)
  - Task 2: LocalMacroSignals singleton pattern
  - Task 3: Stub layer cleanup (sentiment 0.15 + smart_money 0.10 removed)
- **SPEC_S_1:** Brent-Sector Correlation (60-ticker sector_mapping.json) ✅
- **SPEC_R_1:** Compact Report Data (StrategistAgent, ~400 tokens, 66% reduction) ✅
- **SPEC_M_1:** Macro-Equity Correlation Layer ✅
  - `data/macro_sensitivity.json`: 10-ticker profiles (AKSEN, TAVHL, TTKOM, KCHOL, ENERY, ASELS, TOASO, THYAO, HALKB, GARAN)
  - `src/signals/macro_alignment.py`: MacroAlignmentCalculator (brent, usd_try, vix, cds)
  - `tests/test_macro_alignment.py`: 25 tests (unit, integration, regression validation)
  - Integration: daily_update.py portfolio_data includes macro_alignment scores
- **SPEC_CDS_2:** CDS Data Source Alternative ✅
  - `src/signals/local/cds_fallback.py`: CDSFallbackClient (primary → iShares proxy → cache)
  - `data/macro_sensitivity.json`: CDS model coefficients (base=250, α=30, β=2, γ=-100)
  - `tests/test_cds_fallback.py`: 14 tests (cache fallback, source tracking, bounds)
  - Integration: daily_update.py uses CDSFallbackClient, cds_src in macro_snapshot

---

## 7-Layer Intelligence Stack — Implementation Status

| Layer | Name | Status | Notes |
|-------|------|--------|-------|
| 1 | Market Data | ✅ ACTIVE | Yahoo Finance, 60 tickers, SQLite, batch download |
| 2 | Macro Intelligence | ✅ ACTIVE | TCMB + CDS + BIST foreign (local), feature flag ON |
| 3 | Corporate Intelligence | ❌ PENDING | KAP scraper WAF issues, fintables.com alternative pending |
| 4 | Sentiment & Narrative | ❌ PENDING | News scraping, NLP scoring not started |
| 5 | Smart Money Tracking | ❌ PENDING | Institutional flow, bull trap detection not started |
| 6 | Risk Management | ❌ PENDING | Kelly criterion, concentration limits not started |
| 7 | Signal Engine | ✅ ACTIVE | 4-layer weighted (tech 23%, macro 38%, KAP 31%, risk 8%) |

---

## Critical Open Issues

### 🔴 CRITICAL
1. **CDS Scraping WAF Blockage** — `worldgovernmentbonds.com` scraper frequently blocked
   - Impact: CDS spreads fallback to YAML cache (stale data)
   - Solution needed: investing.com or tradingeconomics.com alternative

2. **Macro Alignment Calculator** — SPEC_M_1.MD ready, not yet implemented
   - Sector+hisse makro rejime uyum analizi
   - Impact: Portfolio positioning lacks macro regime validation

### 🟠 HIGH
3. **KAP Edge Case Handling** — National holidays, bulk announcements, system downtime
   - Impact: Gap in event robustness (edge case tests missing)

4. **EVDS Batch Call Optimization** — TCMB + foreign ownership using separate API calls
   - Impact: Latency, potential rate limit exposure

### 🟡 MEDIUM
5. **Kelly Criterion Position Sizing** — Risk management incomplete
6. **Drawdown Management** — -10% risk-off threshold not implemented
7. **News Sentiment NLP** — Layer 4 (sentiment analysis) blocked on architecture

---

## System Health (14 May 2026)

```
Test Suite:        291 passed, 1 skipped ✅
Code Coverage:     ~85% (signal engine + macro layers)
Critical Gaps:     8 (CDS WAF, macro alignment, KAP edge cases, Kelly, drawdown...)
Token Reduction:   66% (1000 → ~400 tokens via SPEC_R_1) ✅
```

---

## Next 3 Decisions (Priority Order)

1. **SPEC_M_1 Implementation** — Macro Alignment Calculator (days 1-3)
   - Sector compliance scores, hisse alignment rating
   - Output: Per-position macro risk flag

2. **CDS WAF Resolution** — investing.com or tradingeconomics.com pivot (day 1)
   - Keep worldgovernmentbonds.com as fallback, switch primary

3. **KAP Edge Case Tests** — National holidays, bulk events, retry logic (days 2-4)
   - Expand test coverage, document behavior per scenario

# BIST OS — System State
**Last Updated:** 19 Mayıs 2026
**Session:** Orchestrator — D-062..D-070 + CI/CD Green + Public Release Prep
**Repo:** github.com/raypun78/bist-trading-system (private — public release bekliyor)

---

### SYSTEM READINESS
- **Overall Status:** ✅ PRODUCTION-READY
- **Test Coverage:** 746 passing (1 skipped)
- **Regression Guard:** ✅ Zero regression
- **CI/CD:** ✅ GitHub Actions tam yeşil (4-job: architecture / integration / lint / full-regression)
- **Pre-commit Hook:** ✅ Aktif (Tier 1+2 + ruff, commit blocker)
- **README.md + ARCHITECTURE.md:** ✅ eklendi (df869ae)
- **LICENSE:** ✅ MIT (1afd2d0)
- **positions.yaml:** ✅ git-ignored (G-2 / 2e2392e)
- **Git History Scrub:** ⏳ PENDING — DEC-012 / public yapmadan önce Cagan yapacak
- **Risk-Free Rate:** %42 (TCMB politika faizi)
- **Sharpe (RF %42):** -5.21 — alpha problemi, weight değil (L4/L5 henüz katkı yapmıyor)
- **Bootstrap System:** ✅ Tiered (Tier 1+2: 2.2s, Tier 3: ~45s)
- **Architecture Safety:** ✅ Enforced + genişletildi (backtest/engine.py scope'a eklendi)
- **Signal Alerting:** ✅ Live
- **Decision Log:** ✅ Active (12 karar — DEC-001..DEC-012)
- **Token Efficiency:** ✅ Optimized
- **Phase 4.5:** ✅ PRODUCTION (D-052 tamamlandı, 18 Mayıs 2026)

---

### PORTFÖY (Güncel — positions.yaml, git-ignored)

| Sembol | Lot | Avg Cost |
|--------|-----|----------|
| AKSEN | 413 | 87.90 |
| TTKOM | 329 | 60.65 |
| KCHOL | 81 | 188.83 |
| ENERY | 1543 | 9.07 |

**Fonlar:** DFI 12310 adet, DVT 4578 adet, PHE 7097 adet
**Not:** TAVHL çıkarıldı. KCHOL ve ENERY bu session'da eklendi.

---

### TEST SUITE STATUS
- **Total Tests:** 746 passing (1 skipped) ✅
- **Zero Regression:** ✅ Confirmed
- **Recent Additions (D-062..D-063):**
  - 4 test: TestBacktestEngineIntegrity (architecture scope genişletme)
  - 2 test: weight_override unknown key validation (G-19)
- **Recent Additions (D-052):**
  - 32 test: conviction_validator + macro_regime_gate
  - 20 test: position_sizer_v2
  - 16 test: technical_level_detector + staged_exit_manager
  - 1 test: weight_validator (test_architecture.py refactor)
- **CLAUDE.md:** ✅ test count 742 güncellendi (D-062)

---

### AGENT PARAMETRELERI (STANDART)

| Agent | Model | Thinking | Effort | Plan Mode | Platform |
|-------|-------|----------|--------|-----------|----------|
| Architect | claude-sonnet-4-6 | ON | High | ON | Cowork (ayrı proje: "BIST OS — Architect") |
| Builder | claude-sonnet-4-20250514 | ON | Medium | OFF | Claude Code |
| Analyst | claude-sonnet-4-20250514 | OFF | Low | OFF | — |
| Auditor | claude-sonnet-4-20250514 | ON | High | ON | — |
| Efficiency | claude-sonnet-4-20250514 | OFF | Low | OFF | — |

**Architect Output Protocol:** ARTEFAKT (Builder'a) + ORCHESTRATOR NOTES (Orchestrator'a) ayrımı zorunlu.

---

### ACTIVE DIRECTIVES

| ID | Target | Konu | Status |
|----|--------|------|--------|
| D-021 | Builder | Exit mechanisms optimization | ⏸️ SUSPENDED (Phase 4.5 staged TP ile obsolete) |
| D-023 | Builder | VERDA application | ✅ SENT — yanıt bekleniyor |
| D-024 | Builder | Matriks AKD inquiry | ✅ RESPONSE RECEIVED — fiyat teklifi bekleniyor |
| D-036..D-059 | Builder/Architect | Çeşitli implementation'lar | ✅ CLOSED |
| D-060 | Builder | docs/OS_STATE.md sil, root tek kaynak | ✅ CLOSED (eb9342b) |
| D-061 | Architect | Comprehensive Project Hygiene Audit | ✅ CLOSED (AUDIT_REPORT_001.md) |
| D-062 | Builder | Sprint 1: Quick wins + guardrails | ✅ CLOSED |
| D-063 | Builder | Sprint 2: Architecture safety + CI/CD | ✅ CLOSED |
| D-064 | Builder | DEC-010 commit | ✅ CLOSED (e1dab3d) |
| D-065 | Builder | Ruff/CI cleanup | ✅ CLOSED |
| D-066 | Builder | Sprint 3: D-060 + scrapers | ✅ CLOSED |
| D-067 | Builder | Sprint 4: C-1 fix + DECISIONS + positions defer | ✅ CLOSED (3592ec8) |
| D-068 | Architect | README + Mimari Diyagram | ✅ CLOSED (df869ae) |
| D-069 | Builder | G-2 Positions Anonymization | ✅ CLOSED (2e2392e) |
| D-070 | Builder | DECISIONS metrics + OS_STATE güncelle | ✅ CLOSED (6169e1f) |

---

### LAYER STACK STATUS

| Layer | Status | Notlar |
|-------|--------|--------|
| L1 Technical | ✅ LIVE | 0.25 weight (Phase 4.5) |
| L2 Macro | ✅ LIVE | 0.20 weight; DXY 0.25, global_signals 0.25, foreign flows aktif, TL bond proxy stub |
| L3 KAP | ✅ LIVE | 0.30 weight (Phase 4.5) |
| L4 Sentiment | ⏸️ SUSPENDED | 0.12×conf; conf=0 → katkı=0. FinBERT hazır (78%), haber kaynağı yok |
| L5 Smart Money | ⏳ DATA COLLECTION | Gün 3 (19 Mayıs; gerçek başlangıç 17 Mayıs, 16 Mayıs miss). Core: foreign(0.70)+short_interest(0.30). Gün 10: momentum live (~28 Mayıs). Gün 20: full composite (~7 Haziran) |
| L5b VIOP | 📋 SPEC HAZIR | Phase 4.4b — VERDA yanıtı bekleniyor |
| L6 Risk/Kelly | ✅ LIVE | 0.03 fixed weight (signal katkısı, position sizing değil) |
| Correlation Matrix | ✅ IMPLEMENTED | master'da, Kelly entegrasyonu Phase 4.3 |

---

### PHASE 4.5 — RUTHLESS ALPHA ✅ PRODUCTION

**Felsefe:** Alpha maximization, concentrated positioning, quality-based signals
**Status:** ✅ PRODUCTION — D-052 tamamlandı (18 Mayıs 2026)

**Signal Formula:**
```
L1: 0.25 (fixed)
L2: 0.20 (fixed) + macro modulation driver
L3: 0.30 (fixed)
L4: 0.12 × l4_confidence (SUSPENDED → 0)
L5: 0.10 × l5_confidence (data collection → ≈0)
L6: 0.03 (fixed)
Statik Σ = 1.00 | Runtime Σ ∈ [0.78, 1.00]
0.78 = emergent floor (L4+L5 conf=0), NOT hardcoded
```

**Macro Modulation:**
- L2 ≥ 65 → ×1.2
- L2 ≥ 50 → ×1.0
- L2 < 50 → ×0.85

**Conviction Tiers:**
- BUY-STRONG: ≥0.68 → %32.5 pozisyon, max 4 eşzamanlı
- BUY-MEDIUM: 0.55–0.67 → %17.5 pozisyon, max 2 eşzamanlı
- WATCH: <0.55 → pozisyon yok

**Macro Gate (Position Scaling):**
- BULL (L2 ≥ 60): 1.0x size
- NEUTRAL (L2 45–59): 0.8x size
- BEAR (L2 < 45): 0.0x — no new entries

**TP Mekanizması (Staged Exits):**
- TP1: %50 çıkış — pivot R1 (ATR ×1.5)
- TP2: %30 çıkış — Fib 0.618 (ATR ×3.0)
- TP3: %20 çıkış — trailing stop (ATR ×5.0)
- Forced exit: conviction < 0.35 | macro BULL→BEAR | DD > %15

**Max Drawdown:** %15 hard stop

---

### SELF-ENFORCING QUALITY LAYER (D-062..D-063)

| Katman | Durum | Detay |
|--------|-------|-------|
| Pre-commit hook | ✅ Aktif | Tier 1+2 + ruff (E9/F63/F7/F82) her commit'te |
| Architecture tests | ✅ Genişletildi | TestBacktestEngineIntegrity dahil — backtest kör noktası kapatıldı |
| GitHub Actions CI | ✅ Yeşil | 4-job pipeline: architecture → integration → lint → full-regression |
| weight_override validation | ✅ Aktif | Unknown key → ValueError |
| MASTER_WEIGHTS tek kaynak | ✅ Enforce | thresholds.py + architecture test guard |
| Lokal ↔ CI ruff tutarlılığı | ✅ | --select E9,F63,F7,F82 (ikisi aynı ruleset) |

---

### L5 SMART MONEY — PROGRESSIVE BUILD TAKVİMİ
- **⚠️ 16 Mayıs:** ❌ Snapshot MISS — scheduler logon failure (0x80070520), hiç çalışmadı. Gerçek başlangıç 17 Mayıs (D-074 diagnostic).
- **Gün 1 (17 Mayıs):** ✅ Parquet DB başladı — 591 sembol, daily_screener.parquet. Short interest sub-signal (D-058), VERDA bağımlılığı kesildi (D-059)
- **Gün 2 (18 Mayıs):** ✅ Phase 4.5 engine entegrasyonu (D-052) — L5 conf-scaling aktif
- **Gün 3 (19 Mayıs):** ✅ CI/CD kuruldu, backtest C-1 fix, untracked modüller commit. Snapshot scheduler fix (D-074: /RU SYSTEM + Istanbul TZ date)
- **Gün 10 (~28 Mayıs):** Momentum sinyali live (10-day foreign ratio change), weight=0.07 aktif
- **Gün 20 (~7 Haziran):** Full composite (60% percentile + 40% momentum)
- **Gün 70+ (~Ağustos):** L2 vs L5 korelasyon ölçümü → corr < 0.5 ise weight 0.10×conf'a yükselt
- **Veri kaynağı:** İş Yatırım screener criterion 40 + BIST DataStore haftalık CSV
- **Finnet geçiş kriteri:** AUM ≥ 5M TL VE L5 ≥ 1.5% yıllık alpha katkısı
- **Matriks AKD:** Fiyat teklifi bekleniyor — AKD gün sonu, ~60 sembol (BIST50 + 10 ek)

---

### L5 KOMPOZİSYON
```
L5 iç ağırlık:
  foreign_ratio_score   × 0.70
  short_interest_score  × 0.30

L5 dış weight:
  Gün 10-70 (ramp):     0.07 (base, discounted)
  Phase 4.5 (IC eşiği): 0.10 × confidence_score

KAP Overlap Guard:
  L3 KAP short event + L5 short_ratio > 15% → dampening ×0.6
```

---

### L5 VERDA BAĞIMSIZLIĞI
- **L5 Core:** ✅ VERDA-FREE — IsYatirim screener + BIST DataStore doğrudan endpoint
- **L5 Extended:** ⏸️ VERDA bağımlı (kasıtlı) — VIOP + Sentiment ayrı blocker
- **Architectural guarantee:** test_l5_no_verda_dependency() Tier 1'de her bootstrap'te çalışır

---

### SENTIMENT LAYER
- **Status:** ⏸️ SUSPENDED
- **FinBERT:** ✅ Hazır (78% accuracy, 34ms latency)
- **YahooFinance:** ❌ BIST haberleri dönmüyor
- **Haber kaynağı:** Finnet/VERDA yanıtı bekleniyor
- **Weight:** 0.12 (base dict) × 0.0 (conf) = 0.0 runtime katkı

---

### MACRO WEIGHTS (GÜNCEL)

**LOCAL_MACRO_WEIGHTS** (local_macro_signals.py composite):
- tcmb: 0.40
- cds: 0.40
- bist_foreign_weekly: 0.20 (D-037 ile aktif edildi)

**MACRO_WEIGHTS_COMPOSITE** (macro_layer.py) — D-041 sonrası:
- global_signals: 0.25
- tcmb: 0.25
- cds: 0.25
- dxy: 0.25
- bist_foreign_weekly: 0.00 (LOCAL_MACRO içinde 0.20 aktif — çakışma yok, tasarım gereği)
- tl_bond_proxy: 0.00 (Phase 5 stub)

---

### DECISION LOG SYSTEM
- **Status:** ✅ ACTIVE
- **Location:** docs/decisions/
- **Kararlar:**
  - DEC-001: KAP Holiday Handling ✅
  - DEC-002: CDS iShares Proxy ✅
  - DEC-003: Macro-Equity Correlation ✅
  - DEC-004: Report Token Optimization ✅
  - DEC-005: Signal Layer Weights ✅
  - DEC-006: Kelly Criterion ✅ (src/risk/kelly.py mevcut)
  - DEC-007: Ruthless Alpha Philosophy ✅ (D-054, 16 Mayıs 2026)
  - DEC-008: VERDA Bağımsızlık Kararı ✅ (D-052, 18 Mayıs 2026)
  - DEC-009: Phase 4.5 Normalizer Derivation ✅ (D-052, 18 Mayıs 2026)
  - DEC-010: Strategist Advisory Boundary ✅ (D-064, 19 Mayıs 2026)
  - DEC-011: src/scrapers/ Reserved for L3 ✅ (19 Mayıs 2026)
  - DEC-012: Git History Scrub ✅ DECIDED — ⏳ execution pending (public release öncesi)

---

### ARCHITECTURE SAFETY
- **Threshold Centralization:** ✅ All constants imported from thresholds.py
- **Weight Integrity:** ✅ MASTER_WEIGHTS statik Σ=1.00, [0.85,1.05] band
- **Runtime Normalizer:** ✅ Emergent floor 0.78 (DEC-009)
- **Singleton Protection:** ✅ LocalMacroSignals enforced single-instance pattern
- **Design Enforcement:** Tier 1 architecture tests (TestBacktestEngineIntegrity dahil)
- **Health Check:** .\scripts\arch_health_check.ps1 haftalık
- **L5 VERDA-free guarantee:** ✅ Tier 1'de her bootstrap'te kontrol edilir

---

### BOOTSTRAP SYSTEM
- **Status:** ✅ ACTIVE + TIERED
- **Tier 1 — Architecture:** ~10 test, ~1s, her bootstrap
- **Tier 2 — Integration:** 29 test, ~2s, her bootstrap
- **Tier 3 — Full Regression:** 746 test, ~45s, commit öncesi / haftalık
- **Daily bootstrap süresi:** ~2.2 saniye (Tier 1+2)
- **Trigger komutu:** "Dependency map aktif, bootstrap başla"
- **OS_STATE:** Root `OS_STATE.md` tek kaynak (docs/OS_STATE.md D-060 ile silindi ✅)

---

### EXIT MECHANISM STATUS
- **Phase 4.5 Staged TP:** ✅ LIVE (staged_exit_manager.py)
- **TP1:** %50 çıkış — pivot R1
- **TP2:** %30 çıkış — Fib 0.618
- **TP3:** %20 çıkış — trailing stop
- **Stop-loss:** -8% below entry
- **Forced exit:** conviction < 0.35 | macro BULL→BEAR | DD > %15

---

### BACKTEST BULGULARI

**Dönem:** Nov 2025 → May 2026 (bull, +29.9%)
| Strategy | Return | Sharpe |
|---|---|---|
| Naive B&H | +34.81% | 1.55 |
| Tech-only | +4.60% | -5.16 |
| Macro-gated | +1.55% | -5.21 |

**Dönem:** Aug 2024 → Oct 2024 (bear, -17.91%)
| Strategy | Return | Trades |
|---|---|---|
| Naive B&H | -13.19% | 1 |
| Tech-only | 0.00% | 0 |
| Macro-gated | 0.00% | 0 |

**Tanı:** L4/L5 = 0 katkı → alpha üretilemiyor. Mimari doğru. L5 Gün 20 (~7 Haziran) itibariyle backtest'e katkı başlar.

---

### CAGAN MANUEL LİSTESİ
1. **GitHub Secret: ANTHROPIC_API_KEY** — github.com/raypun78/bist-trading-system → Settings → Secrets → Actions
2. **GitHub Secret: EVDS_API_KEY** — aynı yerden
3. **DEC-012 Git History Scrub** — public yapmadan hemen önce, DEC-012 adımlarını takip et (irreversible, human-only)
4. **Repo Public** — scrub tamamlandıktan sonra

---

### SPECS DURUMU

| SPEC | Durum | Notlar |
|------|-------|--------|
| SPEC_KELLY_1 | ✅ master'da | Finnet sonrası implement |
| SPEC_SENTIMENT_NLP_1 | ✅ master'da | L4 suspended |
| SPEC_CORRELATION_MATRIX_1 | ✅ master'da | Phase 4.3 |
| SPEC_L2_ENHANCEMENT_1 | ✅ master'da | D-041 tamamlandı |
| SPEC_VIOP_SIGNAL_1 | ✅ master'da | Phase 4.4b — VERDA yanıtı bekleniyor |
| SPEC_SIGNAL_CONVICTION_1 | ✅ master'da + PRODUCTION | D-052 ile implement edildi |
| SPEC_POSITION_SIZING_2 | ✅ master'da + PRODUCTION | D-052 ile implement edildi |
| SPEC_MACRO_REGIME_GATE_2 | ✅ master'da + PRODUCTION | D-052 ile implement edildi |
| SPEC_STAGED_TP_1 | ✅ master'da + PRODUCTION | D-052 ile implement edildi |
| SPEC_STRATEGIST_2 | ✅ master'da + PRODUCTION | D-052 ile implement edildi |
| SPEC_L5_SHORT_INTEREST_1 | ✅ master'da | D-058 ile eklendi |

---

### SIGNAL ALERTING SYSTEM
- **Stop-Loss Approach Warning:** ✅ Active
  - Threshold: STOP_APPROACH_BUFFER = 0.03 (3% warning zone)
  - Format: "⚠️ SYMBOL STOP_APPROACHING — Stop: X.XX TL, Mevcut: Y.YY TL, Mesafe: %Z.Z"
  - Module: src/portfolio/monitor.py
  - Tests: 7 coverage tests

---

### BACKLOG

| Priority | Task | Notes |
|----------|------|-------|
| 🔴 HIGH | DEC-012 Git History Scrub | Public release öncesi — Cagan manuel, irreversible |
| 🔴 HIGH | Repo Public Yap | Scrub sonrası — BIST BT başvurusu |
| 🔴 HIGH | L5b VIOP build | VERDA yanıtı bekleniyor. SPEC_VIOP_SIGNAL_1 hazır |
| 🟠 MED | L5 momentum doğrulama (~28 Mayıs) | Gün 10'da engine score=None değil mi kontrol et |
| 🟠 MED | Matriks AKD fiyat teklifi | ~60 sembol, gün sonu — fiyat gelince vendor kararı |
| 🟠 MED | Gemini slippage formülü cevabı | BIST için lineer/√V/Almgren-Chriss önerisi bekleniyor |
| 🟠 MED | DECISIONS.md metrics 11→12 | DEC-012 eklendi, By Area/Status/Metrics güncellenmedi |
| 🟠 MED | Correlation Matrix → Kelly entegrasyonu | Phase 4.3 |
| 🟠 MED | Broker API | Temmuz |
| 🟠 MED | SPEC_KELLY_1 implement | Finnet sonrası |
| 🟠 MED | Finnet/Matriks RFP | Haziran — vendor seçimi |
| 🟡 LOW | BISTDataStoreConnector gerçek endpoint | CSV URL kesinleşince güncelle |
| 🟡 LOW | L2 vs L5 korelasyon ölçümü | Gün 70+ (~Ağustos) |
| 🟡 LOW | Turkish BERT | FinBERT Phase 5 upgrade |
| 🟡 LOW | TL Bond Yields native | Phase 5 (ICDP/MINT) |
| 🟡 LOW | VaR modeli | Ağustos |
| 🟡 LOW | Slippage modeli | Phase 5+ (Almgren-Chriss) — Gemini cevabı bekleniyor |

---

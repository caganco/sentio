# BIST OS — System State
**Last Updated:** 21 Mayıs 2026 — Session #2 Kapanış (D-112..D-124)
**Session:** Orchestrator — Session #2 (Branch workflow, CI/CD, Ops reliability, Türkçe NLP, Research Registry)
**Repo:** github.com/raypun78/bist-trading-system (private — public release bekliyor)
**Git HEAD:** güncel (D-124 merged, 999 passed)

---

## CRITIC BACKLOG SUMMARY
- **Active findings:** 7 (CB-001/003/006 kapatıldı, CB-010 eklendi)
- **En yüksek öncelik:** CB-002 (Regime-blind weights, 8-10 puan) → Faz 3 (~Aug 2026)
- **Bu session'da kapatılan:** yok (Faz 3 bekliyor)
- **Bu session'da eklenen:** CB-010 (linear mimari)
- **Faz 3 bekleyen:** CB-002, CB-004, CB-005 — 14-20 puan/yıl
- **Yapısal (ayrı SPEC):** CB-007 (D-111), CB-008, CB-009 ✅ D-124 ile kapatıldı, CB-010
- **Detay:** CRITIC_BACKLOG.md

---

## SYSTEM READINESS
- **Overall Status:** ✅ PRODUCTION-READY
- **Test Coverage:** 999 passing (2 skipped)
- **Regression Guard:** ✅ Zero regression
- **CI/CD:** ✅ GitHub Actions 6-job (architecture/integration/lint/full-regression/security/type-check)
- **Pre-commit Hook:** ✅ Aktif
- **Branch Workflow:** ✅ CLAUDE.md zorunlu + gh CLI kuruldu (raypun78)
- **Branch Protection:** ⚠️ Private repo — enforcement yok (public sonrası aktif)
- **Architecture Tests:** 18/18 pass
- **README.md + ARCHITECTURE.md:** ✅
- **LICENSE:** ✅ MIT
- **positions.yaml:** ✅ git-ignored
- **Git History Scrub:** ⏳ PENDING — DEC-012
- **Risk-Free Rate:** %37 (TCMB)
- **Alpha Attribution Faz 1:** ✅ PRODUCTION (veri 21 May'den akıyor)
- **Critic Backlog System:** ✅ PRODUCTION (DEC-016)
- **Dependabot:** ✅ Aktif — 9 PR açık (pandas #6 hariç merge edilebilir)
- **Health Check:** ✅ scripts/health_check.py
- **Backup:** ✅ scripts/backup_db.py (30 gün retention)
- **Fail Notification:** ✅ logs/failures/ + opsiyonel email
- **Research Registry:** ✅ docs/research/ (RR-001..004)
- **mypy:** ✅ CI'da 0 hata (D-121)
- **gh CLI:** ✅ Kuruldu, auth tamamlandı (raypun78)
- **Multi-instance Builder:** ✅ DEC-018 ile belgelendi

---

## PORTFÖY (Güncel — positions.yaml, git-ignored)

| Sembol | Lot | Avg Cost | Fiyat | P&L% | Durum |
|--------|-----|----------|-------|------|-------|
| AKSEN | 413 | 87.90 | 73.50 | %-16.38 | 🔴 SELL emri verildi — gerçekleşmedi henüz |
| TTKOM | 329 | 60.65 | 57.45 | %-5.28 | ⚠️ SELL sinyali — beklemede |
| KCHOL | 81 | 188.83 | 183.30 | %-2.93 | ⚠️ SELL sinyali — beklemede |
| ENERY | 1543 | 9.07 | 8.23 | %-9.26 | ⚠️ SELL sinyali — beklemede |

**Fonlar:** DFI 12310 adet, DVT 4578 adet, PHE 7097 adet
**Makro durum:** BEAR rejim, CDS ~250 bps, TCMB %37, BIST100 ~13.200
**CHP Krizi (21 May 2026):** Mutlak butlan → BIST -%6, bankacılık -%8, devre kesici 17:42. Kurumlar milyarlarca TL satış yaptı.

---

## TEST SUITE STATUS
- **Total Tests:** 999 passing (2 skipped) ✅
- **Session #2 eklenenler:** +125 test (874→999)
- **D-124 eklenenler:** 46 test (lexicon/haiku/hybrid)

---

## AGENT PARAMETRELERI (STANDART)

| Agent | Model | Thinking | Effort | Plan Mode | Platform |
|-------|-------|----------|--------|-----------|----------|
| Architect | claude-sonnet-4-6 | ON | High | ON | Cowork |
| Builder | claude-sonnet-4-20250514 | ON | Medium | OFF | Claude Code |
| Analyst | claude-sonnet-4-20250514 | OFF | Low | OFF | — |
| Research | claude-sonnet-4-6 | OFF | Low | OFF | Yeni chat, projesiz |

**Orchestrator:** Desktop Claude — "ORCHESTRATOR" projesi

---

## LAYER STACK STATUS

| Layer | Status | Weight | Notlar |
|-------|--------|--------|--------|
| L1 Technical | ✅ LIVE | 0.25 | — |
| L2 Macro | ✅ LIVE | 0.20 | CDS percentile overlay aktif (DEC-017) |
| L3 KAP | ✅ LIVE | 0.27 | Google News RSS fallback, per-ticker merge |
| L4 Sentiment | ✅ LIVE | 0.12×conf | Hybrid Türkçe NLP: Tier-1 lexicon (93 term) + Claude Haiku 4.5 (D-124) |
| L5 Smart Money | ✅ LIVE | 0.10×conf | Progressive confidence + Fintables custody offline |
| L5b VIOP | ✅ Implemented | 0.00 | Engine'e bağlı değil, IC bekler |
| L6 Risk/Kelly | ✅ LIVE | 0.06 | Vol-aware stop aktif |

---

## SIGNAL ENGINE

**Macro Gate V2 (DEC-017):**
- BEAR soft: L2<45 + CDS<90th → 0.25x
- BEAR hard: L2<45 + CDS≥90th → 0.0x
- Hard exits: CDS>600bps, DD>15%, USDTRY +3σ

**TP:** BULL 2.5/4.0/6.5×ATR | BEAR 1.5/3.0/5.0×ATR
**Stop:** Vol-aware -%6/-%8/-%12/-%15, floor -%20
**Conviction:** BUY-STRONG ≥0.68→%32.5 | BUY-MEDIUM 0.55-0.67→%17.5

---

## ALPHA ATTRIBUTION — FAZ 1

- **Status:** ✅ Production — veri 21 May'den akıyor
- **Dashboard:** python -m src.reporting.ic_dashboard --tier 1
- **İlk anlamlı IC:** ~Ağustos 2026 (t-stat ≥ 2.0)
- **Faz 3:** IC yeterliyse weight rebalance

---

## MACRO DATA

- **CDS:** ~250 bps (CHP krizi — önceki 243.63)
- **TCMB:** %37.0
- **BIST100:** ~13.200
- **USD/TRY:** ~45.58
- **BRENT:** ~$111
- **EVDS:** Server migration nedeniyle geçici unavailable

---

## DECISION LOG

| ID | Başlık | Tarih | Status |
|----|--------|-------|--------|
| DEC-001..009 | Önceki kararlar | — | ✅ |
| DEC-010 | Strategist Advisory Boundary | May 2026 | ✅ |
| DEC-011 | src/scrapers/ Reserved for L3 | May 2026 | ✅ |
| DEC-012 | Git History Scrub | May 2026 | ⏳ Cagan manuel |
| DEC-013 | L5 Progressive Confidence | May 2026 | ✅ |
| DEC-014 | borsapy Lisans Dışlama | May 2026 | ✅ |
| DEC-015 | Alpha Attribution Faz 1 | 20 May 2026 | ✅ |
| DEC-016 | Critic Backlog System | 20 May 2026 | ✅ |
| DEC-017 | Macro Gate Softening | 20 May 2026 | ✅ |
| DEC-018 | Multi-instance Builder + Branch Workflow | 21 May 2026 | ✅ |

---

## RESEARCH REGISTRY

| ID | Başlık | Tarih | Bağlı CB/SPEC | Status |
|----|--------|-------|---------------|--------|
| RR-001 | Fintables takas scraper fizibilite | 21 May 2026 | D-116 | ✅ Applied |
| RR-002 | AKD terminalleri Python entegrasyonu | 21 May 2026 | D-116 | ✅ Applied |
| RR-003 | Composite mimari alternatifleri | 21 May 2026 | CB-002, CB-010 | ⏳ D-123 HMM SPEC bekliyor |
| RR-004 | Türkçe Finansal NLP — L4 Sentiment | 21 May 2026 | CB-009 | ✅ D-124 ile implement edildi |

---

## L5 SMART MONEY TAKVİMİ
- **Gün 5 (21 Mayıs):** ✅ Fintables custody offline hazır — canlı doğrulama bekliyor
- **Gün 10 (~28 Mayıs):** Momentum sinyali live
- **Gün 20 (~7 Haziran):** Full composite
- **Gün 70+ (~Ağustos):** L2 vs L5 korelasyon

---

## SPECS DURUMU

| SPEC | Status | Direktif |
|------|--------|---------|
| SPEC_ALPHA_INFRASTRUCTURE_1 | ✅ | D-107/D-112 |
| SPEC_MACRO_GATE_SOFTENING_1 | ✅ | D-108 |
| SPEC_TP_REGIME_CONDITIONAL_1 | ✅ | D-109/D-113 |
| SPEC_STOPLOSS_VOLATILITY_AWARE_1 | ✅ | D-110 |
| SPEC_VIOP_SIGNAL_1 | ✅ engine bağlı değil | D-099 |
| SPEC_FINTABLES_TAKAS_SCRAPER_1 | ✅ offline | D-116 — canlı doğrulama bekliyor |
| SPEC_L4_TURKISH_HYBRID_NLP | ✅ | D-124 merged |

---

## AÇIK DIREKTIFLER

| ID | Target | Konu | Status |
|----|--------|------|--------|
| D-111 | Architect/Builder | CB-007 Foreign flow L2 migration | ⏳ |
| D-123 | Architect | HMM Regime-Conditional Weights (RR-003 §3) | ⏳ Sonraki session |

---

## CAGAN MANUEL LİSTESİ
1. **DEC-012 Git History Scrub** — public öncesi zorunlu
2. **Portföy** — AKSEN SELL emri aktif; TTKOM/KCHOL/ENERY kararı bekliyor
3. **Fintables canlı doğrulama** — playwright + CSS selector (D-116 RUNBOOK'ta)
4. **GitHub Secrets** ✅ eklendi
5. **Dependabot PR'ları** — #2-#5,#7-#10 merge edilebilir; #6 pandas beklet
6. **Fintables MKK lisansı** ✅ 78 TL/ay aktif

---

## BACKLOG

| Priority | Task | Notes |
|----------|------|-------|
| 🔴 HIGH | Portföy kararı | AKSEN SELL + TTKOM/KCHOL/ENERY |
| 🔴 HIGH | DEC-012 Git History Scrub | Public öncesi |
| 🟠 MED | D-123 HMM SPEC | Architect — sonraki session öncelik |
| 🟠 MED | D-116 canlı doğrulama | Playwright CSS selector |
| 🟠 MED | Dependabot PR merge | #2-#5,#7-#10 (pandas hariç) |
| 🟠 MED | L5 Gün 10 (~28 Mayıs) | Momentum sinyali live mu? |
| 🟠 MED | IC dashboard günlük kontrol | Veri akıyor mu? |
| 🟡 LOW | D-111 CB-007 | Foreign flow L2 |
| 🟡 LOW | CB-008 VIOP | IC t-stat ≥ 2.0 sonrası |
| 🟡 LOW | Slippage modeli | Phase 5+ |
| 🟡 LOW | Public Release Audit | Kariyer başvurusu öncesi |

---

## ARCHITECTURE SAFETY
- **Threshold Centralization:** ✅
- **Weight Integrity:** ✅ MASTER_WEIGHTS Σ=1.00
- **Runtime Normalizer:** ✅ Floor 0.78
- **Architecture Tests:** 18/18 pass
- **mypy:** ✅ 0 hata
- **Branch protection:** ⚠️ Public sonrası tam aktif

---

*OS_STATE — 21 Mayıs 2026 Session #2 Kapanış (D-124 merged, 999 passed)*
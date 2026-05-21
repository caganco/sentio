# BIST OS — System State
**Last Updated:** 21 Mayıs 2026
**Session:** Orchestrator — D-071..D-110 (Scheduler fix, L4/L5/VIOP, Alpha Attribution, Macro Gate, TP, Stop)
**Repo:** github.com/raypun78/bist-trading-system (private — public release bekliyor)
**Git HEAD:** 4de8118 (DEC-016 + D-108/109/110)

---

## CRITIC BACKLOG SUMMARY
- **Active findings:** 6 (9'dan 3 kapatıldı — CB-001/003/006)
- **En yüksek öncelik:** CB-002 (Regime-blind weights, 8-10 puan) → Faz 3 (IC datası, ~Aug 2026)
- **Bu session'da kapatılan:** CB-001 (D-108), CB-003 (D-109), CB-006 (D-110)
- **Faz 3 bekleyen:** CB-002, CB-004, CB-005 — 14-20 puan/yıl
- **Yapısal (ayrı SPEC):** CB-007 (D-111), CB-008, CB-009
- **Detay:** [`CRITIC_BACKLOG.md`](CRITIC_BACKLOG.md)

**Orchestrator notu:** Bu özet, session başında 30 saniyede taranabilecek snapshot'tır. Detay için CRITIC_BACKLOG.md zorunlu okuma.

---

### SYSTEM READINESS
- **Overall Status:** ✅ PRODUCTION-READY
- **Test Coverage:** 874 passing (2 skipped)
- **Regression Guard:** ✅ Zero regression
- **CI/CD:** ✅ GitHub Actions tam yeşil (4-job: architecture / integration / lint / full-regression)
- **Pre-commit Hook:** ✅ Aktif (Tier 1+2 + ruff, commit blocker)
- **pytest.ini:** addopts = --tb=short (-q kaldırıldı, summary görünür)
- **Architecture Tests:** 18/18 pass
- **README.md + ARCHITECTURE.md:** ✅ eklendi (df869ae)
- **LICENSE:** ✅ MIT (1afd2d0)
- **positions.yaml:** ✅ git-ignored
- **Git History Scrub:** ⏳ PENDING — DEC-012 / public yapmadan önce Cagan yapacak
- **Risk-Free Rate:** %37 (TCMB scraper, D-091 — eski %42 stale)
- **Sharpe (RF %37):** Revize edilmedi (alpha problemi devam ediyor)
- **Bootstrap System:** ✅ Tiered (Tier 1+2: 2.2s, Tier 3: ~45s)
- **Architecture Safety:** ✅ Enforced + genişletildi
- **Signal Alerting:** ✅ Live
- **Decision Log:** ✅ Active (DEC-001..DEC-017)
- **Token Efficiency:** ✅ Optimized
- **Phase 4.5:** ✅ PRODUCTION
- **Alpha Attribution Faz 1:** ✅ PRODUCTION (D-107, 20 May 2026)
- **Critic Backlog System:** ✅ PRODUCTION (DEC-016, 4de8118)

---

### PORTFÖY (Güncel — positions.yaml, git-ignored)

| Sembol | Lot | Avg Cost | Durum |
|--------|-----|----------|-------|
| AKSEN | 413 | 87.90 | ⚠️ SELL — stop kırıldı (79.85 < 80.87) |
| TTKOM | 329 | 60.65 | ⚠️ SELL — BEAR macro, kelly=SKIP |
| KCHOL | 81 | 188.83 | ⚠️ SELL — +3.27% kâr masada |
| ENERY | 1543 | 9.07 | ⚠️ SELL — -4.63%, umut pozisyonu |

**Fonlar:** DFI 12310 adet, DVT 4578 adet, PHE 7097 adet
**Makro durum:** BEAR rejim, CDS 243.63 bps, TCMB %37, BIST100 14029, USD/TRY 45.58, BRENT $111.06
**Not:** İşlemler yapılmadı — Cagan onayı bekliyor

---

### TEST SUITE STATUS
- **Total Tests:** 874 passing (2 skipped) ✅
- **Zero Regression:** ✅ Confirmed
- **Architecture Tests:** 18/18 pass (D-108: +3, D-109: +2, D-110: +2)
- **Session #1 eklenenler:** +128 test (801→874 net, bazı cleanup'lar dahil)

---

### AGENT PARAMETRELERI (STANDART)

| Agent | Model | Thinking | Effort | Plan Mode | Platform |
|-------|-------|----------|--------|-----------|----------|
| Architect | claude-sonnet-4-6 | ON | High | ON | Cowork (ayrı proje: "BIST OS — Architect") |
| Builder | claude-sonnet-4-20250514 | ON | Medium | OFF | Claude Code |
| Analyst | claude-sonnet-4-20250514 | OFF | Low | OFF | — |
| Research | claude-sonnet-4-6 | OFF | Low | OFF | Yeni chat, projesiz |

**Orchestrator:** Desktop Claude — "ORCHESTRATOR" projesi (bu session)

---

### LAYER STACK STATUS

| Layer | Status | Weight | Notlar |
|-------|--------|--------|--------|
| L1 Technical | ✅ LIVE | 0.25 | — |
| L2 Macro | ✅ LIVE | 0.20 | CDS percentile overlay aktif (D-108, DEC-017) |
| L3 KAP | ✅ LIVE | 0.27 | Google News RSS fallback |
| L4 Sentiment | ✅ LIVE | 0.12×conf | Mynet + FinBERT, conf ~0.475 (THYAO 10 makale) |
| L5 Smart Money | ✅ LIVE | 0.10×conf | Progressive confidence, Gün 3+ |
| L5b VIOP | ✅ Implemented | 0.00 | Engine'e bağlı değil, IC bekler (CB-008) |
| L6 Risk/Kelly | ✅ LIVE | 0.06 | Vol-aware stop aktif (D-110) |

---

### SIGNAL ENGINE (GÜNCEL — D-108/109/110 sonrası)

**Macro Gate V2 (D-108, DEC-017):**
- BEAR soft: L2<45 + CDS<90th percentile → 0.25x scaling
- BEAR hard: L2<45 + CDS≥90th percentile → 0.0x
- BULL/NEUTRAL: CDS stress dampening (>90th → 0.25x cap)
- Hard exits: CDS>600bps, DD>15%, USDTRY +3σ (USDTRY z-score Faz 1.5)

**TP Mekanizması (D-109):**
- BULL: TP1 2.5×ATR, TP2 4.0×ATR, TP3 6.5×ATR (let winners run)
- NEUTRAL/BEAR: TP1 1.5×ATR, TP2 3.0×ATR, TP3 5.0×ATR (mevcut)
- Monotonicity guard eklendi

**Stop-loss (D-110):**
- Vol-aware tier: ATR/P <2% → -%6, 2-4% → -%8, 4-6% → -%12, >6% → -%15
- Hard floor: -%20
- Risk parity sizing: equity × 1% / stop_distance
- Legacy EXIT_STOP_LOSS=0.92 korundu (backward compat)

**Conviction Tiers:**
- BUY-STRONG: ≥0.68 → %32.5 pozisyon, max 4
- BUY-MEDIUM: 0.55–0.67 → %17.5 pozisyon, max 2
- WATCH: <0.55 → pozisyon yok

---

### ALPHA ATTRIBUTION — FAZ 1 (D-107)

- **Status:** ✅ Production (20 May 2026)
- **Signal log:** `data/signal_logs/` — günlük parquet, her sembol × her layer
- **Forward returns:** T+1/T+5/T+20/T+60
- **IC calculator:** Spearman Rank-IC + IR + t-stat + p-value
- **Brinson attribution:** Sector allocation + selection (Brinson-Fachler)
- **LOO attribution:** Leave-one-out marginal contribution per layer
- **Dashboard:** `python -m src.reporting.ic_dashboard --tier 1`
- **Veri birikimi başladı:** 20 May 2026
- **İlk anlamlı IC:** ~3 ay (Ağustos 2026, t-stat ≥ 2.0)
- **Faz 3 weight rebalance:** IC datası yeterliyse (~Ağustos 2026)

---

### MACRO DATA

- **CDS:** 243.63 bps (WGB scraper, D-091) — <280 eşiği, risk primi normal
- **TCMB Politika Faizi:** %37.0 (tcmb.gov.tr scraper, D-091)
- **EVDS:** Server-side migration nedeniyle geçici unavailable
- **LOCAL_MACRO_WEIGHTS:** tcmb 0.40, cds 0.40, bist_foreign_weekly 0.20
- **MACRO_WEIGHTS_COMPOSITE:** global_signals 0.25, tcmb 0.25, cds 0.25, dxy 0.25

---

### DECISION LOG

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

---

### L5 SMART MONEY — PROGRESSIVE BUILD TAKVİMİ
- **Gün 1 (17 Mayıs):** ✅ Parquet DB başladı
- **Gün 3 (19 Mayıs):** ✅ Scheduler fix, CI/CD kuruldu
- **Gün 10 (~28 Mayıs):** Momentum sinyali live (10-day foreign ratio change)
- **Gün 20 (~7 Haziran):** Full composite
- **Gün 70+ (~Ağustos):** L2 vs L5 korelasyon ölçümü

**L5 Kompozisyon:**
```
foreign_ratio_score   × 0.70
short_interest_score  × 0.30
L5_CONF_PARTIAL = 0.5  (Gün 10-19)
L5_CONF_FULL    = 0.8  (Gün 20+)
```

---

### SPECS DURUMU

| SPEC | Status | Direktif |
|------|--------|---------|
| SPEC_L5_CONFIDENCE_PROGRESSIVE_1 | ✅ Implement | D-086 |
| SPEC_SECTOR_ROTATION_1 | ✅ Yazıldı | D-087 Builder (Haziran) |
| SPEC_L4_NEWS_1 | ✅ Implement | D-094 |
| SPEC_ALPHA_INFRASTRUCTURE_1 | ✅ Implement | D-107 — Faz 1 aktif |
| SPEC_MACRO_GATE_SOFTENING_1 | ✅ Implement | D-108 — DEC-017 |
| SPEC_TP_REGIME_CONDITIONAL_1 | ✅ Implement | D-109 — caller wiring bekliyor |
| SPEC_STOPLOSS_VOLATILITY_AWARE_1 | ✅ Implement | D-110 |
| SPEC_VIOP_SIGNAL_1 | ✅ Implement (engine bağlı değil) | D-099 — IC bekler |

---

### CAGAN MANUEL LİSTESİ
1. **GitHub Secret: ANTHROPIC_API_KEY** — repo Settings → Secrets → Actions
2. **GitHub Secret: EVDS_API_KEY** — aynı yerden
3. **DEC-012 Git History Scrub** — public yapmadan önce (irreversible)
4. **Portföy işlemleri** — AKSEN/TTKOM/KCHOL/ENERY SELL sinyalleri bekliyor
5. **MKK API** — kapdestek@mkk.com.tr (survivorship-free veri)
6. **Finnet RFP** — haber API fiyatlandırması

---

### AÇIK DIREKTIFLER

| ID | Target | Konu | Status |
|----|--------|------|--------|
| D-021 | Builder | Exit optimization | ⏸️ SUSPENDED |
| D-023 | Builder | VERDA application | ✅ SENT — yanıt bekleniyor |
| D-024 | Builder | Matriks AKD | ✅ Fiyat teklifi bekleniyor |
| D-071..D-110 | Builder/Architect | Session #1 direktifleri | ✅ CLOSED |
| D-111 | Architect/Builder | CB-007 Foreign flow L2 migration | ⏳ Sıraya alınacak |

---

### BACKLOG

| Priority | Task | Notes |
|----------|------|-------|
| 🔴 HIGH | DEC-012 Git History Scrub | Public release öncesi — Cagan manuel |
| 🔴 HIGH | Portföy işlemleri (4 pozisyon) | BEAR SELL sinyali — Cagan kararı |
| 🟠 MED | D-111 CB-007 Foreign flow L2 | RESEARCH-014 bulgusu |
| 🟠 MED | D-109 caller wiring | daily_update.py detect_levels entegrasyonu |
| 🟠 MED | D-108 backtest comparison | Alpha gerçekten kapandı mı? |
| 🟠 MED | L5 Gün 10 monitoring (~28 Mayıs) | Momentum sinyali live mu? |
| 🟠 MED | IC dashboard günlük | Veri akıyor mu kontrol |
| 🟠 MED | Matriks AKD fiyat teklifi | Vendor kararı |
| 🟠 MED | Finnet/Matriks RFP | Haber API — Haziran |
| 🟡 LOW | CB-009 Türkçe NLP reform | Ayrı SPEC, sırası gelmedi |
| 🟡 LOW | CB-008 VIOP IC kalibrasyon | IC t-stat ≥ 2.0 sonrası |
| 🟡 LOW | MKK API sözleşmesi | Survivorship-free veri |
| 🟡 LOW | L2 vs L5 korelasyon | Gün 70+ (~Ağustos) |
| 🟡 LOW | Slippage modeli | Phase 5+ |

---

### ARCHITECTURE SAFETY
- **Threshold Centralization:** ✅ All constants from thresholds.py (14 IC + 7 gate + 4 TP + 9 stop sabit eklendi)
- **Weight Integrity:** ✅ MASTER_WEIGHTS Σ=1.00
- **Runtime Normalizer:** ✅ Floor 0.78 (DEC-009)
- **Architecture Tests:** 18/18 pass
- **L5 VERDA-free guarantee:** ✅ Tier 1'de her bootstrap

---

*OS_STATE — 20 Mayıs 2026 Session #1 Kapanış*
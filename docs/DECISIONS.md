# Architecture Decision Log

**System:** BIST Trading OS v5.0  
**Location:** `docs/decisions/`  
**Last Updated:** 31 May 2026  
**Total Decisions:** 21 karar (DEC-001..DEC-013, DEC-015..DEC-017, DEC-022..DEC-023, DEC-030..DEC-032, DEC-034, DEC-046)  
**Purpose:** Centralized machine-readable log of all architectural decisions

> **For Claude Code users:** Query decisions by `area`, `status`, or `affected_files` to understand context for code changes.

---

## QUICK INDEX

| ID | Title | Area | Status | Date | Affects |
|---|---|---|---|---|---|
| **DEC-001** | KAP Edge Cases & Holiday Handling | Data Sources | ✅ Implemented | 2026-05-14 | `src/data/kap_parser.py`, `src/data/kap_scraper.py` |
| **DEC-002** | CDS iShares Proxy Fallback | Data Sources | ✅ Implemented | 2026-05-13 | `src/data/macro.py`, `tests/test_cds.py` |
| **DEC-003** | Macro-Equity Correlation Layer | Signal Architecture | ✅ Implemented | 2026-05-12 | `src/signals/layers/macro_layer.py` |
| **DEC-004** | Report Token Optimization (≤600) | Efficiency | ✅ Implemented | 2026-05-11 | `src/reports/daily_report.py`, `src/reports/templates/` |
| **DEC-005** | Signal Layer Weights (4-Layer Stack) | Signal Architecture | ✅ Implemented | 2026-05-10 | `src/signals/engine.py`, `src/signals/thresholds.py`, `config.yaml` |
| **DEC-006** | Kelly Criterion Position Sizing | Risk Management | ✅ Implemented | 2026-05-19 | `src/risk/kelly.py` |
| **DEC-007** | Ruthless Alpha Philosophy — Remove Defensive Constraints | Signal Engine | ✅ Decided | 2026-05-16 | `src/signals/engine.py`, `src/signals/thresholds.py`, `tests/test_engine.py` |
| **DEC-008** | VERDA Independence — L5 Core Decoupled from Vendor | Signal Architecture | ✅ Decided | 2026-05-18 | `src/signals/layers/smart_money_layer.py`, `tests/test_architecture.py` |
| **DEC-009** | Phase 4.5 Normalizer — Emergent 0.78 Floor (not hardcoded) | Signal Engine | ✅ Decided | 2026-05-18 | `src/signals/thresholds.py`, `src/signals/engine.py`, `src/utils/weight_validator.py` |
| **DEC-010** | Strategist Advisory Boundary — LLM Output is Read-Only Narrative | Signal Architecture | ✅ Decided | 2026-05-19 | `strategist.py`, `engine.py` |
| **DEC-011** | src/scrapers/ — Financial-Statement Parser Intentionally Preserved (Not Wired) | Signal Architecture | ✅ Decided | 2026-05-19 | `src/scrapers/` |
| **DEC-012** | Git History Scrub — Personal Portfolio Data | Security/Release | ✅ Decided | 2026-05-19 | `config.yaml` |
| **DEC-013** | L5 Progressive Confidence Ramp (flat 0.8 → 3-phase ladder) | Signal Engine | ✅ Implemented | 2026-05-19 | `src/signals/engine.py`, `src/signals/layers/smart_money_layer.py` |
| **DEC-015** | Alpha Attribution Infrastructure (Faz 1) | Signal Architecture / Analytics | ✅ Implemented | 2026-05-20 | `src/analytics/`, `src/reporting/`, `src/data/signal_logger.py`, `src/data/universe_snapshot.py`, `scripts/daily_update.py`, `src/signals/thresholds.py` |
| DEC-016 | Critic Backlog System (persistent memory) | 2026-05-20 | ✅ |
| **DEC-017** | Macro Gate Softening (CDS Percentile Overlay) | Signal Architecture / Risk Management | ✅ Implemented | 2026-05-20 | `src/signals/macro_regime_gate.py`, `src/signals/layers/macro_layer.py`, `src/signals/local/cache_store.py`, `src/signals/thresholds.py`, `scripts/daily_update.py` |
| **DEC-022** | L6 Bayesian kalibrasyonu dışı — statik 0.03 | Signal Architecture / Analytics | ✅ Decided | 2026-05-24 | `src/signals/thresholds.py` |
| **DEC-023** | MASTER_WEIGHTS manuel onay protokolü | Signal Architecture / Analytics | ✅ Decided | 2026-05-24 | `src/signals/thresholds.py`, `docs/DECISIONS.md` |
| **DEC-030** | Multi-LLM Jury mimarisi (2-LLM MVP, Phase 6+) | Signal Architecture / AI | ✅ Decided | 2026-05-26 | `src/signals/` (Phase 6+, Q1 2027+) |
| **DEC-031** | TÜFE canonical kod: TP.FG.J0 | Data Sources | ✅ Decided | 2026-05-26 | `src/data/`, `src/signals/thresholds.py` |
| **DEC-032** | DEC-010-v2: LLM "genuine input" rolü | Signal Architecture / AI | ✅ Decided | 2026-05-26 | `strategist.py`, `src/signals/engine.py` |
| **DEC-034** | D-163/D-173 backtest/production sizing divergence kapandi | Position Sizing | ✅ Closed | 2026-05-28 | `src/backtest/engine.py`, `src/risk/position_sizer_v2.py` |
| **DEC-046** | D-188 olay-confluence karar-kurali FROZEN (iki-null + Holm-per-type + XU100-relative pozitif) | Screening / Measurement | ✅ Frozen (pre-registration) | 2026-05-31 | `src/screening/event_*.py`, `docs/event_test/` |
---

> **DEC numara notu:** DEC-035..DEC-045 araligi diger feature/research dallarinda
> tahsisli (orn. DEC-044 = D-186, DEC-045 = D-187), bu PR'lar henuz master'a merge
> edilmedi -> bu dosyada gorunmuyor. D-188 sirayi DEC-046 ile surdurur; merge
> sirasinda cakisma yok.

**DEC-046 — D-188 olay-tetikli confluence karar-kurali (FROZEN, pre-registration).**
Confluence "edge tasiyor" ANCAK: (1) NULL-1 (olay-kosullu rastgele-teknik) >=%95, VE
(2) NULL-2 (olaysiz rastgele-teknik) >=%95, VE (3) XU100-relative pozitif (maliyet+slippage
sonrasi), VE (4) Holm-Bonferroni (olay-tipi-basina AYRI) anlamli. Ornek < `MIN_EVENTS_PER_TYPE`
(30) -> `undetermined` (pass/fail degil). Post-hoc gevsetme YASAK. Sonuc-oncesi donduruldu
(`docs/event_test/STAGE0_event_confluence_preregistration.json`). DEC-039 geregi program
OLCER + onerir; Yol-1 lab'a terfi the project karari.

## DECISION CATEGORIES

### By Area

**Data Sources** (2 implemented)
- [DEC-001](decisions/DEC-001.md) – KAP holiday handling + bulk queue
- [DEC-002](decisions/DEC-002.md) – CDS fallback to iShares model

**Signal Architecture** (5)
- [DEC-003](decisions/DEC-003.md) – Correlation scoring per stock
- [DEC-005](decisions/DEC-005.md) – Weight distribution
- [DEC-008](decisions/DEC-008-verda-independence.md) – L5 VERDA independence
- [DEC-010](decisions/DEC-010-strategist-advisory-boundary.md) – Strategist advisory boundary
- [DEC-011](decisions/DEC-011-scrapers-reserved.md) – src/scrapers/ reserved

**Signal Engine** (3)
- [DEC-007](decisions/DEC-007.md) – Ruthless Alpha philosophy
- [DEC-009](decisions/DEC-009-phase-45-normalizer-derivation.md) – Emergent 0.78 normalizer floor
- [DEC-013](decisions/DEC-013-l5-progressive-confidence.md) – L5 progressive confidence ramp (3-phase ladder)

**Efficiency** (1 implemented)
- [DEC-004](decisions/DEC-004.md) – Token budget optimization

**Risk Management** (1 implemented)
- [DEC-006](decisions/DEC-006.md) – Position sizing (Kelly Criterion, `src/risk/kelly.py`)

**Security / Release** (1)
- [DEC-012](decisions/DEC-012-git-history-scrub.md) – Git history scrub (personal portfolio data; public-release blocker, the maintainer manual)



### By Status

**✅ Implemented (7)**
- DEC-001, DEC-002, DEC-003, DEC-004, DEC-005, DEC-006, DEC-013

**✅ Decided (6)**
- DEC-007, DEC-008, DEC-009, DEC-010, DEC-011, DEC-012

**💡 Pending (0)**
- (none)

---

## QUICK REFERENCE

### Find decisions affecting a file:

```bash
# Example: What decisions affect src/signals/engine.py?
grep -r "engine.py" docs/decisions/DEC-*.md
# Answer: DEC-005, DEC-007, DEC-009
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

**Current State (19 May 2026):**

| Metric | Count |
|---|---|
| Total Decisions | 13 |
| Implemented | 7 (54%) |
| Decided | 6 (46%) |
| Pending | 0 (0%) |
| Data Sources | 2 |
| Signal Architecture | 5 |
| Signal Engine | 3 |
| Efficiency | 1 |
| Risk Management | 1 |
| Security / Release | 1 |

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

- `docs/BOOT_ARCHITECT.md` – Architecture overview
- `docs/BOOT_BUILDER.md` – Builder development guidelines
- `CLAUDE.md` – Project instructions & bootstrap protocol
- `memory/MEMORY.md` – Session state & context

---

---

## DEC-022 — L6 Bayesian kalibrasyonu dışı: statik 0.03

| Alan | Değer |
|------|-------|
| **ID** | DEC-022 |
| **Başlık** | L6 Bayesian kalibrasyonu dışı — statik 0.03 |
| **Tarih** | 24 May 2026 |
| **Alan** | Signal Architecture / Analytics |
| **Durum** | ✅ Decided |
| **Etkilenen Dosyalar** | `src/signals/thresholds.py` |

### Gerekçe

L6 Risk/Kelly bir alfa sinyali değildir; pozisyon büyütücüdür (position sizer).
ICIR-tabanlı Bayesian kalibrasyon bu katmana anlamsızdir:

- L6 çıktısı bireysel hisse alpha tahmini değil, portföy büyüklük ayarı yapar.
- Sinyal IC'si ile L6 katkısı arasında doğrudan ilişki yoktur.
- Bayesian update yalnızca gerçek alpha üreten L1-L5 katmanlarına uygulanır.

**Sonuç:** L6 ağırlığı `MASTER_WEIGHTS["risk"] = 0.03` olarak statik kalır.
WeightCalibrator (Faz 3) L6'yı güncelleme kapsamı dışında tutar.

**Kaynak:** RR-010 §6 madde 10

---

## DEC-023 — MASTER_WEIGHTS manuel onay protokolü

| Alan | Değer |
|------|-------|
| **ID** | DEC-023 |
| **Başlık** | MASTER_WEIGHTS manuel onay protokolü |
| **Tarih** | 24 May 2026 |
| **Alan** | Signal Architecture / Analytics |
| **Durum** | ✅ Decided |
| **Etkilenen Dosyalar** | `src/signals/thresholds.py`, `docs/DECISIONS.md` |

### Gerekçe

WeightCalibrator (Faz 3, D-135) otomatik ağırlık önerileri üretecektir.
Bu öneriler doğrudan üretime geçmez; aşağıdaki 4 adımlı protokol zorunludur:

1. **Orchestrator değerlendirir:** WeightCalibrator çıktısı
   `data/analytics/weight_history.parquet`'e yazılır. Orchestrator
   önerilen değişimi IC metrikleri, regime koşulları ve CB geçmişiyle
   karşılaştırarak değerlendirir.
2. **the maintainer onaylar:** Orchestrator değerlendirmesini the maintainer inceler ve
   açık onay verir. Sessiz kalma onay sayılmaz.
3. **Ayrı spec ile thresholds.py güncellenir:** Onaylanan değerler
   ayrı bir spec (D-XXX) kapsamında `MASTER_WEIGHTS` bloğuna yazılır.
   Hiçbir Builder `MASTER_WEIGHTS`'i kendi inisiyatifiyle değiştiremez.
4. **PR → CI → merge:** Standart branch workflow (CLAUDE.md) uygulanır.
   Green CI + the maintainer merge onayı olmadan üretim değişmez.

**Kapsam dışı (statik):** L6 (DEC-022 gereği), τ=0 fazı (60 işlem günü dolmadan
herhangi bir otomatik kalibrasyon başlamaz — IC_BAYESIAN_TAU_MIN_DAYS=60).

**Kaynak:** SPEC_IC_FRAMEWORK_1 K-06, G-22

---

**Owner:** Architect  
**Maintained By:** Architect  
**Last Review:** 26 May 2026

---

## DEC-030 — Multi-LLM Jury Mimarisi (2-LLM MVP)

| Alan | Değer |
|------|-------|
| **ID** | DEC-030 |
| **Başlık** | Multi-LLM Jury mimarisi: 2-LLM MVP (Bull=Claude, Bear=GPT) |
| **Tarih** | 26 May 2026 |
| **Alan** | Signal Architecture / AI |
| **Durum** | ✅ Decided |
| **Etkilenen Dosyalar** | `src/signals/` (Phase 6+, Q1 2027+) |

### Gerekçe

Tek LLM (Claude) hem bull hem bear argümanı ürettiğinde echo chamber riski vardır:
kendi önceki output'una karşı "gerçek" itiraz üretemez, bias'ı amplifiye eder.

**Mimari Karar:**
- 2-LLM MVP: Bull rolü = Claude (Anthropic), Bear rolü = GPT-4o (OpenAI)
- **Farklı sağlayıcı zorunlu** — aynı sağlayıcının farklı modelleri kabul edilmez
- `llm_agreement_scalar`: iki LLM aynı yönde hemfikirse güven artar,
  çelişkide ise `disagreement-aware sizing` devreye girer (pozisyon küçülür)
- Phase 6+ kapsamı, Q1 2027+ hedef tarih

**Kapsam Dışı (şimdilik):**
- 3. LLM ekleme (Phase 7+)
- Ağırlıklı jury (eşit oy — MVP simplicity)

**Kaynak:** RR-019

---

## DEC-031 — TÜFE Canonical Kod: TP.FG.J0

| Alan | Değer |
|------|-------|
| **ID** | DEC-031 |
| **Başlık** | TÜFE canonical kod: TP.FG.J0 (TP.FE.OKTG01 deprecated, stale) |
| **Tarih** | 26 May 2026 |
| **Alan** | Data Sources |
| **Durum** | ✅ Decided |
| **Etkilenen Dosyalar** | `src/data/`, `src/signals/thresholds.py` |

### Gerekçe

D-151 empirik test sonucu: `TP.FE.OKTG01` kodu EVDS'te stale veri döndürüyor
(son güncelleme tarihi geride kalıyor, güncel TÜFE rakamını yansıtmıyor).

**Canonical Kodlar:**
- **TÜFE (CPI):** `TP.FG.J0` — aktif, güncel veri ✅
- **Yİ-ÜFE (PPI):** `TP.FG.J01` — aktif, güncel veri ✅
- ~~`TP.FE.OKTG01`~~ — deprecated, stale, KULLANILMAZ

**Staleness Guard:**
- `EVDS_TUFE_STALE_DAYS = 45` — son veri 45 günden eskiyse uyarı üretilir
- Neden 45: TÜFE aylık açıklanır (~30 gün), 45 gün yayın gecikmesi + buffer

**Kaynak:** RR-021 + D-151 empirik test

---

## DEC-032 — DEC-010-v2: LLM "Genuine Input" Rolü

| Alan | Değer |
|------|-------|
| **ID** | DEC-032 |
| **Başlık** | DEC-010 → DEC-010-v2: LLM "reporter" rolünden "genuine input" rolüne geçiş |
| **Tarih** | 26 May 2026 |
| **Alan** | Signal Architecture / AI |
| **Durum** | ✅ Decided |
| **Etkilenen Dosyalar** | `strategist.py`, `src/signals/engine.py` |

### Gerekçe

DEC-010 (2026-05-19): LLM çıktısı read-only narrative — composite'e katkısı sıfır.
Bu tasarım LLM'i salt raporcu konuma indirgiyordu; gerçek değer üretme kapasitesi bloke.

**DEC-010-v2 ile Değişen:**

| | DEC-010 (eski) | DEC-010-v2 (yeni) |
|---|---|---|
| LLM rolü | Reporter (narrative only) | Genuine input (composite etkisi var) |
| Composite katkı | 0 | Çarpımsal multiplier ∈ [0.5, 1.2] |
| Soft veto | — | conf < 0.30 → SKIP (güvensiz analiz dışlanır) |
| Hard veto | — | **YASAK** (LLM tek başına BUY/SELL engelleyemez) |
| BUY kararı | LLM etkileyemez | LLM agreement ile değişebilir — kasıtlı hibrit |

**Korunan İlkeler:**
- the maintainer nihai override yetkisi korunur
- Hard veto yasak: LLM sistemi tek başına durduramayz, sadece ölçeklendirir
- Soft veto (conf < 0.30): güvensiz analiz sessizce atlanır, hata üretmez
- `llm_agreement_scalar` ∈ [0.5, 1.2]: floor 0.5 (en kötü yarıya indirger),
  cap 1.2 (en iyi %20 büyütür) — aşırı amplifikasyon engeli

**DEC-010 ile ilişki:** DEC-010 superseded by DEC-010-v2 (bu karar).
DEC-010 orijinal metni arşiv olarak korunur.

**Kaynak:** CRR-001

---

## DEC-034 — D-163/D-173 Backtest/Production Sizing Divergence ✅ KAPANDI

| Alan | Değer |
|------|-------|
| **ID** | DEC-034 |
| **Başlık** | bist_trend_scalar backtest engine'e entegre edildi (D-173) |
| **Tarih** | 28 May 2026 |
| **Alan** | Position Sizing |
| **Durum** | ✅ Closed (D-173 ile kapandi) |
| **Etkilenen Dosyalar** | `src/backtest/engine.py`, `src/risk/position_sizer_v2.py` |

### Gecmis (D-163)

D-163 `bist_trend_scalar` production sizing'de aktif oldu (daily_update.py).
Backtest engine'e entegre edilmedi — tarihi XU100 serisi ayri veri katmani
gerektiriyordu; D-163 kapsami disindaydi.

### Kapanis (D-173)

`BacktestEngine.run(benchmark_series=...)` parametresi artik BIST100 tarihi
fiyat serisini kabul eder. `_run_loop` basinda:
- `bist.rolling(20/50).mean().shift(1)` — look-ahead guard ile MA hesabi.
- `compute_bist_trend_scalar(close, ma20, ma50)` → 0.75/1.00/1.25.
- Per-date scalar serisi `_bist_ma_scalar_series`'e kaydedilir.

`_execute_buy` icinde Kelly allocation × scalar uygulanir. Production ve
backtest sizing artik ayni mantigi paylasiyor.

**Kaynak:** D-163 + D-173 specleri

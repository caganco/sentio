# Architecture Decision Log

**System:** BIST Trading OS v5.0  
**Location:** `docs/decisions/`  
**Last Updated:** 24 May 2026  
**Total Decisions:** 16 karar (DEC-001..DEC-013, DEC-015..DEC-017, DEC-022..DEC-023)  
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
---

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
**Last Review:** 24 May 2026

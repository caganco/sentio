# BIST Trading System — Dependency Map

**Son güncelleme:** 2026-05-17  
**Değişiklikler:** D-058 (short interest L5), D-059 (L5→VERDA cut)  
**⚠️ Proje büyüdükçe bu dosyayı güncelle**

---

## Core Signal Engine

**src/signals/engine.py** (entry point — `compute_signal()`)
```
engine.py
├── src/signals/thresholds.py ⚠️ CRITICAL
│   └── MASTER_WEIGHTS, SIGNAL_THRESHOLDS, ALL constants
├── src/signals/layers/
│   ├── technical_layer.py → score_technical()
│   ├── macro_layer.py → score_macro()
│   ├── risk_layer.py → score_risk()
│   ├── kap_layer.py → score_kap()
│   ├── sentiment_layer.py → score_sentiment()
│   └── smart_money_layer.py → SmartMoneyLayer()
└── src/signals/models.py
    ├── LayerScore (0-100 score + weight)
    ├── SignalResult (final signal + audit trail)
    └── FinalSignal (BUY-STRONG/BUY-WEAK/HOLD/SELL-WEAK/SELL-STRONG)
```

**Formula:** `composite = Σ(score_i × weight_i) / Σ(weight_i)`

---

## Portfolio Management (NEW)

**src/portfolio/monitor.py** (stop-loss warnings)
```
monitor.py
├── check_stop_loss_approach(symbol, price, entry) → PositionAlert
├── format_stop_approach_alert(alert) → str
├── check_portfolio_alerts(positions, prices) → list[PositionAlert]
└── src/signals/thresholds.py
    ├── EXIT_STOP_LOSS = 0.92
    ├── EXIT_PROFIT_TARGET = 1.20
    └── STOP_APPROACH_BUFFER = 0.03
```

---

## Backtest Framework

**src/backtest/engine.py** (simulation engine)
```
engine.py
├── src/signals/engine.py → compute_signal() / compute_batch()
├── src/signals/thresholds.py
│   ├── MASTER_WEIGHTS (layer weighting)
│   ├── SIGNAL_THRESHOLDS (BUY/SELL boundaries)
│   └── EXIT_STOP_LOSS, EXIT_PROFIT_TARGET
├── src/backtest/data_loader.py
│   ├── build_technical_data(df, as_of) → dict
│   └── build_macro_data(macro_ts, as_of) → dict
└── src/backtest/metrics.py
    ├── calculate_win_rate()
    ├── calculate_sharpe()
    └── calculate_alpha()
```

---

## Local Macro Signals (Singleton)

**src/signals/local_macro_signals.py** (LocalMacroSignals)
```
LocalMacroSignals() [singleton]
├── LocalMacroSignals._instance (must be ONE)
├── LocalMacroSignals._reset() (test helper only)
├── TCMBClient (TCMB policy rate)
├── CDSClient (CDS spreads)
└── BistForeignOwnershipClient (foreign flow)
```

**⚠️ CONSTRAINT:** Don't break singleton pattern. No duplicate instantiation.

---

## L5 Smart Money Layer — Dependency Ayrımı (D-059)

### L5 Core — VERDA BAĞIMSIZ ✅ (D-059 ile unblocked)

```
smart_money_layer.py [CORE]
├── IsYatirimScreenerConnector
│   └── DOĞRUDAN endpoint (NO VERDA proxy)
│       https://www.isyatirim.com.tr/...getScreenerDataNEW
│       Kriter 40: Yabancı Oranı (%)
│       Kriter 44: 1 Haftalık Değişim (bps)
└── BISTDataStoreConnector (D-058 — YENİ)
    └── DOĞRUDAN endpoint (NO VERDA)
        https://datastore.borsaistanbul.com/
        Format: Haftalık CSV, public, lisanssız
```

**Composite (D-058 sonrası):**
```python
l5_score = L5_FOREIGN_WEIGHT(0.70) × foreign_ratio_score
         + L5_SHORT_INT_WEIGHT(0.30) × short_interest_score
```

**L5 dış weight:** `MASTER_WEIGHTS["smart"] = 0.20` (değişmez)

### L5 Extended — VERDA BLOCKER ⏸️ (kasıtlı bekleme)

```
smart_money_layer.py [EXTENDED — ayrı branch]
├── VIOPConnector      → VERDA zorunlu → SPEC_VIOP_SIGNAL_1 blocker
└── SentimentFeed      → VERDA zorunlu → sentiment layer blocker
```

**⚠️ NOT:** SPEC_VIOP_SIGNAL_1.md silinmez. VIOP + Sentiment VERDA bekliyor.
Bu sadece L5 core'un unblock edilmesidir.

### L3 KAP ↔ L5 Short Interest — Çakışma Kararı (D-058)

```
L3 KAP (kap_layer.py)
└── Event-driven: SPK short bildirimleri (≥%0.5), finansallar, özel durum

L5 Short Interest (BISTDataStoreConnector)
└── Pozisyonel: aggregate toplam short oranı (% free float), haftalık

KARAR: Tamamlayıcı sinyaller — overlap YOK
GUARD: Kovaryans dampening (×0.6) — aynı haftada L3 KAP short event
       VE L5 short_ratio > SHORT_INTEREST_HIGH eşiği ise uygula
       (Sabit: L5_KAP_OVERLAP_DAMP = 0.6 — thresholds.py'de)
```

---

## VERDA Dependency Haritası (D-059 Sonrası)

```
╔══════════════════════════════════════════════════════════╗
║  VERDA-BAĞIMSIZ MODÜLLER                                 ║
║  ✅ L5 Core (IsYatirim + BIST DataStore)                  ║
║  ✅ L1 Technical                                          ║
║  ✅ L2 Macro (LocalMacroSignals singleton)                ║
║  ✅ L3 KAP                                                ║
║  ✅ L4 Risk                                               ║
╠══════════════════════════════════════════════════════════╣
║  VERDA-BAĞIMLI MODÜLLER (kasıtlı blocker)                ║
║  ⏸️  VIOP Connector → SPEC_VIOP_SIGNAL_1 bekliyor         ║
║  ⏸️  Sentiment Feed → sentiment layer blocker             ║
╚══════════════════════════════════════════════════════════╝
```

**Silinen edge:** `L5 → VERDA` ❌  
**Korunan edge:** `VIOP_SIGNAL → VERDA` ✅, `SENTIMENT → VERDA` ✅

---

## D-052 Phase 4.5 Unblock Durumu

```
ÖNCEKI (D-059 öncesi):
  D052_PHASE_45: blocked_by = [L5b]   ← L5b VERDA bekliyordu

SONRASI (D-059 ile):
  D052_PHASE_45: blocked_by = []      ← L5 core hazır, başlayabilir
  L5b (VIOP+Sentiment): parallel branch, kendi timeline'ında devam
```

---

## Test Architecture

**tests/test_architecture.py** (design invariants)
```
Test Design Principles:
├── test_thresholds_file_is_single_source()
│   └── No hardcoded thresholds in engine.py
├── test_no_hardcoded_thresholds_in_engine()
│   └── No weight values (0.20, 0.35, 0.15, 0.05) outside thresholds.py
├── test_weight_sum_valid()
│   └── MASTER_WEIGHTS sum ∈ [0.85, 1.05]
├── test_singleton_not_duplicated()
│   └── LocalMacroSignals returns same instance
├── test_singleton_reset_works()
│   └── _reset() clears singleton for tests
└── test_l5_no_verda_dependency()  ← YENİ (D-059)
    └── L5 core dosyalarında "verda" string yok
```

**tests/test_signal_alert.py** (stop-loss warnings)
```
Stop-Loss Detection:
├── test_stop_approach_triggered_within_buffer()
├── test_stop_approach_not_triggered_far_from_stop()
├── test_stop_approach_at_exact_stop()
├── test_stop_approach_below_stop()
├── test_format_approaching_alert()
├── test_format_no_alert_when_not_approaching()
└── test_check_portfolio_mixed_alerts()
```

**tests/test_short_interest.py** (D-058 — YENİ)
```
Short Interest Signal:
├── test_short_interest_score_inverted()
├── test_short_interest_score_clip()
├── test_short_interest_stale_neutral()
├── test_kap_overlap_dampening_triggered()
├── test_kap_overlap_dampening_not_triggered()
├── test_l5_internal_weights_sum_to_one()
├── test_master_weights_unchanged()
└── test_bist_datastore_csv_parse()
```

---

## Test Tier Strategy

| Tier | Kapsam | Testler | Süre | Ne Zaman |
|------|--------|---------|------|----------|
| **Tier 1** — Architecture | Design invariants | `tests/test_architecture.py` (6 test) | ~1 sn | Her bootstrap |
| **Tier 2** — Integration | Signal flow + Portfolio | `tests/test_signal_alert.py` (7) + `tests/test_backtest.py` (22) | ~2 sn | Her bootstrap |
| **Tier 3** — Full Regression | Tüm test suite | `tests/` (657 → 666 hedef) | ~40 sn | Commit öncesi, haftalık |

**Tier 1 test sayısı 5 → 6 oldu** (test_l5_no_verda_dependency eklendi).

**Daily Bootstrap komutu (Tier 1+2):**
```powershell
python -m pytest tests/test_architecture.py tests/test_signal_alert.py tests/test_backtest.py -v --tb=no 2>&1 | Select-String "passed"
# Output: == 35 passed in ~2s ==  (önceki: 34)
```

---

## Critical Constraints

### ❌ YAPMA

| Yasak | Neden | Sonuç |
|-------|-------|-------|
| thresholds.py dışında hardcoded sabit | Single source of truth principle | Inconsistency, hard to test |
| MASTER_WEIGHTS toplamı [0.85, 1.05] dışı | Composite score bias | Signal threshold boundaries shift |
| LocalMacroSignals duplicate instance | Singleton pattern | YAML fallback loaded multiple times |
| Engine.py'de 0.20, 0.35, 72.0 vb. | Architecture safety (test catches this) | test_architecture.py fails |
| L5 core'da VERDA referansı | D-059 kararı | test_l5_no_verda_dependency() fails |
| SPEC_VIOP_SIGNAL_1.md'i silme | VIOP blocker kasıtlı | VIOP/Sentiment pipeline bozulur |

### ✅ YAPMA

| Gerekli | Neden |
|--------|-------|
| Her change sonrası `pytest tests/ -q` | Regression detection |
| Architecture checks geçme | Design principles enforced |
| thresholds.py'i CLAUDE.md "first read"'e ekle | Builder session'ı doğru başlar |
| Memory dokumentasyonu güncelle | Context preservation across sessions |

---

## Current System Status

### Test Suite
- **Total:** 657 passing + 8 (D-058 short interest) + 1 (D-059 arch test) = **666 hedef**
- **Tier 1:** 6 test (5 + test_l5_no_verda_dependency)
- **Skip:** 1 (unchanged)
- **Regression:** ✅ Zero (hedef)

### Layers (7-layer stack)

| Layer | Ağırlık | Durum | Veri Kaynağı |
|---|---|---|---|
| L1: Technical | 20% | ✅ | Market data |
| L2: Macro | 35% | ✅ | LocalMacroSignals (TCMB, CDS, foreign flow) |
| L3: Risk Management | 5% | ✅ | — |
| L4: KAP Events | 15% | ✅ | KAP API |
| L5: Smart Money CORE | 0.07 (ramp) → 0.10×conf (Phase 4.5) | 🟡 Building | IsYatirim(0.70) + BIST DataStore(0.30) |
| L5: Smart Money EXT | — | ⏸️ Blocked | VIOP + Sentiment (VERDA blocker) |
| L6: Sentiment | 5% | ⏸️ Pending | VERDA blocker |
| L7: Signal Engine | composite | ✅ | — |

### New Constants (D-058 — thresholds.py'e eklenecek)

```python
L5_FOREIGN_WEIGHT    = 0.70   # L5 iç ağırlık: foreign ratio
L5_SHORT_INT_WEIGHT  = 0.30   # L5 iç ağırlık: short interest
SHORT_INTEREST_HIGH  = 15.0   # % free float — yüksek crowding eşiği
SHORT_INTEREST_STALE = 10     # gün — stale threshold
L5_KAP_OVERLAP_DAMP  = 0.6   # L3/L5 short kovaryans dampening
ISYATIRIM_SCREENER_URL = "https://www.isyatirim.com.tr/..."  # D-059
```

### Exit Mechanisms
- Stop-loss: -8% (entry × 0.92) ✅ Locked
- Profit-target: +20% (entry × 1.20) ✅ Locked
- Trailing stop: ⏸️ SUSPENDED
- Circuit breaker: -15% portfolio drawdown ✅ Active

---

## Decision Log

### D-058: Short Interest → L5 Sub-Signal
- **Status:** 📋 SPEC READY (SPEC_L5_SHORT_INTEREST_1.md)
- **Karar:** L5 iç ağırlık: foreign(0.70) + short(0.30); dış L5: 0.07 (ramp) → 0.10×conf (Phase 4.5) - User bu satırdaki son parametreleri elle değiştirdi*
- **L3 çakışma:** Tamamlayıcı (event vs aggregate); kovaryans dampening guard eklendi
- **Veri:** BIST DataStore, public, lisanssız

### D-059: L5 → VERDA Dependency Cut
- **Status:** 📋 SPEC READY (SPEC_SIGNAL_CONVICTION_1.md)
- **Karar:** IsYatirimConnector doğrudan endpoint; VERDA parametresi kaldırıldı
- **Korunan:** SPEC_VIOP_SIGNAL_1.md, VIOP + Sentiment VERDA blocker
- **Unblock:** D-052 Phase 4.5 L5b beklemeksizin başlayabilir

### D-021: Exit Mechanisms Optimization
- **Status:** ⏸️ SUSPENDED
- **Reasoning:** Trailing stop too aggressive (0% vs 40% win rate with fixed exits)

### L5 Smart Money (Real Data)
- **Status:** 🟠 IN PROGRESS (D-058/D-059 ile core pipeline oluşuyor)
- **Blocker (kalan):** VIOP/Sentiment → VERDA bağımlı (kasıtlı)

### AKSEN Position
- **Status:** 🟡 REDUCE 30% PENDING
- **Trigger:** Macro stress (CDS >350, USDTRY spike)

---

## Integration Checklist

- [ ] New SPEC added? Update affected files section
- [ ] Threshold changed? Update MASTER_WEIGHTS or SIGNAL_THRESHOLDS here + run pytest
- [ ] New layer added? Register in engine.py + update composite formula
- [ ] Portfolio monitor call added? Verify import from src.portfolio.monitor
- [ ] Tests added? Mark with `pytest.mark.baseline` if permanent
- [ ] Memory updated? Add to memory/MEMORY.md index
- [ ] L5 değişikliği? → VERDA check: `test_l5_no_verda_dependency()` geçmeli

---

## First-Read Files (Session Bootstrap)

1. **[src/signals/thresholds.py](../src/signals/thresholds.py)** — All constants, single source of truth
2. **[src/signals/engine.py](../src/signals/engine.py)** — Signal composition, NO hardcoded values
3. **[src/portfolio/monitor.py](../src/portfolio/monitor.py)** — Stop-loss warnings
4. **[CLAUDE.md](../CLAUDE.md)** — Architecture safety rules (MANDATORY)

---

**Last verified:** 2026-05-17 (D-058 + D-059 SPEC ready; Builder implement bekliyor)

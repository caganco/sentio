# KAP Layer Feature Guide

**Son güncelleme:** 26 Mayıs 2026
**Faz durumu:** Faz 1 ✅ (regex, D-158) / Faz 2 🔜 (LLM, ~Eylül-Kasım 2026)

---

## Ne Yapar

KAP (Kamuyu Aydınlatma Platformu) açıklamalarını L3 sinyal skoruna dönüştürür.

**Faz 1 (D-158, mevcut):** `finansal_rapor` kategorisi için KAP metninden net kâr /
hasılat / FAVÖK değerleri regex ile çekilir; önceki dönemle karşılaştırılır;
normalize edilmiş sürpriz skoru üretilir.

**Diğer kategoriler** (temettu, sermaye_artirimi, vb.) sabit impact tablosundan
(`KAP_CATEGORY_IMPACT`) doğrudan işlenir.

---

## Mimari

```
score_kap(symbol, kap_events, as_of_date)
  └─ finansal_rapor eventi?
       ├─ kap_text mevcut? → parse_earnings_surprise(kap_text)
       │     ├─ confidence > 0 → impact = score × KAP_EARNINGS_IMPACT_SCALE (±40)
       │     └─ confidence = 0 → fallback: KAP_CATEGORY_IMPACT["finansal_rapor"] = 0.0
       └─ kap_text yok → fallback: 0.0
  └─ diğer kategoriler → KAP_CATEGORY_IMPACT.get(category, 0.0)

kap_earnings_parser.py::parse_earnings_surprise(kap_text)
  └─ Regex: net_kar / hasilat / favok + önceki dönem değeri
  └─ _parse_number(): Türkçe format (nokta=binlik, virgül=ondalık)
  └─ _normalize_delta(): ±%5 neutral band, ±%20 strong threshold
  └─ EarningsSurprise(score, confidence, metrics_found, parse_method)
```

**Backtest notu:** `data_loader.py` KAP event'lerine `kap_text` eklemez →
backtest'te `finansal_rapor` her zaman fallback (0.0 impact) verir.
Tarihsel KAP text verisi gerektiren gerçek backtest Faz 2 kapsamındadır.

---

## Kritik Sabitler (`src/signals/thresholds.py`)

| Sabit | Değer | Açıklama |
|-------|-------|---------|
| `KAP_EARNINGS_NEUTRAL_BAND` | 0.05 | ±%5 delta → score=0.0 (beklenti içinde) |
| `KAP_EARNINGS_STRONG_THRESHOLD` | 0.20 | ±%20 delta → ±1.0 (güçlü sürpriz) |
| `KAP_EARNINGS_IMPACT_SCALE` | 40.0 | score×scale → L3 impact (−40..+40) |
| `KAP_CATEGORY_IMPACT["finansal_rapor"]` | 0.0 | DEPRECATED D-158; Faz 2'de silinecek |
| `KAP_BASE_SCORE` | 50.0 | L3 başlangıç skoru (neutral) |
| `KAP_EVENT_WINDOW_DAYS` | 3 | event penceresi (gün) |

### Score-Impact Örnekleri

| Delta | Normalize | Impact (×40) | Final Score |
|-------|-----------|-------------|-------------|
| +50% | +1.0 | +40 | 90.0 |
| +12% | +0.56 | +22.3 | 72.3 |
| +5% | 0.0 | 0.0 | 50.0 |
| -15% | -0.56 | -22.3 | 27.7 |
| -30% | -1.0 | -40 | 10.0 |

---

## Neye Dokunma

- `KAP_EARNINGS_NEUTRAL_BAND` / `KAP_EARNINGS_STRONG_THRESHOLD` değerlerini
  `thresholds.py` dışında tanımlama (CLAUDE.md kuralı)
- `finansal_rapor` satırını `KAP_CATEGORY_IMPACT`'tan silme — Faz 2 kapsamı
- `kap_layer.py` for-loop'una LLM çağrısı ekleme (Faz 1 kısıtı)
- `parse_earnings_surprise()` içine fallback olmayan exception propagation ekleme
- `score_kap()` imzasını değiştirme (`calculator.py` dokunulmaz)

---

## Test Coverage

| Dosya | Test Sınıfı | Kapsam |
|-------|------------|--------|
| `tests/test_kap_earnings_parser.py` | `TestParseEarningsSurprise` | Parser birim (8 test) |
| `tests/test_kap_layer.py` | `TestKapLayerFinansalRapor` | L3 entegrasyon (4 test) |
| `tests/test_engine.py` | `TestKapLayer` | Diğer kategoriler (8 test) |

---

## Sıradaki Adım

**Faz 2 (D-159~D-165, ~Eylül-Kasım 2026):** İki aşamalı filtre:
1. Stage 1 (regex) → yüksek güven (confidence ≥ 0.75) → doğrudan kullan
2. Stage 1 düşük güven (confidence < 0.75) → Stage 2 (LLM) çağır
3. `KAP_CATEGORY_IMPACT["finansal_rapor"]` deprecated satırı silinecek
4. Backtest için tarihsel KAP text verisi pipeline'ı eklenmesi gerekiyor

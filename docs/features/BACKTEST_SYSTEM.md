# Feature Guide: Backtest System
**Son güncelleme:** 25 Mayıs 2026 — D-149e
**Durum:** Faz 1 tamamlandı ✅ | Faz 2 bekliyor (D-150)
**Sorumlu specler:** D-149a/b/c/d/e

---

## Ne Yapar

BIST OS'un sinyal engine'ini geçmiş veriler üzerinde simüle eder.
Production engine ile **aynı** composite hesabını yapar (`src/signals/calculator.py` paylaşımlı modül).

---

## Mimari (D-149 sonrası)

```
src/signals/thresholds.py   ← tek kaynak (tüm sabitler)
        ↑
src/signals/calculator.py   ← paylaşımlı pure functions
    ↑               ↑
src/signals/engine.py   src/backtest/engine.py
(production)            (backtest)
```

**Kritik:** `calculator.py` olmadan backtest ve production farklı composite hesaplar.
D-149 öncesi backtest'te L3/L4/L5 daima 50.0 (neutral) hardcodeddi — tüm eski raporlar bu nedenle RETRACT işaretlendi.

---

## Şu An Çalışan

| Özellik | Durum | Notlar |
|---------|-------|--------|
| L1 Technical composite | ✅ | Gerçek sinyal |
| L2 Macro composite | ✅ | Gerçek sinyal |
| L6 Risk/Kelly composite | ✅ | Gerçek sinyal |
| L3 KAP composite | ⚠️ 50.0 stub | Tarihsel veri yok — Faz 2 |
| L4 Sentiment composite | ⚠️ 50.0 stub | Tarihsel veri yok — Faz 2 |
| L5 Smart Money composite | ⚠️ 50.0 stub | Tarihsel veri yok — Faz 2 |
| Hardcoded değerler | ✅ Temizlendi | thresholds.py'den okunuyor |
| RETRACT raporları | ✅ İşaretlendi | reports/D-038..D-050 |

---

## Nasıl Çalıştırılır

```bash
# Backtest çalıştır
python src/backtest/engine.py

# Parity testi
python -m pytest tests/test_backtest_production_parity.py -v

# Eski raporları RETRACT işaretle (idempotent)
python scripts/retract_old_backtest_reports.py

# Drift raporu: data/analytics/drift_report_<tarih>.json
# D-149b kodu daily_update.py içinde otomatik üretir — ayrı script yok
```

---

## Sonuçları Yorumlarken Dikkat

**Şu an Sharpe rakamlarına tam güvenme:**
- L3/L4/L5 = 50.0 (neutral) → backtest sinyalin %52'sini görmüyor
- Gerçek production sinyali backtest'ten daha güçlü olabilir
- Faz 2 (D-150) tamamlanana kadar Sharpe rakamları conservative estimate

**Parity testi:** `TestBacktestNeutralStubMath` maksimum 26 puan divergence olabileceğini kanıtlıyor. Güçlü KAP haberi + bullish sentiment gününde production BUY-STRONG, backtest HOLD üretebilir.

---

## Neye Dokunma

| Yasak | Neden |
|-------|-------|
| 50.0 stub'ı kaldırma (Faz 2 olmadan) | KAP/L4/L5 tarihsel veri pipeline yok — kaldırırsan backtest anlamsızlaşır |
| `calculator.py`'e engine import ekleme | K-08 ihlali — circular dependency |
| `backtest/engine.py`'e hardcode ekleme | `TestBacktestEngineHardcodedValues` CI'da yakalar |
| RETRACT raporları güncelleme | İçerik kasıtlı donduruldu — sadece header var |

---

## Sıradaki Adım: Faz 2 (D-150)

**Bloklanıyor:** CB-014 (Purged K-Fold) — Architect SPEC şart, Builder'a direkt verme.

Faz 2 kapsamı:
1. KAP tarihsel veri backfill (point-in-time membership)
2. L4 Sentiment tarihsel pipeline
3. L5 Smart Money tarihsel pipeline
4. 50.0 stub kaldırma — gerçek 6-layer backtest
5. Purged K-Fold (k=5, purge=10g, embargo=5g)
6. DSR + PBO hesaplama

**Faz 2 için Architect specini yazmadan önce:** tarihsel KAP veri kaynağını netleştir (KAP API ~2020'den mi, yoksa daha kısa mı?).

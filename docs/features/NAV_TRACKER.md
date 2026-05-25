# Feature Guide: NAV Discount Tracker
**Son güncelleme:** 25 Mayıs 2026 — D-143
**Durum:** Faz 1 production ✅ (KCHOL pilot) | Faz 2 SAHOL/AGHOL bekliyor
**Sorumlu direktifler:** D-143

---

## Ne Yapar

Holding şirketlerinin piyasa değeri ile iştiraklarının toplam değeri arasındaki iskontoyu takip eder.
İskonto tarihsel ortalamadan anlamlı sapma gösterdiğinde sinyal üretir.

**Akademik temel:** Pontiff (1995) — %20 iskontolu fonlar 12 ayda +%6 ek getiri.

---

## Mimari

```
config/holdings.yaml          ← stake yüzdeleri (gitignored, local)
    ↓
NAVCalculator.compute_tier1_nav("KCHOL")
    ↓ yfinance market_cap × stake%
NAVZScoreTracker.update(nav_result)
    ↓ 252d rolling z-score
data/analytics/nav_history.parquet   ← append-only
    ↓
daily_report.md               ← NAV bölümü + ALERT satırları
```

---

## Sinyal Zonları (thresholds.py)

| Z-Skor | Sinyal | Anlam |
|--------|--------|-------|
| > +2.0 | BUY | İskonto tarihsel zirvede |
| +1.0 ile +2.0 | BUY-LEAN | İskonto yüksek |
| -1.0 ile +1.0 | HOLD | Normal bant |
| -1.0 ile -2.0 | TRIM | İskonto daralıyor |
| < -2.0 | AVOID | İskonto tarihsel düşükte |
| < 60 gün veri | COLLECTING | Yeterli tarih yok |

---

## Kritik Eşikler (CB-012 uyarısı)

| Eşik | Değer | Aksiyon |
|------|-------|---------|
| `NAV_DISCOUNT_KADEME1_KAPATMA` | %30 | İskonto < %30 → trim/kapatma sinyali |
| `NAV_DISCOUNT_KADEME2_ALIM` | %45 | İskonto > %45 → ek alım sinyali |

**CB-012 uyarısı:** Z-skor "tarihsel ortalamaya dönüş" varsayar. DOHOL örneğinde yapısal iskonto %50'ye yerleşti. Türkiye idiosyncratic risk dönemlerinde tarihsel mean kayabilir — CDS > 400 bps ise uzun pencere (5Y) kullan.

---

## Mevcut Portföy Durumu

> ⚠️ **Snapshot** — Bu bölüm elle güncellenir, hızla bayatlar.
> Güncel değer için `data/analytics/nav_history.parquet`'e bak.

**KCHOL (25 May 2026):** İskonto ~%41 (z ≈ +1.5, BUY-LEAN zonu) — HOLD korunuyor.
Kademe-2 tetikleyici: %45 — şu an 4 puan uzakta.

---

## Pilot Universe (Genişleme Planı)

| Ticker | Skor | Faz |
|--------|------|-----|
| KCHOL | 5/5 | ✅ Faz 1 aktif |
| SAHOL | 5/5 | Faz 2 |
| AGHOL | 4/5 | Faz 2 sonu |
| KOZAL | 1/5 | ❌ Strateji dışı |
| DOHOL | 2/5 | ❌ Yapısal iskonto |

---

## Neye Dokunma

| Yasak | Neden |
|-------|-------|
| `config/holdings.yaml` commit etme | gitignored — stake verileri özel |
| `nav_history.parquet` silme | Biriken z-skor geçmişi — geri getirilmez |
| `nav_calculator.py`'den engine import | K-08 ihlali |
| Auto-execute sinyal | Manuel onay zorunlu (DEC-023 benzeri prensip) |

---

## Sıradaki Adım

Faz 2: SAHOL + AGHOL stake listesi `config/holdings.yaml`'a ekle → NAVCalculator parametreli çalıştır → Faz 1 ile aynı pipeline.

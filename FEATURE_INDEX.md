# FEATURE INDEX — BIST OS
**Son güncelleme:** 25 Mayıs 2026
**Protokol:** Her Orchestrator session başında bu dosya okunur.
**Kural:** Yeni major feature eklenince bu dosyaya ve `docs/features/` dizinine eklenir.

---

## ⚠️ OKUMA ZORUNLULUĞU

Bu dosya `OS_STATE.md` + `CRITIC_BACKLOG.md` ile birlikte session başlangıç protokolünün parçasıdır.
Büyük özellik direktifi vermeden önce ilgili guide okunur.

---

## Feature Tablosu

| Feature | Guide | Durum | Kritik Uyarı |
|---------|-------|-------|--------------|
| Backtest System | `docs/features/BACKTEST_SYSTEM.md` | Faz 1 ✅ / Faz 2 bekliyor | 50.0 stub intentional — kaldırma |
| IC Framework | `docs/features/IC_FRAMEWORK.md` | Faz 1+2 ✅ / Faz 3 ~Temmuz 2026 | ic_history.parquet silme |
| NAV Tracker | `docs/features/NAV_TRACKER.md` | Faz 1 ✅ (KCHOL) / Faz 2 bekliyor | CB-012 rejim-shift riski |
| Risk Layer | `docs/features/RISK_LAYER.md` | ADV+EV aktif ✅ / Vol gözlem modu | Vol_scalar henüz pasif |
| Signal Engine | — | Production ✅ | MASTER_WEIGHTS değiştirme |
| L1 ADX Regime | — | D-155 ✅ / ADX feed eksik ⚠️ | adx=None → transition mod (basit ort.); D-156: ADX fetch ekle |
| HMM Regime | — | ENABLE=False | AG-001 ~Kasım 2026 |
| Foreign Flow | — | Multi-window ✅ | CB-011 CLOSED (D-144) |
| KAP Boost | — | Event-triggered ✅ | Boost constants test koruyor |

---

## Yeni Feature Ekleme Protokolü

Bir direktif şu kriterleri karşılıyorsa **guide zorunludur:**

1. Yeni `src/` modülü oluşturuluyor (özellikle `analytics/`, `risk/`, `backtest/`)
2. Mevcut davranışı kısıtlayan yeni eşik/sabit ekleniyor
3. "Neye dokunma" kuralı olan bir mimari karar içeriyor
4. Activation gate veya faz bağımlılığı var

**Guide formatı:** `docs/features/FEATURE_NAME.md`
Minimum bölümler: Ne Yapar / Mimari / Kritik Sabitler / Neye Dokunma / Sıradaki Adım

---

## Bekleyen Guide'lar (Yazılacak)

| Feature | Öncelik | Neden |
|---------|---------|-------|
| Signal Engine (tam) | Yüksek | MASTER_WEIGHTS, conviction validator detayı |
| HMM Regime | Orta | AG-001 öncesi hazır olmalı |
| Data Pipeline | Orta | 10 kaynak, fallback zincirleri karmaşık |
| Foreign Flow Parser | Düşük | QNB filter ve multi-window mantığı (D-144 tamamlandı, guide yok) |

---

## CI Enforcement (D-150 sonrası eklenecek)

`test_architecture.py`'e `TestFeatureGuideCoverage` eklenecek:
- `src/analytics/` altındaki her `.py` için `docs/features/` altında karşılık var mı?
- Yoksa → CI sarı uyarı (fail değil — guide yazımı blocking olmamalı)

---

## Session Başlangıç Protokolü (Güncellendi)

```
1. CRITIC_BACKLOG.md oku — ACTIVE FINDINGS özetle
2. OS_STATE.md oku — sistem durumunu kavra
3. FEATURE_INDEX.md oku — hangi feature'lar aktif, faz durumu nedir
4. AG-001 status kontrol
5. Açık direktif var mı kontrol
6. Devir notu var mı kontrol
```

---

*Bu dosya gitignored değil — repo'da yaşar, nesilden nesile otomatik taşınır.*
*Her major direktif kapanışında güncelleme zorunludur.*

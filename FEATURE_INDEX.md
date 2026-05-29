# FEATURE INDEX — BIST OS
**Son güncelleme:** 28 Mayıs 2026 — Session #7 kapanış
**Protokol:** Her Orchestrator session başında bu dosya okunur.
**Kural:** Yeni major feature eklenince bu dosyaya ve docs/features/ dizinine eklenir.

---

## OKUMA ZORUNLULUĞU

Bu dosya OS_STATE.md + CRITIC_BACKLOG.md ile birlikte session başlangıç protokolünün parçasıdır.
Büyük özellik direktifi vermeden önce ilgili guide okunur.

---

## Feature Tablosu

| Feature | Guide | Durum | Kritik Uyarı |
|---------|-------|-------|--------------|
| Backtest System | docs/features/BACKTEST_SYSTEM.md | Faz 1 ✅ / Faz 2 bekliyor | 50.0 stub intentional — kaldırma; CPCV run Kasım 2026 |
| IC Framework | docs/features/IC_FRAMEWORK.md | Faz 1+2 ✅ / Faz 3 ~Temmuz 2026 | ic_history.parquet silme |
| NAV Tracker | docs/features/NAV_TRACKER.md | Faz 1 ✅ (KCHOL) / Faz 2 bekliyor | CB-012 rejim-shift riski |
| Risk Layer | docs/features/RISK_LAYER.md | ADV+EV aktif ✅ / Vol gözlem modu | L6 composite'ten çıktı (D-154); sizing tarafı korundu |
| Signal Engine | — | Production ✅ | MASTER_WEIGHTS 5 katman (L6 çıktı); değiştirme |
| L1 ADX Regime | — | D-155 ✅ / D-156 ✅ | Wilder-14 ADX aktif; RSI TREND nötrleşme D-164 ✅ |
| HMM Regime | — | ENABLE=False | AG-001 ~Kasım 2026 |
| Foreign Flow | — | Multi-window ✅ | CB-011 CLOSED (D-144) |
| KAP Earnings Parser | docs/features/KAP_LAYER.md | Faz 1 ✅ (regex D-158) / Faz 2 ~Eylül 2026 (LLM) | finansal_rapor: kap_text yok → 0.0 fallback; backtest'te hep fallback |
| KAP Boost | — | Event-triggered ✅ | Boost constants test koruyor |
| Statistical Validation | docs/features/BACKTEST_SYSTEM.md Faz 2 | D-150a-e ✅ | DSR/PBO/CPCV framework hazır; gerçek run Kasım 2026 |
| BIST Trend Scalar | — | D-163 ✅ production | Backtest engine'e entegre değil (DEC-034); sadece live sizing |
| Macro Gate (Crisis-Only) | — | D-166 ✅ | BACKTEST_MACRO_MIN_SCORE kaldırıldı; sadece VIX>35/USDTRY>%3 |
| BIST Decoupling Bonus | — | D-167 ✅ | L2<50 AND BIST>MA50 → +8 puan düzeltme |
| Cloud Deployment | docs/ (setup_cloud.md) | D-152 ✅ aktif | GitHub Actions cron 18:30 IST; IC parquet git persist |

---

## Yeni Feature Ekleme Protokolü

Bir direktif şu kriterleri karşılıyorsa guide zorunludur:

1. Yeni src/ modülü oluşturuluyor (özellikle analytics/, risk/, backtest/)
2. Mevcut davranışı kısıtlayan yeni eşik/sabit ekleniyor
3. "Neye dokunma" kuralı olan mimari karar içeriyor
4. Activation gate veya faz bağımlılığı var

**Guide formatı:** docs/features/FEATURE_NAME.md
Minimum bölümler: Ne Yapar / Mimari / Kritik Sabitler / Neye Dokunma / Sıradaki Adım

---

## Bekleyen Guide'lar (Yazılacak)

| Feature | Öncelik | Neden |
|---------|---------|-------|
| Signal Engine (tam) | Yüksek | MASTER_WEIGHTS 5 katman, conviction validator, macro_mult detayı |
| HMM Regime | Orta | AG-001 öncesi hazır olmalı (~Kasım 2026) |
| Data Pipeline | Orta | 10 kaynak, fallback zincirleri karmaşık |
| BIST Trend Scalar | Orta | D-163 production'da; backtest divergence (DEC-034) belgelenmeli |
| Macro Gate | Orta | D-166 crisis-only mantığı belgelenmeli |
| Multi-LLM Jury | Düşük | Phase 6+ (Q1 2027+); ENABLE_MULTI_LLM=False default zorunlu |

---

## CI Enforcement (D-150 sonrası eklenecek)

test_architecture.py'e TestFeatureGuideCoverage eklenecek:
- FEATURE_INDEX.md'deki tüm guide linkleri gerçek dosyalara işaret etmeli (BLOCKING)
- Guide "—" olan satırlar skip (henüz yazılmamış)

---

## Session Başlangıç Protokolü

1. CRITIC_BACKLOG.md oku — ACTIVE FINDINGS özetle
2. OS_STATE.md oku — sistem durumunu kavra
3. FEATURE_INDEX.md oku — aktif feature'lar, faz durumu, neye dokunma
4. AG-001 status kontrol
5. Açık direktif var mı kontrol
6. Devir notu var mı kontrol

---

Bu dosya gitignored değil — repo'da yaşar, nesilden nesile otomatik taşınır.
Her major direktif kapanışında güncelleme zorunludur.

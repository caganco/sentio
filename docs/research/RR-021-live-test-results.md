# RR-021 — EVDS3 Canlı Test Sonuçları

**Test zamanı:** 2026-05-25 19:55 UTC  
**Tarih aralığı:** 20-04-2025 → 25-05-2026 (lookback 400 gün)  
**Base URL:** `https://evds3.tcmb.gov.tr/igmevdsms-dis/`  
**Auth header:** auth header = 'key' (HTTP 200 on TP.DK.USD.A)  
**Özet:** ✅ 14 aktif · ❌ 2 dead · ⚠️ 0 hata (toplam 16)

> Üretildi: `scripts/test_evds3_connection.py`. RR-021 §3 envanterini canlı API'ye karşı doğrular.

## Politika Faizi

| Durum | Seri Kodu | Açıklama | Frekans | Son Veri | Son Değer | Gözlem | Not |
|---|---|---|---|---|---|---|---|
| ✅ ACTIVE | `TP.APIFON4` | TCMB ağırlıklı ort. fonlama maliyeti (AOFM) | Günlük | 25-05-2026 | 40.00000000 | 274 |  |
| ✅ ACTIVE | `TP.API.REP.ORT.G1` | Repo ortalama oranı (gecelik) | Günlük | 2026-4 | 40.00000000 | 5 | aktiflik teyit edilmeli |
| ✅ ACTIVE | `TP.BISTTLREF.ORAN` | TLREF (TL gecelik referans faiz) — oran | Günlük | 22-05-2026 | 39.99510000 | 271 |  |
| ✅ ACTIVE | `TP.BISTTLREF.KAPANIS` | TLREF — kapanış variant | Günlük | 22-05-2026 | 5963.01990000 | 271 | community variant |
| ❌ DEAD | `TP.FAIZ.PYUVDL` | Eski TLREF kodu | — | — | — | 0 | HTTP 400 |

## Döviz

| Durum | Seri Kodu | Açıklama | Frekans | Son Veri | Son Değer | Gözlem | Not |
|---|---|---|---|---|---|---|---|
| ✅ ACTIVE | `TP.DK.USD.A` | USD/TRY Alış (gösterge) | Günlük | 25-05-2026 | 45.55320000 | 274 |  |
| ✅ ACTIVE | `TP.DK.USD.S` | USD/TRY Satış | Günlük | 25-05-2026 | 45.63530000 | 274 |  |
| ✅ ACTIVE | `TP.DK.EUR.A` | EUR/TRY Alış | Günlük | 25-05-2026 | 52.85990000 | 274 |  |
| ✅ ACTIVE | `TP.DK.EUR.S` | EUR/TRY Satış | Günlük | 25-05-2026 | 52.95520000 | 274 |  |
| ✅ ACTIVE | `TP.DK.USD.A.YTL` | USD alış — eski .YTL suffix variant | Günlük | 25-05-2026 | 45.55320000 | 274 | community variant |

## Enflasyon

| Durum | Seri Kodu | Açıklama | Frekans | Son Veri | Son Değer | Gözlem | Not |
|---|---|---|---|---|---|---|---|
| ✅ ACTIVE | `TP.FE.OKTG01` | TÜFE Genel (2003=100, TÜİK yeni seri) | Aylık | 2025-9 | 3367.22000000 | 9 |  |
| ✅ ACTIVE | `TP.FG.J0` | TÜFE alternatif kodu | Aylık | 2026-1 | 3683.83000000 | 10 | OKTG01 daha yaygın |
| ❌ DEAD | `TP.FG01` | Yİ-ÜFE | Aylık | — | — | 0 | HTTP 400 |
| ✅ ACTIVE | `TP.ENFBEK.PKA12ENF` | 12-ay ileri enflasyon beklentisi | Aylık | 2026-5 | 23.82000000 | 14 | nice-to-have |

## Borsa

| Durum | Seri Kodu | Açıklama | Frekans | Son Veri | Son Değer | Gözlem | Not |
|---|---|---|---|---|---|---|---|
| ✅ ACTIVE | `TP.MKNETHAR.M7` | BIST net işlem (genel) | Haftalık | 15-05-2026 | -284.62000000 | 56 | datagroups ile tam tanım doğrula |
| ✅ ACTIVE | `TP.MKNETHAR.M1` | Yabancı net işlem | Haftalık | 15-05-2026 | 44399.70000000 | 56 |  |

## Aksiyon Notları

**Dead seriler (kullanma / koddan çıkar):**
- `TP.FAIZ.PYUVDL` — HTTP 400
- `TP.FG01` — HTTP 400

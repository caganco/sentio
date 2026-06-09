# RR-Y1-011-D — Index Reconstitution Look-Ahead-Safe Olay Paneli

| Alan | Değer |
|------|-------|
| **ID** | RR-Y1-011-D |
| **Tür** | Panel inşası (Sinyal / ölçüm YOK) |
| **Tarih** | 2026-06-09 |
| **İlişkili RR** | RR-Y1-011, RR-Y1-011-B, RR-Y1-011-C |
| **Dayanak** | RR-Y1-011-C §3 (KAP PDF yapısı); RR-Y1-011-B §2 (efektif tarihler) |

---

## 1. Özet

- Hedef bildirim sayısı: 28
- Bulunan KAP bildirim ID sayısı: 28 / 28
- Toplam olay (IN+OUT+RESERVE hariç): 1003
- Temel tier (XU030/050/100) olay sayısı: 705

| Kontrol | Sonuç |
|---------|-------|
| Look-ahead-safe (ilan tarihi PIT) | ✅ EVET — KAP HTML saniye-hassasiyetli timestamp |
| Survivorship-clean | ✅ EVET — clean_universe delisted dahil |
| Tier etiketli | ✅ EVET — XU030/XU050/XU100 ayrı tablo |
| Veri penceresi tam coverage | ✅ 97.0% |

---

## 2. Bildirim Keşif Sonuçları

| Çeyrek | Efektif Tarih | Bildirim ID | İlan Tarihi | İlan→Efektif |
|--------|--------------|------------|------------|-------------|
| Q1-2019 | 2019-01-02 | 725991 | 2018-12-21 | 12 gün |
| Q1-2020 | 2020-01-02 | 803975 | 2019-12-17 | 16 gün |
| Q1-2021 | 2021-01-04 | 894142 | 2020-12-21 | 14 gün |
| Q1-2022 | 2022-01-03 | 984449 | 2021-12-17 | 17 gün |
| Q1-2023 | 2023-01-02 | 1088484 | 2022-12-19 | 14 gün |
| Q1-2024 | 2024-01-02 | 1228194 | 2023-12-22 | 11 gün |
| Q1-2025 | 2025-01-02 | 1367507 | 2024-12-20 | 13 gün |
| Q2-2019 | 2019-04-01 | 748393 | 2019-03-18 | 14 gün |
| Q2-2020 | 2020-04-01 | 830865 | 2020-03-19 | 13 gün |
| Q2-2021 | 2021-04-01 | 918267 | 2021-03-15 | 17 gün |
| Q2-2022 | 2022-04-01 | 1012073 | 2022-03-22 | 10 gün |
| Q2-2023 | 2023-04-03 | 1125624 | 2023-03-16 | 18 gün |
| Q2-2024 | 2024-04-01 | 1261193 | 2024-03-21 | 11 gün |
| Q2-2025 | 2025-04-02 | 1409989 | 2025-03-21 | 12 gün |
| Q3-2019 | 2019-07-01 | 769426 | 2019-06-21 | 10 gün |
| Q3-2020 | 2020-07-01 | 852123 | 2020-06-19 | 12 gün |
| Q3-2021 | 2021-07-01 | 943164 | 2021-06-18 | 13 gün |
| Q3-2022 | 2022-07-01 | 1038557 | 2022-06-21 | 10 gün |
| Q3-2023 | 2023-07-03 | 1159507 | 2023-06-16 | 17 gün |
| Q3-2024 | 2024-07-01 | 1299052 | 2024-06-13 | 18 gün |
| Q3-2025 | 2025-07-01 | 1450711 | 2025-06-20 | 11 gün |
| Q4-2019 | 2019-10-01 | 788219 | 2019-09-20 | 11 gün |
| Q4-2020 | 2020-10-01 | 875734 | 2020-09-18 | 13 gün |
| Q4-2021 | 2021-10-01 | 964181 | 2021-09-16 | 15 gün |
| Q4-2022 | 2022-10-03 | 1064575 | 2022-09-21 | 12 gün |
| Q4-2023 | 2023-10-02 | 1196746 | 2023-09-21 | 11 gün |
| Q4-2024 | 2024-10-01 | 1336462 | 2024-09-20 | 11 gün |
| Q4-2025 | 2025-10-01 | 1489616 | 2025-09-12 | 19 gün |

---

## 3. Temiz-N Analizi (XU030/XU050/XU100)

### 3.1 Yön × Tier Kırılımı

| Tier | IN | OUT | Toplam |
|------|----|----|--------|
| XU030 | 25 | 25 | 50 |
> ✅ XU030 IN: N=25 ≥ 20 — Stage-0 adayı
> ✅ XU030 OUT: N=25 ≥ 20 — Stage-0 adayı
| XU050 | 84 | 84 | 168 |
> ✅ XU050 IN: N=84 ≥ 20 — Stage-0 adayı
> ✅ XU050 OUT: N=84 ≥ 20 — Stage-0 adayı
| XU100 | 243 | 244 | 487 |
> ✅ XU100 IN: N=243 ≥ 20 — Stage-0 adayı
> ✅ XU100 OUT: N=244 ≥ 20 — Stage-0 adayı

### 3.2 Yıl × Tier × Yön Kırılımı

direction        IN  OUT
year index_tier         
2018 XU030        1    1
     XU050        4    4
     XU100        5    5
2019 XU030        1    1
     XU050       12   12
     XU100       37   38
2020 XU030        4    4
     XU050       15   15
     XU100       21   21
2021 XU030        1    1
     XU050       13   13
     XU100       47   47
2022 XU030        4    4
     XU050       11   11
     XU100       37   37
2023 XU030        4    4
     XU050       12   12
     XU100       30   30
2024 XU030        6    6
     XU050       13   13
     XU100       41   41
2025 XU030        4    4
     XU050        4    4
     XU100       25   25

---

## 4. Veri Penceresi Kapsama

- Toplam olay: 1003
- Evren içinde: %99.6
- Ön-pencere OK (≥5 gün): %97.3
- Son-pencere OK (≥10 gün): %99.3
- Tam-pencere OK: %97.0

---

## 5. Ham-N → Temiz-N İndirgeme Gerekçesi

RR-Y1-011 ham-N: XU100=487, XU030=54 (clean_universe bist100/bist30 flag günlük diff).

İndirgeme kaynakları:
1. **IPO otomatik ekleme**: Yeni halka arz, çeyreklik değişiklik yerine anında eklenir.
   → Bu PDFler yalnızca 'Dönemsel Değişiklikler' → sadece planlı oturumlar.
2. **Acil çıkarma (delisting/birleşme)**: Dönemsel PDF'de yer almaz.
3. **Ara dönem serbest dolaşım ayarı**: Bu da bu PDFde yer almaz.
4. **Veri artefaktı**: Günlük flag bazındaki kısa süreli sıfırlanmalar burada görünmez.

> Bu panel = sadece planlı çeyreksel oturumlar (Dönemsel Değişiklikler PDFs).
> Ham-N'in ~4-5x daha düşük olması beklenir (RR-Y1-011-B §4.2 tahmini: ~140-224 XU100).

---

## 6. Stage-0 Ön-Değerlendirmesi

> Bu task Stage-0 AÇMAZ. Kararı Orchestrator + Çağan verir.

| Hücre (Tier×Yön) | Temiz-N | Durum |
|-----------------|---------|-------|
| XU030×IN | 25 | ✅ Stage-0 adayı (N≥20) |
| XU030×OUT | 25 | ✅ Stage-0 adayı (N≥20) |
| XU050×IN | 84 | ✅ Stage-0 adayı (N≥20) |
| XU050×OUT | 84 | ✅ Stage-0 adayı (N≥20) |
| XU100×IN | 243 | ✅ Stage-0 adayı (N≥20) |
| XU100×OUT | 244 | ✅ Stage-0 adayı (N≥20) |

---

## 7. Kapsam-Uyum Beyanı

Bu raporda sinyal / getiri / IC / NW-t / Sharpe / edge hükmü üretilmemiştir.
Committed pipeline dokunulmamıştır.

Çıktı artefaktlar:
- `data/snapshots/index_recon_events_2019_2025.parquet`
- `data/bist_datastore_archive/kap_index_probe/recon_cache/` (gitignored)
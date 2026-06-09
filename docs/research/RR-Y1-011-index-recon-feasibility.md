# RR-Y1-011 — Index Reconstitution Demand-Shock: Fizibilite Probe

| Alan | Değer |
|------|-------|
| **ID** | RR-Y1-011 |
| **Tür** | Yalnızca-fizibilite (Stage-0 DEĞİL, ölçüm YOK) |
| **Tarih** | 2026-06-09 |
| **Kapsam** | XU030 / XU100 rekonstitüsyon olay-paneli veri-zemini |
| **Bağlı CB-SPEC** | — (henüz yok; Stage-0 açılırsa bağlanır) |
| **Status** | ⏳ Fizibilite tamamlandı — Stage-0 kararı bekliyor |

---

## 1. Üç Kesin Sorunun Yanıtı

| Soru | Yanıt |
|------|-------|
| **(a) Panel kurulabilir mi?** | **KOŞULLU EVET** — efektif-tarih paneli kurulabilir; look-ahead-safe panel için ilan-tarihi gerekli (§4) |
| **(b) N kaç?** | **XU100: 487 · XU030: 54** (ham; §3); planlı-çeyreklik-rekon alt-kümesi daha düşük (§3.2) |
| **(c) Look-ahead-safe mi?** | **HENÜZ HAYIR** — ilan-tarihi kaynağı doğrulanmadı (§4); bu fizibilite-engeli §5'te tanımlanıyor |

---

## 2. Veri Kaynağı Envanteri

### 2a. clean_universe PIT Membership Flags

`data/clean_universe/adjusted_prices_2019_2026.parquet` içinde `bist100` ve `bist30`
sütunları bulunmaktadır. Bu sütunlar **point-in-time efektif üyelik** bayraklarıdır
(0/1 veya NaN); her gün için hangi sembollerin endekste olduğunu gösterir.

- **Kapsam:** 2019-01-02 .. 2026-05-26 (günlük)
- **Sembol evreni:** 681 sembol (delisted dahil, survivorship-clean)
- **Sütun kalitesi:** `bist100` ve `bist30` ikisi de mevcut ve eksiksiz

### 2b. DataStore Katalog 3184 (index_components)

| Alan | Durum |
|------|-------|
| **Katalog ID** | 3184 (thresholds.py'de `DATASTORE_PRODUCT_INDEX_COMPONENTS`) |
| **Beklenen dosya formatı** | `exsrk{YYYY}.zip` (yıllık) |
| **Archive dizini** | `data/bist_datastore_archive/index_components/` |
| **Archive durumu** | **BOŞ** — hiç indirilmemiş |
| **ZIP içeriği** | **BİLİNMİYOR** — ilan-tarihi alanı var mı? doğrulanmadı |
| **İndirme altyapısı** | Hazır (`bist_datastore_client.py`; `download_viop_3208.py` pattern'i) |

---

## 3. Olay Sayımı (N) — Kırılımlı

### 3.1 Ham Sayım (flag-bazlı, tüm değişimler)

Kaynak: `bist100`/`bist30` sütunlarında günlük diff = ±1 olan satırlar.

#### XU100

| Yıl | IN | OUT | Toplam |
|-----|----|-----|--------|
| 2019 |  14 |  15 |  29 |
| 2020 |  39 |  34 |  73 |
| 2021 |  44 |  43 |  87 |
| 2022 |  35 |  34 |  69 |
| 2023 |  33 |  33 |  66 |
| 2024 |  38 |  38 |  76 |
| 2025 |  35 |  36 |  71 |
| 2026 |   8 |   8 |  16 |
| **Toplam** | **246** | **241** | **487** |

Tarih aralığı: 2019-04-01 .. 2026-04-01

#### XU030

| Yıl | IN | OUT | Toplam |
|-----|----|-----|--------|
| 2019 |  1 |  1 |   2 |
| 2020 |  4 |  2 |   6 |
| 2021 |  3 |  3 |   6 |
| 2022 |  3 |  3 |   6 |
| 2023 |  6 |  6 |  12 |
| 2024 |  5 |  5 |  10 |
| 2025 |  5 |  5 |  10 |
| 2026 |  1 |  1 |   2 |
| **Toplam** | **28** | **26** | **54** |

Tarih aralığı: 2019-07-01 .. 2026-04-01

### 3.2 Önemli Uyarı: "Ham N" ≠ "Planlı Rekonstitüsyon N"

XU100'ün yıllık ~70-87 olayı beklenenden ~4x yüksek. BIST çeyreklik
rekonstitüsyonunda XU100 için tipik değişim oturumu başına 3-8 isim;
4 oturum × 6 ortalama = yılda ~24 beklenir, elde edilen ~73.

Fark kaynakları:
1. **Acil değişimler** — delisting, birleşme/devralma, halka arz otomatik ekleme
2. **Ara dönem ayarlamaları** — serbest dolaşım ağırlığı yeniden hesaplaması
3. **Veri kalitesi** — ara günlerde flag sıfırlanıp tekrar 1 olması (artifact)

Bu nedenle "rekonstitüsyon demand-shock" hipotezi için **planlı çeyreklik oturumlar**
ayrıştırılmalıdır. DataStore 3184 BIST'in resmi duyuru tarihlerini içeriyorsa bu
ayrıştırma mümkün olur.

**Muhafazakâr N tahmini (planlı oturumlar):**

| Endeks | Çeyrek/yıl | Ort. değişim/oturum | 2019-2026 (~7 yıl) | Tahmini N |
|--------|-----------|---------------------|---------------------|-----------|
| XU100 | 4 | 5-8 | 28 oturum | ~140-224 |
| XU030 | 4 | 1-2 | 28 oturum | ~28-56 |

XU030 ham sayısı (54) bu aralıkla uyumlu → flag kalitesi XU030 için yüksek.
XU100 ham sayısı (487) acil değişimler + artifact içeriyor.

### 3.3 Join-Edilebilirlik

| Endeks | Toplam sembol | clean_universe'de | Eksik |
|--------|--------------|-------------------|-------|
| XU100 | 186 | 186 | **0** |
| XU030 | 31  | 31  | **0** |

**%100 join-edilebilirlik.** Delisted olanlar dahil tüm semboller
clean_universe'de mevcuttur.

---

## 4. Look-Ahead-Safe Panel Analizi

### 4.1 Neden Kritik?

Demand-shock hipotezi şunu öngörür: fiyat-duyarsız pasif-sermaye
rebalans-tarihinde mekanik alım/satım yapar. Bir yatırımcı bu mekanizmadan
**ÖNCE** pozisyon almak için **ilan-tarihini** bilmek zorundadır.

Strateji zaman çizelgesi:
```
[İlan Tarihi]                [Yürürlük Tarihi]
      |                             |
      |--- t+1 t+2 ... t+N gün ----|
      ^                             ^
  buraya GİR                    burada etki zirveye çıkar / pozisyonu kapat
```

İlan-tarihi olmadan yalnızca yürürlük-tarihine dayalı bir entry,
mekanizmanın başladığı noktayı kaçırır veya aynı güne denk gelir.

### 4.2 Mevcut Veri Durumu

| Tarih türü | Kaynak | Mevcut? |
|-----------|--------|---------|
| **Efektif tarih** | clean_universe PIT flags | ✅ EVET |
| **İlan tarihi** | DataStore 3184 ZIP | ❓ BİLİNMİYOR |
| **İlan tarihi** | KAP bildirimleri (serbest arama) | ⚠️ Mümkün ama manuel |
| **İlan tarihi** | BIST resmi site (statik HTML) | ⚠️ Tarihsel erişim belirsiz |

### 4.3 Fizibilite Engeli

> **Ilan-tarihi kaynağı doğrulanmadan look-ahead-safe panel "kurulabilir" sayılmaz.**

Bu DISC-5 gereğidir (veri-premisi varsayılmaz). Engel iki yoldan kalkar:
1. DataStore 3184 ZIP dosyası indirilir ve içinde ilan-tarihi sütunu bulunur
2. KAP arama veya BIST arşivinden ilan tarihleri manuel olarak çekilir

---

## 5. Fizibilite Engeli Özeti

| # | Engel | Giderim |
|---|-------|---------|
| **F-1** | DataStore 3184 archive boş | 1 yıllık ZIP indir, şema incele |
| **F-2** | ZIP'te ilan-tarihi var mı bilinmiyor | ZIP parse et; `ilan_tarihi` / `bildirim_tarihi` sütunu ara |
| **F-3** | XU100 ham N'i planlı rekon'dan ~4x yüksek | DataStore 3184'ten resmi oturum tarihleri ile filtrele |
| **F-4** | Ara-dönem (acil) değişimler, planlı rekon'dan ayrıştırılmamış | F-1/F-2 çözümünün yan-ürünü |

---

## 6. N-Yeterlilik Ön-Değerlendirmesi

| Endeks | Ham N | Planlı N (tahmini) | Hüküm |
|--------|-------|--------------------|-------|
| XU100 | 487 | ~140-224 | **Stage-0 ADAYI** (N ≥ 20) |
| XU030 | 54 | ~28-56 | **Stage-0 ADAYI** (N ≥ 20, ama dikkatli) |

XU030 için planlı-rekon N'i ~28-56 aralığında; alt-kenar 28 ile
C9-tipi düşük-N riski sınırına yakın. Kırılımlı analiz (dahil vs. çıkar)
yapılacaksa her alt-küme ~14-28 olur — bu dikkat gerektirir.

**Bu hüküm Stage-0 açılması kararını besler; kararı VERMEZ.**

---

## 7. Önerilen Sonraki Adımlar (maintainer kararı)

1. **F-1 gider:** `scripts/download_index_components_3184.py` yaz, 1 yıllık ZIP indir
2. **F-2 gider:** ZIP şemasını belgele; ilan-tarihi var mı?
3. Eğer ilan-tarihi mevcut → Stage-0 ön-kayıt açılır (ayrı task)
4. Eğer ilan-tarihi yok → KAP arama ile alternatif kaynak araştırması

---

## 8. Kapsam-Uyumu Beyanı

Bu raporda şunların HİÇBİRİ üretilmemiştir:
sinyal hesabı · forward getiri · IC / NW-t / Sharpe · edge hükmü ·
"tradeable" değerlendirmesi · Stage-0 parametresi · keep-bar · eşik.

Committed kod değiştirilmemiştir.
Yeni artefakt: `scripts/scratch/probe_index_recon_3184.py` (salt-okuma keşif scripti).

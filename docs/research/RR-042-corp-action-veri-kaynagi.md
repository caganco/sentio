# RR-042 — Corp-Action Veri-Kaynağı Geniş Araştırması (NRR-004 + Faz-2 KAP probe)

**Tür:** ARAŞTIRMA (read-only API probe + envanter). **Tarih:** 2 Haziran 2026 (Faz-1 + Faz-2).
**Bağlam:** adjusted + survivorship-temiz evren (D-200) için corp-action verisi (bedelli oran +
subscription-price, bedelsiz oran, nakit temettü) ŞART. DataStore corp-action ürünleri
(100460/461/471) server-whitelist KESİN-bloke; price-implied yaklaşım (YOL-2) çöktü.
**İlgili:** D-200 (clean_universe_builder); RR-020 §BIST-veri-haritası; NRR-EXPLORE-01/02; D-116/D-126 (robots).

> **Faz-1** (§Kaynak-kaynak bulgular): 5 kaynak survey, yfinance = altın kaynak.
> **Faz-2** (§Faz-2 — KAP/MKK_VYK ile kalan 7) : `MKK_VYK_TOKEN` ile delisted-bedelli 7
> sembolün canlı KAP probe'u. ÖNEMLİ: KAP'ın corp-action verisi **yapılandırılmış** çıktı
> (Faz-1 tahmininden iyi); KOZAL kesin çözüldü (bedelsiz, bedelli DEĞİL). Kısıt: IP-bazlı
> rate-limit (whitelist değil) → kör pagination pahalı, bilinçli durduruldu.

---

## TL;DR — VERDICT

**yfinance (`.splits` + `.dividends`) = ALTIN kaynak**, 3196 col-14 otoriter ex-date'leriyle
**hizalı, ücretsiz, robots-temiz (resmi Yahoo API), TERP-problemini çözüyor**.

- **KANIT (bedelli/TERP):** EREGL 2024-11-27, 3196 col-14=`03` (bedelli). Ham 3196 close
  50.10 → 24.70 (oran 0.493). yfinance `.splits` aynı tarihte **factor = 2.0** veriyor →
  ham fiyat sıçramasıyla **birebir** eşleşiyor. yfinance'in price-implied split factor'ü
  **TERP factor'ünün ta kendisi** — subscription-price'a İHTİYAÇ YOK (piyasa yeniden fiyatlaması
  TERP'i zaten içeriyor).
- **KANIT (hizalama):** TUPRS 2023-04-04 col-14=`03` → yfinance split 7.0 (aynı gün); temettü
  (kod 06) `.splits`'te değil `.dividends`'te (doğru ayrışma). 5/5 sembolde ex-date eşleşmesi.
- **TEK BOŞLUK — survivorship:** delisted ticker'lar yfinance'te 404 (KOZAA.IS "possibly delisted").
  2019+ evrende **683 equity sembol → 69 delisted → bunlardan yalnız 7'sinde col-14=03 olayı**
  var (DAGHL, HALKS, IDEAS, ITTFH, KOZAL, PEHOL, QNBFL). Yani residual exclusion **291 → ~7**.
- **FAZ-2 KIRILMASI — "03 ≠ bedelli":** KAP'ta KOZAL kesin çözüldü → `subProcessName=BDLSZ`,
  `internalResourcesBonusPercentage=2000` (20× **bedelsiz**), `preemtiveRightsPercentage` BOŞ.
  Price-implied factor **birebir** (525→~25 vs 3196 ham 26.48). Yani col-14=`03`'lerin önemli
  kısmı aslında **bedelsiz** → price-implied factor zaten kesin → KAP'a gerek YOK. arastirma katmani'ın
  "03 ⇒ bedelli ⇒ DROP" varsayımı **fazla agresif**.

**Karar (DEC-039 sınıfı, maintainer):** Hibrit — fiyat/PIT-üyelik/survivorship/otoriter-ex-date
**3196'dan** (zaten elde), corp-action factor + temettü **yfinance'ten** (survivor'lar),
delisted-`03` 7 sembol için **önce price-implied (ücretsiz, self-validate ≤%2)**; price-implied
tolerans-DIŞI kalan gerçek-bedelli için **KAP/MKK_VYK structured CA formu** (bütçeli, maintainer-onaylı).

---

## Mevcut durum — neden kritik

clean_universe `_meta.json` (D-200, YOL-2 price-implied APPROXIMATE modu):
- `excluded_symbols_count = 291` / 392 → **devasa isimler dışlanıyor**: ASELS, EREGL, FROTO,
  TUPRS, PGSUS, SASA, CCOLA, PETKM, ISCTR, ENKAI… Panel bu haliyle **kullanılamaz**.
- Sebep: bedelli (kod 03) olan her sembol TERP (sub-price) olmadığı için tamamen drop ediliyor.

yfinance hibridi bu 291 dışlamayı ~7'ye indirir (delisted-bedelli kalıntısı).

---

## Kaynak-kaynak bulgular

### KAYNAK-2: yfinance (`.splits` / `.dividends` / `.actions`) — ✅ ÖNERİLEN
| Soru | Cevap |
|---|---|
| Erişilebilir? | **Evet**, ücretsiz, kütüphane zaten kurulu (requirements.txt) |
| Kapsam 2019+? | **Evet** — splits/dividends 2001→2026 (GARAN div_first 2006, div_last 2026-04) |
| Parse-edilebilir? | **Evet** — yapılandırılmış (date, ratio/amount); ek parse yok |
| Meşru (robots/ToS)? | **Evet** — resmi Yahoo Finance endpoint, scrape değil |
| TERP yeterli? | **EVET (dolaylı)** — split factor = piyasa-implied TERP factor; sub-price gereksiz |
| **Sınır** | **Delisted ticker = 404** (survivorship-biased). KOZAA.IS, KOZAL vb. yok |

Kanıt (ampirik probe, network-live):
```
EREGL.IS split 2024-11-27 = 2.0   ↔ 3196 col14=03, raw close 50.10→24.70 (×0.493)  EŞLEŞTİ
TUPRS.IS split 2023-04-04 = 7.0   ↔ 3196 col14=03 aynı tarih                         EŞLEŞTİ
SISE/KCHOL : .splits boş, kod-06 temettüler .dividends'te                            DOĞRU
KOZAA.IS   : HTTP 404 "possibly delisted"                                            BOŞLUK
```
**Not (redenominasyon):** 2005-01-03'te tüm isimlerde factor 0.001 (YTL'den 6 sıfır atılması) —
2019+ penceresi dışında, ilgisiz.

### KAYNAK-1: KAP (MKK VYK API) — ⚠️ yapılandırılmış AMA arama pahalı (Faz-2'de düzeltildi)
- **Faz-1 tahmini yanlış çıktı:** corp-action ODA-narrative değil — KAP `disclosureType=CA`
  bildiriminin `flatData` (KPY52DTO) formu **tam yapılandırılmış** oran alanları taşıyor:
  `subProcessName` (BDLSZ/BDL), `preemtiveRightsPercentage`+`...Amount` (**bedelli**),
  `internalResourcesBonusPercentage`+`...Amount` (**bedelsiz**),
  `bonusIssueFromDividendPercentage`. NLP gerekmez (Faz-2'de KOZAL formunda doğrulandı).
- `MKK_VYK_BASE_URL` (apigwdev→Basic auth) + `MKK_VYK_TOKEN` env gerekir (builder'da yok → maintainer-env).
- **ASIL MALİYET — arama:** `get_disclosures` **tarih/event-type filtresi YOK**; `start_index`'ten
  artan ~9-kayıtlık sayfalar döner ve index **doğrusal-OLMAYAN** büyür (dönem hacmine göre).
  Belirli bir tarihsel CA bildirimini bulmak = kör pagination. (Probe: idx 1138619 → Nis-2023,
  tahmin Oca-2024 değil; QNBFL 2024-03 olayı idx 1.18M/1.205M'de bulunamadı.)
- **Rate-limit:** whitelist DEĞİL ama **IP-bazlı sınırlı istek**. Faz-2'de ~30+ çağrı harcandı;
  kör ikili-arama bu kısıtı ihlal edeceği için **bilinçli durduruldu**.
- **Sonuç:** structured veri MEVCUT ve doğru; ama tarihsel-arama request-pahalı. Yalnız
  price-implied'in tolerans-dışı kaldığı **gerçek-bedelli kalıntı** için bütçeli kullanılır.

### KAYNAK-3: İş Yatırım / Mynet / Bigpara — ⚠️ belgelenmemiş, parçalı
- Prior research (RR-020, RR-032 ailesi, NRR-EXPLORE-02) corp-action **olay tarihçesi** için
  bunları belgelemiyor. İş Yatırım fiyatı bonus sonrası doğru ayarlıyor (RR-020:348) ama yapılandırılmış
  bedelli/bedelsiz **event endpoint'i** yok. `isyatirim_scraper.py` fundamental/screener odaklı.
- Mynet/Bigpara: yalnız güncel oran (F/K, PD/DD) HTML scrape; corp-action geçmişi belgelenmemiş, kırılgan.
- robots: İş Yatırım 🟢 (screener robots-safe), Mynet/Bigpara gri HTML.
- **Sonuç:** yfinance varken gereksiz; yedek bile değil.

### KAYNAK-4: TEFAS / SPK / Borsa İstanbul bülten — ⚠️ uygun değil / auth-gated
- TEFAS: fon-odaklı, bireysel hisse corp-action YOK.
- SPK: yalnız IPO takvimi + açığa-satış listeleri; rights/bonus/dividend endpoint'i yok.
- BIST resmi: index-rebalance/IPO duyuruları; corp-action structured veri = **DataStore 100471
  (Temettü)** → akademik $0 / ticari ücretli, **auth + payment-profile** (NRR-EXPLORE-01 §B: 401).
  Bu, NRR-004'ün başlangıç noktası olan KESİN-blokun ta kendisi.
- **Sonuç:** sadece delisted-bedelli kalıntısı için maintainer-manuel academic-erişim opsiyonu.

### KAYNAK-5: 3196'nın kendi 52 kolonu — ❌ oran YOK
- 52 kolonun **tamamı** ham olarak tarandı (`PP_GUNSONUFIYATHACIM` header doğrulandı).
- Corp-action ile ilgili **tek** alan: **col-14 CORPORATE ACTION** — sadece bir **KOD**
  (`01`=bedelsiz, `03`=bedelli, `06`=temettü ex-date, `06`'lar AKBNK/ANHYT'de doğrulandı).
- Oran, subscription-price, yeni-pay-sayısı **HİÇBİR kolonda YOK**. Diğer 51 kolon
  fiyat/hacim/mikroyapı (opening/closing/VWAP/short-sale/trade-report).
- **Sonuç:** 3196 col-14 = otoriter **NE-ZAMAN + NE-TÜR** kaynağı (tüm isimler, delisted dahil),
  ama **NE-KADAR** (factor) içermez. yfinance'in tamamlayıcı değeri tam burada.

---

## Faz-2 — KAP/MKK_VYK ile kalan 7 (delisted-`03`)

**Amaç:** yfinance'in göremediği (404 delisted) 7 sembolü `MKK_VYK_TOKEN` ile çözmek.
**Kısıt (maintainer, verbatim):** "whitelist değil ip'miz — sınırlı sayıda istek." → kör pagination yasak.

### Erişilebilirlik (KAP `members` haritası)
| Durum | Semboller | Not |
|---|---|---|
| **Erişilir (companyId var)** | DAGHL, KOZAL, PEHOL, QNBFL | `members`'ta kayıtlı |
| **Erişilemez (companyId yok)** | HALKS, IDEAS, ITTFH | hepsi 2019 olayı, sicilden düşmüş → companyId ile sorgulanamaz |

### Kesin çözülen — KOZAL
- KAP `flatData`: `subProcessName=BDLSZ`, `internalResourcesBonusPercentage=2000.00000`,
  `preemtiveRightsPercentage` BOŞ → **BEDELSİZ 20× (bonus)**, bedelli/rights DEĞİL.
  Subscription-price yok/gereksiz.
- Doğrulama: price-implied factor 0.0476 × 525 ≈ 25.0 vs 3196 ham 26.48 → **temiz eşleşme**.
- **Çıkarım:** col-14=`03` ≠ otomatik bedelli. arastirma katmani'ın blanket-drop kuralı yanlış pozitif üretiyor.

### Maliyet bulgusu (neden 4/4 bitirilmedi)
- DAGHL/PEHOL/QNBFL için spesifik tarihsel CA bildirimini bulmak, tarih-filtresiz endpoint'te
  kör ikili-arama gerektiriyor (yukarıda KAYNAK-1). ~30+ çağrı sonrası, maintainer'ın "sınırlı istek"
  kısıtını ihlal etmemek için durduruldu. Daha fazla harcama = açık bütçe + onay gerektirir.

### Faz-2 reframe (önemli)
KOZAL bedelsiz çıkınca problem yeniden çerçevelendi: **eğer `03` kalıntılarının çoğu bedelsiz ise,
3196'dan price-implied factor zaten kesin → KAP'a hiç gerek yok.** arastirma katmani yalnızca price-implied'in
3196 ham fiyat-sıçramasıyla ≤%2 eşleşmediği vakaları "gerçek-bedelli, TERP gerek" diye işaretlemeli.

---

## Önerilen mimari (hibrit) — DEC-039 kararına sunulur

| Veri | Kaynak | Kapsam |
|---|---|---|
| Fiyat + PIT BIST100/30 üyelik + survivorship (delisted dahil) | **3196 (elde)** | tüm 683 sembol |
| Otoriter corp-action ex-date + tür (01/03/06) | **3196 col-14 (elde)** | tüm 683 sembol |
| Corp-action **factor** (bedelli+bedelsiz, TERP dahil) + nakit temettü | **yfinance** | 614 survivor |
| Delisted-`03` factor (kalıntı, çoğu bedelsiz) | **price-implied (3196, ücretsiz, self-validate)** | 7 sembol |
| Yalnız price-implied tolerans-dışı (gerçek-bedelli) | **KAP/MKK_VYK CA formu (bütçeli, maintainer-onay)** | ≤birkaç sembol |

İş akışı: 3196 col-14 olay tarihini (otoriter) yfinance `.splits`/`.dividends` factor'üyle
ex-date üzerinden join et → survivor'lar **tam-doğru** back-adjust + total-return.
clean_universe_builder zaten `parse_corp_actions` + `compute_adjustment_factors` (TERP mantığı)
ve back-adjust pipeline'ına sahip; yalnız **kaynak besleme** (yfinance→ratio) eklenir.

**Net kazanım:** residual exclusion **291 → ~7** (98% iyileşme); TERP problemi survivor'larda çözülür.

---

## maintainer-manuel adımlar (engel-değil, paralel)
1. **(Faz-2'de doğrulandı)** `MKK_VYK_TOKEN` env mevcut ve çalışıyor; structured CA formu erişilebilir.
   Gerek kalırsa yalnız **açık istek-bütçesi + onay** ile kullanılır (IP rate-limit).
2. yfinance entegrasyonu için **manuel adım YOK** — auth-suz, doğrudan çalışır.

---

## Sonraki adım (kod — O onayı gerekir)
- **D-20X (Yol-1, ücretsiz, ÖNERİLEN):** clean_universe_builder kaynak-katmanı:
  (a) survivor factor + temettü = **yfinance** (3196 col-14 ex-date join);
  (b) col-14=`03` kalıntılarına **price-implied factor uygula + self-validate** (price-implied
  vs 3196 ham sıçrama ≤%2 ⇒ kabul/bedelsiz; >%2 ⇒ "gerçek-bedelli" flag).
  YOL-2 blanket-drop kaldırılır; `parse_corp_actions`/`compute_adjustment_factors` imzası korunur.
  **0 KAP çağrısı.** Beklenen: residual exclusion 291 → ~0–3.
- **D-20Y (Yol-2, opsiyonel, bütçeli):** sadece Yol-1'de "gerçek-bedelli" flag kalan + reachable
  (DAGHL/PEHOL/QNBFL) için sınırlı, disk-cache'li KAP CA-form fetcher; **≤N çağrı bütçesi
  (örn. 40), maintainer-onaylı tek koşu.** HALKS/IDEAS/ITTFH (2019, members'ta yok) erişilemez kalır →
  price-implied'e bırakılır.
- Doğrulama testi: yfinance/price-implied factor vs 3196 ham fiyat-sıçraması ≤%2 sapma, tüm 03/01 olayları.

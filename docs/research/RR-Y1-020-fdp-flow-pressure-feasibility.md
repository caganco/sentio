# RR-Y1-020 — Akım-Kaynaklı Baskı (FDP) faktörü — Faz-1 İNŞA-EDİLEBİLİRLİK probu

**Sınıf:** İnşa-edilebilirlik (constructibility) / veri-fizibilite probu. **Stage-0-DEĞİL**,
ölçüm-DEĞİL, edge-iddiası-DEĞİL. Hiçbir getiri / CAR / forward-return / tersine-dönüş
hesaplanmadı; hiçbir dondurulmuş pencere tüketilmedi. Tek çıktı: FDP faktörünün **kullanılabilir
çözünürlükte inşa edilip edilemeyeceğine** dair üç-dallı bir fizibilite hükmü. **Go/no-go kararı
bu rapora ait değildir** — maintainer'a aittir. RR-Y1-017 / RR-Y1-019 prob şablonuyla aynı.

**Aday-kaynak (yetkili, yeniden-türetilmez):** mekanik, bilgisiz fon-akımlarına likidite sağlama
(Coval-Stafford 2007; Gabaix-Koijen inelastik-piyasalar, akım-çarpanı M≈5). Açık-uçlu TR fonları
(hisse + BES emeklilik) NAV'dan birim yaratır/itfa eder; **tasarruf-sahibi** yaratım/itfayı
sürükler ve bu tek-hisse düzeyinde bilgisizdir. İtfa eden tasarruf-sahibi fonu varlık-satmaya
zorlar → geçici fiyat-baskısı → tersine-dönüş (likidite-sağlayarak yararlanmak istediğimiz edge).
Mekanik akım **NAV-değişiminden değil, pay-sayısı-değişiminden** izole edilir.

> **Faktör:** FDP_i,t = Σ_f [ Flow_f,t × w_{f,i,t-k} ], burada
> Flow_f,t = Δ(pay_sayısı_f,t) × NAV_f,t (mekanik yaratım/itfa);
> w_{f,i,t-k} = hisse i'nin f fonundaki ağırlığı, t'den önceki son açıklanan portföy-tarihinde
> (GECİKMELİ, akım-öncesi — baskıyı hisse-i-spesifik bilgiden dik kılan budur).
> **Birincil hipotez (long-only-doğal):** aşırı-negatif FDP (zorunlu-satış) → aşırı-tepki →
> haftalar/aylar boyunca yukarı tersine-dönüş. **İkincil:** yüksek-pozitif FDP → kısa-vadeli
> akım-momentumu.

---

## TL;DR — HÜKÜM

**🟡 HOLDINGS-TOO-COARSE / DATA-INFEASIBLE (günlük çözünürlükte) → save/wait** (mezarlık-DEĞİL).

Faktörün iki girdisi de ücretsiz-public-veride faktörün varsaydığı **günlük** çözünürlükte
inşa-edilemez — iki bağımsız-duvar üst-üste biner:

| Girdi | Bulgu (canlı-ölçülmüş) | Sonuç |
|---|---|---|
| **Mekanik akım payı** (Δpay × NAV) | Günlük pay-sayısı (TEDPAYSAYISI) tarihçesi **hiçbir ücretsiz-yolda yok**: kanonik kaynak `/api/DB/BindHistoryInfo` artık **404** (2026-04 migrasyonunda emekli); v2'de yerine-geçen size/shares-history endpoint'i **yok**; SSR sayfası Akamai-kapılı. Yalnız **anlık-snapshot** (fonBilgiGetir) + **günlük NAV** (5y) var. | **Akım numeratörü FORWARD-SNAPSHOT-ONLY** — geçmişe-dönük test-edilemez |
| **Hisse-bazlı ağırlık** (w_{f,i}) | Per-stock ağırlıklar hiçbir TEFAS JSON'unda yok; asset-class allocation (HS=hisse %) Akamai/Playwright-kapılı ve **toplam** (per-stock değil); per-stock ağırlıklar yalnız **AYLIK** SPK/KAP portföy-dağılım-raporlarında + yayın-gecikmesiyle. | **w_{f,i,t-k} AYLIK + lag** — günlük FDP ay-eski ağırlık taşır |

**Kesişim (Step-3) bağlayıcı-kısıt DEĞİL:** TR hisse-fonları (190 YAT + 41 EMK hisse-kategori +
yüzlerce karma fon, canlı-sayım) mandaları gereği BIST-listeli (ağırlıkla BIST100) hisse tutar →
temiz-panel/investable-liste ile **NON-DISJOINT** (VBTS'in tersine; orada evren-ayrıktı). Adayı
öldüren ayrıklık değil, **veri-çözünürlüğü.**

**Mezarlık-değil gerekçesi:** olgu/literatür sağlam (Coval-Stafford ABD'de çeyreklik-holding ×
aylık-akımla ölçtü — yani aylık-holding kavramı-öldürmez). Duvar bir **veri-erişim/çözünürlük**
duvarı, bir yanlışlama değil. Tek-kavranabilir tarihsel-yol = **aylık-çözünürlük** varyantı ve o
da aylık SPK/KAP regülasyon-arşivlerinin parse-edilmesine bağlı (ayrı, test-edilmemiş fizibilite).

---

## A. Akım numeratörü (mekanik pay) — STEP 1

Akım = `Flow_f,t = Δ(pay_sayısı) × NAV`. Pay-sayısı ≈ `portföy_büyüklüğü / NAV`; dolayısıyla
**ya günlük pay-sayısı ya da günlük portföy-büyüklüğü** tarihçesi gerekir. NAV tek-başına
mekanik-akımı izole edemez (NAV-değişimi getiri-sürücülü; aradığımız ayrım pay-sayısı-sürücülü).

### A.1 — Erişim haritası (READ-ONLY, canlı-ölçülmüş; auth/satın-alma YOK)

| Rota | Sonuç (canlı) | FDP için |
|---|---|---|
| TEFAS v2 `fonFiyatBilgiGetir` (JSON, no-auth) | **200** — 5y **GÜNLÜK NAV** (birim-fiyat); yalnız fiyat, size/shares kolonu **yok** | NAV-ayağı var; akım-ayağı yok |
| TEFAS v2 `fonBilgiGetir` (JSON, no-auth) | **200** — yalnız **ANLIK snapshot**: portBuyukluk, yatirimciSayi, sonFiyat | snapshot — tarihçe-yok |
| TEFAS legacy `/api/DB/BindHistoryInfo` (kanonik günlük TEDPAYSAYISI/PORTFOYBUYUKLUK) | **404** — 2026-04 migrasyonunda emekli | günlük pay-sayısı tarihçesi **artık servis-edilmiyor** |
| TEFAS v2 size/shares-history adayları (`fonToplamDegerGetir`, `fonBuyuklukBilgiGetir`, …) | **404** — emekli endpoint'in v2-karşılığı **yok** | tarihsel size/shares yolu **kapalı** |
| TEFAS `fon-detayli-analiz` SSR sayfası | **200** gövde ama **Akamai-kapılı**; portBuyukluk/tedPaySayisi marker'ı yok (plain-HTTP) | plain-httpx'te size/shares **çekilemiyor** |

### A.2 — Bulgu

**Günlük pay-sayısı / portföy-büyüklüğü tarihçesi ücretsiz-public-yolda MEVCUT-DEĞİL.** Kanonik
günlük kaynak (`BindHistoryInfo`) migrasyonda emekli oldu (404); v2 yalnız **anlık** size +
**günlük NAV** verir. Dolayısıyla `Flow_f,t = Δpay × NAV` tarihsel-panel olarak **kurulamaz**;
yalnız **ileriye-doğru günlük snapshot biriktirilerek** (forward-recorder) oluşturulabilir
([[fizibilite_lab_data_sources]]'deki "flow series must be snapshotted forward" notuyla aynı).
1c (mekanik-vs-NAV ayrıştırma sağlaması) da bu yüzden geçmişe-dönük yapılamaz.

> **Aylık-alternatif (kavramsal):** aylık portföy-büyüklüğü SPK/KAP aylık-istatistik /
> portföy-değer arşivlerinden parse-edilebilirse, aylık `Δpay = Δ(size/NAV)` → **aylık akım**
> kurulabilir. Bu, **günlük** değil ama Coval-Stafford'ın çeyreklik-rejimine uygundur. Test
> edilmedi; ayrı parse-fizibilitesi (RR-042 kör-pagination maliyet-uyarısı geçerli).

---

## B. Hisse-bazlı portföy ağırlıkları (w_{f,i,t-k}) — STEP 2 (BAĞLAYICI kısıt)

Bu, faktörün **belirleyici fizibilite-olgusu**: w_{f,i,t-k}'nın bayatlığını (staleness) belirler.

| Rota | Frekans / nitelik | Sonuç |
|---|---|---|
| TEFAS asset-class allocation (HS = hisse %) | **Akamai/Playwright-kapılı** plain-HTTP'de; üstelik **toplam** hisse-% (per-stock DEĞİL) | per-stock ağırlık vermez |
| SPK / KAP aylık fon **Portföy Dağılım Raporu** | per-stock ağırlıklar **AYLIK** + yayın-gecikmesi (~haftalar) | gerçekçi cadence = **AYLIK + lag** |

**Net:** hisse-bazlı ağırlıklar **hiç günlük değil.** En iyi-durum = **aylık** açıklama + yayın
gecikmesi. `w_{f,i,t-k}` günlük FDP'ye taşındığında **haftalar-eski** ağırlık taşır. (Not: bu,
literatürün kabul-ettiği bayatlık seviyesi — Coval-Stafford çeyreklik N-SAR holding kullandı —
yani kavramı öldürmez, ama **günlük** inşayı öldürür.)

---

## C. Evren-kesişimi — STEP 3

**Canlı-sayım (TEFAS `fonGetiriBazliBilgiGetir`, no-auth):** YAT = 2131 fon (190 "Hisse Senedi
Şemsiye Fonu"); EMK = 399 fon (41 hisse-kategori) — artı yüzlerce karma/değişken/serbest fon
kısmî hisse tutar. Bu fonlar mandaları gereği **BIST-listeli** hisse tutar, ağırlıkla **BIST100**
büyük/orta-kap.

**Kesişim hükmü:** temiz survivorship-panel (681 isim) + 57-isim investable-liste ile
**NON-DISJOINT** (VBTS'in tam tersine — orada 165 olayın 0'ı investable-evrene değiyordu).
Hisse-fon-talebi tam-da held-evrene biner. **Per-stock kesişim-oranı ölçülmedi** çünkü per-stock
holdings yolu Akamai-kapılı/aylık; ancak ayrıklık **bağlayıcı-kısıt değil** (yukarıdaki akım+
holding duvarları üstte), bu yüzden kesinleşse-bile hükmü değiştirmez. Prob-script
(`scripts/probe/rr_y1_020_fdp_constructibility.py --holdings PATH`) bir per-stock snapshot
verildiği an kesişim-sayımlarını (yalnız sayım, getiri-yok) üretir.

---

## D. İnşa-edilebilirlik özeti — STEP 4

**FDP_i,t = günlük mekanik akım × gecikmeli holding, temiz-evrene eşlenmiş.**

- **(günlük, tarihsel) → İNŞA-EDİLEMEZ (ücretsiz-public-veride).** İki bileşik-duvar: (a) akım
  numeratörü forward-only (günlük pay-sayısı tarihçesi yok), (b) holdings aylık+lag. Sınırlayıcı
  faktör: **ikisi birden** — ama günlük-akım eksikliği daha-temel (snapshot-öncesi geçmiş yok).
- **(aylık, tarihsel) → KAVRANABİLİR-AMA-TEST-EDİLMEMİŞ.** Tek-yol: aylık SPK/KAP regülasyon
  arşivlerinden HEM aylık fon-büyüklüğü (→ aylık akım) HEM aylık per-stock holdings parse etmek.
  Ayrı, açılmamış bir parse-fizibilitesi; RR-042 kör-pagination maliyet-uyarısı geçerli.
- **(forward-only) → MÜMKÜN.** Günlük snapshot (size+NAV+allocation) ileriye-doğru biriktirilirse
  forward-recorder kurulabilir; ama bir geçmiş-backtest sağlamaz (yalnız ileriye-akümülasyon).

**Phase-2'nin zorunlu kontrolleri (faktör-getiri ilişkisi BURADA hesaplanmadı):** hisse-kendi-getirisi
(flow ≠ getiri-sürücülü size-değişimi), fon-kendi-getirisi, **orantılı-ticaret varsayımı** (fon
holdinglerini pro-rata satar/alır), fon-evreninin survivorship'i.

---

## E. Phase-2 çerçevesi (yalnız-belirt, HİÇBİR-ŞEY-DONDURMA/ÇALIŞTIRMA) — STEP 5

**Çift-katman tasarım:**
- **Gerçekçi-hüküm katmanı:** tam maliyet/slippage/spread + sonraki-açılış zamanlaması, **long-only**.
  Aşırı-negatif-FDP'de yukarı-tersine-dönüşü provider-likidite olarak ifade eder.
- **İdeal frictionless concept-ledger:** cost=slippage=spread=0 **ama** look-ahead-safe,
  survivorship-clean, **t→t+1 korunur** (zaman-oku asla gevşetilmez; asla bir-hüküm değil).

**Olay/kesit yapısı:** FDP-tersil bazında forward-return (aşırı-negatif-FDP → reversal;
aşırı-pozitif-FDP → momentum), **temiz TR-index**'e karşı benchmark'lı. Keep-bar adayları;
embargo/holdout yapısı. **Güçlü ideal-katman sinyali + ölümcül tradability/data duvarı →
save/wait + concept-ledger, mezarlık-DEĞİL.**

---

## F. Karar-kapısı (tek çıktı) — STEP 6

Üç-dal; hüküm gözlemlenen-veriden çıkar (ön-yargı-yok):

- **CONSTRUCTIBLE → Phase-2 öner (çift-katman), ayrı-soğuk-karara bağlı.** — ❌ değil.
- **🟡 HOLDINGS-TOO-COARSE / DATA-INFEASIBLE → save/wait.** — ✅ **HÜKÜM.** Faktör varsaydığı
  günlük-çözünürlükte ücretsiz-public-veride kurulamaz; akım-numeratörü forward-only, holdings
  aylık+lag. **Mezarlık-değil** (olgu/literatür sağlam; bu bir veri-çözünürlük duvarı). Tek-yol =
  aylık-varyant + aylık-arşiv-parse (ayrı fizibilite).
- **UNIVERSE-DISJOINT → save/wait.** — ❌ değil (evren NON-DISJOINT; hisse-fonları BIST-evrenine biner).

---

## Caveat'lar
- **Yalnız inşa-edilebilirlik** — getiri/sinyal/edge ölçülmedi (kapsam-dışı, DEC-053-safe).
- Online araştırma READ-ONLY: hesap-açma/satın-alma/paywall-indirme/auth/CAPTCHA **YOK**. 404/
  Akamai-kapı bulguları olduğu-gibi rapor edildi, bypass denenmedi.
- Akım/holding erişim-olguları **canlı-ölçüldü** (TEFAS v2 + legacy DB endpoint'leri 2026-06,
  plain httpx + Chrome-UA). Sites restyle eder → endpoint'ler tekrar-doğrulanmalı.
- Ham çekilen-bülten/JSON **repoya commit-EDİLMEDİ** (forward-recorder/flow_intel emsali);
  yalnız sayım-türevi + script + bu RR-doc kalıcıdır.
- Evren-kesişimi per-stock **ölçülmedi** (browser-kapılı/aylık); NON-DISJOINT yapısal-olarak
  rapor edildi, bağlayıcı-kısıt-olmadığı için hükmü-değiştirmez.
- Investable-payda = bugünkü statik `config.yaml` listesi; span-içi-değişim modellenmedi.
- Go/no-go **maintainer kararıdır**; bu rapor olgu-sağlar, hüküm-vermez.

Kaynaklar (online, read-only): TEFAS `tefas.gov.tr/api/funds/*` (v2 JSON, no-auth) ·
TEFAS legacy `/api/DB/*` (emekli, 404) · SPK/KAP aylık fon portföy-dağılım-raporları (aylık+lag) ·
Coval & Stafford (2007) "Asset Fire Sales (and Purchases) in Equity Markets" ·
Gabaix & Koijen (2021) "In Search of the Origins of Financial Fluctuations: The Inelastic Markets Hypothesis".

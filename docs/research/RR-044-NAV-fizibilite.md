# RR-044: NAV-İskonto Paradigması — VERİ-FİZİBİLİTE Turu (test-DEĞİL)

**Tür:** ARAŞTIRMA / FİZİBİLİTE (ölçüm-değil, edge-test-değil, Stage-0 gerekmez)
**Tarih:** 3 Haziran 2026 | **Hazırlayan:** Araştırma katmanı
**Bağlam:** Yol-1 cross-sectional-seçim tükendi (hi52-tavan). Yeni-paradigma haritasında
C-NAV-iskonto (holding mean-reversion) en-dengeli çıktı. Bu, dalmadan-önce VERİ-FİZİBİLİTE turu.
**Önceki:** [RR-013](RR-013_NAV_ISKONTO.md) (pilot metodoloji + literatür — bu tur onu genişletir, tekrarlamaz).
**Çıktı niteliği:** Kod-yok, test-yok, edge-ölçüm-yok. Sadece "test edilebilir mi, hangi veriyle, sonraki adım ne" hükmü.

> ★ **D-200 dersi (bu turun gerekçesi):** Veri-fizibilite, mimari/test-ÖNCESİ doğrulanır. RR-013
> güzel bir metodoloji + literatür sundu AMA tarihsel NAV serisini **stale broker NAV'ından** türetti
> (§9.2: *"Gedik raporundaki SoTP'yi 24 Mayıs 2026 fiyatlarına güncellemek için tam canlı veri elimizde yok"*)
> ve §10.7'de tarihsel iskonto serisini açıkça **"Veri Bulunamadı"** listesine koydu. RR-044, tam da o boşluğu
> kapatır: **NAV iskonto serisini KENDİMİZ, look-ahead-safe, yerel veriden hesaplayabilir miyiz?** price-implied
> %43-çöküşü ve 1e8-INFEASIBLE-havuz derslerinden sonra önce-fizibiliteyi-ölç, kör-test-kurma.

---

## 0. TL;DR — HÜKÜM

**NAV paradigması TARİHSEL-TEST-EDİLEBİLİR.** PEAD/event-signals gibi *forward-only* DEĞİL — geçmiş iskonto
serisini yerel veriden yeniden kurabiliyoruz. Tek bağlayıcı kısıt **kompozisyon (iştirak-pay) katmanı**, ve
o bile sinyal için kritik değil (aşağıda Z-skor-invariyans argümanı). Özet:

| Soru | Hüküm | Bağlayıcı mı? |
|---|---|---|
| **S1** Hangi holding NAV-temiz? | ~3 temiz+likit (KCHOL/SAHOL/AGHOL), ~5-8 ikinci-derece. degoran'da 55 "holding" etiketli ama çoğu tek-iştirakli/küçük yatırım şirketi. **Küçük-N duvarı sürüyor.** | Kısmen (N-problemi) |
| **S2-değer** İştirak piyasa değerleri tarihsel var mı? | **EVET. degoran PİYASA DEĞERİ aylık 2009-01→2026-04 sürekli, tarihli, look-ahead-safe.** + ÖZSERMAYE (özel iştirak book değeri). | HAYIR (çözüldü) |
| **S2-kompozisyon** İştirak-pay tarihsel serisi var mı? | **HAYIR yerel zaman-serisi yok** (corporate_actions/index_components/dividends KLASÖRLERİ BOŞ). Paylar KAP faaliyet raporundan parça-parça-sabit + elle-tarihlenmiş değişim-noktası olarak kurulmalı. **AMA Z-skor sabit-pay-yanlılığına büyük ölçüde duyarsız** (§S2.4) → sinyal için bloke-DEĞİL. | Kısmen (kalibrasyon için evet, sinyal için hayır) |
| **S2-holdco nakit** Solo net nakit tarihsel var mı? | HAYIR (degoran konsolide özsermaye verir, solo-nakit değil). NAV'ın ~%5'i → küçük; sabit-tut/yaklaşık. | HAYIR (küçük) |
| **S3** Literatür fenomen-prior'ı veriyor mu? | US-CEF için GÜÇLÜ (Pontiff: %20-iskonto → +%6/12ay MR). EM/konglomera-iskontosu belgeli. **Türkiye-spesifik holding-MR ampirik testi YOK** (RR-013 + güncel arama doğruladı). Yüksek-faiz (Pontiff-1996 *costly arbitrage*) → iskonto **yapışkan** olabilir. Prior: **ORTA.** | — |
| **S4** Retail-fizibıl mi? | EVET. KCHOL/SAHOL/AGHOL BIST30 mega-cap, sıfır-slipaj. İskonto-aralığı GENİŞ. MR yarı-ömrü 7-10 ay → **DÜŞÜK turnover** → retail-dostu, maliyet-dostu. edge-araştırmasını öldüren overnight/reversal'in TERSİ profil. | HAYIR (pozitif) |

**Sonraki-adım önerisi (D-XXX):** Tam mimari (RR-013 Faz 1-4, holdings.yaml + SQLite + L_NAV katmanı)
KURMA. Önce **minimal sinyal-okuması**: degoran market-cap + sabit-yakın-pay vektörü ile clean-holding sepetinde
(N~6-8) iskonto-Z'sinin ileri-getiri öngörü içeriği var mı (IC + edge-araştırma keep-bar: |NW-t|≥2, EW-null,
§21 carry-trap, nominal-vs-reel). D-200-uyumlu: **önce sinyali-ölç, sonra mimari.** Detay §6.

---

## 1. Veri Envanteri (bu turda fiilen kontrol edildi)

Kaynak: `data/bist_datastore_archive/` (ana repodan symlink; bkz. reference-bist-datastore-archive memory).
Bu turda zip'ler açılıp kolonları **fiilen okundu** — aşağıdaki hükümler spekülasyon değil, doğrulama.

### 1.1 degoran (fundamental_ratios/) — NAV'ın DEĞER ayağı ✅

- **Kapsam:** Aylık, 2009-01 → 2026-04 **sürekli** (eski şema `degoranYYYYMM.zip` 2009-2019 + yeni şema
  `degoran_M_YYYYMM.zip` 2019-07→2026-04). + yıllık 1995-2008. Toplam 229 dosya.
- **İki format:** eski `.xls` (15-kolon, ORAN başlıklı, indeks-agregaları üstte, ticker sütun-0, mcap sütun-3 *Bin TL*);
  yeni `.xlsx`/`.xls` (13-kolon, çift-dilli başlık, ticker sütun-1 `.E`-ekli, MARKET VALUE sütun-6 *TL*). Toleranslı
  parser gerek (çalışan referans: `edge-arastirma/lab/ff_data.py`; geçiş-ayı 2022-06 gibi tek-tük format-varyantı var).
- **Kolonlar (yeni şema):** DATE, EQUITY CODE, SECURITY NAME, MARKET, SECTOR, **SUB SECTOR**, **PIYASA DEGERI
  (market value)**, NET KAR (4Ç), **OZSERMAYE (equity/book)**, NAKIT NET TEMETTU, F/K, PD/DD, TV%.
- **Doğrulama (KCHOL + iştirak market-cap, mlr TL):**

  | dosya | KCHOL | TUPRS | FROTO | YKBNK |
  |---|---|---|---|---|
  | 2010-06 | 13.0 | 7.3 | 3.6 | 18.8 |
  | 2015-06 | 31.4 | 17.0 | 12.6 | 17.1 |
  | 2019-06 | 44.5 | 28.8 | 21.9 | 20.4 |
  | 2019-07 | 47.5 | 35.1 | 21.4 | 23.1 |
  | 2026-04 | 512.8 | 522.2 | 343.9 | 312.9 |

  → Şema-geçişi pürüzsüz, seri sürekli ve makul (TL enflasyonuyla tutarlı monoton büyüme). **İştirak piyasa
  değerleri tarihsel olarak HAZIR.**
- **Kritik sonuç:** NAV = Σ(payᵢ × market_capᵢ) formülünde `market_capᵢ` **tamamen çözülmüş** (her listelenmiş
  iştirak için aylık, tarihli). Ayrıca **OZSERMAYE** özel iştirakleri book-value ile değerlemek için var.
  degoran ayrıca SUB SECTOR="HOLDINGLER VE YATIRIM SIRKETLERI" etiketiyle **hazır holding-filtresi** sunar.

### 1.2 Boş/eksik klasörler — NAV'ın KOMPOZİSYON ayağı ❌

- `corporate_actions/` → **0 dosya** (boş). Pay-değişimi/bölünme/birleşme tarihçesi YOK.
- `index_components/` → **0 dosya** (boş).
- `dividends/` → **0 dosya** (boş).
- **Sonuç:** İştirak-pay (ownership %) zaman-serisi yerel olarak YOK. Paylar KAP faaliyet raporlarından
  manuel kurulmalı (RR-013 §4.1 zaten "yıllık güncelleme; SPK %5+ değişiklik duyurusuyla tetiklenir" demişti).
- `prices_official/` (aylık EOD fiyat+hacim 2016+) ve `prices_weekly/` likidite/teyit için var ama NAV-değeri
  zaten degoran market-cap'ten geliyor; bunlar ikincil.

### 1.3 Holdco solo net nakit — küçük boşluk ⚠️

degoran ÖZSERMAYE **konsolide** özsermayedir, holdco **solo** net nakit değil. RR-013 bunu manuel çeyreklik
`kchol_solo_cash.csv` ile çözmeyi önermişti. KCHOL'da net nakit NAV'ın ~%5.5'i (Gedik) → ikinci-derece kalem;
tarihsel için sabit-oran/yaklaşık tutulabilir, sinyali bozmaz.

---

## 2. S1 — Hangi Holding NAV-Temiz Hesaplanabilir?

**degoran'da 55 isim "holding/yatırım şirketi" etiketli** (2026-04). Ama etiket gürültülü: çoğu ya tek-listelenmiş-
çapa (TAVHL, SISE — operasyonel şirket), ya yeni-halka-arz küçük yatırım holdingi (HEDEF 290bn?, KLRHO, RALYH,
INVES — şişkin/spekülatif değerlemeler), ya da çok-küçük/illikit (alt-pazar, yakın-izleme). NAV-iskonto
paradigması yalnızca **çok-listelenmiş-iştirakli + likit** holdingler için temiz hesaplanır.

**NAV-temiz ayrımı = listelenmiş-iştirak payı yüksek (piyasa-fiyatlı, temiz) vs özel-iştirak payı yüksek
(book/değerleme, gürültülü, look-ahead-zor):**

| Kademe | Holding | Listelenmiş-iştirak durumu | NAV-temizlik |
|---|---|---|---|
| **Temiz çekirdek** | **KCHOL** (513bn) | FROTO/TOASO/TTRAK/OTKAR/TUPRS/AYGAZ/YKBNK/ARCLK ~%85 listelenmiş (Gedik) | ✅ Yüksek |
| | **SAHOL** (201bn) | 11 listelenmiş iştirak (AKBNK dominant + ENJSA/CIMSA/BRISA/KORDS/CRFSA/TKNSA/AGESA/AKGRT/AKCNS); Enerjisa Üretim özel | ✅ Yüksek (1 büyük özel) |
| | **AGHOL** (76bn) | AEFES + CCOLA(AEFES üzerinden, çift-sayım dikkat) + MGROS + ASUZU + ADEL listelenmiş | ✅ Yüksek (çift-sayım uyarısı) |
| **İkinci derece** | TKFEN, ALARK, DOHOL, GLYHO, BRYAT, GSDHO, ECILC, POLHO, NTHOL | Kısmen listelenmiş çapa + ağırlıklı özel/konsolide operasyon → SoTP gürültülü | ⚠️ Orta/Düşük |
| **Strateji-dışı** | KOZAL (tek-varlık altın), HEDEF/KLRHO/RALYH/INVES (spekülatif yeni-arz), alt/yakın-izleme pazarı ~30 isim | NAV-iskonto kavramı uymaz / illikit | ❌ |

**Hüküm S1:** NAV-temiz + likit evren **gerçekçi olarak 3 çekirdek (KCHOL/SAHOL/AGHOL)**, en fazla **~6-8**
ikinci-dereceyi de katarak. Bu, RR-013'ün N=3 pilotunu ve §10.2 *"istatistiksel olarak yetersiz cross-sectional
örneklem"* uyarısını teyit eder. **Küçük-N, bu paradigmanın doğasında olan ve edge-araştırması boyunca tekrar tekrar
çıkan duvar.** (Karşılaştırma: hi52 evreni 681-isim; NAV evreni ≤8 → cross-sectional anlamlılık çok daha zor.)

---

## 3. S2 — Tarihsel NAV Hesaplanabilir mi? (look-ahead-safe — KRİTİK SORU)

NAV iskonto serisini tarihsel kurmak için 3 girdi gerekir. Her birinin yerel-fizibilitesi:

| Girdi | Yerel kaynak | Look-ahead-safe? | Hüküm |
|---|---|---|---|
| İştirak piyasa değerleri (zaman-serisi) | **degoran PİYASA DEĞERİ, aylık 2009-2026** | ✅ ay-sonu tarihli, geleceğe-bakmaz | **ÇÖZÜLDÜ** |
| Özel iştirak değeri | degoran ÖZSERMAYE (book) / peer-multiple | ✅ | Yaklaşık ama yeterli (Tier-1) |
| İştirak payları (zaman-serisi) | YOK (KAP faaliyet raporu manuel) | ⚠️ parça-sabit + tarihli-değişim-noktası | **Yaklaşık** (§3.3-3.4) |
| Holdco solo net nakit | YOK (manuel çeyreklik) | ⚠️ | Küçük, yaklaşık |

### 3.1 Değer ayağı — TAM FİZİBIL
degoran sayesinde her listelenmiş iştirakin aylık piyasa değeri 2009'a kadar mevcut. Bu, NAV'ın **zaman-içinde-
oynayan** bileşenidir (iştirak fiyatları günlük/aylık hareket eder) ve **tamamen yerel veriden, look-ahead-safe**
elde edilir. Bu, RR-013'ün stale-broker-NAV bağımlılığını **ortadan kaldırır** — asıl fizibilite kazanımı budur.

### 3.2 Kompozisyon ayağı — yerel zaman-serisi YOK
İştirak payları (KCHOL'un FROTO'nun %38.7'sine sahip olması gibi) degoran'da yoktur; ownership-yapısı verisidir.
`corporate_actions`/`index_components` boş. Dolayısıyla paylar **KAP yıllık faaliyet raporlarından** manuel
kurulmalı: parça-parça-sabit bir pay vektörü + bilinen büyük değişimlerin elle-tarihlenmesi (ör. KCHOL'un
YKBNK payını UniCredit-çıkışında 2020'de artırması; halka-arz/blok-satış/geri-alım olayları).

### 3.3 Pay yavaş-hareket eder → yaklaşım savunulabilir
Büyük holdinglerde paylar **çok stabildir** — yıllarca sabit, değişimler ayrık olaylarda olur. KCHOL'un FROTO
%38.46 payı yıllardır sabit. Yani parça-sabit + ~birkaç-tarihli-değişim-noktası, stabil-paylı holdingler için
küçük-hatalı bir tarihsel yaklaşımdır. (Aktif portföy-değiştiren GLYHO/DOHOL için hata büyük → onlar zaten
"ikinci derece".) **Tam look-ahead-safe** kompozisyon-serisi KAP faaliyet-raporu kazıması gerektirir (mevcut
değil) — ama bu **bloke değil**, sınırlı-manuel bir kurulum işidir (RR-013 Faz-1/2'nin zaten kapsadığı).

### 3.4 ★ KRİTİK İÇGÖRÜ — Z-skor, sabit-pay-yanlılığına duyarsız
Strateji, iskontonun mutlak-seviyesini değil, **kendi tarihsel ortalamasından sapmasını** (Z-skor) kullanır:
`z_t = (discount_t − rolling_mean) / rolling_std` (RR-013 §5.1). Paylarda **sabit (çarpımsal) bir yanlılık**
iskontonun *seviyesini* kaydırır ama Z-skoru (kendi yuvarlanan ortalama/std'sinden sapma) **büyük ölçüde
değişmez**. İskontonun *zaman-değişimi* degoran market-cap'ten gelir (ki o elimizde). Sonuç:

> **Yaklaşık sabit-pay vektörü bile KULLANILABİLİR bir SİNYAL üretir.** Hassas tarihsel paylar yalnızca
> *mutlak-iskonto kalibrasyonu / hedef-iskonto* (RR-013 Tier-2/3) için gerekir — **ilk sinyal-okuması için değil.**

Bu, kompozisyon-boşluğunu **sinyal açısından büyük ölçüde de-riske eder** ve minimal-test'i mümkün kılar (§6).

### 3.5 Hüküm S2
**Tarihsel NAV iskonto serisi YENİDEN-KURULABİLİR — PEAD gibi forward-only DEĞİL.** Değer-ayağı tam fizibil
(degoran). Kompozisyon-ayağı yerel zaman-serisi olarak yok ama (a) paylar yavaş-hareket → parça-sabit yaklaşım
savunulabilir, (b) Z-skor sabit-pay-yanlılığına duyarsız → sinyal için bloke değil. **Bağlayıcı iş kalemi:**
holding-başına pay-config (tarihli-değişim-noktalarıyla) — sınırlı manuel kurulum, RR-013'ün zaten öngördüğü.

---

## 4. S3 — Literatür: Fenomen-Prior

RR-013 §2 + §8 literatürü kapsamlı; burada **tekrarlamıyoruz, fizibilite-prior'ına çeviriyoruz.** (Güncel
web-araması 2024-2026 için **yeni Türkiye-holding-iskonto-MR ampirik çalışması bulmadı** → RR-013 §10.7'nin
"Türkçe ampirik test bulunamadı" hükmü hâlâ geçerli.)

| Boyut | Kanıt | Prior'a etkisi |
|---|---|---|
| Fenomen var mı (genel)? | Pontiff (1995): %20-iskontolu CEF'ler 12-ayda +%6 ek-getiri, **iskonto MR'ından** (portföy-performansından değil). Lee-Shleifer-Thaler (1991) sentiment-MR. | **GÜÇLÜ** (+) |
| Konglomera-iskontosu yapısal mı? | Berger-Ofek (1995) US %13-15; EM daha yüksek (TR %30-50). Khanna-Palepu, Bae-Kang-Kim, Lins, Yurtoğlu: aile/piramit/tunneling → **yapısal alt-taban** (iskonto sıfıra inmez, ortalamaya MR eder). | Nötr/yapısal (iskonto kalıcı bileşenli) |
| MR hızı? | Ji-Kim (2013): CEF yarı-ömrü 7.7-10.3 ay. | Düşük-turnover-uyumlu (S4 ile bağlanır) |
| **Türkiye-MR tradability?** | **Ampirik test YOK.** + Pontiff (1996) *costly arbitrage*: yüksek-faiz (TR politika %37-46) → iskonto **YAPIŞKAN** kalabilir; long-only kısıt short-bacağı keser (kısmi-alfa). | **RİSK (−)** |

**Hüküm S3 — prior ORTA.** Fenomenin *varlığı* iyi-belgeli; *Türkiye'de yüksek-faiz + long-only altında
tradability'si* açık-uçlu — ki bu tam da bir testin çözeceği soru. Boşluk hem **fırsat** (özgün, literatüre-katkı)
hem **risk** (yerel-validasyon yok, "sticky-discount" teorik-olarak-bekleniyor). edge-araştırma dersi burada uyarıcı:
"gerçek fenomen ≠ tradeable edge" (overnight §17, real-rate §13-14, VIX §19-21 hepsi gerçekti, hiçbiri net-edge değildi).

---

## 5. S4 — Retail-Fizibilite

| Boyut | Bulgu | Değerlendirme |
|---|---|---|
| Tradeable sayısı | KCHOL (513bn), SAHOL (201bn), AGHOL (76bn) = BIST30 mega-cap | ✅ Çekirdek-3 çok-likit |
| Likidite/slipaj | KCHOL günlük hacim ~5bn TL (RR-013 §3.1); retail-ölçekte slipaj ihmal | ✅ Sıfır-slipaj |
| İskonto-aralık genişliği | KCHOL: −%10 (prim) ↔ +%40 (derin), 15-yıl ort ~%13 (Gedik); AGHOL 1yr/3yr %38/%32 (İş Yat.) | ✅ GENİŞ → MR-sinyaline alan var |
| Turnover profili | MR yarı-ömrü 7-10 ay → seyrek sinyal, düşük işlem-frekansı | ✅ Maliyet-dostu |
| Maliyet-duvarı | Düşük-turnover → edge-araştırmasını öldüren round-trip-maliyet duvarına TAKILMAZ | ✅ overnight/reversal'in TERSİ |

**Hüküm S4 — POZİTİF.** Bu paradigma, edge-araştırmasının cost-killed bulgularının (overnight ~500 round-trip/yıl,
short-reversal haftalık churn) **yapısal tersi**: az-sayıda likit-mega-cap, seyrek-sinyal, düşük-maliyet. Retail
için en-uygun profillerden biri. Tek-mahzur: çekirdek-3 ile bu bir "3-isimli-timing-overlay"e benzer (cross-sectional
faktör değil) — test-tasarımında §6'da ele alınmalı.

---

## 6. NAV Paradigması Test-Edilebilir mi? — HÜKÜM + Sonraki Adım

### 6.1 Genel hüküm
**FİZİBİL (test-edilebilir).** Forward-only DEĞİL (PEAD'in aksine). Bağlayıcı kısıtlar net ve sınırlı:
1. **Küçük-N** (≤8 temiz holding) — cross-sectional anlamlılık zor; paradigmanın doğasında.
2. **Kompozisyon yaklaşımı** — pay-config manuel; ama Z-skor buna duyarsız (§3.4) → sinyal için bloke değil.
3. **Sticky-discount riski** — yüksek-faiz/long-only altında iskonto yapışabilir (S3, teorik-beklenen).
4. **Timing-overlay tuzağı** — çekirdek-3'te tek-isim-timing, edge-araştırmasının carry-trap'ine (§21) düşebilir.

### 6.2 NE YAPMA (D-200 dersi)
RR-013 Faz 1-4'ün **tam mimarisini KURMA**: holdings.yaml + SQLite şema + L_NAV composite-katmanı + signal-engine
entegrasyonu. Bu, "kör-mimari" — sinyalin var-olup-olmadığını bilmeden 6-haftalık inşa. price-implied-%43 ve
1e8-INFEASIBLE dersleri: önce sinyali-ölç.

### 6.3 ÖNERİLEN sonraki adım — D-XXX: Minimal NAV-İskonto Sinyal-Okuması
**Amaç:** İskonto-Z'nin ileri-getiri öngörü içeriği **var mı yok mu** — mimari-öncesi tek ölçüm.

- **Evren:** clean-6/8 holding (KCHOL/SAHOL/AGHOL çekirdek + TKFEN/ALARK/GLYHO/BRYAT/GSDHO ikinci-derece),
  **cross-sectional kurguda** (tek-isim-timing değil — §3.4-invariyans ile her-holdingin kendi-Z'si, sonra
  aylık en-yüksek-Z sepeti long, EW-null'a karşı). Bu, edge-araştırmasının EW-null disiplinini anlamlı kılar.
- **Veri:** degoran market-cap (iştirak değeri) + **sabit-yakın pay vektörü** (son KAP faaliyet-raporu payları,
  §3.4 gereği seviyeden-bağımsız sinyal) + book-value özel iştirak. Holdco-nakit sabit-oran.
- **Sinyal:** RR-013 §5.1 Z-skor (252g rolling), aylık rebalance.
- **Keep-bar (edge-araştırma firma-çizgisi):** |NW-HAC t| ≥ 2, non-overlap ICIR ≥ 0.5, **selection-vs-EW-null** kritik
  test; **§21 carry-trap baked-in** (nakit-bacağı→FLAT vs →TLREF, nominal-vs-reel); regime-split (2019-21 vs 2022-07+).
- **Maliyet:** düşük-turnover beklenir ama yine de 100bp cost-ballast (standart).
- **Çıktı:** "iskonto-Z'nin tradeable-öngörü-içeriği var/yok" — tek-sayfa hüküm. Pozitifse → RR-013 mimarisine
  geç. Negatifse → paradigma kapanır (edge-araştırma graveyard'ına "NAV-discount MR: no harvestable signal" eklenir).
- **Fizibilite:** Bu test **mevcut yerel veriyle bugün kurulabilir** — yeni-veri-çekme gerektirmez (degoran zaten var,
  pay-vektörü ~8 holding için elle-config birkaç-saatlik). Stage-0 (maintainer onayı) sonrası küçük bir D-XXX.

### 6.4 Dürüstlük notları
- **Forward-only DEĞİL** — tarihsel-test mümkün (S2 değer-ayağı çözüldü). Bu, RR-013'ün stale-NAV zaafını giderir.
- **Küçük-N gerçek** — N≤8 ile istatistiksel-anlamlılık 2-3 yıl OOS gerektirebilir (RR-013 §11.6); ilk-okuma
  "yön + büyüklük" verir, "kanıt" değil.
- **Sticky-discount teorik-beklenen** — eğer test "sinyal-var ama net-edge-yok" derse, bu edge-araştırmasının tekrarlayan
  dersiyle (gerçek-fenomen ≠ tradeable-edge) tutarlı; sürpriz olmaz, dürüstçe-graveyard.
- **Karar maintainer'da** — bu tur fizibiliteyi netleştirdi; test-kararı onun. Kör-mimari önerilmiyor.

---

## 7. Kaynaklar
- RR-013 (pilot metodoloji + tam literatür): [RR-013_NAV_ISKONTO.md](RR-013_NAV_ISKONTO.md)
- Veri envanteri: `data/bist_datastore_archive/{fundamental_ratios(degoran), prices_official, corporate_actions[boş], index_components[boş]}` (bu turda fiilen açılıp doğrulandı)
- edge-araştırma keep-bar + carry-trap + EW-null disiplini (yerel lab notlari).
- Literatür DOI'leri RR-013 §8'de. Güncel arama (2024-2026): yeni Türkiye-holding-MR ampirik çalışması bulunmadı.

Sources:
- [Borsa Istanbul - Wikipedia](https://en.wikipedia.org/wiki/Borsa_Istanbul)
- [List of companies listed on the Borsa Istanbul - Wikipedia](https://en.wikipedia.org/wiki/List_of_companies_listed_on_the_Borsa_Istanbul)

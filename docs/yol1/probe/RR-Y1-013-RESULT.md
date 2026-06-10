# RR-Y1-013 PEAD Fizibilite Probu — Sonuç

> **Bu bir fizibilite probudur, Stage-0 ölçümü DEĞİLDİR.** Hiçbir CAR / getiri /
> drift-büyüklüğü / Sharpe / t-istatistiği hesaplanmadı ve bu raporda yer almaz
> (`no_performance_metrics: true`, probe-JSON'unda makine-okunur olarak kayıtlı).
> Stage-0 kararı bu raporun kapsamı dışında, ayrı bir değerlendirme adımıdır;
> aşağıdaki hükümler otomatik-Stage-0-tetikleyici değildir (DISC-1).
>
> Üretici script: `scripts/probe/pead_feasibility.py` (committed-motor `src/engine/`
> sıfır-dokunuş; tüm girdiler read-only). Ham kanıt: `data/probe/pead_feasibility_summary.json`
> + `data/probe/pead_feasibility_summary.parquet`. Koşu: 2026-06-10 16:57 UTC.

## Genel Hüküm: CONDITIONAL

- **G2 ve G4 PASS, G3 PASS (tercile-only), G1 CONDITIONAL.** Panel ay-çözünürlükte
  bugün kurulabilir; direktifin sabit T+2 (gün-çözünürlük) giriş parametresi ise
  yalnız KAP Katman-2 gün-damgası backfill'i ile uygulanabilir (yol canlı-doğrulandı,
  toplu-çekim yapılmadı).

## Kapı Sonuçları

### G1 (PIT-temizlik): CONDITIONAL — kanıt: ay-çözünürlükte 5/5 KAP spot exact-month + envanter-bütünlüğü 1.000; gün-damgası lokal 0 satır — Panel ay-çözünürlükte inşaat-gereği PIT-temiz, ama frozen T+2 günlük-giriş parametresi gün-damgasız uygulanamaz; KAP Katman-2 backfill yolu bu probe içinde canlı-doğrulandı.

- **Kaynak:** 24.937 kaydın %100'ü `degoran-month-proxy` — duyuru-ayı, aylık degoran
  snapshot'ında net-kârın İLK göründüğü aydır (snapshot-türevli ay-PIT); sağlayıcının
  sonradan-atadığı tarih değildir, KAP gün-damgası da değildir.
- **KAP spot-doğrulaması (bu probe, MKK VYK API, 25 çağrı ≤ 40 bütçe):** 5 farklı
  sembolün (THYAO, ASELS, TUPRS, BIMAS, AKSEN) FY2022 yıllık FR bildirimi KAP
  yayın-tarihi ile panel `announce_month` **5/5 exact-month** eşleşti (örn. THYAO
  KAP 01.03.2023 ↔ panel 2023-03). Örneklem küçük ama RR-046'daki tek-nokta
  doğrulamayı 5 bağımsız isme genişletir; ay-proxy sadakati doğrudan kanıtlandı.
- **Restate-vs-ilk-duyuru:** dedup'suz yeniden-tespitte 27.943 ham step → 24.937
  fiscal-çeyrek; **2.971 çeyrek (%11,9) birden-fazla step-ayı taşıyor**
  (restate/düzeltme/ikinci-set ADAYI, üst-sınır). Frozen panel en-ERKEN step'i tutar
  → **ilk-duyuru inşaat-gereği korunur**; ayrım YAPILABİLİR (KAP spot örnekleminde
  mükerrer aynı-dönem FR bildirimi: 0).
- **Devir-envanteri bütünlüğü:** frozen panel vs bugünkü arşivden yeniden-tespit:
  24.937/24.937 çeyrek birebir bulundu (örtüşme payı **1.000**).
- **Gün-çözünürlük durumu:** lokal KAP cache 0 satır (`kap_fr_*` 4 dosya, hepsi boş);
  hafta-sonu/seans-sonrası → ertesi-seans eşlemesi ay-çözünürlükte UYGULANAMAZ.
  Backfill yolu: `src/data/kap_historical_fetcher.py` (`publication_date` alanı) —
  kimlik mevcut + API canlı (bu probe kanıtladı). Bilinen sınır: KAP 4.0 öncesi
  (disclosureIndex < 538004) html-only → gün-damgası backfill'i pratikte KAP-4.0
  dönemiyle sınırlı; 2009'a kadar tam-geri-doldurma garantili değil.
- **≥%95 KAP-PIT-doğrulanabilirlik barı:** ay-çözünürlükte kanıt lehte (5/5 spot +
  inşaat-gereği snapshot-PIT); gün-çözünürlükte lokal olarak gösterilemez → CONDITIONAL.

### G2 (SUE/muhasebe): PASS — kanıt: 10.131 SUE-tanımlı firma-çeyrek; SUE1-payda kapsamı %98,9; TMS-29 straddle 862 satır (%8,5) izole-edilebilir — SUE1 bugünkü veriyle hesaplanabilir; rejim tek-seri sabit, enflasyon-kırığı mekanik işaretlenebilir.

- **Firma-çeyrek hacmi:** 24.937 olay / 794 sembol → 21.640 decum-ok →
  17.219 UE-tanımlı → **10.131 SUE-tanımlı** (8-çeyrek-pencere + min-6 UE şartını
  geçen; olayların %40,6'sı). G3'ün likit-kesitleri bu havuzdan beslenir ve yeterli
  çıkar (aşağıda) → "≥X firma-çeyrek" şartı fiilen sağlanır.
- **SUE1-paydası (önceki-çeyrek-sonu özkaynak-piyasa-değeri):** degoran aylık mktval
  (D-206 harmonizasyonlu) UE-tanımlı olayların **%98,97'sinde period_end ayında,
  %98,88'inde duyuru-öncesi-son-ayda** mevcut → direktif bölüm-2'deki SUE1 formu
  uygulanabilir (mevcut snapshot trailing-std ölçekler; mktval-ölçekli SUE1'e geçiş
  veri-engelli DEĞİL).
- **TPC vs IFRS:** degoran TEK sağlayıcı-serisidir; iki-finansal-set ayrımı lokal
  veriden YAPILAMAZ — seçim sağlayıcı-sabitidir (tutarlı-uygulanır ama
  denetlenemez). Çift-set/düzeltme imza-istatistiği: G1 multi-step %11,9 (üst-sınır).
  Bilinen sınır olarak kayıtlı; kapı-kırıcı değil çünkü seri kendi-içinde tutarlı.
- **TMS-29 (enflasyon muhasebesi, FY2023'ten itibaren):** UE'nin mevsimsel çifti
  sınırı kestiği straddle-çeyrekler (period_end ∈ [2023-12-31, 2024-12-30]):
  **862 SUE-satırı (%8,5)** — `period_end` ile mekanik işaretlenebilir/dışlanabilir;
  2025+ çeyrekler TMS29-vs-TMS29 (tutarlı çift). Gözlem: TMS-29-dönemi yıllık-rapor
  çeyreklerinde olay-sayısı düşüşü (fy2023Q4 = 101, fy2024Q4 = 152 vs komşu ~200) —
  işaretlendi; neden-teşhisi Stage-0-hazırlık işidir, probe kapsamı değil.

### G3 (etkin-N): PASS (tercile-only) — kanıt: tercile uç-dilimler çeyreklerin %100'ünde ≥5 (min 7, hiç <3 yok); decile %35,7'de ≥5 + 1 çeyrek <3 — PASS barı ("decile VEYA tercile ≥%80 + hiçbiri <3") tercile yolundan sağlandı; decile uygulanamaz.

- **Likit∩SUE-temiz kesit (fy2019–2025, 28 çeyrek):** ortalama **39,0** /
  medyan **35** / min **21** / max **77** isim. (RR-Y1-008'in "~38 likit isim"
  gözlemiyle tutarlı.) Likidite tanımı: motor `liquid_names` (recon B7; RR-Y1-008
  parite) — trailing-63g medyan işlem-değeri ≥ 10M TL, asof = duyuru-ayının son
  işlem-günü (point-in-time).
- **Decile:** üst/alt dilim ortalama 4,2/4,4; min 2; her-iki-uç ≥5 olan çeyrek payı
  **%35,7** (< %80) ve 1 çeyrekte uç-dilim <3 → decile-bazlı sıralama BIST
  likit-evreninde istatistiksel-kapasite taşımaz.
- **Tercile:** üst/alt dilim ortalama 13,4/13,0; min **7**; her-iki-uç ≥5 olan
  çeyrek payı **%100**; hiçbir çeyrekte <3 yok → direktifin tercile-fallback'i
  (Yılmaz et al. 2020 ile uyumlu) tam-kapasiteli.
- **Likidite-dışlama bulgusu (eleme değil):** SUE-tanımlı olayların çeyrek-ortalaması
  **%81,2'si likit-evren DIŞINDA** kalıyor. PEAD-literatürünün drift'i en güçlü
  beklediği küçük/illikit bölge harvest-evreninin dışındadır → ölçüm-paneli driftin
  muhtemelen EN ZAYIF dilimini (likit ~%19) ölçer. Bu, F6/D6 riskinin sayısal halidir
  ve Stage-0 açılırsa ön-kayda yazılmalıdır (beklenti-disiplini).

### G4 (corp-action/delisted): PASS — kanıt: harmonizasyon-sonrası residual mktval-sıçrama oranı %0,07 (62/87.513); delisted 71/73 duyuru-geçmişli; drift-penceresi-içi delist 57 olay fiyat-verisi delist-gününe kadar dolu — corp-action zinciri SUE-paydasını kirletmiyor, survivorship-tarafı bütün.

- **SUE-paydası corp-action zinciri:** D-206 dedektörü 3 piyasa-genel redenominasyon
  kırığı buldu/uyguladı (2009-09, 2009-10, 2026-02 — earnings-snapshot meta'sıyla
  birebir aynı). Harmonizasyon-sonrası residual MoM sıçrama (>5x / <0,2x):
  **62 / 87.513 geçiş (%0,07, üst-sınır** — gerçek bedelli/birleşme mktval'i meşru
  sıçratır; mcap split-nötrdür, payda için hata değildir).
- **clean_universe ca_code çapraz-kontrolü:** 2019+ residual sıçrama 12 adet; 2'si
  aynı/önceki ay ca_code olayıyla örtüşüyor. Kalan 10 vaka (10/~17k 2019+ geçişi)
  marjinal; tekil-vaka teşhisi Stage-0-hazırlığa not edildi.
- **Delisted duyuru-geçmişi:** fiyat-panelindeki 73 delist-adayının (son işlem,
  panel-sonundan ≥60 işlem-günü önce) **71'i earnings-panelinde** ve 71'inin
  kotasyondayken duyurusu var. Earnings-panelindeki 148 sembol fiyat-panelinde yok —
  bunlar 2019-öncesi delist'ler (fiyat-paneli 2019'da başlar; pencere-farkı,
  survivorship-kırpma DEĞİL).
- **Drift-penceresi-içi delisting:** duyuru-sonrası ≤ ~62 işlem-günü içinde susan
  **57 olay (28'i SUE-tanımlı)**. Fiyat-paneli delist-gününe kadar dolu (inşaat-gereği)
  → delist-gününe-kadar-getiri yaklaşımı uygulanabilir; ele-alım kuralı Stage-0
  tasarım-notu olur.

## Etkin-N Tablosu (G3 detay)

Başlık-aralığı **fy2019–2025** (28 çeyrek; likidite-verisi tam). fy2018 satırları
kenar-vakadır (2018Q3 tek-olay; 2018Q4 duyuruları 2019-başı → trailing-likidite
penceresi kısmi) ve özet-istatistiklere dahil DEĞİLDİR.

| Çeyrek | Likit∩SUE-temiz N | Decile üst-dilim N | Decile alt-dilim N | Tercile üst N | Tercile alt N |
|---|---|---|---|---|---|
| 2018Q3* | 0 | 0 | 0 | 0 | 0 |
| 2018Q4* | 32 | 4 | 4 | 11 | 11 |
| 2019Q1 | 21 | 2 | 3 | 7 | 7 |
| 2019Q2 | 26 | 3 | 3 | 9 | 9 |
| 2019Q3 | 28 | 3 | 3 | 10 | 9 |
| 2019Q4 | 33 | 4 | 4 | 11 | 11 |
| 2020Q1 | 41 | 4 | 5 | 14 | 14 |
| 2020Q2 | 44 | 5 | 5 | 15 | 15 |
| 2020Q3 | 49 | 5 | 5 | 17 | 16 |
| 2020Q4 | 49 | 5 | 5 | 17 | 16 |
| 2021Q1 | 31 | 3 | 4 | 11 | 10 |
| 2021Q2 | 22 | 3 | 3 | 8 | 7 |
| 2021Q3 | 30 | 3 | 3 | 10 | 10 |
| 2021Q4 | 30 | 3 | 3 | 10 | 10 |
| 2022Q1 | 28 | 3 | 3 | 10 | 9 |
| 2022Q2 | 35 | 4 | 4 | 12 | 12 |
| 2022Q3 | 51 | 5 | 6 | 17 | 17 |
| 2022Q4 | 40 | 4 | 4 | 14 | 13 |
| 2023Q1 | 33 | 4 | 4 | 11 | 11 |
| 2023Q2 | 46 | 5 | 5 | 16 | 15 |
| 2023Q3 | 43 | 5 | 5 | 15 | 14 |
| 2023Q4 | 22 | 3 | 3 | 8 | 7 |
| 2024Q1 | 35 | 4 | 4 | 12 | 12 |
| 2024Q2 | 35 | 4 | 4 | 12 | 12 |
| 2024Q3 | 37 | 4 | 4 | 13 | 12 |
| 2024Q4 | 29 | 3 | 3 | 10 | 10 |
| 2025Q1 | 42 | 5 | 5 | 14 | 14 |
| 2025Q2 | 59 | 6 | 6 | 20 | 20 |
| 2025Q3 | 77 | 8 | 8 | 26 | 26 |
| 2025Q4 | 75 | 8 | 8 | 25 | 25 |

\* kenar-vaka, başlık-istatistiklerine dahil değil. Tabloda yalnız likit-N gösterildi;
likidite-öncesi tam kırılım (n_sue_all + n_in_price_panel sütunlarıyla; örn. 2025Q4'te
SUE-tanımlı 309 olaydan 75'i likit): `data/probe/pead_feasibility_summary.parquet`.

## Veri-Kaynak Envanteri

| Kaynak | İçerik | Aralık | Filtre/Not |
|---|---|---|---|
| `data/snapshots/earnings_dates.parquet` (+ meta, 2026-06-03 freeze) | RR-046 ASAMA-2a devir-envanteri: duyuru-ayı-proxy + seasonal-SUE; 24.937 satır / 794 sembol | fy2008–2025 | read-only; yeniden-üretilmedi |
| `bist_datastore_archive/fundamental_ratios/degoran*.zip` (committed loader) | aylık mktval + YTD net-kâr; 88.494 satır | 2009-01–2026-04+ | D-206 redenominasyon-harmonizasyonu (3 kırık) |
| `data/clean_universe/adjusted_prices_2019_2026.parquet` (engine `load_panel`) | 681 sembol × 1.848 gün; value_tl, ca_code, delisted-dahil | 2019-01-02–2026-05-26 | likidite + delist tespiti; **tr_index/getiri sütunları KULLANILMADI** |
| Motor `liquid_names` (recon B7) | 10M-TL trailing-63g medyan işlem-değeri floor'u | per-duyuru-ayı asof | RR-Y1-008 parite; import read-only |
| MKK VYK KAP API (opsiyonel spot) | 5 sembolün FY2022 FR yayın-tarihi | 25 çağrı (≤40 bütçe) | yalnız G1 kanıtı; toplu-çekim YAPILMADI; ham-veri CI'a girmedi |

## Bilinen Sınırlar / Uyarılar

1. **KAP spot-örneklemi küçük (5 detay) ve tek-döneme yığılı (FY2022 yıllıklar)** —
   API'nin disclosure-listeleme sayfalaması ilk-sayfayı döndürdü; ara-çeyrek ve
   küçük-isim doğrulaması Katman-2'ye kaldı. ≥%95 barı ay-bazında lehte-kanıtlı,
   İSPATLANMIŞ değil.
2. **Gün-çözünürlük yokluğu T+2'yi bloke eder** (G1 CONDITIONAL'ın özü): ay-proxy ile
   en-erken look-ahead-safe tüketim `announce_month+1`'dir; T+2-giriş/60g-tutuş
   literatür-parametresi ancak KAP Katman-2 backfill sonrası birebir uygulanabilir.
   KAP 4.0 öncesi html-only → 2009'a tam-geri-doldurma garanti değil.
3. **Tek-sağlayıcı muhasebe-serisi:** TPC/IFRS set-seçimi denetlenemez (G2 notu);
   multi-step %11,9 üst-sınır imzası dışında çift-set etkisi ölçülemez.
4. **Nominal-TL SUE 2021–2024 enflasyon-dönemini taşır** (devir-envanteri caveat'i);
   real-deflasyon/ölçekleme Stage-0 tasarım-seçimidir, burada uygulanmadı.
5. **Likidite-dışlama %81** — ölçülebilir panel likit-dilimle sınırlı; PEAD'in
   illikit-yoğun literatür-profiline göre bu panel drift'in alt-sınırını ölçer
   (bulgu; Stage-0 açılırsa ön-kayıt beklentisine yazılmalı).
6. **Probe kapsam-dışı bıraktıkları:** decay-riski (Stage-0-içi ölçüm sorusu),
   maliyet (D-207 çağrılmadı), benchmark-inşası (FF-tarzı eşleştirme Stage-0 tasarımı),
   2023Q4/2024Q4 olay-sayısı düşüşünün kök-nedeni.

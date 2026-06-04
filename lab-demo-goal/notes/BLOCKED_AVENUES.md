# BLOCKED / UNEXAMINED AVENUES -- veri-eksikligi veya manuel-auth nedeniyle BAKILMAYAN evrenler

Tarih: 2026-06-04. Otonom-faz `lab-demo-goal/` icinde eldeki-veriyle (fiyat/hacim/fundamental/
membership/macro/earnings-aylik) cross-sectional + event edge alanini TUKETTI (L1-L15, FF5-tam).
Asagidaki yollar deger-tasiyabilir AMA otonom-fazda KAPALI kaldi: ya BIZDE-OLMAYAN veri-turu
gerektiriyor, ya da the maintainer'in MANUEL ag/auth islemi gerektiriyor. Hicbiri otonom-cekilemez
(repo READ-ONLY + ag-pull the maintainer-onayina kapali). Burasi tek-bakista "neden bakilamadi + ne gerekir"
kaydidir. Oncelik-gerekce: [FORWARD_DATA_SPEC.md]; go/no-go karti: [FORWARD_DECISION_CARD.md].

Etiket: [DATA-GAP] = veri-turu bizde yok/uretilemez. [MANUEL-AUTH] = the maintainer ag/login/onay-fetch lazim.
[SERVER-BLOK] = kaynak sunucu tarafindan erisime kapali (client-fix imkansiz).
[ARSIV-MEVCUT] = veri LOKAL offline arsivde BULUNDU; ag-fetch GEREKMEZ, otonom-fazda kosulabilir.

---

## VERI-DURUMU DUZELTMESI (2026-06-04) -- onceki [DATA-GAP] beyanlari KISMEN YANLIS

Otonom-faz sirasinda `data/bist_datastore_archive/` LOKAL offline arsivi kesfedildi (gitignored, ag-fetch
GEREKMEDEN okunabilir). Bu, asagidaki birkac yolun "veri bizde yok" on-beyanini FALSIFIE eder. Mevcut
olanlar: `viop` (927M, 2005-2026; gunluk settlement/OHLC/VWAP/traded-value + acik-pozisyon, XU030 vadeli
en-likit + likit buyuk-cap single-stock-futures alt-kumesi), `short_selling` (aylik per-stock acial-satis-TL,
92 dolu-ay 2015-2026, yasak-bosluklariyla), `foreign_flow` (18M, 1997-2026), `fundamental_ratios`
(23M, 1995-2026), `prices_official`/`prices_weekly`. HALA-BOS (dogru-bicimde bloke): `corporate_actions`,
`dividends`, `index_components`.

SONUC: short-selling ekseni L19'da GERCEK-veride test edildi (SHORT-INTENSITY-NOT-TRADEABLE, asagi).
VIOP/foreign-flow/fundamental-ratios artik otonom-kosulabilir [ARSIV-MEVCUT]; sentiment/NLP icin tarihsel
metin-corpus HALA yok (yalniz snapshot) -> L16/L17 scaffold'lari acildi ama gercek-test icin metin-fetch lazim.
Asagidaki ilgili maddeler bu duzeltmeye gore guncellendi.

---

## #1 DAILY-PEAD -- gunluk kazanc-ilan-zaman-damgali surprise drift  [MANUEL-AUTH]
- NEDEN bakilamadi: PEAD'i deploy-edilebilir kilan tek-cozunurluk GUNLUK ifsa-zaman-damgasi (KAP
  publication_date). Bizde yalniz AYLIK earnings-panel var -> L3 aylik-cozunurlukte elendi (drift
  monthly-attenuation'da kayboluyor). L8-L13 bunun TEK power-ulasilabilir forward-sinif oldugunu
  sayisal gosterdi (band ~1-8 yilda |t|=2).
- NE GEREKIR: `kap_historical_fetcher` (schema'da `publication_date` ZATEN var ama cache'ler BOS) ile
  ONAYLI tek-seferlik ag-fetch -> `data/cache/kap_pead_daystamped.parquet` [symbol, publication_date,
  fiscal_year, quarter, sue]. Yeni-scraper DEGIL; mevcut-fetcher'i the maintainer-onayli kosturmak.
- HAZIR-DURUM: on-kayitli + offline-dogrulanmis harness HAZIR (`harness/l11_forward_daily_pead.py`;
  panel gelince sentetik-self-test'ten gercek-teste OTO-gecer, kod-degisimi YOK). AMA AYIK-marj
  (L13: olculmus aylik-sinyal maliyet-tabanini ancak-ancak karsilar) -> fetch NULL donebilir
  (tek-makul-bahis, kesin-kazanc DEGIL).

## #2 SURPRIZ-KOSULLU MAKRO -- CPI actual-vs-forecast surprise  [DATA-GAP]
- NEDEN bakilamadi: makro-panelimiz yalniz olay-TARIHI tasiyor; SURPRIZ-bileseni (actual/forecast veya
  consensus) YOK. L6/L12: kosulsuz CPI-penceresi en-guclu leg post[+1,+5] +61bp ama t=1.48 SIGN-UNSTABLE
  -> driftin yon-tutarliligini saglayacak surprise-kosullamasi OLCULEMIYOR (offline veri yok).
- NE GEREKIR: kesin-CPI-ilan-tarihi + actual + consensus-forecast tarih-serisi (ucretsiz/ucretli
  makro-takvim API). PPK-gecmisi de (n cok-dusuk -> cikarildi). Offline-uretilemez.
- HAZIR-DURUM: rationale-quantified (L12: |t|=2 icin ~1.15x/10yr surprise-carpani yeter -> darbogaz
  MAGNITUDE-degil SIGN-COHERENCE). #1'in ALTINDA siralanir; data-gated.

## #3 TEFAS FON-AKIMI + YATIRIMCI-SAYISI -- retail/kurumsal akim proxy  [MANUEL-AUTH]
- NEDEN bakilamadi: hic-denenmemis ayri-cekim-isi; eldeki-veride YOK. Retail/kurumsal fon-akimi ve
  yatirimci-sayisi (5 yil, ucretsiz TEFAS) potansiyel-yeni sinyal-kaynagi (L5 web-sentez onerdi).
- NE GEREKIR: TEFAS'tan yeni-build cekim-hatti (ag-fetch + parse + panel-insa). the maintainer-onayli kosum.
- HAZIR-DURUM: spec-asamasinda; harness yok. FORWARD_DATA_SPEC #3.

## #4 YABANCI-AKIM -- per-stock foreign-flow timing  [ARSIV-MEVCUT] (onceki [MANUEL-AUTH+DATA-GAP] DUZELTILDI)
- DUZELTME: `data/bist_datastore_archive/foreign_flow` (18M, 1997-2026) LOKAL MEVCUT -> "tarihsel-panel
  uretilemez" on-beyani YANLIS. Ag-fetch GEREKMEZ; otonom-kosulabilir.
- ACIK-KALAN: arsivin tam-semasi (gunluk-mu/per-stock-mu, alan-tanimlari) HENUZ dogrulanmadi; D-211
  foreign-flow index-timing zaten kapali (graveyard) -> bu cross-sectional/per-stock varyant icin
  prior ZAYIF. Bir track acilmadan once sema-dogrulama + Stage-0-on-kayit gerekir.
- HAZIR-DURUM: veri-engeli KALKTI; track acilabilir (otonom). Onceki "ucretli/forward-snapshot" gerekce gecersiz.

## #5 KURUMSAL-AKSIYON (corp-action) VERI-KAYNAGI -- DataStore  [SERVER-BLOK]
- NEDEN bakilamadi: DataStore uzerinden corp-action veri-turleri (100460/461/462/471/3184) sunucu
  basket-whitelist'inde DEGIL; dogrudan /api/file/ de 404. Client-fix IMKANSIZ -> bu kanaldan
  corp-action verisi ERISILEMEZ. (auto-memory: datastore_basket_whitelist; ayrica `--since` epoch-filter
  3196/3153 icin 0 donuyor -> tam-katalog cekilmeli.)
- NE GEREKIR: alternatif corp-action kaynagi (baska saglayici/manuel-export) veya sunucu-tarafi-degisiklik.
  Bu lab-disi bir veri-erisim cikmazidir; burada yalniz REFERANS icin kayitli.
- HAZIR-DURUM: arastirildi -> dead-end (RR-042 / docs/research). Lab-edge'i icin engelleyici-degil
  (eldeki adjusted_prices ca_code zaten tasiyor); kapsamli-corp-action-veri icin engelleyici.

## #6 ANALIST-REVIZYON / KONSENSUS-TAHMIN -- forward EPS revisions  [DATA-GAP]
- NEDEN bakilamadi: analist-revizyon momentum'u (literaturde guclu) konsensus-tahmin tarih-serisi
  gerektirir; bizde YOK ve ucretsiz-tarihsel-kaynak yok (genelde paywalled/forward-snapshot).
- NE GEREKIR: tarihsel konsensus-EPS revizyon-akisi (ucretli) veya bugun-baslayan forward-snapshot.
- HAZIR-DURUM: L5-sentezde "forward-snapshot gerektirir" diye isaretli; spec-disi, dusuk-oncelik.

## #7 SENTIMENT -- haber/sosyal-medya duyarlilik faktoru  [DATA-GAP] (L16 SCAFFOLD acildi)
- NEDEN gercek-test bakilamadi: tarihsel-backtest icin GUN-GUN per-stock duyarlilik-skoru paneli gerekir.
  Bizdeki `data/sentiment_cache.json` PRATIKTE BOS, `data/news_cache.json` ise yalniz ~22KB ANLIK-snapshot
  (son birkac haftalik baslik; gecmis-derinlik YOK, duyarlilik-etiketi YOK). Backtestable tarihsel-panel DEGIL.
- DUZELTME: artik "hic-track-acilmadi" DEGIL -- L16 forward-scaffold acildi (`harness/l16_*`,
  on-kayitli Stage-0 + sentetik self-test PASS + snapshot-karakterizasyon). Panel gelince oto-gercek-teste gecer.
- NE GEREKIR (gercek-run): tarihsel haber-corpus (cok-yillik) + her-haber-gun duyarlilik-skorlama -> ag-fetch +
  saklama + NLP-skorlama hatti (the maintainer-onayli). Offline-uretilemez. Haber-akisi cogu KAP-ifsa -> #1 PEAD ile ortusur.

## #8 NLP / METIN-MADENCILIGI -- KAP-ifsa/haber metin-tabanli sinyal  [DATA-GAP] (L17 SCAFFOLD acildi)
- NEDEN gercek-test bakilamadi: #7 ile ayni kok-sebep -- tarihsel-metin-corpus YOK; gun-damgali tarihsel
  KAP/haber tam-metni gerekir, elimizde yalniz anlik-baslik snapshot var.
- DUZELTME: artik "hic-track-acilmadi" DEGIL -- L17 forward-scaffold acildi (`harness/l17_*`, ifsa-TIPI
  taksonomisi + Bonferroni cok-test-kontrolu + sentetik self-test PASS + snapshot-tip-dagilimi). Panel gelince oto-gecer.
- NE GEREKIR (gercek-run): tarihsel KAP-ifsa tam-metin arsivi (gun-damgali) + NLP-pipeline. Ag-fetch, the maintainer-onayli.
  #1/#7 ile ayni fetch-altyapisina baglanir (KAP-gun-damgasi cekirdek).

## #9 VIOP / TUREVLER -- vadeli-opsiyon tabanli faktorler  [ARSIV-MEVCUT] (onceki [DATA-GAP] DUZELTILDI; L18 SCAFFOLD)
- DUZELTME: "VIOP verisi BIZDE HIC YOK" on-beyani FALSIFIE -- `data/bist_datastore_archive/viop` (927M,
  2005-2026) LOKAL MEVCUT: per-kontrat gunluk settlement/OHLC/VWAP/traded-value + ACIK-POZISYON,
  XU030 vadeli en-likit kontrat + likit buyuk-cap single-stock-futures alt-kumesi (AKBNK/EREGL/BIMAS...).
  Onceki "cross-sectional single-stock VIOP infeasible" iddiasi da KISMEN-revize (likit alt-kume var).
- ACIK-KALAN (gercek-run icin): index-basis overlay icin INSA-EDILMIS bir baz-paneli lazim (front-month
  XU030 vadeli settlement + gunluk SPOT XU030 seviyesi hizalanmis). Bu bir LOKAL-BUILD'tir, ag-fetch DEGIL.
- HAZIR-DURUM: L18 forward-scaffold acildi (`harness/l18_*`, on-kayitli + sentetik self-test PASS,
  arsiv-envanteri + premise-falsifikasyonu kayitli). VIOP veri-engeli KALKTI; overlay'in gercek-run'i
  baz-paneli-build + the maintainer-go-ahead bekler (timing-overlay -> foreign-flow-bitisigi, prior ZAYIF).

## #10 SHORT-SELLING-INTENSITY -- short-konumlanma cross-sectional  [ARSIV-MEVCUT] -> L19 KOSULDU (NOT-TRADEABLE)
- DURUM: `data/bist_datastore_archive/short_selling` LOKAL MEVCUT (aylik per-stock acial-satis-TL, 92 dolu-ay
  2015-2026). GERCEKTEN-YENI eksen (short-selling positioning); L1-L18 graveyard'da yok.
- SONUC: L19 GERCEK-veride test edildi -> SHORT-INTENSITY-NOT-TRADEABLE (significance/sign-duvari + LIQUID
  rejim-instabilitesi; cost-duvari degil). Detay: `notes/L19_short_sale_intensity_REPORT.md`. Graveyard'a temiz-eklendi.
- HAZIR-DURUM: KAPANDI (deploy-iddiasi yok). Yapisal-engeller (short-yasagi-bosluklari, modern thin shortable
  evren, aylik-granularite) ON-BEYAN dogrulandi.

---

## OZET (the maintainer icin) -- 2026-06-04 guncel
- OTONOM-OFFLINE faz icin BLOKE-EDICI yok: cross-sectional/event edge alani eldeki-veriyle tuketildi
  (L1-L15 FF5-tam) + sentiment/NLP/VIOP scaffold'lari (L16/L17/L18) + short-selling GERCEK-test (L19).
- VERI-DURUMU DUZELDI: `data/bist_datastore_archive/` kesfi sayesinde VIOP (#9) + foreign-flow (#4) +
  fundamental-ratios + short-selling (#10) artik LOKAL-MEVCUT [ARSIV-MEVCUT] -> ag-fetch GEREKMEDEN
  otonom-kosulabilir. short-selling kosuldu (L19, NOT-TRADEABLE). HALA-eksik: sentiment/NLP tarihsel
  metin-corpus (#7/#8) + corporate_actions/dividends/index_components (arsivde HALA BOS).
- GERCEK [DATA-GAP]/[MANUEL-AUTH] kalan: #1 DAILY-PEAD (KAP gun-damgali fetch), #2 makro-surprise,
  #3 TEFAS, #6 analist-revizyon, #7 sentiment-corpus, #8 NLP-metin-corpus. Bunlar ag/auth bekler.
- EN-YUKSEK getiri/hazirlik orani DEGISMEDI: #1 DAILY-PEAD (harness on-kayitli + calistirilabilir).
  Karar destegi: [FORWARD_DECISION_CARD.md].
- OTONOM-KOSULABILIR yeni-isler (ag-fetch GEREKMEZ, [ARSIV-MEVCUT]): foreign-flow cross-sectional (#4,
  zayif-prior), fundamental-ratios genis-oran-supurmesi, VIOP index-basis overlay (#9, once LOKAL baz-paneli
  build: front XU030 vadeli + spot XU030 hizalama). Hepsi sema-dogrulama + Stage-0-on-kayit ister.

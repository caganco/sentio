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

SONUC: short-selling ekseni L19'da GERCEK-veride test edildi (SHORT-INTENSITY-NOT-TRADEABLE, asagi),
per-stock foreign-flow ekseni L20'de GERCEK-veride test edildi (FOREIGN-FLOW-XS-NOT-TRADEABLE, #4) ve VIOP
futures open-interest cross-sectional ekseni L21'de GERCEK-veride test edildi (VIOP-OI-XS-NOT-TRADEABLE, #9).
VIOP index-basis overlay + fundamental-ratios HALA otonom-kosulabilir [ARSIV-MEVCUT] ama prior-zayif;
sentiment/NLP icin tarihsel metin-corpus HALA yok (yalniz snapshot) -> L16/L17 scaffold'lari acildi ama
gercek-test icin metin-fetch lazim. Asagidaki ilgili maddeler bu duzeltmeye gore guncellendi.

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

## #4 YABANCI-AKIM -- per-stock foreign-flow cross-sectional  [ARSIV-MEVCUT] -> L20 KOSULDU (NOT-TRADEABLE)
- DUZELTME: `data/bist_datastore_archive/foreign_flow` (351 aylik .xls, 1997-2026) LOKAL MEVCUT -> "tarihsel-panel
  uretilemez" on-beyani YANLIS. Ag-fetch GEREKMEZ; otonom-kosuldu.
- SEMA-DOGRULANDI: legacy OLE2 .xls (xlrd), sheet 'TURKCE', per-stock satir: col0=sembol(.E), col3=ALIS-TL,
  col6=SATIS-TL; market-segment basliklari col1'de (atlanir). Sema 2019/2021/2023/2026'da stabil; evren 367->606.
  Yani veri PER-STOCK + aylik -> cross-sectional test MUMKUN (D-211 aggregate index-timing'den AYRI).
- KOSULDU (L20): imbalance=(alis-satis)/(alis+satis), HIGH=LONG, LIQUID, market-relative net, NW-t lag6, rejim,
  m+1+skip-m+2; 2019-01..2026-04 (87 ay). SONUC: deploy-kapisi (LIQUID HIGH m+1) net -0.10%/ay t=-0.35,
  rejim-INSTABIL -> FOREIGN-FLOW-XS-NOT-TRADEABLE. ALL m+1 long-bacak t=2.03 ama L-S-spread ~0/U-bicim microcap-
  artefakti (gate disinda). ON-BEYAN edilen zayif-prior dogrulandi (es-zamanli-co-move forward'a tasinmiyor).
- HAZIR-DURUM: KAPANDI (gercek-veride test edildi, temiz-arsiv). [L20_foreign_flow_xs_REPORT.md]

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

## #9 VIOP / TUREVLER -- vadeli-opsiyon tabanli faktorler  [ARSIV-MEVCUT] (L18 BASIS-SCAFFOLD; L21 OI-XS KOSULDU; L22 TERIM-YAPISI KOSULDU; L23 PER-STOCK-BASIS KOSULDU)
- DUZELTME: "VIOP verisi BIZDE HIC YOK" on-beyani FALSIFIE -- `data/bist_datastore_archive/viop` (927M,
  2005-2026) LOKAL MEVCUT: per-kontrat gunluk settlement/OHLC/VWAP/traded-value + ACIK-POZISYON,
  XU030 vadeli en-likit kontrat + likit buyuk-cap single-stock-futures alt-kumesi (AKBNK/EREGL/BIMAS...).
  Onceki "cross-sectional single-stock VIOP infeasible" iddiasi da KISMEN-revize (likit alt-kume var).
- L21 KOSULDU (open-interest cross-sectional): SSF (tek-hisse-futures) ACIK POZISYON kullanilarak
  oi_growth=total_OI(m)/total_OI(m-1)-1 cross-sectional tercile test edildi (HIGH=LONG, LIQUID-spot,
  market-relative net, m+1+skip-m+2; 89 ay / 63 dayanak). Fizibilite ON-CHECK: ay-sonu pozitif-OI SSF
  medyan 48 / min 30 -> FIZIBIL (L18-tipi blok DEGIL); 63/63 dayanak spot-panelde. SONUC: deploy-kapisi
  (LIQUID HIGH m+1) net -1.04%/ay t=-5.13 ama TEZ-TERSI/NEGATIF -> keep-bar net>0 GECMEZ + rejim-INSTABIL.
  Baskin desen crowding-reversal (LIQUID L-S t=-3.81, ALL L-S t=-2.46 rejim-stabil-negatif) AMA on-kayit-DEGIL
  + m+2'de coker (t=-0.99) + LIQUID kisa enflasyon-penceresi (2021-12..2026-04) -> iki-yonlu hukumle
  VIOP-OI-XS-NOT-TRADEABLE. Reversal AYRI gelecek-track adayi olarak loglandi (the maintainer-mandasi + taze Stage-0 +
  m+2-survival + rejim-stabilite + gercekci short-maliyeti gerekir). [L21_viop_oi_xs_REPORT.md]
- INDEX-BASIS/TERIM-YAPISI ekseni L22'de KOSULDU -> VIOP-TS-FEASIBILITY-BLOCKED: BIST30 index-futures
  (INF segment, F_XU030MMYY) terim-yapisi egimi GERCEK-olculdu (111 ay-sonu/2017-03..2026-05; kalici
  dik-contango medyan +19.2%/yil, %98.2 contango). AMA deploy-edilebilir index-timing edge OFFLINE kurulamaz,
  IKI baglayici-kisit: (a) TEMIZ tez-testi (slope -> SPOT XU030 getiri) DATA-BLOCKED -- temiz gunluk/haftalik
  spot XU030 SEVIYESI 2017-2026 lokal-YOK [prices_official 'BIST 30 INDEX' kolonu var ama arsiv 2016-11'de
  biter -> futures-doneminde 0 ortusme; prices_weekly per-hisse OHLC, endeks-seviye-yok; exposure xu100
  yanlis-endeks; adjusted_prices'tan divisor-rekonstruksiyon float-hatasi-riskli]; (b) tek offline-varyant
  (slope -> futures KENDI ileri-getirisi) roll-down ile MEKANIK-confounded (~ -slope*dt) ve ZATEN istatistiksel
  ANLAMSIZ [naif slope NW-t=-1.08, carry-soyulmus rezidu NW-t=-0.97, ikisi de |t|<2; roll-down suruklemesi
  isaret-var ama kucuk, corr +0.12]. slope-TLREF korr (2019+) -0.17 zayif -> egri carry/gurultu-domine.
  L18'in acik-biraktigi index-basis ekseni DURUSTCE KAPANDI; spot-basis = harici-gunluk-SPOT-XU030 gerektiren
  the maintainer-kapili ILERI-aday loglandi. [L22_viop_term_structure_REPORT.md]
- PER-STOCK FUNDING-BASIS ekseni L23'te KOSULDU -> VIOP-SS-BASIS-XS-NOT-TRADEABLE. L22'nin index-basisinin
  TAMAMLAYICISI ama KRITIK FARK: spot-bacak burada OFFLINE-VAR (ham `close`) -> L22'yi data-bloklayan tam-leg
  MEVCUT, yani bu GERCEK olculmus-null, feasibility-blok DEGIL. SSF segment, en-yakin-vade uzlasma fiyatinin
  ham-spota yillik primi: basis_ann=ln(F_front.settle/S_raw_close)/(dte/365), F_front=dte>=10 en-kucuk-vade,
  TEK on-kayitli tanim; 89 ay/63 dayanak/3906 baz-gozlem/2019-01..2026-05. Tanimlayici: medyan +29.2%/yil
  %93.9 contango -> SEVIYE TL-carry-domine (NOT temettu-getiri ~0.02-0.05), tercile-rank ortak-carry'yi soyar.
  ON-KAYITLI NEGATIF isaret (yuksek-basis=zengin-future/kalabalik-long/pahali-short -> spot UNDERperform) ->
  LONG=DUSUK-basis tercile. SONUC: PRIMARY (LIQUID DUSUK m+1) market-relative net -0.14%/ay NW-t=-0.36 ANLAMSIZ
  + rejim-INSTABIL -> uc-kosul-UCU-DE GECMEZ. ALL DUSUK-bacak GUCLU-ANLAMLI NEGATIF (NW-t=-3.21 m+1 / -3.38 m+2)
  = TEZIN-TAM-TERSI (zengin-future-continuation ve/veya Q2-temettu-takvim seasonal'i DUSUK-basis-bacagi kirletiyor)
  -> iki-yonlu hukumle CLAIM-EDILMEZ, opposite-sign ayri gelecek-track loglandi. Per-stock funding-basis ekseni
  DURUSTCE KAPANDI. [L23_viop_ss_basis_REPORT.md]
- HAZIR-DURUM: L18 basis-overlay forward-scaffold acildi (`harness/l18_*`, sentetik self-test PASS) -> L22
  bunu index-seviyede GERCEK-olcume cevirdi ve index-basis ekseni KAPATTI (feasibility-blocked, spot-bacak
  offline-yok); L23 per-stock-seviyede GERCEK-olctu (spot-bacak offline-VAR) ve per-stock-basis ekseni KAPATTI
  (olculmus-null); L21 OI-cross-sectional GERCEK-veride KOSULDU ve KAPANDI (NOT-TRADEABLE). VIOP acik-pozisyon +
  terim-yapisi + per-stock-funding-basis eksenlerinin tumu artik ON-KAYITLI ve test-edildi.

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
  (L1-L15 FF5-tam) + sentiment/NLP/VIOP-basis scaffold'lari (L16/L17/L18) + short-selling GERCEK-test (L19) +
  per-stock foreign-flow GERCEK-test (L20) + VIOP futures open-interest GERCEK-test (L21) + VIOP index-futures
  terim-yapisi GERCEK-olcum (L22 -> feasibility-blocked) + VIOP per-stock funding-basis GERCEK-test
  (L23 -> olculmus-null, spot-bacak offline-VAR).
- VERI-DURUMU DUZELDI: `data/bist_datastore_archive/` kesfi sayesinde VIOP (#9) + foreign-flow (#4) +
  fundamental-ratios + short-selling (#10) artik LOKAL-MEVCUT [ARSIV-MEVCUT] -> ag-fetch GEREKMEDEN
  otonom-kosulabilir. short-selling (L19) + foreign-flow cross-sectional (L20) + VIOP open-interest
  cross-sectional (L21) + VIOP per-stock funding-basis cross-sectional (L23) KOSULDU = dordu de NOT-TRADEABLE;
  VIOP index-futures terim-yapisi (L22) GERCEK-olculdu = VIOP-TS-FEASIBILITY-BLOCKED (temiz spot-bacak 2017-2026
  offline-YOK + roll-down confound, ZATEN anlamsiz). L23 KRITIK FARK: per-stock spot-bacak L22'nin tersine
  OFFLINE-VAR -> GERCEK olculmus-null, feasibility-blok DEGIL.
  HALA-eksik: sentiment/NLP tarihsel metin-corpus (#7/#8) + corporate_actions/dividends/index_components
  (arsivde HALA BOS) + temiz gunluk SPOT XU030 seviye-serisi 2017-2026 (L22 spot-basis-gercek-test icin).
- GERCEK [DATA-GAP]/[MANUEL-AUTH] kalan: #1 DAILY-PEAD (KAP gun-damgali fetch), #2 makro-surprise,
  #3 TEFAS, #6 analist-revizyon, #7 sentiment-corpus, #8 NLP-metin-corpus, + spot-XU030-level (L22-gated). ag/auth bekler.
- EN-YUKSEK getiri/hazirlik orani DEGISMEDI: #1 DAILY-PEAD (harness on-kayitli + calistirilabilir).
  Karar destegi: [FORWARD_DECISION_CARD.md].
- OTONOM-KOSULABILIR offline-kuyruk (graveyard-disi) artik TUKENDI: gercekten-yeni offline-touchable eksenlerin
  tumu (short L19, foreign-flow L20, VIOP-OI L21, VIOP index-TS L22, VIOP per-stock-basis L23) kosuldu; kalan
  tek-sey fundamental-ratios genis-oran-supurmesi = TEK-tanim-otesi grid = p-hacking (YASAK; FF5 value/quality/
  investment zaten L14/L15/mezarlikta). VIOP index-basis overlay (#9) L22'de KOSULDU ve feasibility-blocked.
  (foreign-flow #4 L20'de, VIOP open-interest #9 L21'de, VIOP per-stock funding-basis #9 L23'te KAPALI.)
  Yeni offline-edge icin YENI-VERI-TURU gerekir.

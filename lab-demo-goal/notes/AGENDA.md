# lab-demo-goal -- otonom edge-kesif AR-GE ajandasi

Amac: yeni edge adaylari + yeni faktor + yeni veri turleri. Production repo READ-ONLY;
tum is bu dizinde. Mevcut disiplinli olcum cercevesini REUSE: gercekci maliyet (D-207
quoted-primary, ~28-42bp likit round-trip), likit-evren (ADV>=1e7 TL), NW-t (HAC), rejim
split (2022-01), Stage-0 ON-KAYIT (sonuctan once dondur), DURUST beklenti (kutlama-yok),
anlamlilik-vs-maliyet duvari ayrimi, look-ahead-safe ZORUNLU, ASCII.

## Onceki program durumu (graveyard -- TEKRAR TEST ETME)
- Cross-sectional fiyat/hacim faktorleri: value (SERAP), momentum/EDGE-2 (gercek ama daralan),
  hi52 (anlamlilik-duvari, D-208), lowvol63 (SERAP), value-rejim-kolu (elendi). 3/3 kapali.
- Time-series: NAV-iskonto-MR holding (SERAP, D-206).
- Event: dividend pre-ex run-up H2b (anlamlilik-duvari, D-209, KAPANDI).
- Quality/profitability: ROE (L14, SIGNIFICANCE/SIGN-duvari -- brut zaten negatif, kalite-primi YOK).
- Investment/asset-growth: equity-growth proxy (L15, SIGNIFICANCE/SIGN-duvari -- deploy-formunda prim YOK).
- Short-selling positioning: short-intensity (L19, GERCEK-veri; SIGNIFICANCE/SIGN-duvari + LIQUID rejim-
  instabilitesi; LOW-tercile yanlis-isaret). KAPANDI.
- Foreign-flow per-stock cross-sectional: imbalance (L20, GERCEK-veri; LIQUID HIGH-tercile m+1 net -0.10%/ay
  t=-0.35, rejim-INSTABIL; ALL-long-bacak t=2.03 ama L-S-spread~0/U-bicim microcap-artefakti, gate-disinda;
  D-211 index-timing'den AYRI). KAPANDI.
- VIOP futures open-interest cross-sectional: oi_growth (L21, GERCEK-veri; LIQUID HIGH-tercile m+1 net -1.04%/ay
  t=-5.13 ama TEZ-TERSI/NEGATIF -> keep-bar net>0 GECMEZ; baskin crowding-reversal-izi on-kayit-DEGIL + m+2-coker
  + LIQUID rejim-INSTABIL + kisa enflasyon-penceresi). KAPANDI.
- VIOP BIST30 index-futures terim-yapisi: term-structure slope (L22, GERCEK-veri; 111 ay-sonu kalici contango
  medyan +19.2%/yil ama deploy-edge OFFLINE kurulamaz -> VIOP-TS-FEASIBILITY-BLOCKED: temiz tez-testi
  slope->SPOT-XU030-getiri icin spot XU030 SEVIYESI 2017-2026 lokal-YOK + tek offline-varyant roll-down-confounded
  ve zaten anlamsiz [naif NW-t=-1.08, carry-soyulmus NW-t=-0.97]). KAPANDI (index-basis ekseni).
- ANA DERS: cogu gorunur-edge illikit-microcap'te yasiyor, likit-evrende gercekci-maliyet
  sonrasi kayboluyor. Likit-evren + ~30-40bp maliyet = gercek test.

## Eldeki veri (lokal, dogrulandi inv-01)
- adjusted_prices_2019_2026.parquet: 681 sembol, 2019-01..2026-05, 1848 gun. close, vwap,
  value_tl, volume, bist100/bist30 (uyelik bayragi), ca_code, adjusted_close/vwap,
  tr_index_gross/net. (VWAP + traded-value VAR.)
- d207_quoted_spread_panel.parquet: 440 sembol quoted spread (maliyet).
- fundamentals_2019_2026.parquet: aylik, 677 sembol: mktval, net_profit, equity, net_div,
  pe, pbv, dy, ey, bm, dyld.
- pit_membership_2019_2026.parquet: date x symbol, in_bist100 + in_bist30 (POINT-IN-TIME).
  -> INDEX-REBALANCE event study (DOKUNULMAMIS).
- earnings_dates.parquet: 794 sembol, SUE (59% NaN), announce_month/consume_from_month
  (look-ahead-safe), degoran-month-proxy. -> PEAD (aylik cozunurluk).
- macro_event_dates.parquet: 90 olay (CPI + PPK), event_date/reference_period/exact.
- trend_v1_ohlcv: 89 sembol full OHLCV (gap/range studies, ama dar evren).
- exposure: gold_tl (2023+), tlref, tufe, xu100 (2019+).

## Aday kuyrugu -- TAMAMLANDI (L1-L22; bkz SUMMARY.md)
- L1 INDEX-REBALANCE (pit_membership) -> INDEX-EFFECT-VIEW (deploy-degil). [TAMAM]
- L2 SHORT-TERM REVERSAL (1w/1m) -> NOT-TRADEABLE (yanlis-isaret + maliyet-duvari). [TAMAM]
- L3 PEAD (aylik SUE) -> NOT-TRADEABLE (anlamlilik+maliyet duvari; aylik-cozunurluk dersi). [TAMAM]
- L4 CALENDAR/SEASONALITY -> DESCRIPTIVE-VIEW (temiz multiple-testing null). [TAMAM]
- L5 WEB SENTEZ -> yeni-veri-kuyrugu + oncelik (FORWARD_DATA_SPEC). [TAMAM]
- L6 MACRO-EVENT (CPI-ilan) -> DESCRIPTIVE-VIEW (significance-wall + veri-tavani). [TAMAM]
- L7 FEASIBILITY-FRONTIER (sentez) -> DESCRIPTIVE-SYNTHESIS (0/20 NO-WALL; iki-kapi go/no-go). [TAMAM]
- L8 POWER/SAMPLE-SIZE (sentez) -> DESCRIPTIVE-POWER-VIEW (olay-kitligi darbogaz; daily-PEAD
  tek-ulasilabilir; FORWARD_DATA_SPEC #1>>#2>>index-rebalance sayisal-gerekce). [TAMAM]
- L9 PEAD-VOLUME (sentez) -> DESCRIPTIVE-VOLUME-VIEW (gercek likit ~136 olay/yil, %19 likit;
  bounded ~95 date-cluster/yil; L8'in ~120/yil varsayimini ~1.3x icinde dogrular). [TAMAM]
- L10 PEAD-EFFECT (sentez) -> MAGNITUDE-FEASIBILITY-VIEW (olay-seviyesi LIKIT SUE +0.69%/ay ama
  ANLAMSIZ t=0.64; |t|=2 icin ~2-5.5x recovery; isaret-engeli YOK; gunluk-pencere etkisi offline-olculemez). [TAMAM]
- L11 FORWARD-SCAFFOLD (on-kayit+offline-dogrulama) -> SCAFFOLD-SELF-TEST PASS (daily-PEAD test-harness'i
  on-kayitli; sentetik recovery t=5.9/placebo t=0.18/look-ahead-leak t=13.5; network YOK, edge-iddiasi YOK). [TAMAM]
- L12 MACRO-SURPRISE FORWARD-RANK (sentez) -> FORWARD-RANK-RATIONALE-VIEW (gercek CPI ~12.1/yil; en-guclu
  look-ahead-safe leg post[+1,+5] +61bp t=1.48 SIGN-UNSTABLE; |t|=2 icin yalniz ~1.15x/10yr carpan ->
  darbogaz MAGNITUDE-degil SIGN-COHERENCE; offline-olculemez; #2 tam-kurulu tek-fetch #1'in ALTINDA). [TAMAM]
- L13 DAILY-PEAD TWO-GATE BAR (sentez) -> DESCRIPTIVE-FEASIBILITY-VIEW (D-208 maliyet + L8 power TEK bara;
  olculmus aylik sinyal maliyet-tabanini ancak-ancak karsilar [long-only 37.7/38.0bp, long-short 69.4/76.1bp];
  net-bar pencerenin aylik-spread'in ~2-6x'ini ister; baglayan-duvar POWER->COST-FLOOR; #1 TEMPER, NULL gercek-olasilik). [TAMAM]
- L14 QUALITY/PROFITABILITY (ROE) -- YENI FAKTOR -> QUALITY-NOT-TRADEABLE (BIST likit kalite-primi YOK;
  K=1 LIQUID long top-ROE net -0.44%/ay t=-0.91; long-short ~0 t=0.28; maliyet-ONCESI brut zaten negatif
  -> SIGNIFICANCE/SIGN-duvari, cost-DEGIL; rejim-stabil-negatif). Graveyard'a profitability-ekseni eklendi. [TAMAM]
- L15 INVESTMENT/ASSET-GROWTH (FF CMA) -- YENI FAKTOR (FF5'in SON ayagi) -> INVESTMENT-NOT-TRADEABLE
  (deploy-formunda investment-primi YOK; equity-growth PROXY [aktif-yok, ON-BEYAN]; K=1 LIQUID long
  low-growth net -0.57%/ay t=-0.92; low-high spread ~0 t=0.46; SIGNIFICANCE/SIGN-duvari, brut zaten
  negatif t=-0.68; WRINKLE: agresif short-bacak K=3 anlamli-negatif=CMA-yonu ama deploy-kapida/spread'de
  anlamliliga ulasmaz). FF5-cross-sectional supurmesi (size/value/RMW/CMA) TUKETILDI. [TAMAM]
- L16 NEWS-SENTIMENT -- FORWARD-SCAFFOLD -> SCAFFOLD-SELF-TEST PASS (polarite-tercile CAR; sentetik
  recovery t=5.9/placebo t=0.18/leak t=13.5; snapshot 6-sembol/1-ay NOT-backtestable; gercek-run tarihsel
  haber/sentiment fetch ister -- the maintainer-kapili; edge-iddiasi YOK). [TAMAM]
- L17 NLP DISCLOSURE-TYPE -- FORWARD-SCAFFOLD -> SCAFFOLD-SELF-TEST PASS (9-tip taksonomi + Bonferroni;
  sentetik BUYBACK recovery t=2.70/placebo t=0.92/leak t=7.20; gercek-run tarihsel KAP-metin fetch ister
  -- the maintainer-kapili; edge-iddiasi YOK). [TAMAM]
- L18 VIOP index-basis overlay -- FORWARD-SCAFFOLD -> SCAFFOLD-SELF-TEST PASS (PREMISE FALSIFIED: VIOP
  arsivi LOKAL MEVCUT, 2005-2026; sentetik safe t=5.08/placebo t=-0.77/contemp-leak t=26.09; gercek-run
  INSA-EDILMIS baz-paneli [front XU030 + spot XU030] ister -- LOKAL-build, ag-fetch DEGIL; prior zayif). [TAMAM]
- L19 SHORT-SALE-INTENSITY -- YENI FAKTOR, GERCEK-VERI -> SHORT-INTENSITY-NOT-TRADEABLE (short_selling
  arsiviyle acildi; LIQUID LOW-tercile m+1 net -0.36%/ay t=-0.58 WRONG-SIGNED; tum |t|<1.1; SIGNIFICANCE/
  SIGN-duvari + LIQUID rejim-instabilitesi; yapisal-engeller [yasak-bosluk/thin-evren/aylik] ON-BEYAN dogrulandi). [TAMAM]
- L20 FOREIGN-FLOW per-stock cross-sectional -- YENI FAKTOR, GERCEK-VERI -> FOREIGN-FLOW-XS-NOT-TRADEABLE
  (foreign_flow arsiviyle acildi, 87 ay; imbalance=(alis-satis)/(alis+satis), HIGH=LONG; LIQUID HIGH m+1 net
  -0.10%/ay t=-0.35 + rejim-INSTABIL; ALL m+1 long-bacak t=2.03 ama L-S-spread~0/U-bicim microcap-artefakti
  gate-disinda, m+2'de coker; es-zamanli-co-move forward'a tasinmiyor; D-211 index-timing'den AYRI). [TAMAM]
- L21 VIOP TEK-HISSE-FUTURES ACIK-POZISYON cross-sectional -- YENI FAKTOR, GERCEK-VERI -> VIOP-OI-XS-NOT-TRADEABLE
  (viop arsiviyle acildi, 89 ay/63 dayanak; oi_growth=total_OI(m)/total_OI(m-1)-1, HIGH=LONG; fizibilite ON-CHECK
  medyan 48/min 30 SSF -> FIZIBIL; LIQUID HIGH m+1 net -1.04%/ay t=-5.13 ama TEZ-TERSI/NEGATIF -> keep-bar net>0
  GECMEZ; baskin crowding-reversal [LIQUID L-S t=-3.81, ALL L-S t=-2.46] AMA on-kayit-DEGIL + m+2-coker [t=-0.99]
  + LIQUID rejim-INSTABIL + kisa enflasyon-penceresi [2021-12..2026-04]; reversal AYRI-track-adayi loglandi). [TAMAM]
- L22 VIOP BIST30 INDEX-FUTURES TERIM-YAPISI (spot-free basis) -- YENI EKSEN (TUREV TERIM-YAPISI), GERCEK-VERI
  -> VIOP-TS-FEASIBILITY-BLOCKED (viop arsivi INF segment, F_XU030MMYY; 111 ay-sonu/2017-03..2026-05/389 egri-satir;
  slope_ann=ln(F2/F1)/((dte2-dte1)/365), TEK on-kayitli tanim; egri kalici dik-contango medyan +19.2%/yil %98.2
  contango AMA deploy-index-timing-edge OFFLINE kurulamaz: (a) TEMIZ tez-testi slope->SPOT-XU030-getiri DATA-BLOCKED
  -- spot XU030 SEVIYESI 2017-2026 lokal-YOK [resmi-gunluk 2016-11 biter, futures-doneminde 0 dosya; haftalik
  endeks-seviye-yok; xu100 yanlis]; (b) tek offline-varyant slope->futures-kendi-getirisi roll-down-MEKANIK-confounded
  [~ -slope*dt] ve ZATEN anlamsiz [naif NW-t=-1.08, carry-soyulmus NW-t=-0.97, |t|<2]; slope-TLREF korr -0.17 zayif
  -> egri carry/gurultu-domine; L18'in acik-biraktigi index-basis ekseni DURUSTCE KAPANDI; spot-basis the maintainer-kapili
  ileri-aday loglandi). [TAMAM]

## Program durumu (guncel)
12/12 yeni-EDGE-aday (L1-L4,L6 + L14 quality + L15 investment + L19 short-intensity + L20 foreign-flow-XS + L21 viop-OI-XS): deploy-edge YOK.
L7-L13 = karar/forward-araclari; L16/L17/L18 = forward-scaffold (sentetik-PASS, edge-iddiasi YOK);
L22 = TUREV TERIM-YAPISI GERCEK-olcum -> feasibility/veri-blok (deploy-edge degil; index-basis ekseni KAPANDI).
VERI-DURUMU DUZELDI: `data/bist_datastore_archive/` LOKAL kesfi -> VIOP/foreign-flow/fundamental-ratios/
short-selling artik LOKAL-MEVCUT (ag-fetch GEREKMEZ). short-selling (L19) + foreign-flow cross-sectional (L20)
+ VIOP futures open-interest cross-sectional (L21) KOSULDU = ucu de NOT-TRADEABLE; VIOP index-futures
terim-yapisi (L22) GERCEK-olculdu = feasibility-blocked (temiz spot-bacak offline-YOK + roll-down confound).
Deger hala buyuk-olcude YENI-VERI-TURUNDE (FORWARD_DATA_SPEC):
  #1 DAILY-PEAD (KAP gun-damgasi; L8 = tek power-ulasilabilir sinif; L9 hacim + L10 magnitude + L11
     on-kayitli-harness + L13 iki-kapi-maliyet/power-bar ile hazir AMA AYIK-marj; ONAYLI-FETCH gerek
     -> data/cache/kap_pead_daystamped.parquet) -- HALA ag/auth-gated,
  #2 SURPRIZ-KOSULLU MAKRO + #3 TEFAS + sentiment/NLP-corpus (#7/#8) -- HALA ag/auth-gated.
OTONOM-KOSULABILIR offline-kuyruk (graveyard-disi) artik buyuk-olcude TUKENDI: kalan tek-sey fundamental-ratios
genis oran-supurmesi = TEK-tanim-otesi grid-supurme = p-hacking (YASAK; ustelik FF5 zaten L14/L15/mezarlikta).
VIOP index-basis overlay L22'de KOSULDU (feasibility-blocked); foreign-flow L20'de, VIOP open-interest L21'de kapali.
Otonom-faz ag-pull yapmadan durur; LOKAL-arsiv okuma in-scope. Detay -> [BLOCKED_AVENUES.md].
Lab butunlugu: `harness/verify_lab.py` (read-only) -> deploy-edge-yok, ASCII, frozen Stage-0.

## Disiplin checklist (her aday)
1. Stage-0 dondur (hipotez, pencere, evren, maliyet, keep-bar, DURUST beklenti) SONUCTAN ONCE.
2. look-ahead-safe (pozisyon yalniz gozlenen-veriyle acilir; maliyet/likit trailing).
3. Likit-evren (ADV>=1e7) + ALL ikisi de raporla.
4. Gercekci maliyet (D-207) + breakeven + turnover.
5. NW-t (HAC), rejim-split sign-stability.
6. Verdict: TRADEABLE-aday / DEGIL (anlamlilik-duvari mi maliyet-duvari mi).
7. Sonuc ne olursa kaydet. Kutlama-yok. p-hacking/grid-supurme YASAK.

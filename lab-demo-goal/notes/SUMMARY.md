# lab-demo-goal -- otonom edge-kesif AR-GE: PROGRAM-DUZEYI OZET

Tarih: 2026-06-04. Tum is `lab-demo-goal/` icinde (production repo READ-ONLY). Mevcut disiplinli
olcum cercevesi REUSE edildi (Stage-0 on-kayit, look-ahead-safe, D-207 gercekci-maliyet, likit-evren
>=1e7 ADV, NW-t HAC, rejim-split 2022-01, EW-full durust-bar, ASCII, kutlama-yok). Her aday icin
keep-bar SONUCTAN ONCE donduruldu. Hicbir grid-supurme / p-hacking yapilmadi.

## Test edilen yeni adaylar + HUKUMLER
| # | aday | yontem | HUKUM |
|---|---|---|---|
| L1 | INDEX-REBALANCE (BIST100/30 ekleme-cikarma) | event-study, CAR, pit_membership | INDEX-EFFECT-VIEW (deploy-degil) |
| L2 | SHORT-TERM REVERSAL (1h/1ay contrarian) | tercile-sepet, D-207 maliyet | NOT-TRADEABLE (yanlis-isaret + maliyet-duvari) |
| L3 | PEAD (kazanc-surprizi drift) | aylik SUE cross-sectional sort | NOT-TRADEABLE (anlamlilik+maliyet duvari) |
| L4 | CALENDAR/SEASONALITY | XU100 takvim-etki tarama, Bonferroni | DESCRIPTIVE-VIEW (deploy-degil) |
| L5 | WEB SENTEZ (borsapy/borsamcp + literatur) | iki otonom arastirma-raporu damitildi | yeni-veri-kuyrugu + oncelik-guncelleme |
| L6 | MACRO-EVENT (CPI-ilan penceresi) | XU100 event-study, olay-clustered t, Bonferroni | DESCRIPTIVE-VIEW (deploy-degil; significance-wall + veri-tavani) |
| L7 | FEASIBILITY-FRONTIER (sentez) | L1/L2/L3/L6 ledger, iki-kapi siniflama | DESCRIPTIVE-SYNTHESIS (0/20 NO-WALL; ileri go/no-go kurali) |
| L8 | POWER/SAMPLE-SIZE (sentez) | L1/L6 right-signed likit-leg, n_required(\|t\|=2) + reachability | DESCRIPTIVE-POWER-VIEW (olay-kitligi darbogaz; daily-PEAD tek-ulasilabilir) |

6/6 yeni-EDGE-aday: deploy-edilebilir-edge YOK. L7+L8 = sentez (yeni-edge degil, karar-araclari).
(Onceki program: 3/3 cross-sectional + NAV + H2b + foreign-flow zaten kapali.)

## DETAYLI bulgular (her rapor ayri dosyada)
- **L1**: Niteliksel endeks-etkisi VAR (ekleme pre-efektif run-up + post reversal; cikarma ayna),
  literaturle tutarli (Bildik-Gulay 2008: hacim>fiyat, efektif-gun-zirve). AMA tek-look-ahead-safe
  pencere [+1,+K] tum-gruplarda maliyet-sonrasi NET<0; date-clustered |t| hicbir likit-tradeable
  pencerede >=2 degil (anlamlilik-duvari; N-ince ~250 ekleme/32 tarih). [L1_index_rebalance_REPORT.md]
- **L2**: KRITIK bulgu -- reversal YANLIS-ISARET. BIST 2019-2026 kisa-vade MOMENTUM gosteriyor
  (kaybedenler kaybetmeye, kazananlar kazanmaya devam; L-W spread her-yerde anlamli-negatif). Eski
  Bildik-Gulay-contrarian'in TERSI = rejim/orneklem-disi-gecerlik kaybi. Ters-yon momentum da
  deploy-degil: gross-edge ~10bp/hafta likit'te anlamsiz, turnover ~0.65 -> ~46bp maliyet yer
  (maliyet-duvari). [L2_short_reversal_REPORT.md]
- **L3**: Klasik POZITIF PEAD aylik-cozunurlukte YOK; long-only likit-tercile anlamli ALTinda
  (kismen size/benchmark-confound), scope-ici L-S pozitif-degil (K=1-likit anlamli-NEGATIF =
  consume-lag mean-reversion yakaliyor). Cozunurluk-dersi: BIST'te PEAD GUNLUK-ilan-zaman-damgasi
  gerektirir (bizde YOK). [L3_pead_REPORT.md]
- **L4**: Yatirilabilir XU100'de hicbir takvim-etkisi ham-anlamli bile degil; EW-full'daki zayif
  gun-ici yapi microcap-bagli + sub-Bonferroni. TOM-overlay yillik %12 vs B&H %47 (out-of-market
  opportunity-cost). Temiz multiple-testing null. [L4_calendar_REPORT.md]
- **L5**: En-iyi-yeni-bedava-veri = TEFAS fon-akimi/yatirimci-sayisi (5y) + KAP olay-madenciligi
  (tam-gecmis); yabanci-takas-orani + analist-revizyon forward-snapshot gerektirir. Literaturde
  likit/maliyet-aware hayatta-kalmaya en-yakin: (a) PEAD [L3'te aylik-cozunurlukte elendi],
  (b) yabanci-akim ENDEKS-timing [bizde gunluk-panel YOK]. [WEB_SYNTHESIS.md]
- **L6**: Kosulsuz CPI-ilan-penceresi XU100'de ham-anlamli bile degil (en-buyuk post[+1,+5]
  +0.61% AMA t=1.48, rejim-stabil-degil = significance-wall, cost-testine GELMEDEN dusuyor).
  Tek-iz = endeks-duzeyi vol-bump (ilan-gunu |AR| 1.50% vs 1.19%; EW-full'da YOK -> macro-beta,
  yon-tasimaz). KRITIK veri-tavani: veri yalniz TARIH tasiyor, SURPRIZ (actual/forecast) YOK ->
  drift'i tasiyan-bilesen olculemiyor; CPI-tarih proxy (+/-1-2g); PPK n=2 (cikarildi). Bu null,
  SURPRIZ-KOSULLU testin neden YENI-VERI gerektirdigini somutlastiriyor. [L6_macro_event_REPORT.md]
- **L7**: 20 deploy-leg (L1/L2/L3/L6, LIQUID+ALL) iki-kapiya gore siniflandi -> 0 NO-WALL. INCE-BULGU:
  likit'te BAGLAYAN kapi = ANLAMLILIK/POWER, maliyet DEGIL. Cross-sectional tercile (L2/L3) likit'te
  YANLIS-isaret/anlamsiz; dusuk-turnover event-driven (L1 BIST30-add +82bp, L6 post-CPI +61bp) likit'te
  DOGRU-isaret VE maliyet-ustu ama 2-sigma-alti (|t|=0.7-1.5). Microcap-killer=COST, liquid-killer=
  SIGNIFICANCE. Ileri go/no-go kurali damitildi (iki-kapiyi likit'te gec, dusuk-turnover/event tercih,
  power'i artir). [L7_feasibility_frontier_REPORT.md]
- **L8**: L7-power-darbogazini SAYIYA cevirdi. Right-signed likit event-leg'lerde n_required(|t|=2)=
  n_obs*(2/|t|)^2. BIST30-add likit (+82bp, t=0.71) ~95 tarih = ~41 yil (yilda ~2 tarih -> UMITSIZ);
  +33bp legi ~373 yil. CPI post[+1,+5] (+61bp, t=1.48) yalniz ~1.8x olay = ~6 yil AMA regime-sign-
  stable=FALSE -> "bekle, t=2 olur" hesabi verinin-desteklemedigi sabit-etki varsayar (SERAP). KRITIK:
  power darbogazi olay-GELIS-HIZI (1 CPI/ay, ~2 BIST30-tarih/yil sert-tavan), orneklem-uzunlugu degil.
  Daily-PEAD ~120 bagimsiz ifsa-tarihi/yil -> gozlenen-etki-bandi (n_req 95..759) ~0.8-6.3 yilda
  birikir = |t|=2'yi insan-ufkunda ulasilabilir kilan TEK event-sinifi. FORWARD_DATA_SPEC
  #1(daily-PEAD)>>#2(surpriz-makro)>>index-rebalance siralamasinin SAYISAL gerekcesi. [L8_power_REPORT.md]

## META-BULGU (programin ana-dersinin pekismesi)
Tekrar-eden YAPISAL DUVAR: likit-evrende gercekci round-trip ~28-46bp. Tercile-sepet + aylik/haftalik
turnover (~0.4-0.7) bunu her kucuk-edge'in uzerine bindirir -> maliyet-sonrasi olur. Maliyet-sonrasi
yasayabilecek TEK yapi = DUSUK-TURNOVER event-driven; ama elimizdeki dusuk-turnover olaylar
(index-rebalance L1, aylik-PEAD L3, makro-ilan L6) likit-evrende ANLAMLI-edge tasimiyor. Gorunur-edge'ler ya microcap'te
(yatirilamaz) ya da maliyet/anlamlilik duvarinda. Bu, onceki graveyard ile %100 tutarli.

L7-RAFINESI (iki-kapi): "tek cost-wall" yerine IKI ayri baglayici-kapi var. MICROCAP-killer = COST
(ALL-evrende gross daha-buyuk ama turnover-cost ~46-140bp yer; 10/10 BOTH). LIQUID-killer =
SIGNIFICANCE/POWER (likit'te cost-magnitude duser ama gross-edge ya yanlis-isaret [tercile L2/L3] ya
da 2-sigma-alti [event-driven L1/L6 dogru-isaret +55..+82bp ama |t|=0.7-1.5]). Yani survivable-arketip
(dusuk-turnover, event-driven, likit, dogru-isaret) DOGRU teshis edildi; eksik olan = bagimsiz
gozlem-sayisi/POWER. Bu, "deger YENI-VERI-TURUNDE" onerisine sayisal-gerekce verir: bottleneck =
likit dusuk-turnover olaylarda olay-sayisi + kesin-zamanlama.

## CAGAN ICIN SOMUT ILERI-YOL (eldeki-veriyle yeni-test degil, VERI-EDINIMI)
Eldeki-veri (fiyat/hacim/fundamental/membership/macro/earnings-aylik) ile cross-sectional/event
edge alani buyuk-olcude TUKETILDI. A-priori en-umutlu iki-yol da BIZDE-OLMAYAN veriye dayaniyor:
1. **GUNLUK PEAD**: kazanc-ilan GUN-damgasi (intraday/daily) gerekir -> KAP olay-madenciligi
   (bedava, tam-gecmis; borsapy/pykap). L3 aylik-attenuation'i bunu dogruladi.
2. **YABANCI-AKIM ENDEKS-TIMING**: gunluk-yabanci-takas-orani paneli gerekir -> forward-snapshot
   BUGUN-baslamali (bedava-API yalniz anlik). Cross-sectional-degil, index-overlay.
3. **TEFAS fon-akimi + yatirimci-sayisi** (5y bedava): retail/kurumsal-akim proxy -> hic-denenmemis,
   ayri-cekim-isi.
ONERI: siradaki-faz = lab'da bir VERI-SNAPSHOT cekim-hatti (KAP gunluk-olay + yabanci-oran + TEFAS),
sonra bu yeni-veri-turleriyle dusuk-turnover event-driven test. Mevcut-veride yeni-faktor aramak
azalan-getiri; deger artik YENI-VERI-TURUNDE.

DETAYLI ONCELIKLI SPEC (mevcut-infra-eslemeli, look-ahead-safe-kayit-kurali, CALISTIRILMADI):
[FORWARD_DATA_SPEC.md]. L7-power-gerekce ile siralandi: #1 DAILY-PEAD (KAP ifsa gun-damgasi;
kap_historical_fetcher zaten disclosureDetail.time veriyor -> infra-cogu-hazir, EN-YUKSEK power-kazanci),
#2 surpriz-kosullu makro (kesin-CPI-tarih+actual/forecast+PPK-gecmis), #3 TEFAS (yeni-build),
#4 per-stock gunluk yabanci-oran (L7-prior olumsuz; en-son).

## Disiplin teyidi
Hicbir aday icin kutlama yapilmadi; hepsi DURUST-beklentiyle (cogu duvar-bekleniyordu) ONCEDEN
beyan edildi ve olcumle dogrulandi. Tek SURPRIZ = L2'nin reversal-yerine-momentum cikmasi (yine de
deploy-degil). Sonuclar ne-olursa-olsun kaydedildi. Grid-supurme/2.tur YOK. Production repo'ya
SIFIR-dokunus (yalniz lab-demo-goal/ yazildi).

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
| L9 | PEAD-VOLUME (sentez/feasibility) | GERCEK earnings-panel likit-SUE olay-sayimi + L8-bandi reachability | DESCRIPTIVE-VOLUME-VIEW (~95-136 likit-olay/yil; band ~1-8 yilda ulasilir; L8'i empirik dogrular) |
| L10 | PEAD-EFFECT (sentez/feasibility) | per-olay etki-buyuklugu + recovery-carpani + ISARET-engeli | MAGNITUDE-FEASIBILITY-VIEW (olay-seviyesi LIKIT SUE +0.69%/ay ama ANLAMSIZ t=0.64; |t|=2 icin ~2-5.5x recovery; isaret-engeli YOK) |
| L11 | FORWARD-SCAFFOLD (on-kayit+offline-dogrulama) | daily-PEAD test-harness'i (t+1 CAR, SUE-sort, NW-t, cost, keep-bar) + sentetik self-test | SCAFFOLD-SELF-TEST PASS (recovery t=5.9 / placebo t=0.18 / look-ahead-leak t=13.5; network YOK, edge-iddiasi YOK; fetch Cagan-onayina kapili) |
| L12 | MACRO-SURPRISE (sentez/forward-rank) | #2 surpriz-kosullu-makro power+arrival rationale (L6+L8+gercek-panel) | FORWARD-RANK-RATIONALE-VIEW (CPI ~12/yil; magnitude ~1.1-1.6x yeter; baglayan-kisit ISARET-COHERENCE; #2 yine #1'in altinda, data-gated) |
| L13 | DAILY-PEAD TWO-GATE BAR (sentez/feasibility) | D-208 maliyet + L8 power TEK bara katlandi (L8/L9/L10+D208) | DESCRIPTIVE-FEASIBILITY-VIEW (aylik sinyal maliyet-tabanini ancak-ancak karsilar: long-only 37.7bp vs 38bp, long-short 69.4bp vs 76bp; net-bar pencerenin aylik-spread'in ~2-6x'ini ister; baglayan-duvar POWER->COST-FLOOR; #1 TEMPER edildi, NULL gercek-olasilik) |
| L14 | QUALITY/PROFITABILITY (ROE) -- YENI FAKTOR | ROE=net_profit/equity tercile, LIQUID, D-207 maliyet, NW-t, rejim (look-ahead lag=1mo) | QUALITY-NOT-TRADEABLE (kalite-primi YOK; K=1 LIQUID long-tercile net -0.44%/ay t=-0.91; long-short ~0 t=0.28; teshis SIGNIFICANCE/SIGN-duvari, cost-DEGIL) |
| L15 | INVESTMENT/ASSET-GROWTH (FF CMA) -- YENI FAKTOR | g=equity_t/equity_{t-12mo}-1 (asset-growth PROXY) tercile, LOW-growth=LONG, LIQUID, D-207 maliyet, NW-t, rejim (lag=1mo) | INVESTMENT-NOT-TRADEABLE (deploy-formunda investment-primi YOK; K=1 LIQUID long low-growth net -0.57%/ay t=-0.92; low-high spread ~0 t=0.46; teshis SIGNIFICANCE/SIGN-duvari; agresif-bacakta zayif-CMA-iz ama anlamliliga ulasmaz) |
| L16 | NEWS-SENTIMENT (cross-sectional) -- FORWARD-SCAFFOLD | polarite-tercile [+1,+H] CAR long-short, olay-kumeli NW-t; sentetik self-test + snapshot-karakterizasyon | SCAFFOLD-SELF-TEST PASS (recovery t=5.9 / placebo t=0.18 / leak t=13.5; network YOK; edge-iddiasi YOK; gercek-run tarihsel haber/sentiment fetch ister -- Cagan-kapili) |
| L17 | NLP DISCLOSURE-TYPE drift -- FORWARD-SCAFFOLD | 9-tip taksonomi, tip-kosullu [+1,+H] CAR, Bonferroni; sentetik self-test + snapshot-tip-dagilimi | SCAFFOLD-SELF-TEST PASS (BUYBACK recovery t=2.70 / placebo t=0.92 / leak t=7.20; network YOK; edge-iddiasi YOK; gercek-run tarihsel KAP-metin fetch ister -- Cagan-kapili) |
| L18 | VIOP index-basis TIMING overlay -- FORWARD-SCAFFOLD | feasibility + dunku-basis long/flat overlay, NW-t; sentetik safe/placebo/contemporaneous-leak | SCAFFOLD-SELF-TEST PASS (safe t=5.08 / placebo t=-0.77 / contemp-leak t=26.09; PREMISE FALSIFIED -- VIOP arsivi LOKAL var; gercek-run insa-edilmis baz-paneli + spot XU030 ister, ag-fetch DEGIL) |
| L19 | SHORT-SALE-INTENSITY (cross-sectional) -- YENI FAKTOR, GERCEK-VERI | short-TL/toplam-TL tercile, LOW=LONG, LIQUID, market-relative net, NW-t lag6, rejim (m+1 + skip-m+2) | SHORT-INTENSITY-NOT-TRADEABLE (LIQUID LOW-tercile m+1 net -0.36%/ay t=-0.58, WRONG-SIGNED; tum \|t\|<1.1; SIGNIFICANCE/SIGN-duvari + LIQUID rejim-INSTABILITESI; cost-DEGIL) |
| L20 | FOREIGN-FLOW (per-stock cross-sectional) -- YENI FAKTOR, GERCEK-VERI | imbalance=(alis-satis)/(alis+satis) tercile, HIGH=LONG, LIQUID, market-relative net, NW-t lag6, rejim (m+1 + skip-m+2) | FOREIGN-FLOW-XS-NOT-TRADEABLE (LIQUID HIGH-tercile m+1 net -0.10%/ay t=-0.35, rejim-INSTABIL; ALL m+1 long-bacak t=2.03 ama L-S-spread ~0/U-bicim microcap-artefakti, m+2'de coker; D-211 index-timing'den AYRI) |
| L21 | VIOP TEK-HISSE-FUTURES ACIK-POZISYON (cross-sectional) -- YENI FAKTOR, GERCEK-VERI | oi_growth=total_OI(m)/total_OI(m-1)-1 tercile, HIGH=LONG, LIQUID-spot, market-relative net, NW-t lag6, rejim (m+1 + skip-m+2) | VIOP-OI-XS-NOT-TRADEABLE (LIQUID HIGH-tercile m+1 net -1.04%/ay t=-5.13 ama TEZ-TERSI/NEGATIF -> keep-bar net>0 GECMEZ; baskin desen crowding-reversal AMA on-kayit-DEGIL + m+2'de coker t=-0.99 + LIQUID rejim-INSTABIL + kisa enflasyon-penceresi; iki-yonlu hukumle reversal CLAIM-edilmez) |

12/12 yeni-EDGE-aday (L1-L4,L6 + L14 quality + L15 investment + L19 short-intensity + L20 foreign-flow-XS + L21 viop-OI-XS): deploy-edilebilir-edge YOK.
L7-L13 = sentez (karar/forward-araclari); L16/L17/L18 = forward-scaffold (sentetik-PASS, edge-iddiasi YOK).
(Onceki program: 3/3 cross-sectional + NAV + H2b zaten kapali; foreign-flow INDEX-TIMING D-211'de kapaliydi --
L20 simdi AYRI per-stock CROSS-SECTIONAL varyanti gercek-veride test etti = yine NOT-TRADEABLE. L21 = VIOP
turev-konumlanma ekseni gercek-veride = yine NOT-TRADEABLE, ek-olarak guclu-anlamli TEZ-TERSI reversal-izi
ama on-kayit-DEGIL/m+2-coker -> iki-yonlu hukumle claim-edilmedi.)

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
- **L9**: L8'in VARSAYDIGI daily-PEAD hizini (~120/yil) GERCEK earnings-paneliyle olctu. 2019+ SUE-
  testable 5735 olay AMA yalniz %19 likit (1091) -> likidite YINE baglayan-kisit. Likit ~136 olay/yil;
  ay->gun bounded ~95 date-cluster/yil (L8-varsayiminin ~1.3x icinde = empirik-dogrulama). L8 n_req-bandi
  [95,759]: guclu-etki (+82bp, n~95) ~1 yilda, en-zayif (+33bp, n~759) ~8 yilda ulasilir -> daily-PEAD
  bandi <10yil ULASILABILIR (kit-siniflari CPI 12/yil & index ~2/yil ezici-asar). SONUC: FORWARD #1
  artik teorik-power degil, GERCEK-likit-hacimle bandi-gecirir-gosterildi. CAVEAT: ay-cozunurluk
  date-cluster'a TAVAN; gercek-deger gun-damgasinin etkiyi monthly-attenuation'dan kurtarmasina bagli.
  [L9_pead_volume_REPORT.md]
- **L10**: Forward-data #1 feasibility-dongusunu KAPATTI (L8=n, L9=hacim, L10=etki). Olay-seviyesi
  aylik SUE yari-bolme (pos-neg, market-relative consume-ay) LIKIT'te +0.69%/ay = DOGRU-isaretli ama
  ANLAMSIZ (Welch t=0.64; gercek-kisit sd_event ~%18.5/ay kesitsel-gurultu). Stage-0 beklentisi
  NEGATIF-isaret-engeliydi; CIKMADI (Stage-0 bu dali onceden-kaydetti) -> isaret-engeli YOK, MAGNITUDE
  sorusu. |t|=2 icin gun-damgali etki aylik-yari-bolmenin ~2-5.5x'i gerekir (1-8yil); PEAD-literatur
  driftin ilk-gunlerde yogunlasmasi -> makul. KONSERVATIF: sd_event aylik; gunluk-pencere sd cok-dusuk
  (~sqrt(gun/21)) -> gercek-gereken-etki bound'dan KUCUK. SONUC: hacim yeterli + isaret-dogru +
  magnitude-makul; tek-kalan-bilinmeyen gunluk-pencere etkisi -> OFFLINE OLCULEMEZ, fetch karara-baglar.
  [L10_pead_effect_REPORT.md]
- **L11**: daily-PEAD sentezinin TACI -- forward-deneyi CALISTIRILABILIR yapan on-kayitli test-harness.
  Tasarim donmus (t+1 look-ahead-safe giris, market-relative [+1,+H] CAR, SUE-tercile long-short,
  olay-kumeli NW-t, gercekci round-trip cost, keep-bar). Gercek-mod: data/cache/kap_pead_daystamped.parquet
  geldiginde (onayli-fetch) ayni harness on-kayitli testi kosar. Offline-mod: seed'li sentetik gun-damgasiyla
  3 self-test assert PASS -- RECOVERY (planted-drift geri-kazanilir, t=5.9, dogru-isaret), PLACEBO
  (SUE-permute -> t=0.18), LOOK-AHEAD (olay-gunu girisi sicramayi sizdirir t=13.5 > guvenli t=5.9 ->
  ilan-gunu t+1 ile DISLANIR). Sentetik PASS yalniz pipeline-dogrulugu+look-ahead-guvenligi kanitlar;
  GERCEK BIST-edge'i hakkinda HICBIR sey demez. Network/scraper YOK -> fetch Cagan-onayina kapili.
  SONUC: FORWARD #1 artik power[L8]+hacim[L9]+magnitude[L10]+calistirilabilir-harness[L11] = DORT-yonden hazir.
  [L11_forward_daily_pead_REPORT.md]
- **L12**: FORWARD_DATA_SPEC #2'yi (surpriz-kosullu makro) sayisallastirdi. GERCEK makro-panel: CPI
  ~12.1/yil (L8'i dogrular). En-guclu look-ahead-safe leg post_tight [+1,+5]: kosulsuz +61bp, t=1.48,
  SIGN-UNSTABLE. |t|=2 icin gereken surpriz-CARPANI yalniz ~1.15x (10yil) / ~1.62x (5yil) -> magnitude
  neredeyse-ulasilir. DEMEK: #2'nin darbogazi power-magnitude DEGIL, ISARET-COHERENCE (en-guclu leg
  yon-tutarsiz). Surpriz-kosullama (surpriz-isareti -> tepki-isareti) tam-bunu saglayabilecek mekanizma,
  ama konsensus-surpriz verisi offline YOK -> test-edilemez. Kosulsuz etki Bonferroni-gecmez (artifakt-riski).
  SONUC: #2 magnitude-yakin + sign-coherence-vaadi tasir AMA tam-kurulu tek-fetch #1'in ALTINDA kalir
  (#1>>#2 artik sayisal-gerekceli). [L12_macro_surprise_REPORT.md]
- **L13**: daily-PEAD'i significance-only cerceveden IKI-KAPI bara yukseltti -- D-208 gercekci maliyet
  (~38bp likit round-trip) L8 power-duvariyla TEK ileri-bara katlandi. AYIK ana-bulgu: olculmus AYLIK
  likit sinyali maliyet-tabanini ANCAK-ANCAK karsiliyor (long-only high-SUE +37.7bp vs tek round-trip
  38.0bp = 0.99x; long-short half-split +69.4bp vs cift round-trip 76.1bp = 0.91x) -> POWER bir-yana,
  maliyet-tabani bile gecilmiyor. Net-|t|=2 brut ilan-penceresi-CAR bari (konservatif 95.4/yil, 5g):
  long-short 261bp(1yr)->142bp(8yr); baglayan-duvar kisa-ufukta POWER, uzun-ufukta sabit COST-FLOOR
  (long-short 5g'de H=8yr). Pencere aylik-spread'in ~2-6x'ini saglamali -> daily-PEAD'in TUM-umudu
  ilan-penceresi KONSANTRASYONU + gercek-gurultu sqrt-altinda; IKISI de offline-OLCULEMEZ. SONUC: #1
  hala tek power-ulasilabilir sinif AMA TEMPER edildi -- net-deploy bari yuksek, aylik-sinyal marji yok,
  fetch NULL donebilir (tek-makul-bahis, kesin-kazanc degil). [L13_daily_pead_feasibility_REPORT.md]
- **L14**: GERCEKTEN YENI canonical faktor -- QUALITY/PROFITABILITY (ROE=net_profit/equity, Fama-French
  RMW ailesi), graveyard'da DEGIL. On-kayitli tek-tanim, rank-tercile, look-ahead lag=1ay, LIQUID +
  D-207 maliyet. Sonuc: BIST likit-evrende kalite-primi YOK. Deploy-kapisi (K=1 LIQUID long top-ROE
  tercile) market-relative net = -0.44%/ay, ANLAMSIZ (t=-0.91); long-short ROE spread ~0 (t=0.28,
  benchmark-bagimsiz teyit). KRITIK teshis farki: bu COST-duvari DEGIL -- maliyet-ONCESI brut sinyal
  zaten negatif (t=-0.66), turnover dusuk (0.20, kalite yavas-sinyal) -> SIGNIFICANCE/SIGN-duvari.
  Rejim-stabil-negatif (pre+post 2022 negatif). META-BULGU'yu profitability-ekseninde teyit eder.
  [L14_quality_roe_REPORT.md]
- **L15**: FF5'in SON test-edilmemis ayagi -- INVESTMENT/ASSET-GROWTH (CMA). Proxy: trailing-12-ay
  kitap-ozkaynak buyumesi (aktif-paneli yok; PROXY-caveat Stage-0'da ON-BEYAN -- borc-finansmanli
  buyumeyi kacirir). Isaret: dusuk-buyume(konservatif)=LONG. Sonuc: deploy-formunda investment-primi
  YOK. Deploy-kapisi (K=1 LIQUID long low-growth tercile) market-relative net = -0.57%/ay, ANLAMSIZ
  (t=-0.92); low-minus-high spread ~0 (LIQUID +0.33%/ay t=0.46, benchmark-bagimsiz teyit). Teshis yine
  SIGNIFICANCE/SIGN-duvari (cost-DEGIL; costfree brut zaten negatif t=-0.68, turnover dusuk 0.20).
  DURUST WRINKLE: K=3 LIQUID'te HIGH-growth (agresif) short-bacak ANLAMLI negatif (net t=-2.95) =
  TAM CMA-yonu, AMA long-only deploy-kapisinda ve low-high spread'de anlamliliga ULASMIYOR (iz, edge-degil).
  Bununla FF5-cross-sectional-fundamental supurmesi (size/value=mezarlik, RMW=L14, CMA=L15) TUKETILDI.
  [L15_investment_growth_REPORT.md]
- **L16**: Direktifin SENTIMENT avenusu L11-forward-scaffold formuna kristalize edildi. Offline tek
  sentiment-verisi CANLI snapshot (`news_cache.json`: 6 sembol / 60 makale / ~1-ay / baslik-only,
  polarite-siniflanabilir yalniz %33) -> backtestable-panel DEGIL. Sentetik 3-assert PASS (recovery t=5.9
  / placebo t=0.18 / look-ahead-leak t=13.5). Yalniz pipeline-dogrulugu+look-ahead-guvenligi kanitlanir;
  gercek-edge ag-fetch'e (Cagan-kapili) bagli. Snapshot KAP-ifsa-baskin -> L17 + #1 daily-PEAD ile
  ortak-fetch'ten beslenebilir. [L16_sentiment_scaffold_REPORT.md]
- **L17**: Direktifin NLP avenusu, L16-polaritesinden ayri: HANGI ifsa-TIPI drift ongoruyor, 9-tip
  taksonomi + Bonferroni cok-test-kontrolu. Sentetik 3-assert PASS (BUYBACK recovery t=2.70 / placebo
  t=0.92 / leak t=7.20). Snapshot tip-dagilimi var ama gun-damgali-derinlik YOK -> backtest IMKANSIZ.
  Gercek-run tarihsel KAP tam-metin + NLP-pipeline (Cagan-onayli) ister. [L17_nlp_disclosure_type_REPORT.md]
- **L18**: Direktifin VIOP avenusu. KRITIK: Stage-0 "offline VIOP-yok" premise'i FALSIFIE -- 
  `data/bist_datastore_archive/viop` LOKAL MEVCUT (256 EOD-ay, 2005-2026; settlement/OHLC/OI, XU030
  vadeli en-likit + likit single-stock-futures alt-kume). Sentetik index-basis overlay 3-assert PASS
  (safe-lagged t=5.08 / placebo t=-0.77 / contemporaneous-leak t=26.09 -> ayni-gun es-hareket safe'ten
  cok-buyuk |t|, dogru-sebeple gecer). Gercek-run icin EKSIK = INSA-EDILMIS baz-paneli (front XU030
  vadeli vs gunluk SPOT XU030); bu LOKAL-build, ag-fetch DEGIL. Prior ZAYIF (timing-overlay,
  foreign-flow-bitisik). Acik-pozisyon (OI) ek-eksen olarak arsivde, henuz on-kayitsiz. [L18_viop_feasibility_REPORT.md]
- **L19**: GERCEKTEN YENI eksen, GERCEK-veride -- SHORT-SALE-INTENSITY (short-TL/toplam-TL), yeni-kesfedilen
  `data/bist_datastore_archive/short_selling` arsiviyle acildi (aylik per-stock, 2015-2026, yasak-bosluklari).
  Tez (Boehmer/Jones/Zhang): DUSUK-short=LONG. Sonuc: deploy-kapisi (LIQUID LOW-tercile m+1) market-relative
  net = -0.36%/ay, ANLAMSIZ (t=-0.58) ve YANLIS-ISARET (LOW-bacak underperform); tum |t|<1.1. Teshis
  SIGNIFICANCE/SIGN-duvari + LIQUID rejim-INSTABILITESI (2022'de isaret donuyor: pre +0.30%/ay, post
  -1.07%/ay), cost-DEGIL (gross zaten yanlis-isaret, turnover 0.39, cost ~16bp). primary(m+1) vs
  robust(m+2) L-S isaretleri bile ZIT. Yapisal-engeller (short-yasagi-bosluklari, thin ~50-isim modern
  shortable evren, aylik-granularite) ON-BEYAN dogrulandi. SHORT-INTENSITY-NOT-TRADEABLE. [L19_short_sale_intensity_REPORT.md]
- **L20**: GERCEKTEN YENI eksen, GERCEK-veride -- per-stock FOREIGN-FLOW cross-sectional (yabanci net-akim
  imbalance), yeni-kesfedilen `data/bist_datastore_archive/foreign_flow` arsiviyle acildi (aylik per-stock
  alis/satis-TL, legacy .xls; 2019-01..2026-04 join = 87 ay / 41643 gozlem). D-211 (yabanci INDEX-TIMING
  graveyard) den AYRI per-stock varyant. Tez (Richards 2005 EM): yuksek-imbalance(net-alis)=LONG. Sonuc:
  deploy-kapisi (LIQUID HIGH-tercile m+1) market-relative net = -0.10%/ay, ANLAMSIZ (t=-0.35) ve rejim-INSTABIL
  (pre-2022 -0.82%/ay, post +0.35%/ay -> isaret donuyor); LIQUID L-S spread hafifce-negatif (-0.90% t=-1.66 =
  zayif reversal-egilimi). "Anlamli"-gorunen tek hucre (ALL m+1 long-bacak net t=2.03) on-kayitli LIQUID-kapinin
  DISINDA + L-S-spread'i ANLAMSIZ (gross t=0.81, net t=-0.44) + U-bicimli (hem HIGH hem LOW orta-tercile'i geciyor)
  + m+2'de t=1.29'a coker + ~477 microcap-agirlikli isim -> edge degil, evren-secim/microcap artefakti (p-hacking
  koruma calisti: gate on-kayitliydi). Teshis SIGNIFICANCE/SIGN-duvari + es-zamanli-co-move(forward-DEGIL) +
  LIQUID rejim-INSTABILITESI; cost-DEGIL (LIQUID gross zaten ~0). Hepsi ON-BEYAN dogrulandi. FOREIGN-FLOW-XS-NOT-TRADEABLE.
  [L20_foreign_flow_xs_REPORT.md]
- **L21**: GERCEKTEN YENI eksen, GERCEK-veride -- VIOP TEK-HISSE-FUTURES ACIK-POZISYON cross-sectional (futures
  open-interest buyumesi), var-olan `data/bist_datastore_archive/viop` arsiviyle acildi (VIOP_GUNSONU per-sozlesme
  ACIK POZISYON, segment SSF; 89 ay / 63 dayanak / 3947 OI-gozlem). Fizibilite ON-CHECK: ay-sonu pozitif-OI SSF
  medyan 48 / min 30 -> tercile testi FIZIBIL (L18-tipi blok DEGIL); 63/63 dayanak spot-panelde. Tez (Hong-Yogo
  cross-sectional analogu): yuksek-OI-growth=LONG. Sonuc: deploy-kapisi (LIQUID HIGH-tercile m+1) market-relative
  net = -1.04%/ay, GUCLU-ANLAMLI (t=-5.13) ama TEZ-TERSI/NEGATIF -> keep-bar net>0 GECMEZ + rejim-INSTABIL.
  Baskin desen tezin TERSI = crowding/dikkat-reversal (LIQUID long-bacak t=-5.13, L-S t=-3.81; ALL L-S t=-2.46
  rejim-stabil-negatif) AMA edge-CLAIM-EDILMEZ: (a) iki-yonlu hukum -- reversal on-kayitli-DEGIL, isaret-donderme
  = p-hacking; (b) LIQUID-kapi KISA-yakin enflasyon-penceresi (2021-12..2026-04, 32 ay) + KENDI-icinde rejim-INSTABIL;
  (c) m+2'de COKER (t=-0.99); (d) breakeven NEGATIF (on-kayitli yonde brut prim YOK). Teshis es-zamanli-co-move +
  crowding-reversal + LIQUID rejim-INSTABILITESI + INCE-kesit (avg 31.8); cost-DEGIL. Hepsi ON-BEYAN dogrulandi.
  Reversal-gozlemi AYRI gelecek-track adayi olarak loglandi (Cagan-mandasi + taze Stage-0 + m+2-survival +
  rejim-stabilite + gercekci short-maliyeti gerekir). VIOP-OI-XS-NOT-TRADEABLE. [L21_viop_oi_xs_REPORT.md]

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

## PROGRAM DURUMU (guncel -- 2026-06-04)
21 track tamamlandi (L1-L21): FF5-cross-sectional supurmesi tam (size/value=mezarlik, momentum/reversal/
hi52/lowvol/NAV/temettu zaten kapali, RMW=L14, CMA=L15), short-selling-positioning GERCEK-test (L19),
per-stock foreign-flow cross-sectional GERCEK-test (L20), VIOP futures open-interest cross-sectional
GERCEK-test (L21), sentiment/NLP/VIOP-basis forward-scaffold'lari (L16/L17/L18, sentetik-PASS).
12/12 yeni-EDGE-aday deploy-edge YOK; verdict'ler honest-non-deployable.

VERI-DURUMU DUZELDI (onceki "ucu de offline-veri-yok" YANLISTI): `data/bist_datastore_archive/` LOKAL
arsivi kesfedildi -> VIOP (#9), foreign-flow (#4), fundamental-ratios, short-selling artik LOKAL-MEVCUT,
ag-fetch GEREKMEDEN otonom-kosulabilir. short-selling (L19), foreign-flow cross-sectional (L20) ve VIOP
futures open-interest cross-sectional (L21) KOSULDU -- ucu de NOT-TRADEABLE. HALA-eksik: sentiment/NLP
tarihsel metin-corpus (#7/#8 -- yalniz snapshot) + corporate_actions/dividends/index_components (arsivde HALA BOS).

KALAN GERCEK ag/auth-gates -> [BLOCKED_AVENUES.md]: #1 daily-PEAD (KAP gun-damgasi fetch, en-yuksek power),
#2 surprise-makro, #3 TEFAS, #6 analist-revizyon, #7 sentiment-corpus, #8 NLP-metin-corpus. OTONOM-KOSULABILIR
KALAN (ag-fetch GEREKMEZ, [ARSIV-MEVCUT]): fundamental-ratios (degoran/ORAN .xls; P/E-P/B-vb. -- ama FF5
value/quality/investment zaten L14/L15/mezarlikta, prior-zayif), VIOP index-basis overlay (once LOKAL
baz-paneli build: front XU030 + spot XU030 hizalama, prior-zayif). VIOP open-interest konumlanma ekseni
artik L21'de KOSULDU (NOT-TRADEABLE; tezin-tersi crowding-reversal-izi on-kayitsiz, ayri-track adayi).
Otonom-faz ag-pull yapmadan durur ama LOKAL-arsiv okuma in-scope ve arastirma-isinin kendisidir.

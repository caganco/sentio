# L21 -- VIOP TEK-HISSE-FUTURES ACIK-POZISYON CROSS-SECTIONAL (HUKUM: VIOP-OI-XS-NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L21_viop_oi_xs.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l21_viop_oi_xs_results.json`. ASCII. OLCUM (yeni-FAKTOR, sentez-degil).
GERCEK-VERI testi. Yeni-veri-CEKIMI YOK (var-olan offline arsiv), optimizasyon YOK, grid-supurme YOK,
committed-motor SIFIR-dokunus, look-ahead-safe. repo READ-ONLY (yazim yalniz lab-demo-goal/ altinda).

GERCEKTEN YENI eksen: oi_growth(sembol, ay m) = total_OI_sonu(m)/total_OI_sonu(m-1) - 1, total_OI =
o dayanagin TUM SSF (tek-hisse-futures) sozlesmelerinin ACIK POZISYON (col21) toplami, ayin SON islem
gununde. Bu bir per-stock TUREV-KONUMLANMA ekseni (futures acik-pozisyon buyumesi) -- L1-L20'deki hicbir
ekseni tekrar-etmez (fiyat/hacim/temel/sentiment/short/yabanci-akim disinda). Yeni etkinlesti cunku VIOP
gun-sonu arsivi (`data/bist_datastore_archive/viop`, VIOP_GUNSONU_FIYATHACIM aylik CSV, 2017-2026 sikistirilmamis)
per-sozlesme ACIK POZISYON + segment SSF tasiyor. Tez (Hong-Yogo 2012 aggregate-OI-growth-getiriyi-onceler'in
cross-sectional analogu): OI'si BUYUYEN isimler (konumlanma birikiyor) sonradan OUTPERFORM. Deploy-formu:
likit-spot-evrende YUKSEK-OI-growth tercile'i LONG, market-relative, gercekci-maliyet-net.

FIZIBILITE (Stage-0-ONCESI, donmus): ay-sonu pozitif-OI SSF dayanak sayisi 2019-2026: medyan 48, min 30,
max 52 -> tercile testine YETER (>= 30 her ay). 63 farkli dayanagin TUMU spot fiyat-panelinde mevcut (0-eksik)
-> getiri ve D-205 likidite filtresi spot'tan hesaplanir. KARAR: gercek cross-sectional test FIZIBIL (L18-tipi
fizibilite-bloku DEGIL).

DURUST BEKLENTI (ON-BEYAN, Stage-0): prior ZAYIF (L20'den de zayif). Lehte: futures OI-growth aggregate
zaman-serisinde taninan konumlanma sinyali (Hong-Yogo). Aleyhte: (a) per-stock CROSS-SECTIONAL OI-growth
anomalisi iyi-kurulmus DEGIL (Hong-Yogo aggregate); (b) BIST SSF piyasasi INCE (~48 isim), OI yogun ->
oran gurultulu; (c) OI-degisimi es-zamanli hacim/oynaklik/fiyat ile bagli -> look-ahead-safe m+1 bu co-move'u
DISLAYINCA cogu yikanir, hatta yuksek-OI-growth (dikkat-ceken) isimler TERSINE-doner (crowding-reversal);
(d) sozlesme-roll mevsimselligi gurultu ekler. En-olasi: anlamlilik-duvari / monoton-spread-yok / rejim-instabilitesi.
Kutlama beklentisi YOK; sonuc ne olursa kaydedilir.

## Tasarim (donmus)
- Sinyal: oi_growth = total_OI_sonu(m)/total_OI_sonu(m-1) - 1. Ardisik-ay + onceki-OI>0 zorunlu. Her ay
  cross-sectional tercile (rank-bazli -> oran-aykiri-degerlerine dayanikli, winsorization-parametresi YOK).
  TEK on-kayitli tanim (alternatif-normalizasyon YOK, grid YOK -> multiple-testing YOK). YUKSEK OI-growth = LONG,
  DUSUK = SHORT. Teyit L-S = mean(HIGH) - mean(LOW).
- Look-ahead-safe: OI (ACIK POZISYON) gun-sonu PUBLIC veri, AYNI-GUN yayinlanir -> ay-sonu total-OI ay-sonunda
  bilinir -> PRIMARY ay m sinyali -> ay m+1 forward SPOT getiri KESIN look-ahead-safe (L20'nin bulten-gecikmesi
  varsayimindan TEMIZ). ROBUST skip-ay: m -> m+2. IKISI de raporlanir.
- Evren: SSF dayanaklar (.E atilir -> ciplak spot-ticker). ALL + LIQUID (spot trailing-63-islem-gunu medyan
  value_tl >= 1e7 TL, D-205 mutlak-esik). min 30 isim/ay. Spot-hisse alinir (deploy-uygun); futures OI sadece sinyal.
- Getiri: adjusted_close(forward-ay-sonu)/adjusted_close(giris-ay-sonu)-1 (yalniz ardisik ay); market-relative =
  ayni-kapsam EW-evren forward getirisi cikarilarak. Benchmark: EW same-scope.
- Maliyet: round_trip_bps=40 x LONG-sepetin aylik turnover'i. Keep-bar: LIQUID HIGH-OI-growth tercile
  market-relative NET mean>0 VE |NW-t|>=2 (HAC lag 6) VE rejim-isaret-stabil (2022-01-01 split). Aksi ->
  VIOP-OI-XS-NOT-TRADEABLE. Iki-yonlu hukum: ANLAMLI-NEGATIF spread (yuksek-OI-growth UNDERperform = crowding-
  reversal) de on-kayitli edge DEGIL -> NOT-TRADEABLE (reversal taze on-kayit ister).

## Olculen (OI: 3947 gozlem / 89 ay / 63 dayanak; sinyal-join: 3881 / 88 ay; pencere 2019-02..2026-04)
| scope / lag | aylar | avg isim | HIGH-rel gross (t) | HIGH-rel NET (t) | rejim-stabil | L-S net (t) | turnover | realized-cost | breakeven |
|---|---:|---:|---|---|:--:|---|---:|---:|---:|
| ALL primary m+1 | 87 | 44.0 | -0.11%/ay (t=-0.53) | -0.41%/ay (t=-1.88) | EVET(NEG) | -0.91% (t=-2.46) | 0.74 | 29.6bp | -15.5bp |
| ALL robust m+2 | 86 | 43.9 | -0.16%/ay (t=-0.46) | -0.46%/ay (t=-1.29) | HAYIR | -0.98% (t=-1.63) | 0.74 | 29.5bp | -22.0bp |
| **LIQUID primary m+1** | 32 | 31.8 | **-0.74%/ay (t=-3.60)** | **-1.04%/ay (t=-5.13)** | **HAYIR** | -2.31% (t=-3.81) | 0.76 | 30.4bp | -96.9bp |
| LIQUID robust m+2 | 31 | 31.8 | -0.38%/ay (t=-0.55) | -0.68%/ay (t=-0.99) | HAYIR | -1.37% (t=-1.02) | 0.76 | 30.4bp | -49.7bp |

LIQUID pencere = 2021-12..2026-04 (32 ay): sabit 1e7-TL nominal esik, TL-cirosu enflasyonla sisene kadar (>=2021-sonu)
30+ SSF-isim gecemiyor -> LIQUID kapsam TAMAMEN post-2021 enflasyon-doneminde, kisa ve yakin. avg 31.8 isim = 30-tabanini
ancak gecer (INCE). LIQUID rejim-detay (primary m+1): pre-2022 mean=~0.00%/ay, post +(-)1.08%/ay -> ISARET-instabil
(ve negatif-tarafta). ALL rejim-detay (primary m+1): pre -0.43%/ay, post -0.40%/ay -> stabil ama NEGATIF.

## Okuma (beklenti DOGRULANDI -- durust-null; tez TERS-isaretli)
- **Deploy-kapisi (LIQUID HIGH-OI-growth, primary m+1) GECMEZ**: market-relative net = -1.04%/ay -- on-kayitli
  tezin (HIGH=outperform) TAM TERSI isaret. Keep-bar net>0 ister; net NEGATIF + rejim-INSTABIL -> dusukten-de-duser.
  `VIOP-OI-XS-NOT-TRADEABLE`.
- **Baskin desen tezin TERSI = crowding/dikkat-reversal**: yuksek-OI-growth isimler UNDERperform. LIQUID-kapida
  guclu-anlamli (long-bacak t=-5.13, L-S t=-3.81); ALL'da L-S t=-2.46 ve rejim-stabil-negatif. ANCAK bunu edge'e
  CEVIRMEK YASAK: (a) iki-yonlu hukum -- reversal on-kayitli edge DEGIL, isareti sonradan donderme = p-hacking;
  (b) guclu-anlamli LIQUID-kapi KISA-yakin pencere (2021-12..2026-04, 32 ay, enflasyon-donemi) ve KENDI-icinde
  rejim-INSTABIL (pre ~0, post -1.08%); (c) m+2 robustlugu COKER (t=-0.99 / L-S t=-1.02) -- reversal tek-ay-skip'i
  GECMEZ -> hizli (~1-ay) mikroyapi-reversali, kalici faktor DEGIL; (d) breakeven NEGATIF -> on-kayitli yonde brut
  prim HIC YOK.
- **Es-zamanli co-move teyidi**: ON-BEYAN edilen (c) riski -- OI-degisimi dikkat/hacim ile es-zamanli, m+1 forward'a
  tasinmiyor/tersine donuyor -- dogrudan teyit edildi.
- **Rejim-INSTABILITESI + INCE-kesit**: ON-BEYAN edilen (b)/(d) -- LIQUID kesit 30-tabanini ancak geciyor (avg 31.8),
  yalniz yakin enflasyon-penceresinde; rejim-isareti tek-kararli degil. Teyit edildi.
- **Cost-duvari DEGIL**: on-kayitli (LONG-HIGH) yonde brut prim zaten negatif; oldurulecek brut sinyal YOK.

## Reversal-gozlemi (opposite-sign finding; on-kayit-DEGIL -> AYRI gelecek-track adayi)
Yuksek-OI-growth -> underperform deseni L20'nin artefaktlarindan GUCLU; ama (i) on-kayitli yon DEGIL, (ii) m+2'de
COKER, (iii) LIQUID-kapida kisa/enflasyon-penceresi + rejim-instabil. AYRI bir on-kayitli REVERSAL-track olarak
denenebilir; ZORUNLU on-kayit kosullari: the maintainer-mandasi + taze Stage-0 + m+2-hayatta-kalma + rejim-stabilite +
gercekci SHORT-bacak maliyeti (futures/short maliyeti). Bu track'te CLAIM EDILMEZ (anti-p-hacking).

## Hukum: VIOP-OI-XS-NOT-TRADEABLE (no deployable edge)
Gercekten-yeni bir eksen (per-stock futures acik-pozisyon konumlanmasi), var-olan VIOP arsiviyle GERCEK-veride
acildi ve olculdu: BIST likit-spot-evrende YUKSEK-OI-growth deploy-formunda prim YOK; aslinda on-kayitli tezin
TERSI (high-OI-growth UNDERperform). Keep-bar net>0 gecmez (net=-1.04%/ay), rejim-instabil, m+2'de coker, breakeven
negatif. Anlamli-NEGATIF (crowding-reversal) on-kayitli edge degil -> iki-yonlu hukumle NOT-TRADEABLE (reversal taze
on-kayit ister; AYRI track adayi olarak loglandi). Teshis es-zamanli-co-move + crowding-reversal + LIQUID rejim-
INSTABILITESI + INCE-kesit (cost-duvari degil) -- hepsi Stage-0'da ON-BEYAN edildi. Deploy-iddiasi YOK. Sonuc
kaydedildi (kutlama-yok). TEK on-kayitli tanim; varyant-supurme yapilmadi (p-hacking YOK). N<=1 (gercek-test).
L21 ARSIVLENDI.

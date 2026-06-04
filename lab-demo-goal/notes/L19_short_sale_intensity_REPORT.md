# L19 -- SHORT-SALE-INTENSITY CROSS-SECTIONAL FACTOR (HUKUM: SHORT-INTENSITY-NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L19_short_sale_intensity.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l19_short_sale_intensity_results.json`. ASCII. OLCUM (yeni-FAKTOR, sentez-degil).
GERCEK-VERI testi. Yeni-veri-CEKIMI YOK (var-olan offline arsiv), optimizasyon YOK, grid-supurme YOK,
committed-motor SIFIR-dokunus, look-ahead-safe. repo READ-ONLY (yazim yalniz lab-demo-goal/ altinda).

GERCEKTEN YENI eksen: short_intensity(sembol, ay m) = acial-satis-TL(m) / toplam-islem-TL(m). Bu bir
KONUMLANMA/AKIM ekseni (short-selling positioning) -- L1-L18 graveyard'in fiyat/hacim/temel/sentiment
eksenlerinin HICBIRI degil; fiyattan ya da temelden TUREYEN bir sey degil. Yeni etkinlesti cunku gercek bir
offline acial-satis arsivi kesfedildi (`data/bist_datastore_archive/short_selling`, aylik per-stock short-TL,
2015-2026). Tez (Boehmer/Jones/Zhang): short-baskisi BILGILIDIR -> YUKSEK short-yogunlugu sonradan
UNDERPERFORM, DUSUK short-yogunlugu OUTPERFORM. Deploy-formu: likit-evrende DUSUK-short-yogunlugu tercile'i
LONG, market-relative, gercekci-maliyet-net.

DURUST BEKLENTI (ON-BEYAN, Stage-0): prior MODERATE-to-WEAK. BIST'te (a) tekrarli short-YASAKLARI -> uzun
bosluklar + yapisal-secili ornek (2020-03..06 COVID yasagi; 2023 + 2024 parcalari turmoil-yasaklari),
(b) modern rejimde KISITLI ~50-isim shortable evren -> ince, yalniz-buyuk-cap kesit, (c) AYLIK (gunluk-degil)
granularite -> zayif zamanlama. En-olasi sonuc: anlamlilik-duvari ya da rejim-isaret-instabilitesi. Kutlama
beklentisi YOK; sonuc ne olursa kaydedilir.

## Tasarim (donmus)
- Sinyal: short_intensity = aylik acial-satis-TL / aylik toplam-islem-TL. Her ay cross-sectional tercile.
  DUSUK-yogunluk = LONG (pozitif-bilgi bacagi), YUKSEK-yogunluk = SHORT. Teyit L-S = mean(LOW) - mean(HIGH).
- Look-ahead-safe: PRIMARY ay m sinyali -> ay m+1 forward getiri (pozisyon m-sonunda kurulur; varsayim:
  aylik Acial Satis Bulteni ay-sonunda yayinlanir, m+1 basinda mevcuttur). ROBUST skip-ay: m -> m+2
  (kesin look-ahead-safe; yayin-gecikmesine duyarlilik siniri). IKISI de raporlanir; isaret/anlamlilik
  ayrisirsa o bir bulgudur.
- Evren: ALL + LIQUID (>=1e7 TL trailing-63-islem-gunu medyan value_tl, D-205 mutlak-esik). min 30 isim/ay.
  Sembol-join: short sembollerinden sondaki ".E" atilir -> ciplak fiyat-ticker'a eslenir.
- Getiri: adjusted_close(forward-ay-sonu)/adjusted_close(giris-ay-sonu)-1; market-relative = ayni-kapsam
  EW-evren forward getirisi cikarilarak. Benchmark: EW same-scope.
- Maliyet: round_trip_bps=40 (likit orta-aralik, D-207/D-208) x LONG-sepetin aylik turnover'i.
- Keep-bar: LIQUID LOW-tercile market-relative NET mean>0 VE |NW-t|>=2 (HAC lag 6) VE rejim-isaret-stabil
  (2022-01-01 split). Aksi -> SHORT-INTENSITY-NOT-TRADEABLE. Iki-yonlu hukum (D-205/D-209 deseni).

## Olculen (short: 92 ay / 17600 gozlem; sinyal: 55 ay / 6426 gozlem)
| scope / lag | aylar | avg isim | LOW-rel gross (t) | LOW-rel NET (t) | rejim-stabil | L-S net (t) | turnover | realized-cost | breakeven |
|---|---:|---:|---|---|:--:|---|---:|---:|---:|
| ALL primary m+1 | 54 | 118.4 | -0.02%/ay (t=-0.03) | -0.19%/ay (t=-0.36) | EVET(neg) | +0.09% (t=0.10) | 0.43 | 17.2bp | -4.2bp |
| ALL robust m+2 | 53 | 120.0 | -0.00%/ay (t=-0.00) | -0.18%/ay (t=-0.49) | EVET(neg) | -0.31% (t=-0.50) | 0.44 | 17.5bp | -0.3bp |
| **LIQUID primary m+1** | 27 | 40.6 | **-0.21%/ay (t=-0.33)** | **-0.36%/ay (t=-0.58)** | **HAYIR** | -0.63% (t=-0.56) | 0.39 | 15.6bp | -53.0bp |
| LIQUID robust m+2 | 27 | 40.6 | -0.24%/ay (t=-0.69) | -0.40%/ay (t=-1.09) | HAYIR | +0.33% (t=0.53) | 0.39 | 15.6bp | -62.5bp |

LIQUID rejim-detay (primary m+1): pre-2022 mean=+0.30%/ay, post-2022 mean=-1.07%/ay -> ISARET DONUYOR.
LIQUID rejim-detay (robust m+2): pre=-0.90%/ay, post=+0.14%/ay -> yine ISARET DONUYOR (ters-yonde).

## Okuma (beklenti DOGRULANDI -- durust-null)
- **Short-baskisi primi YOK (deploy-formunda)**: deploy-kapisi (LIQUID LOW-yogunluk tercile, primary m+1)
  market-relative net = -0.36%/ay, ANLAMSIZ (t=-0.58) ve YANLIS-isaret (LOW-bacak underperform ediyor,
  tez OUTPERFORM bekliyordu). Keep-bar GECMEZ. `SHORT-INTENSITY-NOT-TRADEABLE`.
- **Bu bir COST-duvari DEGIL, bir SIGNIFICANCE/SIGN duvari**: maliyet-ONCESI (gross) LOW-yogunluk likit
  getirisi ZATEN negatif (t=-0.33) ve butun |t|<1.1. Turnover dusuk (0.39), realized-cost yalniz ~16bp;
  ortada oldurulecek bir brut-LONG-sinyal YOK. breakeven NEGATIF (-53bp) cunku gross zaten yanlis-isaret.
- **Rejim-INSTABILITESI (LIQUID)**: deploy-kapsaminda isaret 2022'de DONUYOR (pre +0.30%/ay, post -1.07%/ay).
  Bu, ON-BEYAN edilen iki riskten birini -- modern KISITLI ~50-isim shortable rejimin erken genis-rejimden
  FARKLI davranmasini -- dogrudan teyit ediyor. Tek bir kararli yon yok -> tradeable-DEGIL.
- **Lag/yayin-gecikmesi tutarsiz**: primary(m+1) ve robust(m+2) LIQUID L-S isaretleri ZIT (-0.63% vs +0.33%),
  ikisi de anlamsiz. Sinyal yayin-gecikmesi varsayimina dayaniksiz -> ek bir kirilganlik bulgusu.
- **ALL daha-genis ama yine bos**: erken-rejim ~290-325 isim genis kesitte bile LOW-rel net ~0 (t=-0.36)
  ve L-S ~0 (t=0.10). Genislik anlamlilik getirmiyor; sinyal-icerigi yok.
- **Yapisal-secili ornek (DURUST caveat)**: short-yasagi-bosluklari (2020, 2023-24) ve modern thin shortable
  evren olcumu kacinilmaz-bicimde sansurluyor; AYLIK granularite gunluk short-akim zamanlamasini kacirir.
  US/DM'de robust olan anomali burada bu uc yapisal-engelle bulunamiyor -- null'i bunlar baglaminda oku.

## Hukum: SHORT-INTENSITY-NOT-TRADEABLE (no deployable edge)
Gercekten-yeni bir eksen (short-selling positioning), yeni-kesfedilen offline arsivle GERCEK-veride acildi ve
olculdu: BIST likit-evrende DUSUK-short-yogunlugu deploy-formunda prim YOK; LOW-bacak (anlamsizca ve
tez-tersine) underperform, L-S spread ~0 ve lag'lere gore isaret-tutarsiz. Teshis SIGNIFICANCE/SIGN-duvari +
LIQUID rejim-INSTABILITESI (cost-duvari degil) -- her ikisi de Stage-0'da ON-BEYAN edildi. META-BULGU'nun
(graveyard) yeni bir teyidi, simdi short-konumlanma ekseninde; ek-olarak short-yasagi-bosluklari, thin
modern shortable-evren ve aylik-granularite yapisal-engelleri ON-BEYAN dogrulandi. Deploy-iddiasi YOK.
Sonuc kaydedildi (kutlama-yok). ONE on-kayitli tanim; varyant-supurme yapilmadi (p-hacking YOK).

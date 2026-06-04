# L15 -- INVESTMENT / ASSET-GROWTH (FF CMA) CROSS-SECTIONAL FACTOR (HUKUM: INVESTMENT-NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L15_investment_growth.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l15_investment_growth_results.json`. ASCII. OLCUM (yeni-FAKTOR, sentez-degil).
Yeni-veri-CEKIMI YOK, optimizasyon YOK, grid-supurme YOK, committed-motor SIFIR-dokunus, look-ahead-safe.

GERCEKTEN YENI faktor: g = equity_t/equity_{t-12mo}-1 (trailing-12-ay kitap-ozkaynak buyumesi).
Fama-French 5-faktor'un SON test-edilmemis ayagi (CMA = Conservative-Minus-Aggressive). Market onemsiz,
size/SMB ve value/HML mezarlikta, profitability/RMW = L14, investment/CMA = BU. Tek on-kayitli tanim
(varyant-supurme YOK = p-hacking YOK). Fiyat sinyalde YOK -> value-re-test DEGIL; L14 ROE'den de farkli
(seviye degil, BUYUME). Isaret: DUSUK-buyume (konservatif) = LONG, YUKSEK-buyume (agresif) = SHORT.

PROXY-CAVEAT (Stage-0'da ON-BEYAN): kitap-ozkaynak buyumesi FF'in toplam-AKTIF buyumesinin PROXY'sidir
(aktif paneli yok). Tutulan-kazanc + net-hisse-ihracini yakalar ama BORC-finansmanli aktif buyumesini
KACIRIR -> investment-faktorunun KISMI olcumu. Null, CMA'yi tumden curutmez; yalniz bu proxy'yi likit-BIST'te.

## Tasarim (donmus)
- Sinyal: g = equity_t/equity_{t-12mo}-1, her iki ozkaynak>0; `fundamentals_2019_2026.parquet` (69 buyume-ayi).
  RANK-tabanli tercile -> fat-tail buyume-outlier'ina dayanikli (gozlemde max ~6.7e4, min ~-1.0; winsorize-knob YOK).
- Look-ahead-safe: formasyon ayi M'de g = ay M-1'de biten trailing-12-ay degisimi (LAG=1 ay konservatif tampon;
  panel aylik-snapshot, equity yalniz rapor-YAYINLANINCA siciyor).
- Evren: ALL + LIQUID (>=1e7 TL trailing-63g medyan ADV). Benchmark: EW-full aylik (durust-bar).
- Portfoy: LONG bottom-growth (konservatif) tercile (deploy-kapi, market-relative) + akademik low-minus-high
  spread. K=1 PRIMARY, K=3 turnover-azaltma legi. D-207 per-isim gercekci maliyet. NW-t (HAC), rejim-split 2022-01.
- Keep-bar: K=1 LIQUID long-tercile rel-net>0 VE |NW-t|>=2 VE rejim-isaret-stabil.

## Olculen (88 formasyon ayi; 68 yatirimli)
| K / scope | long(low-g) size | turnover | costfree mean (t) | NET mean (t) | rejim-stabil | L-S(low-high) mean (t) | realized-cost |
|---|---:|---:|---|---|:--:|---|---:|
| K=1 ALL | ~149 | 0.130 | -0.32%/ay (t=-1.45) | -0.55%/ay (t=-2.60) | EVET(neg) | +0.12% (t=0.30) | 124bp |
| **K=1 LIQUID** | ~25 | 0.204 | **-0.42%/ay (t=-0.68)** | **-0.57%/ay (t=-0.92)** | EVET(neg) | +0.33% (t=0.46) | **47bp** |
| K=3 ALL | ~150 | 0.086 | -0.38%/ay (t=-1.89) | -0.54%/ay (t=-2.75) | EVET(neg) | -0.09% (t=-0.28) | 116bp |
| K=3 LIQUID | ~25 | 0.130 | -0.45%/ay (t=-0.76) | -0.57%/ay (t=-0.95) | EVET(neg) | +0.73% (t=1.11) | 46bp |

## Okuma (beklenti DOGRULANDI -- durust-null)
- **Investment-primi YOK (deploy-formunda)**: deploy-kapisi (K=1 LIQUID long bottom-growth tercile)
  market-relative net = -0.57%/ay, ANLAMSIZ (t=-0.92). Keep-bar GECMEZ. `INVESTMENT-NOT-TRADEABLE`.
- **Bu bir COST-duvari DEGIL, bir SIGNIFICANCE/SIGN duvari** (L14-ROE ile ayni teshis): costfree
  (maliyet-ONCESI) low-growth likit getirisi ZATEN negatif (t=-0.68). Maliyet (~47bp, turnover dusuk 0.20)
  sinyali oldurmuyor; ortada oldurulecek brut-LONG-sinyal YOK.
- **Benchmark-bagimsiz teyit = long-short spread ~0**: low-growth minus high-growth (size-confound'dan
  goreli-bagisik) LIQUID'te +0.33%/ay ama t=0.46 -> sifirdan ayirt-edilemez. Sonuc EW-full secimine bagli degil.
- **DURUST WRINKLE (CMA-yonunde zayif iz, ama tradeable-DEGIL)**: K=3 LIQUID'te HIGH-growth (agresif)
  short-tercile ANLAMLI negatif (costfree t=-2.68, net t=-2.95) -> agresif-isimler underperform ediyor,
  ki bu TAM CMA-yonu. AMA (a) deploy-kapi long-ONLY low-growth bacagidir ve o anlamsiz; (b) low-minus-high
  spread |t|>=2'yi gecmiyor (K=3 LIQUID +0.73%/ay t=1.11 en-yuksek ama yine <2). Yani agresif-bacakta
  faint-yon var, long-only deploy-formunda ve spread'de anlamliliga ULASMIYOR. Iz NOT EDILDI, edge-DEGIL.
- **Size-confound (DURUST)**: ALL'da her iki tercile de EW-full'a gore negatif (EW-full microcap-agirlikli;
  buyume-terciller daha-buyuk/olgun isimler) -> ALL NET t=-2.6 ama YANLIS-isaret (long-tercile rel-negatif),
  deploy-degil; long-short ALL ~0 (t=0.30) bunu zaten goreli-bagisik teyit ediyor.
- **Dusuk-turnover hipotezi dogrulandi ama kurtarmadi**: investment yavas-sinyal (turnover 0.13-0.20,
  L14-kalite ile ayni mertebede) -> maliyet drag'i kucuk; ama brut-LONG-sinyal yok oldugu icin onemsiz.
- **Rejim-stabil (negatif)**: hem pre- hem post-2022 negatif -> tutarli bir (non)deploy-etki, gecici-anomali degil.

## Hukum: INVESTMENT-NOT-TRADEABLE (no deployable edge)
FF5'in son test-edilmemis ayagi olculdu ve graveyard'a temiz-eklendi: BIST likit-evrende konservatif
(dusuk-ozkaynak-buyume) deploy-formunda investment-primi YOK; long-only low-growth likit isimler EW-full'a
gore (anlamsizca) underperform, low-minus-high spread'i ~0. Agresif-bacakta CMA-yonunde zayif-iz var ama
long-only deploy-kapisinda ve spread'de anlamliliga ulasmiyor. Teshis SIGNIFICANCE/SIGN-duvari (cost-duvari
degil; equity-growth PROXY-caveat ON-BEYAN) -> META-BULGU'nun yeni bir teyidi, simdi investment-ekseninde.
Bununla FF5-cross-sectional-fundamental supurmesi (size/value-mezarlik, RMW=L14, CMA=L15) TUKETILDI.
Deploy-iddiasi YOK. Sonuc kaydedildi (kutlama-yok). ONE on-kayitli tanim; varyant-supurme yapilmadi.

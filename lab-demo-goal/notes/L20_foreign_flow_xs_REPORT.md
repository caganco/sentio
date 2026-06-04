# L20 -- FOREIGN-FLOW CROSS-SECTIONAL FACTOR (HUKUM: FOREIGN-FLOW-XS-NOT-TRADEABLE)

Stage-0: `lab-demo-goal/stage0/STAGE0_L20_foreign_flow_xs.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l20_foreign_flow_xs_results.json`. ASCII. OLCUM (yeni-FAKTOR, sentez-degil).
GERCEK-VERI testi. Yeni-veri-CEKIMI YOK (var-olan offline arsiv), optimizasyon YOK, grid-supurme YOK,
committed-motor SIFIR-dokunus, look-ahead-safe. repo READ-ONLY (yazim yalniz lab-demo-goal/ altinda).

GERCEKTEN YENI eksen: foreign_imbalance(sembol, ay m) = (yabanci-alis-TL(m) - yabanci-satis-TL(m)) /
(alis-TL + satis-TL), [-1,+1] sinirli, olcek-bagimsiz. Bu bir per-stock KONUMLANMA/AKIM ekseni
(yabanci-yatirimci net-akimi). D-211 GRAVEYARD'indan AYRI: D-211 yabanci-akimi AGGREGATE INDEX-TIMING
(piyasa-seviyesi) idi; bu ise CROSS-SECTIONAL per-stock varyant (yabancinin HANGI hisseleri net-topladigi).
Yeni etkinlesti cunku gercek bir offline yabanci-akim arsivi kesfedildi (`data/bist_datastore_archive/
foreign_flow`, aylik per-stock alis/satis-TL, legacy OLE2 .xls, 1997-2026). Tez (Richards 2005,
Froot-O'Connell-Seasholes 2001 EM): yabanci net-alisi (yuksek imbalance) sonradan OUTPERFORM (kisa-vadeli
sureklilik/bilgili-akim). Deploy-formu: likit-evrende YUKSEK-imbalance tercile'i LONG, market-relative,
gercekci-maliyet-net.

DURUST BEKLENTI (ON-BEYAN, Stage-0): prior MODERATE-to-WEAK. Lehte: cross-sectional yabanci-akim
ongorulebilirligi EM'de destekli. Aleyhte: (a) yabanci-akim TIMING ekseni index-seviyede zaten graveyard
(D-211); (b) akim-yonu AYNI-AY (contemporaneous) getiriyle KISMEN-MEKANIK iliskilidir (yabanci gecmis-performans
kovalar) -> look-ahead-safe m+1 testi bu es-zamanli co-move'u DISLAYINCA cok-az yakalar, hatta TERSINE donebilir;
(c) AYLIK granularite zamanlamayi zayiflatir; (d) imbalance orani dusuk-aktivite isimlerde gurultulu
(LIQUID filtresi hafifletir). En-olasi sonuc: anlamlilik-duvari / es-zamanli-co-move / rejim-instabilitesi.
Kutlama beklentisi YOK; sonuc ne olursa kaydedilir.

## Tasarim (donmus)
- Sinyal: imbalance = (alis-TL - satis-TL)/(alis-TL + satis-TL). Her ay cross-sectional tercile. TEK
  on-kayitli tanim (alternatif-normalizasyon YOK, grid YOK -> multiple-testing YOK). YUKSEK imbalance = LONG
  (yabanci net-alis bacagi), DUSUK = SHORT. Teyit L-S = mean(HIGH) - mean(LOW).
- Look-ahead-safe: PRIMARY ay m sinyali -> ay m+1 forward getiri (pozisyon m-sonunda kurulur; varsayim:
  aylik yabanci-bulteni ay-sonunda yayinlanir, m+1 basinda mevcuttur). ROBUST skip-ay: m -> m+2 (kesin
  look-ahead-safe; yayin-gecikmesine duyarlilik siniri). IKISI de raporlanir.
- Evren: ALL + LIQUID (>=1e7 TL trailing-63-islem-gunu medyan value_tl, D-205 mutlak-esik). min 30 isim/ay.
  Sembol-join: yabanci sembollerinden sondaki ".E" atilir -> ciplak fiyat-ticker'a eslenir.
- Getiri: adjusted_close(forward-ay-sonu)/adjusted_close(giris-ay-sonu)-1 (yalniz takvim-bosluksuz ardisik ay);
  market-relative = ayni-kapsam EW-evren forward getirisi cikarilarak. Benchmark: EW same-scope.
- Maliyet: round_trip_bps=40 (likit orta-aralik, D-207/D-208) x LONG-sepetin aylik turnover'i.
- Keep-bar: LIQUID HIGH-imbalance tercile market-relative NET mean>0 VE |NW-t|>=2 (HAC lag 6) VE
  rejim-isaret-stabil (2022-01-01 split). Aksi -> FOREIGN-FLOW-XS-NOT-TRADEABLE. Iki-yonlu hukum
  (D-205/D-209/L19 deseni). ANLAMLI-NEGATIF spread (yabanci-alinan UNDERperform = reversal) de on-kayitli
  edge DEGIL -> NOT-TRADEABLE (reversal taze on-kayit ister).

## Olculen (yabanci: 87 ay / 41643 gozlem; sinyal-join: 87 ay / 41555 gozlem; pencere 2019-01..2026-04)
| scope / lag | aylar | avg isim | HIGH-rel gross (t) | HIGH-rel NET (t) | rejim-stabil | L-S net (t) | turnover | realized-cost | breakeven |
|---|---:|---:|---|---|:--:|---|---:|---:|---:|
| ALL primary m+1 | 87 | 476.8 | +0.63%/ay (t=3.46) | +0.37%/ay (t=2.03) | EVET(poz) | -0.18% (t=-0.44) | 0.64 | 25.7bp | 97.8bp |
| ALL robust m+2 | 86 | 474.5 | +0.65%/ay (t=2.13) | +0.39%/ay (t=1.29) | EVET(poz) | +0.16% (t=0.40) | 0.64 | 25.7bp | 101.2bp |
| **LIQUID primary m+1** | 85 | 79.4 | **+0.17%/ay (t=0.57)** | **-0.10%/ay (t=-0.35)** | **HAYIR** | -0.90% (t=-1.66) | 0.69 | 27.7bp | 24.9bp |
| LIQUID robust m+2 | 84 | 78.3 | +0.34%/ay (t=1.31) | +0.07%/ay (t=0.25) | HAYIR | -0.15% (t=-0.42) | 0.69 | 27.8bp | 49.5bp |

LIQUID rejim-detay (primary m+1): pre-2022 mean=-0.82%/ay, post-2022 mean=+0.35%/ay -> ISARET DONUYOR.
ALL rejim-detay (primary m+1): pre=+0.16%/ay, post=+0.52%/ay -> stabil-poz ama (asagi) deploy-kapisi DEGIL.

## Okuma (beklenti DOGRULANDI -- durust-null)
- **Deploy-kapisi (LIQUID HIGH-imbalance, primary m+1) GECMEZ**: market-relative net = -0.10%/ay, ANLAMSIZ
  (t=-0.35), YANLIS-isaret (yabanci-alinan likit-isimler underperform-egilimli) ve rejim-INSTABIL. Keep-bar
  uc-kosulun UCUNDE de duser. `FOREIGN-FLOW-XS-NOT-TRADEABLE`.
- **"Anlamli" ALL m+1 long-bacak (net t=2.03) bir FAKTOR DEGIL, evren-secim/microcap artefakti**: (1) L-S
  spread'i (HIGH-LOW) ANLAMSIZ (gross t=0.81, net t=-0.44) -> imbalance siralamasinin monoton-getirisi YOK;
  (2) hem HIGH hem LOW tercile orta-tercile'i geciyor (U-bicim) -> bu yabanci-alis sinyali degil, ~477-isimlik
  microcap-agirlikli evrende uc-tercile/likidite gurultusu; (3) m+2'de long-bacak t=2.03 -> 1.29'a coker; (4)
  bu ~477 isim 40bp'de gercekci tradeable degil. Yani anlamli-gorunen tek hucre on-kayitli kapidan (LIQUID)
  DISARIDA ve teyit-spread'i tarafindan REDDEDILIYOR -> edge sayilmaz (p-hacking-koruma calisti).
- **Cost-duvari DEGIL**: deploy-kapsaminda (LIQUID) gross HIGH-bacak zaten ~0 (t=0.57) ve net ~0; oldurulecek
  brut sinyal YOK. Turnover ~0.69, realized-cost ~28bp; breakeven 24.9bp gross'un altinda -> maliyet sorun degil,
  SINYAL yok.
- **Es-zamanli co-move teyidi**: ON-BEYAN edildigi gibi, yabanci akim-yonu ayni-ay performansa baglidir
  (performans-kovalama); look-ahead-safe m+1 bunu disladiginda likit kesitte forward sinyal NULL/zayif-reversal.
  Bu, Stage-0'daki (b) riskini dogrudan teyit eder.
- **Rejim-INSTABILITESI (LIQUID)**: deploy-kapsaminda isaret 2022'de DONUYOR (pre -0.82%/ay, post +0.35%/ay)
  -> tek kararli yon yok. ON-BEYAN edilen rejim-riski teyit edildi.
- **Lag tutarsizligi**: LIQUID primary(m+1) ve robust(m+2) long-bacak isaretleri zit/anlamsiz; yayin-gecikmesi
  varsayimina dayaniksiz -> ek kirilganlik.

## Hukum: FOREIGN-FLOW-XS-NOT-TRADEABLE (no deployable edge)
Gercekten-yeni bir eksen (per-stock yabanci net-akim konumlanmasi), yeni-kesfedilen offline arsivle GERCEK-veride
acildi ve olculdu: BIST likit-evrende YUKSEK-yabanci-imbalance deploy-formunda prim YOK; HIGH-bacak net ~0
(anlamsiz, hafifce tez-tersine), L-S spread ~0/negatif, rejim-isareti 2022'de donuyor, lag'lere gore tutarsiz.
ALL-kapsamdaki anlamli-gorunen long-bacak (t=2.03) on-kayitli LIQUID-kapinin DISINDA, monoton-spread'siz,
U-bicimli microcap artefakti -> edge degil. Teshis SIGNIFICANCE/SIGN-duvari + es-zamanli-co-move (forward-DEGIL)
+ LIQUID rejim-INSTABILITESI (cost-duvari degil) -- hepsi Stage-0'da ON-BEYAN edildi. D-211 (yabanci index-timing
graveyard) artik per-stock cross-sectional eksende de NULL ile tamamlandi. Deploy-iddiasi YOK. Sonuc kaydedildi
(kutlama-yok). TEK on-kayitli tanim; varyant-supurme yapilmadi (p-hacking YOK). N<=1 (gercek-test). L20 ARSIVLENDI.

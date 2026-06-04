# L18 -- VIOP / DERIVATIVES FEASIBILITY + INDEX-BASIS OVERLAY FORWARD-SCAFFOLD (HUKUM: SCAFFOLD-SELF-TEST PASS)

Stage-0: `lab-demo-goal/stage0/STAGE0_L18_viop_feasibility.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l18_viop_feasibility_results.json`. ASCII. VERI-CEKIMI DEGIL, network YOK,
yeni-edge YOK. Spec ACIKCA VIOP istedi. L11-deseni: aday VIOP faktorlerini on-kaydet, BIST-VIOP
likiditesine gore HANGI-tasarimin uygulanabilir oldugunu muhakeme et, ve uygulanabilir tek tasarimi
(XU030 index-futures basis TIMING overlay) sentetik-veride offline-dogrula.

## STAGE-0 PREMISE FALSIFIKASYONU (sonuc-aninda kayit)
Stage-0 honest_expectation "offline HIC VIOP verisi YOK (dogrulanmis-yoklik)" diye ON-BEYAN etmisti.
Bu YANLIS cikti: `data/bist_datastore_archive/viop` LOKAL MEVCUT (331 dosya, 256 EOD-ayi, 2005-02 .. 2026-05):
per-kontrat gunluk settlement/OHLC/VWAP/traded-value + ACIK-POZISYON (open interest); XU030 vadeli
en-likit kontrat + likit buyuk-cap single-stock-futures alt-kumesi (AKBNK/EREGL/BIMAS...). Stage-0 tarihsel
on-kayit olarak DONUK birakildi; falsifikasyon yalniz BURADA (sonuc-aninda) kaydedildi -- keep-bar/test-tasarim
DEGISMEDI, yalniz veri-durum beklentisi yanlisti. "Tum single-stock VIOP illikit" iddiasi da KISMEN-revize
(likit alt-kume var).

## Tasarim (Stage-0'da donmus -- forward gercek-mod)
- Feasibility-muhakemesi (on-kayitli): cross-sectional single-stock VIOP faktoru likidite-infeasible
  (L7-duvari instrument-varlik seviyesinde); tek likit-ulasilabilir oyun INDEX-seviye basis/term-structure
  TIMING OVERLAY (stock-selection DEGIL, market-timing -> D-211 foreign-flow-index-timing-bitisigi).
- Sinyal: state(t) = (futures_t - spot_t)/spot_t (+ near-far term-structure); pozisyon t+1'de alinir;
  [+1,+H] index getirisi ongorulur. Look-ahead-safe: yalniz close-t bilgisi t+1 pozisyonuna girer.
- Stat: overlay gunluk-aktif-getiri NW-t; keep-bar = mean-active>0 AND |NW-t|>=2 AND regime-stabil
  (2022-01-01) AND futures-round-trip-maliyet sonrasi yasar. Verdict: gecerse VIOP-OVERLAY TRADEABLE-EDGE;
  yoksa VIOP-OVERLAY-NOT-TRADEABLE. Single-stock cross-section ON-BEYAN likidite-infeasible (keep-bar yok).

## Offline self-validation (sentetik, seed=20260604)
Gercek-tehlikeye SADIK sentetik: ZAYIF lagged-ongorulebilirlik (beta_pred=0.002, dunku-basis -> bugunku-getiri)
+ GUCLU ayni-gun es-hareket (gamma_contemp=0.010, basis ve spot ayni-gun birlikte). Look-ahead-safe tasarim
MODEST-anlamli edge geri-kazanir; CONTEMPORANEOUS basis'e kosullanan tasarim buyuk es-hareketi SIZDIRIR.

| assert | sonuc | NW-t |
|---|---|---:|
| RECOVERY (dunku-basis overlay sign-correct, \|t\|>=2) | **PASS** | 5.08 |
| PLACEBO (basis-sinyali shuffle -> icerik yok, \|t\|<2) | **PASS** | -0.77 |
| LOOK-AHEAD (ayni-gun basis es-hareketi SIZDIRIR, \|t\| safe'ten cok-buyuk) | **PASS** | 26.09 (vs 5.08) |

all_asserts_pass = **True**. Pipeline DOGRU, look-ahead-GUVENLI; leak-assert dogru-sebeple geciyor
(ayni-gun es-hareket safe-lagged tasarimdan cok-daha-buyuk |t| veriyor).

## Okuma
- **Mekanik kanit, edge-kaniti DEGIL**: sentetik yalniz planted ZAYIF-lagged + GUCLU-contemporaneous
  yapinin pipeline tarafindan dogru ayristirildigini kanitlar. Gercek XU030-basis edge'i hakkinda HICBIR sey demez.
- **VIOP veri-engeli KALKTI** (premise-falsifikasyonu): ham EOD arsivi lokal -> ag-fetch GEREKMEZ.
- **Gercek-run icin EKSIK = INSA-EDILMIS baz-paneli**: front-month XU030 vadeli settlement, gunluk SPOT
  XU030 endeks-seviyesine hizalanmis. Bu bir LOKAL-BUILD'tir (network DEGIL) + the maintainer-go-ahead.
- **Prior ZAYIF (DURUST)**: index-basis bir TIMING-overlay'dir (cross-sectional DEGIL), zaten-graveyardlanan
  foreign-flow index-timing'e (D-211) bitisik -> veri-olsa-bile prior zayif.
- **Ek-eksen (on-kayitsiz)**: ACIK-POZISYON (open interest) + OI-degisimi arsivde var -> ek bir konumlanma
  sinyali (index- veya single-stock); henuz on-kayit-edilmedi.

## Hukum: SCAFFOLD-SELF-TEST PASS (no deployable edge)
Specin VIOP avenusu kristalize edildi. Stage-0 "VIOP-yok" premise'i YANLIS cikti (ham EOD arsivi lokal,
2005-2026, settlement/OHLC/OI, XU030 en-likit). Index-basis TIMING overlay pipeline-dogrulandi ama ZAYIF-prior
tasiyor (timing-overlay, foreign-flow-bitisik). Gercek-run INSA-EDILMIS baz-paneli (front XU030 vadeli vs
gunluk SPOT XU030) + the maintainer-go-ahead bekler -- ag-fetch DEGIL, lokal-build. N<=1 (scaffold). L18 ARSIVLENDI.
Yeni-edge iddiasi YOK.

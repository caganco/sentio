# L22 -- VIOP BIST30 INDEX-FUTURES TERM-STRUCTURE (spot-free basis) (HUKUM: VIOP-TS-FEASIBILITY-BLOCKED)

Stage-0: `lab-demo-goal/stage0/STAGE0_L22_viop_term_structure.json` (sonuc-ONCESI donduruldu).
Sonuc: `lab-demo-goal/results/l22_viop_term_structure_results.json`. ASCII. OLCUM (gercek-VERI, sentez-degil).
GERCEK-VERI testi (lokal VIOP arsivi). Yeni-veri-CEKIMI YOK, optimizasyon YOK, grid-supurme YOK,
committed-motor SIFIR-dokunus, look-ahead-safe. repo READ-ONLY (yazim yalniz lab-demo-goal/ altinda).

GERCEKTEN YENI eksen: TUREV TERIM-YAPISI (futures egrisi sekli). L1-L21'in HICBIRI futures egrisini
olcmedi -- fiyat/hacim/temel/sentiment/short/yabanci-akim/tek-hisse-OI eksenlerinden KATEGORIK farkli.
L18 (VIOP index-basis FORWARD-SCAFFOLD) bu ekseni on-kayitlamis ama "gercek-run LOKAL baz-paneli ister"
diye birakmisti. L22 o scaffold'u GERCEK-OLCUME cevirir VE ekseni DURUSTCE kapatir.

Veri: `data/bist_datastore_archive/viop` VIOP_GUNSONU_FIYATHACIM aylik CSV (2017-03..2026-05). INF segmenti =
BIST30 INDEKS FUTURES (D_IX_FUT / DE_BIST30_FUT, dayanak D_XU030D), seri kodu F_XU030MMYY (MM=vade-ayi, YY=yil),
SETTLEMENT PRICE = col7. Her ay-sonu (son islem gunu) 3-4 vade listeli, settlement>0 -> egri HER ay hesaplanir.

## Tasarim (donmus, TEK on-kayitli tanim)
- Egri: ay-sonu m'de vadeleri dte'ye gore sirala; F1 = on-ay (dte>=10g), F2 = sonraki vade.
- Sinyal: slope_ann(m) = ln(F2.settle/F1.settle) / ((F2.dte - F1.dte)/365) -- yillik log terim-yapisi egimi
  (futures-imali tasima/carry). TEK tanim (winsorize-yok, grid-yok, alternatif-normalizasyon-yok -> multiple-testing YOK).
- TEZ (on-kayit, ZAYIF prior): dik-contango (yuksek slope) -> sonraki SPOT getiri DAHA DUSUK (negatif on-kayitli isaret).
  Deploy-formu: indeks-timing overlay'i (egri-ucuzken long, zenginken flat/short).
- Look-ahead-safe: slope(m) gun-m settlement'inden (ayni-gun public); ileri-getiri kesin m->m+1.

## KRITIK fizibilite/metodoloji (Stage-0'da ON-BEYAN, donmus)
1. TEMIZ test (slope -> SPOT XU030 getirisi) OFFLINE DATA-BLOCKED: futures-doneminde (>=2017) temiz gunluk/haftalik
   SPOT XU030 (BIST30 nakit endeks) SEVIYESI lokal-YOK. Dogrulandi:
   - prices_official (PP_GUNSONUFIYATHACIM) "BIST 30 INDEX" kolonu tasir AMA arsiv 2016-11'de BITER -> futures ile
     SIFIR-ortusme (runtime: futures-doneminde 0 resmi-gunluk dosya).
   - prices_weekly (PP_HAFTALIKOZET) per-hisse haftalik OHLC xlsx -> endeks-seviye kolonu YOK.
   - exposure yalniz xu100 (BIST100 != BIST30, YANLIS endeks), 2019+.
   - adjusted_prices'tan resmi-bolu(divisor)-tabanli BIST30 seviyesi REKONSTRUKSIYONU float/divisor-hatasi -> bazi sismeyle yikar.
2. TEK offline-hesaplanabilir varyant (slope -> futures'in KENDI ileri-getirisi) MEKANIK-CONFOUNDED: tutulan ileri-vade
   sozlesme vade-yaklastikca spota dogru cozulur (roll-down ~ -slope*dt) -> yuksek-slope mekanik-olarak negatif getiri-
   bileseni dogurur; bu, prediksiyon DEGIL saf-carry-mekaniginden gelen SAHTE bir slope<->getiri iliskisidir.

## Olculen (egri: 389 satir / 111 ay-sonu / 110 ileri-gozlem; pencere 2017-03..2026-05)
- Egri-betimi: yillik slope medyan **+0.1918** (p25 +0.0997 / p75 +0.2963), ay-sonlarin **%98.2'si** contango (slope>0).
  -> kalici dik-contango (pozitif tasima). ANCAK slope-TLREF korelasyonu (2019+) **-0.17** (zayif/negatif) -> near-near
  yillik slope GURULTULU bir carry-vekili, temiz risksiz-faiz-takipcisi DEGIL.
- Roll-down confound DEMO (gercek-sayilarla):
  - Naif ret_F2 ~ slope: katsayi **-0.77, NW-t=-1.08** -> ANLAMSIZ (|t|<2).
  - corr(ret_F2, carry_rolldown) = **+0.12** -> roll-down suruklemesi ISARET-olarak var AMA spot-kaynakli aylik
    varyansa gore KUCUK (ret_F2'yi domine ETMIYOR).
  - carry-soyulmus rezidu ~ slope: katsayi -0.69, **NW-t=-0.97** -> ANLAMSIZ.
  - rejim: corr_pre(2022-oncesi)=-0.15, corr_post=-0.04 -> her-iki tarafta zayif-negatif (anlamsiz).

## Okuma (beklenti DOGRULANDI -- durust-null + feasibility-block)
- **HICBIR offline-testte anlamli prediktif icerik YOK**: ne naif (t=-1.08) ne carry-soyulmus (t=-0.97) slope-katsayisi
  anlamliliga ulasir. 110 aylik-gozlem (dusuk-power, tek-zaman-serisi indeks-timing) + tespit-edilebilir sinyal-yok.
- **Baglayan kisit = GERCEK offline DATA-BLOK + roll-down confound**: temiz tez-testi (slope -> SPOT getirisi) icin gereken
  temiz gunluk/haftalik SPOT XU030 seviyesi 2017-2026 lokal-YOK; tek offline-varyant (slope -> futures kendi-getirisi)
  ilkesel-olarak roll-down ile confounded (burada zaten anlamsiz). Ikisi birlikte -> deploy-iddiasi MUMKUN-DEGIL.
- **Egri carry-domine, sentiment-degil**: kalici dik-contango + slope'un risksiz-faizle zayif/gurultulu iliskisi ->
  egri-egimi buyuk-olcude tasima(carry)/gurultu, temiz-konumlanma-sinyali degil. (Stage-0 "faizi takip eder" beklentisi
  KISMEN duzeltildi: contango kalici ama slope-TLREF takibi ZAYIF.)
- **Cost-duvari DEGIL, anlamlilik-duvari DEGIL -- FEASIBILITY/VERI-BLOK**: oldurulecek anlamli sinyal yok; deploy-edilebilir
  bir defter kurmak (futures kendi-getirisi uzerinde) confounded olurdu -> backtest BILEREK kurulmadi (yaniltici olurdu).

## Hukum: VIOP-TS-FEASIBILITY-BLOCKED (no deployable edge)
Gercekten-yeni eksen (BIST30 futures terim-yapisi) lokal VIOP arsiviyle GERCEK-olculdu (111 ay-sonu, 2017-2026): egri
kalici dik-contango. Ama deploy-edilebilir indeks-timing edge'i OFFLINE kurulamaz: (a) temiz tez-testi (slope->SPOT getiri)
icin temiz spot XU030 seviyesi 2017-2026 lokal-YOK (resmi-gunluk 2016-11'de biter; haftalik endeks-seviye tasimaz; xu100
yanlis-endeks); (b) tek offline-varyant (slope->futures kendi-getirisi) roll-down ile mekanik-confounded; uustelik burada
naif VE carry-soyulmus slope-katsayilari ANLAMSIZ. Deger: L18'in acik biraktigi index-basis eksenini DURUSTCE KAPATIR ve
GERCEK bir tartisilamaz-offline VERI-kisitini belgeler (mandanin "blogu belgele" maddesi). Spot-basis, harici gunluk SPOT
XU030 seviye-serisi gerektiren bir the maintainer-kapili ILERI-aday olarak loglandi. Deploy-iddiasi YOK. Sonuc kaydedildi (kutlama-yok).
TEK on-kayitli tanim; varyant-supurme yok (p-hacking YOK). L22 ARSIVLENDI.

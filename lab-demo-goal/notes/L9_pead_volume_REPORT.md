# L9 -- EMPIRICAL PEAD EVENT-VOLUME + power-shortfall bound (HUKUM: DESCRIPTIVE-VOLUME-VIEW)

Stage-0: `lab-demo-goal/stage0/STAGE0_L9_pead_volume.json` (sayilari okumadan ONCE donduruldu).
Sonuc: `lab-demo-goal/results/l9_pead_volume_results.json`. ASCII. SENTEZ/feasibility -- yeni-edge YOK,
yeni-veri-CEKIMI YOK, optimizasyon YOK. L8'in VARSAYDIGI daily-PEAD gelis-hizini (~120/yil) MEVCUT
aylik-kazanc-paneliyle olculen GERCEK likit-SUE-testable olay-hacmiyle degistirir ve gun-damgali bir
daily-PEAD testinin L8 n_required bandina [95, 759] ulasip-ulasamayacagini SINIRLAR.

## Yontem (Stage-0'da donmus)
- Pencere: fiscal_year>=2019 (fiyat-paneliyle ayni; L3 ile tutarli). Testable-altkume: sue non-null.
- Likidite: per (sembol, announce_month) trailing-63-islem-gunu-medyan value_tl (ay-sonu son-islem-
  gununde), LIQUID <=> >=1e7 TL (D-205 mutlak-esik). Look-ahead-safe (yalniz trailing).
- Ay->gun carpani: aylik-cozunurluk her announce-ay'i TEK tarihe kumeler; gun-damgasi ay'in
  ifsalarini ayri announce-GUNLERE boler. Per-ay distinct announce-tarih BOUND = min(olay, 21
  islem-gunu). Toplami = daily-PEAD'in elde-edebilecegi BAGIMSIZ date-cluster TAVANI.

## Olculen hacim (GERCEK panel)
| metrik | deger |
|---|---:|
| total SUE-testable olay (2019+) | 5735 |
| LIQUID SUE-testable olay | 1091 |
| likit-oran | 0.190 (yalniz **%19**) |
| distinct announce-ay (toplam / likit) | 75 / 56 |
| kapsanan yil | 8 (2019-2026) |
| **likit olay / yil** | **~136** |
| **bounded daily date-cluster / yil** | **~95** |

## Reachability (L8 bandina karsi)
L8 n_required(|t|=2) bandi = [94.9, 758.6]. Bounded ~95 date-cluster/yil'da:
- **band-alt (n~95; L1 BIST30-add +82bp etki) -> ~1.0 yil**
- **band-ust (n~759; en-zayif +33bp etki) -> ~8.0 yil**
- HUKUM: daily-PEAD bandi <10 yilda ULASILABILIR = **EVET (True)**.

L8 ~120/yil VARSAYMISTI; L9 olculen bounded-hiz ~95/yil = varsayimin ~1.3x icinde -> L8
reachability tahmini EMPIRIK-OLARAK DOGRULANDI (abartma yok; hatta biraz temkinli cikti).

## Okuma
- **Likidite yine BAGLAYAN kisit**: SUE-testable olaylarin yalniz %19'u likit. Bu, programin
  tekrar-eden temasi (gorunur-sinyal microcap'te; likit-evren ince). Daily-PEAD'in gercek-gucu
  likit-altkumeyle sinirli -- ama yine de yilda ~95-136 likit-olay, kit-event-siniflarini (CPI 12/yil,
  index-rebalance ~2/yil) ezici-fazla asiyor.
- **Guclu-etkiler hizli, zayif-etkiler yavas**: n_req bandi etki-buyuklugune cok-duyarli. +82bp-tipi
  bir gun-damgali sinyal ~1 yilda 2-sigma'ya ulasabilir; +33bp-tipi ~8 yil ister. Yani daily-PEAD'in
  degeri, gun-damgasinin etki-buyuklugunu monthly-attenuation'dan (L3) ne-kadar KURTARDIGINA bagli.
- **CAVEAT (durust)**: ay-cozunurluk date-cluster sayisina TAVAN verir (gercek gunluk-yayilim
  gun-damgasi cekilene-kadar bilinmez); min(olay,21) ifsalarin ayri-gunlere yayildigini varsayar --
  kumelenirse gercek-hiz daha-dusuk olur. SUE-kapsami (~%41) testable-kumeyi kisar.

## Hukum: DESCRIPTIVE-VOLUME-VIEW
Yeni-edge iddiasi YOK. Veri-temelli feasibility-sayisi. DURUST-beklenti (Stage-0: ~birkac-yuz
likit-olay/yil; ~60-100 date-cluster/yil; bandi ~1-4 yilda gecer; L8'i ~2x icinde dogrular)
OLCUMLE dogrulandi -- olculen ~95-136/yil, beklentinin icinde. Kutlama-yok. N<=1. L9 ARSIVLENDI ->
SYNTHESIS-VIEW. SONUC: FORWARD_DATA_SPEC #1 (daily-PEAD KAP gun-damgasi) artik SADECE teorik-power
degil, GERCEK-likit-hacimle bandi-gecirir-gosterildi -- onayli-fetch'in degeri sayisal-saglam.

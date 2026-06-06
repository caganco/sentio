# D-204 hi52 STRES-TEST -- gercekci-maliyet + vade + OOS + mekanizma + likidite-paradoksu

> Stage-0 on-kayit: `docs/yol1/STAGE0_d204.json` (config_version d204-v1, sonuclardan
> ONCE donduruldu). Ham sonuc: `docs/yol1/d204_results.json`. Motor:
> `src/screening/d204_hi52_stress.py`. Maliyet mekanigi: `src/screening/realistic_cost.py`
> (ballast'tan PORT, import DEGIL). Olcum geometrisi: `src/screening/d204_config.py`.
> Karar esikleri: `src/signals/thresholds.py` (D204_* blok, tek-kaynak).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N=1 aday (hi52 IZOLE). lambda_kyle DONMUS;
> kadans (1/2/3-ay) ve breakeven-grid raporlama VIEW'lari, "en iyi" SECILMEZ. D-203 donmus
> paneli aynen REUSE (ayni hash). Verdict bir deploy-ADAYI degerlendirmesidir; deployment
> karari ayri (maintainer).

## 1. Soru

D-203'te **hi52 (52wk-high proximity) = GERCEK-EDGE** cikti: en guclu aday, EW_FULL-relative
+%2.57/ay, NW t=3.19, primer 2022-01 split'te post>=pre, 5/5 gate -- sistemin **ilk
asteriksiz edge'i**. AMA "5-gate-gecti" != "deploy-edilebilir". D-203 dort caveat birakti
(flat-maliyet, aylik kadans, tek-uzun-rejim, mekanizma-acik-degil) ve EKLEME-3 besinciyi:
**likidite-paradoksu** -- D-203'te hi52 illikit(+%1.77) > likit(+%1.35), literaturun TERSI
(RR-043: likit > illikit). D-204 bu deploy-bosluguni kapatan stres-testidir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren / faktor / pencere / istatistik:** D-203'ten AYNEN reuse (ayni content-hash;
  motor yuklemede hash'i assert eder). hi52 tanimi D-203 ile birebir.
- **Gercekci per-stock maliyet (STRES-1):** round-trip = 2*(tek-yon-spread + tek-yon-impact)
  + komisyon(0, Midas). Spread = **Roll (1984)** close-only [2*sqrt(max(-cov(dp_t,dp_{t-1}),0))];
  D-202 paneli close-only oldugu icin Abdi-Ranaldo(2017) OHLC tahmincisi CALISMAZ, Roll onun
  close-only analogudur. **RR-015 tier half-spread** (mega/large/mid/micro) model-BAGIMSIZ
  capraz-kontrol (Roll 0/tanimsiz cikinca devreye girer). Impact = **Kyle (1985)** karekok
  [lambda*sigma*sqrt(order/adv)], lambda_kyle DONMUS. order_value = 300K-TL / 15 = 20K/pozisyon;
  adv = trailing-63g value_tl.
- **Ana hukum = BREAKEVEN bps** (model-bagimsiz): edge'i sifirlayan flat round-trip maliyet.

## 3. Bes stres -- sonuclar (primer: common pencere, aylik kadans)

### STRES-1 -- gercekci maliyet (ASIL HUKUM)

| olcum | deger |
|---|---|
| EW_FULL-relative, **maliyet-oncesi** | **+%2.57/ay**, NW t=**3.19** (D-203 edge'i birebir tekrarlandi) |
| EW_FULL-relative, **Roll-maliyet-sonrasi** | **-%0.32/ay**, NW t=**-0.38** (edge YOK) |
| EW_FULL-relative, **tier-maliyet-sonrasi** (capraz-kontrol) | +%1.06/ay |
| **breakeven** (edge'i sifirlayan flat round-trip) | **~302 bps** |
| **gerceklesen gercekci maliyet** (flat-bps-esdegeri) | **~340 bps** |

**Hukum:** gerceklesen maliyet (~340bp) > breakeven (~302bp) -> aylik hi52 edge'i gercekci
maliyet altinda SIFIRIN ALTINA dusuyor. Roll-leg maliyet-sonrasi negatif ve anlamsiz.

**EKLEME-A (roll-zero ayristirmasi):** degerlendirilen 40 458 (tarih,isim) hucresinin
**%51.9'unda Roll=0** (seri-kovaryans >= 0 -> tier-floor devreye). Yani maliyetin yaklasik
yarisi Roll-OLCULU, yarisi tier-IMPUTE. Ortalama round-trip: Roll-leg %3.72, tier-leg %1.84.
Maliyet bir tier-floor artefakti DEGIL -- Roll-olculu yari da yuksek (yuksek-turnover'in
ince isimlere carpmasi).

### STRES-2 -- vade / kadans

- **Tutus suresi:** ortalama **1.13 ay**, medyan **1.0 ay**; ortalama turnover **%88**. hi52
  pratikte her ay neredeyse TAM rotasyon -> maliyetin kok nedeni budur.
- **Kadans VIEW'lari** (common pencere; SECIM DEGIL, hepsi raporlanir):

  | kadans | maliyet-oncesi | Roll-maliyet-sonrasi | breakeven | gerceklesen maliyet |
  |---|---|---|---|---|
  | **1-ay (primer)** | +%2.57 | **-%0.32** | ~302bp | ~340bp |
  | 2-ay | +%3.86 | +%1.03 | inf (grid'de sifirlanmaz) | ~330bp |
  | 3-ay | +%2.28 | -%0.73 | ~270bp | ~357bp |

  **Onemli ama dikkatli okuma:** 2-ay kadansta maliyet-sonrasi edge POZITIF gorunuyor.
  ANCAK bu MONOTON DEGIL (3-ay yine basarisiz) -> 2-ay'i "deploy kadansi" diye secmek
  **cherry-picking = optimizasyon** olur ki D-204'te YASAK. Bu uc kadans ayni olcumun uc
  VIEW'idir; verdict primer (aylik, D-203-kiyaslanabilir) kadansta DONUKTUR. 2-ay'in tek,
  monoton-olmayan bir gozlem olarak hayatta-kalmasi gelecek bir spec icin ipucu olabilir
  (turnover-azaltma yonu), ama D-204 onu bir deploy-secimine donusturmez.

### STRES-3 -- OOS / rejim

Roll-maliyet-sonrasi relative seride walk-forward (split 2023-01-01): train(2019-22)
+%0.39, holdout(2023-26) **-%1.09**, both_positive=**False**. Disinflasyon 2024-26 alt-penceresi:
**-%0.76**. Maliyet-sonrasi edge in-sample split'i bile gecemiyor.

> **OOS-BOSLUK (zorunlu, her durumda beyan edilir):** ornek (2019-2026) tek-uzun
> yuksek-enflasyon rejimidir. Gercek enflasyon-normallesme OOS YOK -> rejim-degisim
> dayanikligi KANITLANAMAZ. Walk-forward in-sample; disinflasyon 2024-26 YALNIZCA zayif-proxy.
> pre-2019 acquisition reddedildi (corp-action-yok -> kirli, D-185-riski). Bu bir olcumdur;
> deployment ayri maintainer karari.

### STRES-4 -- mekanizma

- **hi52 vs mom120:** basket-overlap **%8.5**, long-short korelasyon **0.41**. hi52
  "sadece momentum" DEGIL -- ayri bir faktor (orta korelasyon, dusuk basket-ortusmesi).
- **Konsantrasyon (formal sektor verisi yok -> proxy):** basket'in %20'si bist100-uyesi,
  %40'i ust-mktval-tercilinde, basket boyu 15. Asiri mikrocap konsantrasyonu yok; orta/buyuk
  isimlere hafif tilt. Anchoring/George-Hwang proximity literaturuyle tutarli bir
  cross-sectional fenomen; ama yuksek turnover onu maliyet-altinda erityor.

### EKLEME-3 / H1 -- likidite paradoksu (COZULDU)

| tercil | maliyet-oncesi rel | Roll-maliyet-sonrasi rel | reel maliyet-sonrasi |
|---|---|---|---|
| likit | +%1.35 | **-%0.86** | +%1.10 |
| orta | +%0.71 | -%1.72 | +%0.17 |
| illikit | +%1.77 | **-%1.17** | +%0.73 |

- Maliyet-oncesi: illikit(+%1.77) > likit(+%1.35) -- D-203 tersligi tekrarlandi.
- **Roll-maliyet-sonrasi:** her uc tercil de NEGATIF; ve siralama TERSINE doner -- likit(-%0.86)
  > illikit(-%1.17). `illiquid_dominates_after_cost = False`, `liquid_positive_after_cost = False`.
- **Sonuc:** paradoks bir **MALIYET-SERABI**. Gercekci maliyet -- en sert illikit isimlere
  vurur -- illikit "primini" buharlastirir ve siralamayi literature (RR-043: likit > illikit)
  uygun hale getirir. Likit-tercil bile maliyet-sonrasi EW_FULL'u GECEMIYOR.

> Not: likit reel-maliyet-sonrasi (+%1.10) TLREF-mevduat-esigini (+%0.0222/ay) gecer, yani
> strateji enflasyonu mutlak-reel olarak yener; ama EW_FULL-RELATIVE (secim-edge'i)
> maliyet-sonrasi NEGATIF -- yani tum evreni esit-agirlik tutmaya kiyasla deger katmiyor.
> Deploy sorusu secim-edge'idir; o yuzden `liquid_positive_after_cost=False`.

## 4. EKLEME-B -- deploy esigi keyfi degil (TLREF-mevduat-reel-carry)

`D204_DEPLOY_MIN_LIQUID_NET = +0.000222` (proje-ilkesi "reel > max(TUFE, TLREF)"). Getiriler
zaten TUFE-deflate oldugundan esik = aylik reel-TLREF-carry = ort. (TLREF_t1/TLREF_t0)/(TUFE
orani) - 1. TLREF return-endeksi 2022-07'de basladigindan esik **2022-07..2026-04 (n=45 ay)**
uzerinde hesaplanir. Motor bu esigi donmus snapshot'lardan YENIDEN hesaplar ve
|hesap - 0.000222| <= 5e-6 assert eder (drift-guard). Kosumda dogrulandi:
recomputed = 0.000222, n=45, coverage_start = 2022-07-29.

## 5. HUKUM: GERCEK-ama-tradeable-DEGIL

hi52 **gercek bir cross-sectional fenomendir** (maliyet-oncesi +%2.57/ay, t=3.19) AMA
**deploy-edilebilir DEGILDIR**:

1. Gercekci round-trip maliyet (~340bp) breakeven'i (~302bp) GECER -- cunku strateji ayda
   ~%88 rotasyon yapar (tutus ~1 ay).
2. Likit-tercil maliyet-sonrasi secim-edge'i NEGATIF (-%0.86); likit_positive_after_cost=False.
3. Likidite-paradoksu bir maliyet-serabi olarak cozuldu (literature-uygun) -- illikit ustunluk
   maliyet-sonrasi kayboluyor.

Bu **temiz, degerli bir "denendi-ve-deploy-icin-reddedildi" arsiv sonucudur**: D-203'un
GERCEK-EDGE bulgusunu CURUTMEZ (fenomen gercek), ama deploy-bosluguni durustce kapatir
(tradeable degil). Karar-kurali Stage-0'da donduruldu, post-hoc gevsetilmedi. 2-ay kadansin
tek/monoton-olmayan hayatta-kalmasi gelecek bir "dusuk-turnover hi52" arastirmasi icin not
edildi; D-204 onu bir secime donusturmez.

## 6. Olcum-only / kisitlar

Optimizasyon yapilmadi (lambda_kyle donmus; kadans/breakeven VIEW). ballast import EDILMEDI
(PORT). yfinance-OHLC ve pre-2019 acquisition kullanilmadi (YASAK). D-203 motoru + paneli
kirilmadan/yeniden-olculmeden reuse edildi (Strangler). Dayanak: RR-015 sec.3.1 (tier
half-spread), RR-043 (likit>illikit literaturu); Roll(1984), Abdi-Ranaldo(2017), Kyle(1985),
Almgren et al.(2005).

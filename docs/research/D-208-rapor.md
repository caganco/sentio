# D-208 hi52 LIKIT RE-TEST -- D-205-REVISITED: duzeltilmis-maliyetle hi52-likit (ADIM-1)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d208.json` (sonuclardan ONCE donduruldu). Ham sonuc:
> `docs/yol1/d208_results.json`. Surucu: yerel betik (arsiv-destekli, CI-disi -- kote panel ENJEKTE edilir). Motor: `src/screening/d205_hi52_liquid.py` (D-205 ile
> AYNI; tek ekleme `quoted_panel` parametresi -- geriye-uyumlu pass-through). Duzeltilmis maliyet:
> `src/screening/realistic_cost.py` + `d204_hi52_stress.per_stock_cost_panel` + `quoted_spread.py`
> (D-207'den OLDUGU-GIBI reuse). Karar esikleri: `src/signals/thresholds.py` (D205_* + D207_* blok).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** D-208 = **D-205-REVISITED**: D-205 hi52-likit
> 5-gate olcumunu AYNEN tekrarlar, **YALNIZ maliyet girdisini** degistirir (D-207-duzeltilmis
> kote-birincil model). Sinyal/evren/benchmark/5-gate/verdict-kurali/deploy-esigi D-205 ile
> **BIREBIR**. Hicbir esik, sinyal ya da evren gevsetilmedi.
>
> **STRANGLER (sert-kisit):** D-205 kayitlari -- `docs/research/D-205-rapor.md`,
> `docs/yol1/STAGE0_d205.json`, `docs/yol1/d205_results.json` -- **DOKUNULMADI**. D-205 verdict'i
> tarihsel olarak gecerli kalir ("o-zamanki sisik-maliyet altinda verildi"). D-208 KENDI
> verdict'ini verir (duzeltilmis-maliyet altinda). Gecmis evrim silinmez.
>
> **N<=3 notu:** hi52'nin N<=3 butcesi (D-203 KESIN + D-204 STRES + D-205 LIKIT-ONCE) DOLU.
> D-208 bir 4. N-turu DEGIL; maliyet-PREMISI-degisen bir re-test'tir: NRR-010/D-207 YENI BILGI
> uretti (D-205 verdict'inin dayandigi maliyet modeli sisik idi ve duzeltildi), bu da AYNI adayi
> adil-zeminde yeniden-olcmeyi mesru kilar. Sinyal-yeniden-tanimi/esik-yeniden-secimi/evren-degisimi
> YOK -- yalniz duzeltilmis maliyet uygulandi. Bu bir REVISITED'dir, yeni-aday degil.

## 1. Soru

NRR-010 ortak islem-maliyet modelini likit-isimlerde **~12-25x sisik** teshis etti; D-207 onu
duzeltti (FIDELITY gecti: likit-mega round-trip 271-509bp -> 16-26bp; microcap impact GERCEK
kaldi). D-205, hi52-likit'i **YINE-TRADEABLE-DEGIL** ilan etmisti -- kismen bu **sisik maliyetle**
(gerceklesen ~298bp >> breakeven ~138bp -> gate5 maliyet-kapisi FAIL). Duzeltilmis ~maliyetle
breakeven-138 >> gerceklesen -> **maliyet-kapisi artik GECEBILIR.**

**D-208 sorusu:** sisik-maliyet karistirmasi kaldirilinca, hi52-likit **adil-zeminde** tradeable
mi? Bu, D-204/D-205 verdict'lerini gevsetmez; onlarin dayandigi tek-degisken (maliyet) duzeltilince
sonucun ne oldugunu OLCER.

**Onceden-ilan-edilmis durust beklenti (kutlama YOK):** maliyet-kapisi (gate5) muhtemelen GECER,
ama **istatistik-duvari (gate2: NW|t| >= 2) muhtemelen DURUR** -- hi52-likit'in maliyet-ONCESI
relatif edge'i zaten yalniz NW t=1.70 idi (CI sifiri ICERIYOR). Olasi hukum: "maliyet degil --
ANLAMLILIK olduruyor" -- ama bu kez **varsayimla degil, OLCUMLE.**

## 2. Olcum cercevesi (Stage-0'da donmus -- D-205 ile birebir)

- **Sinyal / evren / benchmark / 5-gate / istatistik / deploy-esigi:** D-205'ten **AYNEN** reuse
  (ayni content-hash; motor yuklemede hash assert eder, deploy-hurdle drift-guard'i gecti).
  hi52 = `close / rolling-252g-max`; likit-evren = trailing-63g-medyan-ADV >= **1e7 TL**;
  benchmark = **EW_FULL_LIQUID**; top-15, aylik rebalans; NW lags=3; null seed 12345/2000.
- **TEK FARK -- maliyet girdisi:** D-207-duzeltilmis `realistic_cost` (kote-birincil EOD-spread
  -> 252g-Roll geri-dusus -> re-olcekli tier; FIX-1 yari-spread x2; FIX-3 re-tier) D-205'in
  o-zamanki maliyetinin (21g-Roll-birincil + 2S cift-sayim + erisilemez D-204 tier'lari) yerine.
  Kyle impact (lambda=1.0, sigma-penceresi 21g) **DEGISMEDI** -- yalniz spread-leg + tier-tabani
  degisti (D-207 kapsami). Microcap impact GERCEK ve degismemis.
- **Kote panel:** likit-birlesim (338 isim) icin yerel EOD bid/ask arsivinden kurulup ENJEKTE
  edildi (window=63, min_coverage=21, span 2019-07..2026-04). **Kapsam %100** (338/338); kotesi
  olmayan gun/isimler 252g-Roll'a duser (modelin kendi belgelenmis hiyerarsisi). Arsiv CI'a girmez.

## 3. Sonuclar (primer: common pencere, aylik kadans, EW_FULL_LIQUID-relatif)

### 3.1 Sisik-vs-duzeltilmis (ASIL okuma -- TEK fark maliyet)

| olcum | D-205 (sisik maliyet) | D-208 (duzeltilmis maliyet) |
|---|---|---|
| EW_FULL_LIQUID-relatif, **maliyet-ONCESI** | +%0.77 / NW t=1.70 | +%0.77 / NW t=1.70 (BIREBIR) |
| EW_FULL_LIQUID-relatif, **maliyet-SONRASI** (ASIL) | **-%0.89 / t=-1.78** | **+%0.54 / t=+1.17** |
| gerceklesen gercekci maliyet (flat-bps-esdeger) | ~298 bps | **~41.8 bps** |
| secilen-isimler round-trip ortalama | ~307 bps | **~38 bps** |
| secilen-isimler roll-zero orani | %45.2 | **%3.7** |
| breakeven (model-bagimsiz; degismez) | ~138 bps | ~138 bps |
| 5-gate gecen | 1/5 (yalniz gate1) | **4/5 (gate1,3,4,5)** |
| **verdict** | YINE-TRADEABLE-DEGIL (maliyet-olduruyor) | **YINE-TRADEABLE-DEGIL (anlamlilik-olduruyor)** |

Maliyet-ONCESI seri **birebir ayni** (maliyet degisikligi cost-free bir seriyi oynatamaz) --
bu, "tek fark maliyet" displine edilmis kanit. Duzeltilmis maliyet, gerceklesen ~maliyeti
**298 -> 41.8bp** dusurdu (kote-birincil; roll-zero %45 -> %4). Maliyet-sonrasi seri NEGATIF'ten
(-%0.89) **POZITIF'e** (+%0.54) dondu -> **sisik maliyet gercekten bir edge'i maskeliyormus.**

### 3.2 Maliyet -- duzeltilmis kote-birincil model breakeven'in COK altinda

Gerceklesen ~**41.8 bps** << breakeven ~**138 bps** (2x-guvenlik rahatca saglandi: 138 >= 2x41.8).
D-205'teki tablo tersine donmus: orada gerceklesen (298) >> breakeven (138) idi -> gate5 FAIL;
burada gerceklesen (41.8) << breakeven (138) -> **gate5 PASS.** Maliyet-kapisi adil-zeminde gecti.

### 3.3 Edge -- maliyet-sonrasi pozitif-ama-ZAYIF (anlamlilik yetersiz)

| seri | ortalama/ay | NW t | CI sifiri-disliyor mu |
|---|---|---|---|
| EW_FULL_LIQUID-relatif, maliyet-oncesi | +%0.77 | 1.70 | hayir |
| EW_FULL_LIQUID-relatif, **Roll-maliyet-sonrasi** (ASIL) | **+%0.54** | **1.17** | **hayir** |
| EW_FULL_LIQUID-relatif, tier-maliyet-sonrasi (capraz) | +%0.61 | 1.33 | hayir |
| EW_FULL-relatif, Roll-maliyet-sonrasi (baglam) | +%0.06 | 0.09 | hayir |
| long-short, maliyet-oncesi | +%2.26 | 2.96 | evet (pozitif) |

Ham hi52-sinyali GERCEK (long-short cost-free +%2.26/ay, t=2.96; gate1 PASS) -- NRR-005 ile
tutarli. Maliyet-sonrasi relatif edge artik **pozitif** (+%0.54) ama **t=1.17 << 2**: CI sifiri
iceriyor. Onemli: maliyet-ONCESI bile t yalniz 1.70 idi -- yani **anlamlilik hicbir zaman yoktu**;
duzeltilmis maliyet onu 1.70 -> 1.17'ye biraz indirdi, fakat duvar maliyet DEGIL, sinyal-inceligi.

### 3.4 5-gate -- 4/5 PASS (yalniz gate2 anlamlilik FAIL)

| gate | sonuc | not |
|---|---|---|
| gate1 secim-null (cost-free, ayni likit-havuzdan random-15) | **PASS** | strateji 0.02267 > null-p95 0.02166 (D-205 ile birebir) |
| gate2 NW\|t\| >= 2 (maliyet-sonrasi) | **FAIL** | **t = 1.17** -- ASIL duvar |
| gate3 capraz-rejim (2022-01, maliyet-sonrasi) | **PASS** | pre +%0.09 / post +%0.80, ikisi-de pozitif |
| gate4 likit-ici alt-tutarlilik (ust/alt-yari ADV) | **PASS** | ust +%0.74 / alt +%0.44, ikisi-de pozitif |
| gate5 maliyet-sonrasi relatif > 0 | **PASS** | +%0.54 |

**gate3/gate4/gate5** D-205'te (sisik-maliyetle) FAIL idi; duzeltilmis-maliyetle **PASS** --
cunku maliyet-sonrasi seri pozitife dondu. **gate4 — orneklem-boyutu notu:** her iki
ADV-yarisi da **tam basket-boyutu 15** (basket_size_min=15, medyan=15) ile calisti -- gate4-PASS
**kucuk-orneklem artefakti DEGIL.** Tek kalan FAIL **gate2: anlamlilik** (t=1.17).

### 3.5 Yardimci olcumler

- **Tutus / turnover:** ortalama tutus **1.75 ay**, turnover **%57.2** (D-205 ile ayni -- sinyal
  degismedi, yalniz maliyet).
- **Walk-forward (in-sample):** train +%0.38 / holdout +%0.71 / disinflasyon-2024-26 +%0.52 --
  uc pencere de **pozitif** (D-205'te uchu-de negatifti). Yine de hicbiri istatistiksel-anlamli degil.
- **Buffer VIEW (enter15/exit30):** turnover %37.5'e dustu, relatif +%0.37/ay (t=0.93) -- yine
  anlamli-alti. (Ikincil VIEW, secim DEGIL.)
- **Deploy-hurdle:** likit-long MUTLAK reel maliyet-sonrasi +%2.03/ay TLREF-mevduat-esigini
  (0.000222) gecti; hurdle-reuretim guard'i gecti (yeniden-hesap 0.000222, tol 5e-6). AMA bu
  MUTLAK; EW_FULL_LIQUID-RELATIF edge anlamli-degil oldugundan verdict bunu tek-basina yeterli
  saymaz.

## 4. Hukum: YINE-TRADEABLE-DEGIL (anlamlilik) -> hi52-likit adil-zeminde KESIN-KAPANIR

**Verdict: YINE-TRADEABLE-DEGIL.** 5-gate'ten 4'u (gate1,3,4,5) **PASS**, ama **gate2 (NW|t| >= 2)
FAIL** (t=1.17). Maliyet-sonrasi relatif edge artik **pozitif** (+%0.54/ay) ve maliyet breakeven'in
cok altinda (41.8 << 138bp) -- yani **sisik-maliyet bahanesi kaldirildi.** Geriye kalan tek duvar
**anlamlilik**: sinyal, likit-evrenin kendi-EW'sine gore istatistiksel-tradeable olacak kadar
guclu DEGIL (maliyet-oncesi bile t=1.70, CI sifiri iceriyor).

**Yorum (D-204/D-205 ile TUTARLI, onlari CURUTMEZ):** D-205, hi52-likit'i kismen sisik-maliyetle
kapatmisti; D-208 gosteriyor ki **maliyet duzeltilince edge pozitife doner ama anlamli-olmaz.**
Yani D-205'in BOTTOM-LINE'i (tradeable-DEGIL) korunur; degisen yalniz SEBEP: "maliyet-olduruyor"dan
"**anlamlilik-olduruyor**"a. Bu, hi52 icin **temiz-kapanis**tir -- artik adil-zeminde: ne sisik-
maliyet, ne dar-evren (havuz min 44), ne kucuk-orneklem (gate4 tam-boyut). Sinyal gercek
(long-short +%2.26, gate1 PASS) ama **retail-tradeable degil**: tek-yonlu-likit relatif-edge cok
ince. **hi52 KESIN-karar: temiz-arsiv** (D-204 + D-205 verdict'leri korunur).

**OOS-bosluk (her durumda ZORUNLU):** ornek (2019-2026) tek-uzun yuksek-enflasyon rejimi; gercek
enflasyon-normallesme OOS YOK; walk-forward in-sample; disinflasyon 2024-26 yalniz zayif-proxy.
Rejim-degisim dayanikligi KANITLANAMAZ. (Burada da gecerli: edge anlamli-alti oldugundan moot.)

**post-hoc gevsetme YOK:** hicbir esik/guvenlik-katsayisi/gate/sinyal/evren gevsetilmedi. D-205'e
gore TEK degisiklik sisik-maliyetin D-207-duzeltilmis-maliyetle degistirilmesidir.

## 5. Reuse / disiplin

- **Strangler:** D-205 motoru (`run_d205`) yalniz tek geriye-uyumlu parametre (`quoted_panel=None`,
  varsayilan = degismemis D-205 davranisi) ile genisletildi; gate-mantigi/sinyal/evren/benchmark
  AYNEN. D-207-duzeltilmis maliyet (`realistic_cost` + `per_stock_cost_panel` + `quoted_spread`)
  OLDUGU-GIBI reuse (DEGISTIRILMEDI). D-205 kayitlari (rapor/STAGE0/results) DOKUNULMADI.
- **Disiplin:** Stage-0 (`STAGE0_d208.json`) sonuclardan ONCE donduruldu; durust-beklenti
  (gate5-gecer/gate2-kalir) onceden-ilan-edildi ve OLCUMLE dogrulandi; kutlama YOK; N<=3
  REVISITED (4. tur DEGIL). Surucu yerel + arsiv-destekli (CI-guvenli; kote panel enjekte,
  arsiv CI'a girmez); edge-kor (maliyet yalniz kote/ADV'den, getiriden DEGIL).

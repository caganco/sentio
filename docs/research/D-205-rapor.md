# D-205 hi52 LIKIT-ONCE -- likit-evren-once hi52, gercekci maliyet altinda (SON hi52-olcumu, N<=3)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d205.json` (config_version d205-v1, sonuclardan
> ONCE donduruldu; likit-ADV-esigi 1e7 TL edge-GORMEDEN donduruldu). Ham sonuc:
> `docs/yol1/d205_results.json`. Motor: `src/screening/d205_hi52_liquid.py`. Maliyet
> mekanigi: `src/screening/realistic_cost.py` (ballast'tan PORT). Olcum geometrisi:
> `src/screening/d205_config.py`. Karar esikleri: `src/signals/thresholds.py` (D205_* blok).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N=1 aday (hi52 LIKIT-ONCE). Likit-ADV-esigi
> (1e7 TL) NRR-006 havuz-fizibilitesi + the maintainer-deploy gerekcesiyle, **edge-GORMEDEN** donduruldu
> (post-hoc esik-secimi YASAK). lambda_kyle DONMUS; buffer (enter15/exit30) raporlama VIEW'i,
> secim DEGIL. hi52 sinyali D-203 ile BIREBIR. D-203 donmus paneli aynen REUSE (ayni hash).
> **D-205 = hi52'nin 3. ve SON olcumu (N<=3: D-203 + D-204 + D-205). Dorduncu tur YOK.**

## 1. Soru

D-203'te **hi52 = GERCEK-EDGE** cikti (sistemin ilk asteriksiz edge'i; NW t=3.19, 5/5 gate).
D-204 stres-testi bu **prototipi** (252g + top15 + EW + aylik + filtre-yok) **tradeable-DEGIL**
buldu: gerceklesen gercekci round-trip ~340bp > breakeven ~302bp; kok-neden ~%88 turnover x
~%98 microcap (medyan-ADV 1.65M-TL). NRR-005 gozlemsel-teshis (a) kok-nedenin **maliyet-ORANI
(microcap)** oldugunu (turnover-seviyesi degil) ve (b) **hi52-sinyalinin likit-isimlerde de
var** oldugunu gosterdi (likit-havuz rank-IC 0.048 ~ tum-evren 0.047; likit-once top15 pre-cost
+%1.47).

**D-205 hipotezi:** hi52-SINYALINI degistirmeden EVRENI bastan likit-kisitla (trailing-63g-medyan
-ADV >= 1e7 TL) -> maliyet-orani duser + sinyal-orada -> gercekci-maliyet-SONRASI tradeable
OLABILIR. Bu D-204'u GEVSETMEZ; D-204-kok-nedenine (maliyet-orani) saldirir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren / faktor / pencere / istatistik / maliyet:** D-203/D-204'ten AYNEN reuse (ayni
  content-hash; motor yuklemede hash assert eder). hi52 tanimi D-203 ile birebir. Roll(1984)
  spread + Kyle(1985) impact + RR-015 tier capraz-kontrol; lambda_kyle DONMUS.
- **Likit-evren (D-205 cekirdek):** her ay trailing-63g-medyan-ADV >= **1e7 TL** olan isimler.
  Esik NRR-006 ADIM-1 havuz-olcumunde (edge-OLCULMEDEN) belirlenip ADIM-2'de donduruldu.
- **Benchmark:** ana = **EW_FULL_LIQUID** (likit-evrenin EW'i -- "hi52-top15, butun likit
  isimleri EW tutmaktan iyi mi?" -- durust secim-bari). Baglam = EW_FULL (tum evren).
- **Ana hukum = BREAKEVEN bps** (model-bagimsiz): edge'i sifirlayan flat round-trip maliyet.

## 3. Sonuclar (primer: common pencere, aylik kadans, EW_FULL_LIQUID-relatif)

### 3.1 Likit-evren saglikli -- dar-evren artefakti DEGIL

| olcum | deger |
|---|---|
| havuz boyutu (zaman-ici) | min **44** / medyan **78** / max **171** isim |
| top-15 fizibil | **%100** rebalanslarin |
| saglikli (>=30 isim) | **%100** rebalanslarin |

Esik bu sonucu **yapay-daraltmiyor**: top-15 her ay rahatca mumkun. Yani asagidaki FAIL'lar
**dar-evren artefakti DEGIL** -- gercek sinyal/maliyet okumasi.

### 3.2 Maliyet -- likit-once maliyet-oranini SADECE-ILIMLI dusurdu (yetersiz)

| olcum | D-205 likit-once | D-204 prototip (micro) |
|---|---|---|
| secilen-isimler ortalama round-trip (Roll-leg) | **~307 bps** (%3.07) | ~340 bps |
| secilen-isimler roll-zero orani | **%45.2** | %51.9 |
| gerceklesen gercekci maliyet (flat-bps-esdeger) | **~298 bps** | ~340 bps |
| **breakeven** (EW_FULL_LIQUID-relatif edge'i sifirlayan) | **~138 bps** | ~302 bps |

**Hukum:** likit-once maliyet-oranini **307 vs 340bp** (roll-zero %45 vs %52) -- yalniz
ILIMLI dusurdu, umulan ~4-6x ucuzlama DEGIL. Ustelik **EW_FULL_LIQUID daha-zor bir bar**:
likit-evrenin kendi-EW'sine gore hi52-top15'in fazlasi ince (breakeven ~138bp, D-204'un
~302bp'sinin cok altinda). Gerceklesen ~298bp >> breakeven ~138bp -> maliyet-sonrasi NEGATIF.

### 3.3 Edge -- maliyet-oncesi pozitif-ama-zayif, maliyet-sonrasi negatif

| seri | ortalama/ay | NW t | CI sifiri-disliyor mu |
|---|---|---|---|
| EW_FULL_LIQUID-relatif, **maliyet-oncesi** | +%0.77 | 1.70 | hayir |
| EW_FULL_LIQUID-relatif, **Roll-maliyet-sonrasi** (ASIL) | **-%0.89** | **-1.78** | hayir |
| EW_FULL_LIQUID-relatif, **tier-maliyet-sonrasi** (capraz) | +%0.24 | 0.51 | hayir |
| EW_FULL-relatif, Roll-maliyet-sonrasi (baglam) | -%1.35 | -2.02 | evet (negatif) |
| **long-short, maliyet-oncesi** | **+%2.26** | **2.96** | evet (pozitif) |

Ham hi52-sinyali GERCEK (long-short cost-free +%2.26/ay, NW t=2.96; gate1 cost-free secim-null'i
geciyor) -- NRR-005 ile tutarli. AMA likit-evrenin kendi-EW'sine RELATIF ust-fazla ince ve
gercekci-maliyet onu sifirin altina cekiyor.

### 3.4 5-gate -- 1/5 PASS

| gate | sonuc | not |
|---|---|---|
| gate1 secim-null (cost-free real, ayni likit-havuzdan random-15'e karsi) | **PASS** | strateji 0.0227 > null-p95 0.0217 |
| gate2 NW\|t\| >= 2 (maliyet-sonrasi) | **FAIL** | t = -1.78 |
| gate3 capraz-rejim (2022-01, maliyet-sonrasi) | **FAIL** | pre -%1.16 / post -%0.72 (ikisi-de negatif) |
| gate4 likit-ici alt-tutarlilik (ust/alt-yari ADV, maliyet-sonrasi) | **FAIL** | ust -%0.20 / alt -%0.72, ikisi-de negatif |
| gate5 maliyet-sonrasi relatif > 0 | **FAIL** | -%0.89 |

**gate4 / the maintainer-notu (orneklem-boyutu):** her iki yari da **tam basket-boyutu 15** ile calisti
(basket_size_min = 15, medyan = 15) -- yani gate4-FAIL **kucuk-orneklem gurultusu DEGIL**,
gercek sinyal-kaybi. Konservatif false-negatif riski (dar-alt-yari) burada GECERLI DEGIL;
likit-evren her iki yarida da yeterince genis. FAIL gercek.

### 3.5 Yardimci olcumler

- **Tutus / turnover:** ortalama tutus **1.75 ay**, turnover **%57** (prototip %88'den dusuk,
  cunku likit-evren daha-kararli) -- ama yine de yuksek.
- **Buffer VIEW (enter15/exit30):** turnover **%37.5**'e dustu, ama relatif yine **-%0.51**/ay
  (NW t=-1.20). Buffer kurtarmiyor -- NRR-005 ile tutarli: kok-neden turnover-seviyesi DEGIL,
  maliyet-orani x ince-relatif-edge. (Ikincil VIEW, secim DEGIL.)
- **Walk-forward (in-sample):** train -%0.94 / holdout -%0.82 / disinflasyon-2024-26 -%0.75 --
  her uc pencere de negatif.
- **Deploy-hurdle:** likit-long MUTLAK reel maliyet-sonrasi +%0.61/ay TLREF-mevduat-esigini
  (0.000222) gecdi -- AMA bu RELATIF degil mutlak; EW_FULL_LIQUID-relatif negatif oldugundan
  ve breakeven < maliyet oldugundan verdict bunu tek-basina yeterli SAYMAZ. Hurdle-reuretim
  guard'i gecti (yeniden-hesap 0.000222, tol 5e-6).

## 4. Hukum: YINE-TRADEABLE-DEGIL -> hi52 KESIN-KAPANIR (N<=3 SON)

**Verdict: YINE-TRADEABLE-DEGIL.** 5-gate'ten 4'u FAIL; EW_FULL_LIQUID-relatif maliyet-sonrasi
-%0.89/ay; breakeven ~138bp << gerceklesen ~298bp (2x-guvenlik-cok-uzak). Likit-evren saglikli
(dar-degil), gate4 tam-boyutla FAIL (gurultu-degil) -> sonuc **gercek**.

**Yorum (D-204 ile TUTARLI, onu CURUTMEZ):** likit-once hipotezi maliyet-oranini sadece-ilimli
dusurdu (307 vs 340bp) -- microcap-tuzagindan cikmak ucuzlugu ~4-6x getirmedi, cunku Roll-spread
likit-isimlerde de yuksek (roll-zero hala %45) VE asil-kisit relatif-edge'in inceligi: likit-
evrenin kendi-EW'sine gore hi52-ust-fazlasi (breakeven ~138bp) gercekci-maliyeti tasiyamiyor.
Ham sinyal gercek (long-short +%2.26, gate1 PASS) ama **retail-tradeable degil -- likit-once
bile.** hi52 icin KESIN-karar: **temiz-arsiv.** D-204-verdict (prototip tradeable-degil) korunur.

**OOS-bosluk (her durumda):** ornek (2019-2026) tek-uzun yuksek-enflasyon rejimi; gercek
enflasyon-normallesme OOS YOK; walk-forward in-sample; disinflasyon 2024-26 yalniz zayif-proxy;
pre-2019 acquisition reddedildi (corp-action-yok -> kirli, D-185-riski). Rejim-degisim
dayanikligi KANITLANAMAZ. (Burada moot: maliyet-sonrasi zaten negatif.)

## 5. Reuse / disiplin

- **Strangler:** D-203 motoru (panel/hi52/secim/null/rejim/NW/CI/reel) + D-204 maliyet-harness'i
  (per_stock_cost_panel / d204_basket_net_series / breakeven / holding-period / walk-forward /
  deploy-hurdle) READ-ONLY reuse; ikisi de DEGISTIRILMEDI. Yeni mantik yalniz: likit-evren,
  likit-EW-benchmark, gate4 likit-ici alt-tutarlilik (alt-yari orneklem-boyutu raporlu), 2-yollu
  verdict.
- **Disiplin:** Stage-0 sonuclardan ONCE donduruldu (motor yoksa RAISE); likit-ADV-esigi
  edge-gormeden donduruldu (post-hoc YASAK); N<=3 SON (dorduncu tur YOK).

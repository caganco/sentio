# NRR-008 value-REJIM-KOLU -- value'nun 3. ve SON turu (N<=3 kapanis): rejim-gating value'yu kurtariyor mu?

> Stage-0 on-kayit: `docs/yol1/STAGE0_nrr008.json` (config_version nrr008-v1, sonuclardan
> ONCE donduruldu; rejim-degiskeni edge-GORMEDEN secildi). Ham sonuc:
> `docs/yol1/nrr008_results.json`. Motor: `src/screening/nrr008_value_regime.py` (committed
> D-203 motoruna SIFIR-dokunus -- gate-1..4 `run_gates_on_score` replica'si, MATCH=True ile
> dogrulanir). Maliyet mekanigi: D-204 harness'i (`per_stock_cost_panel` /
> `d204_basket_net_series` / `breakeven_cost_bps`) REUSE. Olcum geometrisi:
> `src/screening/nrr008_config.py`. Karar esikleri: `src/signals/thresholds.py`
> (D203_*/D204_* blok -- yeni-threshold YOK).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N=1 aday (value-regime). value-tanimi
> D-203-BIREBIR (`eng.score_panel_for("value", ...)`, bm-primary, lag-safe; yeni-tanim YOK).
> Rejim-kurali DIRECTION-temelli (yon, seviye-DEGIL) -> yeni-decision-threshold YOK. D-203
> donmus paneli aynen REUSE (ayni hash fd207550). **value = D-203 + D-Y1 + NRR-008 = 3 olcum;
> NRR-008 value'nun 3. ve SON turu. Dorduncu-YOK.**

## 1. Soru

value-statik IKI kez olculdu, iki kez gecemedi: **D-203 = SERAP** (Gate-2 NW |t|=0.76,
illikit-yogun) ve **D-Y1-001 = KIRILGAN/REJIM-BAGIMLI** (P/B mekanik-PASS ama E/P celisiyor +
out-of-sample cokus + disinflasyonda prim-yok). RR-Y1 tezi: **BIST-value makro-rejim-suruculu**
(yayin-decay degil) -- Aras/Cam (2018) HML=-%1.09/ay NEGATIF; value pre_surge+yuksek-enflasyonda
var, disinflasyonda cokuyor. **Test-EDILMEMIS tek-kol:** "value-tilt yalniz uygun-makro-rejimde
aktif." NRR-008 sorusu: **disinflasyon-aylarinda value-tilt'i KAPATMAK, otherwise-fragile-value'yu
kurtarir mi?**

**Beklenti-kalibrasyonu (durust, ONCEDEN):** BELIRSIZ. Statik-value iki kez elendi/kirilgan-cikti
-> prior-zayif; AMA rejim-kollu-kol HIC-test-edilmedi -> gercekten-acik. Rejim-gating value'yu
kurtarabilir, YA-DA disinflasyon-kapatmak bile yetmeyebilir. Eleme-de-degerli (value-ipliginin
kesin-kapanisi). Kutlama-beklentisi YOK; sonuc-ne-olursa durust raporlanir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren / value-faktor / pencere / istatistik / maliyet:** D-203/D-204'ten AYNEN reuse (ayni
  content-hash fd207550; motor yuklemede hash assert eder). value-tanimi D-203-BIREBIR:
  `eng.score_panel_for("value", pdata, rebal, "bm")` -> `_xs_rank(value_factor_panel(...))`,
  book-to-market primary, ay-sonu fundamentaller 1-ay-lagli (look-ahead-safe). Roll(1984)
  spread + Kyle(1985) impact; lambda_kyle DONMUS.
- **Rejim-kurali (Aday-A, APPROVED Cagan+O 2026-06-03; DIRECTION-not-LEVEL):** rebal-ay M'de
  `infl_yoy = trailing-12ay-YoY-TUFE`. ON (value-tilt AKTIF = D-203 top-15) eger
  `infl_yoy(M-1) >= infl_yoy(M-7)` (sabit/yukselen VEYA tanimsiz-warmup); OFF (value-tilt KAPALI
  = EW_FULL-notr, relatif-fazla=0) eger `infl_yoy(M-1) < infl_yoy(M-7)` (disinflasyon). 6-ay-
  pencere + t-1-lag + 12-ay-YoY STRUKTUREL-sabit, Stage-0'da donmus (3/6/12-supurme = coklu-
  karsilastirma = YASAK). **Yon-degil-seviye -> yeni-decision-threshold YOK.**
- **Warmup (look-ahead-safe):** OFF yalniz YoY(M-1) ve YoY(M-7) IKISI-DE-tanimli VE recent<prior
  iken iddia edilir; tanimsiz-warmup (~2019-07..2020) ON kalir -- gelecek-bilgi-sizmasi-YOK,
  ekonomik-olarak yukselen pre_surge rejimi.
- **SIFIR-motor-dokunusu (Strangler):** gate-1..4 motorun `run_gates`'inin BIREBIR-kopyasi
  `run_gates_on_score` ile kosar; tek-fark skor-paneli disaridan enjekte + OFF-aylarinda
  EW_FULL-notr override. Bir test
  `run_gates_on_score(score_panel_for("value",...), regime_mask=None) == run_gates("value",...)`
  esitligini dogrular (MATCH=True) -> committed `score_panel_for`/`run_gates`/`D203_CANDIDATES`
  DEGISMEDI.
- **Benchmark:** ana = **EW_FULL** (D-203-standart durust-bar: "rejim-gated value-tilt, butun
  isimleri EW tutmaktan iyi mi?").
- **gate-5 GERCEKCI (direktif):** D-203 flat-gate'i yerine D-204 Roll+Kyle gercekci-maliyet;
  maliyet yalniz 15-isimlik tilt'in giris/cikis/dengeleme turnover'inde tahakkuk eder (OFF-aylar
  EW_FULL'u sifir-ek-turnover ile tutar). PASS = maliyet-sonrasi EW_FULL-relatif mean > 0.

## 3. Sonuclar (primer: common pencere 2019-07..2026-04, aylik kadans, EW_FULL-relatif)

### 3.0 Rejim-bolunmesi -- ON=50 / OFF=31 (on_frac %61.7)

82 rebal'in 81-getiri-periyodunda rejim ON=50, OFF=31. Ilk-OFF ayi **2020-08**. OFF-bloklar
disinflasyon-donemlerine denk geliyor (2020-ortasi, 2023-ortasi, ve 2024-26 normallesme-kuyrugu);
2019-21 yukselen pre_surge warmup ON. Yani rejim-kurali ekonomik-olarak beklendigi-gibi davraniyor.

### 3.1 Edge -- maliyet-oncesi pozitif-ama-ANLAMSIZ (D-203 statik t=0.76 ile NEREDEYSE BIREBIR)

| seri | ortalama/ay | NW t | CI sifiri-disliyor mu |
|---|---|---|---|
| EW_FULL-relatif, **maliyet-oncesi** (ASIL soru) | +%0.40 | **0.76** | hayir [-0.68%, +1.42%] |
| EW_FULL-relatif, **Roll-maliyet-sonrasi** | -%0.17 | -0.32 | hayir |
| EW_FULL-relatif, **tier-maliyet-sonrasi** (capraz) | +%0.20 | +0.38 | hayir |
| long-short, maliyet-oncesi | +%0.70 | -- | hayir [-0.84%, +2.12%] |

**Onemli okuma:** cost-free NW t = **0.758912** -- D-203-statik-value'nun **t=0.76'sini NEREDEYSE
BIREBIR uretiyor**. Yani **rejim-gating value'nun istatistiksel-anlamliligini neredeyse-hic
oynatmadi**: disinflasyon-aylarini kapatmak (OFF=31/81) cost-free-edge'i t=2-cizgisine yaklastirmadi.
Sinyal pozitif-egilimli (+%0.40/ay) ama EW_FULL-relatif ust-fazla istatistiksel-anlamsiz
(Gate-2 t>=2-esik-alti); long-short CI'si bile sifir-iceriyor.

### 3.2 5-gate -- gate-2 (ASIL gate) tek-tasiyici-FAIL; cost-free verdict SERAP

| gate | sonuc | not |
|---|---|---|
| gate1 secim-null (cost-free real, ayni havuzdan random-15) | **PASS** | strateji 0.02558 > null-p95 0.02465 (pctile **%96.2**) |
| gate2 NW\|t\| >= 2 (cost-free) -- ASIL gate | **FAIL** | t = **0.759** (D-203 statik 0.76 ile birebir) |
| gate3 capraz-rejim (2022-01, cost-free) | **PASS** | pre +%0.30 / post +%0.45 (her-iki-pozitif); 2022-07 sekonder de her-iki-pozitif |
| gate4 likidite-tercil (cost-free) | **PASS** | likit +%0.07 / illikit +%0.96 -> collapse-YOK ama edge hala illikite-egilimli |
| gate5 maliyet-sonrasi GERCEKCI (Roll+Kyle) | **FAIL** | -%0.17/ay |
| gate5 flat 20/100bp (yalniz BAGLAM) | (PASS) | +%0.38 / +%0.29 -- ama gercekci-gate ASIL |

**Tasiyici-FAIL = gate2 NW |t|=0.759.** lowvol63'un (NRR-007) aksine burada gate1/3/4 PASS
(secim-null'i geciyor, her-iki-rejimde pozitif, likidite-collapse-yok) -- AMA D-203-statik-value'nun
da geremedi-i ASIL gate (NW |t|>=2 anlamlilik) yine gecilemedi. **Kritik okuma: gate2-t rejim-
gating-ile 0.76'dan 0.759'a gitti -- yani disinflasyonu-kapatmak anlamliligi HIC-arttirmadi.** Bu,
cost-free verdict'i dogrudan **SERAP** yapar (gates_failed: gate2). Not: gate4'te edge hala
illikite-egilimli (illikit +%0.96 vs likit +%0.07) -- D-203'teki illikit-yogunluk problemi
rejim-gating-sonrasi da surur, sadece "collapse" esigini gecmeyecek kadar.

### 3.3 Maliyet -- turnover DUSUK (tilt-only), ama yine de breakeven < maliyet

| olcum | NRR-008 value-regime | D-204 hi52 prototip (referans) |
|---|---|---|
| tum-evren ortalama round-trip (Roll-leg) | **~372 bps** (%3.72) | ~340 bps |
| tum-evren roll-zero orani | **%51.9** | %51.9 |
| gerceklesen gercekci maliyet (flat-bps-esdeger) | **~346.6 bps** | ~340 bps |
| **breakeven** (EW_FULL-relatif edge'i sifirlayan) | **~230 bps** | ~302 bps |
| ortalama tutus / turnover | **4.54 ay / %13.3** | ~1 ay / %88 |

**Maliyet-notu (direktif):** value-tilt turnover'i (%13.3, tutus 4.54-ay) cok-DUSUK -- value
yavas-doner, beklendigi-gibi. AMA bu kurtarmiyor: gerceklesen ~346.6bp > breakeven ~230bp
(2x-guvenlik-cizgisi 460bp cok-uzak). Asil-kisit zaten maliyet degil: **cost-free sinyal zaten
anlamsiz** (gate-2 t=0.759). Maliyet-katmani sadece zaten-zayif-edge'i negatife ceviriyor
(maliyet-sonrasi -%0.17/ay). Turnover-dusuklugu ancak gercek-bir-cost-free-edge olsaydi onemli
olurdu; burada o yok.

### 3.4 Walk-forward (in-sample) -- holdout negatif

train (-> 2023-01) -%0.03 / holdout +sonrasi -%0.33 -- her-iki-pencere maliyet-sonrasi NEGATIF
(both_positive=false). disinflasyon-proxy penceresi (2024-01..2026-04) maliyet-sonrasi +%0.23
(zayif-pozitif, n=27). (Burada moot: cost-free zaten SERAP.)

## 4. Hukum: ELENDI -> value-ipligi KAPANIR (N<=3 final)

**Verdict: ELENDI** (cost-free verdict = **SERAP**, gates_failed: gate2). Rejim-gated value
sinyali **maliyet-oncesi-bile** ASIL-gate'i (NW |t|>=2) gecemedi: cost-free t=**0.759**, ki bu
**D-203-statik-value'nun t=0.76'siyla neredeyse-BIREBIR**. gate1/3/4 PASS olsa-da tasiyici-FAIL
gate2'dir; gercekci-maliyet-sonrasi -%0.17/ay (ek-onay, ama gerek-yok -- sinyal cost-free-bile
gercek-degil).

**Yorum -- ana-bulgu:** **Rejim-gating value'yu KURTARMADI.** Disinflasyon-aylarini kapatmak
(OFF=31/81, ekonomik-olarak-dogru-zamanlamali) value'nun istatistiksel-anlamliligini
neredeyse-hic-degistirmedi (0.76 -> 0.759). RR-Y1 "value-makro-rejim-suruculu" tezi: rejim-yonu
dogru-yakalansa-bile, ON-aylarindaki value-tilt'in kendisi EW_FULL-uzerinde anlamli-fazla
uretmiyor -- yani problem "yanlis-zamanlama" degil, **ON-rejiminde-bile edge'in zayif/illikit-
egilimli olmasi** (gate4: illikit +%0.96 vs likit +%0.07). value-statik iki kez (D-203 SERAP,
D-Y1 kirilgan) gecemedi; rejim-kollu-ucuncu-kol da gecemedi. **Temiz-arsiv; value-ipligi KAPANIR.**

**N<=3 kapanis:** value = D-203 + D-Y1-001 + NRR-008 = 3 olcum tamam. **Dorduncu-tur YOK.**

**OOS-bosluk:** verdict SERAP oldugu-icin OOS-bosluk-beyani MOOT (`oos_gap=null`; sinyal
cost-free-bile gercek-degil; rejim-dayanikligi sorusu hic dogmadi). Yine-de kayit: ornek
(2019-2026) tek-uzun yuksek-enflasyon rejimi; gercek enflasyon-normallesme OOS hala YOK.

## 5. Reuse / disiplin

- **Strangler:** D-203 motoru (panel/value_factor_panel/secim/null/rejim/NW/CI/reel) + D-204
  maliyet-harness'i (per_stock_cost_panel / d204_basket_net_series / breakeven / holding-period /
  walk-forward) READ-ONLY reuse; ikisi de DEGISTIRILMEDI. gate-1..4 motorun `run_gates`'inin
  BIREBIR-kopyasi `run_gates_on_score` ile kosar (tek-fark enjekte-skor + OFF-notr-override),
  **MATCH=True** (regime_mask=None) ile committed motoru birebir-yeniden-urettigi dogrulanir.
  Yeni mantik yalniz: look-ahead-safe rejim-etiketi (`regime_mask_for`), OFF-notr-override,
  tilt-only gercekci-gate5 (`gated_tilt_cost_series`), birlesik-verdict.
- **Disiplin:** Stage-0 sonuclardan ONCE donduruldu (motor yoksa RAISE); rejim-degiskeni
  edge-GORMEDEN secildi (Iki-asama: Cagan+O TEK-degiskeni+yonu 2026-06-03 onayladi); rejim-
  pencere/lag/YoY-span edge-gormeden donmus (3/6/12-supurme YASAK; post-hoc-gevsetme YOK);
  value-tanimi D-203-BIREBIR; yeni-decision-threshold YOK (yon-degil-seviye); look-ahead-safe
  ZORUNLU; N<=3 (value 3. ve SON-tur). Eleme-de-degerli: kesin-kapatma, temiz-arsiv.

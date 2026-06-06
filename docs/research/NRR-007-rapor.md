# NRR-007 lowvol63-IZOLE -- EDGE-2-icindeki gizli bilesenin ilk-izole-testi (5-gate, gate-5 gercekci)

> Stage-0 on-kayit: `docs/yol1/STAGE0_nrr007.json` (config_version nrr007-v1, sonuclardan
> ONCE donduruldu). Ham sonuc: `docs/yol1/nrr007_results.json`. Motor:
> `src/screening/nrr007_lowvol63.py` (committed D-203 motoruna SIFIR-dokunus -- gate-1..4
> `run_gates_on_score` replica'si, MATCH=True ile dogrulanir). Maliyet mekanigi:
> `src/screening/realistic_cost.py` (ballast'tan PORT), `d204_hi52_stress.py` uzerinden.
> Olcum geometrisi: `src/screening/nrr007_config.py`. Karar esikleri:
> `src/signals/thresholds.py` (D203_*/D204_* blok -- yeni-threshold YOK).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** N=1 aday (lowvol63 IZOLE). lowvol-penceresi
> (63) D-203/EDGE-2 ile BIREBIR donmus; lambda_kyle DONMUS; yeni-tanim YOK. lowvol63-sinyali
> motorda zaten var (`eng.lowvol_panel` CAGRILIR, motor degistirilmez). D-203 donmus paneli
> aynen REUSE (ayni hash fd207550). **NRR-007 = lowvol63'un ilk-izole olcumu (N<=3).**

## 1. Soru

D-203'te EDGE-2-kompozit (mom120 + hi52 + lowvol63, esit-agirlik rank-avg) test edildi, ama
motor-dispatch yalniz value/edge2/hi52 idi -- **lowvol63 HIC-izole gecmedi**. hi52-dersi: bir
bundle distinct bir faktoru gizleyebilir (hi52 EDGE-2'de gizliyken izole-olcumde GERCEK-EDGE
cikmisti). **lowvol63 da izole-test hak-ediyor.**

**Beklenti-kalibrasyonu (durust, ONCEDEN):** edge-arastirma S1/H4 lowvol63-izole zaten on-olctu:
+%0.56/ay, t=0.94 (Gate-2 t>=2-esik-ALTI, ANLAMSIZ) -> **MUHTEMELEN-ELENIR**. Bu test
KESIN-KAPATMA icin; ucuz oldugu-icin-deger (motor-hazir, tek-kosu). Ama on-gosterge maliyet-
ONCESI + tum-evren idi; izole-tam-test (5-gate + gercekci-maliyet) farkli-cikabilir -> yine-de
hak-etti. Kutlama-beklentisi YOK; sonuc-ne-olursa durust raporlanir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Evren / faktor / pencere / istatistik / maliyet:** D-203/D-204'ten AYNEN reuse (ayni
  content-hash fd207550; motor yuklemede hash assert eder). lowvol63 tanimi D-203/EDGE-2 ile
  birebir (`-std` of trailing-63g klipli gunluk-getiri; dusuk-vol = yuksek-skor). Roll(1984)
  spread + Kyle(1985) impact + RR-015 tier capraz-kontrol; lambda_kyle DONMUS.
- **SIFIR-motor-dokunusu (Strangler):** gate-1..4 motorun `run_gates`'inin BIREBIR-kopyasi
  `run_gates_on_score` ile kosar; tek-fark skor-paneli disaridan enjekte edilir
  (`comp = eng._xs_rank(eng.lowvol_panel(daily, rebal))`). Bir test
  `run_gates_on_score(score_panel_for("hi52",...)) == run_gates("hi52",...)` esitligini
  dogrular (MATCH=True) -> committed `score_panel_for`/`run_gates`/`D203_CANDIDATES` DEGISMEDI.
- **Benchmark:** ana = **EW_FULL** (tum uygun-evrenin EW'i -- D-203-standart durust-bar:
  "lowvol63-top15, butun isimleri EW tutmaktan iyi mi?").
- **gate-5 GERCEKCI (spec):** D-203'un flat 20/100bp gate-5'i yerine D-204 Roll+Kyle
  gercekci-maliyet (flat-legler yalniz BAGLAM-olarak raporlu). PASS = maliyet-sonrasi
  EW_FULL-relatif mean > 0.

## 3. Sonuclar (primer: common pencere 2019-07..2026-04, aylik kadans, EW_FULL-relatif)

### 3.1 Edge -- maliyet-oncesi pozitif-ama-ANLAMSIZ (edge-arastirma t=0.94 ile TUTARLI)

| seri | ortalama/ay | NW t | CI sifiri-disliyor mu |
|---|---|---|---|
| EW_FULL-relatif, **maliyet-oncesi** (ASIL soru) | +%0.56 | **0.94** | hayir |
| EW_FULL-relatif, **Roll-maliyet-sonrasi** | -%0.82 | -1.53 | hayir |
| EW_FULL-relatif, **tier-maliyet-sonrasi** (capraz) | -%0.21 | -0.37 | hayir |
| long-short, maliyet-oncesi | +%3.59 | -- | evet (pozitif) |

**Onemli okuma:** cost-free NW t = **0.937** -- edge-arastirma on-gostergesinin **t=0.94'unu BIREBIR
dogruluyor**. on-gosterge != tam-test endisesi burada gerceklesmedi; izole-tam-test de ayni
sonucu verdi. lowvol63 cross-section'da pozitif egilim gosteriyor (long-short +%3.59 CI>0) ama
EW_FULL-relatif ust-fazla **istatistiksel-anlamsiz** (Gate-2 t>=2-esik-alti).

### 3.2 5-gate -- 0/5 cost-free PASS (gate-5 flat-CONTEXT haric)

| gate | sonuc | not |
|---|---|---|
| gate1 secim-null (cost-free real, ayni havuzdan random-15) | **FAIL** | strateji 0.0234 < null-p95 0.0253 (pctile %89.8 < %95) |
| gate2 NW\|t\| >= 2 (cost-free) -- ASIL gate | **FAIL** | t = **0.94** (edge-arastirma ile birebir) |
| gate3 capraz-rejim (2022-01, cost-free) | **FAIL** | pre -%0.96 / post +%1.45 (yalniz-post-pozitif) |
| gate4 likidite-tercil (cost-free) | **FAIL** | likit -%0.31 / illikit +%1.20 -> **liquidity_collapse** |
| gate5 maliyet-sonrasi GERCEKCI (Roll+Kyle) | **FAIL** | -%0.82/ay |
| gate5 flat 20/100bp (yalniz BAGLAM) | (PASS) | +%0.46 / +%0.06 -- ama gercekci-gate ASIL |

**Tasiyici-FAIL = gate4 liquidity_collapse:** lowvol63-edge'i **yalniz illikit isimlerde**
var (illikit +%1.20 vs likit -%0.31). Yani gorulen cost-free pozitiflik likidite-primi/microcap
artefakti -- likit-tarafta sinyal NEGATIF. Bu, cost-free verdict'i dogrudan **SERAP** yapar.

### 3.3 Maliyet -- turnover ILIMLI, ama maliyet-orani edge'i tasiyamiyor

| olcum | NRR-007 lowvol63-izole | D-204 hi52 prototip (referans) |
|---|---|---|
| secilen-isimler ortalama round-trip (Roll-leg) | **~236 bps** (%2.36) | ~340 bps |
| secilen-isimler roll-zero orani | **%49.0** | %51.9 |
| gerceklesen gercekci maliyet (flat-bps-esdeger) | **~277 bps** | ~340 bps |
| **breakeven** (EW_FULL-relatif edge'i sifirlayan) | **~111 bps** | ~302 bps |
| ortalama tutus / turnover | **1.92 ay / %52** | ~1 ay / %88 |

**Maliyet-notu (spec):** lowvol turnover'i (%52) hi52'nin %88'inden DUSUK -- beklendigi gibi
daha-kararli. AMA bu kurtarmiyor: gerceklesen ~277bp >> breakeven ~111bp (2x-guvenlik cok-uzak).
Asil-kisit maliyet degil: **cost-free sinyal zaten anlamsiz + likit-tarafta yok** (gate-2/gate-4).
Turnover-dusuklugu ancak gercek-bir-cost-free-edge olsaydi onemli olurdu; burada o yok.

### 3.4 Walk-forward (in-sample) -- her pencere negatif

train (-> 2023-01) -%1.04 / holdout -%0.59 / disinflasyon-2024-26 -%0.59 .. -%1.41 -- her uc
pencere de maliyet-sonrasi NEGATIF. (Burada moot: cost-free zaten SERAP.)

## 4. Hukum: ELENDI -> lowvol63 izole-olcumde KAPANIR (N<=3)

**Verdict: ELENDI** (cost-free verdict = **SERAP**). lowvol63 sinyali **maliyet-oncesi-bile**
gate-gecmiyor: 0/5 cost-free gate PASS; tasiyici-neden gate4 **liquidity_collapse** (edge yalniz
illikit) + gate2 NW t=0.94 (anlamsiz). gercekci-maliyet-sonrasi -%0.82/ay (ek-onay, ama gerek-yok
-- sinyal cost-free-bile gercek-degil). **edge-arastirma on-gostergesi (t=0.94) BIREBIR dogrulandi** ->
on-gosterge != tam-test endisesi bu kez gerceklesmedi.

**Yorum:** EDGE-2-bundle'da lowvol63 gizliydi; izole-test, hi52'nin aksine, **distinct bir edge
ORTAYA-CIKARMADI** -- gorulen cross-section pozitifligi likidite-primi/illikit-artefakti.
Temiz-arsiv. (hi52 izole-edince GERCEK-EDGE cikmisti; lowvol63 cikmadi -- izole-testin neden
gerektiginin iki-yonlu kaniti.)

**OOS-bosluk:** verdict SERAP oldugu-icin OOS-bosluk-beyani MOOT (sinyal cost-free-bile gercek-
degil; rejim-dayanikligi sorusu hic dogmadi). Yine-de kayit: ornek (2019-2026) tek-uzun yuksek-
enflasyon rejimi; gercek enflasyon-normallesme OOS YOK.

## 5. Reuse / disiplin

- **Strangler:** D-203 motoru (panel/lowvol_panel/secim/null/rejim/NW/CI/reel) + D-204 maliyet-
  harness'i (per_stock_cost_panel / d204_basket_net_series / breakeven / holding-period /
  walk-forward) READ-ONLY reuse; ikisi de DEGISTIRILMEDI. gate-1..4 motorun `run_gates`'inin
  BIREBIR-kopyasi `run_gates_on_score` ile kosar (tek-fark enjekte-skor), **MATCH=True** ile
  committed motoru birebir-yeniden-urettigi dogrulanir. Yeni mantik yalniz: enjekte-skor yolu,
  gercekci-gate5, birlesik-verdict.
- **Disiplin:** Stage-0 sonuclardan ONCE donduruldu (motor yoksa RAISE); lowvol-penceresi (63) +
  gate-esikleri + lambda_kyle edge-gormeden donmus (post-hoc YASAK); yeni-tanim/yeni-threshold
  YOK; N<=3 (lowvol63 ilk-izole-olcum = 1). Eleme-de-degerli: kesin-kapatma, temiz-arsiv.

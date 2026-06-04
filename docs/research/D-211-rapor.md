# D-211 RR-Y1-002 STAGE-0: YABANCI-AKIM -> FORWARD TL-REEL ENDEKS GETIRISI -- ilk-resmi-olcum (N<=3: 1)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d211.json` (sonuclardan ONCE donduruldu + commit'lendi).
> Ham sonuc: `docs/yol1/d211_results.json`. Motor: `src/screening/d211_foreign_flow.py` (YENI) +
> `src/screening/d211_config.py` (geometri). Karar esikleri: `src/signals/thresholds.py` D211_* blok
> (ADDITIVE) + reuse D207_TIER_MEGA_HALF_SPREAD / D204_COMMISSION_PCT (READ-ONLY). Veri-dayanak:
> D-210 / `docs/yol1/RR-Y1-002-asama0-veri.md` (envanter). FF parser geometrisi
> `demo_smart_money/lab/ff_data.py`'den PORT (read-only). NW-mean-t demo-goal'den PORT.
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** Cerceve-B surekli zaman-serisi tahmin (tek-varlik
> timing; hisse-secimi DEGIL). Tum esik/tanim/keep-bar Stage-0'da donduruldu ve **sonuclardan ONCE
> commit'lendi**; hicbiri post-hoc gevsetilmedi (predictor-yeniden-tanimi YOK, pencere-genisletme
> YOK, lag-yeniden-secimi YOK, maliyet-yeniden-kalibrasyonu YOK, keep-bar-gevsetme YOK). N=1 aday
> (agrega yabanci-akim piyasa-timing'i), fiyat-ORTOGONAL eksen.
>
> **STRANGLER (sert-kisit):** committed motor (d203/d204/d205/d209 + realistic_cost + thresholds
> mevcut bloklar + ballast) SIFIR-dokunus -- D-211 yalniz YENI d211_* dosyalari + D211_* esik-blogu
> + registry + doc ekledi. foreign_flow arsivi CI'a GIRMEZ (sentetik unit-test); gercek olcum
> yerel ARTIFACT (`d211_results.json`). HTTP-free, offline. ASCII. Mutlak-yol commit'lenmez.

## 1. Soru

Bu-ayki agrega yabanci NET akim, **~6-hafta yayin-gecikmesiyle bilinebilir** formda (yani lag-2),
**gelecek-ayin BIST-endeks TL-REEL getirisini** tahmin ediyor mu? Tek-varlik zaman-serisi; hisse
secimi DEGIL. Fiyat-ortogonal bir eksen (akim, fiyatin kendisi degil).

**Onceden-ilan-edilmis durust beklenti (kutlama YOK):** prior DUSUK. RR-038 yabanci tekil-isim
tahmini zayifti; yabanci katilim cok-yillik dip; ~6hf gecikme handikap; timing bizi iki kez yendi
(DISC-2). Olasi hukum TRADEABLE-DEGIL -- ama bu kez fiyat-ORTOGONAL eksende, OLCUMLE. Surpriz
ihtimali: tekil-isim testlerinin kacirdigi agrega-timing icerigi; cikarsa duz raporlanir.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Predictor (LOCK):** `NF_pct(m) = SUM(buy_usd - sell_usd) / SUM(buy_usd + sell_usd)`, dogal
  [-1,1], olcek-bagimsiz "yabanci aktivitenin net egilimi". USD sutunlar TL-enflasyon olcek-
  bozulmasini azaltmak icin (LOCKED, mining DEGIL). Return-ay t'yi tahmin icin predictor = NF_pct(t-2):
  (t-2)-ay akimi ~(t-1)-ortasi yayinlanir (~6hf), yani (t-1)-sonu karar-aninda bilgi-kumesinde ->
  look-ahead-safe. Ticker filtresi `^[A-Z0-9]{2,6}\.E$` (segment alt-basliklari haric).
- **Dependent (LOCK):** XU100.IS fiyat-only (temettu YOK; snapshot-meta: hisse ~%2-4/yil dezavantajli;
  XU100-total-return yerel YOK -> fiyat-getiri spec-izinli fallback). Aylik nominal
  `r_nom(t) = idx(t-sonu)/idx(t-1-sonu) - 1`; TL-reel = `r_nom(t) - infl(t)` (TUFE MoM cikarmasi,
  spec-literal; deflasyon ZORUNLU).
- **Pencere (LOCK, Orchestrator-onayli Option-1, 2026-06-04):** PRIMARY 2019-01..2026-04 (87 forward-ay).
  Spec 2010-01..2026-04 PRIMARY demisti; DATA-FACT (D-210): tek temiz LOKAL XU100 (exposure_d187_xu100)
  yalniz 2019+ kapsiyor (prices_official BIST100-index sutunu tumden NULL; clean_universe adj-fiyat
  da 2019-baslar) -> kurumsal-aksiyon-temiz pre-2019 endeks yerel kurulabilir DEGIL. 2017-04 FF-bosluk
  pencere-disinda; interpolasyon YOK (eksik ay DROP).
- **Rejim (LOCK):** split 2022-01-01; A=2019-02..2021-12 (35 ay), B=2022-01..2026-04 (52 ay).
  Kararlilik: slope-isareti A ve B'de AYNI olmali. Konsantrasyon (leave-one-regime-out): herhangi
  bir alt-donemi cikarmak tam-orneklem isaretini CEVIRMEMELI (deger-faktoru dersi).
- **Istatistik (LOCK):** OLS slope + Newey-West HAC t, lag=6 (spec lag>=6). Seri lag-2 predictor
  + 1-ay forward ile insaen NON-overlapping. Stambaugh-farkindaligi: NF_pct AR(1) + non-overlap
  raporlanir.
- **Deploy-edilebilir bacak (LOCK):** (t-1)-sonu, NF_pct(t-2)>0 -> XU100 long (t-ayi reel getiri);
  <=0 -> TLREF nakit (reel TLREF carry). Aylik kadans. Maliyet: endeks-switch one-way =
  D207_TIER_MEGA_HALF_SPREAD (5.28bp); Kyle=0 (endeks mega-likit, en-derin defter); komisyon=0;
  her endeks GIRIS + her endeks CIKIS one-way; buy-and-hold tek giris one-way oder. NET kumulatif
  TL-reel vs buy-and-hold XU100 NET kumulatif TL-reel.
- **keep-bar (LOCK, 4'u-de zorunlu):** [1] primary NW|t|(lag=6)>=2.0; [2] slope-isareti rejim-stabil
  (A AND B ayni) AND konsantre-degil; [3] deploy-bacak NET-kumulatif buy-hold'u GECER (post-cost,
  lag-2); [4] look-ahead-safe (lag-2; lag-0 leg NON-DEPLOYABLE, sayilmaz). 4'u-de PASS -> TRADEABLE
  (aday-only); herhangi-biri fail -> TRADEABLE-DEGIL.

## 3. Sonuclar (frozen snapshot hash-asserted; 87 forward-ay, NF_pct mean=-0.0037 std=0.0163 AR1=0.24)

### 3.1 Primary regresyon (lag-2) -- anlamlilik-alti, slope NEGATIF

| olcum | deger |
|---|---|
| slope b (NF_pct(t-2) -> forward TL-reel) | **-0.252** |
| NW HAC t (lag=6) | **-0.725** |
| n (forward-ay) | 87 |
| R^2 | 0.0023 |
| NF_pct AR(1) | 0.244 (dusuk persistans -> Stambaugh-yanlilik kucuk) |

Slope NEGATIF ve istatistiksel-sifir (NW|t|=0.73 << 2.0; R^2 binde-2). Yani "yuksek yabanci net-alim
-> yuksek forward reel getiri" yonunde **anlamli icerik YOK**; isaret zayifca tersine (negatif).

### 3.2 Rejim kararliligi -- isaret stabil (her iki donemde negatif), AMA edge yok

| | slope | NW t | n |
|---|---|---|---|
| A 2019-2021 | -0.397 | -0.99 | 35 |
| B 2022-2026 | -0.087 | -0.10 | 52 |

Iki donemde de slope NEGATIF (full_sign=-1, same_sign_AB=true); leave-one-regime-out tam-orneklem
isaretini cevirmiyor (konsantre-DEGIL) -> keep-bar[2] teknik-olarak PASS. AMA bu "stabil bir EDGE"
degil; **stabil bir SIFIR/zayif-negatif**: her iki donemde de anlamlilik-alti. Kararlilik testi
gecmesi hukmu degistirmez (tek basina yeterli leg degil).

### 3.3 Deploy-edilebilir bacak -- buy-hold'u AGIR kaybediyor

| olcum | deger |
|---|---|
| n_ay (nakit-bacak veri kisiti, asagi-bkz) | **45** (2022-08..2026-04) |
| endeks-long pay | %53.3 |
| switch sayisi | 19 |
| one-way maliyet | 5.28 bp |
| strat NET kumulatif TL-reel | **-%7.6** |
| buy-hold XU100 NET kumulatif TL-reel | **+%51.2** |
| strat buy-hold'u gecer mi | **HAYIR** |
| aylik relatif ortalama (strat-bh) | -%1.34 |
| aylik relatif NW-t | -0.88 |

Sinyal-kosullu timing, buy-and-hold'u ~59 puan reel GERIDE birakti (-%7.6 vs +%51.2). Maliyet burada
DUVAR DEGIL (endeks mega-likit, switch one-way yalniz 5.28bp, toplam 19 switch); kayip sinyal-iceriginin
yoklugundan: NF_pct>0 kapisi long/cash kararini iyilestirmedi, tersine kotulestirdi (aylik relatif
-%1.34, NW-t=-0.88). **keep-bar[3] FAIL.**

**Nakit-bacak honesty-caveat:** yerel TLREF snapshot'inda reel-veri yalniz 2022-07'den baslar;
oncesi bu snapshot'ta NaN (Stage-0 "proxy-extended -> flagged" demisti, ama snapshot fiilen bos).
Dolayisiyla deploy-bacak fiilen yalniz **rejim-B (2022-08..2026-04, 45 ay)** uzerinde calisti --
yuksek-enflasyon tek-rejimi. Bu, sonucu zayif-flatter degil zayif-tutar: o pencerede bile timing
buy-hold'u agir kaybetti.

### 3.4 Look-ahead + contemporaneous teshis (NON-DEPLOYABLE) -- akim fiyatla ES-ZAMANLI hareket eder, ONCE DEGIL

| | slope | NW t | n | R^2 | durum |
|---|---|---|---|---|---|
| lag-2 (primary) | -0.252 | -0.73 | 87 | 0.002 | DEPLOYABLE |
| lag-0 (es-zamanli) | **+2.342** | **+3.68** | 87 | **0.184** | **NON-DEPLOYABLE** |

**En ogretici bulgu:** es-zamanli (ayni-ay) yabanci net-akim ile TL-reel getiri arasinda GUCLU,
POZITIF, anlamli iliski var (NW-t=3.68, R^2=0.18). AMA bu lag-0'dir -- karar-aninda bilinmez (akim
~6hf sonra yayinlanir). Knowable lag-2 forma gecince hem buyukluk hem anlamlilik kayboluyor (hatta
isaret cevriliyor). Yorum: yabanci-akim fiyatin **YANSIMASIDIR/es-hareketidir, ONCULU DEGIL** --
agrega-timing icin oncu-bilgi tasimiyor. keep-bar[4] (look-ahead-safe): lag-2 uygulandi; lag-0 leg
sadece teshis, hukma SAYILMAZ -> PASS (disiplin).

### 3.5 Ikincil (report-only, hukmu kurtaramaz)

- **z-score(NET_usd) lag-2:** slope-isaret NEGATIF, NW-t=-0.38, n=87 -> primary ile ayni yon, anlamlilik-alti.
- **NET_usd / mcap:** CALISTIRILMADI (opsiyonel; agrega-mcap join gerektirir; hukum-immutable).

Ikincil tanimlar primary'yi kurtarmaz (cherry-pick YASAK); ikisi de ayni hukme isaret eder.

### 3.6 keep-bar -- [1] ve [3] FAIL -> verdict TRADEABLE-DEGIL

| keep-bar leg | sonuc |
|---|---|
| [1] primary NW\|t\|(lag=6) >= 2.0 | **FAIL** (0.73) |
| [2] rejim-stabil AND konsantre-degil | PASS (ama stabil-SIFIR) |
| [3] deploy-bacak buy-hold'u gecer | **FAIL** (-%7.6 vs +%51.2) |
| [4] look-ahead-safe (lag-2; lag-0 NON-DEPLOYABLE) | PASS |
| **verdict** | **TRADEABLE-DEGIL** |

## 4. Hukum: TRADEABLE-DEGIL (temiz-kayit) -- fiyat-ortogonal eksende de timing-edge YOK

**Verdict: TRADEABLE-DEGIL.** keep-bar[1] (anlamlilik) ve [3] (deploy-bacak) FAIL; [2]/[4] teknik-PASS
ama tek-baslarina yeterli degil. Onceden-ilan-edilen durust beklenti (prior-dusuk, TRADEABLE-DEGIL)
**OLCUMLE dogrulandi** -- ama bu kez fiyat-ORTOGONAL bir eksende (akim, fiyat-momentumu degil).

**Duvar tipi -- ANLAMLILIK (icerik-yoklugu), maliyet DEGIL:** endeks mega-likit; switch one-way
yalniz 5.28bp; maliyet bahanesi yok. lag-2 knowable formda primary NW|t|=0.73 ve deploy-bacak
buy-hold'u 59-puan reel geride. Es-zamanli lag-0'da guclu pozitif iliski (t=3.68) VAR ama
NON-DEPLOYABLE: akim fiyatin es-hareketidir, ~6hf-knowable formda **oncu-icerik tasimiyor**. ->
DISC-2 (timing bizi yendi) ucuncu kez, bu kez fiyat-ortogonal akim-ekseninde, OLCUMLE teyit.

**Yorum:** RR-038 yabanci tekil-isim tahmininin zayifligi, agrega-timing'de de tekrarlaniyor;
tekil-isim testlerinin kacirdigi bir agrega-timing surprizini ARADIK, BULAMADIK. lag-0 es-hareket
gercek ama islenebilir-degil (gecikme handikabi). Yabanci-katilimin cok-yilli dipte olmasi da
sinyal-gucunu zayiflatan zemin.

**OOS-bosluk (her durumda ZORUNLU, ACIK):** 2019-2026 tek-uzun yuksek-enflasyon rejimidir; gercek
enflasyon-normallesme OOS YOK -> rejim-degisim dayanikligi KANITLANAMAZ. Deploy-bacak fiilen yalniz
rejim-B (2022-08+) uzerinde (yerel TLREF reel-veri 2022-07-baslar); pre-2022 nakit-bacak yerel
snapshot'ta yok. Burada moot: lag-2 primary tum-orneklemde zaten anlamli-alti.

**post-hoc gevsetme YOK:** hicbir esik/tanim/pencere/lag/maliyet/keep-bar gevsetilmedi. Stage-0
sonuclardan ONCE commit'lendi (anti-post-hoc guard). Deployment ayri bir the project kararidir; bu
harness OLCER + ONERIR, asla otomatik-deploy ETMEZ -- ve burada onerilecek bir aday yok.

**KARAR: agrega yabanci-akim -> forward TL-reel endeks timing'i temiz-arsiv (N<=3, count=1).**
Kutlama YOK -- beklenen sonuc, fiyat-ortogonal eksende OLCULDU ve duz kaydedildi.

## 5. Reuse / disiplin

- **Strangler:** committed d203/d204/d205/d209 + realistic_cost + thresholds mevcut bloklar
  SIFIR-dokunus; yalniz YENI `d211_foreign_flow.py` + `d211_config.py` + D211_* esik-blogu (ADDITIVE)
  eklendi. Maliyet legi D207_TIER_MEGA_HALF_SPREAD + D204_COMMISSION_PCT'yi READ-ONLY reuse eder.
  FF parser geometrisi demo_smart_money/lab/ff_data.py'den PORT (kopya-okuma, mutlak-yol commit'lenmez);
  NW-mean-t demo-goal'den PORT. Snapshot icerik-hash'leri yukleme-aninda assert edilir (drift -> RAISE).
- **Disiplin:** Stage-0 (`STAGE0_d211.json`) sonuclardan ONCE donduruldu + COMMIT'lendi (motor,
  dosya yoksa calismayi REDDEDER); durust-beklenti (prior-dusuk, TRADEABLE-DEGIL) onceden-ilan-edildi
  ve OLCUMLE dogrulandi; kutlama YOK; N<=3 ilk-resmi-olcum (count=1). Olcum yerel + arsiv-destekli;
  foreign_flow arsivi CI'a GIRMEZ -> committed test SENTETIK (`tests/test_d211_foreign_flow.py`),
  gercek sonuc ARTIFACT (`d211_results.json`). Edge-kor; look-ahead-safe (lag-2 boyunca; lag-0 leg
  NON-DEPLOYABLE damgali, hukma sayilmaz). ASCII.

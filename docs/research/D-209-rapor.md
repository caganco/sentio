# D-209 H2b TEMETTU-RUNUP RE-TEST -- duzeltilmis-maliyetle ilk-resmi-olcum (N<=3: 1)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d209.json` (sonuclardan ONCE donduruldu). Ham sonuc:
> `docs/yol1/d209_results.json`. Motor: `src/screening/d209_h2b_runup.py` (YENI; donmus demo-goal
> H2 detection + V1/V2 defteri BIREBIR PORT -- yeni-tanim YOK). Maliyet: `src/screening/realistic_cost.py`
> + `d204_hi52_stress.per_stock_cost_panel` + `quoted_spread.py` (D-207'den OLDUGU-GIBI reuse, kote
> panel ENJEKTE). Frozen panel: D-203 `adjusted_prices_2019_2026.parquet` (tr_index_gross +
> adjusted_close tasiyor -> ex-tarih detection LOKAL reproduke). Karar esikleri:
> `src/signals/thresholds.py` (D209_* blok + reuse D205_*/D204_*/D203_*).
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** D-209, donmus demo-goal H2/H2b sinyalini AYNEN
> tekrarlar (detection + defter BIREBIR PORT, yeni-esik-secimi YOK) ve **YALNIZ maliyet girdisini**
> degistirir: demo-goal'in FLAT 20/100bp/side maliyeti (H2b'yi eleyen) yerine D-207-duzeltilmis
> per-isim realistic_cost (Roll+Kyle, kote-birincil). Sinyal/pencere/benchmark/keep-bar/verdict-kurali
> degismedi. Hicbir esik, sinyal, pencere ya da evren gevsetilmedi.
>
> **STRANGLER (sert-kisit):** committed motor (d203/d204/d205 + realistic_cost + thresholds mevcut
> bloklar) SIFIR-dokunus -- D-209 yalniz YENI d209_* dosyalari + D209_* esik-blogu + registry + doc
> ekledi. Demo-goal H2 lab kayitlari OKUNDU, kopyalanmadi (mutlak-yol commit'lenmez).
>
> **N<=3 notu:** demo-goal FLAT-maliyetli eleme bir LAB sonucuydu, resmi Yol-1 turu DEGIL. D-209,
> H2b'nin committed-motorda **ilk RESMI olcumudur** (count=1/N<=3). YINE-TRADEABLE-DEGIL cikarsa
> H2b temiz-arsivlenir; 4. tur YOK.

## 1. Soru

H2b = temettu ex-tarihi ONCESI [-5,-1] run-up'i yakalayan, gunluk-rebalance, long-only EW sepet
(ex-ONCESI cikis -> temettu/stopaj YOK). Demo-goal mezarliginda **tek t>=2-olan aday** idi
(maliyet-ONCESI gunluk NW-t=2.57) ama orada **FLAT 20/100bp/side** maliyetle ELENDI ve **D-207
duzeltilmis per-isim maliyetle HIC olculmedi.** NRR-010/D-207 ortak maliyet modelini likit
isimlerde ~12-25x sisik teshis edip duzeltti -> H2b, hi52'nin D-208'de aldigi adil-zemin
re-testini hak ediyor.

**D-209 sorusu:** duzeltilmis (gercekci) maliyetle H2b hala tradeable mi, yoksa hi52-gibi
**anlamlilik-duvarina** mi carpiyor? Bu, demo-goal FLAT-elemesini gevsetmez; tek-degisken
(maliyet) duzeltilince sonucun ne oldugunu OLCER.

**Onceden-ilan-edilmis durust beklenti (kutlama YOK):** demo-goal `h2b_runup_basket.json` 20bp/side
sutununda ZATEN gunluk-relatif NW-t = 0.86 (ALL) / 1.16 (likit-tercile). 20bp/side ~= 40bp
round-trip ~= D-207-duzeltilmis (~42bp, D-208). -> H2b'nin ZATEN insignifikan oldugu sutunun
komsulugu. **Olasi hukum: YINE-TRADEABLE-DEGIL, ANLAMLILIK-duvari (hi52-ikizi), maliyet-duvari
DEGIL.** Bir varyant beklenmedik sekilde NW|t|>=2'yi gecerse, bu gercek bir surpriz olarak acikca
raporlanir. Hangi sonuc cikarsa kaydedilir.

## 2. Olcum cercevesi (Stage-0'da donmus -- demo-goal H2 ile birebir)

- **Detection (PORT, donmus):** ex-tarih nerede `tr_index_gross.pct - adjusted_close.pct > 0.005`,
  sembol-basi. est_div_yield = bu gap. Demo-goal H2 lab figuru: **~1108 olay / 265 sembol** --
  motor bandin (900-1300 olay / 220-300 sembol) disina cikarsa RAISE eder (drift-guard).
- **V1 daily-churn [-5,-1]** (demo-goal `h2b_runup_basket.py` BIREBIR): gunluk-rebalance EW;
  isim gun-t'de TUTULUR <=> ex-tarihi [t+1, t+5] icinde; ex-ONCESI cikis. PRIMARY = yatirimli-gun
  (strat_net - EW_FULL) aritmetik relatif seri (carry-immune). NW HAC t, lag=5.
- **V2 discrete-capture [-10,-1]** (demo-goal H2 lab `RUNUP_capture` legi BIREBIR): her (sembol,ex)
  olayi = TEK round-trip, [-10,-1] (10 islem-gunu = "hold-10g") bilesik getiri, ex-ay-basi
  EW-birlestir, ex-ONCESI cikis (add_div=False -> temettu YOK -> stopaj YOK). Anlamlilik = aylik
  kohort serisi uzerinde basit-t (donmus metrik; gunluk NW-lag5 aylik-kohorta uygulanmaz).
  NOT: "hold-10g" = donmus RUNUP_capture legi olarak YORUMLANDI (ex-SONRASI 10-gun tutus DEGIL --
  o, ex'i gecip temettu-dususu + %15 stopaji yer, tezi tersine cevirir). Stage-0'da acik-beyan.
- **Likit-evren (D-205-esik, donmus reuse):** ex-tarihte trailing-63g-medyan-ADV >= **1e7 TL**
  (MUTLAK esik, tercile-DEGIL; D205_LIQUID_ADV_MIN_TL). V1 + V2 icin ALL ve LIQUID kitaplari
  ayri raporlanir; likit-hayatta-kalma keep-bar'in retail-tradeability legidir.
- **TEK FARK -- maliyet girdisi:** demo-goal FLAT (per-side bp; round-trip = 2*bp/1e4) yerine
  D-207 per-isim round-trip rt[sym] (kote-birincil EOD-spread -> 252g-Roll geri-dusus -> re-olcekli
  tier). V1: her giris/cikis 0.5*rt[sym] yukler, /n_held; V2: olay-basi rt[sym]. **INDIRGEME
  GARANTISI:** rt uniform == 2*bp/1e4 oldugunda per-isim drag FLAT-drag'e BIREBIR esit
  (`tests/test_d209_h2b_runup.py` ile assert). lambda_kyle/order_value/pencereler D-204/207'de
  donuk -- kalibrasyon/optimizasyon YOK.
- **Kote panel:** olay-sembolleri icin yerel EOD bid/ask arsivinden kurulup ENJEKTE edildi
  (window=63, min_coverage=21, span 2019-07..2026-04). Kapsam %60 kote / %5.8 Roll / %34 tier
  (kote'siz gun/isimler modelin kendi belgelenmis hiyerarsisine duser). Arsiv CI'a girmez.

## 3. Sonuclar (frozen panel, ~1108 olay / 265 sembol BIREBIR reproduke; median est-yield %2.28)

### 3.1 ASIL okuma -- maliyet-ONCESI anlamlilik ALL'da var, LIKIT'te YOK

| olcum | V1 ALL | V1 LIQUID | V2 ALL | V2 LIQUID |
|---|---|---|---|---|
| relatif, **maliyet-ONCESI** ortalama | +%0.129/gun | +%0.055/gun | +%1.12/olay | -%0.27/olay |
| relatif, maliyet-ONCESI t | **NW 2.57** | NW 0.61 | 1.72 | -0.34 |
| relatif, **maliyet-SONRASI** (ASIL) | **-%0.123/gun** | +%0.0068/gun | +%0.065/olay | -%0.54/olay |
| relatif, maliyet-SONRASI t | **NW -2.27** | **NW 0.074** | **0.10** | -0.68 |
| gerceklesen round-trip maliyet | ~117 bps | ~28.6 bps | ~109 bps | ~27.6 bps |
| breakeven round-trip | ~60 bps | ~32.5 bps | ~115 bps | ~0 bps |
| rejim sign-stable (2022-01) | evet (--) | hayir (-+) | hayir (-+) | hayir (-+) |

**Kilit bulgu -- demo-goal NW-t=2.57 bir ALL-evren (illikit-suruklu) istatistigidir.** Maliyet-ONCESI
V1 gunluk-relatif NW-t **2.565** olarak BIREBIR reproduke oldu (port-fidelite kaniti). AMA bu
anlamlilik, **deploy-edilebilir likit-evrene** restrikte edildiginde KAYBOLUYOR: V1 LIQUID
maliyet-ONCESI NW-t = **0.61** (CI sifiri iceriyor); V2 LIQUID cost-free t = **-0.34** (negatif).
Yani edge, retail'in islem-yapamayacagi illikit isimlerde yasiyor.

### 3.2 Maliyet -- likit-evrende DUVAR DEGIL, anlamlilik duvar

Deploy-edilebilir **likit** evrende gerceklesen round-trip maliyet yalniz **~28.6 bps** (V1) /
**~27.6 bps** (V2) -- D-207-duzeltilmis kote-birincil model sayesinde ucuz, ve V1 likit breakeven'i
(**32.5 bps**) ALTINDA. Yani likit-evrende maliyet edge'i oldurmuyor: edge zaten cost-free
istatistiksel-sifir (madde 3.1). Buna karsin **ALL** evrende gerceklesen maliyet **~117 bps** >>
breakeven **~60 bps** -> V1 ALL maliyet-sonrasi anlamli-NEGATIF'e (NW-t=-2.27) doner; ama bu, retail'in
deploy-edemeyecegi illikit isimlerin maliyet-duvaridir. **Iki okuma da ayni HUKUMa cikar.**

### 3.3 V1 maliyet-sonrasi: ALL anlamli-negatif, LIQUID anlamli-alti-pozitif

- **V1 ALL:** maliyet-sonrasi -%0.123/gun, **NW-t = -2.27**, rejim sign-stable (pre -%0.062 /
  post -%0.159, ikisi-de negatif). Gerceklesen 117bp >> breakeven 60bp. -> ALL-evren maliyet-duvari
  (illikit), deploy-edilemez.
- **V1 LIQUID:** maliyet-sonrasi +%0.0068/gun, **NW-t = 0.074** (CI sifiri iceriyor), rejim
  sign-stable DEGIL (pre -%0.064 / post +%0.039). Gerceklesen 28.6bp < breakeven 32.5bp.
  -> likit-evren anlamlilik-duvari: cost-free bile t=0.61, sinyal istatistiksel-tradeable degil.

### 3.4 V2 maliyet-sonrasi: ALL anlamli-alti-pozitif, LIQUID negatif

- **V2 ALL:** cost-free +%1.12/olay (t=1.72, zaten anlamli-alti); maliyet-sonrasi +%0.065/olay,
  **t = 0.10**; rejim sign-stable DEGIL (pre -%0.86 / post +%0.67). Gerceklesen 109bp < breakeven
  115bp ama edge anlamli-degil.
- **V2 LIQUID:** cost-free bile **-%0.27/olay** (t=-0.34, NEGATIF); maliyet-sonrasi -%0.54/olay
  (t=-0.68); rejim sign-stable DEGIL. -> likit-evrende dusuk-turnover capture'da bile edge YOK.

### 3.5 keep-bar -- iki varyant da FAIL

| keep-bar leg | V1 (NW lag5) | V2 (basit-t) |
|---|---|---|
| maliyet-sonrasi rel ALL > 0 | FAIL (-%0.123) | PASS (+%0.065) |
| ALL \|t\| >= 2 | PASS* (\|-2.27\|, ama negatif) | FAIL (0.10) |
| rejim sign-stable | PASS (ikisi-de neg) | FAIL |
| likit-hayatta-kalma (likit rel>0 AND \|t\|>=2) | FAIL (t=0.074) | FAIL (negatif) |
| **keep-bar** | **FAIL** | **FAIL** |

*V1 ALL'da |t|>=2 saglaniyor ama isaret NEGATIF (anlamli-zarar) ve likit-hayatta-kalma FAIL ->
keep-bar yine FAIL. Hicbir varyant tam keep-bar'i (rel>0 AND |t|>=2 AND rejim-stabil AND
likit-hayatta-kalir) gecmiyor.

## 4. Hukum: YINE-TRADEABLE-DEGIL -> H2b adil-zeminde KESIN-KAPANIR (N<=3 SON)

**Verdict: YINE-TRADEABLE-DEGIL.** Ne V1 ne V2, donmus keep-bar'i frozen-anlamlilik-metriginde
geciyor. Onceden-ilan-edilen durust beklenti (anlamlilik-duvari, hi52-ikizi) **OLCUMLE dogrulandi.**

**Duvar tipi (Stage-0 sorusu) -- deploy-edilebilir likit-evrende ANLAMLILIK, maliyet DEGIL:**
H2b'nin unlu demo-goal NW-t=2.57'si bir **ALL-evren** (illikit-suruklu) istatistigidir. Deploy-
edilebilir likit-evrene (>=1e7 ADV) restrikte edilince edge **cost-free bile** istatistiksel-sifir
(V1 likit NW-t=0.61; V2 likit cost-free t=-0.34 negatif). Likit-evrendeki gercekci maliyet
(~28bp) breakeven'in (32.5bp) ALTINDA -- yani **maliyet bahanesi de kalkti**; geriye kalan tek
duvar **anlamlilik**. (ALL-evrende ek olarak bir maliyet-duvari var: 117bp >> 60bp breakeven, V1
ALL anlamli-negatife doner; ama o illikit ve deploy-edilemez.) -> **hi52'nin ikizi: maliyet degil,
ANLAMLILIK olduruyor -- bu kez varsayimla degil, OLCUMLE.**

**Yorum (demo-goal FLAT-elemesini CURUTMEZ, dogrular):** demo-goal H2b'yi FLAT-maliyetle elemisti;
D-209 gosteriyor ki maliyet duzeltilse bile -- ve likit-evrende maliyet GERCEKTEN ucuz olsa bile --
sinyal deploy-edilebilir evrende istatistiksel-tradeable degil. BOTTOM-LINE (tradeable-DEGIL)
korunur; netlesen: demo-goal'in tek-t>=2-adayinin o anlamliligi likit-deploy-evrende yok.

**OOS-bosluk (her durumda ZORUNLU):** ornek (2019-2026) tek-uzun yuksek-enflasyon rejimi; gercek
enflasyon-normallesme OOS YOK; rejim-degisim dayanikligi KANITLANAMAZ. (Burada moot: edge likit-
evrende cost-free bile anlamli-alti.)

**post-hoc gevsetme YOK:** hicbir esik/gate/sinyal/pencere/evren gevsetilmedi. Demo-goal lab'e gore
TEK degisiklik FLAT-maliyetin D-207-duzeltilmis per-isim maliyetle degistirilmesidir.

**KARAR: H2b temiz-arsiv** (N<=3 SON, 4. tur YOK). Mezarliktaki son t>=2-aday da adil-zeminde
kapandi; demo-goal H2/H2b graveyard-boslugu kapatildi. Kutlama YOK -- beklenen sonuc, olculdu.

## 5. Reuse / disiplin

- **Strangler:** donmus demo-goal H2 detection + V1/V2 defteri BIREBIR PORT edildi (drift-guard:
  motor ~1108/265 bandi disinda RAISE eder). D-207-duzeltilmis maliyet (`realistic_cost` +
  `per_stock_cost_panel` + `quoted_spread`) OLDUGU-GIBI reuse; D-203 frozen panel reuse. Committed
  d203/d204/d205 motorlari + thresholds mevcut bloklar SIFIR-dokunus (yalniz YENI d209_* + D209_*
  esik-blogu eklendi). INDIRGEME-GARANTISI (rt uniform -> FLAT) test ile kanitli.
- **Disiplin:** Stage-0 (`STAGE0_d209.json`) sonuclardan ONCE donduruldu; durust-beklenti
  (anlamlilik-duvari, hi52-ikizi) onceden-ilan-edildi ve OLCUMLE dogrulandi; kutlama YOK; N<=3
  ilk-resmi-olcum (count=1, 4. tur YOK). Olcum yerel + arsiv-destekli (CI-guvenli; kote panel
  enjekte, arsiv + parquet CI'a girmez -> committed test SENTETIK, gercek sonuc artifact olarak
  commit). Edge-kor (maliyet yalniz kote/ADV'den, getiriden DEGIL); look-ahead-safe (pozisyon
  ex-ONCESI 1..10 gun acilir, ex-ONCESI kapanir; likit-filtre + maliyet yalniz trailing-veri).
  ASCII.

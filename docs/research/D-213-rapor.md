# D-213 RR-Y1-003 STAGE-0: EX-ANTE REEL-FAIZ -> FORWARD XU100 TL-REEL GETIRISI -- ilk-resmi-olcum (N<=3: 1)

> Stage-0 on-kayit: `docs/yol1/STAGE0_d213.json` (sonuclardan ONCE donduruldu + commit'lendi).
> Ham sonuc: `docs/yol1/d213_results.json`. Motor: `src/screening/d213_real_rate.py` (YENI) +
> `src/screening/d213_config.py` (geometri). Karar esikleri: `src/signals/thresholds.py` D213_* blok
> (ADDITIVE) + reuse D207_TIER_MEGA_HALF_SPREAD / D204_COMMISSION_PCT (READ-ONLY). Veri-dayanak:
> D-212 / `docs/yol1/RR-Y1-003-asama0-veri.md` (envanter). NW-istatistikleri d211'den PORT.
>
> **Bu bir OLCUMDUR, optimizasyon DEGILDIR.** Cerceve-B surekli zaman-serisi tahmin (tek-varlik
> timing; hisse-secimi DEGIL). Tum esik/tanim/keep-bar/efektif-pencere Stage-0'da donduruldu ve
> **sonuclardan ONCE commit'lendi**; hicbiri post-hoc gevsetilmedi (predictor-yeniden-tanimi YOK,
> pencere-genisletme YOK, lag-yeniden-secimi YOK, maliyet-yeniden-kalibrasyonu YOK, keep-bar-gevsetme
> YOK, change-form-mining YOK). N=1 aday (ex-ante reel-faiz piyasa-timing'i), fiyat-ORTOGONAL eksen.
>
> **STRANGLER (sert-kisit):** committed motor (d203/d204/d205/d209/d211 + realistic_cost + thresholds
> mevcut bloklar + evds_client + ballast) SIFIR-dokunus -- D-213 yalniz YENI d213_* dosyalari +
> D213_* esik-blogu + registry + doc ekledi. EVDS ham-verisi CI'a GIRMEZ (sentetik unit-test); EVDS
> pull'lari donmus tracked snapshot (D-211 deseni), gercek olcum yerel ARTIFACT (`d213_results.json`).
> Calisma-aninda HTTP-free (donmus snapshot okur). ASCII. Mutlak-yol commit'lenmez.

## 0. Kapsam-guard (OLCUMDEN ONCE; efektif-pencere GERCEK-deger, varsayilmadan)

Olcumden once 3 EVDS serisi + bagimli-panel + deploy-nakit-bacak GERCEK-temiz-baslangici denetlendi
(lab-demo-clone1 bolum-6 "sessiz-kirli mid-2019" tuzagina karsi):

| seri (rol) | gercek-temiz baslangic |
|---|---|
| TP.APIFON4 (nominal predictor + nakit-bacak) | **2019-01** temiz (1839 gunluk, annual-pct) |
| TP.ENFBEK.PKA12ENF (12ay-beklenen-enflasyon) | **2019-01** temiz (88 aylik, annual-pct) |
| XU100 fiyat-only (bagimli getiri / long-bacak) | **2019-01** temiz (her ay deger-var; mid-2019-sessiz-DEGIL) |
| TUFE (deflator + CPI-YoY) | 2010-01 temiz |
| TLREF return-index (deploy-nakit ADAYI) | **2022-07** -- oncesi sessiz-NaN (tarih-var, value-NULL) |

**TUZAK BULUNDU (TLREF):** TLREF snapshot'inda tarihler 2019-01'den ~31/ay mevcut AMA value-sutunu
2022-07-01'e kadar NaN (ilk-non-null ay-sonu = 2022-07). Gercek-temiz-baslangic 2022-07, 2019-DEGIL.

**COZUM-LOCK (the maintainer, sonuc-oncesi tasarim-secimi -- post-hoc DEGIL):** nakit-bacak TLREF DEGIL;
nakit-bacak = APIFON4-turevli reel-carry (`cash_nom(t)=(1+APIFON4(t)/100)^(1/12)-1`, T+0-knowable
ay-ici-tahakkuk; `cash_real(t)=cash_nom(t)-infl_MoM(t)`). APIFON4 2019-01-temiz VE TLREF'i
yakindan-izler (ikisi-de TR gecelik/kisa referans-maliyeti). **EFEKTIF-PENCERE = 2019-01..2026-04**
(tum bacaklar temiz; ~87 forward-ay, lag-1 sonrasi 87 kullanilabilir). TLREF'i literal-uygulayip
pencereyi 2022-07'ye daraltmak rejim-A'yi (2019-21) silip keep-bar[2]'yi olduruurdu; APIFON4-nakit
bunu sessiz-kirli-veri SOKMADAN engeller. Reel-faiz prediktoru zaten SAF-EVDS (faiz+enflasyon),
mcap-panel-tuzagindan bagimsiz.

## 1. Soru

Ex-ante reel-faiz (nominal funding-faizi eksi 12ay-beklenen-enflasyon), **~t+15g bilinebilir** formda
(yani lag-1), **gelecek-ayin XU100 TL-REEL getirisini** tahmin ediyor mu? Tek-varlik zaman-serisi
(endeks-long vs nakit); hisse secimi DEGIL. Fiyat-ORTOGONAL eksen (faiz/enflasyon girdileri, fiyat-
ozelligi YOK).

**Onceden-ilan-edilmis durust beklenti (kutlama YOK):** prior DUSUK-ORTA. Ex-ante reel-faiz, D-211
yabanci-akimdan DAHA AZ bayat (~t+15g vs ~6hf) -> yapisal-olarak daha-yuksek oncu-sans. Olasi hukum
yine TRADEABLE-DEGIL, AMA tutarsa D-211'den GERCEK bir ayrim olurdu (farkli mekanizma: makro-politika-
durusu vs akim). Reel-faiz cok-persistan (yuksek AR1) -> Stambaugh-farkindaligi ZORUNLU; es-hareket
(lag-0) != oncu-tahmin (lag-1). Surpriz ihtimali: lag-1 anlamliligi hayatta-kalirsa duz raporlanir.
Her durumda teshis-degeri: lag-0 vs lag-1 vs ex-post-lag-2 kontrasti basli-basina ogretici.

## 2. Olcum cercevesi (Stage-0'da donmus)

- **Predictor (LOCK):** `r_ex_ante(t) = nominal(t) - expected_inf(t)` (annual yuzde-puan, LEVEL).
  nominal = TP.APIFON4 (TCMB AOFM agirlikli-ortalama fonlama-maliyeti); expected_inf =
  TP.ENFBEK.PKA12ENF (TCMB Piyasa-Katilimcilari-Anketi 12ay-ileri beklenen-enflasyon). **LEVEL
  birincil**; change/impulse (delta r_ex_ante) yalniz IKINCIL-rapor, primary'yi kurtaramaz (mining
  YASAK). Return-ay t icin predictor = r_ex_ante(t-1): nominal gunluk-gozlemli + (t-1)-anketi
  ~(t-1)-ortasi yayinlanir (~t+15g) -> (t-1)-sonu karar-aninda bilgi-kumesinde -> look-ahead-safe.
- **Dependent (LOCK, D-211 ile AYNI):** XU100.IS fiyat-only (temettu YOK; fiyat-getiri fallback).
  `r_nom(t)=idx(t-sonu)/idx(t-1-sonu)-1`; TL-reel = `r_nom(t) - infl(t)` (TUFE MoM, spec-literal).
- **Pencere (LOCK):** PRIMARY 2019-01..2026-04 (87 forward-ay). Kapsam-guard (bolum-0) tum-bacaklari
  2019-01-temiz dogruladi; TLREF haric (sessiz-NaN 2022-07'ye-kadar). Interpolasyon YOK (eksik ay DROP).
- **Rejim (LOCK):** split 2022-01-01; A=2019-02..2021-12 (derin-negatif reel-faiz), B=2022-01..2026-04
  (yuksek-enf; reel-faiz negatif sonra 2024+ pozitife doner). Kararlilik: slope-isareti A ve B'de AYNI.
  Konsantrasyon (leave-one-regime-out): bir alt-donemi cikarmak tam-orneklem isaretini CEVIRMEMELI.
- **Istatistik (LOCK):** OLS slope + Newey-West HAC t, lag=6. Seri lag-1 predictor + 1-ay forward ile
  NON-overlapping. Stambaugh-farkindaligi: r_ex_ante AR(1) + non-overlap raporlanir.
- **Deploy-edilebilir bacak (LOCK):** ekonomik-prior = negatif-reel-faiz hisseyi-tesvik (finansal-
  baski/TINA). (t-1)-sonu, r_ex_ante(t-1) < 0 -> XU100 long (t-ayi reel getiri); >= 0 -> APIFON4-nakit
  reel-carry. Sifir-esik (tam-orneklem-medyan PEEK-etmez -> look-ahead-safe). Maliyet: endeks-switch
  one-way = D207_TIER_MEGA_HALF_SPREAD (5.28bp); Kyle=0; komisyon=0; her giris+her cikis one-way;
  buy-hold tek-giris one-way. NET kumulatif TL-reel vs buy-hold XU100 NET kumulatif TL-reel.
- **Ex-post kontrol (IKINCIL, ZORUNLU):** `r_ex_post(t)=nominal(t)-CPI_YoY(t)`, ~t+45g -> lag-2.
  reg(forward ~ r_ex_post(t-2)). DIAGNOSIS-only; keep-bar'a SAYILMAZ (daha-bayat; CPI deflator'a-da
  girer -> yorum-dikkati). Primary'yi kurtaramaz.
- **keep-bar (LOCK, 4'u-de zorunlu):** [1] primary ex-ante lag-1 NW|t|(lag=6)>=2.0; [2] slope-isareti
  rejim-stabil (A AND B ayni) AND konsantre-degil; [3] deploy-bacak NET-kumulatif buy-hold'u GECER
  (post-cost, lag-1); [4] look-ahead-safe (lag-1; lag-0 + ex-post-lag-2 NON-DEPLOYABLE, sayilmaz).
  4'u-de PASS -> TRADEABLE (aday-only); herhangi-biri fail -> TRADEABLE-DEGIL.

## 3. Sonuclar (frozen snapshot hash-asserted; 87 forward-ay)

r_ex_ante(t-1) ozet: mean=**+2.26** std=**15.20** min=**-28.99** max=**+24.08** puan; AR(1)=**0.986**
(cok-yuksek persistans -> Stambaugh-yanlilik BUYUK, asagi-bkz); negatif-pay %34.5 (30 ay reel-faiz<0).

### 3.1 Primary regresyon (ex-ante lag-1) -- DOGRU-ISARET ama anlamlilik-alti

| olcum | deger |
|---|---|
| slope b (r_ex_ante(t-1) -> forward TL-reel) | **-0.00100** |
| NW HAC t (lag=6) | **-1.82** |
| n (forward-ay) | 87 |
| R^2 | 0.032 |
| r_ex_ante AR(1) | 0.986 (cok-yuksek -> Stambaugh-yanlilik BUYUK) |

Slope NEGATIF ve **ekonomik-olarak dogru-isaret**: yuksek ex-ante reel-faiz -> dusuk forward hisse
TL-reel getiri (siki-politika hisseye-kotu). AMA NW|t|=1.82 < 2.0 -> **anlamlilik-alti**; R^2 ~%3.
Bu D-211'den DAHA-iyi (orada slope sifir/ters, t=0.73) ama keep-bar[1]'i GECMIYOR. **kritik uyari:**
AR(1)=0.986 -> regresyon-t Stambaugh-yanli (siser); gercek-anlamlilik eger-varsa daha-da-zayif ->
TRADEABLE-DEGIL hukmu bu yonde SAGLAMLASIR.

### 3.2 Rejim kararliligi -- isaret stabil (her iki donemde negatif), konsantre-degil

| | slope | NW t | n |
|---|---|---|---|
| A 2019-2021 | -0.00150 | -0.79 | 35 |
| B 2022-2026 | -0.00098 | -1.77 | 52 |

Iki donemde de slope NEGATIF (full_sign=-1, same_sign_AB=true); leave-one-regime-out tam-orneklem
isaretini cevirmiyor (konsantre-DEGIL) -> keep-bar[2] PASS. Isaret tutarli/dogru-yon AMA her-iki
donemde de anlamlilik-alti (B daha-guclu ama yine <2). Kararlilik tek-basina yeterli leg degil.

### 3.3 Deploy-edilebilir bacak -- buy-hold'u GECIYOR ama anlamli-DEGIL

| olcum | deger |
|---|---|
| n_ay | **87** (2019-02..2026-04; APIFON4-nakit, tum-pencere temiz) |
| deploy-kural | r_ex_ante(t-1)<0 -> XU100-long; else APIFON4-nakit |
| endeks-long pay | %34.5 |
| switch sayisi | **4** (cok-dusuk turnover; reel-faiz persistan) |
| one-way maliyet | 5.28 bp |
| strat NET kumulatif TL-reel | **+%85.5** |
| buy-hold XU100 NET kumulatif TL-reel | **+%47.5** |
| strat buy-hold'u gecer mi | **EVET** |
| aylik relatif ortalama (strat-bh) | +%0.10 |
| aylik relatif NW-t | **0.16** |

Deploy-bacak buy-hold'u ~38 puan reel GECTI (+%85.5 vs +%47.5) -> keep-bar[3] PASS. AMA bu "gecer"
istatistiksel-DEGIL: aylik relatif NW-t yalniz **0.16** (sifirdan ayrilamaz). 87-ay boyunca yalniz 4
switch (reel-faiz persistan oldugundan rejim-anahtarlama nadir) -> ustunluk birkac iyi-zamanli geciste
yogun, anlamli-degil. Yani keep-bar[3] teknik-PASS ama ANLAMLILIK yok -> tek-basina edge kaniti degil.

### 3.4 Look-ahead + contemporaneous teshis -- lag-1 ~ lag-0 (D-211'den FARKLI)

| | slope | NW t | n | R^2 | durum |
|---|---|---|---|---|---|
| lag-1 (primary, deployable) | -0.00100 | **-1.82** | 87 | 0.032 | DEPLOYABLE |
| lag-0 (es-zamanli) | -0.00110 | **-1.91** | 87 | 0.039 | NON-DEPLOYABLE |

**En ogretici bulgu (D-211 ile zit):** D-211'de lag-0 GUCLU (t=3.68) ama knowable lag-2 BOS'tu ->
akim "es-hareket, oncu-degil". D-213'te lag-1 (t=-1.82) ~ lag-0 (t=-1.91) NEREDEYSE-AYNI. Yani
ex-ante reel-faizde knowable-form ile es-zamanli-form arasinda UCURUM YOK: icerigi neyse (zayif-ama-
dogru-isaret) deploy-edilebilir formda da KORUNUYOR. Bu, reel-faizin yuksek-persistansinin (AR1=0.99)
dogal sonucu -- bir-ay-once-bilmek bilgi kaybetmiyor. **Bu D-211'den GERCEK bir mekanizma-ayrimi:**
icerik bayat-form-handikabindan DEGIL, basitce ZAYIF (anlamlilik-alti) oldugundan eksik. keep-bar[4]
PASS (lag-1 uygulandi; lag-0 sadece teshis, hukma sayilmaz).

### 3.5 Ikincil ex-post kontrol (report-only, hukmu kurtaramaz)

- **r_ex_post(t-2) (ex-post reel-faiz, CPI_YoY ile):** slope=-0.00050, NW-t=**-1.24**, n=86.
  Ex-ante (t=-1.82) > ex-post (t=-1.24): **ileri-bakan beklenen-enflasyon, gerceklesmis-enflasyondan
  biraz-daha-bilgili** (ama ikisi-de anlamlilik-alti). Ex-post daha-bayat (lag-2) + CPI deflator'a-da
  girdiginden mekanik-bagimli -> sadece teshis, hukum-immutable.
- **change/impulse (delta r_ex_ante):** primary-olarak CALISTIRILMADI (LEVEL kilitli primary; change
  mining YASAK).

### 3.6 keep-bar -- yalniz [1] FAIL -> verdict TRADEABLE-DEGIL

| keep-bar leg | sonuc |
|---|---|
| [1] primary ex-ante lag-1 NW\|t\|(lag=6) >= 2.0 | **FAIL** (1.82, dogru-isaret ama <2) |
| [2] rejim-stabil AND konsantre-degil | PASS (her-iki-donem negatif, konsantre-degil) |
| [3] deploy-bacak buy-hold'u gecer | PASS (+%85.5 vs +%47.5) AMA rel-NW-t=0.16 anlamsiz |
| [4] look-ahead-safe (lag-1; lag-0/ex-post NON-DEPLOYABLE) | PASS |
| **verdict** | **TRADEABLE-DEGIL** |

## 4. Hukum: TRADEABLE-DEGIL (temiz-kayit) -- dogru-isaret/dogru-mekanizma ama anlamlilik-alti

**Verdict: TRADEABLE-DEGIL.** Yalniz keep-bar[1] (anlamlilik) FAIL; [2]/[3]/[4] PASS. Onceden-ilan-
edilen durust beklenti (prior dusuk-orta, olasi TRADEABLE-DEGIL) **OLCUMLE dogrulandi** -- fiyat-
ORTOGONAL bir eksende (makro-politika-durusu).

**Duvar tipi -- ANLAMLILIK (zayif-icerik), maliyet/bayatlik DEGIL:** endeks mega-likit, switch
one-way 5.28bp, yalniz 4 switch; maliyet bahanesi yok. Bayatlik-bahanesi de yok: lag-1 (t=-1.82) ~
lag-0 (t=-1.91) -> knowable-form es-zamanli-formla ayni; icerik kayip-degil, BASITCE-ZAYIF. AR1=0.99
Stambaugh-yanliligi gercek-t'yi daha-da-asagi-cekecek -> hukum saglamlasir.

**MEZARLIK-DURUSTLUGU -- "total-return olsa kurtarirdi" YANLIS-ACILISINI ONCEDEN KAPAT
(invariyans-ispati):** Bagimli XU100 fiyat-only'dur (temettu YOK; meta.json caveat'i: equity
~%2-4/yil cezali). Gelecek-biz "tam total-return endeks olsaydi keep-bar[1] gecerdi" diye
yeniden-acmasin diye burada matematiksel olarak kapatiyoruz. Yanltmayan TEK total-return
duzeltmesi -- sabit (flat) yillik temettu-getirisi ekleme -- primary anlamliligi YAPISI GEREGI
DEGISTIREMEZ: `r_nom'(t)=r_nom(t)+d` (d=yillik/12 sabit) -> `real_ret'(t)=real_ret(t)+d`, yani
bagimliya **sabit eklemek** OLS egimini ve onun NW-t'sini DEGISTIRMEZ (yalniz kesisimi kaydirir).
Dolayisiyla keep-bar[1]'in NW|t|=1.82'si sabit-temettu altinda AYNEN 1.82 kalir -- TR-fix fail'i
kurtaramaz. (Gercek/mevsimsel TR egimi oynatabilirdi AMA tam-TR endeksi yerelde KURULAMAZ:
snapshot fiyat-only, `dividends/`+`index_components/`+`corporate_actions/` arsiv-klasorleri BOS,
kompozisyon-agirligi yok -> her yeniden-kurulum cok-serbestlik-dereceli = yanltma araci, REDDEDILDI.)
TR-fix'in TEK gercek etkisi deploy-bacak ekonomisidir ve YONU bizim-aleyhimize: temettu always-in
buy-hold'u, bazen-cash timing'den daha-cok besler -> B&H'i yenmek ZORLASIR; yani fiyat-only kurulum
timing'imizi hafifce KAYIRIYORDU. Ozet: bu duvar anlamlilik-duvaridir, temettu-handikap-duvari
DEGIL. Tam fizibilite: `docs/yol1/RR-Y1-003-totalreturn-fizibilite.md`.

**D-211'den ayrim (ogretici):** D-211'de yabanci-akim "es-hareket, oncu-degil"di (lag-0 guclu, knowable
lag-2 bos). D-213'te ex-ante reel-faiz dogru-isaretli, rejim-stabil, deploy-bacagi buy-hold'u geciyor
VE knowable-form es-zamanli-formla ayni guctedir -- AMA bu guc anlamlilik-baremine (t>=2) ulasmiyor.
Yani D-213 "neredeyse-bir-sey" ama olculen-pencerede istatistiksel-degil. Bu, hipotezin tamamen-bos
(D-211) yerine ZAYIF-AMA-DOGRU-YONLU oldugunu gosterir: gelecekte daha-uzun/farkli-rejim OOS'ta
yeniden-bakmaya degebilecek tek fark, ama SU-AN tradeable-DEGIL.

**OOS-bosluk (her durumda ZORUNLU, ACIK):** 2019-2026 tek-uzun yuksek-enflasyon rejimidir; gercek
enflasyon-normallesme OOS YOK -> rejim-degisim dayanikligi KANITLANAMAZ. Reel-faiz derin-negatiften
(2021-23 baski) pozitife (2024+) gecti ama hepsi yuksek-enf-semsiyesi altinda. Stambaugh: AR1=0.99
persistan-regressor -> kucuk-orneklem t-yanliligi yukari; gercek-anlamlilik raporlanandan zayif.

**post-hoc gevsetme YOK:** hicbir esik/tanim/pencere/lag/maliyet/keep-bar gevsetilmedi. Stage-0
sonuclardan ONCE commit'lendi (anti-post-hoc guard; motor dosya-yoksa REDDEDER). Nakit-bacak APIFON4-
secimi sonuc-ONCESI kapsam-guard'da (bolum-0) gerekceli-donduruldu, post-hoc-DEGIL. Deployment ayri
bir the project kararidir; bu harness OLCER + ONERIR, asla otomatik-deploy ETMEZ -- ve burada onerilecek
aday yok.

**KARAR: ex-ante reel-faiz -> forward XU100 TL-reel endeks timing'i temiz-arsiv (N<=3, count=1).**
Kutlama YOK -- beklenen-yonde sonuc, fiyat-ortogonal eksende OLCULDU ve duz kaydedildi. (Tek not:
D-211'in tam-bos'una karsi bu zayif-ama-dogru-yonlu -- gelecekte rejim-degisim OOS'ta tekrar-bakim
gerekcesi, deploy-aday-DEGIL.)

## 5. Reuse / disiplin

- **Strangler:** committed d203/d204/d205/d209/d211 + realistic_cost + thresholds mevcut bloklar +
  evds_client SIFIR-dokunus; yalniz YENI `d213_real_rate.py` + `d213_config.py` + D213_* esik-blogu
  (ADDITIVE) eklendi. Maliyet legi D207_TIER_MEGA_HALF_SPREAD + D204_COMMISSION_PCT'yi READ-ONLY reuse
  eder. NW-istatistikleri d211'den PORT. Snapshot icerik-hash'leri yukleme-aninda assert edilir
  (drift -> RAISE): apifon4 e279aba1829da9d3, enfbek12 716c5dc2685f8f1a, xu100 f909f79881ca8e2b,
  tufe 28052c6f46d08446.
- **Disiplin:** Stage-0 (`STAGE0_d213.json`) sonuclardan ONCE donduruldu + COMMIT'lendi (kapsam-guard
  RESULT'i ICINDE, efektif-pencere gercek-deger); durust-beklenti (prior dusuk-orta, TRADEABLE-DEGIL)
  onceden-ilan-edildi ve OLCUMLE dogrulandi; kutlama YOK; N<=3 ilk-resmi-olcum (count=1). EVDS
  ham-verisi CI'a GIRMEZ -> committed test SENTETIK (`tests/test_d213_real_rate.py`), gercek sonuc
  ARTIFACT (`d213_results.json`); EVDS pull'lari donmus tracked snapshot. Edge-kor; look-ahead-safe
  (lag-1 boyunca; lag-0 + ex-post-lag-2 NON-DEPLOYABLE damgali, hukma sayilmaz). ASCII; mutlak-yol-yok.

# D-186 Trend-Motor Duzeltme Turu -- Sonuc Raporu

**Tarih:** 31 May 2026
**Tur:** Olcum-duzeltme turu (yeni Stage 0 on-kayit) + 5-ajan adversarial dogrulama
**Dayanak:** D-185 raporu (3 caveat + bozuk DD), RR-039 §6, RR-038, ARCHITECTURE v2.0, DEC-044, DEC-039
**Stage 0 on-kayit:** `docs/trend_test/STAGE0_d186_preregistration.json` (commit ec16aae, sonuc ONCESI)
**Ham sonuc:** `docs/trend_test/d186_results.json`
**Veri:** AYNI frozen OHLCV snapshot `trend_v1_ohlcv` (content_hash `d1423f89`), AYNI 88 ticker, AYNI trade'ler

---

## 1. TL;DR -- DEC-044 VERDICT: GECMEZ (5-ajan dogrulamali)

D-185 verdict'i (PROMISING ama INCONCLUSIVE) uc caveat + bozuk DD ile sakatti. D-186 bunlari
duzeltti (kurallari/snapshot'i/trade'leri DEGISTIRMEDEN -- sadece olcum). Frozen DEC-044 kuralina gore:

**HICBIR varyant gecmedi. 6 hucrenin tamami YALNIZCA `fails_fair_random_benchmark` ile takildi.**

Uc bagimsiz duzeltme, uc bagimsiz sonuc:

1. **DD ARTEFAKTI dogrulandi (D-185 max_dd cokuyordu).** Concurrency-cap K=10 gercek portfoy DD =
   **%15-21** (D-185 ~%99 yerine), %35 esiginin cok altinda. D-185'in TEK gate basarisizligi
   (max_dd) gercekten artefaktti; **risk hicbir zaman sorun degildi.**
2. **Drift ANA edge'di.** Nominal full-window getiri %9-13 → XU100-relative %2.2-2.8 (drift ~%72-80).
   Disinflasyon diliminde relative getiri %0.8-3.0 -- D-185 nominal'den COK dusuk (KASITLI; XU100 da
   yukseliyor, relative "ne kadar gectin"i olcer).
3. **Entry-timing edge'i ANLAMSIZ.** Adil null'a (random girise AYNI stop+trailing+on-filtre) karsi,
   disinflasyonda, strateji random'i %95 dilimde YENEMEDI (en iyi C: %90.6-91.7, near-miss; A/B
   %63-79). Kesitsel-duzeltilmis CI'ler TUM hucrelerde sifiri ICERIYOR (C: [-0.017, +0.084]).

**NIHAI YORUM (5-ajan dogrulamali):** D-185'in "edge"i agirlikla (a) nominal TL drifti + (b) cikis/stop
mekanizmasi (kaybedeni kirpmasi) idi -- **entry-timing becerisi DEGIL.** Tetik/retest giris kurallari,
dogru kontrol edilince (drift-arinmis + adil-null + disinflasyon + kesitsel-anlamlilik), random girise
gore anlamli deger KATMIYOR.

**DEC-044 → GECMEZ.** Frozen kural: bu kesisimde edge anlamsizlasir → trend-motoru da (Faz 0
cross-sectional gibi) bu evren/pencerede ZAYIF. **Iki paradigma da test edildi (bilgi, basarisizlik
degil).** Sonraki adim: premise yeniden dusunulur (DEC-039, O+Cagan).

---

## 2. Yontem (on-kayitli; sadece olcum degisti)

AYNI 3 varyant (A/B/C), AYNI parabolik on/off, AYNI trend_config parametreleri, AYNI frozen snapshot,
AYNI trade'ler (trend_backtest.backtest_variant). Degisen yalniz metrik (N<=3 korundu, dogrulama turu):

- **FIX1:** concurrency-cap K=10, esit-agirlik (1/K), gunluk MTM portfoy → gercek max-DD (bozuk
  full-capital cumprod yerine). `trend_portfolio.build_portfolio`.
- **FIX2:** XU100-relative (DECISIVE) + real-CPI (CONFIRMATORY -- EVDS TUFE TP.FG.J0 yuklendi, 85 ay).
  Dilim-bazli getiri. `trend_d186.add_relative_returns/add_real_returns`.
- **FIX3:** ADIL null (random girise AYNI stop+trailing+MAX_HOLD + AYNI on-filtre: ADV her zaman,
  parabolik-eligibility parabolic_on'da) → entry-timing izolasyonu. Kesitsel-anlamlilik: gunluk-toplanmis
  blok-bootstrap (block=21, reuse `block_bootstrap_ci`). `trend_d186.fair_random_null/cs_significance`.

---

## 3. FIX 1 -- Gercek portfoy DD (D-185 artefakti capandi)

| Varyant/filtre | D-185 max_dd (ARTEFAKT) | D-186 gercek max_dd | admit/skip (K=10) |
|---|---|---|---|
| A on | ~0.99 | **0.2012** | 481/670 |
| A off | ~0.99 | 0.2148 | 483/684 |
| B on | ~0.98 | **0.1485** | 275/582 |
| B off | ~0.99 | 0.1503 | 287/727 |
| C on | ~0.91 | **0.1666** | 338/437 |
| C off | ~0.95 | 0.1666 | 332/491 |

Tum gercek DD'ler %15-21 → %35 esiginin altinda. **D-185'in max_dd gate'i tam-sermaye cumprod
artefaktiydi (total_net_return ~1e+26); gercek risk her zaman makuldu.** (Adversarial denetim:
`confirmed_correct`.)

---

## 4. FIX 2 -- Drift-arinmis getiri (nominal vs relative) + dilim-bazli decay

**Full-window (drift cikariliyor):**

| Varyant | nominal/trade | XU100-relative/trade | drift payi |
|---|---|---|---|
| A on | 0.0904 | 0.0255 | ~%72 |
| B on | 0.1273 | 0.0283 | ~%78 |
| C on | 0.0835 | 0.0221 | ~%74 |

**Dilim-bazli relative (+ real-CPI), parabolic_on:**

| Varyant | pre_surge 2019-21 | high_inflation 2021-24 | disinflation 2024-26 |
|---|---|---|---|
| A | rel 0.048 / real 0.062 | rel 0.025 / real 0.056 | rel **0.008** / real **-0.001** |
| B | rel 0.060 / real 0.074 | rel 0.017 / real 0.073 | rel **0.016** / real 0.007 |
| C | rel 0.052 / real 0.054 | rel 0.003 / real 0.031 | rel **0.029** / real 0.020 |

KRITIK (kasitli siklastirma -- on-kayitta belirtildi): XU100-relative disinflasyon sayilari D-185
nominal'den COK dusuk. Bu BEKLENEN ve KASITLI, hata DEGIL: endeks de yukseliyor, relative yalniz
endeksi gecme miktarini olcer. Karar kurali bilerek zor. Relative edge en yuksek pre_surge'da (~%5),
high_inflation'da neredeyse kayboluyor (nominal sisirmesi drift'ti), disinflasyonda kucuk.

---

## 5. FIX 3 -- Entry-timing izolasyonu (adil null) + kesitsel anlamlilik

| Varyant/filtre | disinflasyon relMean | adil-null mean | null p95 | random pctile | gate (>=0.95)? | CS 95% CI | sifir disinda? |
|---|---|---|---|---|---|---|---|
| A on | 0.0083 | 0.0045 | 0.0264 | 0.650 | HAYIR | [-0.027, 0.044] | HAYIR |
| A off | 0.0082 | 0.0050 | 0.0283 | 0.637 | HAYIR | [-0.027, 0.044] | HAYIR |
| B on | 0.0156 | 0.0048 | 0.0309 | 0.787 | HAYIR | [-0.038, 0.122] | HAYIR |
| B off | 0.0093 | 0.0053 | 0.0313 | 0.651 | HAYIR | [-0.041, 0.098] | HAYIR |
| C on | 0.0289 | 0.0050 | 0.0355 | **0.906** | HAYIR | [-0.017, 0.084] | HAYIR |
| C off | 0.0302 | 0.0053 | 0.0360 | **0.917** | HAYIR | [-0.016, 0.089] | HAYIR |

- Adil-null null_mean POZITIF (~0.005): random girisler de AYNI karli trailing-stop cikisiyla endeksi
  hafifce geciyor → null, "entry-agnostik trend-takibi" -- ZOR bir baseline. Bu dogru.
- C en guclu (relMean null_mean'in ~6 kati) AMA relMean (0.029-0.030) null'un p95'inin (0.036) ALTINDA →
  random eslesmis girislerin ~%8-9'u C'yi geciyor → pctile 0.91, %95 barini gecmiyor. **Temiz near-miss,
  artefakt degil** (adversarial denetim: `confirmed_correct`).
- **TUM hucrelerin kesitsel-duzeltilmis CI'si sifiri iciyor** → disinflasyon relative edge'i bagimsiz
  olarak da sifirdan ayirt edilemez.

**HONEST hukum (adversarial denetim direktifi):** Entry-timing disinflasyonda istatistiksel olarak
ANLAMLI alfa URETMIYOR (pctile 0.65-0.92 < 0.95; CS-CI sifiri iciyor). Gozlenen %0.8-3.0 relative getiri
adil random baseline'dan ayirt edilemez. "Zayif-ama-gercek edge" iddiasi yapilMAMALI (CS-CI reddediyor);
C'nin 0.917'si yalnizca betimsel near-miss.

---

## 6. Adversarial dogrulama (5 bagimsiz denetci -- workflow wf_098362b6)

| Denetim | Iddia | Verdict | Severity |
|---|---|---|---|
| Adil-null dogru/adil mi? | entry izolasyonu temiz | **confirmed_correct** | none |
| Relative drift dogru mu? | drift dogru cikariliyor | **partially** | minor (asagida) |
| Gercek DD dogru mu? | DD under-count degil | **confirmed_correct** | none |
| C aslinda geciyor mu? (steelman) | C false-negative | **confirmed_correct** (C temiz near-miss) | none |
| "Iki paradigma zayif" dogru yorum mu? | yorum dogru | **confirmed_correct** | none |

5/5 GECMEZ'i DOGRULADI. Tek minor bulgu (denetci #2): relative formul `(1+gross)/(1+xu)-1-cost` yerine
`(1+net)/(1+xu)-1` olmaliydi (cost, geometrik olceginin disinda cikariliyor → fark ~1e-4). AMA bu
**simetrik** (hem strateji hem null ayni formulu kullaniyor) → verdict'i ETKILEMEZ. Ayrica fair-null'daki
bos-resample sifir-doldurmasi (varsa) strateji LEHINE calisir (GECMEZ'e karsi). Ikisi de immaterial ve
verdict'i degistirmiyor. Post-hoc duzeltilMEDI (on-kayit disiplini); gelecek tur icin temiz formul onerildi.

---

## 7. Ne anlama geliyor

- **D-185'in edge'i = nominal drift + cikis-mekanizmasi, entry-timing DEGIL.** Drift cikarilip, cikis
  random'da da eslestirilince, tetik/retest girisleri random'i anlamli yenmiyor.
- **Risk (DD) hicbir zaman sorun degildi** -- D-185 max_dd gate'i artefaktti.
- **Iki paradigma da test edildi:** Faz 0 (cross-sectional faktor, honest_t<2) + D-185/186 (zaman-serisi
  trend, fair-null gecmiyor). Her ikisi de bu evren (BIST100 survivors) / pencerede (2019-2026) zayif.
  Bu **degerli bilgi**, basarisizlik degil: iki ana hipotez de kendi verimizle elendi.

---

## 8. Caveat'lar (Cagan onayinda gorulmeli)

- Survivors-only (88 ticker) korundu → relative edge de UST-SINIR egilimli; gercek edge daha da kucuk
  olabilir. GECMEZ bu yuzden DAHA guclu (ust-sinirda bile gecmiyor).
- Real-CPI (EVDS TUFE) CONFIRMATORY ve in-memory cekildi (parquet'e DONDURULMADI) → re-run EVDS key
  ister. DECISIVE taban XU100-relative frozen snapshot'tan TAM reproducible.
- Relative formul minor cost-yerlesim kusuru (simetrik, ~1e-4, verdict'i etkilemez) -- gelecek tur
  `(1+net)/(1+xu)-1` kullansin + bos-resample'i atlasin (denetci #2 onerisi).
- C 0.917 betimsel near-miss; "gercek edge" olarak SUNULMUYOR (CS-CI sifiri iciyor).
- Veri olayi: D-186 gelistirme sirasinda clone3 calisma agaci Stage 0 commit'inden sonra harici bir
  `git checkout master` ile master'a gecmisti (reflog HEAD@{0}); is feature branch'te commit'liydi,
  kurtarildi (kayip yok). Builder erken-commit ile korudu.

---

## 9. DEC-039 + Oneri

Bu program OLCTU + 5-ajan adversarial dogruladi + frozen DEC-044'e gore verdict uretti: **GECMEZ.**
Builder oneri sunar, karar vermez. Oneri (O+Cagan karari):

- **Katman A motoru olarak ne cross-sectional faktor ne de bu trend-varyant seti gerekcelenMIYOR**
  (ikisi de test edildi, ikisi de zayif). Mevcut kanit, bu evren/pencerede "alfa entry-secimi"nden
  cok "rejim/maliyet/cikis-disiplini"nde oldugunu soyluyor (RR-038 ana dersiyle tutarli).
- Sonraki adim secenekleri (O+Cagan): (a) premise yeniden -- farkli evren (BIST-genis/likidite-disi
  delisted dahil), farkli ufuk, veya fundamental-suzgec eklenmis hibrit; (b) entry'den cok cikis/risk-
  yonetimi + rejim-filtresi merkezli tasarim; (c) trend-motoru tamamen rafa, baska Katman A hipotezi.
- Karar kurali frozen oldugu icin verdict mekanik; Builder gevsetmedi, O+Cagan da sonuc gorup
  gevsetmemeli (post-hoc yasagi).
